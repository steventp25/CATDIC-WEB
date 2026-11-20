# Fundación F2 · medición de concurrencia real en SQLite (no es una prueba de pytest: se ejecuta a mano).
#
#   python tests/medir_concurrencia_f2.py <carpeta-temporal> [--rondas 3]
#
# Crea bases nuevas en la carpeta dada (nunca la base real) y mide, en modo de diario 'delete' (el de hoy) y 'wal':
#   A) escritores concurrentes: hilos y procesos que hacen el patrón de la app (BEGIN IMMEDIATE, leer versión,
#      UPDATE ... WHERE version = ?, INSERT en auditoría, COMMIT) mientras otros hilos leen;
#   B) una transacción larga de escritura (3 s) mientras otros leen y escriben;
#   C) una caída a mitad de transacción (proceso matado con la transacción abierta).
# Con espera de 15 s (la de get_connection) y con 0.1 s, para ver qué pasa si no se espera.
# Imprime una tabla de latencias (p50/p95/máx en ms), errores «database is locked» y comprobaciones de integridad.
import argparse
import json
import multiprocessing as mp
import os
import sqlite3
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY, version INTEGER NOT NULL, contador INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER, version INTEGER,
                                      quien TEXT, detalle TEXT);
"""


def nueva_base(ruta: Path, modo: str, filas: int = 20) -> None:
    for sufijo in ("", "-wal", "-shm", "-journal"):
        Path(str(ruta) + sufijo).unlink(missing_ok=True)
    c = sqlite3.connect(ruta)
    c.execute(f"PRAGMA journal_mode = {modo}")
    c.executescript(ESQUEMA)
    c.executemany("INSERT INTO pedidos (id, version, contador) VALUES (?, 1, 0)", [(i,) for i in range(1, filas + 1)])
    c.commit()
    c.close()


def conectar(ruta: Path, espera: float) -> sqlite3.Connection:
    c = sqlite3.connect(ruta, timeout=espera, isolation_level=None, check_same_thread=False)
    c.execute("PRAGMA foreign_keys = ON")
    return c


def escribir_una(c: sqlite3.Connection, pedido_id: int, quien: str) -> str:
    """Patrón de la app: devuelve 'ok', 'conflicto' (409) o 'bloqueada' (database is locked)."""
    try:
        c.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc) or "busy" in str(exc):
            return "bloqueada"
        raise
    try:
        v = c.execute("SELECT version FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()[0]
        cur = c.execute("UPDATE pedidos SET version = version + 1, contador = contador + 1 WHERE id = ? AND version = ?",
                        (pedido_id, v))
        if cur.rowcount == 0:
            c.execute("ROLLBACK")
            return "conflicto"
        c.execute("INSERT INTO auditoria (pedido_id, version, quien, detalle) VALUES (?, ?, ?, ?)",
                  (pedido_id, v + 1, quien, "x" * 200))
        c.execute("COMMIT")
        return "ok"
    except sqlite3.OperationalError as exc:
        if c.in_transaction:
            c.execute("ROLLBACK")
        if "locked" in str(exc) or "busy" in str(exc):
            return "bloqueada"
        raise


def _percentiles(ms):
    if not ms:
        return {"p50": None, "p95": None, "max": None}
    s = sorted(ms)
    return {"p50": round(statistics.median(s), 1), "p95": round(s[min(len(s) - 1, int(len(s) * 0.95))], 1),
            "max": round(s[-1], 1)}


def _escritor_hilo(ruta, espera, n, quien, salida, filas):
    c = conectar(ruta, espera)
    for i in range(n):
        t0 = time.perf_counter()
        r = escribir_una(c, 1 + (i % filas), quien)
        salida.append((r, (time.perf_counter() - t0) * 1000))
    c.close()


def _lector_hilo(ruta, espera, parar, salida):
    c = conectar(ruta, espera)
    while not parar.is_set():
        t0 = time.perf_counter()
        try:
            c.execute("SELECT COUNT(*), SUM(contador) FROM pedidos").fetchone()
            c.execute("SELECT * FROM auditoria ORDER BY id DESC LIMIT 20").fetchall()
            salida.append(("ok", (time.perf_counter() - t0) * 1000))
        except sqlite3.OperationalError as exc:
            salida.append(("bloqueada" if "locked" in str(exc) else str(exc), (time.perf_counter() - t0) * 1000))
        time.sleep(0.002)
    c.close()


def _escritor_proceso(ruta, espera, n, quien, cola, filas):
    salida = []
    _escritor_hilo(Path(ruta), espera, n, quien, salida, filas)
    cola.put(salida)


def _comprobar(ruta: Path) -> dict:
    c = sqlite3.connect(ruta)
    try:
        suma = c.execute("SELECT SUM(contador), SUM(version) - COUNT(*) FROM pedidos").fetchone()
        auditadas = c.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
        return {"integridad": c.execute("PRAGMA integrity_check").fetchone()[0], "cambios": suma[0],
                "versiones": suma[1], "auditadas": auditadas}
    finally:
        c.close()


def medir_escritores(carpeta: Path, modo: str, espera: float, hilos=4, procesos=4, por_escritor=60, lectores=3,
                     filas=5) -> dict:
    ruta = carpeta / f"conc-{modo}-{espera}.db"
    nueva_base(ruta, modo, filas)
    escrituras, lecturas, parar = [], [], threading.Event()
    ls = [threading.Thread(target=_lector_hilo, args=(ruta, espera, parar, lecturas)) for _ in range(lectores)]
    for t in ls:
        t.start()
    cola = mp.Queue()
    ps = [mp.Process(target=_escritor_proceso, args=(str(ruta), espera, por_escritor, f"proc{i}", cola, filas))
          for i in range(procesos)]
    hs = [threading.Thread(target=_escritor_hilo, args=(ruta, espera, por_escritor, f"hilo{i}", escrituras, filas))
          for i in range(hilos)]
    t0 = time.perf_counter()
    for p in ps:
        p.start()
    for h in hs:
        h.start()
    for h in hs:
        h.join()
    for _ in ps:
        escrituras.extend(cola.get())
    for p in ps:
        p.join()
    total = time.perf_counter() - t0
    parar.set()
    for t in ls:
        t.join()
    ok = [ms for r, ms in escrituras if r == "ok"]
    res = {"modo": modo, "espera_s": espera, "escritores": f"{hilos} hilos + {procesos} procesos",
           "intentos": len(escrituras), "ok": len(ok),
           "bloqueadas": sum(1 for r, _ in escrituras if r == "bloqueada"),
           "conflictos_409": sum(1 for r, _ in escrituras if r == "conflicto"),
           "escritura_ms": _percentiles(ok), "lecturas": len(lecturas),
           "lecturas_bloqueadas": sum(1 for r, _ in lecturas if r != "ok"),
           "lectura_ms": _percentiles([ms for r, ms in lecturas if r == "ok"]),
           "escrituras_por_s": round(len(ok) / total, 1), **_comprobar(ruta)}
    # Ninguna escritura confirmada se perdió y cada una tiene su fila de auditoría
    res["sin_perdidas"] = res["cambios"] == res["ok"] == res["versiones"] == res["auditadas"]
    return res


def medir_transaccion_larga(carpeta: Path, modo: str, espera: float, dura=3.0) -> dict:
    """Un escritor abre BEGIN IMMEDIATE y lo mantiene `dura` s; mientras, 2 lectores y 2 escritores trabajan."""
    ruta = carpeta / f"larga-{modo}-{espera}.db"
    nueva_base(ruta, modo)
    listo = threading.Event()

    def larga():
        c = conectar(ruta, 15)
        c.execute("BEGIN IMMEDIATE")
        c.execute("UPDATE pedidos SET contador = contador + 1, version = version + 1 WHERE id = 1")
        c.execute("INSERT INTO auditoria (pedido_id, version, quien, detalle) VALUES (1, 2, 'larga', 'x')")
        listo.set()
        time.sleep(dura)
        c.execute("COMMIT")
        c.close()

    escrituras, lecturas, parar = [], [], threading.Event()
    tl = threading.Thread(target=larga)
    tl.start()
    listo.wait()
    ls = [threading.Thread(target=_lector_hilo, args=(ruta, espera, parar, lecturas)) for _ in range(2)]
    ws = [threading.Thread(target=_escritor_hilo, args=(ruta, espera, 3, f"w{i}", escrituras, 20)) for i in range(2)]
    for t in ls + ws:
        t.start()
    for t in ws:
        t.join()
    tl.join()
    parar.set()
    for t in ls:
        t.join()
    ok = [ms for r, ms in escrituras if r == "ok"]
    return {"modo": modo, "espera_s": espera, "duracion_larga_s": dura, "escrituras_ok": len(ok),
            "escrituras_bloqueadas": sum(1 for r, _ in escrituras if r == "bloqueada"),
            "espera_escritura_ms": _percentiles(ok), "lecturas": len(lecturas),
            "lecturas_bloqueadas": sum(1 for r, _ in lecturas if r != "ok"),
            "lectura_ms": _percentiles([ms for r, ms in lecturas if r == "ok"]), **_comprobar(ruta)}


_HIJO_QUE_CAE = r"""
import os, sqlite3, sys
c = sqlite3.connect(sys.argv[1], isolation_level=None)
c.execute("BEGIN IMMEDIATE")
for i in range(500):
    c.execute("UPDATE pedidos SET contador = contador + 1, version = version + 1 WHERE id = ?", (1 + i % 20,))
    c.execute("INSERT INTO auditoria (pedido_id, version, quien, detalle) VALUES (?, 0, 'caida', ?)", (i, 'x' * 2000))
print("DENTRO", flush=True)
sys.stdin.readline()      # el padre lo mata aquí, con la transacción abierta y escrita a medias
"""


def medir_caida(carpeta: Path, modo: str) -> dict:
    ruta = carpeta / f"caida-{modo}.db"
    nueva_base(ruta, modo)
    antes = _comprobar(ruta)
    p = subprocess.Popen([sys.executable, "-c", _HIJO_QUE_CAE, str(ruta)], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "DENTRO"
    diarios = sorted(x.name.replace(ruta.name, "") for x in carpeta.glob(ruta.name + "-*"))
    p.kill()
    p.wait()
    t0 = time.perf_counter()
    c = conectar(ruta, 15)
    r = escribir_una(c, 1, "despues")        # la primera escritura tras la caída deshace el diario caliente
    recuperacion_ms = round((time.perf_counter() - t0) * 1000, 1)
    c.close()
    despues = _comprobar(ruta)
    return {"modo": modo, "diarios_durante": diarios, "escritura_tras_caida": r, "recuperacion_ms": recuperacion_ms,
            "integridad": despues["integridad"], "filas_caida_visibles":
                sqlite3.connect(ruta).execute("SELECT COUNT(*) FROM auditoria WHERE quien = 'caida'").fetchone()[0],
            "cambios_antes": antes["cambios"], "cambios_despues": despues["cambios"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--rondas", type=int, default=3)
    a = ap.parse_args()
    carpeta = Path(a.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    resultados = {"sqlite": sqlite3.sqlite_version, "python": sys.version.split()[0], "carpeta": str(carpeta),
                  "escritores": [], "larga": [], "caida": []}
    for modo in ("delete", "wal"):
        for espera in (15.0, 0.1):
            for _ in range(a.rondas):
                resultados["escritores"].append(medir_escritores(carpeta, modo, espera))
            resultados["larga"].append(medir_transaccion_larga(carpeta, modo, espera))
        resultados["caida"].append(medir_caida(carpeta, modo))
    print(json.dumps(resultados, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
