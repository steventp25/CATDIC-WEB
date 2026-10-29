# BACKEND/visor.py
# Etapa 2 · T5n — Visor del plano vectorial y recuadros de LOCALIZACION / DETALLE (PLANES/etapa-2.md, T5n).
#
# - El visor muestra la hoja del VECTORIAL vigente (T4n) rasterizada a un dpi dado y guardada en una caché local
#   (config.obtener_cache_raiz: fuera del repo y de Dropbox).
# - El programa PROPONE los dos recuadros de un elemento; toda propuesta lleva su fuente y queda `pendiente de
#   verificar`. Si no se puede proponer, queda VACÍA y pendiente, con el motivo: nunca se adivina (Regla de Oro #1).
# - El usuario confirma, corrige o dibuja el recuadro. Se guarda en elementos_diseno.recorte_planta_json /
#   recorte_detalle_json como {plano_id, pagina, rect, ...} con auditoría (usuario, valor anterior y nuevo).
# - Marco de coordenadas: PUNTOS del PDF (1 pt = 1/72 in) en el marco VISUAL de la hoja (con la rotación aplicada,
#   el mismo del lector de planos y del rasterizado); `pagina` es el número de página del PDF desde 1.
import io
import json
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

import pymupdf
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

import config
from database import get_connection
from generators.comun import detalle as m4_detalle
from generators.comun import localizacion as m3_localizacion
from obras import ErrorObra, _auditar, _proyecto, _transaccion, _usuario, _ahora
from plano import lector_plano
from reglas_ingenieria import PENDIENTE

router = APIRouter()

DPI_MIN, DPI_MAX, DPI_DEFECTO = 30, 300, 60
CELDA_VISTA_PREVIA = (750, 520)     # la celda de LOCALIZACION / DETALLE de la hoja fotográfica del STP-MIVED
MARGEN_CRUCE_PT = 45.0              # medio lado del recuadro propuesto en el cruce de ejes
MARGEN_ID_PT = 20.0                 # holgura alrededor del bbox de un ID
LADO_MINIMO_PT = 5.0
TIPOS_RECUADRO = {"localizacion": "recorte_planta_json", "detalle": "recorte_detalle_json"}
_RE_EJE_PUNTUAL = re.compile(r"^EJE\s+([A-Z]'?)-(\d{1,2}'?)$")
_candado_indice = threading.Lock()
_indices: Dict[int, List[Dict]] = {}   # plano_id -> índice de hojas (el vectorial de un plano no cambia)


# ---------- Conversión píxel ↔ punto ----------

def pt_a_px(valor_pt: float, dpi: float) -> float:
    return valor_pt * dpi / 72.0


def px_a_pt(valor_px: float, dpi: float) -> float:
    return valor_px * 72.0 / dpi


def rect_px_a_pt(rect_px, dpi: float) -> List[float]:
    return [round(px_a_pt(v, dpi), 2) for v in rect_px]


def rect_pt_a_px(rect_pt, dpi: float) -> List[float]:
    return [pt_a_px(v, dpi) for v in rect_pt]


# ---------- Plano vigente y hojas ----------

def _plano_vigente(conn, proyecto_id: str):
    _proyecto(conn, proyecto_id)
    fila = conn.execute("SELECT * FROM planos WHERE proyecto_id = ? AND estado = 'vigente'", (proyecto_id,)).fetchone()
    if fila is None:
        raise ErrorObra("La obra no tiene plano vigente: sube primero el vectorial y el sellado.", 409)
    if not Path(fila["vectorial_ruta"]).is_file():
        raise ErrorObra("El archivo del vectorial vigente no está en la carpeta de datos.", 409)
    return fila


def _validar_pagina(plano, pagina: int):
    if not 1 <= pagina <= plano["vectorial_paginas"]:
        raise ErrorObra(f"La hoja {pagina} no existe: el vectorial tiene {plano['vectorial_paginas']} hojas.", 404)


def _dpi_valido(dpi: int) -> int:
    if not DPI_MIN <= dpi <= DPI_MAX:
        raise ErrorObra(f"El dpi debe estar entre {DPI_MIN} y {DPI_MAX}.")
    return int(dpi)


def info_hoja(proyecto_id: str, pagina: int, dpi: int = DPI_DEFECTO) -> Dict:
    conn = get_connection()
    try:
        plano = _plano_vigente(conn, proyecto_id)
    finally:
        conn.close()
    _validar_pagina(plano, pagina)
    dpi = _dpi_valido(dpi)
    with pymupdf.Document(plano["vectorial_ruta"]) as doc:
        r = doc[pagina - 1].rect
        rot = doc[pagina - 1].rotation
    return {"plano_id": plano["id"], "pagina": pagina, "ancho_pt": round(r.width, 2), "alto_pt": round(r.height, 2),
            "rotacion": rot, "dpi": dpi, "ancho_px": round(pt_a_px(r.width, dpi)), "alto_px": round(pt_a_px(r.height, dpi))}


def rasterizar_hoja(proyecto_id: str, pagina: int, dpi: int = DPI_DEFECTO) -> Path:
    """PNG de la hoja del vectorial vigente en la caché local (se crea una vez por plano, hoja y dpi)."""
    conn = get_connection()
    try:
        plano = _plano_vigente(conn, proyecto_id)
    finally:
        conn.close()
    _validar_pagina(plano, pagina)
    dpi = _dpi_valido(dpi)
    try:
        carpeta = config.obtener_cache_raiz() / proyecto_id / f"plano-{plano['id']}"
    except config.CarpetaDatosInvalida as exc:
        raise ErrorObra(str(exc), 409) from None
    destino = carpeta / f"p{pagina:02d}-{dpi}.png"
    if destino.is_file():
        return destino
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp.png")
    with pymupdf.Document(plano["vectorial_ruta"]) as doc:
        doc[pagina - 1].get_pixmap(dpi=dpi, alpha=False).save(str(temporal))
    temporal.replace(destino)
    return destino


def indice_del_plano(proyecto_id: str) -> Dict:
    conn = get_connection()
    try:
        plano = _plano_vigente(conn, proyecto_id)
    finally:
        conn.close()
    with _candado_indice:
        if plano["id"] not in _indices:
            _indices[plano["id"]] = lector_plano.indice_hojas(plano["vectorial_ruta"])
        hojas = _indices[plano["id"]]
    return {"plano": {"id": plano["id"], "revision": plano["revision"], "paginas": plano["vectorial_paginas"]},
            "hojas": [{"pagina": h["pagina"], "hoja": h["hoja"], "rotacion": h["rotacion"],
                       "titulos": [t["texto"] for t in h["titulos"]]} for h in hojas]}


# ---------- Elementos ----------

def listar_elementos(proyecto_id: str) -> List[Dict]:
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
        filas = conn.execute("""SELECT uid, id_elemento, tipo_elemento, nivel_rango, ejes, hoja_plano_origen, plano_id,
                                revisar_motivo, recorte_planta_json, recorte_detalle_json
                                FROM elementos_diseno WHERE proyecto_id = ? ORDER BY id_elemento""", (proyecto_id,)).fetchall()
    finally:
        conn.close()
    out = []
    for f in filas:
        d = dict(f)
        d["recorte_planta"] = json.loads(d.pop("recorte_planta_json") or "{}")
        d["recorte_detalle"] = json.loads(d.pop("recorte_detalle_json") or "{}")
        out.append(d)
    return out


def _elemento(conn, proyecto_id: str, uid: str):
    fila = conn.execute("SELECT * FROM elementos_diseno WHERE proyecto_id = ? AND uid = ?", (proyecto_id, uid)).fetchone()
    if fila is None:
        raise ErrorObra("Elemento no encontrado en esta obra.", 404)
    return fila


# ---------- Propuestas ----------

def _vacia(motivo: str) -> Dict:
    return {"rect": None, "pagina": None, "estado": PENDIENTE, "motivo": motivo, "fuente": None}


def _pagina_de_hoja(indice: List[Dict], hoja_origen: str) -> Optional[Dict]:
    m = re.search(r"\d+", hoja_origen or "")
    if not m:
        return None
    nn = str(int(m.group())).zfill(2)
    candidatas = [h for h in indice if h["hoja"] == nn]
    return candidatas[0] if len(candidatas) == 1 else None


def _centro(b):
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2


def _limitar(rect, pagina_rect) -> List[float]:
    x0, y0, x1, y1 = rect
    return [round(max(pagina_rect.x0, x0), 2), round(max(pagina_rect.y0, y0), 2),
            round(min(pagina_rect.x1, x1), 2), round(min(pagina_rect.y1, y1), 2)]


def _proponer_localizacion(doc, nombre, indice, elemento) -> Dict:
    h = _pagina_de_hoja(indice, elemento["hoja_plano_origen"])
    if h is None:
        return _vacia(f"No se pudo ubicar la hoja '{elemento['hoja_plano_origen']}' del elemento en el índice del vectorial.")
    pagina = h["pagina"]
    page_rect = doc[pagina - 1].rect
    ids = [i for i in lector_plano.ids_en_planta(doc, pagina) if i["texto"] == elemento["id_elemento"]]
    m = _RE_EJE_PUNTUAL.match(elemento["ejes"] or "")
    motivo_ejes = "el campo EJES no es un cruce puntual (EJE <LETRA>-<NÚMERO>)"
    if m:
        letra, numero = m.group(1), m.group(2)
        globos = lector_plano.globos_de_eje(doc, pagina)
        letras = [g for g in globos if g["texto"] == letra and g["orientacion"] == "fila"]
        numeros = [g for g in globos if g["texto"] == numero and g["orientacion"] == "columna"]
        if len(letras) == 1 and len(numeros) == 1:
            cx, cy = _centro(letras[0]["bbox"])[0], _centro(numeros[0]["bbox"])[1]
            rect = _limitar([cx - MARGEN_CRUCE_PT, cy - MARGEN_CRUCE_PT, cx + MARGEN_CRUCE_PT, cy + MARGEN_CRUCE_PT], page_rect)
            return {"rect": rect, "pagina": pagina, "estado": PENDIENTE, "motivo": None,
                    "fuente": {"metodo": "cruce_de_ejes", "archivo": nombre, "hoja": h["hoja"], "pagina": pagina,
                               "globo_letra": letras[0]["bbox"], "globo_numero": numeros[0]["bbox"]}}
        motivo_ejes = (f"los globos del eje {letra} y {numero} no son únicos en la hoja ({len(letras)} y {len(numeros)})")
    if len(ids) == 1:
        b = ids[0]["bbox"]
        rect = _limitar([b[0] - MARGEN_ID_PT, b[1] - MARGEN_ID_PT, b[2] + MARGEN_ID_PT, b[3] + MARGEN_ID_PT], page_rect)
        return {"rect": rect, "pagina": pagina, "estado": PENDIENTE, "motivo": None,
                "fuente": {"metodo": "bbox_id", "archivo": nombre, "hoja": h["hoja"], "pagina": pagina,
                           "bbox_id": b, "nota": f"sin cruce de ejes: {motivo_ejes}"}}
    return _vacia(f"Sin cruce de ejes ({motivo_ejes}) y el ID '{elemento['id_elemento']}' aparece {len(ids)} veces en la "
                  f"hoja {h['hoja']}: no se adivina.")


def _region_sobre_titulo(page, titulo_bbox, limite_hueco: float = 25.0, alto_max: float = 900.0) -> Optional[List[float]]:
    """Bloque contiguo de dibujo y texto justo encima de un rótulo: crece hacia arriba mientras no haya un hueco > 25 pt."""
    m = page.rotation_matrix
    tx0, ty0, tx1, _ = titulo_bbox
    banda = pymupdf.Rect(tx0 - 60, ty0 - alto_max, tx1 + 60, ty0 - 1)
    items = [pymupdf.Rect(d["rect"]) * m for d in page.get_drawings()]
    items += [l["rect"] for l in lector_plano._lineas(page)]
    items = [r for r in items if r.intersects(banda) and r.y1 <= ty0]
    if not items:
        return None
    items.sort(key=lambda r: -r.y1)
    region = pymupdf.Rect(items[0])
    for r in items[1:]:
        if r.y1 >= region.y0 - limite_hueco:
            region |= r
    region |= pymupdf.Rect(titulo_bbox)
    region = region & page.rect
    return None if region.is_empty else [round(v, 2) for v in region]


def _proponer_detalle(doc, nombre, indice, elemento) -> Dict:
    ident = re.escape(elemento["id_elemento"])
    hallados = [(h, t) for h in indice for t in h["titulos"] if t["tipo"] == "otro"
                and re.search(rf"(?<![A-Z0-9]){ident}(?![A-Z0-9])", t["texto"]) and not t["texto"].startswith("PLANTA")]
    if len(hallados) != 1:
        return _vacia(f"El rótulo del detalle de '{elemento['id_elemento']}' aparece {len(hallados)} veces en el vectorial: "
                      "no se adivina." if hallados else f"No hay un rótulo de detalle para '{elemento['id_elemento']}' en el vectorial.")
    h, t = hallados[0]
    region = _region_sobre_titulo(doc[h["pagina"] - 1], t["bbox"])
    if region is None:
        return _vacia(f"Se halló el rótulo '{t['texto']}' pero no hay dibujo encima de él.")
    return {"rect": region, "pagina": h["pagina"], "estado": PENDIENTE, "motivo": None,
            "fuente": {"metodo": "rotulo", "archivo": nombre, "hoja": h["hoja"], "pagina": h["pagina"],
                       "rotulo": t["texto"], "bbox_rotulo": t["bbox"]}}


def proponer_recuadros(proyecto_id: str, uid: str) -> Dict:
    """Propone LOCALIZACION y DETALLE del elemento; no guarda nada. Cada propuesta queda `pendiente de verificar`."""
    conn = get_connection()
    try:
        plano = _plano_vigente(conn, proyecto_id)
        elemento = dict(_elemento(conn, proyecto_id, uid))
    finally:
        conn.close()
    indice = indice_del_plano(proyecto_id)
    with _candado_indice:
        hojas = _indices[plano["id"]]
    with pymupdf.Document(plano["vectorial_ruta"]) as doc:
        nombre = plano["vectorial_archivo"]
        return {"uid": uid, "plano_id": plano["id"],
                "localizacion": _proponer_localizacion(doc, nombre, hojas, elemento),
                "detalle": _proponer_detalle(doc, nombre, hojas, elemento)}


# ---------- Guardar el recuadro confirmado ----------

def _validar_rect(plano, pagina: int, rect: List[float]) -> List[float]:
    _validar_pagina(plano, pagina)
    try:
        x0, y0, x1, y1 = [float(v) for v in rect]
    except (TypeError, ValueError):
        raise ErrorObra("El recuadro debe ser [x0, y0, x1, y1] en puntos.") from None
    with pymupdf.Document(plano["vectorial_ruta"]) as doc:
        hoja = doc[pagina - 1].rect
    if not (hoja.x0 - 0.5 <= x0 < x1 <= hoja.x1 + 0.5 and hoja.y0 - 0.5 <= y0 < y1 <= hoja.y1 + 0.5):
        raise ErrorObra(f"El recuadro {[x0, y0, x1, y1]} no cabe en la hoja {pagina} ({hoja.width:.0f} × {hoja.height:.0f} pt).")
    if min(x1 - x0, y1 - y0) < LADO_MINIMO_PT:
        raise ErrorObra(f"El recuadro es demasiado pequeño (menos de {LADO_MINIMO_PT:.0f} pt de lado).")
    return [round(max(hoja.x0, x0), 2), round(max(hoja.y0, y0), 2), round(min(hoja.x1, x1), 2), round(min(hoja.y1, y1), 2)]


def guardar_recuadro(proyecto_id: str, uid: str, tipo: str, pagina: int, rect: List[float], origen: str,
                     usuario: Optional[str] = None) -> Dict:
    """
    Guarda el recuadro que el usuario confirma, corrige o dibuja (`origen`: confirmado | corregido | dibujado) como
    {plano_id, pagina, rect, origen, estado: 'confirmado', confirmado_por, confirmado_en}, con auditoría (usuario,
    valor anterior y nuevo). El recuadro queda atado al plano vigente en ese momento.
    """
    usuario = usuario or _usuario()
    if tipo not in TIPOS_RECUADRO:
        raise ErrorObra("El tipo de recuadro debe ser 'localizacion' o 'detalle'.")
    if origen not in ("confirmado", "corregido", "dibujado"):
        raise ErrorObra("El origen debe ser 'confirmado', 'corregido' o 'dibujado'.")
    columna = TIPOS_RECUADRO[tipo]
    conn = get_connection()
    try:
        plano = _plano_vigente(conn, proyecto_id)
        rect = _validar_rect(plano, pagina, rect)
        elemento = _elemento(conn, proyecto_id, uid)
        anterior = json.loads(elemento[columna] or "{}")
        nuevo = {"plano_id": plano["id"], "pagina": pagina, "rect": rect, "origen": origen, "estado": "confirmado",
                 "confirmado_por": usuario, "confirmado_en": _ahora()}
        _transaccion(conn)
        try:
            conn.execute(f"UPDATE elementos_diseno SET {columna} = ?, actualizado = ? WHERE proyecto_id = ? AND uid = ?",
                         (json.dumps(nuevo, ensure_ascii=False), _ahora(), proyecto_id, uid))
            _auditar(conn, "GUARDAR_RECUADRO", uid, {"proyecto_id": proyecto_id, "recuadro": tipo,
                                                     "anterior": anterior, "nuevo": nuevo}, usuario)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return {"uid": uid, "recuadro": tipo, "guardado": nuevo}


# ---------- Vista previa con los generadores de la Etapa 3 ----------

def vista_previa(proyecto_id: str, tipo: str, pagina: int, rect: List[float]) -> bytes:
    """PNG tal como lo usarán los informes: LOCALIZACION (planta completa + recuadro rojo) o DETALLE (recorte nítido)."""
    if tipo not in TIPOS_RECUADRO:
        raise ErrorObra("El tipo de recuadro debe ser 'localizacion' o 'detalle'.")
    conn = get_connection()
    try:
        plano = _plano_vigente(conn, proyecto_id)
    finally:
        conn.close()
    rect = _validar_rect(plano, pagina, rect)
    ruta = Path(plano["vectorial_ruta"])
    try:
        if tipo == "localizacion":
            dpi = m3_localizacion.DPI_PLANTA
            imagen = m3_localizacion.generar_localizacion(ruta, pagina - 1, tuple(rect_pt_a_px(rect, dpi)), *CELDA_VISTA_PREVIA, dpi=dpi)
        else:
            imagen = m4_detalle.recortar_detalle(ruta, pagina - 1, tuple(rect), ruta.parent.parent)
    except ValueError as exc:
        raise ErrorObra(str(exc)) from None
    salida = io.BytesIO()
    imagen.thumbnail((1600, 1600))
    imagen.save(salida, format="PNG")
    return salida.getvalue()


# ---------- API ----------

class CuerpoRecuadro(BaseModel):
    tipo: str
    pagina: int
    rect: List[float]
    origen: str = "confirmado"


class CuerpoVistaPrevia(BaseModel):
    tipo: str
    pagina: int
    rect: List[float]


def _http(exc: ErrorObra) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=str(exc))


@router.get("/api/proyectos/{proyecto_id}/visor/indice")
def api_indice(proyecto_id: str):
    try:
        return indice_del_plano(proyecto_id)
    except ErrorObra as exc:
        raise _http(exc)


@router.get("/api/proyectos/{proyecto_id}/visor/hojas/{pagina}/info")
def api_info_hoja(proyecto_id: str, pagina: int, dpi: int = DPI_DEFECTO):
    try:
        return info_hoja(proyecto_id, pagina, dpi)
    except ErrorObra as exc:
        raise _http(exc)


@router.get("/api/proyectos/{proyecto_id}/visor/hojas/{pagina}.png")
def api_hoja_png(proyecto_id: str, pagina: int, dpi: int = DPI_DEFECTO):
    try:
        return FileResponse(rasterizar_hoja(proyecto_id, pagina, dpi), media_type="image/png")
    except ErrorObra as exc:
        raise _http(exc)


@router.get("/api/proyectos/{proyecto_id}/elementos")
def api_elementos(proyecto_id: str):
    try:
        return {"elementos": listar_elementos(proyecto_id)}
    except ErrorObra as exc:
        raise _http(exc)


@router.post("/api/proyectos/{proyecto_id}/elementos/{uid}/propuesta")
def api_propuesta(proyecto_id: str, uid: str):
    try:
        return proponer_recuadros(proyecto_id, uid)
    except ErrorObra as exc:
        raise _http(exc)


@router.put("/api/proyectos/{proyecto_id}/elementos/{uid}/recuadro")
def api_guardar_recuadro(proyecto_id: str, uid: str, cuerpo: CuerpoRecuadro):
    try:
        return guardar_recuadro(proyecto_id, uid, cuerpo.tipo, cuerpo.pagina, cuerpo.rect, cuerpo.origen)
    except ErrorObra as exc:
        raise _http(exc)


@router.post("/api/proyectos/{proyecto_id}/visor/vista-previa")
def api_vista_previa(proyecto_id: str, cuerpo: CuerpoVistaPrevia):
    try:
        return Response(content=vista_previa(proyecto_id, cuerpo.tipo, cuerpo.pagina, cuerpo.rect), media_type="image/png")
    except ErrorObra as exc:
        raise _http(exc)
