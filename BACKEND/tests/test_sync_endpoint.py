# BACKEND/tests/test_sync_endpoint.py
# Etapa 1 · T5 — POST /api/dropbox/sync (PLANES/etapa-1.md: T5, P1, P3, P4; CLAUDE.md
# Regla de Oro #1, §1.3, §1.5, §5.1, §5.2).
# Etapa 1 · T8 — P3 estricta, origen_datos_json y corrección única de las Procesada (B1, B2).
#
# BD temporal (CATDIC_DB_PATH) y Dropbox falso (CATDIC_DROPBOX_RAIZ -> tmp_path).
# Convención de datos:
#   - "# REAL: ..."      -> nombre copiado literalmente de Dropbox (listado en solo lectura
#                           el 21/10/2026). Solo se usan los nombres; el contenido es falso.
#   - "# SINTÉTICO: ..." -> dato inventado solo para probar la regla; no es dato de proyecto.
import json
import os
import shutil
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import config
import main
from reglas_ingenieria import PENDIENTE
from sync.escaner_dropbox import (
    LAYOUT_NO_SOPORTADO,
    LAYOUT_SUPERVISION,
    SUBRUTA_INFORMES_PROCESADOS,
    SUBRUTA_PLANOS_SELLADOS,
    SUBRUTA_VISITAS,
)
from sync.sincronizador import evaluar_p3, stp_de_fecha

CONTENIDO_FALSO = b"%PDF-1.4 contenido sintetico de prueba\n"  # SINTÉTICO

# REAL: …\TERRA LIVING\LEVANTAMIENTO\VISITA A OBRA\<carpeta>\<PDFs>
VISITAS_TERRA_LIVING = {
    "1. FONDO DE SEPTICO": ["1. Platea.pdf"],
    "1. FUNDACIONES PARCIAL": ["2. Zapata.pdf"],
    "10 - LOSA S-6 COMPLETIVO": ["LOSAS S-6.pdf", "Pórticos S-6 Completivo.pdf"],
    "11 - COLUMNAS S-5 31-07-2026": ["Verticales S-5 Parcial.pdf"],
    "12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026": ["Verticales parcial sótano -5.pdf"],
    "13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026": ["LOSAS S-5 PARCIAL.pdf"],
    "14. VERTICALES PARCIALES S-4 28-08-2026": ["S-4 verticales parcial.pdf"],
    "15 LOSAS Y PORTICOS S-5 COMPLETIVO 02-09-2026": ["Completivo Losa Sótano 5.pdf"],
    "16. VERTICALES PARCIAL S-4 11-09-2026": ["TERRA LIVING Verticales S-4.pdf"],
    "17. COMPLETIVO VERTICALES S-4 28-09-2026": ["VERTICALES S-4 COMPLETIVO.pdf"],
    "17.PARCIAL VERTICALES S-3 28-09-2026": ["VERTICALES S-3 PARCIAL.pdf"],
    "18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026": ["Losa y viga entrepiso 4 completivo (1).pdf"],
    "19. VERTICALES S-3 COMPLETIVO 09-10-2026": [],  # REAL: carpeta sin PDF
    "2. MURO DE SEPTICO": ["3. Muro séptico.pdf"],
    "20. LOSA SOTANO 3 PARCIAL 15-10-2026": ["Losa S-3 parcial.pdf"],
    "3. VERTICALES SOTANO -7": ["4. Verticales Fundacion.pdf"],
    "4. FUNDACIONES COMPLETIVO": ["5.  Platea 06.05.2026.pdf"],
    "5. VERTICALES SOTANO -6 PARCIAL": ["6.Verticales Sotano_1x1s.pdf"],
    "6. LOSA SEPTICO": ["7. Muros y sépticos.pdf"],
    "7. LOSA SOTANO -7": ["8. Planta estructural losa de piso (S7).pdf", "CORRECIONES LOSA S-7.pdf"],
    "8 - COLUMNAS S-6 COMPLETIVO": ["10.Columnas parcial S-6.pdf"],
    "9 - LOSA S-6 PARCIAL": ["CORRECCIONES SUPERVISION 23-07-2026.pdf", "PÓRTICOS Y LOSAS S-6 PARCIAL.pdf"],
}
PLANO_SELLADO_TERRA = "TERRA LIVING -ESTRUCTURALES.pdf"  # REAL
# REAL: …\TERRA LIVING\INFORMES\2.DATA PROCESADA\ (los 13 archivos del 21/10/2026)
INFORMES_TERRA = [
    "MIVED - TERRA LIVING-FUNDACIONES 09.05.2026.PDF",
    "MIVED - TERRA LIVING-FUNDACIONES y FONDO DE SEPTICO.pdf",
    "MIVED - TERRA LIVING-LOSA DE SEPTICO.PDF",
    "MIVED - TERRA LIVING-LOSAS Y PORTICOS SOTANO -5 v2.PDF",
    "MIVED - TERRA LIVING-LOSAS Y VIGAS PARCIAL SOTANO -3.PDF",
    "MIVED - TERRA LIVING-VIGAS SOTANO -7.pdf",
    "Terra Living - STP - Losa y Vigas Entrepiso 3 Sotano S3 Parcial - 15-10-2026.pdf",
    "Terra Living - STP - Losa y Vigas Entrepiso 4 Sotano S4 - 02-10-2026 v2.pdf",
    "Terra Living - STP - Losa y Vigas Entrepiso 5 Sotano S5 Completivo - 02-09-2026.pdf",
    "Terra Living - STP - Verticales Sotano S3 Parcial - 28-09-2026.pdf",
    "Terra Living - STP - Verticales Sotano S4 Completivo - 28-09-2026.pdf",
    "Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026.pdf",
    "Terra Living - STP - Verticales Sotano S4 Parcial - 28-08-2026.pdf",
]

# Estado esperado tras el primer sync con los nombres reales (reglas P1, P3 y T5)
ESTADOS_ESPERADOS = {
    "1. FONDO DE SEPTICO": "Con dudas",                    # sin fecha ni clase
    "1. FUNDACIONES PARCIAL": "Con dudas",                 # sin fecha
    "10 - LOSA S-6 COMPLETIVO": "Con dudas",               # sin fecha
    "11 - COLUMNAS S-5 31-07-2026": "Sin procesar",        # sin STP de esa fecha
    "12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026": "Sin procesar",
    "13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026": "Sin procesar",
    "14. VERTICALES PARCIALES S-4 28-08-2026": "Procesada",
    "15 LOSAS Y PORTICOS S-5 COMPLETIVO 02-09-2026": "Procesada",
    "16. VERTICALES PARCIAL S-4 11-09-2026": "Procesada",
    "17. COMPLETIVO VERTICALES S-4 28-09-2026": "Procesada",
    "17.PARCIAL VERTICALES S-3 28-09-2026": "Procesada",
    "18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026": "Con dudas",  # STP sin clase (P3 estricta)
    "19. VERTICALES S-3 COMPLETIVO 09-10-2026": "Con dudas",  # sin PDF
    "2. MURO DE SEPTICO": "Con dudas",
    "20. LOSA SOTANO 3 PARCIAL 15-10-2026": "Procesada",
    "3. VERTICALES SOTANO -7": "Con dudas",
    "4. FUNDACIONES COMPLETIVO": "Con dudas",              # fecha del PDF en otro formato
    "5. VERTICALES SOTANO -6 PARCIAL": "Con dudas",
    "6. LOSA SEPTICO": "Con dudas",
    "7. LOSA SOTANO -7": "Con dudas",
    "8 - COLUMNAS S-6 COMPLETIVO": "Con dudas",
    "9 - LOSA S-6 PARCIAL": "Sin procesar",                # fecha del PDF, sin STP de esa fecha
}


def _crear_terra_living(raiz: Path) -> Path:
    """Árbol falso con el layout §5.1 y los nombres reales de Terra Living."""
    proyecto = raiz / "SUPERVISION" / "EN CURSO" / "TERRA LIVING"
    planos = proyecto / SUBRUTA_PLANOS_SELLADOS
    planos.mkdir(parents=True)
    (planos / PLANO_SELLADO_TERRA).write_bytes(CONTENIDO_FALSO)
    visitas = proyecto / SUBRUTA_VISITAS
    for carpeta, pdfs in VISITAS_TERRA_LIVING.items():
        (visitas / carpeta).mkdir(parents=True)
        for pdf in pdfs:
            (visitas / carpeta / pdf).write_bytes(CONTENIDO_FALSO)
    informes = proyecto / SUBRUTA_INFORMES_PROCESADOS
    informes.mkdir(parents=True)
    for nombre in INFORMES_TERRA:
        (informes / nombre).write_bytes(CONTENIDO_FALSO)
    return proyecto


def _foto_arbol(raiz: Path):
    foto = {}
    for actual, dirs, archivos in os.walk(raiz):
        for nombre in dirs + archivos:
            ruta = Path(actual) / nombre
            st = ruta.stat()
            foto[str(ruta.relative_to(raiz))] = (ruta.is_dir(), st.st_size, st.st_mtime_ns)
    return foto


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """BD temporal + Dropbox falso de Terra Living; el startup de FastAPI siembra la BD."""
    carpeta_bd = tmp_path / "bd"
    carpeta_bd.mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(carpeta_bd / "catdic_test.db"))
    raiz = tmp_path / "dropbox"
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(raiz))
    terra = _crear_terra_living(raiz)
    with TestClient(main.app) as cliente:
        yield cliente, terra, raiz


def _bd():
    conn = sqlite3.connect(config.obtener_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _sync(cliente, proyecto_id="terra-living"):
    params = {"proyecto_id": proyecto_id} if proyecto_id else None
    r = cliente.post("/api/dropbox/sync", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _resumen(respuesta, proyecto_id="terra-living"):
    return next(p for p in respuesta["proyectos"] if p["id"] == proyecto_id)


def _visitas(conn, proyecto_id="terra-living"):
    return {f["nombre_carpeta"]: dict(f) for f in conn.execute(
        "SELECT * FROM visitas WHERE proyecto_id = ?", (proyecto_id,))}


def _dudas(conn):
    return [dict(f) for f in conn.execute("SELECT * FROM dudas_y_hallazgos ORDER BY id")]


def _n_auditoria_sync(conn, proyecto_id=None):
    sql = "SELECT COUNT(*) FROM auditoria WHERE modulo = 'SYNC' AND accion = 'SINCRONIZAR_DROPBOX'"
    if proyecto_id:
        return conn.execute(sql + " AND entidad_id = ?", (proyecto_id,)).fetchone()[0]
    return conn.execute(sql).fetchone()[0]


# =====================================================================
# CONTRATO Y PRIMER SYNC
# =====================================================================
def test_contrato_de_respuesta(entorno):
    cliente, _, _ = entorno
    resp = _sync(cliente)
    assert resp["status"] == "ok" and len(resp["proyectos"]) == 1
    p = _resumen(resp)
    for clave in ("id", "nombre", "layout", "visitas_nuevas", "actualizadas", "sin_cambios",
                  "con_dudas", "procesadas", "desaparecidas", "omitidas", "avisos"):
        assert clave in p
    assert p["nombre"] == "Terra Living" and p["layout"] == LAYOUT_SUPERVISION
    assert (p["visitas_nuevas"], p["actualizadas"], p["sin_cambios"]) == (22, 0, 0)
    assert p["con_dudas"] == 12 and p["procesadas"] == 6
    assert p["desaparecidas"] == [] and p["omitidas"] == []
    assert p["corregidas_p3"] == []  # BD nueva: nada que corregir


def test_404_si_el_proyecto_no_existe(entorno):
    cliente, _, _ = entorno
    r = cliente.post("/api/dropbox/sync", params={"proyecto_id": "no-existe"})  # SINTÉTICO
    assert r.status_code == 404


def test_primer_sync_estados_y_columnas(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)
    assert {k: x["estado"] for k, x in v.items()} == ESTADOS_ESPERADOS
    for nombre, fila in v.items():
        assert json.loads(fila["formatos_solicitados"]) == ["STP-MIVED"]  # P4
        assert Path(fila["ruta_carpeta"]) == terra / SUBRUTA_VISITAS / nombre
        archivos = json.loads(fila["archivos_json"])
        assert [a["nombre"] for a in archivos] == sorted(
            VISITAS_TERRA_LIVING[nombre], key=lambda n: (n.casefold(), n))
        assert fila["id"].startswith("terra-living-")
    # Valores leídos del nombre (T3) llegan tal cual
    v20 = v["20. LOSA SOTANO 3 PARCIAL 15-10-2026"]
    assert (v20["numero"], v20["fecha_visita"], v20["clase"]) == (20, "2026-10-15", "Parcial")
    assert v20["id"] == "terra-living-20-losa-sotano-3-parcial-15-10-2026"
    v12 = v["12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026"]
    assert v12["clase"] == "Mixta" and len(json.loads(v12["clase_detalle_json"])) == 2
    v3 = v["3. VERTICALES SOTANO -7"]
    assert v3["fecha_visita"] == PENDIENTE and v3["clase"] == PENDIENTE
    assert json.loads(v3["campos_pendientes_json"]) == ["fecha_visita", "clase"]


def test_visita_sin_fecha_con_dudas_y_duda_bloqueante(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)["3. VERTICALES SOTANO -7"]  # REAL: sin fecha
        dudas = [d for d in _dudas(conn) if d["visita_id"] == v["id"]]
    assert v["estado"] == "Con dudas" and v["fecha_visita"] == PENDIENTE
    bloqueantes = {d["campo_afectado"]: d for d in dudas if d["categoria"] == "DUDA_BLOQUEANTE"}
    assert set(bloqueantes) == {"fecha_visita", "clase"}
    assert "no trae fecha" in bloqueantes["fecha_visita"]["descripcion_pregunta"]
    assert bloqueantes["fecha_visita"]["resuelta"] == 0
    assert bloqueantes["fecha_visita"]["proyecto_id"] == "terra-living"


def test_visita_sin_pdf_con_dudas(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)["19. VERTICALES S-3 COMPLETIVO 09-10-2026"]  # REAL: sin PDF
        dudas = [d for d in _dudas(conn) if d["visita_id"] == v["id"]]
    assert v["estado"] == "Con dudas" and v["fecha_visita"] == "2026-10-09"
    assert [(d["categoria"], d["campo_afectado"]) for d in dudas] == [("DUDA_BLOQUEANTE", "archivos_json")]
    assert "no tiene PDF" in dudas[0]["descripcion_pregunta"]


def test_aviso_de_interpretacion_es_hallazgo_interno(entorno):
    """REAL #8: la carpeta dice COMPLETIVO y el PDF parcial -> HALLAZGO_INTERNO de clase."""
    cliente, _, _ = entorno
    _sync(cliente)
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)["8 - COLUMNAS S-6 COMPLETIVO"]
        hallazgos = [d for d in _dudas(conn)
                     if d["visita_id"] == v["id"] and d["categoria"] == "HALLAZGO_INTERNO"]
    assert v["clase"] == "Completivo"  # manda la carpeta
    assert len(hallazgos) == 1 and hallazgos[0]["campo_afectado"] == "clase"
    assert "10.Columnas parcial S-6.pdf" in hallazgos[0]["descripcion_pregunta"]


def test_fecha_nunca_sale_del_mtime(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)["1. FONDO DE SEPTICO"]  # REAL: sin fecha en carpeta ni PDF
    assert v["fecha_visita"] == PENDIENTE
    assert json.loads(v["archivos_json"])[0]["mtime"]  # el mtime existe, pero no se usa


# =====================================================================
# SEGUNDO SYNC: IDEMPOTENCIA Y NO PISAR
# =====================================================================
def test_segundo_sync_no_crea_ni_cambia_nada(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        antes = _visitas(conn)
        dudas_antes = _dudas(conn)
    p2 = _resumen(_sync(cliente))
    assert (p2["visitas_nuevas"], p2["actualizadas"], p2["sin_cambios"]) == (0, 0, 22)
    assert p2["con_dudas"] == 12 and p2["procesadas"] == 6
    assert p2["corregidas_p3"] == [] and p2["p3_confirmadas"] == []
    with _bd() as conn:
        despues = _visitas(conn)
        dudas_despues = _dudas(conn)
        assert conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0] == 22
    assert despues == antes  # ni estado, ni salida, ni 'actualizado'
    assert dudas_despues == dudas_antes  # dudas sin duplicar


def test_visita_en_revision_sigue_en_revision(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    nombre = "13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026"  # REAL
    with _bd() as conn:
        conn.execute("UPDATE visitas SET estado = 'En revisión', salida_json = ? WHERE nombre_carpeta = ?",
                     (json.dumps({"stp": ["x.pdf"]}), nombre))  # SINTÉTICO
    # Cambio en Dropbox: se quita su PDF (el estado igual no se toca)
    (terra / SUBRUTA_VISITAS / nombre / "LOSAS S-5 PARCIAL.pdf").unlink()
    p = _resumen(_sync(cliente))
    with _bd() as conn:
        v = _visitas(conn)[nombre]
        dudas = [d for d in _dudas(conn) if d["visita_id"] == v["id"]]
    assert v["estado"] == "En revisión"
    assert json.loads(v["salida_json"]) == {"stp": ["x.pdf"]}
    assert json.loads(v["archivos_json"]) == []  # lo leído sí se actualiza
    assert [d["campo_afectado"] for d in dudas] == ["archivos_json"]
    assert p["actualizadas"] == 1


def test_visita_procesada_no_cambia_aunque_cambie_dropbox(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    nombre = "20. LOSA SOTANO 3 PARCIAL 15-10-2026"  # REAL
    with _bd() as conn:
        antes = _visitas(conn)[nombre]
    informes = terra / SUBRUTA_INFORMES_PROCESADOS
    (informes / "Terra Living - STP - Losa Sotano S3 - 15-10-2026.pdf").write_bytes(CONTENIDO_FALSO)  # SINTÉTICO
    _sync(cliente)
    with _bd() as conn:
        despues = _visitas(conn)[nombre]
    assert despues["estado"] == "Procesada" and despues["salida_json"] == antes["salida_json"]


def test_duda_resuelta_no_se_pisa(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    nombre = "1. FONDO DE SEPTICO"  # REAL: sin fecha ni clase
    fecha_steven = "2026-03-10"  # SINTÉTICO: fecha "respondida por Steven" en la Mesa de Dudas
    with _bd() as conn:
        v = _visitas(conn)[nombre]
        conn.execute("""UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = ?
                        WHERE visita_id = ? AND campo_afectado = 'fecha_visita'""", (fecha_steven, v["id"]))
        conn.execute("UPDATE visitas SET fecha_visita = ? WHERE id = ?", (fecha_steven, v["id"]))
        n_dudas = conn.execute("SELECT COUNT(*) FROM dudas_y_hallazgos").fetchone()[0]
    _sync(cliente)
    with _bd() as conn:
        v2 = _visitas(conn)[nombre]
        dudas_fecha = conn.execute("""SELECT COUNT(*) FROM dudas_y_hallazgos
                                      WHERE visita_id = ? AND campo_afectado = 'fecha_visita'""",
                                   (v["id"],)).fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM dudas_y_hallazgos").fetchone()[0] == n_dudas
    assert v2["fecha_visita"] == fecha_steven
    assert dudas_fecha == 1
    assert json.loads(v2["campos_pendientes_json"]) == ["clase"]  # la clase sigue pendiente
    assert v2["clase"] == PENDIENTE
    assert v2["estado"] == "Con dudas"


def test_visita_desaparecida_no_se_borra(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    nombre = "6. LOSA SEPTICO"  # REAL
    shutil.rmtree(terra / SUBRUTA_VISITAS / nombre)
    p = _resumen(_sync(cliente))
    assert [d["nombre_carpeta"] for d in p["desaparecidas"]] == [nombre]
    with _bd() as conn:
        assert nombre in _visitas(conn)
    assert p["sin_cambios"] == 21


def test_visita_nueva_en_segundo_sync(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    nueva = terra / SUBRUTA_VISITAS / "21. VERTICALES S-2 PARCIAL 20-10-2026"  # SINTÉTICO
    nueva.mkdir()
    (nueva / "Verticales S-2 parcial.pdf").write_bytes(CONTENIDO_FALSO)  # SINTÉTICO
    p = _resumen(_sync(cliente))
    assert (p["visitas_nuevas"], p["sin_cambios"]) == (1, 22)
    with _bd() as conn:
        v = _visitas(conn)[nueva.name]
    assert v["estado"] == "Sin procesar" and v["numero"] == 21


# =====================================================================
# NÚMERO ILEGIBLE, IDS
# =====================================================================
def test_carpeta_sin_numero_se_omite(entorno):
    cliente, terra, _ = entorno
    sin_numero = terra / SUBRUTA_VISITAS / "VERTICALES S-2 PARCIAL 20-10-2026"  # SINTÉTICO
    sin_numero.mkdir()
    (sin_numero / "a.pdf").write_bytes(CONTENIDO_FALSO)  # SINTÉTICO
    p = _resumen(_sync(cliente))
    assert p["visitas_nuevas"] == 22
    assert [o["nombre_carpeta"] for o in p["omitidas"]] == [sin_numero.name]
    assert "número" in p["omitidas"][0]["motivo"]
    with _bd() as conn:
        assert sin_numero.name not in _visitas(conn)


def test_id_que_choca_lleva_sufijo(entorno):
    cliente, terra, _ = entorno
    # SINTÉTICO: mismo slug que la REAL "17.PARCIAL VERTICALES S-3 28-09-2026"
    gemela = terra / SUBRUTA_VISITAS / "17 PARCIAL VERTICALES S-3 28-09-2026"
    gemela.mkdir()
    (gemela / "b.pdf").write_bytes(CONTENIDO_FALSO)
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)
    ids = {v["17 PARCIAL VERTICALES S-3 28-09-2026"]["id"], v["17.PARCIAL VERTICALES S-3 28-09-2026"]["id"]}
    assert ids == {"terra-living-17-parcial-verticales-s-3-28-09-2026",
                   "terra-living-17-parcial-verticales-s-3-28-09-2026-2"}
    # Ids estables entre syncs
    _sync(cliente)
    with _bd() as conn:
        assert {k: x["id"] for k, x in _visitas(conn).items()} == {k: x["id"] for k, x in v.items()}


# =====================================================================
# P3: ESTADO "PROCESADA" DESDE INFORMES\2.DATA PROCESADA
# =====================================================================
def test_p3_las_dos_17_quedan_procesadas_con_su_stp(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    informes = terra / SUBRUTA_INFORMES_PROCESADOS
    with _bd() as conn:
        v = _visitas(conn)
    s4 = v["17. COMPLETIVO VERTICALES S-4 28-09-2026"]
    s3 = v["17.PARCIAL VERTICALES S-3 28-09-2026"]
    assert s4["estado"] == s3["estado"] == "Procesada"
    stp_s4 = str(informes / "Terra Living - STP - Verticales Sotano S4 Completivo - 28-09-2026.pdf")
    stp_s3 = str(informes / "Terra Living - STP - Verticales Sotano S3 Parcial - 28-09-2026.pdf")
    assert json.loads(s4["salida_json"]) == {"stp": [stp_s4]}
    assert json.loads(s3["salida_json"]) == {"stp": [stp_s3]}
    origen_s4 = json.loads(s4["origen_datos_json"])
    assert origen_s4["estado"] == "sync_p3" and origen_s4["stp"] == [stp_s4]
    assert origen_s4["regla_p3"] == "estricta"
    assert origen_s4["stp_otra_clase"] == [[Path(stp_s3).name]]


def test_p3_v2_cuenta_como_el_mismo_informe(entorno):
    cliente, terra, _ = entorno
    informes = terra / SUBRUTA_INFORMES_PROCESADOS
    base = "Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026"  # REAL
    (informes / f"{base} v2.pdf").write_bytes(CONTENIDO_FALSO)  # SINTÉTICO: versión v2
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)
    v16 = v["16. VERTICALES PARCIAL S-4 11-09-2026"]
    assert v16["estado"] == "Procesada"
    assert json.loads(v16["salida_json"]) == {
        "stp": [str(informes / f"{base}.pdf"), str(informes / f"{base} v2.pdf")]}


def test_p3_estricta_stp_sin_clase_va_a_dudas(entorno):
    """B1: REAL #18 (Completivo) solo tiene un STP del 02-10-2026 que no dice la clase."""
    cliente, _, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        v18 = _visitas(conn)["18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026"]
        dudas = [d for d in _dudas(conn) if d["visita_id"] == v18["id"]]
    assert v18["estado"] == "Con dudas"
    assert json.loads(v18["salida_json"]) == {}
    assert [(d["categoria"], d["campo_afectado"]) for d in dudas] == [("DUDA_BLOQUEANTE", "estado")]
    stp = "Terra Living - STP - Losa y Vigas Entrepiso 4 Sotano S4 - 02-10-2026 v2.pdf"  # REAL
    assert stp in dudas[0]["descripcion_pregunta"]
    assert "no dice Completivo" in dudas[0]["descripcion_pregunta"]
    origen = json.loads(v18["origen_datos_json"])
    assert origen["estado"] == "sync_dudas" and origen["stp_candidatos"] == [[stp]]
    assert origen["regla_p3"] == "estricta"


def test_p3_estricta_mixta_con_stp_de_su_fecha_va_a_dudas(entorno):
    """REAL #12 (Mixta, 17-08-2026) con un STP SINTÉTICO de su fecha: no se decide solo."""
    cliente, terra, _ = entorno
    informes = terra / SUBRUTA_INFORMES_PROCESADOS
    stp = "Terra Living - STP - Columnas Sotano S5 Completivo - 17-08-2026.pdf"  # SINTÉTICO
    (informes / stp).write_bytes(CONTENIDO_FALSO)
    _sync(cliente)
    with _bd() as conn:
        v12 = _visitas(conn)["12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026"]
        dudas = [d for d in _dudas(conn) if d["visita_id"] == v12["id"]]
    assert v12["clase"] == "Mixta" and v12["estado"] == "Con dudas"
    assert json.loads(v12["salida_json"]) == {}
    assert [(d["categoria"], d["campo_afectado"]) for d in dudas] == [("DUDA_BLOQUEANTE", "estado")]
    assert stp in dudas[0]["descripcion_pregunta"] and "Mixta" in dudas[0]["descripcion_pregunta"]


def test_p3_estricta_mixta_sin_stp_de_su_fecha_sin_procesar(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        v12 = _visitas(conn)["12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026"]
    assert v12["estado"] == "Sin procesar"
    assert json.loads(v12["origen_datos_json"])["estado"] == "sync_sin_stp"


def test_p3_estricta_solo_stp_de_la_clase_contraria_sin_procesar(entorno):
    """REAL #13 (Parcial, 19-08-2026) con un STP SINTÉTICO Completivo de esa fecha."""
    cliente, terra, _ = entorno
    stp = "Terra Living - STP - Losas Sotano S5 Completivo - 19-08-2026.pdf"  # SINTÉTICO
    (terra / SUBRUTA_INFORMES_PROCESADOS / stp).write_bytes(CONTENIDO_FALSO)
    _sync(cliente)
    with _bd() as conn:
        v13 = _visitas(conn)["13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026"]
    assert v13["estado"] == "Sin procesar" and json.loads(v13["salida_json"]) == {}
    origen = json.loads(v13["origen_datos_json"])
    assert origen["estado"] == "sync_sin_stp" and origen["stp_otra_clase"] == [[stp]]


def test_p3_caso_ambiguo_con_dudas(entorno):
    cliente, terra, _ = entorno
    informes = terra / SUBRUTA_INFORMES_PROCESADOS
    # SINTÉTICO: dos STP del 19-08-2026, uno Parcial y otro sin clase en el nombre
    (informes / "Terra Living - STP - Losas Sotano S5 Parcial - 19-08-2026.pdf").write_bytes(CONTENIDO_FALSO)
    (informes / "Terra Living - STP - Porticos Sotano S5 - 19-08-2026.pdf").write_bytes(CONTENIDO_FALSO)
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)["13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026"]  # REAL
        dudas = [d for d in _dudas(conn) if d["visita_id"] == v["id"]]
    assert v["estado"] == "Con dudas" and json.loads(v["salida_json"]) == {}
    assert [(d["categoria"], d["campo_afectado"]) for d in dudas] == [("DUDA_BLOQUEANTE", "estado")]
    assert "Losas Sotano S5 Parcial - 19-08-2026.pdf" in dudas[0]["descripcion_pregunta"]
    assert "Porticos Sotano S5 - 19-08-2026.pdf" in dudas[0]["descripcion_pregunta"]


def test_p3_no_usa_informes_mived_ni_otra_fecha(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)
    # REAL: hay STP del 28-08-2026 y del 11-09-2026, pero no del 31-07 ni del 19-08
    assert v["11 - COLUMNAS S-5 31-07-2026"]["estado"] == "Sin procesar"
    assert json.loads(v["11 - COLUMNAS S-5 31-07-2026"]["salida_json"]) == {}


# Pruebas directas de la regla P3 estricta (nombres REALES salvo indicación)
def _informes(*nombres):
    return [{"nombre": n, "ruta": f"X\\{n}"} for n in nombres]


def test_evaluar_p3_misma_clase_y_agrupa_versiones():
    inf = _informes(
        "Terra Living - STP - Verticales Sotano S3 Parcial - 28-09-2026.pdf",
        "Terra Living - STP - Verticales Sotano S4 Completivo - 28-09-2026.pdf",
        "Terra Living - STP - Verticales Sotano S4 Completivo - 28-09-2026 v2.pdf",  # SINTÉTICO
        "MIVED - TERRA LIVING-LOSAS Y VIGAS PARCIAL SOTANO -3.PDF",
    )
    assert len(stp_de_fecha(inf, "2026-09-28")) == 2  # el MIVED no cuenta
    e = evaluar_p3(inf, "2026-09-28", "Completivo")
    assert e["estado"] == "Procesada" and e["origen"] == "sync_p3"
    assert len(e["stp"]) == 2 and e["stp"][1].endswith("28-09-2026 v2.pdf")
    assert len(e["descartados"]) == 1  # el Parcial es de la otra #17
    assert evaluar_p3(inf, "2026-09-28", "Parcial")["estado"] == "Procesada"
    # Mixta o clase pendiente con STP de su fecha: siempre a dudas, con los candidatos
    for clase in ("Mixta", PENDIENTE):
        e = evaluar_p3(inf, "2026-09-28", clase)
        assert e["estado"] == "Con dudas" and len(e["candidatos"]) == 2 and e["stp"] == []
    assert evaluar_p3(inf, PENDIENTE, "Parcial")["estado"] == "Sin procesar"


def test_evaluar_p3_stp_sin_clase_no_basta():
    inf = _informes("Terra Living - STP - Losa y Vigas Entrepiso 4 Sotano S4 - 02-10-2026 v2.pdf")
    for clase in ("Completivo", "Parcial"):
        e = evaluar_p3(inf, "2026-10-02", clase)
        assert e["estado"] == "Con dudas" and e["origen"] == "sync_dudas" and e["stp"] == []
        assert len(e["candidatos"]) == 1


def test_evaluar_p3_dos_con_su_clase_o_una_mas_sin_clase_va_a_dudas():
    # SINTÉTICOS
    dos = _informes("Terra Living - STP - Losas S5 Parcial - 19-08-2026.pdf",
                    "Terra Living - STP - Porticos S5 Parcial - 19-08-2026.pdf")
    assert evaluar_p3(dos, "2026-08-19", "Parcial")["estado"] == "Con dudas"
    mezcla = _informes("Terra Living - STP - Losas S5 Parcial - 19-08-2026.pdf",
                       "Terra Living - STP - Porticos S5 - 19-08-2026.pdf")
    e = evaluar_p3(mezcla, "2026-08-19", "Parcial")
    assert e["estado"] == "Con dudas" and len(e["candidatos"]) == 2
    ambas = _informes("Terra Living - STP - Losas S5 Parcial y Completivo - 19-08-2026.pdf")
    assert evaluar_p3(ambas, "2026-08-19", "Parcial")["estado"] == "Con dudas"


def test_evaluar_p3_fecha_exacta():
    inf = _informes("Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026.pdf")
    assert evaluar_p3(inf, "2026-09-11", "Parcial")["estado"] == "Procesada"
    assert evaluar_p3(inf, "2026-09-12", "Parcial")["estado"] == "Sin procesar"
    assert evaluar_p3(inf, "2026-11-09", "Parcial")["estado"] == "Sin procesar"  # no M/D


# =====================================================================
# T8: ORIGEN DE LOS DATOS Y CORRECCIÓN ÚNICA DE LAS "PROCESADA" DE LA REGLA LAXA
# =====================================================================
NOMBRE_18 = "18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026"  # REAL
STP_18 = "Terra Living - STP - Losa y Vigas Entrepiso 4 Sotano S4 - 02-10-2026 v2.pdf"  # REAL
PROCESADAS_ESTRICTAS = {
    "14. VERTICALES PARCIALES S-4 28-08-2026", "15 LOSAS Y PORTICOS S-5 COMPLETIVO 02-09-2026",
    "16. VERTICALES PARCIAL S-4 11-09-2026", "17. COMPLETIVO VERTICALES S-4 28-09-2026",
    "17.PARCIAL VERTICALES S-3 28-09-2026", "20. LOSA SOTANO 3 PARCIAL 15-10-2026",
}  # REAL


def _n_auditoria_correccion(conn):
    return conn.execute("SELECT COUNT(*) FROM auditoria WHERE modulo = 'SYNC' "
                        "AND accion = 'CORREGIR_P3_ESTRICTA'").fetchone()[0]


def _simular_bd_de_t5(conn, terra):
    """Deja la BD como la dejó T5 (regla laxa, sin origen): la #18 Procesada con su STP v2."""
    informes = terra / SUBRUTA_INFORMES_PROCESADOS
    conn.execute("UPDATE visitas SET origen_datos_json = '{}'")
    v18 = _visitas(conn)[NOMBRE_18]
    conn.execute("DELETE FROM dudas_y_hallazgos WHERE visita_id = ? AND campo_afectado = 'estado'",
                 (v18["id"],))
    conn.execute("UPDATE visitas SET estado = 'Procesada', salida_json = ? WHERE id = ?",
                 (json.dumps({"stp": [str(informes / STP_18)]}, ensure_ascii=False), v18["id"]))
    return v18["id"]


def test_origen_fecha_pdf_caso_9(entorno):
    """B2: REAL #9 toma la fecha del PDF 'CORRECCIONES SUPERVISION 23-07-2026.pdf' (Steven
    confirmó que es la fecha de la visita); el origen queda guardado en la BD."""
    cliente, _, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        v9 = _visitas(conn)["9 - LOSA S-6 PARCIAL"]
        v20 = _visitas(conn)["20. LOSA SOTANO 3 PARCIAL 15-10-2026"]
        v11 = _visitas(conn)["11 - COLUMNAS S-5 31-07-2026"]
        v3 = _visitas(conn)["3. VERTICALES SOTANO -7"]
    assert v9["fecha_visita"] == "2026-07-23"
    o9 = json.loads(v9["origen_datos_json"])
    assert o9["fecha"] == "pdf" and o9["pdfs_fecha"] == ["CORRECCIONES SUPERVISION 23-07-2026.pdf"]
    assert o9["clase"] == "carpeta" and o9["pdfs_clase"] == []
    assert o9["estado"] == "sync_sin_stp"
    o20 = json.loads(v20["origen_datos_json"])
    assert (o20["fecha"], o20["clase"], o20["estado"]) == ("carpeta", "carpeta", "sync_p3")
    o11 = json.loads(v11["origen_datos_json"])
    assert (o11["fecha"], o11["clase"]) == ("carpeta", "pdf")
    assert o11["pdfs_clase"] == ["Verticales S-5 Parcial.pdf"]
    o3 = json.loads(v3["origen_datos_json"])
    assert (o3["fecha"], o3["clase"], o3["estado"]) == (None, None, "sync_dudas")


def test_origen_se_rellena_en_visitas_existentes_y_respeta_dudas_resueltas(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    nombre = "1. FONDO DE SEPTICO"  # REAL: sin fecha ni clase
    with _bd() as conn:
        conn.execute("UPDATE visitas SET origen_datos_json = '{}'")  # como quedó T5
        v = _visitas(conn)[nombre]
        conn.execute("""UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = '2026-03-10'
                        WHERE visita_id = ? AND campo_afectado = 'fecha_visita'""", (v["id"],))  # SINTÉTICO
    p = _resumen(_sync(cliente))
    assert p["actualizadas"] == 22  # se rellenó el origen de todas
    with _bd() as conn:
        v9 = _visitas(conn)["9 - LOSA S-6 PARCIAL"]
        v1 = _visitas(conn)[nombre]
    assert json.loads(v9["origen_datos_json"])["fecha"] == "pdf"
    o1 = json.loads(v1["origen_datos_json"])
    assert "fecha" not in o1 and o1["clase"] is None  # la fecha la respondió Steven
    assert _resumen(_sync(cliente))["sin_cambios"] == 22


def test_correccion_unica_pasa_la_18_a_dudas_una_sola_vez(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        id18 = _simular_bd_de_t5(conn, terra)
        assert _visitas(conn)[NOMBRE_18]["estado"] == "Procesada"
        assert _n_auditoria_correccion(conn) == 0

    p = _resumen(_sync(cliente))
    assert [c["visita_id"] for c in p["corregidas_p3"]] == [id18]
    assert len(p["p3_confirmadas"]) == 6
    assert p["procesadas"] == 6 and p["con_dudas"] == 12
    with _bd() as conn:
        v = _visitas(conn)
        dudas = [d for d in _dudas(conn) if d["visita_id"] == id18]
        filas = conn.execute("SELECT entidad_id, detalle_json FROM auditoria "
                             "WHERE accion = 'CORREGIR_P3_ESTRICTA'").fetchall()
    v18 = v[NOMBRE_18]
    assert v18["estado"] == "Con dudas" and json.loads(v18["salida_json"]) == {}
    assert [(d["categoria"], d["campo_afectado"]) for d in dudas] == [("DUDA_BLOQUEANTE", "estado")]
    assert STP_18 in dudas[0]["descripcion_pregunta"]
    origen = json.loads(v18["origen_datos_json"])
    salida_vieja = {"stp": [str(terra / SUBRUTA_INFORMES_PROCESADOS / STP_18)]}
    assert origen["correccion_p3"]["salida_anterior"] == salida_vieja
    assert origen["correccion_p3"]["estado_anterior"] == "Procesada"
    assert origen["estado"] == "sync_dudas" and origen["stp_candidatos"] == [[STP_18]]
    assert len(filas) == 1 and filas[0]["entidad_id"] == id18
    detalle = json.loads(filas[0]["detalle_json"])
    assert detalle["estado_anterior"] == "Procesada" and detalle["candidatos"] == [[STP_18]]
    assert detalle["salida_anterior"] == salida_vieja
    # Las otras 6 (incluidas las dos #17) siguen Procesada y quedan marcadas con la regla estricta
    for nombre in PROCESADAS_ESTRICTAS:
        assert v[nombre]["estado"] == "Procesada", nombre
        o = json.loads(v[nombre]["origen_datos_json"])
        assert (o["estado"], o["regla_p3"]) == ("sync_p3", "estricta")
        assert o["stp"] == json.loads(v[nombre]["salida_json"])["stp"]

    # Segunda vez: no hace nada
    with _bd() as conn:
        antes, dudas_antes = _visitas(conn), _dudas(conn)
    p2 = _resumen(_sync(cliente))
    assert p2["corregidas_p3"] == [] and p2["p3_confirmadas"] == []
    assert (p2["visitas_nuevas"], p2["actualizadas"], p2["sin_cambios"]) == (0, 0, 22)
    with _bd() as conn:
        assert _visitas(conn) == antes and _dudas(conn) == dudas_antes
        assert _n_auditoria_correccion(conn) == 1


def test_correccion_no_toca_procesada_con_origen_ajeno_al_sync(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    informes = terra / SUBRUTA_INFORMES_PROCESADOS
    ajena = "11 - COLUMNAS S-5 31-07-2026"  # REAL; estado y salida SINTÉTICOS (p. ej. Etapa 3)
    sin_origen = "13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026"  # REAL; salida SINTÉTICA no del sync
    with _bd() as conn:
        _simular_bd_de_t5(conn, terra)
        conn.execute("""UPDATE visitas SET estado = 'Procesada', salida_json = ?,
                        origen_datos_json = ? WHERE nombre_carpeta = ?""",
                     (json.dumps({"stp": [str(informes / "SINTETICO 31-07-2026.pdf")]}),
                      json.dumps({"estado": "generador_etapa3"}), ajena))
        conn.execute("""UPDATE visitas SET estado = 'Procesada', salida_json = ?
                        WHERE nombre_carpeta = ?""",
                     (json.dumps({"stp-mived": "C:\\SINTETICO\\x.pdf"}), sin_origen))
        antes = _visitas(conn)
    p = _resumen(_sync(cliente))
    assert [c["nombre_carpeta"] for c in p["corregidas_p3"]] == [NOMBRE_18]
    with _bd() as conn:
        despues = _visitas(conn)
    for nombre in (ajena, sin_origen):
        assert despues[nombre]["estado"] == "Procesada"
        assert despues[nombre]["salida_json"] == antes[nombre]["salida_json"]
        assert json.loads(despues[nombre]["origen_datos_json"]).get("estado") == \
            json.loads(antes[nombre]["origen_datos_json"] or "{}").get("estado")


def test_correccion_respeta_duda_de_estado_resuelta(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    with _bd() as conn:
        id18 = _simular_bd_de_t5(conn, terra)
        # SINTÉTICO: Steven ya respondió la duda de estado de la #18
        conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                        campo_afectado, descripcion_pregunta, respuesta_usuario, resuelta, creado)
                        VALUES ('terra-living', ?, '', 'DUDA_BLOQUEANTE', 'estado', 'SINTETICO',
                        'SINTETICO', 1, '2026-10-21T00:00:00')""", (id18,))
    p = _resumen(_sync(cliente))
    assert p["corregidas_p3"] == []
    with _bd() as conn:
        assert _visitas(conn)[NOMBRE_18]["estado"] == "Procesada"
        assert _n_auditoria_correccion(conn) == 0


# =====================================================================
# AUDITORÍA, PROYECTOS, LAYOUT NO SOPORTADO, SOLO LECTURA
# =====================================================================
def test_una_fila_de_auditoria_por_sync_y_proyecto(entorno):
    cliente, _, _ = entorno
    with _bd() as conn:
        assert _n_auditoria_sync(conn) == 0
    _sync(cliente)
    with _bd() as conn:
        assert _n_auditoria_sync(conn, "terra-living") == 1
        assert _n_auditoria_sync(conn) == 1
        detalle = json.loads(conn.execute(
            "SELECT detalle_json FROM auditoria WHERE modulo = 'SYNC' ORDER BY id DESC").fetchone()[0])
    assert detalle["visitas_nuevas"] == 22 and detalle["con_dudas"] == 12
    _sync(cliente)
    with _bd() as conn:
        assert _n_auditoria_sync(conn, "terra-living") == 2
    resp = _sync(cliente, proyecto_id=None)  # todos los proyectos
    assert {p["id"] for p in resp["proyectos"]} == {"terra-living", "torre-p16", "hotel-zoetry-h2-h5"}
    with _bd() as conn:
        assert _n_auditoria_sync(conn) == 2 + 3
        assert _n_auditoria_sync(conn, "torre-p16") == 1


def test_layout_no_soportado_aviso_sin_visitas(entorno):
    cliente, _, raiz = entorno
    p16 = raiz / "SUPERVISION" / "EN CURSO" / "PROYECTO P16"  # REAL (D3)
    zapatas = p16 / "VISITAS" / "VISITA A OBRA" / "00. ZAPATAS"  # REAL
    zapatas.mkdir(parents=True)
    (zapatas / "08-09-2025 Zapata parcial 3.pdf").write_bytes(CONTENIDO_FALSO)  # REAL (nombre)
    p = _resumen(_sync(cliente, "torre-p16"), "torre-p16")
    assert p["layout"] == LAYOUT_NO_SOPORTADO
    assert p["visitas_nuevas"] == 0
    assert any(LAYOUT_NO_SOPORTADO in a for a in p["avisos"])
    with _bd() as conn:
        assert _visitas(conn, "torre-p16") == {}
        assert _n_auditoria_sync(conn, "torre-p16") == 1


def test_carpeta_de_proyecto_inexistente_es_aviso(entorno):
    cliente, _, _ = entorno
    p = _resumen(_sync(cliente, "hotel-zoetry-h2-h5"), "hotel-zoetry-h2-h5")  # no existe en tmp
    assert p["layout"] == PENDIENTE and p["visitas_nuevas"] == 0
    assert any(a.startswith(PENDIENTE) for a in p["avisos"])


def test_planos_sellados_se_actualizan_y_no_se_borran(entorno):
    cliente, terra, _ = entorno
    with _bd() as conn:
        conn.execute("UPDATE proyectos SET planos_sellados = '' WHERE id = 'terra-living'")
    _sync(cliente)
    with _bd() as conn:
        assert conn.execute("SELECT planos_sellados FROM proyectos WHERE id = 'terra-living'"
                            ).fetchone()[0] == PLANO_SELLADO_TERRA
    (terra / SUBRUTA_PLANOS_SELLADOS / PLANO_SELLADO_TERRA).unlink()
    p = _resumen(_sync(cliente))
    with _bd() as conn:
        assert conn.execute("SELECT planos_sellados FROM proyectos WHERE id = 'terra-living'"
                            ).fetchone()[0] == PLANO_SELLADO_TERRA
    assert any("planos sellados" in a for a in p["avisos"])


def test_dashboard_devuelve_las_visitas(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    r = cliente.get("/api/dashboard")
    assert r.status_code == 200
    datos = r.json()
    assert len(datos["visitas"]) == 22
    assert datos["stats"]["visitas_con_dudas"] == 12


def test_sync_no_modifica_dropbox(entorno):
    cliente, _, raiz = entorno
    antes = _foto_arbol(raiz)
    _sync(cliente)
    _sync(cliente, proyecto_id=None)
    assert _foto_arbol(raiz) == antes


def test_fallo_revierte_el_proyecto(entorno, monkeypatch):
    """Una transacción por proyecto: si algo falla, no queda nada a medias."""
    cliente, _, _ = entorno
    import sync.sincronizador as s

    def falla(*args, **kwargs):
        raise RuntimeError("fallo sintetico")  # SINTÉTICO

    monkeypatch.setattr(s, "_auditar", falla)
    with pytest.raises(RuntimeError):
        cliente.post("/api/dropbox/sync", params={"proyecto_id": "terra-living"})
    with _bd() as conn:
        assert conn.execute("SELECT COUNT(*) FROM visitas").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM dudas_y_hallazgos").fetchone()[0] == 0


# =====================================================================
# Etapa 3 · T4b — hallazgos no congelan campos; el sync cierra la duda archivos_json
# =====================================================================

def test_t4b_a_hallazgo_revisado_no_congela_el_campo(entorno):
    """#8 REAL: hallazgo de clase. Revisado, el sync sigue actualizando la clase desde Dropbox."""
    cliente, _, _ = entorno
    _sync(cliente)
    nombre = "8 - COLUMNAS S-6 COMPLETIVO"
    with _bd() as conn:
        v = _visitas(conn)[nombre]
        conn.execute("""UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = 'revisado'
                        WHERE visita_id = ? AND categoria = 'HALLAZGO_INTERNO'
                        AND campo_afectado = 'clase'""", (v["id"],))
        conn.execute("UPDATE visitas SET clase = 'Parcial' WHERE id = ?", (v["id"],))  # SINTÉTICO: valor viejo
        from sync.sincronizador import _campos_resueltos
        assert "clase" not in _campos_resueltos(conn, v["id"])
    _sync(cliente)
    with _bd() as conn:
        assert _visitas(conn)[nombre]["clase"] == "Completivo"  # manda la carpeta


def test_t4b_a_bloqueante_resuelta_si_congela_el_campo(entorno):
    cliente, _, _ = entorno
    _sync(cliente)
    nombre = "1. FONDO DE SEPTICO"
    with _bd() as conn:
        v = _visitas(conn)[nombre]
        conn.execute("""UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = 'x'
                        WHERE visita_id = ? AND campo_afectado = 'clase'""", (v["id"],))
        from sync.sincronizador import _campos_resueltos
        assert "clase" in _campos_resueltos(conn, v["id"])


def _duda_archivos(conn, v):
    return dict(conn.execute("""SELECT * FROM dudas_y_hallazgos WHERE visita_id = ?
                                AND campo_afectado = 'archivos_json'""", (v["id"],)).fetchone())


def _n_aud(conn, accion):
    return conn.execute("SELECT COUNT(*) FROM auditoria WHERE accion = ?", (accion,)).fetchone()[0]


def test_t4b_b_el_sync_cierra_la_duda_archivos_cuando_aparece_el_pdf(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    carpeta = "19. VERTICALES S-3 COMPLETIVO 09-10-2026"  # REAL: carpeta sin PDF
    with _bd() as conn:
        v = _visitas(conn)[carpeta]
        assert v["estado"] == "Con dudas" and _duda_archivos(conn, v)["resuelta"] == 0
    (terra / SUBRUTA_VISITAS / carpeta / "VERTICALES S-3 COMPLETIVO.pdf").write_bytes(CONTENIDO_FALSO)  # SINTÉTICO
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)[carpeta]
        d = _duda_archivos(conn, v)
        assert d["resuelta"] == 1 and d["respuesta_usuario"] == "resuelta por sincronización"
        assert d["resuelto_en"]
        fila = conn.execute("SELECT * FROM auditoria WHERE accion = 'CERRAR_DUDA_ARCHIVOS'").fetchone()
        detalle = json.loads(fila["detalle_json"])
        assert fila["entidad_id"] == str(d["id"])
        assert detalle["estado_anterior"] == "Con dudas" and detalle["estado_nuevo"] == "Sin procesar"
    assert v["estado"] == "Sin procesar" and json.loads(v["salida_json"]) == {}  # nunca Procesada solo
    # Segundo sync: nada cambia ni se vuelve a auditar
    _sync(cliente)
    with _bd() as conn:
        assert _n_aud(conn, "CERRAR_DUDA_ARCHIVOS") == 1
        assert _visitas(conn)[carpeta]["estado"] == "Sin procesar"


def test_t4b_b_si_queda_otra_bloqueante_la_visita_sigue_con_dudas(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    carpeta = "19. VERTICALES S-3 COMPLETIVO 09-10-2026"
    with _bd() as conn:
        v = _visitas(conn)[carpeta]
        conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                        campo_afectado, descripcion_pregunta, creado)
                        VALUES ('terra-living', ?, 'C1', 'DUDA_BLOQUEANTE', 'ejes', 'SINTÉTICO', 'x')""",
                     (v["id"],))
    (terra / SUBRUTA_VISITAS / carpeta / "VERTICALES S-3 COMPLETIVO.pdf").write_bytes(CONTENIDO_FALSO)  # SINTÉTICO
    _sync(cliente)
    with _bd() as conn:
        assert _duda_archivos(conn, _visitas(conn)[carpeta])["resuelta"] == 1
        assert _visitas(conn)[carpeta]["estado"] == "Con dudas"


def test_t4b_b_si_el_pdf_vuelve_a_faltar_se_reabre_la_duda(entorno):
    cliente, terra, _ = entorno
    _sync(cliente)
    carpeta = "19. VERTICALES S-3 COMPLETIVO 09-10-2026"
    pdf = terra / SUBRUTA_VISITAS / carpeta / "VERTICALES S-3 COMPLETIVO.pdf"
    pdf.write_bytes(CONTENIDO_FALSO)  # SINTÉTICO
    _sync(cliente)
    pdf.unlink()
    _sync(cliente)
    with _bd() as conn:
        v = _visitas(conn)[carpeta]
        d = _duda_archivos(conn, v)
        assert d["resuelta"] == 0 and d["respuesta_usuario"] == ""
        assert _n_aud(conn, "REABRIR_DUDA_ARCHIVOS") == 1
    assert v["estado"] == "Con dudas"
