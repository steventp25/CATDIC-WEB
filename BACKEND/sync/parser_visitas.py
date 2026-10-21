# BACKEND/sync/parser_visitas.py
# Etapa 1 · T3 — Lectura de los nombres de las carpetas de visita y de sus PDFs.
#
# Regla de Oro #1: solo se toma lo que está escrito en el nombre. Lo que falte o sea
# ambiguo queda en PENDIENTE y se lista en `campos_pendientes` (va a "Con dudas").
# Nunca se usa la fecha de modificación del archivo (respuesta de Steven P1).
#
# Formatos reales vistos en Terra Living (PLANES/etapa-1.md, D2):
#   "1. FONDO DE SEPTICO", "10 - LOSA S-6 COMPLETIVO", "17.PARCIAL VERTICALES S-3 28-09-2026",
#   "15 LOSAS Y PORTICOS S-5 COMPLETIVO 02-09-2026",
#   "12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026" (clase mixta, P2).
import json
import re
from datetime import date
from typing import Dict, List, Optional, Tuple

from reglas_ingenieria import PENDIENTE

CLASE_PARCIAL = "Parcial"
CLASE_COMPLETIVO = "Completivo"
CLASE_MIXTA = "Mixta"

# Palabras de clase: las de los nombres reales (PARCIAL, PARCIALES, COMPLETIVO) y su
# singular/plural; COMPLETIVA(S) por indicación del coordinador. Sin otros sinónimos.
PALABRAS_CLASE = {
    "PARCIAL": CLASE_PARCIAL,
    "PARCIALES": CLASE_PARCIAL,
    "COMPLETIVO": CLASE_COMPLETIVO,
    "COMPLETIVOS": CLASE_COMPLETIVO,
    "COMPLETIVA": CLASE_COMPLETIVO,
    "COMPLETIVAS": CLASE_COMPLETIVO,
}

# Nombres de campo = columnas de la tabla `visitas` (para la Mesa de Dudas, T5)
CAMPO_NUMERO = "numero"
CAMPO_DESCRIPCION = "descripcion"
CAMPO_FECHA = "fecha_visita"
CAMPO_CLASE = "clase"
_ORDEN_CAMPOS = [CAMPO_NUMERO, CAMPO_DESCRIPCION, CAMPO_FECHA, CAMPO_CLASE]

_RE_CLASE = re.compile(
    r"\b(" + "|".join(sorted(PALABRAS_CLASE, key=len, reverse=True)) + r")\b", re.IGNORECASE
)
# Fecha DD-MM-AAAA (§5.1); no pegada a otros dígitos
_RE_FECHA = re.compile(r"(?<!\d)(\d{2})-(\d{2})-(\d{4})(?!\d)")
# Algo con forma de fecha pero en otro formato (06.05.2026, 6-5-26, 2026.06.016...): no se interpreta
_RE_FECHA_OTRO_FORMATO = re.compile(r"(?<!\d)\d{1,4}[./-]\d{1,2}[./-]\d{1,4}(?!\d)")
# Número de visita al inicio + separador real: "1. ", "10 - ", "17.PARCIAL", "15 LOSAS"
_RE_NUMERO = re.compile(r"^(\d{1,3})(?:\s*[.\-]\s*|\s+)(\S.*)$")
# Conector entre grupos de una clase mixta
_RE_CONECTOR_Y = re.compile(r"\s+Y\s+", re.IGNORECASE)
_RE_EXTENSION_PDF = re.compile(r"\.pdf$", re.IGNORECASE)


def _espacios(texto: str) -> str:
    """Espacios simples y sin bordes (hay nombres con doble espacio)."""
    return re.sub(r"\s+", " ", texto or "").strip()


def _limpiar(texto: str) -> str:
    """Quita espacios dobles y separadores sueltos en los bordes (". ", " - ", ",")."""
    t = _espacios(texto)
    t = re.sub(r"^(?:[.,;]|-(?=\s|$))+\s*", "", t)
    t = re.sub(r"\s*(?:[.,;]|(?<=\s)-)+$", "", t)
    return _espacios(t)


def _leer_fecha(texto: str) -> Tuple[str, str, Optional[str], bool, str]:
    """Devuelve (fecha_iso, fecha_ddmmaaaa, motivo, ambigua, texto_sin_fecha).

    `ambigua` = el nombre trae algo de fecha pero no se puede leer sin adivinar
    (fecha inexistente, varias fechas distintas u otro formato).
    """
    encontradas = list(_RE_FECHA.finditer(texto))
    texto_sin_fecha = _RE_FECHA.sub(" ", texto)
    if not encontradas:
        otra = _RE_FECHA_OTRO_FORMATO.search(texto)
        if otra:
            motivo = f"fecha '{otra.group(0)}' en formato distinto de DD-MM-AAAA; no se interpreta"
            return PENDIENTE, PENDIENTE, motivo, True, texto_sin_fecha
        return PENDIENTE, PENDIENTE, "el nombre no trae fecha DD-MM-AAAA", False, texto_sin_fecha

    distintas = sorted({m.group(0) for m in encontradas})
    if len(distintas) > 1:
        motivo = f"el nombre trae varias fechas ({', '.join(distintas)})"
        return PENDIENTE, PENDIENTE, motivo, True, texto_sin_fecha

    dd, mm, aaaa = encontradas[0].groups()
    try:
        fecha = date(int(aaaa), int(mm), int(dd))
    except ValueError:
        motivo = f"la fecha '{encontradas[0].group(0)}' no existe en el calendario"
        return PENDIENTE, PENDIENTE, motivo, True, texto_sin_fecha
    return fecha.isoformat(), fecha.strftime("%d/%m/%Y"), None, False, texto_sin_fecha


def _clase_de(palabra: str) -> str:
    return PALABRAS_CLASE[palabra.upper()]


def _leer_clase(texto: str) -> Tuple[str, List[Dict[str, str]], Optional[str], bool, str]:
    """Devuelve (clase, clase_detalle, motivo, ambigua, texto_sin_clase).

    Clase mixta (P2): solo si el texto se parte en un único " Y " que deja una sola
    palabra de clase a cada lado, con clases distintas y elementos en ambos lados.
    """
    encontradas = list(_RE_CLASE.finditer(texto))
    if not encontradas:
        return PENDIENTE, [], "el nombre no trae PARCIAL ni COMPLETIVO", False, texto

    clases = {_clase_de(m.group(1)) for m in encontradas}
    if len(clases) == 1:
        return clases.pop(), [], None, False, _RE_CLASE.sub(" ", texto)

    particiones = []
    for conector in _RE_CONECTOR_Y.finditer(texto):
        izquierda, derecha = texto[: conector.start()], texto[conector.end():]
        clases_izq = [_clase_de(m.group(1)) for m in _RE_CLASE.finditer(izquierda)]
        clases_der = [_clase_de(m.group(1)) for m in _RE_CLASE.finditer(derecha)]
        if len(clases_izq) != 1 or len(clases_der) != 1 or clases_izq[0] == clases_der[0]:
            continue
        elem_izq = _limpiar(_RE_CLASE.sub(" ", izquierda))
        elem_der = _limpiar(_RE_CLASE.sub(" ", derecha))
        if elem_izq and elem_der:
            particiones.append([
                {"elementos": elem_izq, "clase": clases_izq[0]},
                {"elementos": elem_der, "clase": clases_der[0]},
            ])

    if len(particiones) == 1:
        detalle = particiones[0]
        texto_sin_clase = " Y ".join(g["elementos"] for g in detalle)
        return CLASE_MIXTA, detalle, None, False, texto_sin_clase

    motivo = "el nombre trae PARCIAL y COMPLETIVO y no se puede partir en grupos sin adivinar"
    return PENDIENTE, [], motivo, True, texto


def _ordenar(campos) -> List[str]:
    return [c for c in _ORDEN_CAMPOS if c in campos]


def interpretar_nombre_carpeta_visita(nombre: str) -> Dict:
    """Lee número, descripción, clase y fecha del nombre de una carpeta de visita (§5.1).

    Devuelve un dict con: nombre_original, numero (int o PENDIENTE), descripcion,
    clase ("Parcial" | "Completivo" | "Mixta" | PENDIENTE), clase_detalle (lista de
    {"elementos", "clase"}; solo con clase Mixta), fecha_iso (AAAA-MM-DD),
    fecha_ddmmaaaa (DD/MM/AAAA, §5.2), campos_pendientes, motivos ({campo: por qué})
    y ambiguos (campos que el nombre trae pero no se pueden leer sin adivinar).
    """
    texto = _espacios(nombre)
    motivos: Dict[str, str] = {}
    ambiguos: List[str] = []

    # 1. Número de visita (un nombre que empieza por fecha no tiene número)
    coincide = None if _RE_FECHA.match(texto) else _RE_NUMERO.match(texto)
    if coincide:
        numero = int(coincide.group(1))
        resto = coincide.group(2)
    else:
        numero = PENDIENTE
        resto = texto
        motivos[CAMPO_NUMERO] = "el nombre no empieza por un número de visita legible"

    # 2. Fecha
    fecha_iso, fecha_ddmmaaaa, motivo, ambigua, resto = _leer_fecha(resto)
    if motivo:
        motivos[CAMPO_FECHA] = motivo
    if ambigua:
        ambiguos.append(CAMPO_FECHA)

    # 3. Clase (puede ir antes o después de los elementos)
    clase, clase_detalle, motivo, ambigua, resto = _leer_clase(resto)
    if motivo:
        motivos[CAMPO_CLASE] = motivo
    if ambigua:
        ambiguos.append(CAMPO_CLASE)

    # 4. Descripción: elementos y nivel, en limpio
    descripcion = _limpiar(resto)
    if not descripcion:
        descripcion = PENDIENTE
        motivos[CAMPO_DESCRIPCION] = "el nombre no trae elementos ni nivel"

    return {
        "nombre_original": nombre,
        "numero": numero,
        "descripcion": descripcion,
        "clase": clase,
        "clase_detalle": clase_detalle,
        "fecha_iso": fecha_iso,
        "fecha_ddmmaaaa": fecha_ddmmaaaa,
        "campos_pendientes": _ordenar(motivos),
        "motivos": motivos,
        "ambiguos": _ordenar(ambiguos),
    }


def interpretar_nombre_pdf_visita(nombre_pdf: str) -> Dict:
    """Lee fecha (DD-MM-AAAA) y clase del nombre del PDF de la visita (respaldo, P1).

    El número que traen algunos PDFs ("4. Verticales Fundacion.pdf") es otra numeración
    y no se usa. Devuelve nombre_original, clase, clase_detalle, fecha_iso,
    fecha_ddmmaaaa, campos_pendientes, motivos y ambiguos.
    """
    texto = _espacios(_RE_EXTENSION_PDF.sub("", _espacios(nombre_pdf)))
    motivos: Dict[str, str] = {}
    ambiguos: List[str] = []

    fecha_iso, fecha_ddmmaaaa, motivo, ambigua, resto = _leer_fecha(texto)
    if motivo:
        motivos[CAMPO_FECHA] = motivo
    if ambigua:
        ambiguos.append(CAMPO_FECHA)

    clase, clase_detalle, motivo, ambigua, _ = _leer_clase(resto)
    if motivo:
        motivos[CAMPO_CLASE] = motivo
    if ambigua:
        ambiguos.append(CAMPO_CLASE)

    return {
        "nombre_original": nombre_pdf,
        "clase": clase,
        "clase_detalle": clase_detalle,
        "fecha_iso": fecha_iso,
        "fecha_ddmmaaaa": fecha_ddmmaaaa,
        "campos_pendientes": _ordenar(motivos),
        "motivos": motivos,
        "ambiguos": _ordenar(ambiguos),
    }


def _clave_clase(datos: Dict) -> Tuple[str, str]:
    return datos["clase"], json.dumps(datos.get("clase_detalle") or [], ensure_ascii=False)


def _clases_contenidas(datos: Dict) -> set:
    """Clases simples que abarca un resultado (las de cada grupo si es Mixta)."""
    if datos["clase"] == CLASE_MIXTA:
        return {g["clase"] for g in datos.get("clase_detalle") or []}
    return {datos["clase"]}


def combinar_datos_visita(datos_carpeta: Dict, datos_pdfs: List[Dict]) -> Dict:
    """Aplica la regla de Steven P1 para fecha y clase de una visita.

    1. Se usa lo que diga el nombre de la carpeta.
    2. Si la carpeta no lo trae, se usa el nombre de los PDFs, solo si todos los PDFs
       que traen el dato coinciden y ninguno lo trae ilegible.
    3. Si no, PENDIENTE (Mesa de Dudas). Si la carpeta trae el dato pero ilegible,
       no se busca en los PDFs: lo decide Steven.
    Nunca se usa la fecha de modificación del archivo.

    Devuelve una copia de `datos_carpeta` con fecha/clase resueltas, `campos_pendientes`
    y `motivos` recalculados, más: origen_fecha y origen_clase ("carpeta" | "pdf" | None),
    pdfs_origen ({campo: [nombres de PDF usados]}) y avisos (discrepancias informativas).
    """
    resultado = dict(datos_carpeta)
    resultado["clase_detalle"] = list(datos_carpeta.get("clase_detalle") or [])
    motivos = dict(datos_carpeta.get("motivos") or {})
    pendientes = set(datos_carpeta.get("campos_pendientes") or [])
    ambiguos_carpeta = set(datos_carpeta.get("ambiguos") or [])
    avisos: List[str] = []
    pdfs_origen: Dict[str, List[str]] = {}
    datos_pdfs = list(datos_pdfs or [])

    # ---- Fecha ----
    origen_fecha = None
    if datos_carpeta["fecha_iso"] != PENDIENTE:
        origen_fecha = "carpeta"
        for pdf in datos_pdfs:
            if pdf["fecha_iso"] != PENDIENTE and pdf["fecha_iso"] != datos_carpeta["fecha_iso"]:
                avisos.append(
                    f"el PDF '{pdf['nombre_original']}' dice {pdf['fecha_ddmmaaaa']}; "
                    f"se usa la fecha de la carpeta ({datos_carpeta['fecha_ddmmaaaa']})"
                )
    elif CAMPO_FECHA not in ambiguos_carpeta:
        con_dato = [p for p in datos_pdfs if p["fecha_iso"] != PENDIENTE]
        ilegibles = [p for p in datos_pdfs if CAMPO_FECHA in (p.get("ambiguos") or [])]
        valores = {p["fecha_iso"] for p in con_dato}
        if len(valores) == 1 and not ilegibles:
            resultado["fecha_iso"] = con_dato[0]["fecha_iso"]
            resultado["fecha_ddmmaaaa"] = con_dato[0]["fecha_ddmmaaaa"]
            origen_fecha = "pdf"
            pdfs_origen[CAMPO_FECHA] = [p["nombre_original"] for p in con_dato]
            pendientes.discard(CAMPO_FECHA)
            motivos.pop(CAMPO_FECHA, None)
        elif valores or ilegibles:
            detalle = [
                f"'{p['nombre_original']}': {p['fecha_ddmmaaaa'] if p in con_dato else p['motivos'].get(CAMPO_FECHA)}"
                for p in con_dato + [p for p in ilegibles if p not in con_dato]
            ]
            motivos[CAMPO_FECHA] = (
                "la carpeta no trae fecha y los PDFs no coinciden o no se pueden leer: "
                + "; ".join(detalle)
            )

    # ---- Clase ----
    origen_clase = None
    if datos_carpeta["clase"] != PENDIENTE:
        origen_clase = "carpeta"
        clases_carpeta = _clases_contenidas(datos_carpeta)
        for pdf in datos_pdfs:
            if pdf["clase"] != PENDIENTE and not _clases_contenidas(pdf) <= clases_carpeta:
                avisos.append(
                    f"el PDF '{pdf['nombre_original']}' dice {pdf['clase']}; "
                    f"se usa la clase de la carpeta ({datos_carpeta['clase']})"
                )
    elif CAMPO_CLASE not in ambiguos_carpeta:
        con_dato = [p for p in datos_pdfs if p["clase"] != PENDIENTE]
        ilegibles = [p for p in datos_pdfs if CAMPO_CLASE in (p.get("ambiguos") or [])]
        valores = {_clave_clase(p) for p in con_dato}
        if len(valores) == 1 and not ilegibles:
            resultado["clase"] = con_dato[0]["clase"]
            resultado["clase_detalle"] = list(con_dato[0].get("clase_detalle") or [])
            origen_clase = "pdf"
            pdfs_origen[CAMPO_CLASE] = [p["nombre_original"] for p in con_dato]
            pendientes.discard(CAMPO_CLASE)
            motivos.pop(CAMPO_CLASE, None)
        elif valores or ilegibles:
            detalle = [
                f"'{p['nombre_original']}': {p['clase'] if p in con_dato else p['motivos'].get(CAMPO_CLASE)}"
                for p in con_dato + [p for p in ilegibles if p not in con_dato]
            ]
            motivos[CAMPO_CLASE] = (
                "la carpeta no trae clase y los PDFs no coinciden o no se pueden leer: "
                + "; ".join(detalle)
            )

    resultado["campos_pendientes"] = _ordenar(pendientes)
    resultado["motivos"] = {c: motivos[c] for c in _ordenar(motivos)}
    resultado["origen_fecha"] = origen_fecha
    resultado["origen_clase"] = origen_clase
    resultado["pdfs_origen"] = pdfs_origen
    resultado["avisos"] = avisos
    return resultado
