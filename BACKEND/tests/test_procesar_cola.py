# BACKEND/tests/test_procesar_cola.py
# Etapa 3 · T10a — Procesador de la cola (PLANES/etapa-3.md, T10a). Sustituye a las pruebas de la Etapa 1 · T9
# (botón desactivado con 409).
#
# BD, Dropbox, datos, caché y salida temporales. Todo es # SINTÉTICO: obra, plano, elementos de diseño, visita y
# fotos inventados solo para probar las reglas; no son datos de ningún proyecto. Las pruebas que generan el STP
# (Chromium de Playwright) se saltan con un mensaje si el navegador no está instalado.
import functools
import io
import json
import sqlite3
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import config
import database
import main
import mesa_dudas
import procesador_cola as pc
from reglas_ingenieria import PENDIENTE
from sync import lector_visita
from sync.sincronizador import estado_tras_cerrar_bloqueantes

PID = "obra-sint"
VID = "obra-sint-18-losa-s-4-completivo-02-10-2026"
CARPETA = "18. LOSA S-4 COMPLETIVO 02-10-2026"  # SINTÉTICO
CAMPOS_DISENO = {"tipo_losa": "MACIZA", "H": "0.25", "TOP X": '2-Ø1/2"', "BOT X": '2-Ø1/2"', "BOT Y": '2-Ø1/2"',
                 "fc_kgcm2": "350"}  # SINTÉTICO
MAPEO_SINT = {"losa": {"filas": {"a": "fc_kgcm2", "h": "TOP X", "i": "BOT X", "n": "BOT Y"},
                       "medidas": {"b": "H"}}}  # SINTÉTICO: el mapeo real lo decide Steven
OBRA_COMPLETA = {"b": 0.20, "obra": {"a": "350", "e": "SI", "f": "0.025", "g": "0.025", "h": '2-Ø1/2"',
                                     "i": '2-Ø1/2"', "n": '2-Ø1/2"'}}  # SINTÉTICO: 0.20 + 2·0.025 = 0.25


# ---------- Material sintético ----------

def _pdf_plano(ruta: Path):
    doc = pymupdf.open()
    hoja = doc.new_page(width=792, height=612)
    hoja.draw_rect(pymupdf.Rect(120, 120, 260, 220), color=(0, 0, 0), width=2)
    hoja.insert_text((300, 300), "PLANTA SINTETICO", fontsize=24)
    doc.save(str(ruta))
    doc.close()


def _jpeg(color) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (768, 1024), color).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _pdf_visita(ruta: Path, etiquetas):
    """Una foto por página, la etiqueta (12 pt negrita) y 'Creado el:' debajo, como los PDF de visita."""
    doc = pymupdf.open()
    for i, et in enumerate(etiquetas, start=1):
        hoja = doc.new_page(width=612, height=792)
        hoja.insert_image(pymupdf.Rect(56, 99, 465, 644), stream=_jpeg((40 * i % 255, 100, 120)))
        y = 660
        if et:
            hoja.insert_text((56, y), et, fontname="hebo", fontsize=12)
            y += 20
        hoja.insert_text((56, y), "Creado el:", fontname="hebo", fontsize=10)
        hoja.insert_text((117, y), f"02/10/2026 10:{i:02d}", fontname="helv", fontsize=10)
    doc.save(str(ruta))
    doc.close()


def _bd():
    conn = sqlite3.connect(config.obtener_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _arbol(raiz: Path):
    return sorted((str(p.relative_to(raiz)), p.stat().st_size, p.stat().st_mtime_ns) for p in raiz.rglob("*"))


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    for nombre in ("bd", "dropbox", "datos", "cache", "salida"):
        (tmp_path / nombre).mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "prueba.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(config.ENV_DATOS_RAIZ, str(tmp_path / "datos"))
    monkeypatch.setenv(config.ENV_CACHE_RAIZ, str(tmp_path / "cache"))
    monkeypatch.setenv(lector_visita.ENV_CACHE_RAIZ, str(tmp_path / "cache"))
    monkeypatch.setenv(config.ENV_SALIDA_PRUEBAS, str(tmp_path / "salida"))
    monkeypatch.setattr(pc, "MAPEO_DISENO_A_STP", {})
    database.inicializar_bd()
    obra = tmp_path / "dropbox" / "OBRA SINT"
    (obra / "INFORMES" / "2.DATA PROCESADA").mkdir(parents=True)
    carpeta_visita = obra / "LEVANTAMIENTO" / "VISITA A OBRA" / CARPETA
    carpeta_visita.mkdir(parents=True)
    planos = tmp_path / "datos" / PID / "planos" / "r01"
    planos.mkdir(parents=True)
    vectorial = planos / "vectorial.pdf"
    _pdf_plano(vectorial)
    with _bd() as conn:
        conn.execute("""INSERT INTO proyectos (id, nombre, tipo, formato_defecto, carpeta_dropbox, no_solicitud,
                        no_licencia, direccion_obra, provincia, sector, residente_obra, actualizado)
                        VALUES (?, 'Obra Sintetica', 'Supervisión', 'STP-MIVED', ?, 'SOL-SINT', 'LIC-SINT',
                        'CALLE SINT 1', 'PROV SINT', 'SECTOR SINT', 'RESIDENTE SINT', 'x')""", (PID, str(obra)))
        conn.execute("""INSERT INTO planos (proyecto_id, revision, estado, vectorial_archivo, vectorial_ruta,
                        vectorial_sha256, vectorial_bytes, vectorial_paginas, sellado_archivo, sellado_ruta, sellado_sha256,
                        sellado_bytes, sellado_paginas, certificado_por, certificado_en, certificacion_texto, subido_en)
                        VALUES (?, 1, 'vigente', 'vectorial.pdf', ?, 'x', 1, 1, 'sellado.pdf', ?, 'x', 1, 1, 'prueba',
                        'x', 'x', 'x')""", (PID, str(vectorial), str(planos / "sellado.pdf")))
        conn.execute("""INSERT INTO visitas (id, proyecto_id, numero, nombre_carpeta, ruta_carpeta, fecha_visita, clase,
                        estado, formatos_solicitados, archivos_json, actualizado)
                        VALUES (?, ?, 18, ?, ?, '2026-10-02', 'Completivo', 'Sin procesar', '["STP-MIVED"]', ?, 'x')""",
                     (VID, PID, CARPETA, str(carpeta_visita),
                      json.dumps([{"nombre": "visita.pdf", "ruta": str(carpeta_visita / "visita.pdf")}])))
    return {"tmp": tmp_path, "obra": obra, "carpeta_visita": carpeta_visita, "vectorial": vectorial}


def _diseno(uid="ed-0001", id_elemento="L5", nivel="SOTANO S4", ejes="—", confirmado=True, recuadros=True,
            tipo="LOSA MACIZA"):
    estado = {k: ("confirmado" if confirmado else "pendiente_de_verificar")
              for k in ["id_elemento", "tipo_elemento", "nivel_rango", "ejes"] + [f"datos_diseno.{c}" for c in CAMPOS_DISENO]}
    loc = {"plano_id": 1, "pagina": 1, "rect": [100, 100, 300, 250], "estado": "confirmado"} if recuadros else {}
    det = {"plano_id": 1, "pagina": 1, "rect": [0, 0, 300, 200], "estado": "confirmado"} if recuadros else {}
    with _bd() as conn:
        conn.execute("""INSERT INTO elementos_diseno (uid, proyecto_id, id_elemento, tipo_elemento, nivel_rango, ejes,
                        hoja_plano_origen, archivo_plano_origen, datos_diseno_json, estado_campos_json,
                        recorte_planta_json, recorte_detalle_json, actualizado, fuente_json, plano_id)
                        VALUES (?, ?, ?, ?, ?, ?, '21', 'vectorial.pdf', ?, ?, ?, ?, 'x', ?, 1)""",
                     (uid, PID, id_elemento, tipo, nivel, ejes, json.dumps(CAMPOS_DISENO), json.dumps(estado),
                      json.dumps(loc), json.dumps(det),
                      json.dumps({"tabla": "p1:acero_en_losa", "bbox_id": [[10, 10, 20, 20]]})))


def _elemento_visita(entorno, orden=1, etiqueta="L5 —", id_elemento="L5", ejes="—", nivel="S-4", medidas=None):
    """Capa 2 ya leída (como la deja el lector), con sus fotos en la caché."""
    cache = entorno["tmp"] / "cache"
    rel = f"{PID}/{VID}/p{orden:03d}.jpg"
    (cache / rel).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (400, 300), (200, 60, 60)).save(cache / rel, format="JPEG")
    with _bd() as conn:
        conn.execute("""INSERT INTO elementos_visita (uid, visita_id, orden_en_log, etiqueta_original, id_elemento,
                        tipo_elemento, nivel, ejes, fotos_json, medidas_acero_campo_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (f"{VID}-{orden:03d}", VID, orden, etiqueta, id_elemento, PENDIENTE, nivel, ejes,
                      json.dumps([{"pagina": orden, "etiqueta": etiqueta, "cache": rel}]), json.dumps(medidas or {})))


def _duda_lector(orden=1, etiqueta="L5", resuelta=False, respuesta=""):
    with _bd() as conn:
        cur = conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria,
                              campo_afectado, descripcion_pregunta, respuesta_usuario, resuelta, creado)
                              VALUES (?, ?, ?, 'DUDA_BLOQUEANTE', ?, 'SINT', ?, ?, 'x')""",
                           (PID, VID, etiqueta, f"elemento_visita:p{orden:03d}", respuesta, int(resuelta)))
        return cur.lastrowid


def _procesar(visita_id=VID):
    t = pc.lanzar_trabajo([visita_id], en_hilo=False, usuario="prueba")
    t = pc.obtener_trabajo(t["id"])
    eventos = pc.listar_eventos(t["id"])["eventos"]
    return t, eventos


def _visita():
    with _bd() as conn:
        return dict(conn.execute("SELECT * FROM visitas WHERE id = ?", (VID,)).fetchone())


def _abiertas():
    with _bd() as conn:
        return [dict(d) for d in conn.execute("""SELECT * FROM dudas_y_hallazgos WHERE visita_id = ? AND resuelta = 0
                                                 AND categoria = 'DUDA_BLOQUEANTE' ORDER BY id""", (VID,))]


@functools.lru_cache(maxsize=1)
def _chromium_disponible() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:  # noqa: BLE001
        return False


def _exigir_chromium():
    if not _chromium_disponible():
        pytest.skip("Chromium de Playwright no está instalado en esta máquina (python -m playwright install chromium)")


# ---------- Unidades ----------

def test_niveles_del_sotano_y_clave_completa():
    assert pc.niveles_de_diseno("S-4") == {"S-4", "SOTANO S4", "SOTANO S-4", "SOTANO -4"}
    assert pc.niveles_de_diseno("NIVEL 4@8") == {"NIVEL 4@8"}  # un rango nunca se expande solo
    assert pc.clave_nivel_completa("S-4") == "SOTANO -4"
    assert pc.clave_nivel_completa(PENDIENTE) is None


@pytest.mark.parametrize("texto, esperado", [
    ("C1 A4", {"id": "C1", "ejes": "EJE A-4"}),
    ("c1 4a", {"id": "C1", "ejes": "EJE A-4"}),
    ("L5 —", {"id": "L5", "ejes": "—"}),
    ("L5", {"id": "L5", "ejes": None}),
    ("ed-00ab", {"uid": "ed-00ab"}),
    ("pertenece al anterior", {"anterior": True}),
    ("es la losa de al lado", None),
    ("Mh4", {"id": "MH4", "ejes": None}),  # el ID que escribe Steven, en mayúsculas (normalización aprobada)
    ("Mh4 pantalla eje 3", None),
    ("", None),
])
def test_respuesta_de_steven_se_lee_de_forma_estricta(texto, esperado):
    assert pc.interpretar_respuesta(texto) == esperado


# ---------- Cruce (§4.2) y Regla de Oro ----------

def test_sin_candidato_en_el_plano_crea_duda_con_referencias_y_el_trabajo_sigue(entorno):
    _elemento_visita(entorno, 1, "L5 —", "L5", "—")
    _elemento_visita(entorno, 2, "L9 —", "L9", "—")
    _diseno()
    t, eventos = _procesar()
    assert t["estado"] == "terminado"
    tipos = [e["tipo"] for e in eventos]
    assert tipos[0] == "visita_inicio" and tipos[-1] == "fin" and "visita_fin" in tipos
    assert tipos.count("elemento_inicio") == 2  # la duda del primero no detuvo el segundo
    dudas = [e for e in eventos if e["tipo"] == "duda"]
    cruce = next(d for d in dudas if d["campo"] == "cruce:p002")
    assert "ningún elemento de diseño" in cruce["pregunta"]
    assert cruce["visita_pdf"]["pagina"] == 2 and cruce["visita_pdf"]["ruta"].endswith("visita.pdf")
    assert cruce["plano"]["plano_id"] == 1 and cruce["elemento"]["etiqueta"] == "L9 —"
    assert _visita()["estado"] == "Con dudas"


def test_varios_candidatos_no_se_elige_uno(entorno):
    _elemento_visita(entorno, 1, "L5", "L5", PENDIENTE)
    _duda_lector(1, resuelta=True, respuesta="L5")  # solo el ID
    _diseno("ed-0001", ejes="—")
    _diseno("ed-0002", nivel="SOTANO -4", ejes="—")
    _, eventos = _procesar()
    d = next(e for e in eventos if e["tipo"] == "duda" and e["campo"] == "cruce:p001")
    assert "2 elementos de diseño" in d["pregunta"] and "ed-0001" in d["pregunta"] and "ed-0002" in d["pregunta"]


def test_diseno_sin_confirmar_es_duda_con_la_hoja_del_plano(entorno):
    _elemento_visita(entorno, 1)
    _diseno(confirmado=False)
    _, eventos = _procesar()
    d = next(e for e in eventos if e["tipo"] == "duda" and e["campo"] == "diseno:p001")
    assert "sin confirmar" in d["pregunta"] and "datos_diseno.H" in d["pregunta"]
    assert d["plano"] == {"plano_id": 1, "pagina": 1, "bbox": [[10, 10, 20, 20]], "uid_diseno": "ed-0001",
                          "recuadro": {"plano_id": 1, "pagina": 1, "rect": [100, 100, 300, 250], "estado": "confirmado"}}
    assert not list((entorno["tmp"] / "salida").rglob("*.pdf"))


def test_sin_mapeo_de_filas_aprobado_el_elemento_queda_en_espera(entorno):
    _elemento_visita(entorno, 1)
    _diseno()
    _, eventos = _procesar()
    assert any(e["tipo"] == "duda" and e["campo"] == "diseno:p001:mapeo" for e in eventos)
    assert not any(e["tipo"] == "pdf_generado" for e in eventos)


def test_recuadros_sin_confirmar_son_duda(entorno, monkeypatch):
    monkeypatch.setattr(pc, "MAPEO_DISENO_A_STP", MAPEO_SINT)
    _elemento_visita(entorno, 1)
    _diseno(recuadros=False)
    _procesar()
    campos = {d["campo_afectado"] for d in _abiertas()}
    assert {"diseno:p001:localizacion", "diseno:p001:detalle"} <= campos


def test_la_etiqueta_nunca_se_usa_como_id(entorno):
    # 'L5' suelta: el lector la dejó pendiente con su duda. Aunque L5 existe en el plano, no se cruza.
    _elemento_visita(entorno, 1, "L5", PENDIENTE, PENDIENTE)
    lector = _duda_lector(1)
    _diseno()
    _, eventos = _procesar()
    assert not any(e["tipo"] == "elemento_listo" for e in eventos)
    d = [e for e in eventos if e["tipo"] == "duda"]
    assert d[0]["duda_id"] == lector and d[0]["nueva"] is False
    assert not any(x["campo_afectado"].startswith("cruce:") for x in _abiertas())


def test_o4_la_respuesta_de_steven_se_aplica_estricta(entorno, monkeypatch):
    monkeypatch.setattr(pc, "MAPEO_DISENO_A_STP", MAPEO_SINT)
    _elemento_visita(entorno, 1, "L5", PENDIENTE, PENDIENTE)
    _elemento_visita(entorno, 2, "losa grande", PENDIENTE, PENDIENTE)
    _duda_lector(1, resuelta=True, respuesta="L5 —")
    _duda_lector(2, "losa grande", resuelta=True, respuesta="es la losa de al lado")
    _diseno()
    _, eventos = _procesar()
    listos = [e for e in eventos if e["tipo"] == "elemento_listo"]
    assert [e["elemento"]["orden_en_log"] for e in listos] == [1]
    d = next(e for e in eventos if e["tipo"] == "duda" and e["campo"] == "cruce:p002:respuesta")
    assert "no se puede aplicar sin" in d["pregunta"]


def test_reintento_antes_de_cerrar_si_steven_responde_mientras_corre(entorno, monkeypatch):
    monkeypatch.setattr(pc, "MAPEO_DISENO_A_STP", MAPEO_SINT)
    _elemento_visita(entorno, 1, "L5", PENDIENTE, PENDIENTE)
    lector = _duda_lector(1)
    _diseno()
    original = pc.ProcesoVisita._elemento

    def con_respuesta(self, ev, reintento=False):
        r = original(self, ev, reintento)
        if not reintento:  # Steven responde en la Mesa mientras el trabajo sigue
            mesa_dudas.responder_duda(lector, "L5 —")
        return r
    monkeypatch.setattr(pc.ProcesoVisita, "_elemento", con_respuesta)
    _, eventos = _procesar()
    inicios = [e for e in eventos if e["tipo"] == "elemento_inicio"]
    assert [e["reintento"] for e in inicios] == [False, True]
    assert any(e["tipo"] == "elemento_listo" for e in eventos)


def test_una_respuesta_que_ya_no_hace_falta_cierra_la_duda_propia(entorno, monkeypatch):
    _elemento_visita(entorno, 1)
    _diseno(confirmado=False)
    _procesar()
    assert any(d["campo_afectado"] == "diseno:p001" for d in _abiertas())
    with _bd() as conn:  # se confirman los datos en el plano (T7n)
        estado = {k: "confirmado" for k in json.loads(conn.execute(
            "SELECT estado_campos_json FROM elementos_diseno").fetchone()[0])}
        conn.execute("UPDATE elementos_diseno SET estado_campos_json = ?", (json.dumps(estado),))
    _procesar()
    campos = {d["campo_afectado"] for d in _abiertas()}
    assert "diseno:p001" not in campos and "diseno:p001:mapeo" in campos
    with _bd() as conn:
        assert conn.execute("""SELECT respuesta_usuario FROM dudas_y_hallazgos WHERE campo_afectado = 'diseno:p001'""").fetchone()[0] \
            == pc.RESPUESTA_CIERRE


# ---------- Visita: lector, P3 (O5), clase, cabecera ----------

def test_lector_corre_si_la_visita_no_fue_leida_y_queda_con_dudas(entorno):
    _pdf_visita(entorno["carpeta_visita"] / "visita.pdf", ["Mh4", "", "Tramo D-B"])
    _, eventos = _procesar()
    with _bd() as conn:
        assert conn.execute("SELECT COUNT(*) FROM elementos_visita WHERE visita_id = ?", (VID,)).fetchone()[0] == 2
    assert any(e["tipo"] == "aviso" and "Visita leída" in e["texto"] for e in eventos)
    assert _visita()["estado"] == "Con dudas"  # O1 del lector
    assert {d["campo_afectado"] for d in _abiertas()} >= {"elemento_visita:p001", "elemento_visita:p003"}


def test_o5_si_ya_hay_un_stp_de_su_fecha_no_se_regenera(entorno, monkeypatch):
    monkeypatch.setattr(pc, "MAPEO_DISENO_A_STP", MAPEO_SINT)
    stp = entorno["obra"] / "INFORMES" / "2.DATA PROCESADA" / "Obra Sintetica - STP - Losa S4 Completivo - 02-10-2026.pdf"
    stp.write_bytes(b"%PDF-1.4 SINT")
    _elemento_visita(entorno, 1, medidas=OBRA_COMPLETA)
    _diseno()
    antes = _arbol(entorno["tmp"] / "dropbox")
    _, eventos = _procesar()
    estado = next(d for d in _abiertas() if d["campo_afectado"] == "estado")
    assert stp.name in estado["descripcion_pregunta"] and estado["id_elemento"] == ""
    assert json.loads(_visita()["origen_datos_json"])["stp_candidatos"] == [[stp.name]]
    assert not any(e["tipo"] == "pdf_generado" for e in eventos)
    assert _arbol(entorno["tmp"] / "dropbox") == antes  # Dropbox solo lectura


def test_visita_mixta_y_cabecera_vacia_son_dudas_de_la_visita(entorno):
    _elemento_visita(entorno, 1)
    _diseno()
    with _bd() as conn:
        conn.execute("UPDATE visitas SET clase = 'Mixta' WHERE id = ?", (VID,))
        conn.execute("UPDATE proyectos SET residente_obra = '' WHERE id = ?", (PID,))
    _procesar()
    campos = {d["campo_afectado"]: d for d in _abiertas()}
    assert "procesador:clase" in campos and "residente_obra" in campos["proyecto:cabecera"]["descripcion_pregunta"]
    with _bd() as conn:  # Steven llena la cabecera: la duda propia se recalcula y se cierra sola
        conn.execute("UPDATE proyectos SET residente_obra = 'RESIDENTE SINT' WHERE id = ?", (PID,))
        conn.execute("UPDATE visitas SET estado = 'Sin procesar' WHERE id = ?", (VID,))
    _procesar()
    assert "proyecto:cabecera" not in {d["campo_afectado"] for d in _abiertas()}


def test_catdic_stp_se_omite_con_aviso(entorno):
    _elemento_visita(entorno, 1)
    _diseno()
    with _bd() as conn:
        conn.execute("""UPDATE visitas SET formatos_solicitados = '["STP-MIVED", "CATDIC-STP"]' WHERE id = ?""", (VID,))
    _, eventos = _procesar()
    assert any(e["tipo"] == "aviso" and "CATDIC-STP" in e["texto"] for e in eventos)
    assert "procesador:formatos" not in {d["campo_afectado"] for d in _abiertas()}


# ---------- Generación y cierre ----------

def test_visita_completa_queda_procesada_con_su_stp(entorno, monkeypatch):
    _exigir_chromium()
    monkeypatch.setattr(pc, "MAPEO_DISENO_A_STP", MAPEO_SINT)
    _elemento_visita(entorno, 1, medidas=OBRA_COMPLETA)
    _diseno()
    antes = _arbol(entorno["tmp"] / "dropbox")
    t, eventos = _procesar()
    pdf = [e for e in eventos if e["tipo"] == "pdf_generado"]
    assert len(pdf) == 1 and pdf[0]["con_dudas"] is False
    ruta = Path(pdf[0]["ruta"])
    assert ruta.name == "Obra Sintetica - STP - LOSA S-4 Completivo - 02-10-2026.pdf"
    assert ruta.parent == entorno["tmp"] / "salida" and ruta.stat().st_size < 30_000_000
    assert not (entorno["tmp"] / "salida" / pc.CARPETA_DE_PASO).exists()
    v = _visita()
    assert v["estado"] == "Procesada" and json.loads(v["salida_json"])["procesador"][0]["ruta"] == str(ruta)
    assert _abiertas() == [] and t["resumen"]["pdf"][0]["ruta"] == str(ruta)
    assert _arbol(entorno["tmp"] / "dropbox") == antes
    # Una segunda corrida (tras volver a la cola) no sobrescribe: v2
    with _bd() as conn:
        conn.execute("UPDATE visitas SET estado = 'Sin procesar' WHERE id = ?", (VID,))
    _, eventos = _procesar()
    assert Path(next(e for e in eventos if e["tipo"] == "pdf_generado")["ruta"]).name.endswith("02-10-2026 v2.pdf")


def test_sin_datos_de_obra_el_pdf_se_nombra_con_dudas_y_la_visita_no_se_procesa(entorno, monkeypatch):
    _exigir_chromium()
    monkeypatch.setattr(pc, "MAPEO_DISENO_A_STP", MAPEO_SINT)
    _elemento_visita(entorno, 1)  # sin medidas ni columna OBRA
    _diseno()
    _, eventos = _procesar()
    pdf = next(e for e in eventos if e["tipo"] == "pdf_generado")
    assert pdf["con_dudas"] is True and Path(pdf["ruta"]).name.endswith(" - 02-10-2026 - CON DUDAS.pdf")
    obra = next(d for d in _abiertas() if d["campo_afectado"] == "obra:p001")
    assert "OBRA" in obra["descripcion_pregunta"]
    assert _visita()["estado"] == "Con dudas" and json.loads(_visita()["salida_json"]) == {}


def test_un_error_en_una_visita_no_detiene_el_trabajo(entorno, monkeypatch):
    _elemento_visita(entorno, 1)
    _diseno()
    with _bd() as conn:
        conn.execute("""INSERT INTO visitas (id, proyecto_id, numero, nombre_carpeta, ruta_carpeta, fecha_visita, clase,
                        estado, formatos_solicitados, actualizado) VALUES ('otra', ?, 19, '19. OTRA S-4 PARCIAL 03-10-2026',
                        'x', '2026-10-03', 'Parcial', 'Sin procesar', '["STP-MIVED"]', 'x')""", (PID,))
    original = pc.ProcesoVisita._procesar

    def falla(self, visita):
        if self.visita_id == VID:
            raise RuntimeError("fallo SINTÉTICO")
        return original(self, visita)
    monkeypatch.setattr(pc.ProcesoVisita, "_procesar", falla)
    t = pc.lanzar_trabajo([VID, "otra"], tipo="cola", en_hilo=False, usuario="prueba")
    t = pc.obtener_trabajo(t["id"])
    assert t["estado"] == "fallido" and "fallo SINTÉTICO" in t["error"]
    assert [v["visita_id"] for v in t["resumen"]["visitas"]] == [VID, "otra"]
    assert _visita()["estado"] == "Sin procesar"  # vuelve al estado que tenía


# ---------- API ----------

@pytest.fixture
def cliente(entorno):
    with TestClient(main.app) as c:
        yield c


def test_api_lanza_el_trabajo_y_entrega_los_eventos_desde_n(cliente, entorno):
    _elemento_visita(entorno, 1)
    _diseno(confirmado=False)
    r = cliente.post(f"/api/visitas/{VID}/procesar")
    assert r.status_code == 202
    tid = r.json()["trabajo"]["id"]
    pc.esperar(tid, 60)
    t = cliente.get(f"/api/trabajos/{tid}").json()
    assert t["estado"] == "terminado" and t["visitas"] == [VID] and t["eventos"] >= 5
    todos = cliente.get(f"/api/trabajos/{tid}/eventos").json()
    assert [e["n"] for e in todos["eventos"]] == list(range(1, t["eventos"] + 1))
    resto = cliente.get(f"/api/trabajos/{tid}/eventos", params={"desde": 3}).json()
    assert [e["n"] for e in resto["eventos"]] == list(range(4, t["eventos"] + 1)) and resto["ultimo"] == t["eventos"]
    assert {"visita_inicio", "elemento_inicio", "duda", "visita_fin", "fin"} <= {e["tipo"] for e in todos["eventos"]}
    with _bd() as conn:
        acciones = {f[0] for f in conn.execute("SELECT accion FROM auditoria WHERE modulo = 'PROCESADOR'")}
    assert {"LANZAR_TRABAJO", "ABRIR_DUDA", "PROCESAR_VISITA", "TERMINAR_TRABAJO"} <= acciones


def test_api_errores_404_y_409(cliente, entorno):
    assert cliente.post("/api/visitas/no-existe/procesar").status_code == 404
    assert cliente.get("/api/trabajos/no-existe").status_code == 404
    assert cliente.get("/api/trabajos/no-existe/eventos").status_code == 404
    with _bd() as conn:
        conn.execute("UPDATE visitas SET estado = 'Procesada' WHERE id = ?", (VID,))
    r = cliente.post(f"/api/visitas/{VID}/procesar")
    assert r.status_code == 409 and "Procesada" in r.json()["detail"]
    with _bd() as conn:
        conn.execute("UPDATE visitas SET estado = 'Sin procesar' WHERE id = ?", (VID,))
        conn.execute("""INSERT INTO trabajos (id, tipo, visitas_json, estado, usuario, creado)
                        VALUES ('trab-sint', 'visita', '[]', 'corriendo', 'prueba', 'x')""")
    r = cliente.post(f"/api/visitas/{VID}/procesar")
    assert r.status_code == 409 and "trab-sint" in r.json()["detail"]


def test_api_procesar_cola_toma_solo_sin_procesar_y_en_cola(cliente, entorno):
    with _bd() as conn:
        conn.execute("UPDATE visitas SET estado = 'Con dudas' WHERE id = ?", (VID,))
    r = cliente.post("/api/visitas/procesar-cola")
    assert r.status_code == 202 and r.json()["trabajo"] is None
    with _bd() as conn:
        conn.execute("UPDATE visitas SET estado = 'En cola' WHERE id = ?", (VID,))
    r = cliente.post("/api/visitas/procesar-cola", params={"proyecto_id": PID})
    t = pc.esperar(r.json()["trabajo"]["id"], 60)
    assert t["tipo"] == "cola" and t["visitas"] == [VID] and t["estado"] == "terminado", t["error"]


def test_trabajos_huerfanos_al_arrancar(entorno):
    with _bd() as conn:
        conn.execute("""INSERT INTO trabajos (id, tipo, visitas_json, estado, usuario, creado)
                        VALUES ('trab-viejo', 'visita', ?, 'corriendo', 'prueba', 'x')""", (json.dumps([VID]),))
        conn.execute("UPDATE visitas SET estado = 'En proceso', origen_datos_json = ? WHERE id = ?",
                     (json.dumps({"procesador": {"trabajo": "trab-viejo", "estado_anterior": "Sin procesar"}}), VID))
    r = pc.marcar_huerfanos(usuario="prueba")
    assert r == {"trabajos": ["trab-viejo"], "visitas_restauradas": [VID]}
    assert pc.obtener_trabajo("trab-viejo")["estado"] == "fallido" and _visita()["estado"] == "Sin procesar"
    assert pc.marcar_huerfanos(usuario="prueba") == {"trabajos": [], "visitas_restauradas": []}


# ---------- O1 de T4b: el STP elegido en la Mesa debe seguir existiendo ----------

@pytest.mark.parametrize("existe", [True, False])
def test_o1_estado_tras_cerrar_bloqueantes_comprueba_el_stp(entorno, existe):
    stp = entorno["obra"] / "INFORMES" / "2.DATA PROCESADA" / "Obra Sintetica - STP - X Completivo - 02-10-2026.pdf"
    if existe:
        stp.write_bytes(b"%PDF-1.4 SINT")
    origen = {"estado_mesa": {"estado": "Procesada", "stp": [str(stp)]}, "stp_candidatos": [[stp.name]]}
    conn = database.get_connection()
    try:
        cambios = estado_tras_cerrar_bloqueantes(conn, VID, "Con dudas", origen)
        nuevas = conn.execute("SELECT * FROM dudas_y_hallazgos WHERE visita_id = ? AND campo_afectado = 'estado'",
                              (VID,)).fetchall()
    finally:
        conn.rollback()
        conn.close()
    if existe:
        assert cambios["estado"] == "Procesada" and not nuevas
    else:
        assert cambios == {} and len(nuevas) == 1 and "ya no está" in nuevas[0]["descripcion_pregunta"]
        assert "estado_mesa" not in origen and origen["estado_mesa_anulado"]["motivo"]
