# BACKEND/generators/fi_mived.py
# Etapa 3 · T8 — Actualizador de los formularios MIVED FI-01 / FI-02 / FI-03 (PyMuPDF), CLAUDE.md §3.2.
#
# Los FI NO son AcroForm (reconocimiento de T0b): se escribe con texto y dibujos, localizando todo por el
# TEXTO de los rótulos y no por coordenadas fijas a ciegas. Método de fi02.py / fi02_s5.py: buscar el span,
# taparlo con una redacción blanca y escribir en la línea base. El generador NO lee la BD: recibe
# diccionarios. Regla de Oro #1: nada de datos fijos de ningún proyecto; lo que falte => error y no se
# escribe nada. Nunca se inserta una firma y se borran todas las anotaciones (#16); la mampostería nunca se
# marca (#17); si ya existe un FI del mismo nivel y tipo se actualiza como versión nueva (#18) y nunca se
# parte del FI de otro nivel. La fecha de autorización es la de la visita y va en la siguiente fila libre; las
# anteriores se conservan (respuesta de Steven, 23/10/2026).
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymupdf

from generators.comun import salida
from reglas_ingenieria import PENDIENTE, _es_fecha_ddmmaaaa_valida, _normalizar_texto

TIPOS_FI = {"FI-01": "cimentación", "FI-02": "losas, escaleras y vigas", "FI-03": "muros y columnas"}
CLASES = ("Parcial", "Completivo")
TAMANO_OBS = 10.6
INTERLINEADO = 15.8
X_NIVEL = 132.2
X_FECHA = 487.0
LADO_MARCA = 12.0
GROSOR_MARCA = 1.5
X_OBS_POR_DEFECTO = {"FI-01": 41.8, "FI-02": 26.8, "FI-03": 39.3}

# Filas con "Sí" marcado en los FI llenados de ejemplo (T0b, parte 2; filas = código del rótulo). Nunca las de
# mampostería (FI-03, sección 8) ni ninguna "No". Las de dinteles (FI-02, secciones 8 y 9) y las de muros de
# cerramiento/pandereta (FI-03, sección 9) solo se marcan si la visita trae un elemento de ese tipo (FILAS_SI_SI_HAY).
FILAS_SI = {
    "FI-01": {"1a", "1b", "1c", "1d", "1e", "1f", "1g", "1h", "1i", "4a", "4c", "4d", "4e",
              "7a", "7b", "7c", "7d", "7e", "7f", "8a"},
    "FI-02": {"1a", "1b", "1c", "1d", "1e", "2a", "2b", "2c", "2d", "2e", "6a", "6b",
              "7a", "7b", "7c", "7d", "7e", "11a", "11b", "11c", "11d", "11e", "11f", "12a"},
    "FI-03": {"1a", "1b", "1c", "1d", "1e", "2a", "2b", "2c", "2d", "4a", "4b", "4c", "4d", "4e", "4f",
              "5a", "5c", "5d", "5e", "10a", "10b", "10c", "10d", "10e", "11a", "11b", "11c", "11d"},
}

# FI -> (patrón del nombre de elemento que activa las filas, filas). Steven: "solo cuando la visita lo incluye".
FILAS_SI_SI_HAY = {
    "FI-02": (re.compile(r"\bDINTEL(ES)?\b"), {"8a", "8b", "8c", "8d", "9a", "9b", "9c", "9d"}),
    "FI-03": (re.compile(r"\b(MUROS? DE CERRAMIENTO|CERRAMIENTOS?|PANDERETAS?)\b"), {"9a", "9b", "9c"}),
}

# Campos de la cabecera de la hoja 1 (rótulo, clave de proyecto, lado, x del valor). Se localizan por su
# rótulo. "Encargado de obra" toma el residente (pendiente de que Steven lo confirme). Lado "i": columna de la
# izquierda (el valor va hasta x=398); lado "d": columna de la derecha (hasta el borde de la hoja).
X_LIMITE_IZQ = 398.0
X_LIMITE_DER = 580.0
CAMPOS_CABECERA = [
    (re.compile(r"^Nombre del proyecto$"), "nombre", "i", 12.6, None),
    (re.compile(r"^Licencia No\.$"), "no_licencia", "d", 8.6, None),
    (re.compile(r"^Sol\.\s*Licencia No\.$"), "no_solicitud", "d", 8.6, None),
    (re.compile(r"^Encargado de obra$"), "residente_obra", "i", None, 132.2),
    (re.compile(r"^Dirección$"), "direccion_obra", "i", None, 119.8),
]
_RE_ROTULO = re.compile(r"^(\d{1,2}[a-z])\s*\.")
_RE_SI = re.compile("^S[ií\u0301]$")
_RE_OBS = re.compile(r"^\d{1,2}\.\s*OBSERVACIONES", re.IGNORECASE)
_RE_FIRMAS = re.compile(r"^\d{1,2}\.\s*NOMBRES Y FIRMAS", re.IGNORECASE)
_FUENTES_CALIBRI = [Path(r"C:\Windows\Fonts\calibri.ttf")]


def _fuente() -> Tuple[str, Optional[str]]:
    for ruta in _FUENTES_CALIBRI:
        if ruta.exists():
            return "calibri", str(ruta)
    return "helv", None  # sin Calibri en la máquina: fuente base de PDF (se avisa al llamador)


def limpiar_extraido(texto: str) -> str:
    """Calibri, al insertarse, se extrae con espacios duros (U+00A0) y guiones U+2010: se normalizan al leer."""
    return texto.replace(" ", " ").replace("‐", "-").replace("‑", "-").replace("–", "-")


def _vacio(v) -> bool:
    return v is None or str(v).strip() == "" or str(v).strip().lower() == PENDIENTE


def _spans(page) -> List[Dict]:
    return [s for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for s in l["spans"]
            if s["text"].strip()]


def _error(res, texto):
    res["errores"].append(texto)
    return res


# ---------- Localización por rótulos ----------

def _filas_si(page) -> Dict[str, Dict]:
    """código de fila -> {si: bbox del texto 'Sí', caja: rect de la caja (imagen) de esa fila}."""
    spans = _spans(page)
    izq = sorted([s for s in spans if s["bbox"][0] < 40 and s["bbox"][1] > 85], key=lambda s: s["bbox"][1])
    bloques: List[List] = []
    for s in izq:
        m = _RE_ROTULO.match(s["text"].strip())
        if m:
            bloques.append([m.group(1), s["bbox"][1], s["bbox"][3]])
        elif bloques and not re.match(r"^\d{1,2}\.\s", s["text"].strip()) and s["bbox"][1] - bloques[-1][2] < 4:
            bloques[-1][2] = max(bloques[-1][2], s["bbox"][3])
    imagenes = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()
                if i["bbox"][0] > 480 and 40 < (i["bbox"][2] - i["bbox"][0]) < 60
                and (i["bbox"][3] - i["bbox"][1]) < 14]
    filas: Dict[str, Dict] = {}
    for s in spans:
        if not (_RE_SI.match(s["text"].strip()) and s["bbox"][0] > 480):
            continue
        y0, y1 = s["bbox"][1], s["bbox"][3]
        mejor = max(bloques, key=lambda b: min(b[2], y1) - max(b[1], y0), default=None)
        if not mejor or min(mejor[2], y1) - max(mejor[1], y0) <= 0:
            continue
        centro = (y0 + y1) / 2
        caja = min(imagenes, key=lambda r: abs((r.y0 + r.y1) / 2 - centro), default=None)
        if caja is not None and abs((caja.y0 + caja.y1) / 2 - centro) > 9:
            caja = None
        filas[mejor[0]] = {"si": pymupdf.Rect(s["bbox"]), "caja": caja}
    return filas


def _rect_marca(fila: Dict, x_cajas: Optional[float] = None) -> pymupdf.Rect:
    """
    Cuadro de 12x12 pt centrado en la primera caja de la fila (la de 'Sí'). Una fila sin caja propia (como la 7c
    del FI-02) toma la x de las cajas vecinas de la misma página; solo si ninguna tiene caja, va a la izquierda
    del texto.
    """
    caja = fila["caja"]
    if caja is not None:
        cx, cy = caja.x0 + 4.6, (caja.y0 + caja.y1) / 2
    else:
        si = fila["si"]
        cx = x_cajas + 4.6 if x_cajas is not None else si.x0 - 15.0
        cy = (si.y0 + si.y1) / 2
    m = LADO_MARCA / 2
    return pymupdf.Rect(cx - m, cy - m, cx + m, cy + m)


def _ya_marcada(page, rect: pymupdf.Rect) -> bool:
    for d in page.get_drawings():
        r = d["rect"]
        if (r.width < 20 and r.height < 20 and d.get("color") is not None and len(d["items"]) <= 3
                and abs((r.x0 + r.x1) / 2 - (rect.x0 + rect.x1) / 2) < 6
                and abs((r.y0 + r.y1) / 2 - (rect.y0 + rect.y1) / 2) < 6):
            return True
    return False


def _redactar(page, rects: List[pymupdf.Rect]):
    for r in rects:
        r = pymupdf.Rect(r)
        r.y0 += 1.5
        r.y1 -= 1.5
        page.add_redact_annot(r, fill=(1, 1, 1))
    if rects:
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)


def _texto_nivel_existente(page) -> Optional[str]:
    """Texto de la fila 'Nivel a inspeccionar' (vacío si el FI está en blanco); None si no hay rótulo."""
    spans = _spans(page)
    rotulo = next((s for s in spans if s["text"].strip() == "Nivel a inspeccionar"), None)
    if rotulo is None:
        return None
    y0, y1 = rotulo["bbox"][1] - 2, rotulo["bbox"][3] + 2
    valores = [s["text"] for s in spans if 110 < s["bbox"][0] < 400 and s["bbox"][1] >= y0 and s["bbox"][3] <= y1 + 3]
    return limpiar_extraido(" ".join(valores)).strip()


def _kw_texto(nombre_fuente, archivo_fuente) -> Dict:
    kw = {"fontname": nombre_fuente, "fontsize": TAMANO_OBS, "color": (0, 0, 0)}
    if archivo_fuente:
        kw["fontfile"] = archivo_fuente
    return kw


def _ancho(texto: str, tam: float, archivo_fuente) -> float:
    fuente = pymupdf.Font(fontfile=archivo_fuente) if archivo_fuente else pymupdf.Font("helv")
    return fuente.text_length(texto, fontsize=tam)


def _campos_de_proyecto(page, proyecto: Dict, nombre_fuente, archivo_fuente) -> Tuple[Optional[str], List[str]]:
    """
    Escribe nombre del proyecto, licencia, solicitud, encargado y dirección donde el FI los tiene vacíos.
    Un valor ya escrito NUNCA se sobrescribe; si difiere del del proyecto se deja un aviso.
    """
    spans = _spans(page)
    avisos: List[str] = []
    for patron, clave, lado, dx, x_abs in CAMPOS_CABECERA:
        rotulo = next((s for s in spans if patron.match(limpiar_extraido(s["text"]).strip())
                       and (s["bbox"][0] >= 400 if lado == "d" else s["bbox"][0] < 400)), None)
        if rotulo is None:
            return f"El formulario no trae el rótulo del campo '{clave}' en la primera hoja ({PENDIENTE}).", avisos
        valor = str(proyecto[clave]).strip()
        centro = (rotulo["bbox"][1] + rotulo["bbox"][3]) / 2
        x_desde = rotulo["bbox"][2] - 3  # el valor puede quedar pegado al final del rótulo
        x_hasta = X_LIMITE_DER + 20 if lado == "d" else X_LIMITE_IZQ + 2
        # Un valor escrito a mano queda unos puntos más arriba que el rótulo: se compara por el centro de la fila
        previos = [s for s in spans if s["bbox"][0] >= x_desde and s["bbox"][0] < x_hasta
                   and abs((s["bbox"][1] + s["bbox"][3]) / 2 - centro) < 7 and not patron.match(s["text"].strip())]
        previo = limpiar_extraido(" ".join(s["text"] for s in previos)).strip()
        if previo:
            if _normalizar_texto(previo) != _normalizar_texto(valor):
                avisos.append(f"El FI ya trae en '{clave}' el valor '{previo}', distinto del proyecto "
                              f"('{valor}'): no se cambió.")
            continue
        x = x_abs if x_abs is not None else rotulo["bbox"][2] + dx
        limite = X_LIMITE_DER if lado == "d" else X_LIMITE_IZQ
        tam = TAMANO_OBS
        while tam > 7.0 and x + _ancho(valor, tam, archivo_fuente) > limite:
            tam -= 0.25
        if x + _ancho(valor, tam, archivo_fuente) > limite:
            return f"El valor de '{clave}' no cabe en el campo del formulario ({PENDIENTE}).", avisos
        kw = _kw_texto(nombre_fuente, archivo_fuente)
        kw["fontsize"] = tam
        page.insert_text((x, rotulo["origin"][1] - 0.3), valor, **kw)
    return None, avisos


def _escribir_cabecera(page, nivel_txt: str, fecha: str, proyecto: Dict, nombre_fuente,
                       archivo_fuente) -> Tuple[Optional[str], List[str]]:
    """Datos del proyecto, nivel y fecha de la primera página. Devuelve (mensaje de error o None, avisos)."""
    spans = _spans(page)
    rotulo_nivel = next((s for s in spans if s["text"].strip() == "Nivel a inspeccionar"), None)
    rotulo_fecha = next((s for s in spans if s["text"].strip() == "Fecha" and s["bbox"][0] > 380
                         and s["bbox"][1] < 170), None)
    if rotulo_nivel is None or rotulo_fecha is None:
        return (f"El formulario no trae los rótulos 'Nivel a inspeccionar' y 'Fecha' en la primera hoja "
                f"({PENDIENTE}).", [])
    error, avisos = _campos_de_proyecto(page, proyecto, nombre_fuente, archivo_fuente)
    if error:
        return error, avisos
    n0, n1 = rotulo_nivel["bbox"][1] - 2, rotulo_nivel["bbox"][3] + 2
    viejos = [pymupdf.Rect(s["bbox"]) for s in spans
              if 110 < s["bbox"][0] < 400 and s["bbox"][1] >= n0 and s["bbox"][3] <= n1 + 3]
    f0, f1 = rotulo_fecha["bbox"][1] - 2, rotulo_fecha["bbox"][3] + 2  # lo que haya a la derecha de 'Fecha'
    viejos += [pymupdf.Rect(s["bbox"]) for s in spans if s["bbox"][0] >= rotulo_fecha["bbox"][2] + 10
               and s["bbox"][1] >= f0 and s["bbox"][3] <= f1 + 3]
    _redactar(page, viejos)
    kw = _kw_texto(nombre_fuente, archivo_fuente)
    page.insert_text((X_NIVEL, rotulo_nivel["origin"][1] - 0.1), nivel_txt, **kw)
    page.insert_text((X_FECHA, rotulo_fecha["origin"][1] + 0.6), fecha, **kw)
    return None, avisos


def _envolver(texto: str, ancho: float, tam: float, fuente: pymupdf.Font) -> List[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if fuente.text_length(prueba, fontsize=tam) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def _agregar_observaciones(doc, tipo_fi: str, lineas_nuevas: List[str], nombre_fuente,
                          archivo_fuente) -> Tuple[Optional[str], List[str]]:
    """
    Agrega las líneas debajo de las observaciones existentes. Si el FI trae un cierre anterior ("Todo segun ..."),
    se tapa con redacción blanca y se vuelve a escribir igual DESPUÉS de la observación nueva (respuesta de
    Steven). Devuelve (mensaje de error o None, textos del cierre que se movieron).
    """
    for page in doc:
        spans = _spans(page)
        cab = next((s for s in spans if _RE_OBS.match(s["text"].strip())), None)
        if cab is None:
            continue
        firmas = next((s for s in spans if _RE_FIRMAS.match(s["text"].strip()) and s["bbox"][1] > cab["bbox"][3]), None)
        limite = (firmas["bbox"][1] - 6) if firmas else page.rect.height - 40
        existentes = sorted((s for s in spans if s["bbox"][1] > cab["bbox"][3] and s["bbox"][3] < limite),
                            key=lambda s: (s["origin"][1], s["bbox"][0]))
        inicio_cierre = next((i for i, s in enumerate(existentes)
                              if _normalizar_texto(s["text"]).startswith("TODO SEGUN")), None)
        cierre = existentes[inicio_cierre:] if inicio_cierre is not None else []
        previas = existentes[:inicio_cierre] if inicio_cierre is not None else existentes
        base = (max(s["origin"][1] for s in previas) + INTERLINEADO) if previas else cab["bbox"][3] + 15.0
        x0 = min((s["bbox"][0] for s in existentes), default=X_OBS_POR_DEFECTO[tipo_fi])
        fuente = pymupdf.Font(fontfile=archivo_fuente) if archivo_fuente else pymupdf.Font("helv")
        ancho = page.rect.width - x0 - 20
        envueltas = [l for texto in lineas_nuevas for l in _envolver(texto, ancho, TAMANO_OBS, fuente)]
        ultima_nueva = base + (len(envueltas) - 1) * INTERLINEADO
        # El cierre conserva la separación que tenía respecto de la última observación (mínimo una línea en blanco)
        hueco = max(2 * INTERLINEADO, (cierre[0]["origin"][1] - previas[-1]["origin"][1]) if cierre and previas else 0)
        base_cierre = ultima_nueva + hueco
        ultima = base_cierre + (cierre[-1]["origin"][1] - cierre[0]["origin"][1]) if cierre else ultima_nueva
        if ultima > limite:
            return (f"Las observaciones no caben en el espacio disponible del formulario "
                    f"({len(envueltas)} líneas nuevas): {PENDIENTE}."), []
        movidos = [s["text"].strip() for s in cierre]
        if cierre:
            _redactar(page, [pymupdf.Rect(s["bbox"]) for s in cierre])
        kw = _kw_texto(nombre_fuente, archivo_fuente)
        for i, linea in enumerate(envueltas):
            page.insert_text((x0, base + i * INTERLINEADO), linea, **kw)
        for s in cierre:
            y = base_cierre + (s["origin"][1] - cierre[0]["origin"][1])
            page.insert_text((s["bbox"][0], y), s["text"].strip(), **kw)
        return None, movidos
    return f"El formulario no trae la sección OBSERVACIONES ({PENDIENTE}).", []


# ---------- Fechas de autorización de vaciado ----------

_RE_SEP = re.compile(r"^/\s*$")
_RE_NUM = re.compile(r"^(\d{2}|\d{4})$")
_RE_FECHA_COMPLETA = re.compile(r"^\d{2}/\d{2}/\d{4}$")  # fecha escrita de una sola vez, como en algunos FI llenados
_PLACEHOLDER = {"dd", "mm", "aaaa"}
LIMITE_INFERIOR = 36.0           # margen inferior de la hoja: una fila nueva no puede pasar de aquí (el pie impreso)
Y_SUPERIOR_HOJA_SIGUIENTE = 90.0  # arranque de la tabla cuando la fila nueva va en la hoja siguiente


def _filas_autorizacion(doc) -> List[Dict]:
    """
    Filas 'dd / mm / aaaa' de la sección NOMBRES Y FIRMAS (de la hoja del rótulo en adelante), de arriba abajo.
    Una fila está LIBRE si no trae ninguna cifra (solo el 'dd / mm / aaaa' impreso o solo las barras).
    """
    filas: List[Dict] = []
    visto = False
    for page in doc:
        spans = _spans(page)
        cab = next((s for s in spans if _RE_FIRMAS.match(s["text"].strip())), None)
        if cab is not None:
            visto = True
            y_min = cab["bbox"][3]
        elif visto:
            y_min = 80.0  # en las hojas siguientes se salta el encabezado impreso (con su fecha de impresión)
        else:
            continue
        candidatos = sorted((s for s in spans if s["bbox"][0] >= 455 and s["bbox"][1] > y_min and (
            _RE_SEP.match(s["text"].strip()) or _RE_NUM.match(s["text"].strip())
            or _RE_FECHA_COMPLETA.match(s["text"].strip()) or s["text"].strip().lower() in _PLACEHOLDER)),
                            key=lambda s: s["origin"][1])
        grupos: List[List[Dict]] = []
        for s in candidatos:  # una fila reúne los textos cuya línea base difiere en menos de 3 pt
            if grupos and s["origin"][1] - grupos[-1][-1]["origin"][1] < 3.0:
                grupos[-1].append(s)
            else:
                grupos.append([s])
        for grupo in grupos:
            barras = sorted((g for g in grupo if _RE_SEP.match(g["text"].strip())), key=lambda g: g["bbox"][0])
            marcadores = [g for g in grupo if g["text"].strip().lower() in _PLACEHOLDER]
            llena = any(_RE_NUM.match(g["text"].strip()) or _RE_FECHA_COMPLETA.match(g["text"].strip())
                        for g in grupo)
            if len(barras) < 2 and not marcadores and not llena:
                continue  # no es una fila de fecha
            filas.append({"pagina": page.number, "barras": barras[:2], "y": grupo[0]["origin"][1],
                          "marcadores": marcadores, "libre": not llena, "grupo": grupo})
    return filas


def _rects_de_dibujo(page) -> List[pymupdf.Rect]:
    return [pymupdf.Rect(it[1]) for d in page.get_drawings() for it in d["items"] if it[0] == "re"]


def _estilo_fecha(fila: Dict) -> Optional[Dict]:
    """Cómo está escrita la fecha de una fila: de una vez ('dd/mm/aaaa') o en tres partes con sus dos barras."""
    grupo = fila["grupo"]
    completas = [g for g in grupo if _RE_FECHA_COMPLETA.match(g["text"].strip())]
    if completas:
        return {"completa": completas[0]["origin"][0]}
    numeros = sorted((g for g in grupo if _RE_NUM.match(g["text"].strip())), key=lambda g: g["bbox"][0])
    if len(numeros) == 3 and len(fila["barras"]) == 2:
        return {"partes": [n["origin"][0] for n in numeros], "barras": [b["origin"][0] for b in fila["barras"]]}
    return None


def _agregar_fila_autorizacion(doc, fecha: str, nombre_fuente, archivo_fuente) -> Tuple[Optional[str], Optional[str]]:
    """
    Sin fila libre: agrega UNA fila debajo de la última de NOMBRES Y FIRMAS, con la misma altura, las mismas líneas
    verticales y las mismas posiciones de la fecha que la fila anterior, y escribe ahí la fecha de la visita.
    Si no cabe antes del margen inferior de la hoja va al principio de la hoja siguiente; si tampoco hay sitio,
    error. Devuelve (error, aviso).
    """
    sin_geometria = (f"El formulario no tiene ninguna fila libre para la fecha de autorización y no se pudo "
                     f"copiar la geometría de la última fila ({PENDIENTE}); no se escribe nada a ciegas.")
    filas = _filas_autorizacion(doc)
    ultima = filas[-1] if filas else None
    estilo = _estilo_fecha(ultima) if ultima else None
    if estilo is None:
        return sin_geometria, None
    page = doc[ultima["pagina"]]
    base = ultima["y"]
    rects = _rects_de_dibujo(page)
    anchas = [r for r in rects if r.width > 300 and r.height <= 2.5]
    fondos = [r for r in anchas if r.width >= 540 and r.y0 > base]
    inferiores = [r for r in anchas if r.y0 > base]
    if not fondos or not inferiores:
        return sin_geometria, None
    fondo = min(fondos, key=lambda r: r.y0)
    previas = [r for r in anchas if r.y1 < fondo.y0 - 3]
    if not previas:
        return sin_geometria, None
    alto = fondo.y0 - max(r.y1 for r in previas)               # altura de la última fila
    desplazamiento = min(r.y0 for r in inferiores) - base         # de la línea base a la línea inferior de su fila
    verticales = [r for r in rects if r.width < 2.5 and r.height > 8 and r.y1 >= fondo.y0 - 0.5
                  and r.y0 < fondo.y0 - 8]
    espesor = fondo.height
    destino, arriba = page, fondo.y1
    nuevo_fondo = arriba + alto
    if nuevo_fondo + espesor > page.rect.height - LIMITE_INFERIOR:
        if ultima["pagina"] + 1 >= len(doc):
            return (f"La fila nueva de autorización no cabe en la hoja y no hay hoja siguiente ({PENDIENTE}).", None)
        destino = doc[ultima["pagina"] + 1]
        arriba = Y_SUPERIOR_HOJA_SIGUIENTE + espesor
        nuevo_fondo = arriba + alto
        zona = pymupdf.Rect(fondo.x0 - 3, Y_SUPERIOR_HOJA_SIGUIENTE - 2, fondo.x1 + 3, nuevo_fondo + espesor + 2)
        if (nuevo_fondo + espesor > destino.rect.height - LIMITE_INFERIOR
                or any(pymupdf.Rect(sp["bbox"]).intersects(zona) for sp in _spans(destino))
                or any(r.intersects(zona) for r in _rects_de_dibujo(destino))):
            return (f"La fila nueva de autorización no cabe en la hoja ni hay espacio libre en la siguiente "
                    f"({PENDIENTE}).", None)
        destino.draw_rect(pymupdf.Rect(fondo.x0, Y_SUPERIOR_HOJA_SIGUIENTE, fondo.x1, arriba), color=None,
                          fill=(0, 0, 0))  # borde superior de la tabla, copiado del inferior
    for v in verticales:
        destino.draw_rect(pymupdf.Rect(v.x0, arriba if destino is page else Y_SUPERIOR_HOJA_SIGUIENTE, v.x1,
                                       nuevo_fondo + espesor), color=None, fill=(0, 0, 0))
    destino.draw_rect(pymupdf.Rect(fondo.x0, nuevo_fondo, fondo.x1, nuevo_fondo + espesor), color=None, fill=(0, 0, 0))
    y = nuevo_fondo - desplazamiento
    kw = _kw_texto(nombre_fuente, archivo_fuente)
    if "completa" in estilo:
        destino.insert_text((estilo["completa"], y), fecha, **kw)
    else:
        for x, texto in zip(estilo["partes"], fecha.split("/")):
            destino.insert_text((x, y), texto, **kw)
        for x in estilo["barras"]:
            destino.insert_text((x, y), "/", **kw)
    donde = "en la hoja siguiente" if destino is not page else "debajo de la última"
    return None, f"No había fila libre de autorización: se agregó una fila nueva {donde} con la fecha {fecha}."


def _escribir_fecha_autorizacion(doc, fecha: str, nombre_fuente, archivo_fuente) -> Tuple[Optional[str], Optional[str]]:
    """
    Escribe dd/mm/aaaa de la visita en la siguiente fila de autorización libre. Las fechas anteriores se
    conservan; sin fila libre se agrega una fila nueva (ver _agregar_fila_autorizacion). Devuelve (error, aviso).
    """
    libre = next((f for f in _filas_autorizacion(doc) if f["libre"]), None)
    if libre is None:
        return _agregar_fila_autorizacion(doc, fecha, nombre_fuente, archivo_fuente)
    page = doc[libre["pagina"]]
    dia, mes, anio = fecha.split("/")
    pos = {m["text"].strip().lower(): m["bbox"][0] for m in libre["marcadores"]}
    if len(libre["barras"]) == 2:
        s1, s2 = libre["barras"]
        x_dia = pos.get("dd", s1["bbox"][0] - 20.9)
        x_mes = pos.get("mm", s1["bbox"][0] + 13.0)
        x_anio = pos.get("aaaa", s2["bbox"][0] + 21.6)
    elif {"dd", "mm", "aaaa"} <= set(pos):
        x_dia, x_mes, x_anio = pos["dd"], pos["mm"], pos["aaaa"]
    else:
        return (f"No se pudo ubicar dónde escribir la fecha de autorización en la fila libre ({PENDIENTE}); "
                "no se escribe nada a ciegas."), None
    _redactar(page, [pymupdf.Rect(m["bbox"]) for m in libre["marcadores"]])
    kw = _kw_texto(nombre_fuente, archivo_fuente)
    for x, texto in ((x_dia, dia), (x_mes, mes), (x_anio, anio)):
        page.insert_text((x, libre["y"]), texto, **kw)
    return None, None


def _filas_condicionales(tipo_fi: str, elementos: List[str]) -> set:
    """Filas de dinteles / cerramiento que se marcan porque la lista de elementos trae uno de ese tipo."""
    regla = FILAS_SI_SI_HAY.get(tipo_fi)
    if regla and any(regla[0].search(_normalizar_texto(e)) for e in elementos):
        return set(regla[1])
    return set()


def _marcar_si(doc, tipo_fi: str, extra=frozenset()) -> Tuple[int, List[str]]:
    """Dibuja la marca 'Sí' (X de 12x12 pt) en las filas de FILAS_SI más `extra`. Devuelve (marcas, filas no halladas)."""
    a_marcar = set(FILAS_SI[tipo_fi]) | set(extra)
    pendientes = set(a_marcar)
    dibujadas = 0
    for page in doc:
        filas = _filas_si(page)
        xs = sorted(f["caja"].x0 for f in filas.values() if f["caja"] is not None)
        x_cajas = xs[len(xs) // 2] if xs else None  # mediana de las cajas de la hoja
        for codigo, fila in filas.items():
            if codigo not in a_marcar:
                continue
            pendientes.discard(codigo)
            r = _rect_marca(fila, x_cajas)
            if _ya_marcada(page, r):
                continue
            forma = page.new_shape()  # un solo trazo de 2 líneas, como las marcas de los FI de ejemplo
            forma.draw_line((r.x0, r.y0), (r.x1, r.y1))
            forma.draw_line((r.x0, r.y1), (r.x1, r.y0))
            forma.finish(color=(0, 0, 0), width=GROSOR_MARCA, closePath=False)
            forma.commit()
            dibujadas += 1
    return dibujadas, sorted(pendientes)


def _borrar_anotaciones(doc) -> int:
    n = 0
    for page in doc:
        for a in list(page.annots() or []):
            page.delete_annot(a)
            n += 1
    return n


# ---------- API ----------

def _clave_en_nivel(clave: str, nivel_existente: str) -> Optional[str]:
    """
    Comprueba que `clave` identifique el nivel del FI existente, con límites de palabra (SOTANO -3 no encaja en
    SOTANO -30). Una clave sin número solo vale si es el nivel completo. Devuelve un mensaje de error o None.
    """
    c, n = _normalizar_texto(clave), _normalizar_texto(nivel_existente)
    if not re.search(r"\d", c):
        if c == n:
            return None
        return (f"La clave de nivel '{clave}' es genérica (no tiene número) y no es el nivel completo del FI "
                f"existente ('{nivel_existente}'): {PENDIENTE}.")
    if re.search(r"(?<![0-9A-Z])" + re.escape(c) + r"(?![0-9A-Z])", n):
        return None
    return f"El FI existente es de otro nivel ('{nivel_existente}', se esperaba '{clave}'): no se actualiza el FI de otro nivel (#18)."


def nombre_archivo(proyecto: Dict, nivel_txt: str) -> str:
    """§5.2: MIVED - <PROYECTO>-<ELEMENTOS NIVEL>.PDF"""
    return f"MIVED - {proyecto['nombre'].upper()}-{nivel_txt.upper()}.PDF"


def actualizar_fi(tipo_fi: str, proyecto: Dict, visita: Dict, nivel_txt: str, nivel_clave: str,
                  elementos: List[str], existente: Optional[Path] = None, en_blanco: Optional[Path] = None,
                  carpeta_salida=None, usuario: Optional[str] = None) -> Dict:
    """
    Genera o actualiza el FI de un nivel y tipo. Devuelve {"ok", "ruta", "errores", "avisos", "marcas"}.
    - existente: el FI ya hecho para ESTE nivel y tipo (se actualiza y se guarda como versión nueva);
      en_blanco: el FI en blanco del proyecto, solo si no existe uno. Nunca se parte del FI de otro nivel.
    - nivel_txt: texto de 'Nivel a inspeccionar'; nivel_clave: parte que identifica el nivel (p. ej. 'SOTANO -3'),
      que debe aparecer en el FI existente.
    - proyecto: nombre, no_licencia, no_solicitud, residente_obra ("Encargado de obra", pendiente de confirmar) y
      direccion_obra; se escriben solo donde el FI los tiene vacíos y nunca se sobrescribe un valor existente.
    - elementos: nombres de lo supervisado en la visita (se agregan a Observaciones).
    - visita: fecha (DD/MM/AAAA), clase (Parcial/Completivo) y, opcional, discrepancias_abiertas.
    """
    res = {"ok": False, "ruta": None, "errores": [], "avisos": [], "marcas": 0, "cierre_movido": [],
           "fila_agregada": False}
    if tipo_fi not in TIPOS_FI:
        return _error(res, f"Tipo de formulario '{tipo_fi}' desconocido; usa FI-01, FI-02 o FI-03.")
    for campo in ("nombre", "no_licencia", "no_solicitud", "residente_obra", "direccion_obra"):
        if _vacio(proyecto.get(campo)):
            res["errores"].append(f"Falta 'proyecto.{campo}' para la cabecera del formulario: {PENDIENTE}.")
    for etiqueta, valor in (("nivel_txt", nivel_txt),
                            ("nivel_clave", nivel_clave), ("visita.fecha", visita.get("fecha")),
                            ("visita.clase", visita.get("clase"))):
        if _vacio(valor):
            res["errores"].append(f"Falta '{etiqueta}': {PENDIENTE}.")
    if not elementos or any(_vacio(e) for e in elementos):
        res["errores"].append(f"La visita no trae los elementos supervisados: {PENDIENTE}.")
    fecha, clase = visita.get("fecha"), visita.get("clase")
    if not _vacio(fecha) and not (isinstance(fecha, str) and _es_fecha_ddmmaaaa_valida(fecha)):
        res["errores"].append(f"La fecha '{fecha}' no está en formato DD/MM/AAAA.")
    if not _vacio(clase) and clase not in CLASES:
        res["errores"].append(f"La clase '{clase}' debe ser Parcial o Completivo.")
    origen = existente or en_blanco
    if origen is None:
        res["errores"].append("No hay FI de partida: indica el existente de este nivel y tipo o el FI en blanco del proyecto.")
    elif not Path(origen).is_file():
        res["errores"].append(f"El FI de partida no existe: '{origen}'.")
    if res["errores"]:
        return res

    doc = pymupdf.open(str(origen))  # el archivo de partida no se modifica: se guardan bytes nuevos
    try:
        if existente is not None:
            actual = _texto_nivel_existente(doc[0])
            if actual is None:
                return _error(res, f"El FI existente no tiene el rótulo 'Nivel a inspeccionar' ({PENDIENTE}).")
            err = _clave_en_nivel(nivel_clave, actual)
            if err:
                return _error(res, err)
        nombre_fuente, archivo_fuente = _fuente()
        if archivo_fuente is None:
            res["avisos"].append("Calibri no está instalada en esta máquina: se usó la fuente base del PDF.")
        err, avisos = _escribir_cabecera(doc[0], nivel_txt, fecha, proyecto, nombre_fuente, archivo_fuente)
        res["avisos"].extend(avisos)
        if err:
            return _error(res, err)
        lineas = [f"{fecha} - {clase.upper()}: Se supervisaron {', '.join(elementos)}."]
        if clase == "Completivo" and not (visita.get("discrepancias_abiertas") or []):
            lineas.append("CONFORME A PLANOS APROBADOS")
        err, movidos = _agregar_observaciones(doc, tipo_fi, lineas, nombre_fuente, archivo_fuente)
        if err:
            return _error(res, err)
        res["cierre_movido"] = movidos
        if movidos:
            res["avisos"].append("El cierre anterior se movió después de la observación nueva: " + " | ".join(movidos))
        err, aviso = _escribir_fecha_autorizacion(doc, fecha, nombre_fuente, archivo_fuente)
        if err:
            return _error(res, err)
        if aviso:
            res["avisos"].append(aviso)
            res["fila_agregada"] = True
        extra = _filas_condicionales(tipo_fi, elementos)
        if extra:
            res["avisos"].append(f"La visita trae dinteles/cerramiento: se marcan también las filas {', '.join(sorted(extra))}.")
        marcas, no_halladas = _marcar_si(doc, tipo_fi, extra)
        if no_halladas:
            return _error(res, f"No se hallaron en el formulario las filas {', '.join(no_halladas)} "
                               f"({PENDIENTE}); no se marca nada a ciegas.")
        res["marcas"] = marcas
        borradas = _borrar_anotaciones(doc)
        if borradas:
            res["avisos"].append(f"Se borraron {borradas} anotaciones de firma (el sistema nunca firma).")
        doc.set_metadata({"title": nombre_archivo(proyecto, nivel_txt)[:-4]})
        contenido = doc.tobytes(garbage=3, deflate=True)
    finally:
        doc.close()
    try:
        guardado = salida.guardar_pdf(nombre_archivo(proyecto, nivel_txt), contenido, carpeta=carpeta_salida,
                                      formato=tipo_fi, entidad_id=visita.get("id", ""), usuario=usuario)
    except salida.SalidaInvalida as exc:
        return _error(res, str(exc))
    res.update(ok=True, ruta=guardado["ruta"], version_nueva=guardado["version_nueva"])
    return res
