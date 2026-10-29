# BACKEND/tests/test_obras.py
# Etapa 2 · T4n — "Nueva obra": POST /api/proyectos, POST /api/proyectos/{id}/planos, datos del usuario
# (PLANES/etapa-2.md, T4n; CLAUDE.md §1.5, Regla de Oro #1).
# Todo # SINTÉTICO: los PDF se generan aquí con PyMuPDF; BD, carpeta de datos y Dropbox son temporales.
import hashlib
import io
import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

import config
import database
import main
import obras
from reglas_ingenieria import PENDIENTE


def _pdf(paginas=2, texto="SINTETICO") -> bytes:
    doc = pymupdf.open()
    for i in range(paginas):
        doc.new_page(width=300, height=200).insert_text((20, 50), f"{texto} {i + 1}", fontsize=12)
    datos = doc.tobytes()
    doc.close()
    return datos


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    (tmp_path / "bd").mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "prueba.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(config.ENV_DATOS_RAIZ, str(tmp_path / "datos"))
    database.inicializar_bd()
    with TestClient(main.app) as c:   # el arranque siembra los 3 proyectos
        yield c, tmp_path


def _nueva_obra(c, **extra):
    datos = {"nombre": "Obra Sintetica", "no_licencia": "LIC-SINT", "no_solicitud": "SOL-SINT",
             "residente_obra": "RESIDENTE SINT", "direccion_obra": "CALLE SINTETICA 1", "provincia": "PROV SINT",
             "sector": "SECTOR SINT", "inicio_obra": "01/03/2026", **extra}
    r = c.post("/api/proyectos", json=datos)
    assert r.status_code == 201, r.text
    return r.json()["proyecto"]


def _subir(c, pid, vectorial=None, sellado=None, certifico="true", **form):
    archivos = {"vectorial": ("vec.pdf", vectorial if vectorial is not None else _pdf(3), "application/pdf"),
                "sellado": ("sel.pdf", sellado if sellado is not None else _pdf(2), "application/pdf")}
    return c.post(f"/api/proyectos/{pid}/planos", files=archivos, data={"certifico": certifico, **form})


def _bd(sql, *args):
    conn = database.get_connection()
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


# ---------- Crear la obra ----------

def test_crear_obra_con_datos_generales_y_auditoria(entorno):
    c, _ = entorno
    p = _nueva_obra(c)
    assert p["id"] == "obra-sintetica" and p["tipo"] == "Supervisión" and p["inicio_obra"] == "01/03/2026"
    for campo, valor in (("no_licencia", "LIC-SINT"), ("no_solicitud", "SOL-SINT"), ("residente_obra", "RESIDENTE SINT"),
                         ("direccion_obra", "CALLE SINTETICA 1"), ("provincia", "PROV SINT"), ("sector", "SECTOR SINT")):
        assert p[campo] == valor
    a = _bd("SELECT usuario, modulo, accion, entidad_id, detalle_json FROM auditoria WHERE accion = 'CREAR_PROYECTO'")
    assert len(a) == 1 and a[0]["entidad_id"] == "obra-sintetica" and a[0]["usuario"]
    assert json.loads(a[0]["detalle_json"])["no_licencia"] == "LIC-SINT"


def test_obra_con_el_mismo_nombre_recibe_otro_id_y_no_pisa_la_anterior(entorno):
    c, _ = entorno
    a, b = _nueva_obra(c), _nueva_obra(c)
    assert a["id"] == "obra-sintetica" and b["id"] == "obra-sintetica-2"


@pytest.mark.parametrize("cambio,texto", [({"nombre": "  "}, "nombre"), ({"inicio_obra": "2026-03-01"}, "DD/MM/AAAA"),
                                           ({"inicio_obra": "31/02/2026"}, "DD/MM/AAAA"), ({"tipo": "Otro"}, "tipo")])
def test_datos_invalidos_no_crean_la_obra(entorno, cambio, texto):
    c, _ = entorno
    antes = len(_bd("SELECT id FROM proyectos"))
    r = c.post("/api/proyectos", json={"nombre": "X", **cambio})
    assert r.status_code == 422 and texto in r.json()["detail"]
    assert len(_bd("SELECT id FROM proyectos")) == antes


def test_los_campos_vacios_quedan_vacios_no_inventados(entorno):
    c, _ = entorno
    r = c.post("/api/proyectos", json={"nombre": "Solo Nombre"})
    p = r.json()["proyecto"]
    assert r.status_code == 201 and p["no_licencia"] == "" and p["inicio_obra"] == "" and p["residente_obra"] == ""


# ---------- Subir los planos ----------

def test_subida_guarda_los_dos_archivos_con_sha256_y_certificacion_auditada(entorno):
    c, tmp = entorno
    p = _nueva_obra(c)
    vec, sel = _pdf(3, "VEC"), _pdf(2, "SEL")
    r = _subir(c, p["id"], vec, sel, etiqueta_revision="Rev. sintetica", fecha_plano="10/03/2026", notas="n")
    assert r.status_code == 201, r.text
    pl = r.json()["plano"]
    assert pl["revision"] == 1 and pl["estado"] == "vigente" and pl["fecha_plano"] == "10/03/2026"
    assert pl["vectorial_sha256"] == hashlib.sha256(vec).hexdigest() and pl["sellado_sha256"] == hashlib.sha256(sel).hexdigest()
    assert (pl["vectorial_paginas"], pl["sellado_paginas"]) == (3, 2)
    assert Path(pl["vectorial_ruta"]).read_bytes() == vec and Path(pl["sellado_ruta"]).read_bytes() == sel
    assert Path(pl["vectorial_ruta"]).is_relative_to(tmp / "datos" / "obra-sintetica" / "planos")
    assert pl["certificado_por"] and pl["certificado_en"] and "corresponde a la versión sellada" in pl["certificacion_texto"]
    a = _bd("SELECT usuario, detalle_json FROM auditoria WHERE accion = 'SUBIR_PLANOS'")
    d = json.loads(a[0]["detalle_json"])
    assert a[0]["usuario"] == pl["certificado_por"] and d["certificado_en"] == pl["certificado_en"]
    assert d["vectorial"]["sha256"] == pl["vectorial_sha256"] and d["certificacion"].startswith("Certifico")


@pytest.mark.parametrize("certifico", ["false", "", "no"])
def test_sin_la_casilla_de_certificacion_no_se_guarda_nada(entorno, certifico):
    c, tmp = entorno
    p = _nueva_obra(c)
    r = _subir(c, p["id"], certifico=certifico)
    assert r.status_code == 422 and "Certifico" in r.json()["detail"]
    assert _bd("SELECT id FROM planos") == [] and not (tmp / "datos").exists()


def test_hacen_falta_los_dos_archivos(entorno):
    c, _ = entorno
    p = _nueva_obra(c)
    r = c.post(f"/api/proyectos/{p['id']}/planos", files={"vectorial": ("v.pdf", _pdf(), "application/pdf")},
               data={"certifico": "true"})
    assert r.status_code == 422                      # falta el sellado: FastAPI lo exige
    assert _bd("SELECT id FROM planos") == []


@pytest.mark.parametrize("vec,sel,texto", [
    (b"no soy un pdf", None, "vectorial"), (None, b"%PDF-1.4 roto", "sellado"), (b"", None, "vacío")])
def test_archivos_que_no_son_pdf_legible_se_rechazan_sin_dejar_restos(entorno, vec, sel, texto):
    c, tmp = entorno
    p = _nueva_obra(c)
    r = _subir(c, p["id"], vec, sel)
    assert r.status_code == 422 and texto in r.json()["detail"]
    assert _bd("SELECT id FROM planos") == []
    restos = [f for f in (tmp / "datos").rglob("*") if f.is_file()] if (tmp / "datos").exists() else []
    assert restos == []


def test_fecha_del_plano_invalida_y_obra_inexistente(entorno):
    c, _ = entorno
    p = _nueva_obra(c)
    assert _subir(c, p["id"], fecha_plano="2026-03-10").status_code == 422
    assert _subir(c, "no-existe").status_code == 404


def test_la_subida_deja_las_dudas_bloqueantes_de_lo_que_el_plano_no_da(entorno):
    c, _ = entorno
    p = _nueva_obra(c)
    r = _subir(c, p["id"])
    assert set(r.json()["plano"]["dudas_creadas"]) == {"emparejamiento_hojas", "equivalencias_en_nivel", "losas_tipo"}
    d = _bd("SELECT categoria, campo_afectado, descripcion_pregunta, resuelta, visita_id FROM dudas_y_hallazgos "
            "WHERE proyecto_id = ?", p["id"])
    assert {x["campo_afectado"] for x in d} == {"emparejamiento_hojas", "equivalencias_en_nivel", "losas_tipo"}
    assert all(x["categoria"] == "DUDA_BLOQUEANTE" and x["resuelta"] == 0 and x["visita_id"] is None for x in d)
    assert any("3 hojas" in x["descripcion_pregunta"] and "2" in x["descripcion_pregunta"] for x in d)
    # una segunda subida no duplica las dudas abiertas
    _subir(c, p["id"])
    assert len(_bd("SELECT id FROM dudas_y_hallazgos WHERE proyecto_id = ?", p["id"])) == 3


# ---------- Cambiar el plano ----------

def test_cambiar_el_plano_deja_el_nuevo_vigente_el_anterior_historico_y_marca_los_elementos(entorno):
    c, tmp = entorno
    p = _nueva_obra(c)
    pid = p["id"]
    primero = _subir(c, pid, _pdf(3, "V1"), _pdf(2, "S1")).json()["plano"]
    conn = database.get_connection()
    for i, plano in enumerate((primero["id"], None)):    # un elemento del plano 1 y otro sin plano registrado
        conn.execute("""INSERT INTO elementos_diseno (uid, proyecto_id, id_elemento, tipo_elemento, nivel_rango, ejes,
                        hoja_plano_origen, archivo_plano_origen, datos_diseno_json, estado_campos_json, actualizado, plano_id)
                        VALUES (?, ?, ?, 'COLUMNA RECTANGULAR', 'S-1', ?, '01', 'vec.pdf', '{}', '{}', 'x', ?)""",
                     (f"u{i}", pid, f"C{i}", f"EJE A-{i}", plano))
    conn.commit()
    conn.close()
    segundo = _subir(c, pid, _pdf(3, "V2"), _pdf(2, "S2")).json()["plano"]
    assert segundo["revision"] == 2 and segundo["elementos_marcados"] == 2
    estados = {r["revision"]: r["estado"] for r in _bd("SELECT revision, estado FROM planos WHERE proyecto_id = ?", pid)}
    assert estados == {1: "historico", 2: "vigente"}
    assert {r["revisar_motivo"] for r in _bd("SELECT revisar_motivo FROM elementos_diseno WHERE proyecto_id = ?", pid)} == {
        "plano cambiado: revisar"}
    assert _bd("SELECT accion FROM auditoria WHERE accion = 'CAMBIAR_PLANO'")
    # los archivos del plano anterior siguen intactos y los nuevos van a otra carpeta
    assert Path(primero["vectorial_ruta"]).exists() and Path(segundo["vectorial_ruta"]).exists()
    assert Path(primero["vectorial_ruta"]).parent != Path(segundo["vectorial_ruta"]).parent
    assert [x["revision"] for x in c.get(f"/api/proyectos/{pid}/planos").json()["planos"]] == [2, 1]


def test_la_primera_subida_no_marca_elementos_para_revisar(entorno):
    c, _ = entorno
    p = _nueva_obra(c)
    assert _subir(c, p["id"]).json()["plano"]["elementos_marcados"] == 0


def test_un_nombre_repetido_nunca_sobrescribe_el_archivo(entorno, monkeypatch):
    c, _ = entorno
    p = _nueva_obra(c)
    primero = _subir(c, p["id"], _pdf(2, "UNO"), _pdf(2, "UNO-S")).json()["plano"]
    contenido = Path(primero["vectorial_ruta"]).read_bytes()
    # Se fuerza la misma carpeta de revisión: el archivo existente se conserva y el nuevo recibe " v2"
    destino = Path(primero["vectorial_ruta"]).parent
    nuevo = destino.parent / "temporal.pdf"
    nuevo.write_bytes(_pdf(2, "DOS"))
    ruta = obras._mover_sin_sobrescribir(nuevo, destino, Path(primero["vectorial_ruta"]).name)
    assert ruta.name.endswith(" v2.pdf") and Path(primero["vectorial_ruta"]).read_bytes() == contenido


def test_si_la_base_falla_no_quedan_archivos_ni_filas(entorno, monkeypatch):
    c, tmp = entorno
    p = _nueva_obra(c)

    def falla(*a, **k):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(obras, "_asegurar_duda", falla)
    with pytest.raises(RuntimeError):
        obras.guardar_planos(p["id"], _Subida("v.pdf", _pdf()), _Subida("s.pdf", _pdf()), True)
    assert _bd("SELECT id FROM planos") == []
    assert [f for f in (tmp / "datos").rglob("*") if f.is_file()] == []


class _Subida:
    def __init__(self, nombre, datos):
        self.filename, self.file = nombre, io.BytesIO(datos)


# ---------- Carpeta de datos ----------

def test_la_carpeta_de_datos_no_puede_estar_en_dropbox_ni_en_el_repo(entorno, monkeypatch):
    c, tmp = entorno
    p = _nueva_obra(c)
    repo = Path(config.__file__).resolve().parent.parent
    for malo in (tmp / "dropbox" / "CATDIC-DATOS", repo / "FABRICA" / "datos", tmp / "Mi Dropbox Cliente" / "datos"):
        monkeypatch.setenv(config.ENV_DATOS_RAIZ, str(malo))
        r = _subir(c, p["id"])
        assert r.status_code == 409 and ("Dropbox" in r.json()["detail"] or "repositorio" in r.json()["detail"]), malo
        assert _bd("SELECT id FROM planos") == []
        assert not malo.exists()                                   # no se creó nada allí


def test_por_defecto_la_carpeta_es_catdic_datos_en_la_carpeta_del_usuario(monkeypatch):
    monkeypatch.delenv(config.ENV_DATOS_RAIZ, raising=False)
    assert config.obtener_datos_raiz() == (Path.home() / "CATDIC-DATOS").resolve()


# ---------- Datos que escribe el usuario ----------

def _guardar(c, pid, tipo, items, completo=False):
    return c.put(f"/api/proyectos/{pid}/datos-obra", json={"tipo": tipo, "items": items, "completo": completo})


def test_equivalencias_y_losas_quedan_confirmadas_con_auditoria_y_cierran_su_duda(entorno):
    c, _ = entorno
    pid = _nueva_obra(c)["id"]
    _subir(c, pid)
    r = _guardar(c, pid, "equivalencia_nivel", [{"clave": "e-1", "valor": "SOTANO S7"}, {"clave": "E-2", "valor": "SOTANO S6"}])
    assert r.status_code == 200 and r.json()["guardados"] == 2 and r.json()["dudas_cerradas"] == 0
    datos = c.get(f"/api/proyectos/{pid}/datos-obra").json()
    assert {(d["clave"], d["valor"], d["estado"], d["fuente"]) for d in datos["datos"]["equivalencia_nivel"]} == {
        ("E-1", "SOTANO S7", "confirmado", "usuario"), ("E-2", "SOTANO S6", "confirmado", "usuario")}
    assert "equivalencias_en_nivel" in {d["campo_afectado"] for d in datos["dudas_abiertas"]}   # lo que falte sigue abierto
    r = _guardar(c, pid, "equivalencia_nivel", [{"clave": "E-1", "valor": "SOTANO S7 (corregido)"}], completo=True)
    assert r.json()["dudas_cerradas"] == 1
    a = _bd("SELECT detalle_json FROM auditoria WHERE accion = 'GUARDAR_DATOS_OBRA' ORDER BY id")
    ultimo = json.loads(a[-1]["detalle_json"])
    assert ultimo["datos"] == [{"clave": "E-1", "anterior": "SOTANO S7", "nuevo": "SOTANO S7 (corregido)"}] and ultimo["completo"]
    _guardar(c, pid, "losa_tipo", [{"clave": "l13", "valor": "a"}], completo=True)
    assert [d["valor"] for d in c.get(f"/api/proyectos/{pid}/datos-obra").json()["datos"]["losa_tipo"]] == ["A"]


@pytest.mark.parametrize("tipo,item,texto", [
    ("equivalencia_nivel", {"clave": "SOTANO", "valor": "x"}, "E-n"), ("losa_tipo", {"clave": "L1", "valor": "D"}, "A, B o C"),
    ("losa_tipo", {"clave": "X1", "valor": "A"}, "L#"), ("hoja_par", {"clave": "99", "valor": "1"}, "entre 1 y 3"),
    ("hoja_par", {"clave": "1", "valor": "9"}, "entre 1 y 2"), ("otro", {"clave": "a", "valor": "b"}, "tipo de dato"),
    ("equivalencia_nivel", {"clave": "E-1", "valor": ""}, "clave y valor")])
def test_datos_invalidos_no_se_guardan(entorno, tipo, item, texto):
    c, _ = entorno
    pid = _nueva_obra(c)["id"]
    _subir(c, pid)                                   # vectorial de 3 hojas, sellado de 2
    r = _guardar(c, pid, tipo, [item])
    assert r.status_code == 422 and texto in r.json()["detail"]
    assert _bd("SELECT id FROM obra_datos_usuario") == []


def test_emparejamiento_de_hojas_con_las_de_mas_y_sin_planos_no_se_puede(entorno):
    c, _ = entorno
    pid = _nueva_obra(c)["id"]
    assert _guardar(c, pid, "hoja_par", [{"clave": "1", "valor": "1"}]).status_code == 409   # sin planos
    _subir(c, pid)
    r = _guardar(c, pid, "hoja_par", [{"clave": "1", "valor": "1"}, {"clave": "2", "valor": "2"},
                                      {"clave": "3", "valor": "sin pareja"}], completo=True)
    assert r.status_code == 200 and r.json()["dudas_cerradas"] == 1
    assert {(d["clave"], d["valor"]) for d in c.get(f"/api/proyectos/{pid}/datos-obra").json()["datos"]["hoja_par"]} == {
        ("1", "1"), ("2", "2"), ("3", "sin pareja")}


# ---------- Tablero y migración ----------

def test_el_tablero_trae_el_resumen_del_plano_vigente(entorno):
    c, _ = entorno
    pid = _nueva_obra(c)["id"]
    assert pid not in c.get("/api/dashboard").json()["planos_vigentes"]
    _subir(c, pid, etiqueta_revision="Rev. S")
    v = c.get("/api/dashboard").json()["planos_vigentes"][pid]
    assert v["revision"] == 1 and v["etiqueta_revision"] == "Rev. S" and len(v["vectorial_sha256"]) == 12


def test_migracion_agrega_las_columnas_nuevas_con_respaldo_y_es_idempotente(tmp_path, monkeypatch):
    import sqlite3
    ruta = tmp_path / "vieja.db"
    monkeypatch.setenv(config.ENV_DB_PATH, str(ruta))
    conn = sqlite3.connect(ruta)
    conn.executescript("""
        CREATE TABLE proyectos (id TEXT PRIMARY KEY, nombre TEXT);
        CREATE TABLE elementos_diseno (uid TEXT PRIMARY KEY);
        CREATE TABLE auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_hora TEXT, usuario TEXT, modulo TEXT,
                                accion TEXT, entidad_id TEXT, detalle_json TEXT);
        INSERT INTO proyectos VALUES ('p', 'P'); INSERT INTO elementos_diseno VALUES ('e');
    """)
    conn.commit()
    conn.close()
    r = database.migrar_columnas_t4n()
    assert r["migrada"] and set(r["columnas_nuevas"]) == {"proyectos", "elementos_diseno"}
    assert Path(r["respaldo"]).exists()
    conn = sqlite3.connect(ruta)
    assert "inicio_obra" in {x[1] for x in conn.execute("PRAGMA table_info(proyectos)")}
    assert conn.execute("SELECT COUNT(*) FROM proyectos").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM auditoria WHERE accion = 'MIGRACION_COLUMNAS_T4N'").fetchone()[0] == 1
    conn.close()
    assert database.migrar_columnas_t4n()["migrada"] is False
