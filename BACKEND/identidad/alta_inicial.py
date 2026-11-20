# backend/identidad/alta_inicial.py
# Fundación F2: alta inicial LOCAL de usuarios (contrato §4.1). No hay usuario ni contraseña en el repositorio: la
# persona los escribe aquí, en su PC, y la contraseña se pide con getpass (no se ve ni queda en el historial).
#
#   cd BACKEND
#   py -3.14 -m identidad.alta_inicial                       # crear un usuario y darle obras
#   py -3.14 -m identidad.alta_inicial --contrasena <usuario> # cambiar la contraseña (cierra sus sesiones)
#
# Usa la misma base que el servidor (CATDIC_DB_PATH o la de siempre) y deja todo en la auditoría.
import argparse
import getpass
import json
import sys
from datetime import datetime

import database
from identidad import contrasenas, sesiones
from migracion_fundacion import FUNCIONES_OBRA


def _si(pregunta: str, defecto: bool = False) -> bool:
    r = input(f"{pregunta} [{'S/n' if defecto else 's/N'}]: ").strip().lower()
    return defecto if not r else r in ("s", "si", "sí", "y")


def _pedir_contrasena() -> str:
    while True:
        una = getpass.getpass("Contraseña (mínimo 10 caracteres): ")
        try:
            contrasenas.validar_nueva(una)
        except contrasenas.ContrasenaInvalida as exc:
            print(f"  {exc}")
            continue
        if getpass.getpass("Repite la contraseña: ") != una:
            print("  No coinciden; vuelve a escribirla.")
            continue
        return una


def _transaccion():
    conn = database.get_connection()
    conn.isolation_level = None
    conn.execute("BEGIN IMMEDIATE")
    return conn


def crear() -> int:
    login = input("Usuario (3–40: minúsculas, números, punto, guion): ").strip()
    nombre = input("Nombre visible: ").strip()
    contrasena = _pedir_contrasena()
    es_admin = _si("¿Administrador global (usuarios y configuración; NO da acceso técnico a obras)?")
    conn = database.get_connection()
    try:
        obras = [dict(f) for f in conn.execute("SELECT id, nombre FROM proyectos ORDER BY nombre")]
    finally:
        conn.close()
    elegidas = {}
    if obras:
        print("\nObras existentes:")
        for i, o in enumerate(obras, 1):
            print(f"  {i}. {o['nombre']} ({o['id']})")
        print(f"Funciones: {', '.join(FUNCIONES_OBRA)}")
        for i, o in enumerate(obras, 1):
            texto = input(f"Funciones en «{o['nombre']}» (separadas por coma; vacío = ninguna): ").strip()
            funciones = sorted({f.strip() for f in texto.split(",") if f.strip()})
            malas = [f for f in funciones if f not in FUNCIONES_OBRA]
            if malas:
                print(f"  Se ignoran funciones que no existen: {', '.join(malas)}")
                funciones = [f for f in funciones if f in FUNCIONES_OBRA]
            if funciones:
                elegidas[o["id"]] = funciones
    conn = _transaccion()
    try:
        u = sesiones.crear_usuario(conn, login, nombre, contrasena, es_admin, None)
        ahora = datetime.now().isoformat()
        for obra_id, funciones in elegidas.items():
            conn.execute("""INSERT INTO membresias (usuario_id, obra_id, funciones, version, creada, actualizada)
                            VALUES (?, ?, ?, 1, ?, ?)""", (u["id"], obra_id, json.dumps(funciones), ahora, ahora))
            conn.execute("""INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                            VALUES (?, 'local', 'MEMBRESIAS', 'ASIGNAR', ?, ?)""",
                         (ahora, f"{obra_id}:{u['id']}", json.dumps({"funciones": funciones, "motivo": "alta inicial"},
                                                                     ensure_ascii=False)))
        conn.execute("COMMIT")
    except sesiones.ErrorUsuarios as exc:
        conn.execute("ROLLBACK")
        print(f"No se creó: {exc}")
        return 1
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    print(f"\nUsuario «{u['usuario']}» creado{' (administrador global)' if es_admin else ''}.")
    for obra_id, funciones in elegidas.items():
        print(f"  {obra_id}: {', '.join(funciones)}")
    return 0


def cambiar_contrasena(login: str) -> int:
    login = sesiones.normalizar_login(login)
    contrasena = _pedir_contrasena()
    conn = _transaccion()
    try:
        f = conn.execute("SELECT id FROM usuarios WHERE usuario = ?", (login,)).fetchone()
        if f is None:
            conn.execute("ROLLBACK")
            print("Ese usuario no existe.")
            return 1
        conn.execute("UPDATE usuarios SET hash_contrasena = ?, version = version + 1, actualizado = ? WHERE id = ?",
                     (contrasenas.generar_hash(contrasena), datetime.now().isoformat(), f["id"]))
        n = sesiones.cerrar_todas(conn, f["id"], "contrasena_cambiada")
        conn.execute("""INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json)
                        VALUES (?, 'local', 'SESION', 'CAMBIAR_CONTRASENA', ?, ?)""",
                     (datetime.now().isoformat(), str(f["id"]), json.dumps({"sesiones_cerradas": n})))
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    print(f"Contraseña cambiada; se cerraron {n} sesiones abiertas.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Alta inicial local de usuarios de CATDIC-WEB.")
    ap.add_argument("--contrasena", metavar="USUARIO", help="cambiar la contraseña de un usuario existente")
    a = ap.parse_args(argv)
    database.inicializar_bd()          # crea o migra la base si hace falta (con su respaldo)
    return cambiar_contrasena(a.contrasena) if a.contrasena else crear()


if __name__ == "__main__":
    sys.exit(main())
