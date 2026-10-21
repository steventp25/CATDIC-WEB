# backend/reglas_ingenieria.py
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

PENDIENTE = "pendiente de verificar"


def _normalizar_texto(texto: str) -> str:
    """Mayúsculas, sin tildes y con espacios simples (D3, D11, N10, N12)."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_tildes.upper()).strip()


# =====================================================================
# 1. REGLA DE RECUBRIMIENTOS Y MEDIDAS EN OBRA (CLAUDE.md §4.5)
# =====================================================================
# Recubrimiento por lado según las categorías de §4.5
RECUBRIMIENTO_POR_CATEGORIA_M = {
    "ZAPATAS Y MUROS DE CONTENCION": 0.075,
    "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.": 0.040,
    "LOSAS Y ESCALERAS": 0.025,
}

# Tipo de elemento (normalizado, sin tildes) -> categoría de §4.5 (N3)
CATEGORIA_POR_TIPO = {
    "ZAPATA": "ZAPATAS Y MUROS DE CONTENCION",  # N3
    "ZAPATA AISLADA": "ZAPATAS Y MUROS DE CONTENCION",
    "ZAPATA COMBINADA": "ZAPATAS Y MUROS DE CONTENCION",
    "ZAPATA DE MURO": "ZAPATAS Y MUROS DE CONTENCION",
    "MURO DE CONTENCION": "ZAPATAS Y MUROS DE CONTENCION",
    "PLATEA": "ZAPATAS Y MUROS DE CONTENCION",  # N15: cimentación, 0.075 (Steven)
    "COLUMNA": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",  # N3
    "COLUMNA RECTANGULAR": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",
    "COLUMNA CIRCULAR": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",  # D3 / P3
    "VIGA": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",  # N3
    "VIGA HORMIGON": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",
    "VIGA DE AMARRE": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",  # D3 / P3
    "RIOSTRA": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",
    "PORTICO": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",
    "MURO H.A.": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",  # N3
    "MURO DE HORMIGON": "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.",
    "LOSA": "LOSAS Y ESCALERAS",  # N3
    "LOSA ALIGERADA": "LOSAS Y ESCALERAS",
    "LOSA MACIZA": "LOSAS Y ESCALERAS",
    "RAMPA DE ESCALERA": "LOSAS Y ESCALERAS",
    "ESCALERA": "LOSAS Y ESCALERAS",  # D3 / P3
}
# Perfiles metálicos, conexiones metálicas y metaldeck no tienen categoría (P3): pendiente de verificar.

# Tabla derivada tipo -> recubrimiento (se conserva el nombre anterior)
RECUBRIMIENTO_POR_LADO_M = {
    tipo: RECUBRIMIENTO_POR_CATEGORIA_M[cat] for tipo, cat in CATEGORIA_POR_TIPO.items()
}

TIPOS_ESCALERA = {"RAMPA DE ESCALERA", "ESCALERA"}  # D7 / P3


def obtener_categoria_elemento(tipo_elemento: str) -> str:
    """Devuelve la categoría de §4.5 del tipo (sin distinguir tildes ni mayúsculas)."""
    tipo_norm = _normalizar_texto(tipo_elemento)
    if tipo_norm not in CATEGORIA_POR_TIPO:
        # T9 / O10 (auditoría Gemini): mismo texto 'pendiente de verificar' en minúscula
        raise ValueError(f"{PENDIENTE}: recubrimiento no definido para '{tipo_elemento}'")
    return CATEGORIA_POR_TIPO[tipo_norm]


def obtener_recubrimiento(tipo_elemento: str) -> float:
    return RECUBRIMIENTO_POR_CATEGORIA_M[obtener_categoria_elemento(tipo_elemento)]

def evaluar_medida_acero_obra(
    tipo_elemento: str,
    valor_plano_m: float,
    medida_acero_campo_m: Optional[float],
    tolerancia_m: Optional[float] = None
) -> Dict[str, object]:
    """
    Suma 2 * recubrimiento a la medida tomada sobre el acero en campo.
    Si coincide con el plano, la columna OBRA lleva el valor del plano.
    tolerancia_m llega como dato de la visita; si es None se compara con
    igualdad exacta (D2 / P2).
    T9 / O8 (auditoría Gemini): una tolerancia negativa o no numérica no se
    corrige ni se ignora -> ValueError 'pendiente de verificar'.
    """
    rec = obtener_recubrimiento(tipo_elemento)
    # N1: sin valor del plano no hay comparación posible
    if valor_plano_m is None:
        raise ValueError(f"{PENDIENTE}: falta el valor del plano para '{tipo_elemento}'.")
    # T9 / O8: la tolerancia de la visita debe ser un número >= 0
    if tolerancia_m is not None:
        if isinstance(tolerancia_m, bool) or not isinstance(tolerancia_m, (int, float)):
            raise ValueError(f"{PENDIENTE}: tolerancia de la visita no numérica ({tolerancia_m!r}).")
        if tolerancia_m < 0:
            raise ValueError(f"{PENDIENTE}: tolerancia de la visita negativa ({tolerancia_m}).")
    if medida_acero_campo_m is None:
        return {
            "valor_columna_obra_m": valor_plano_m,
            "recubrimiento_min_m": rec,
            "recubrimiento_max_m": rec,
            "conforme": True,
            "hallazgo_interno": "Pendiente de verificación de medida en campo (solo ubicación/fotos)."
        }

    medida_corregida_concreto = round(medida_acero_campo_m + (2.0 * rec), 4)
    diferencia = round(medida_corregida_concreto - valor_plano_m, 4)

    # D2 / P2: sin tolerancia de la visita -> igualdad exacta
    conforme = diferencia == 0 if tolerancia_m is None else abs(diferencia) <= tolerancia_m
    if conforme:
        return {
            "valor_columna_obra_m": valor_plano_m,
            "recubrimiento_min_m": rec,
            "recubrimiento_max_m": rec,
            "conforme": True,
            "hallazgo_interno": None
        }
    else:
        return {
            "valor_columna_obra_m": medida_corregida_concreto,
            "recubrimiento_min_m": rec,
            "recubrimiento_max_m": rec,
            "conforme": False,
            "hallazgo_interno": (
                f"Discrepancia tras corrección de recubrimiento ({2*rec:.3f}m): "
                f"Plano={valor_plano_m:.2f}m vs Obra corregida={medida_corregida_concreto:.2f}m "
                f"(medido en acero={medida_acero_campo_m:.2f}m, dif={diferencia:+.3f}m)."
            )
        }


# =====================================================================
# 2. FORMATO ESTRICTO DEL CAMPO EJES (CLAUDE.md §4.4)
# =====================================================================
# D4 + T4b (respuesta de Steven): ejes con prima opcional, p. ej. A' o 2'
_PATRON_EJE_LETRA = r"[A-ZÑ]+'?"
_PATRON_EJE_NUMERO = r"\d+'?"
# T4b: EJES de platea como área, ejemplo de Steven '(A-B),(1-2)'
_RE_EJES_AREA = re.compile(
    rf"\({_PATRON_EJE_LETRA}-{_PATRON_EJE_LETRA}\),\({_PATRON_EJE_NUMERO}-{_PATRON_EJE_NUMERO}\)"
)


def _es_eje_letra(valor: Optional[str]) -> bool:
    # D4: el eje-letra solo lleva letras (T4b: prima opcional, A')
    return bool(valor) and re.fullmatch(_PATRON_EJE_LETRA, valor.strip().upper()) is not None


def _es_eje_numero(valor: Optional[str]) -> bool:
    # D4: el eje-número solo lleva dígitos (T4b: prima opcional, 2')
    return bool(valor) and re.fullmatch(_PATRON_EJE_NUMERO, valor.strip()) is not None


# T7 (auditoría Gemini, CLAUDE.md §4.3): extremo de tramo en el muro de contención
TOKEN_MURO_CONTENCION = "MC"


def _familia_eje_tramo(valor: Optional[str]) -> Optional[str]:
    """
    T7: clasifica un eje de pórtico/viga como 'LETRA', 'NUMERO' o 'MC'
    (muro de contención, sin prima). Cualquier otra cosa -> None.
    """
    if not isinstance(valor, str) or not valor.strip():
        return None
    token = valor.strip().upper()
    if token == TOKEN_MURO_CONTENCION:
        return "MC"
    if token.rstrip("'") == TOKEN_MURO_CONTENCION:
        return None  # "MC'" no existe: no se adivina si es MC o un eje-letra
    if re.fullmatch(_PATRON_EJE_NUMERO, token):
        return "NUMERO"
    if re.fullmatch(_PATRON_EJE_LETRA, token):
        return "LETRA"
    return None


def _tramo_coherente(principal: Optional[str], extremo_1: Optional[str], extremo_2: Optional[str]) -> bool:
    """
    T7 (auditoría Gemini): el eje principal es letra o número; cada extremo es
    de la otra familia o 'MC'. 'MC-MC', vacíos, extremos de la misma familia
    que el principal o tokens inválidos -> False ('pendiente de verificar').
    """
    fam_principal = _familia_eje_tramo(principal)
    if fam_principal not in ("LETRA", "NUMERO"):
        return False
    permitidas = {"NUMERO", "MC"} if fam_principal == "LETRA" else {"LETRA", "MC"}
    fam_1 = _familia_eje_tramo(extremo_1)
    fam_2 = _familia_eje_tramo(extremo_2)
    if fam_1 not in permitidas or fam_2 not in permitidas:
        return False
    return not (fam_1 == "MC" and fam_2 == "MC")


def interpretar_eje_de_visita(texto: Optional[str]) -> Union[Tuple[str, str], str]:
    """
    Lee el cruce puntual tal como viene escrito en la visita y devuelve
    (eje_letra, eje_numero), o 'pendiente de verificar'.

    Regla de Steven (T4b): si el elemento en la visita dice solamente 'A1' o
    '1A', está ubicado en los ejes A y 1; el orden letra/número suele venir
    cruzado, así que se aceptan ambos órdenes. Se admite prima opcional en la
    letra y en el número ('A'1', '1A'', 'A2'') y minúsculas.

    Solo se acepta un token que sea exactamente letra(s)+prima opcional y
    número+prima opcional, en cualquier orden. Cualquier otra cosa (guiones,
    espacios internos, varios números, vacío) -> 'pendiente de verificar':
    no se adivina (Regla de Oro #1).
    """
    if not texto or not texto.strip():
        return PENDIENTE
    token = texto.strip().upper()
    m = re.fullmatch(rf"({_PATRON_EJE_LETRA})({_PATRON_EJE_NUMERO})", token)
    if m:
        return (m.group(1), m.group(2))
    m = re.fullmatch(rf"({_PATRON_EJE_NUMERO})({_PATRON_EJE_LETRA})", token)
    if m:
        return (m.group(2), m.group(1))
    return PENDIENTE


def formatear_campo_ejes(
    caso: str,
    eje_letra_1: Optional[str] = None,
    eje_letra_2: Optional[str] = None,
    eje_num_1: Optional[str] = None,
    eje_num_2: Optional[str] = None,
    referencia_unica: Optional[str] = None
) -> str:
    """
    Aplica la tabla obligatoria del formato EJES:
    - 'losa' o 'viga_sin_eje_letra' -> '—'
    - 'cruce_puntual' (columna, zapata) -> 'EJE F-11'
    - 'muro_entre_letras' -> 'EJE D-E,4' (con coma, sin 'FILA' ni paréntesis)
    - 'viga_recta_sobre_letra' -> 'EJE C, ENTRE 2-3'
    - 'tramo_portico' -> 'EJE F ENTRE 10-11'
    - 'area' (platea) -> '(A-B),(1-2)' con eje_letra_1/2 y eje_num_1/2.
      Formato dado por Steven (T4b); las losas siguen con '—' (§4.4).
    - 'elemento_unico_en_planta' -> devuelve referencia_unica en mayúsculas,
      o '—' si no se pasa referencia. Caso que no figura en el CLAUDE.md §4.4;
      se conserva documentado por decisión de Steven (P6).
    Los ejes-letra deben ser letras y los ejes-número dígitos (D4), ambos con
    prima opcional ('A'', '2'', T4b); si faltan o no cumplen -> 'pendiente de verificar'.

    T7 (auditoría Gemini, CLAUDE.md §4.3) en 'viga_recta_sobre_letra' y
    'tramo_portico': eje_letra_1 es el EJE PRINCIPAL (letra o número, con prima)
    y eje_num_1 / eje_num_2 son los EXTREMOS del tramo, que pueden ser números,
    letras o 'MC' (muro de contención). Si el principal es letra, cada extremo
    es número o 'MC'; si es número, cada extremo es letra o 'MC'. Ejemplos:
    1 / MC / A -> 'EJE 1 ENTRE MC-A'; 1 / B / D -> 'EJE 1 ENTRE B-D';
    B / MC / 1 -> 'EJE B ENTRE MC-1'. 'MC-MC', extremos vacíos, de la misma
    familia que el principal o tokens inválidos -> 'pendiente de verificar'
    (así se siguen rechazando los argumentos invertidos, D4).
    """
    caso = caso.lower().strip()
    if caso in ("losa", "viga_sin_eje_letra"):
        return "—"
    if caso == "cruce_puntual":
        if not _es_eje_letra(eje_letra_1) or not _es_eje_numero(eje_num_1):
            return PENDIENTE
        return f"EJE {eje_letra_1.strip().upper()}-{eje_num_1.strip()}"
    if caso == "muro_entre_letras":
        if not _es_eje_letra(eje_letra_1) or not _es_eje_letra(eje_letra_2) or not _es_eje_numero(eje_num_1):
            return PENDIENTE
        return f"EJE {eje_letra_1.strip().upper()}-{eje_letra_2.strip().upper()},{eje_num_1.strip()}"
    if caso in ("viga_recta_sobre_letra", "tramo_portico"):
        # T7: eje principal letra o número; extremos de la otra familia o 'MC'
        if not _tramo_coherente(eje_letra_1, eje_num_1, eje_num_2):
            return PENDIENTE
        principal = eje_letra_1.strip().upper()
        extremos = f"{eje_num_1.strip().upper()}-{eje_num_2.strip().upper()}"
        if caso == "viga_recta_sobre_letra":
            return f"EJE {principal}, ENTRE {extremos}"
        return f"EJE {principal} ENTRE {extremos}"
    if caso == "area":
        # T4b: platea como área '(A-B),(1-2)'
        if (not _es_eje_letra(eje_letra_1) or not _es_eje_letra(eje_letra_2)
                or not _es_eje_numero(eje_num_1) or not _es_eje_numero(eje_num_2)):
            return PENDIENTE
        return (f"({eje_letra_1.strip().upper()}-{eje_letra_2.strip().upper()}),"
                f"({eje_num_1.strip()}-{eje_num_2.strip()})")
    if caso == "elemento_unico_en_planta":
        return referencia_unica.strip().upper() if referencia_unica else "—"
    return PENDIENTE


# =====================================================================
# 3. CÁLCULO REAL DE CUANTÍA POR ELEMENTO (CLAUDE.md §4.6)
# =====================================================================
AREA_BARRA_CM2 = {
    '3/8"': 0.71, '#3': 0.71,
    '1/2"': 1.29, '#4': 1.29,
    '5/8"': 1.99, '#5': 1.99,
    '3/4"': 2.84, '#6': 2.84,
    '7/8"': 3.87, '#7': 3.87,
    '1"':   5.10, '#8': 5.10,
    '1-1/8"': 6.45, '#9': 6.45,
    '1-1/4"': 8.19, '#10': 8.19,
    '1-3/8"': 10.06, '#11': 10.06,
}

def calcular_cuantia_elemento(
    lx_m: float,
    ly_m: float,
    barras: List[Tuple[int, str]],
    en_porcentaje: bool = False
) -> float:
    """
    Calcula As_total / (Lx * Ly) a partir de una lista [(cantidad, diametro), ...].
    Nunca copia valores de informes anteriores.
    Si en_porcentaje=True (para CATDIC-STP), devuelve el valor en % (ej. 1.85).
    Si en_porcentaje=False (para STP-MIVED), devuelve razón decimal (ej. 0.0185).
    """
    if lx_m <= 0 or ly_m <= 0:
        # T9 / O9 (auditoría Gemini): el mensaje dice 'pendiente de verificar'
        raise ValueError(f"{PENDIENTE}: dimensiones de sección inválidas para cálculo de cuantía.")
    # N2: sin barras no se inventa una cuantía 0.0
    if not barras:
        raise ValueError(f"{PENDIENTE}: no hay barras para calcular la cuantía.")
    area_seccion_cm2 = (lx_m * 100.0) * (ly_m * 100.0)
    as_total_cm2 = 0.0
    for cant, diam in barras:
        if cant <= 0:  # N2
            raise ValueError(f"{PENDIENTE}: cantidad de barras inválida ({cant}) para '{diam}'.")
        diam_limpio = diam.replace("Ø", "").strip()
        if diam_limpio not in AREA_BARRA_CM2:
            raise ValueError(f"Diámetro '{diam}' pendiente de verificar en tabla de áreas.")
        as_total_cm2 += cant * AREA_BARRA_CM2[diam_limpio]

    cuantia = as_total_cm2 / area_seccion_cm2
    return round(cuantia * 100.0, 2) if en_porcentaje else round(cuantia, 4)


# =====================================================================
# 4. AGRUPACIÓN SECUENCIAL DEL LOG FOTOGRÁFICO (CLAUDE.md §4.7 M1 y §4.3)
# =====================================================================
def agrupar_log_fotografico_visita(lista_fotos_log: List[Dict[str, str]]) -> List[Dict[str, object]]:
    """
    Recibe el log secuencial de fotos de la app CATDIC:
    [{'archivo': 'foto_01.jpg', 'etiqueta_elemento': 'C1 A4', 'leyenda': ''}, ...]
    Agrupa secuencialmente: una etiqueta de elemento abre el elemento y las
    fotos siguientes sin etiqueta nueva le pertenecen.
    Pórticos (P9): 'P eje X' abre el eje y cada 'Tramo n-n' (en etiqueta o
    leyenda) abre un elemento singular 'X (n-n)'. Un mismo tramo puede abrir
    varios elementos (elementos grandes o complejos, N6).
    Los grupos sin elemento claro llevan 'duda' = 'pendiente de verificar...'
    para la bandeja 'Con dudas' (D6a, D6c). T8 / O5 (auditoría Gemini): una
    etiqueta con 'Tramo n-n' sin pórtico abierto abre un grupo con
    id_sugerido 'pendiente de verificar' y 'duda' (nunca id 'TRAMO').
    """
    elementos_agrupados = []
    actual = None
    portico_activo = None

    def _abrir(etiqueta_apertura, id_sugerido, es_tramo, archivo, leyenda, duda=None):
        grupo = {
            "orden_en_log": len(elementos_agrupados) + 1,
            "etiqueta_apertura": etiqueta_apertura,
            "id_sugerido": id_sugerido,
            "es_portico_tramo": es_tramo,
            "fotos": [archivo],
            "leyendas_medicion": [leyenda] if leyenda else [],
            "duda": duda,
        }
        elementos_agrupados.append(grupo)
        return grupo

    patron_tramo = r"Tramo\s+([A-Z0-9]+\s*-\s*[A-Z0-9]+)"
    for idx, item in enumerate(lista_fotos_log, start=1):
        etiqueta = (item.get("etiqueta_elemento") or "").strip()
        leyenda = (item.get("leyenda") or "").strip()
        archivo = item["archivo"]

        # Caso especial Pórticos: "P eje X" abre el eje; cada "Tramo n-n" es un elemento singular
        m_eje = re.match(r"^P\s+eje\s+([A-Z0-9]+)", etiqueta, re.IGNORECASE)
        tramo_en_etiqueta = re.search(patron_tramo, etiqueta, re.IGNORECASE)
        if m_eje:
            portico_activo = m_eje.group(1).upper()
        elif etiqueta and not tramo_en_etiqueta:
            portico_activo = None  # D6b: otro elemento cierra el pórtico

        # N5: el tramo se busca en la etiqueta y también en la leyenda
        es_tramo_nuevo = tramo_en_etiqueta or re.search(patron_tramo, leyenda, re.IGNORECASE)

        if es_tramo_nuevo and portico_activo:
            tramo = es_tramo_nuevo.group(1).replace(" ", "")
            id_portico_tramo = f"{portico_activo} ({tramo})"
            actual = _abrir(f"P eje {portico_activo} - Tramo {tramo}", id_portico_tramo, True, archivo, leyenda)
        elif m_eje:
            # D6c: "P eje X" sin tramo no crea un elemento con id "P"
            actual = _abrir(etiqueta, PENDIENTE, False, archivo, leyenda,
                            duda=f"{PENDIENTE}: foto del pórtico eje {portico_activo} sin tramo.")
        elif tramo_en_etiqueta:
            # T8 / O5 (auditoría Gemini): 'Tramo n-n' sin 'P eje X' abierto no
            # crea un elemento con id 'TRAMO'; queda en duda como en D6c
            actual = _abrir(etiqueta, PENDIENTE, False, archivo, leyenda,
                            duda=f"{PENDIENTE}: tramo '{tramo_en_etiqueta.group(1)}' sin pórtico abierto ('P eje X').")
        elif etiqueta:
            actual = _abrir(etiqueta, etiqueta.split()[0].upper(), False, archivo, leyenda)
        else:
            # Foto sin etiqueta nueva: pertenece al elemento actualmente abierto
            if actual is not None:
                actual["fotos"].append(archivo)
                if leyenda:
                    actual["leyendas_medicion"].append(leyenda)
            else:
                # D6a: fotos antes de la primera etiqueta no se descartan
                actual = _abrir("", PENDIENTE, False, archivo, leyenda,
                                duda=f"{PENDIENTE}: fotos antes de la primera etiqueta del log.")

    return elementos_agrupados


def _repartir_fotos(fotos: List[str], maximo: int) -> List[str]:
    """Elige 'maximo' fotos repartidas en la secuencia, con la primera y la última, en orden."""
    if len(fotos) <= maximo:
        return fotos
    paso = (len(fotos) - 1) / float(maximo - 1)
    indices = [round(i * paso) for i in range(maximo)]
    return [fotos[i] for i in indices]


def seleccionar_fotos_m1(fotos: List[str], tipo_elemento: str) -> List[str]:
    """
    M1 · FOTO DEL LEVANTAMIENTO (HV-LEV):
    Incluye TODAS las fotos del elemento salvo en escaleras (RAMPA DE ESCALERA o
    ESCALERA): tope de 9 fotos repartidas a lo largo de la secuencia.
    """
    if _normalizar_texto(tipo_elemento) in TIPOS_ESCALERA:  # D7 / P3
        return _repartir_fotos(fotos, 9)
    return fotos


def seleccionar_fotos_pick4(fotos: List[str]) -> List[str]:
    """
    M1 · STP-MIVED hoja fotográfica (D7): hasta 4 fotos repartidas en la
    secuencia (primera y última incluidas, en orden); con 1 foto va 1 grande.
    """
    return _repartir_fotos(fotos, 4)


# =====================================================================
# 5. CÁLCULO DE GROSOR DEL RECUADRO ROJO EN LOCALIZACIÓN (CLAUDE.md §4.7 M3)
# =====================================================================
def calcular_grosor_recuadro_rojo(
    ancho_fuente_px: int,
    alto_fuente_px: int,
    ancho_celda_px: int,
    alto_celda_px: int,
    grosor_deseado_px: float = 4.5
) -> int:
    """
    Compensa el factor de reducción de la planta estructural completa para que
    el recuadro rojo se vea de ~4.5 px en el PDF final: grosor = 4.5 / factor.
    factor = el menor entre ancho y alto (la planta se encaja completa, D8 / P8).
    Datos <= 0 -> ValueError 'pendiente de verificar'. Mínimo 4 px (P8).
    """
    if min(ancho_fuente_px, alto_fuente_px, ancho_celda_px, alto_celda_px, grosor_deseado_px) <= 0:
        raise ValueError(f"{PENDIENTE}: dimensiones inválidas para el grosor del recuadro rojo.")
    factor_escala = min(ancho_celda_px / float(ancho_fuente_px), alto_celda_px / float(alto_fuente_px))
    grosor_fuente = round(grosor_deseado_px / factor_escala)
    return max(4, grosor_fuente)


# =====================================================================
# 6. ARCHIVADOR SIN SOBRESCRITURA (CLAUDE.md §5.2)
# =====================================================================
def obtener_ruta_salida_sin_sobrescribir(carpeta_salida: Path, nombre_base_pdf: str) -> Path:
    """
    Garantiza la regla: 'Siempre archivo nuevo, nunca sobrescribir'.
    Si 'Informe.pdf' existe, devuelve 'Informe v2.pdf', 'Informe v3.pdf', etc.
    Solo consulta: no crea carpetas (D9); quien escribe el archivo la crea.
    """
    candidato = carpeta_salida / nombre_base_pdf
    if not candidato.exists():
        return candidato

    stem = candidato.stem
    suffix = candidato.suffix
    version = 2
    while True:
        nuevo_candidato = carpeta_salida / f"{stem} v{version}{suffix}"
        if not nuevo_candidato.exists():
            return nuevo_candidato
        version += 1


# =====================================================================
# 6b. FECHA DD/MM/AAAA (CLAUDE.md §5.2, D10)
# =====================================================================
def formatear_fecha_ddmmaaaa(fecha: date) -> str:
    """Devuelve la fecha en el formato obligatorio DD/MM/AAAA (con ceros)."""
    if not isinstance(fecha, date):
        raise ValueError(f"{PENDIENTE}: fecha inválida '{fecha}'.")
    return fecha.strftime("%d/%m/%Y")


def _es_fecha_ddmmaaaa_valida(fecha: str) -> bool:
    # D10: formato DD/MM/AAAA y fecha real del calendario
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", fecha):
        return False
    try:
        datetime.strptime(fecha, "%d/%m/%Y")
    except ValueError:
        return False
    return True


# =====================================================================
# 7. AUDITOR AUTOMÁTICO CONTRA LOS 18 ERRORES RECURRENTES (CLAUDE.md §6)
# =====================================================================
# Unidad de la cuantía impresa por formato (§4.6): decimal o porcentaje
CUANTIA_EN_PORCENTAJE_POR_FORMATO = {
    "STP-MIVED": False,   # §4.6: decimal (ej. 0.0185)
    "CATDIC-STP": True,   # §4.6: porcentaje (ej. 1.85, 2 decimales P5)
}
DECIMALES_CUANTIA = {False: 4, True: 2}  # mismo redondeo que calcular_cuantia_elemento


def _a_numero(valor: object) -> Optional[float]:
    """Convierte int/float o texto numérico ('0.0185', '1.85%') a float; si no se puede -> None."""
    if isinstance(valor, bool) or valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        try:
            return float(valor.strip().rstrip("%").strip())
        except ValueError:
            return None
    return None


def _auditar_cuantia_ficha(ficha_data: Dict[str, object], formato: str) -> List[str]:
    """Error #12 (cuantía copiada): la cuantía declarada debe ser la recalculada (§4.6)."""
    if ficha_data.get("cuantia_declarada") is None:
        return []  # la ficha no imprime cuantía: nada que comparar
    if formato not in CUANTIA_EN_PORCENTAJE_POR_FORMATO:
        return [f"Error #12: unidad de cuantía no definida para el formato '{formato}' ({PENDIENTE})."]
    en_pct = CUANTIA_EN_PORCENTAJE_POR_FORMATO[formato]
    declarada = _a_numero(ficha_data.get("cuantia_declarada"))
    if declarada is None:
        return [f"Error #12: la cuantía declarada '{ficha_data.get('cuantia_declarada')}' no es numérica ({PENDIENTE})."]

    b = _a_numero(ficha_data.get("seccion_b_m"))
    h = _a_numero(ficha_data.get("seccion_h_m"))
    barras = ficha_data.get("barras_longitudinales")
    if b is None or h is None or not barras:
        # Regla de Oro #1: sin datos no se puede recalcular y no se supone que esté bien
        return [f"Error #12: faltan sección (b, h) o barras para recalcular la cuantía ({PENDIENTE})."]
    try:
        calculada = calcular_cuantia_elemento(b, h, list(barras), en_porcentaje=en_pct)
    except (ValueError, TypeError) as exc:
        return [f"Error #12: no se pudo recalcular la cuantía ({PENDIENTE}): {exc}"]

    if round(declarada, DECIMALES_CUANTIA[en_pct]) != calculada:
        unidad = "%" if en_pct else "decimal"
        return [f"Error #12: cuantía no coincide con el cálculo (declarada={declarada}, "
                f"calculada={calculada} {unidad})."]
    return []


def _auditar_columna_obra(ficha_data: Dict[str, object]) -> List[str]:
    """Error #12 (OBRA sin corrección): cada valor OBRA debe salir de evaluar_medida_acero_obra (§4.5, D1, P2)."""
    medidas = ficha_data.get("medidas_obra")
    if not medidas:
        return []  # la ficha no trae comparaciones plano/obra
    errores = []
    tipo = ficha_data.get("tipo_elemento")
    if not isinstance(tipo, str):
        tipo = ""  # T9: sin tipo de texto -> recubrimiento 'pendiente de verificar' (ValueError controlado)
    tolerancia = ficha_data.get("tolerancia_visita_m")  # T9 / O8: negativa o no numérica -> ValueError controlado
    for i, m in enumerate(medidas, start=1):
        etiqueta = m.get("dimension") or f"medida {i}"
        plano = _a_numero(m.get("valor_plano_m"))
        obra = _a_numero(m.get("valor_obra_m"))
        acero_crudo = m.get("medida_acero_campo_m")
        acero = _a_numero(acero_crudo)
        if plano is None or obra is None or (acero_crudo is not None and acero is None):
            errores.append(f"Error #12: columna OBRA de '{etiqueta}' sin datos numéricos para verificarla ({PENDIENTE}).")
            continue
        try:
            esperado = evaluar_medida_acero_obra(tipo, plano, acero, tolerancia)["valor_columna_obra_m"]
        except ValueError as exc:
            errores.append(f"Error #12: columna OBRA de '{etiqueta}' no verificable ({PENDIENTE}): {exc}")
            continue
        if round(obra, 4) != round(esperado, 4):
            errores.append(f"Error #12: columna OBRA de '{etiqueta}' no coincide con la corrección por "
                           f"recubrimiento (OBRA={obra}, esperado={esperado}).")
    return errores


# T9 (auditoría Gemini): error que se reporta si un campo de texto llega con otro tipo
ERROR_POR_CAMPO_TEXTO = {
    "tipo_elemento": "#9/#11/#12",
    "observaciones_texto": "#9/#10",
    "ejes": "#11",
    "nombre_proyecto": "#8",
    "fecha": "#12",
}


def _campo_texto_ficha(ficha_data: Dict[str, object], clave: str, errores: List[str]) -> Tuple[str, bool]:
    """
    T9 (auditoría Gemini): devuelve (texto, es_valido). None o ausente -> ('', True).
    Un valor que no sea str (date, int...) no se convierte ni revienta el auditor:
    se reporta como error con 'pendiente de verificar' y se usa ''.
    """
    valor = ficha_data.get(clave)
    if valor is None:
        return "", True
    if isinstance(valor, str):
        return valor, True
    errores.append(f"Error {ERROR_POR_CAMPO_TEXTO[clave]}: el campo '{clave}' no es texto "
                   f"(tipo {type(valor).__name__}, valor {valor!r}; {PENDIENTE}).")
    return "", False


def auditar_datos_ficha_antes_de_renderizar(ficha_data: Dict[str, object], formato: str) -> List[str]:
    """
    Revisa automáticamente el diccionario de la ficha antes de generar el PDF
    para bloquear cualquiera de los 18 errores documentados en el CLAUDE.md §6.
    Los textos se comparan sin tildes ni mayúsculas (D11, N10, N12).

    Claves de la ficha que usa el auditor:
    - 'tipo_elemento', 'observaciones_texto', 'ejes', 'nombre_proyecto', 'fecha'
      (errores #8, #9, #10, #11, #12 fecha) y 'firma_inspector_imagen' /
      'firma_texto_fabricado' (#16).
    - Error #12 cuantía (§4.6), solo si viene 'cuantia_declarada':
        'cuantia_declarada'      valor que se imprimirá (decimal en STP-MIVED,
                                 % en CATDIC-STP; número o texto '1.85%').
        'seccion_b_m', 'seccion_h_m'  dimensiones de la sección en m.
        'barras_longitudinales'  [(cantidad, diámetro), ...] como en
                                 calcular_cuantia_elemento.
      Si faltan datos para recalcular, o el formato no define la unidad, el
      error dice 'pendiente de verificar' (nunca se da por buena).
    - Error #12 columna OBRA (§4.5), solo si viene 'medidas_obra':
        'medidas_obra'  [{'dimension': 'b' (opcional), 'valor_plano_m': 0.40,
                          'medida_acero_campo_m': 0.32 o None (D1),
                          'valor_obra_m': 0.40}, ...]
        'tolerancia_visita_m'  tolerancia de la visita (P2); None -> igualdad exacta.
      Usa 'tipo_elemento' para el recubrimiento. OBRA debe ser igual (a 4
      decimales) a evaluar_medida_acero_obra; datos faltantes -> 'pendiente de verificar'.
      Una tolerancia negativa o no numérica es error #12 controlado (T9 / O8).
    - T9 (auditoría Gemini): 'tipo_elemento', 'observaciones_texto', 'ejes',
      'nombre_proyecto' y 'fecha' deben ser str; con otro tipo (p. ej. date o
      int) se reporta el error de ERROR_POR_CAMPO_TEXTO con 'pendiente de
      verificar', sin lanzar TypeError.
    """
    errores = []
    tipo_txt, _ = _campo_texto_ficha(ficha_data, "tipo_elemento", errores)
    texto_obs, _ = _campo_texto_ficha(ficha_data, "observaciones_texto", errores)
    ejes, _ = _campo_texto_ficha(ficha_data, "ejes", errores)
    nombre_txt, _ = _campo_texto_ficha(ficha_data, "nombre_proyecto", errores)
    fecha, fecha_es_texto = _campo_texto_ficha(ficha_data, "fecha", errores)
    tipo = _normalizar_texto(tipo_txt)
    texto_norm = _normalizar_texto(texto_obs)
    lineas_norm = [_normalizar_texto(l) for l in texto_obs.splitlines() if l.strip()]
    nombre_proy = _normalizar_texto(nombre_txt)

    # Error 8: NOMBRE PROYECTO con sufijo de visita o nivel en HV-LEV (D11: sin tildes)
    if formato == "HV-LEV" and any(p in nombre_proy for p in ["VISITA", "SOTANO", "NIVEL", "PARCIAL", "COMPLETIVO"]):
        errores.append("Error #8: NOMBRE PROYECTO no puede llevar sufijo de visita ni nivel en HV-LEV.")

    # Error 9a: Palabra prohibida "CORRIDO" en rótulos de acero (N8: palabra completa)
    if re.search(r"\bCORRIDOS?\b", texto_norm):
        errores.append("Error #9: Está prohibido usar la palabra 'CORRIDO' en rótulos de acero.")

    # Error 9b: Toda viga debe llevar ESTRIBOS al final (D11, N10)
    if "VIGA" in tipo or "RIOSTRA" in tipo or "PORTICO" in tipo:
        if "ESTRIBOS" not in texto_norm:
            errores.append("Error #9: Toda viga/riostra/pórtico debe incluir obligatoriamente el campo ESTRIBOS.")
        elif not lineas_norm[-1].startswith("ESTRIBOS"):
            errores.append("Error #9: En viga/riostra/pórtico el campo ESTRIBOS debe ir al final.")

    # Regla HV-LEV Columnas: "ESTRIBOSS" con doble S (D11: sin distinguir mayúsculas; N11: toda COLUMNA)
    if formato == "HV-LEV" and tipo.startswith("COLUMNA"):
        if "ESTRIBOSS" not in texto_norm:
            errores.append("Regla HV-LEV Columna: El rótulo exacto debe ser 'ESTRIBOSS' (con doble S).")

    # Error 9c: ACERO ADICIONAL combinado con "+"
    for linea in lineas_norm:
        if "ACERO ADICIONAL" in linea and "+" in linea:
            errores.append("Error #9: ACERO ADICIONAL IZQUIERDO y DERECHO van en líneas separadas, nunca combinados con '+'.")

    # Error 10: Cajas o secciones editoriales prohibidas (P7: sin "NOTA PENDIENTE"; N12: sin tildes)
    prohibidas = ["REFERENCIA DE PLANO", "FUENTE DE LOS DATOS", "VERIFICACION EN CAMPO"]
    for frase in prohibidas:
        if frase in texto_norm:
            errores.append(f"Error #10: Sección no autorizada detectada en OBSERVACIONES: '{frase}'.")

    # Error 11: Ejes de losa distintos de "—" (N15: la PLATEA no es losa)
    if "LOSA" in tipo and ejes != "—":
        errores.append(f"Error #11: Las losas nunca llevan ejes (valor actual: '{ejes}', debe ser '—').")

    # Error 11 / T4b: la PLATEA lleva EJES en formato de área '(A-B),(1-2)' (respuesta de Steven)
    es_platea = "PLATEA" in tipo
    if es_platea and not _RE_EJES_AREA.fullmatch(ejes):
        errores.append(
            f"Error #11: EJES de PLATEA debe tener formato de área '(A-B),(1-2)' "
            f"(valor actual: '{ejes}', {PENDIENTE})."
        )

    # Error 11 / §4.4: EJES de muro sin 'FILA' ni paréntesis (N13; no aplica a la platea)
    if "MURO" in tipo and not es_platea and ("FILA" in _normalizar_texto(ejes) or "(" in ejes or ")" in ejes):
        errores.append(f"Error #11: EJES de muro sin 'FILA' ni paréntesis (valor actual: '{ejes}', formato 'EJE D-E,4').")

    # Error 12: Fecha obligatoria (N14) en formato DD/MM/AAAA y real (D10)
    if not fecha_es_texto:
        pass  # T9: ya reportada como error #12 'pendiente de verificar' (no es str)
    elif not fecha:
        errores.append(f"Error #12: La ficha no tiene fecha ({PENDIENTE}).")
    elif not _es_fecha_ddmmaaaa_valida(fecha):
        errores.append(f"Error #12: La fecha '{fecha}' no cumple el formato obligatorio DD/MM/AAAA.")

    # Error 12: Cuantía recalculada (§4.6) y columna OBRA corregida por recubrimiento (§4.5)
    errores.extend(_auditar_cuantia_ficha(ficha_data, formato))
    errores.extend(_auditar_columna_obra(ficha_data))

    # Error 16: Firmas fabricadas
    if ficha_data.get("firma_inspector_imagen") or ficha_data.get("firma_texto_fabricado"):
        errores.append("Error #16: Las firmas nunca se fabrican; el campo debe quedar en blanco.")

    return errores


# =====================================================================
# 8. AUDITOR DEL ARCHIVO PDF YA GENERADO (CLAUDE.md §5.2, error #15)
# =====================================================================
# §5.2: todo PDF debe pesar < 30 MB. Se toma 30 MB = 30 000 000 bytes (el
# límite más estricto entre MB decimal y MiB), así cumple en ambas lecturas.
PESO_MAXIMO_PDF_BYTES = 30_000_000


def auditar_archivo_pdf_generado(ruta_pdf: Path, destino_existia_antes: Optional[bool]) -> List[str]:
    """
    Error #15: revisa el PDF ya escrito en disco (solo lectura).
    - ruta_pdf: ruta del PDF que se acaba de generar.
    - destino_existia_antes: lo que devolvió ruta_pdf.exists() JUSTO ANTES de
      escribirlo (el generador lo registra). True -> se sobrescribió un archivo
      existente sin crear v2. None -> no se registró: 'pendiente de verificar'.
    Reporta también PDF inexistente y peso >= 30 MB (§5.2 exige < 30 MB).
    """
    errores = []
    ruta = Path(ruta_pdf)
    if destino_existia_antes is None:
        errores.append(f"Error #15: no se registró si el destino ya existía ({PENDIENTE}).")
    elif destino_existia_antes:
        errores.append(f"Error #15: se sobrescribió un archivo existente sin crear v2 ('{ruta.name}').")

    if not ruta.is_file():
        errores.append(f"Error #15: el PDF generado no existe en '{ruta}' ({PENDIENTE}).")
        return errores
    peso = ruta.stat().st_size
    if peso >= PESO_MAXIMO_PDF_BYTES:
        errores.append(f"Error #15: el PDF pesa {peso / 1_000_000:.1f} MB; debe pesar < 30 MB.")
    return errores
