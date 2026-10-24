# BACKEND/plano/lector_plano.py
# Etapa 2 · T6n-a — Núcleo del lector de planos vectoriales (PLANES/etapa-2.md, T6n-a; informe T3n).
#
# Módulo PURO: lee un PDF vectorial y devuelve CANDIDATOS con su fuente (archivo, página, bbox, hoja). No escribe
# en la BD ni en disco, no asigna elementos a cruces de ejes y NO resuelve E-n <-> nivel ni L# <-> tipo (los da el
# usuario). Regla de Oro #1: una celda que no encaja en una columna o en una fila queda `pendiente de verificar` o
# se descarta con su motivo; jamás se rellena por vecindad.
#
# Coordenadas: todas las bbox salen en el marco VISUAL de la página (con `rotation_matrix` aplicada, como en las
# hojas giradas 270°); páginas numeradas desde 1.
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymupdf

from reglas_ingenieria import PENDIENTE

TOLERANCIA_Y = 4.0           # pt: dos textos con centros a menos de esto están en la misma fila
TOLERANCIA_X = 8.0           # pt de holgura de una celda respecto de la columna de su encabezado
SALTO_MAXIMO_FILAS = 30.0    # pt: un hueco mayor entre filas termina la tabla

_RE_NUMERO_HOJA = re.compile(r"^(\d{1,3})\s*/\s*(\d{1,3})$")
_RE_GLOBO = re.compile(r"^[A-Z0-9]{1,2}'?$")
_RE_SECCION = re.compile(r"^S-?\d{1,2}'?(?:\s*/\s*S-?\d{1,2}'?)?$")
IDS_EN_PLANTA = [  # (tipo, patrón del texto completo)
    ("columna", re.compile(r"^C\d{1,3}$")),
    ("losa", re.compile(r"^L\d{1,3}$")),
    ("muro", re.compile(r"^MH?\d{1,3}$")),
    ("viga", re.compile(r"^V-?\s?\d{2,3}\s?[Xx]\s?\d{2,3}$")),
]
MARCAS_DE_MODIFICACION = [  # (clave, patrón sobre el texto con espacios normalizados)
    ("se_modifico", re.compile(r"\bSE MODIFIC[OÓ]\b", re.I)),
    ("en_reemplazo", re.compile(r"\bEN REEMPLAZO\b", re.I)),
    ("plano_anterior", re.compile(r"\bPLANO ANTERIOR\b", re.I)),
]


# ---------- Apertura y líneas ----------

def _abrir(origen):
    if isinstance(origen, pymupdf.Document):
        return origen, Path(origen.name).name
    return pymupdf.Document(str(origen)), Path(str(origen)).name


def _rect(r) -> List[float]:
    return [round(float(v), 1) for v in (r.x0, r.y0, r.x1, r.y1)]


def _lineas(page) -> List[Dict]:
    """Líneas de texto de la página con su bbox VISUAL (rotation_matrix aplicada), tamaño y texto."""
    m = page.rotation_matrix
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            texto = "".join(s["text"] for s in l["spans"]).strip()
            if not texto:
                continue
            tam = max((s["size"] for s in l["spans"]), default=0.0)
            out.append({"texto": texto, "rect": pymupdf.Rect(l["bbox"]) * m, "tam": round(tam, 1)})
    return out


def _fuente(nombre: str, numero: int, rect, hoja: Optional[str]) -> Dict:
    return {"archivo": nombre, "pagina": numero, "bbox": _rect(rect), "hoja": hoja}


def _centro_y(r) -> float:
    return (r.y0 + r.y1) / 2


def _centro_x(r) -> float:
    return (r.x0 + r.x1) / 2


# ---------- 1. Índice de hojas ----------

def _numero_de_hoja(lineas: List[Dict]) -> Tuple[Optional[str], Optional[str], Optional[pymupdf.Rect]]:
    """
    'NN' y total del cajetín. El número puede venir en una línea ('13/36') o partido ('13' + '/36') con los dos
    trozos pegados en la misma fila; entre varias coincidencias se toma la que está más abajo y a la derecha
    (el cajetín), porque los textos del dibujo pueden contener fracciones.
    """
    candidatos = []
    for l in lineas:
        m = _RE_NUMERO_HOJA.match(l["texto"])
        if m:
            candidatos.append((m.group(1), m.group(2), l["rect"]))
    for l in lineas:
        m = re.match(r"^/\s*(\d{1,3})$", l["texto"])
        if not m:
            continue
        # el número va pegado a "/36": a su izquierda (hojas horizontales) o encima (texto girado 90° en las verticales)
        junto = [o for o in lineas if o is not l and re.fullmatch(r"\d{1,3}", o["texto"]) and (
            (abs(_centro_y(o["rect"]) - _centro_y(l["rect"])) < 4 and 0 <= l["rect"].x0 - o["rect"].x1 < 8)
            or (abs(_centro_x(o["rect"]) - _centro_x(l["rect"])) < 8 and 0 <= l["rect"].y0 - o["rect"].y1 < 8))]
        if junto:
            o = max(junto, key=lambda o: o["rect"].x1 + o["rect"].y1)
            candidatos.append((o["texto"], m.group(1), o["rect"] | l["rect"]))
    if not candidatos:
        return None, None, None
    n, total, r = max(candidatos, key=lambda c: (c[2].y1 + c[2].x1))
    return n.zfill(2), total, r


def _titulos(lineas: List[Dict], pagina: pymupdf.Rect, cajetin: Optional[pymupdf.Rect]) -> List[Dict]:
    """
    Títulos impresos bajo cada dibujo: líneas de rótulo (mayúsculas, 14-50 pt) fuera de la franja del cajetín, y
    las líneas contiguas del mismo rótulo (mismo tamaño y misma esquina izquierda) unidas en un solo título.
    """
    margen = pagina.x1 - 0.1 * pagina.width
    cand = []
    for l in lineas:
        t = l["texto"]
        letras = [c for c in t if c.isalpha()]
        if not (14.0 <= l["tam"] <= 50.0) or len(letras) < 6 or " " not in t:
            continue
        if sum(c.isupper() for c in letras) < 0.85 * len(letras):
            continue
        if l["rect"].x0 >= margen or (cajetin is not None and l["rect"].intersects(cajetin)):
            continue
        cand.append(l)
    cand.sort(key=lambda l: (round(l["rect"].x0 / 40), l["rect"].y0))
    grupos: List[List[Dict]] = []
    for l in sorted(cand, key=lambda l: (l["rect"].y0, l["rect"].x0)):
        for g in grupos:
            u = g[-1]
            if (abs(u["tam"] - l["tam"]) < 0.8 and -0.6 * l["tam"] <= l["rect"].y0 - u["rect"].y1 < 0.9 * l["tam"]
                    and abs(u["rect"].x0 - l["rect"].x0) < 25 + 0.5 * l["tam"]):
                g.append(l)
                break
        else:
            grupos.append([l])
    out = []
    for g in grupos:
        r = pymupdf.Rect(g[0]["rect"])
        for l in g[1:]:
            r |= l["rect"]
        out.append({"texto": " ".join(" ".join(l["texto"].split()) for l in g), "bbox": _rect(r), "tam": g[0]["tam"]})
    return sorted(out, key=lambda t: (t["bbox"][1], t["bbox"][0]))


def indice_hojas(ruta) -> List[Dict]:
    """
    Una entrada por página: {pagina, rotacion, hoja (NN), total (/36), bbox_numero, titulos[], fuente}. El número
    sale del cajetín; si no se encuentra, `hoja` queda PENDIENTE (nunca se deduce del orden de las páginas).
    """
    doc, nombre = _abrir(ruta)
    salida = []
    for p in doc:
        lineas = _lineas(p)
        n, total, rn = _numero_de_hoja(lineas)
        cajetin = pymupdf.Rect(p.rect.x1 - 0.1 * p.rect.width, p.rect.y0, p.rect.x1, p.rect.y1)
        salida.append({
            "pagina": p.number + 1, "rotacion": p.rotation, "hoja": n or PENDIENTE, "total": total,
            "bbox_numero": _rect(rn) if rn is not None else None,
            "titulos": _titulos(lineas, p.rect, cajetin),
            "fuente": _fuente(nombre, p.number + 1, p.rect, n),
        })
    return salida


def _hoja_de(doc, pagina: int) -> Optional[str]:
    n, _, _ = _numero_de_hoja(_lineas(doc[pagina - 1]))
    return n.zfill(2) if n else None


# ---------- 2. Tablas por posición ----------

def _celda(valor: Optional[str], rect) -> Dict:
    return {"valor": valor if valor is not None else PENDIENTE, "bbox": _rect(rect) if rect is not None else None}


def _buscar_ancla(lineas: List[Dict], patron: re.Pattern) -> Optional[Dict]:
    return next((l for l in sorted(lineas, key=lambda l: (l["rect"].y0, l["rect"].x0))
                 if patron.match(" ".join(l["texto"].split()))), None)


def _tabla_por_encabezado(lineas, ancla, encabezados, etiqueta_col, ancho_busqueda, alto_busqueda):
    """
    Lee una tabla anclada a un encabezado. `encabezados`: nombres exactos de las columnas (la primera es la de
    etiquetas de fila, p. ej. TIPO DE / MURO). Las filas nacen de las etiquetas; cada celda se asigna a la fila cuyo
    ancla esté a ≤ TOLERANCIA_Y y a la columna cuyo encabezado la contenga (± TOLERANCIA_X). Lo que no encaja se
    lista en `descartadas` con el motivo y la fila queda con esa celda PENDIENTE.
    """
    zona = pymupdf.Rect(ancla["rect"].x0 - ancho_busqueda[0], ancla["rect"].y1,
                        ancla["rect"].x1 + ancho_busqueda[1], ancla["rect"].y1 + alto_busqueda)
    dentro = [l for l in lineas if l is not ancla and zona.contains(pymupdf.Rect(l["rect"].x0 + 0.5, l["rect"].y0 + 0.5,
                                                                                 l["rect"].x1 - 0.5, l["rect"].y1 - 0.5))]
    norm = lambda t: " ".join(t.split())  # noqa: E731
    cab = {}
    for l in sorted(dentro, key=lambda l: l["rect"].y0):
        t = norm(l["texto"])
        if t in encabezados and t not in cab:
            cab[t] = l
    avisos, descartadas = [], []
    faltan = [e for e in encabezados if e not in cab]
    if etiqueta_col not in cab or faltan == list(encabezados):
        return {"encabezados": {}, "filas": [], "descartadas": [],
                "avisos": [f"No se halló el encabezado de la columna de etiquetas '{etiqueta_col}'."]}
    if faltan:
        avisos.append(f"Columnas sin encabezado en el plano: {', '.join(faltan)} ({PENDIENTE}).")
    base_y = max(l["rect"].y1 for l in cab.values())
    col_et = cab[etiqueta_col]["rect"]
    etiquetas = []
    for l in sorted(dentro, key=lambda l: l["rect"].y0):
        if _centro_y(l["rect"]) <= base_y or norm(l["texto"]) in encabezados:
            continue
        if col_et.x0 - TOLERANCIA_X <= _centro_x(l["rect"]) <= col_et.x1 + TOLERANCIA_X and len(l["texto"]) <= 4:
            if etiquetas and l["rect"].y0 - etiquetas[-1]["rect"].y1 > SALTO_MAXIMO_FILAS:
                break  # la tabla terminó
            etiquetas.append(l)
    columnas = {e: cab[e]["rect"] for e in encabezados if e in cab and e != etiqueta_col}
    filas = [{"etiqueta": _celda(norm(e["texto"]), e["rect"]), "celdas": {c: _celda(None, None) for c in columnas},
              "_y": _centro_y(e["rect"])} for e in etiquetas]
    limite = (etiquetas[-1]["rect"].y1 + TOLERANCIA_Y + 2) if etiquetas else base_y
    usados = {id(e) for e in etiquetas}
    for l in dentro:
        if id(l) in usados or _centro_y(l["rect"]) <= base_y or l["rect"].y0 > limite or norm(l["texto"]) in encabezados:
            continue
        cx = _centro_x(l["rect"])
        cols = [c for c, r in columnas.items()
                if r.x0 - max(TOLERANCIA_X, 12 - (r.x1 - r.x0) / 2) <= cx <= r.x1 + max(TOLERANCIA_X, 12 - (r.x1 - r.x0) / 2)]
        fila = min(filas, key=lambda f: abs(f["_y"] - _centro_y(l["rect"])), default=None)
        if fila is None or abs(fila["_y"] - _centro_y(l["rect"])) > TOLERANCIA_Y:
            descartadas.append({"texto": l["texto"], "bbox": _rect(l["rect"]), "motivo": "ninguna fila a ±4 pt"})
        elif len(cols) != 1:
            descartadas.append({"texto": l["texto"], "bbox": _rect(l["rect"]),
                                "motivo": "no cae en ninguna columna" if not cols else "cae en varias columnas"})
        elif fila["celdas"][cols[0]]["bbox"] is not None:
            descartadas.append({"texto": l["texto"], "bbox": _rect(l["rect"]), "motivo": f"segunda celda en {cols[0]}"})
        else:
            fila["celdas"][cols[0]] = _celda(norm(l["texto"]), l["rect"])
    for f in filas:
        f.pop("_y")
        f["pendientes"] = [c for c, v in f["celdas"].items() if v["bbox"] is None]
    return {"encabezados": {e: _rect(cab[e]["rect"]) for e in cab}, "filas": filas, "descartadas": descartadas,
            "avisos": avisos}


def tabla_acero_losa(ruta, pagina: int) -> Optional[Dict]:
    """'TABLA DE ACERO EN LOSA' (tipos A/B/C): H, Bw1, Bw2, h1, h2, acero inferior DIR. X / DIR. Y y AS. ADIC."""
    doc, nombre = _abrir(ruta)
    lineas = _lineas(doc[pagina - 1])
    ancla = _buscar_ancla(lineas, re.compile(r"^TABLA DE ACERO EN LOSA$"))
    if ancla is None:
        return None
    r = _tabla_por_encabezado(lineas, ancla, ["TIPO DE", "H", "Bw1", "Bw2", "h1", "h2", "DIR. X", "DIR. Y", "AS. ADIC."],
                              "TIPO DE", (70, 380), 130)
    return {"tabla": "acero_en_losa", "fuente": _fuente(nombre, pagina, ancla["rect"], _hoja_de(doc, pagina)), **r}


def tabla_zapata_lindero(ruta, pagina: int) -> Optional[Dict]:
    """'TABLA DE APLICACION PARA ZAPATA DE MURO LINDERO': MURO, B, h, Df, ACERO Ast, ACERO Asl."""
    doc, nombre = _abrir(ruta)
    lineas = _lineas(doc[pagina - 1])
    ancla = _buscar_ancla(lineas, re.compile(r"^TABLA DE APLICACION PARA$"))
    if ancla is None:
        return None
    r = _tabla_por_encabezado(lineas, ancla, ["MURO", "B", "h", "Df", "ACERO Ast", "ACERO Asl"], "MURO", (20, 120), 110)
    return {"tabla": "zapata_muro_lindero", "fuente": _fuente(nombre, pagina, ancla["rect"], _hoja_de(doc, pagina)), **r}


_RE_RANGO = re.compile(r"^(FUND\.?|E-?\d{1,2})\s*@\s*(E-?\d{1,2}|TECHO)$", re.I)
_RE_FC = re.compile(r"^(\d{3})\s*Kg\s*/\s*cm\s*2?$", re.I)


def tabla_fc_por_rango(ruta, pagina: int) -> Optional[Dict]:
    """
    f'c por rango de entrepisos (`FUND.@ E3`, `E3 @ E10`…) anclado a 'CONCRETO F'c'. Cada fila une el rango y el
    valor SOLO si están en la misma fila (±4 pt); un valor sin rango (o al revés) queda pendiente. El rango se
    devuelve tal cual está escrito: no se expande ni se traduce a niveles.
    """
    doc, nombre = _abrir(ruta)
    lineas = _lineas(doc[pagina - 1])
    ancla = _buscar_ancla(lineas, re.compile(r"^CONCRETO F['’]c$"))
    if ancla is None:
        return None
    zona = pymupdf.Rect(ancla["rect"].x0 - 60, ancla["rect"].y1, ancla["rect"].x1 + 120, ancla["rect"].y1 + 140)
    dentro = sorted((l for l in lineas if l is not ancla and zona.contains(pymupdf.Rect(l["rect"].x0 + .5, l["rect"].y0 + .5,
                                                                                      l["rect"].x1 - .5, l["rect"].y1 - .5))),
                    key=lambda l: l["rect"].y0)
    rangos = [l for l in dentro if _RE_RANGO.match(" ".join(l["texto"].split()))]
    valores = [l for l in dentro if _RE_FC.match(" ".join(l["texto"].split()))]
    filas, descartadas, libres = [], [], list(valores)
    for rg in rangos:
        par = [v for v in libres if abs(_centro_y(v["rect"]) - _centro_y(rg["rect"])) <= TOLERANCIA_Y]
        v = min(par, key=lambda v: abs(_centro_y(v["rect"]) - _centro_y(rg["rect"]))) if par else None
        if v is not None:
            libres.remove(v)
        m = _RE_RANGO.match(" ".join(rg["texto"].split()))
        filas.append({"rango": _celda(" ".join(rg["texto"].split()), rg["rect"]), "desde": m.group(1).upper(),
                      "hasta": m.group(2).upper(),
                      "fc_kgcm2": _celda(_RE_FC.match(" ".join(v["texto"].split())).group(1) if v else None,
                                         v["rect"] if v else None)})
    for v in libres:
        descartadas.append({"texto": v["texto"], "bbox": _rect(v["rect"]), "motivo": "valor de f'c sin rango en su fila"})
    return {"tabla": "fc_por_rango", "fuente": _fuente(nombre, pagina, ancla["rect"], _hoja_de(doc, pagina)),
            "filas": filas, "descartadas": descartadas, "avisos": []}


# ---------- 3. Globos de eje ----------

def _circulos(page) -> List[Dict]:
    """Círculos vectoriales (4 curvas Bézier cerradas, caja casi cuadrada de 10 a 45 pt)."""
    m = page.rotation_matrix
    out = []
    for d in page.get_drawings():
        items = d["items"]
        if len(items) not in (4, 8) or any(it[0] != "c" for it in items):
            continue
        r = pymupdf.Rect(d["rect"]) * m
        if 10.0 <= r.width <= 45.0 and abs(r.width - r.height) <= 1.5:
            out.append({"rect": r, "capa": d.get("layer")})
    return out


def globos_de_eje(ruta, pagina: int) -> List[Dict]:
    """
    Globos de eje de una planta: texto de 1-2 caracteres rodeado por un círculo vectorial, alineado con otros
    globos del mismo tamaño en una fila o una columna del margen, con rótulos TODOS DISTINTOS (una letra repetida
    en varios círculos —marcas de apoyo de la losa— no es un eje). Devuelve {texto, bbox, diametro, capa, orientacion,
    confianza, fuente}; confianza 'alta' si la capa del círculo es de ejes (nombre con "EJE"), 'media' si no.
    """
    doc, nombre = _abrir(ruta)
    page = doc[pagina - 1]
    hoja = _hoja_de(doc, pagina)
    lineas = [l for l in _lineas(page) if _RE_GLOBO.match(l["texto"])]
    cand = []
    for c in _circulos(page):
        dentro = [l for l in lineas if c["rect"].contains(_centro_punto(l["rect"]))]
        if len(dentro) == 1:
            cand.append({**c, "texto": dentro[0]["texto"]})
    elegidos = {}
    for orient, centro in (("fila", _centro_y), ("columna", _centro_x)):
        for clase in ("letra", "numero"):  # un eje se rotula con letras o con números, no mezclados
            propios = [c for c in cand if (c["texto"].rstrip("'").isalpha() if clase == "letra"
                                           else c["texto"].rstrip("'").isdigit())]
            for c in propios:
                grupo = [o for o in propios if abs(centro(o["rect"]) - centro(c["rect"])) <= 3.0
                         and abs(o["rect"].width - c["rect"].width) <= 1.5]
                if len(grupo) >= 2 and len({o["texto"] for o in grupo}) == len(grupo):
                    for o in grupo:
                        elegidos[id(o)] = (o, orient)
    out = []
    for o, orient in sorted(elegidos.values(), key=lambda t: (t[1], t[0]["rect"].y0, t[0]["rect"].x0)):
        out.append({"texto": o["texto"], "bbox": _rect(o["rect"]), "diametro": round(o["rect"].width, 1),
                    "capa": o["capa"], "orientacion": orient,
                    "confianza": "alta" if "EJE" in (o["capa"] or "").upper() else "media",
                    "fuente": _fuente(nombre, pagina, o["rect"], hoja)})
    return out


def _centro_punto(r) -> pymupdf.Point:
    return pymupdf.Point(_centro_x(r), _centro_y(r))


# ---------- 4. IDs en planta ----------

def ids_en_planta(ruta, pagina: int) -> List[Dict]:
    """IDs de elementos en planta (C#, L#, MH#, V-bxh) con su bbox. NO se asignan a un cruce de ejes."""
    doc, nombre = _abrir(ruta)
    hoja = _hoja_de(doc, pagina)
    out = []
    for l in _lineas(doc[pagina - 1]):
        t = " ".join(l["texto"].split())
        for tipo, patron in IDS_EN_PLANTA:
            if patron.match(t):
                out.append({"texto": t, "tipo": tipo, "bbox": _rect(l["rect"]),
                            "fuente": _fuente(nombre, pagina, l["rect"], hoja)})
                break
    return sorted(out, key=lambda i: (i["bbox"][1], i["bbox"][0]))


# ---------- 5. Notas de modificación ----------

def notas_de_modificacion(ruta, pagina: int) -> List[Dict]:
    """
    Une las líneas contiguas de cada párrafo (mismo tamaño, misma esquina izquierda, interlineado normal) y marca los
    que dicen 'SE MODIFICO', 'EN REEMPLAZO' o 'PLANO ANTERIOR': candidatos a duda, nunca datos.
    """
    doc, nombre = _abrir(ruta)
    hoja = _hoja_de(doc, pagina)
    lineas = sorted(_lineas(doc[pagina - 1]), key=lambda l: (round(l["rect"].x0 / 8), l["rect"].y0))
    parrafos: List[List[Dict]] = []
    for l in lineas:
        for g in parrafos:
            u = g[-1]
            if (abs(u["tam"] - l["tam"]) < 0.6 and abs(u["rect"].x0 - l["rect"].x0) < 6
                    and -0.6 * l["tam"] <= l["rect"].y0 - u["rect"].y1 < 0.9 * l["tam"]):
                g.append(l)
                break
        else:
            parrafos.append([l])
    out = []
    for g in parrafos:
        texto = " ".join(" ".join(l["texto"].split()) for l in g)
        claves = [k for k, p in MARCAS_DE_MODIFICACION if p.search(texto)]
        if claves:
            r = pymupdf.Rect(g[0]["rect"])
            for l in g[1:]:
                r |= l["rect"]
            out.append({"texto": texto, "claves": claves, "lineas": len(g), "bbox": _rect(r),
                        "fuente": _fuente(nombre, pagina, r, hoja)})
    return out


# ---------- 6. Rótulos S-1 / S-2 ----------

def rotulos_de_seccion(ruta, pagina: int) -> List[Dict]:
    """Rótulos S-1, S-2…: su clave lleva la hoja ('26:S-1') porque el mismo S-1 se repite con otro sentido en cada hoja."""
    doc, nombre = _abrir(ruta)
    hoja = _hoja_de(doc, pagina)
    out = []
    for l in _lineas(doc[pagina - 1]):
        t = " ".join(l["texto"].split())
        if _RE_SECCION.match(t):
            clave = t.replace(" ", "")
            out.append({"rotulo": t, "clave": f"{hoja or PENDIENTE}:{clave}", "bbox": _rect(l["rect"]),
                        "fuente": _fuente(nombre, pagina, l["rect"], hoja)})
    return sorted(out, key=lambda r: (r["bbox"][1], r["bbox"][0]))
