# BACKEND/tests/test_visor.py
# Etapa 2 · T5n — Visor del vectorial y recuadros de LOCALIZACION / DETALLE (PLANES/etapa-2.md, T5n).
# Todo # SINTÉTICO: el vectorial se genera aquí con PyMuPDF (globos de eje, IDs, rótulos de detalle, una hoja girada).
import io
import json
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import config
import database
import main
import visor
from reglas_ingenieria import PENDIENTE

ROJO_PURO = (255, 0, 0)


def _globo(pag, cx, cy, texto, linea):
    pag.draw_circle((cx, cy), 9.5, color=(0, 0, 0), width=0.7)
    pag.insert_text((cx - 3 * len(texto), cy + 3), texto, fontsize=9)
    pag.draw_line((cx + linea[0] * 9.5, cy + linea[1] * 9.5), (cx + linea[0] * 66, cy + linea[1] * 66), color=(0, 0, 0), width=0.7)


def _numero_de_hoja(pag, nn):
    pag.insert_text((940, 770), nn, fontsize=14)
    pag.insert_text((958, 770), "/36", fontsize=14)


def _vectorial() -> bytes:
    doc = pymupdf.open()
    # Hoja 1 (hoja 05): planta con ejes A, B (fila) y 1, 2 (columna), con la línea del eje, y IDs
    p = doc.new_page(width=1000, height=800)
    _numero_de_hoja(p, "05")
    p.insert_text((60, 770), "PLANTA ESTRUCTURAL NIVEL 2", fontsize=15)
    for x, t in ((300, "A"), (420, "B")):
        _globo(p, x, 700, t, (0, -1))
    for y, t in ((300, "1"), (420, "2")):
        _globo(p, 100, y, t, (1, 0))
    p.insert_text((305, 305), "C1", fontsize=8)        # ID único: columna en el cruce A-1
    p.insert_text((600, 500), "L7", fontsize=8)        # ID único de una losa (sin cruce de ejes)
    p.insert_text((500, 200), "C5", fontsize=8)
    p.insert_text((700, 600), "C5", fontsize=8)        # ID repetido: ambiguo
    p.draw_rect(pymupdf.Rect(800, 100, 860, 150), color=None, fill=(1, 0, 0))   # marca roja para la prueba de conversión
    # Hoja 2 (hoja 06): dos detalles lado a lado con su rótulo debajo
    p = doc.new_page(width=1000, height=800)
    _numero_de_hoja(p, "06")
    for x0, nombre in ((100, "COLUMNA C1"), (500, "COLUMNA C2")):
        p.draw_rect(pymupdf.Rect(x0, 100, x0 + 150, 300), color=(0, 0, 0), width=1)
        p.draw_rect(pymupdf.Rect(x0 + 20, 120, x0 + 130, 280), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
        p.insert_text((x0 + 10, 330), nombre, fontsize=15)
    # Hoja 3 (hoja 07), GIRADA 270°: un rectángulo rojo en una posición conocida y un bloque verde para el detalle
    p = doc.new_page(width=1000, height=800)
    _numero_de_hoja(p, "07")
    p.draw_rect(pymupdf.Rect(200, 100, 320, 180), color=None, fill=(1, 0, 0))
    p.draw_rect(pymupdf.Rect(500, 300, 700, 420), color=None, fill=(0, 1, 0))
    p.set_rotation(270)
    datos = doc.tobytes()
    doc.close()
    return datos


def _sellado() -> bytes:
    doc = pymupdf.open()
    doc.new_page(width=300, height=200)
    datos = doc.tobytes()
    doc.close()
    return datos


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    (tmp_path / "bd").mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "prueba.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(config.ENV_DATOS_RAIZ, str(tmp_path / "datos"))
    monkeypatch.setenv(config.ENV_CACHE_RAIZ, str(tmp_path / "cache"))
    database.inicializar_bd()
    visor._indices.clear()
    with TestClient(main.app) as c:
        yield c, tmp_path


def _obra_con_plano(c):
    pid = c.post("/api/proyectos", json={"nombre": "Obra Visor"}).json()["proyecto"]["id"]
    r = c.post(f"/api/proyectos/{pid}/planos", files={"vectorial": ("vec.pdf", _vectorial(), "application/pdf"),
                                                       "sellado": ("sel.pdf", _sellado(), "application/pdf")},
               data={"certifico": "true"})
    assert r.status_code == 201, r.text
    return pid


def _elemento(pid, uid, id_elemento, ejes, hoja="05"):
    conn = database.get_connection()
    conn.execute("""INSERT INTO elementos_diseno (uid, proyecto_id, id_elemento, tipo_elemento, nivel_rango, ejes,
                    hoja_plano_origen, archivo_plano_origen, datos_diseno_json, estado_campos_json, actualizado)
                    VALUES (?, ?, ?, 'COLUMNA RECTANGULAR', 'S-1', ?, ?, 'vec.pdf', '{}', '{}', 'x')""",
                 (uid, pid, id_elemento, ejes, hoja))
    conn.commit()
    conn.close()


def _png(respuesta) -> Image.Image:
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.content[:8] == b"\x89PNG\r\n\x1a\n"
    return Image.open(io.BytesIO(respuesta.content)).convert("RGB")


def _caja_de_color(img: Image.Image, color, tol=40):
    """bbox (en px) de los píxeles de `color`; None si no hay."""
    px = img.load()
    xs, ys = [], []
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = px[x, y]
            if abs(r - color[0]) <= tol and abs(g - color[1]) <= tol and abs(b - color[2]) <= tol:
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs) + 1, max(ys) + 1) if xs else None


# ---------- Rasterizado y caché ----------

def test_la_hoja_se_rasteriza_con_su_dpi_y_se_guarda_en_la_cache_local(entorno):
    c, tmp = entorno
    pid = _obra_con_plano(c)
    info = c.get(f"/api/proyectos/{pid}/visor/hojas/1/info?dpi=72").json()
    assert (info["ancho_pt"], info["alto_pt"], info["rotacion"], info["ancho_px"]) == (1000.0, 800.0, 0, 1000)
    img = _png(c.get(f"/api/proyectos/{pid}/visor/hojas/1.png?dpi=72"))
    assert img.size == (1000, 800)
    en_cache = list((tmp / "cache").rglob("*.png"))
    assert len(en_cache) == 1 and en_cache[0].name == "p01-72.png"
    antes = en_cache[0].stat().st_mtime_ns
    c.get(f"/api/proyectos/{pid}/visor/hojas/1.png?dpi=72")
    assert en_cache[0].stat().st_mtime_ns == antes                    # segunda vez: se sirve de la caché
    assert _png(c.get(f"/api/proyectos/{pid}/visor/hojas/1.png?dpi=144")).size == (2000, 1600)


def test_hojas_dpi_y_obra_sin_plano_se_rechazan(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    assert c.get(f"/api/proyectos/{pid}/visor/hojas/9.png").status_code == 404
    assert c.get(f"/api/proyectos/{pid}/visor/hojas/1.png?dpi=5").status_code == 422
    assert c.get(f"/api/proyectos/{pid}/visor/hojas/1.png?dpi=900").status_code == 422
    vacia = c.post("/api/proyectos", json={"nombre": "Sin Plano"}).json()["proyecto"]["id"]
    r = c.get(f"/api/proyectos/{vacia}/visor/hojas/1.png")
    assert r.status_code == 409 and "plano vigente" in r.json()["detail"]
    assert c.get("/api/proyectos/no-existe/visor/hojas/1.png").status_code == 404


def test_la_cache_no_puede_estar_en_dropbox_ni_en_el_repo(entorno, monkeypatch):
    c, tmp = entorno
    pid = _obra_con_plano(c)
    repo = Path(config.__file__).resolve().parent.parent
    for malo in (tmp / "dropbox" / "cache", repo / "FABRICA" / "cache"):
        monkeypatch.setenv(config.ENV_CACHE_RAIZ, str(malo))
        r = c.get(f"/api/proyectos/{pid}/visor/hojas/1.png")
        assert r.status_code == 409 and ("Dropbox" in r.json()["detail"] or "repositorio" in r.json()["detail"])
        assert not malo.exists()


def test_indice_del_visor_trae_hoja_y_titulos_de_cada_pagina(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    d = c.get(f"/api/proyectos/{pid}/visor/indice").json()
    assert d["plano"]["paginas"] == 3 and [h["hoja"] for h in d["hojas"]] == ["05", "06", "07"]
    assert "PLANTA ESTRUCTURAL NIVEL 2" in d["hojas"][0]["titulos"] and d["hojas"][2]["rotacion"] == 270


# ---------- Conversión píxel ↔ punto ----------

def test_conversion_pixel_punto_ida_y_vuelta():
    for dpi in (30, 72, 150, 300):
        r = [10.5, 20.25, 300.0, 410.75]
        assert [round(v, 1) for v in visor.rect_px_a_pt(visor.rect_pt_a_px(r, dpi), dpi)] == [round(v, 1) for v in r]
    assert visor.pt_a_px(72, 150) == 150 and visor.px_a_pt(150, 150) == 72


@pytest.mark.parametrize("pagina,rect_sin_girar", [(1, None), (3, (200, 100, 320, 180))])
def test_un_objeto_conocido_cae_donde_dice_la_conversion_tambien_en_hoja_girada(entorno, pagina, rect_sin_girar):
    """Hoja 3 está girada 270°: el rectángulo rojo dibujado en (200,100,320,180) sin girar debe aparecer en el PNG en el
    rect obtenido con rotation_matrix, y px_a_pt del PNG debe devolver esos mismos puntos."""
    c, _ = entorno
    pid = _obra_con_plano(c)
    if rect_sin_girar is None:                                   # hoja 1: marca roja, sin giro
        esperado, color = [800, 100, 860, 150], ROJO_PURO
    else:
        with pymupdf.Document(stream=_vectorial(), filetype="pdf") as doc:
            r = pymupdf.Rect(rect_sin_girar) * doc[pagina - 1].rotation_matrix
        esperado, color = [r.x0, r.y0, r.x1, r.y1], ROJO_PURO
    dpi = 144
    img = _png(c.get(f"/api/proyectos/{pid}/visor/hojas/{pagina}.png?dpi={dpi}"))
    caja = _caja_de_color(img, color)
    obtenido = visor.rect_px_a_pt(caja, dpi)
    assert all(abs(a - b) <= 1.5 for a, b in zip(obtenido, esperado)), (obtenido, esperado)
    if rect_sin_girar:
        info = c.get(f"/api/proyectos/{pid}/visor/hojas/{pagina}/info?dpi={dpi}").json()
        assert (info["ancho_pt"], info["alto_pt"]) == (800.0, 1000.0)      # el marco visual de la hoja girada


# ---------- Propuestas ----------

def test_localizacion_se_propone_en_el_cruce_de_los_globos_con_su_fuente_y_pendiente(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    _elemento(pid, "u1", "C1", "EJE A-1")
    p = c.post(f"/api/proyectos/{pid}/elementos/u1/propuesta").json()["localizacion"]
    assert p["estado"] == PENDIENTE and p["pagina"] == 1 and p["fuente"]["metodo"] == "cruce_de_ejes"
    x0, y0, x1, y1 = p["rect"]
    assert abs((x0 + x1) / 2 - 300) < 1 and abs((y0 + y1) / 2 - 300) < 1          # x del globo A, y del globo 1
    assert p["fuente"]["archivo"] == "vec.pdf" and p["fuente"]["hoja"] == "05" and p["fuente"]["globo_letra"]


def test_sin_cruce_de_ejes_se_usa_el_bbox_del_id_si_es_unico(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    _elemento(pid, "u2", "L7", "—")
    p = c.post(f"/api/proyectos/{pid}/elementos/u2/propuesta").json()["localizacion"]
    assert p["fuente"]["metodo"] == "bbox_id" and p["estado"] == PENDIENTE
    assert p["rect"][0] < 600 < p["rect"][2] and p["rect"][1] < 500 < p["rect"][3]


@pytest.mark.parametrize("uid,id_,ejes,hoja,texto", [
    ("u3", "C5", "—", "05", "2 veces"),                 # ID repetido: no se adivina
    ("u4", "C9", "EJE A-1", "05", "0 veces"),           # el cruce existe pero el ID no está: sí hay cruce → propuesta; ver abajo
    ("u5", "C5", "EJE Z-9", "05", "no son únicos"),     # globos que no existen y el ID está repetido
    ("u6", "C1", "EJE A-1", "99", "No se pudo ubicar la hoja"),
])
def test_si_no_se_puede_proponer_queda_vacia_y_pendiente_con_motivo(entorno, uid, id_, ejes, hoja, texto):
    c, _ = entorno
    pid = _obra_con_plano(c)
    _elemento(pid, uid, id_, ejes, hoja)
    p = c.post(f"/api/proyectos/{pid}/elementos/{uid}/propuesta").json()["localizacion"]
    if uid == "u4":
        assert p["fuente"]["metodo"] == "cruce_de_ejes"       # el cruce no depende del ID: se propone igual, pendiente
        return
    assert p["rect"] is None and p["estado"] == PENDIENTE and texto in p["motivo"] and p["fuente"] is None


def test_detalle_se_propone_por_su_rotulo_sin_invadir_al_vecino(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    _elemento(pid, "u7", "C1", "EJE A-1")
    p = c.post(f"/api/proyectos/{pid}/elementos/u7/propuesta").json()["detalle"]
    assert p["estado"] == PENDIENTE and p["pagina"] == 2 and p["fuente"]["metodo"] == "rotulo"
    assert p["fuente"]["rotulo"] == "COLUMNA C1"
    x0, y0, x1, y1 = p["rect"]
    assert x0 <= 100 and x1 >= 250 and y0 <= 100 and y1 >= 330                    # abarca su dibujo y su rótulo
    assert x1 < 500                                                                   # no llega al detalle de C2
    _elemento(pid, "u8", "C9", "EJE A-1")
    vacia = c.post(f"/api/proyectos/{pid}/elementos/u8/propuesta").json()["detalle"]
    assert vacia["rect"] is None and vacia["estado"] == PENDIENTE and "C9" in vacia["motivo"]


def test_proponer_no_guarda_nada(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    _elemento(pid, "u9", "C1", "EJE A-1")
    c.post(f"/api/proyectos/{pid}/elementos/u9/propuesta")
    fila = database.get_connection().execute("SELECT recorte_planta_json, recorte_detalle_json FROM elementos_diseno WHERE uid='u9'").fetchone()
    assert (fila[0], fila[1]) == ("{}", "{}")
    assert c.post(f"/api/proyectos/{pid}/elementos/no-existe/propuesta").status_code == 404


# ---------- Guardar el recuadro ----------

def _guardar(c, pid, uid, **cambios):
    cuerpo = {"tipo": "localizacion", "pagina": 1, "rect": [250, 250, 350, 350], "origen": "corregido", **cambios}
    return c.put(f"/api/proyectos/{pid}/elementos/{uid}/recuadro", json=cuerpo)


def test_el_recuadro_confirmado_se_guarda_en_puntos_con_plano_pagina_y_auditoria(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    _elemento(pid, "u1", "C1", "EJE A-1")
    r = _guardar(c, pid, "u1")
    assert r.status_code == 200
    fila = database.get_connection().execute("SELECT recorte_planta_json, recorte_detalle_json FROM elementos_diseno WHERE uid='u1'").fetchone()
    g = json.loads(fila[0])
    assert g["rect"] == [250.0, 250.0, 350.0, 350.0] and g["pagina"] == 1 and g["origen"] == "corregido"
    assert g["estado"] == "confirmado" and g["confirmado_por"] and g["plano_id"] == 1 and json.loads(fila[1]) == {}
    # segunda vez: la auditoría trae el valor anterior y el nuevo
    _guardar(c, pid, "u1", rect=[260, 260, 360, 360], origen="dibujado")
    a = database.get_connection().execute("SELECT usuario, detalle_json FROM auditoria WHERE accion='GUARDAR_RECUADRO' ORDER BY id").fetchall()
    d = json.loads(a[-1]["detalle_json"])
    assert len(a) == 2 and a[-1]["usuario"] and d["anterior"]["rect"] == [250.0, 250.0, 350.0, 350.0]
    assert d["nuevo"]["rect"] == [260.0, 260.0, 360.0, 360.0] and d["recuadro"] == "localizacion"
    r = _guardar(c, pid, "u1", tipo="detalle", rect=[100, 100, 250, 300], pagina=2)
    assert json.loads(database.get_connection().execute("SELECT recorte_detalle_json FROM elementos_diseno WHERE uid='u1'").fetchone()[0])["pagina"] == 2


@pytest.mark.parametrize("cambios,texto", [
    ({"rect": [900, 700, 1200, 900]}, "no cabe"), ({"rect": [10, 10, 12, 12]}, "pequeño"), ({"rect": [50, 50, 20, 80]}, "no cabe"),
    ({"rect": [1, 2, 3]}, "x0, y0, x1, y1"), ({"pagina": 9}, "no existe"), ({"tipo": "otro"}, "tipo de recuadro"),
    ({"origen": "adivinado"}, "origen")])
def test_recuadros_invalidos_no_se_guardan(entorno, cambios, texto):
    c, _ = entorno
    pid = _obra_con_plano(c)
    _elemento(pid, "u1", "C1", "EJE A-1")
    r = _guardar(c, pid, "u1", **cambios)
    assert r.status_code in (404, 422) and texto in r.json()["detail"]
    assert database.get_connection().execute("SELECT recorte_planta_json FROM elementos_diseno WHERE uid='u1'").fetchone()[0] == "{}"


# ---------- Vista previa con los generadores de la Etapa 3 ----------

def _previa(c, pid, tipo, pagina, rect):
    return c.post(f"/api/proyectos/{pid}/visor/vista-previa", json={"tipo": tipo, "pagina": pagina, "rect": rect})


@pytest.mark.parametrize("pagina,rect", [(1, [250, 250, 350, 350]), (3, [100, 50, 400, 300])])
def test_la_vista_previa_de_localizacion_dibuja_el_recuadro_en_la_misma_posicion_tambien_girada(entorno, pagina, rect):
    c, _ = entorno
    pid = _obra_con_plano(c)
    img = _png(_previa(c, pid, "localizacion", pagina, rect))
    info = c.get(f"/api/proyectos/{pid}/visor/hojas/{pagina}/info").json()
    assert abs(img.width / img.height - info["ancho_pt"] / info["alto_pt"]) < 0.01     # planta COMPLETA, no un zoom
    caja = _caja_de_color(img, (220, 0, 0), tol=30)
    assert caja is not None
    esperado = [rect[0] / info["ancho_pt"], rect[1] / info["alto_pt"], rect[2] / info["ancho_pt"], rect[3] / info["alto_pt"]]
    obtenido = [caja[0] / img.width, caja[1] / img.height, caja[2] / img.width, caja[3] / img.height]
    assert all(abs(a - b) < 0.012 for a, b in zip(obtenido, esperado)), (obtenido, esperado)


def test_la_vista_previa_de_detalle_recorta_exactamente_la_region(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    # hoja 3 girada: el bloque verde dibujado en (500,300,700,420) sin girar es la región visual obtenida con la matriz
    with pymupdf.Document(stream=_vectorial(), filetype="pdf") as doc:
        r = pymupdf.Rect(500, 300, 700, 420) * doc[2].rotation_matrix
    region = [round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)]
    img = _png(_previa(c, pid, "detalle", 3, region))
    assert abs(img.width / img.height - (region[2] - region[0]) / (region[3] - region[1])) < 0.03
    verde = _caja_de_color(img, (0, 255, 0), tol=40)
    assert verde is not None and (verde[2] - verde[0]) * (verde[3] - verde[1]) > 0.97 * img.width * img.height   # todo es el bloque


def test_vista_previa_invalida_se_rechaza(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    assert _previa(c, pid, "detalle", 1, [10, 10, 40, 40]).status_code == 422       # recorte ilegible (< 200 px)
    assert _previa(c, pid, "localizacion", 1, [900, 700, 1200, 900]).status_code == 422
    assert _previa(c, pid, "otro", 1, [10, 10, 100, 100]).status_code == 422
    assert _previa(c, "no-existe", "detalle", 1, [10, 10, 100, 100]).status_code == 404


def test_listar_elementos_con_sus_recuadros(entorno):
    c, _ = entorno
    pid = _obra_con_plano(c)
    _elemento(pid, "u1", "C1", "EJE A-1")
    _guardar(c, pid, "u1")
    e = c.get(f"/api/proyectos/{pid}/elementos").json()["elementos"]
    assert len(e) == 1 and e[0]["recorte_planta"]["rect"] == [250.0, 250.0, 350.0, 350.0] and e[0]["recorte_detalle"] == {}
