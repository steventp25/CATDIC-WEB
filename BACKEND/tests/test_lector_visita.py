# BACKEND/tests/test_lector_visita.py
# Etapa 3 · T3 — Lector del PDF de visita -> elementos_visita (PLANES/etapa-3.md, T3;
# PLANES/etapa-3-reconocimiento-visita.md). PDF y fotos # SINTÉTICO generados en la prueba; las
# etiquetas de ejemplo son literales copiadas de las visitas REALES #17 y #20 (solo el texto).
import io
import json
import sqlite3

import pymupdf
import pytest
from PIL import Image

import config
import database
from reglas_ingenieria import PENDIENTE
from sync import lector_visita

CARPETA_17 = "17. COMPLETIVO VERTICALES S-4 28-09-2026"  # REAL: nombre de carpeta
VISITA_ID = "terra-living-17-completivo-verticales-s-4-28-09-2026"


def _jpeg(color=(120, 110, 100), tam=(768, 1024), ruido=False):
    buffer = io.BytesIO()
    imagen = Image.effect_noise(tam, 80).convert("RGB") if ruido else Image.new("RGB", tam, color)
    imagen.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _pdf_visita(ruta, paginas, ancho=612, alto=792, solo_texto_extra=None):
    """
    paginas: lista de dicts {etiqueta, nota, color, rotar}. Una foto por página, la etiqueta (12 pt
    negrita), 'Creado el:' (10 pt negrita) y la nota (10 pt) bajo la foto, como en los PDF reales.
    """
    doc = pymupdf.open()
    for i, p in enumerate(paginas, start=1):
        hoja = doc.new_page(width=ancho, height=alto)
        hoja.insert_text((56, 30), "Contacto: SINTETICO", fontname="hebo", fontsize=10)
        hoja.insert_text((283, 30), "Creado el: vie, 2/10/2026", fontname="hebo", fontsize=10)  # cabecera: no cuenta
        rect = pymupdf.Rect(56, 68, 400, 678) if p.get("lado") else pymupdf.Rect(56, 99, 465, 644)
        hoja.insert_image(rect, stream=_jpeg(p.get("color", (120, 110, 100)), (3000, 2000) if p.get("ruido") else ((688, 1220) if p.get("lado") else (768, 1024)),
                                       ruido=p.get("ruido", False)),
                          rotate=p.get("rotar", 0))
        if p.get("lado"):  # foto apaisada de la #18: 'Creado' / 'el:' / fecha A LA DERECHA de la foto
            hoja.insert_text((407, 80), "Creado", fontname="hebo", fontsize=10)
            hoja.insert_text((407, 92), "el:", fontname="hebo", fontsize=10)
            hoja.insert_text((465, 80), "vie, 2/10/2026", fontname="helv", fontsize=10)
            continue
        hoja.insert_image(pymupdf.Rect(56, 25, 100, 70), stream=_jpeg((5, 5, 5), (64, 64)))  # logo
        y = 660
        if p.get("etiqueta"):
            hoja.insert_text((56, y), p["etiqueta"], fontname="hebo", fontsize=12)
            y += 20
        if p.get("hora_junta"):  # #20: un solo texto
            hoja.insert_text((56, y), f"Creado el: 28/09/2026 11:{i:02d}", fontname="hebo", fontsize=10)
        else:  # #17: 'Creado el:' y la hora son líneas distintas a la misma altura
            hoja.insert_text((56, y), "Creado el:", fontname="hebo", fontsize=10)
            hoja.insert_text((117, y), f"28/09/2026 11:{i:02d}", fontname="helv", fontsize=10)
        if p.get("nota"):
            hoja.insert_text((56, y + 16), p["nota"], fontname="helv", fontsize=10)
        hoja.insert_text((480, 760), f"Id. de doc. 29 pagina {i} de {len(paginas)}", fontname="helv", fontsize=10)
    doc.save(str(ruta))
    doc.close()
    return ruta


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """BD, Dropbox y caché temporales, con una visita sembrada (SINTÉTICA) que apunta al PDF."""
    (tmp_path / "bd").mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "catdic_prueba.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(lector_visita.ENV_CACHE_RAIZ, str(tmp_path / "cache"))
    database.inicializar_bd()
    conn = database.get_connection()
    conn.execute("INSERT INTO proyectos (id, nombre, tipo, formato_defecto, actualizado) "
                 "VALUES ('terra-living','Terra Living','Supervisión','STP-MIVED','x')")
    conn.execute("""INSERT INTO visitas (id, proyecto_id, numero, nombre_carpeta, ruta_carpeta, fecha_visita,
                    clase, estado, formatos_solicitados, actualizado) VALUES (?, 'terra-living', 17, ?, ?,
                    '2026-09-28', 'Completivo', 'Sin procesar', '["STP-MIVED"]', 'x')""",
                 (VISITA_ID, CARPETA_17, str(tmp_path / "dropbox" / CARPETA_17)))
    conn.commit()
    conn.close()
    return tmp_path


def _bd():
    conn = sqlite3.connect(config.obtener_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _filas():
    with _bd() as c:
        return [dict(f) for f in c.execute("SELECT * FROM elementos_visita ORDER BY orden_en_log")]


def _dudas():
    with _bd() as c:
        return [dict(f) for f in c.execute("SELECT * FROM dudas_y_hallazgos ORDER BY id")]


PAGINAS = [  # etiquetas literales de la #17 REAL
    {"etiqueta": "Mh4"}, {}, {}, {"etiqueta": "Mh1 pantalla eje 3"}, {}, {"etiqueta": "Pantalla eje B"}, {},
]


# ---------- Lectura ----------

def test_lee_etiquetas_notas_y_orden_de_paginas(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [
        {"etiqueta": "P eje C corregir Peralte de 0.60 a 0.70m", "nota": "Conforme. Ing de obra se realizó un cambio."},
        {}, {"etiqueta": "L5"}])
    p = lector_visita.leer_pdf_visita(pdf)
    assert [x["pagina"] for x in p] == [1, 2, 3]
    assert p[0]["etiqueta"] == "P eje C corregir Peralte de 0.60 a 0.70m"
    assert p[0]["nota"] == "Conforme. Ing de obra se realizó un cambio."  # tal cual, sin convertir a número
    assert p[1]["etiqueta"] == "" and p[1]["nota"] == ""
    assert p[2]["etiqueta"] == "L5" and p[0]["hora"] == "28/09/2026 11:01"


@pytest.mark.parametrize("junta", [False, True])
def test_b1_la_hora_se_toma_por_su_altura_no_se_confunde_con_la_nota(entorno, junta):
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "Mh4", "hora_junta": junta},
                                          {"hora_junta": junta, "nota": "texto libre"}])
    p = lector_visita.leer_pdf_visita(pdf)
    assert [x["hora"] for x in p] == ["28/09/2026 11:01", "28/09/2026 11:02"]
    assert p[0]["nota"] == "" and p[1]["nota"] == "texto libre"


def test_b2_creado_el_a_la_derecha_de_una_foto_apaisada_en_lineas_partidas(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{"lado": True}, {"etiqueta": "Tramo C-D"}, {"lado": True}])
    p = lector_visita.leer_pdf_visita(pdf)
    assert [x["pagina"] for x in p] == [1, 2, 3]
    assert [x["etiqueta"] for x in p] == ["", "Tramo C-D", ""]
    assert p[0]["hora"] == "vie, 2/10/2026" and p[0]["nota"] == ""  # no se cuenta la cabecera
    assert p[0]["foto_bbox"][3] > 600


def test_b2_la_cabecera_sola_no_cuenta_como_creado_el(entorno):
    doc = pymupdf.open()
    hoja = doc.new_page(width=595, height=841)
    hoja.insert_image(pymupdf.Rect(56, 68, 400, 678), stream=_jpeg())
    hoja.insert_text((283, 30), "Creado el: vie, 2/10/2026", fontname="hebo", fontsize=10)  # solo en la cabecera
    doc.save(str(entorno / "sin.pdf"))
    doc.close()
    with pytest.raises(ValueError, match="sin 'Creado el:'"):
        lector_visita.leer_pdf_visita(entorno / "sin.pdf")


def test_la_foto_principal_es_la_grande_no_el_logo(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "L1"}])
    bbox = lector_visita.leer_pdf_visita(pdf)[0]["foto_bbox"]
    assert (bbox[2] - bbox[0]) > 300  # la foto de 409 pt, no el logo de 44 pt


def test_pdf_que_no_es_de_visita_se_rechaza(entorno):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Plano estructural sintetico")
    doc.save(str(entorno / "plano.pdf"))
    doc.close()
    with pytest.raises(ValueError, match="no tiene la estructura de una visita"):
        lector_visita.leer_pdf_visita(entorno / "plano.pdf")


# ---------- Interpretación sin adivinar ----------

@pytest.mark.parametrize("etiqueta,esperado", [
    ("A1", ("pendiente de verificar", "EJE A-1")),            # cruce: el orden letra/número se acepta
    ("1A", ("pendiente de verificar", "EJE A-1")),
    ("C1 A4", ("C1", "EJE A-4")),                              # NORMA: CLAUDE.md §3.2 ejemplo ID + eje
    ("Mh4", (PENDIENTE, PENDIENTE)),                           # REAL #17: no es un cruce de ejes
    ("Tramo D-B", (PENDIENTE, PENDIENTE)),                     # REAL #18: el eje del pórtico no se deduce
    ("Mc eje A’ Tramo 3-4’", (PENDIENTE, PENDIENTE)),          # REAL #20: se normaliza la prima pero no es un cruce simple
    ("A’1", (PENDIENTE, "EJE A'-1")),                          # prima ’ normalizada a ' recta
    ("a'1", (PENDIENTE, "EJE A'-1")),
    ("c1 a4", ("C1", "EJE A-4")),                              # mayúsculas normalizadas
    ("mh4", (PENDIENTE, PENDIENTE)),                           # una sola letra de eje: Mh4 sigue pendiente
    ("Garantizar recubrimiento", (PENDIENTE, PENDIENTE)),
    ("", (PENDIENTE, PENDIENTE)),
])
def test_interpretar_etiqueta(etiqueta, esperado):
    r = lector_visita.interpretar_etiqueta(etiqueta)
    assert (r["id_elemento"], r["ejes"]) == esperado
    assert r["tipo_elemento"] == PENDIENTE  # el tipo nunca se deduce


def test_la_etiqueta_original_se_guarda_literal_aunque_se_normalice_para_interpretar(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "c1 a4"}, {"etiqueta": "Mh4"}])
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    filas = _filas()
    assert [f["etiqueta_original"] for f in filas] == ["c1 a4", "Mh4"]  # literal, en minúsculas
    assert (filas[0]["id_elemento"], filas[0]["ejes"]) == ("C1", "EJE A-4")
    assert len(_dudas()) == 1 and "'Mh4'" in _dudas()[0]["descripcion_pregunta"]  # la duda cita el literal


def test_armar_grupos_conserva_la_prima_tipografica_en_la_etiqueta():
    pagina = {"pagina": 1, "etiqueta": "Mc eje A’ Tramo 3-4’", "nota": "", "hora": None, "foto_bbox": (0, 0, 1, 1)}
    g = lector_visita.armar_grupos([pagina], CARPETA_17)[0]
    assert g["etiqueta_original"] == "Mc eje A’ Tramo 3-4’"  # con U+2019, sin normalizar
    assert (g["id_elemento"], g["ejes"]) == (PENDIENTE, PENDIENTE) and not g["reconocido"]
    assert "'Mc eje A’ Tramo 3-4’'" in lector_visita._texto_duda(g)


def test_nivel_solo_si_la_carpeta_trae_exactamente_uno():
    assert lector_visita.nivel_de_carpeta(CARPETA_17) == "S-4"
    assert lector_visita.nivel_de_carpeta("12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026") == "S-5"
    assert lector_visita.nivel_de_carpeta("13. LOSAS S-4 Y S-3") == PENDIENTE
    assert lector_visita.nivel_de_carpeta("3. VERTICALES SOTANO -7") == PENDIENTE


# ---------- Carga ----------

def test_carga_agrupa_guarda_literal_y_crea_una_duda_por_grupo(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", PAGINAS)
    r = lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf, usuario="prueba")
    filas = _filas()
    assert [(f["orden_en_log"], f["etiqueta_original"]) for f in filas] == [
        (1, "Mh4"), (4, "Mh1 pantalla eje 3"), (6, "Pantalla eje B")]
    assert [len(json.loads(f["fotos_json"])) for f in filas] == [3, 2, 2]
    assert all(f["id_elemento"] == PENDIENTE and f["tipo_elemento"] == PENDIENTE and f["ejes"] == PENDIENTE
               for f in filas)
    assert all(f["nivel"] == "S-4" for f in filas)
    dudas = _dudas()
    assert len(dudas) == 3  # UNA por grupo, no una por campo
    assert {d["categoria"] for d in dudas} == {"DUDA_BLOQUEANTE"} and {d["visita_id"] for d in dudas} == {VISITA_ID}
    assert "'Mh1 pantalla eje 3'" in dudas[1]["descripcion_pregunta"] and "Fotos de las páginas 4 a 5" in dudas[1]["descripcion_pregunta"]
    assert "abre un elemento nuevo" in dudas[1]["descripcion_pregunta"]
    assert dudas[2]["descripcion_pregunta"].startswith("Fotos de las páginas 6 a 7")
    assert r["grupos"] == 3 and r["paginas"] == 7


def test_primeras_fotos_sin_etiqueta_forman_un_grupo_pendiente_con_duda(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{}, {}, {"etiqueta": "L5"}])
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    filas = _filas()
    assert [(f["orden_en_log"], f["etiqueta_original"], f["id_elemento"]) for f in filas] == [
        (1, "", PENDIENTE), (3, "L5", PENDIENTE)]
    assert len(json.loads(filas[0]["fotos_json"])) == 2
    d = _dudas()[0]
    assert "no tienen etiqueta" in d["descripcion_pregunta"] and d["id_elemento"] == "(sin etiqueta)"


def test_grupo_de_una_sola_foto_usa_singular(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "L1"}, {"etiqueta": "L2"}])
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    assert _dudas()[0]["descripcion_pregunta"].startswith("Foto de la página 1 con la etiqueta literal 'L1'")


def test_a1_llena_ejes_y_queda_con_duda_por_el_id(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "A1"}])
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    f = _filas()[0]
    assert f["ejes"] == "EJE A-1" and f["id_elemento"] == PENDIENTE
    assert len(_dudas()) == 1  # el ID sigue sin saberse


def test_c1_a4_queda_reconocido_sin_duda(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "C1 A4"}, {}])
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    f = _filas()[0]
    assert (f["id_elemento"], f["ejes"]) == ("C1", "EJE A-4")
    assert _dudas() == []


@pytest.mark.parametrize("estado,esperado", [
    ("Sin procesar", "Con dudas"), ("En cola", "Con dudas"), ("Con dudas", "Con dudas"),
    ("Procesada", "Procesada"), ("En proceso", "En proceso"), ("En revisión", "En revisión"),
])
def test_o1_visita_abierta_con_bloqueantes_pasa_a_con_dudas_las_avanzadas_no(entorno, estado, esperado):
    with _bd() as c:
        c.execute("UPDATE visitas SET estado = ? WHERE id = ?", (estado, VISITA_ID))
    pdf = _pdf_visita(entorno / "v.pdf", PAGINAS)
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    with _bd() as c:
        assert c.execute("SELECT estado FROM visitas WHERE id = ?", (VISITA_ID,)).fetchone()[0] == esperado
        assert len(_dudas()) == 3


def test_o1_un_pdf_rechazado_tambien_pasa_la_visita_a_con_dudas(entorno):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Plano")
    doc.save(str(entorno / "plano.pdf"))
    doc.close()
    with pytest.raises(ValueError):
        lector_visita.cargar_visita(VISITA_ID, ruta_pdf=entorno / "plano.pdf")
    with _bd() as c:
        assert c.execute("SELECT estado FROM visitas WHERE id = ?", (VISITA_ID,)).fetchone()[0] == "Con dudas"


def test_o5_respalda_por_defecto_y_tambien_antes_de_rechazar(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", PAGINAS)
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)  # sin pasar respaldar
    respaldos = list((entorno / "bd").glob("catdic_prueba.backup-*.db"))
    assert len(respaldos) == 1
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Plano")
    doc.save(str(entorno / "plano.pdf"))
    doc.close()
    with pytest.raises(ValueError):
        lector_visita.cargar_visita(VISITA_ID, ruta_pdf=entorno / "plano.pdf")
    assert len(list((entorno / "bd").glob("catdic_prueba.backup-*.db"))) == 2  # el rechazo también respaldó


def test_actualiza_fotos_json_sin_duplicar_filas_ni_dudas_cuando_cambia_la_hora(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", PAGINAS)
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    with _bd() as c:  # simula la BD vieja de T3: hora nula y la hora guardada como nota
        for f in _filas():
            fotos = json.loads(f["fotos_json"])
            for foto in fotos:
                foto["nota"], foto["hora"] = foto["hora"], None
            c.execute("UPDATE elementos_visita SET fotos_json = ? WHERE uid = ?", (json.dumps(fotos), f["uid"]))
    r = lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    assert r["filas_nuevas"] == 0 and r["filas_actualizadas"] == 3 and r["dudas_nuevas"] == 0
    fotos = [x for f in _filas() for x in json.loads(f["fotos_json"])]
    assert all(x["hora"] and x["nota"] == "" for x in fotos) and len(fotos) == 7
    assert len(_filas()) == 3 and len(_dudas()) == 3


def test_nota_guardada_tal_cual_en_fotos_json(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "Garantizar recubrimiento", "nota": "1 cm más de eso 0.26"}])
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    foto = json.loads(_filas()[0]["fotos_json"])[0]
    assert foto["nota"] == "1 cm más de eso 0.26" and foto["etiqueta"] == "Garantizar recubrimiento"
    assert foto["cache"] == f"terra-living/{VISITA_ID}/p001.jpg"


def test_segunda_corrida_no_duplica_filas_ni_dudas(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", PAGINAS)
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    antes = (_filas(), _dudas())
    r = lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    assert (_filas(), _dudas()) == antes
    assert r["filas_nuevas"] == 0 and r["sin_cambios"] == 3 and r["dudas_nuevas"] == 0


def test_pdf_que_no_es_de_visita_no_carga_nada_y_crea_una_duda(entorno):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Plano estructural sintetico")
    doc.save(str(entorno / "plano.pdf"))
    doc.close()
    with pytest.raises(ValueError, match="estructura de una visita"):
        lector_visita.cargar_visita(VISITA_ID, ruta_pdf=entorno / "plano.pdf")
    assert _filas() == []
    dudas = _dudas()
    assert len(dudas) == 1 and dudas[0]["campo_afectado"] == "lector_visita"
    with _bd() as c:
        assert c.execute("SELECT COUNT(*) FROM auditoria WHERE accion='RECHAZAR_PDF_VISITA'").fetchone()[0] == 1
    with pytest.raises(ValueError):  # repetir no duplica la duda
        lector_visita.cargar_visita(VISITA_ID, ruta_pdf=entorno / "plano.pdf")
    assert len(_dudas()) == 1


# ---------- Caché ----------

def test_cache_reducida_q72_orientada_y_mas_liviana_que_el_pdf(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "L1", "rotar": 90, "ruido": True}, {"etiqueta": "L2", "ruido": True}])
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    carpeta = entorno / "cache" / "terra-living" / VISITA_ID
    jpgs = sorted(carpeta.glob("p*.jpg"))
    assert [j.name for j in jpgs] == ["p001.jpg", "p002.jpg"]
    for j in jpgs:
        im = Image.open(j)
        assert im.format == "JPEG" and max(im.size) <= 1000
    assert sum(j.stat().st_size for j in jpgs) < pdf.stat().st_size
    # La foto se guarda como se ve en la página: la rotada 90° queda vertical y la otra, horizontal
    w0, h0 = Image.open(jpgs[0]).size
    w1, h1 = Image.open(jpgs[1]).size
    assert h0 > w0 and w1 > h1


def test_cache_dentro_de_dropbox_se_rechaza(entorno, monkeypatch):
    monkeypatch.setenv(lector_visita.ENV_CACHE_RAIZ, str(entorno / "dropbox" / "cache"))
    pdf = _pdf_visita(entorno / "v.pdf", [{"etiqueta": "L1"}])
    with pytest.raises(ValueError, match="Dropbox"):
        lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    assert _filas() == [] and not (entorno / "dropbox").exists()


def test_cache_por_defecto_es_la_carpeta_del_usuario(monkeypatch):
    monkeypatch.delenv(lector_visita.ENV_CACHE_RAIZ, raising=False)
    ruta = lector_visita.obtener_cache_raiz()
    assert ruta.name == "CATDIC-CACHE" and ruta.parent == lector_visita.Path.home()


def test_no_toca_el_pdf_de_origen_ni_su_carpeta(entorno):
    pdf = _pdf_visita(entorno / "v.pdf", PAGINAS)
    antes = (pdf.read_bytes(), sorted(p.name for p in entorno.iterdir() if p.name != "cache" and p.name != "bd"))
    lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf)
    assert pdf.read_bytes() == antes[0]


# ---------- Auditoría y respaldo ----------

def test_auditoria_con_el_usuario_que_ejecuta_y_respaldo_opcional(entorno, monkeypatch):
    monkeypatch.setattr(lector_visita.getpass, "getuser", lambda: "usuario_sintetico")
    pdf = _pdf_visita(entorno / "v.pdf", PAGINAS)
    r = lector_visita.cargar_visita(VISITA_ID, ruta_pdf=pdf, respaldar=True)
    with _bd() as c:
        fila = c.execute("SELECT * FROM auditoria WHERE modulo='LECTOR_VISITA' AND accion='CARGAR_VISITA'").fetchone()
    assert fila["usuario"] == "usuario_sintetico" and fila["entidad_id"] == VISITA_ID
    detalle = json.loads(fila["detalle_json"])
    assert detalle["grupos"] == 3 and detalle["respaldo"] == r["respaldo"]
    assert list((entorno / "bd").glob("catdic_prueba.backup-*.db"))


def test_visita_inexistente_o_con_varios_pdf(entorno):
    with pytest.raises(LookupError):
        lector_visita.cargar_visita("no-existe")
    with pytest.raises(ValueError, match="0 PDF"):
        lector_visita.cargar_visita(VISITA_ID)  # la visita sembrada no tiene archivos_json
