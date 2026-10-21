# BACKEND/tests/test_reglas_ingenieria.py
# Etapa 0 · T3 — Pruebas del motor de reglas contra lo que exige el CLAUDE.md
# (§4.4–§4.7, §5.2, §6) y las respuestas de Steven del 21/10/2026 (PLANES/etapa-0.md).
#
# Las pruebas expresan la ESPECIFICACIÓN (CLAUDE.md y respuestas de Steven): cada
# docstring cita la regla verificada y su referencia D#, P#, N#, T4b, T5 o T7–T9
# (ajustes de la auditoría Gemini) (PLANES/etapa-0.md y PLANES/etapa-0-matriz-reglas.md).
#
# Convención de constantes (Regla de Oro #1):
#   - "# SINTÉTICO: no es dato de proyecto"  -> valor inventado solo para probar (P11).
#   - "# NORMA: CLAUDE.md §x"                 -> valor normativo copiado del CLAUDE.md.
#   - "# NORMA: respuesta de Steven Px"        -> valor confirmado por Steven en el plan.
# Ningún valor se guarda en la BD.
import re
import unicodedata
from datetime import date

import pytest

import reglas_ingenieria as ri


# =====================================================================
# CONSTANTES
# =====================================================================
PENDIENTE = "pendiente de verificar"
PENDIENTE_RE = r"(?i)pendiente de verificar"   # N4; desde T9 / O10 todos los mensajes van en minúscula
GUION_LARGO = "—"                          # "—" de §4.4

# Recubrimiento por lado (m)
REC_ZAPATA_MURO_CONTENCION_M = 0.075  # NORMA: CLAUDE.md §4.5
REC_COLUMNA_VIGA_RIOSTRA_MURO_HA_M = 0.040  # NORMA: CLAUDE.md §4.5
REC_LOSA_ESCALERA_M = 0.025  # NORMA: CLAUDE.md §4.5

# Tabla de áreas de barras en cm² (nominales)
AREA_BARRA_CONFIRMADA_CM2 = {  # NORMA: respuesta de Steven P4 (tabla 3/8" 0.71 … 1-3/8" 10.06)
    '3/8"': 0.71, '#3': 0.71,
    '1/2"': 1.29, '#4': 1.29,
    '5/8"': 1.99, '#5': 1.99,
    '3/4"': 2.84, '#6': 2.84,
    '7/8"': 3.87, '#7': 3.87,
    '1"': 5.10, '#8': 5.10,
    '1-1/8"': 6.45, '#9': 6.45,
    '1-1/4"': 8.19, '#10': 8.19,
    '1-3/8"': 10.06, '#11': 10.06,
}
DECIMALES_CUANTIA_DECIMAL = 4  # NORMA: CLAUDE.md §4.6 (ej. 0.0185)
DECIMALES_CUANTIA_PORCENTAJE = 2  # NORMA: respuesta de Steven P5 (ej. 1.85)

# Grosor del recuadro rojo (M3)
GROSOR_DESEADO_PX = 4.5  # NORMA: CLAUDE.md §4.7 M3 (grosor_fuente = 4.5 px / factor)
GROSOR_MINIMO_PX = 4  # NORMA: respuesta de Steven P8 (se mantiene el mínimo de 4 px)
GROSOR_TIPICO_200DPI_PX = 22  # NORMA: CLAUDE.md §4.7 M3 ("típicamente width=22 en plantas de 200 dpi")

# Selección de fotos (M1)
MAX_FOTOS_ESCALERA_HVLEV = 9  # NORMA: CLAUDE.md §4.7 M1
MAX_FOTOS_STP_MIVED = 4  # NORMA: CLAUDE.md §4.7 M1 (pick4)

# Sección y barras para cuantía
B_SECCION_M = 0.30  # SINTÉTICO: no es dato de proyecto
H_SECCION_M = 0.40  # SINTÉTICO: no es dato de proyecto
BARRAS_SECCION = [(4, '#6'), (4, '5/8"')]  # SINTÉTICO: no es dato de proyecto
DIAMETRO_INEXISTENTE = '#12'  # SINTÉTICO: no está en la tabla P4

# Medida en obra (sobre el acero) vs. plano
VALOR_PLANO_COLUMNA_M = 0.40  # SINTÉTICO: no es dato de proyecto
MEDIDA_ACERO_COLUMNA_CONFORME_M = 0.32  # SINTÉTICO: 0.32 + 2*0.040 = 0.40
MEDIDA_ACERO_COLUMNA_CASI_M = 0.323  # SINTÉTICO: 0.323 + 0.08 = 0.403 (dif 0.003)
MEDIDA_ACERO_COLUMNA_DISCREPANTE_M = 0.30  # SINTÉTICO: 0.30 + 0.08 = 0.38
VALOR_PLANO_ZAPATA_M = 1.50  # SINTÉTICO: no es dato de proyecto
MEDIDA_ACERO_ZAPATA_M = 1.35  # SINTÉTICO: 1.35 + 2*0.075 = 1.50
VALOR_PLANO_LOSA_M = 0.20  # SINTÉTICO: no es dato de proyecto
MEDIDA_ACERO_LOSA_M = 0.15  # SINTÉTICO: 0.15 + 2*0.025 = 0.20
TOLERANCIA_VISITA_AMPLIA_M = 0.005  # SINTÉTICO: tolerancia que traería una visita (P2)
TOLERANCIA_VISITA_ESTRICTA_M = 0.001  # SINTÉTICO: tolerancia que traería una visita (P2)

# Planta y celda (px) para el grosor del recuadro rojo
PLANTA_200DPI_ANCHO_PX = 6600  # SINTÉTICO: no es dato de proyecto
PLANTA_200DPI_ALTO_PX = 4400  # SINTÉTICO: no es dato de proyecto
CELDA_200DPI_ANCHO_PX = 1350  # SINTÉTICO: factor 0.2045 en ancho y alto
CELDA_200DPI_ALTO_PX = 900  # SINTÉTICO: factor 0.2045 en ancho y alto
PLANTA_ANCHA_ANCHO_PX = 6000  # SINTÉTICO: no es dato de proyecto
PLANTA_ANCHA_ALTO_PX = 4000  # SINTÉTICO: no es dato de proyecto
CELDA_CUADRADA_PX = 1000  # SINTÉTICO: factor ancho 0.167 < factor alto 0.25
PLANTA_PEQUENA_PX = 1000  # SINTÉTICO: planta menor que la celda
CELDA_GRANDE_PX = 2000  # SINTÉTICO: factor 2 -> grosor por debajo del mínimo

# Cantidades de fotos en un log
N_FOTOS_MUCHAS = 12  # SINTÉTICO: no es dato de proyecto
N_FOTOS_ESCALERA = 20  # SINTÉTICO: no es dato de proyecto
N_FOTOS_STP = 10  # SINTÉTICO: no es dato de proyecto

# Nombres de salida de ejemplo (CLAUDE.md §5.2)
NOMBRE_STP_MIVED = "Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026.pdf"
NOMBRE_MIVED_FI = "MIVED - TERRA LIVING-LOSAS Y VIGAS PARCIAL SOTANO -3.PDF"

# Fechas
FECHA_EJEMPLO = "11/09/2026"  # NORMA: CLAUDE.md §5.2 (ejemplo del nombre STP-MIVED)


# =====================================================================
# AYUDANTES
# =====================================================================
def _sin_tildes(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def _fotos(n: int, prefijo: str = "foto") -> list:
    return [f"{prefijo}_{i:02d}.jpg" for i in range(1, n + 1)]


def _log(*items):
    """Construye un log con el formato de la app CATDIC (P9): archivo, etiqueta_elemento, leyenda."""
    return [
        {"archivo": a, "etiqueta_elemento": e, "leyenda": l} for (a, e, l) in items
    ]


def _todas_las_fotos(elementos) -> list:
    return [f for el in elementos for f in el["fotos"]]


def _ids(elementos) -> list:
    return [el["id_sugerido"] for el in elementos]


def _ficha(**cambios):
    """Ficha HV-LEV de columna sin errores; cada prueba cambia solo lo que revisa."""
    base = {
        "tipo_elemento": "COLUMNA RECTANGULAR",
        "observaciones_texto": "ACERO LONGITUDINAL\nESTRIBOSS",  # SINTÉTICO: rótulos sin valores
        "ejes": "EJE F-11",  # ejemplo CLAUDE.md §4.4
        "nombre_proyecto": "Terra Living",
        "fecha": FECHA_EJEMPLO,
    }
    base.update(cambios)
    return base


def _errores(ficha, formato="HV-LEV", contiene=None):
    errores = ri.auditar_datos_ficha_antes_de_renderizar(ficha, formato)
    if contiene is None:
        return errores
    return [e for e in errores if contiene.upper() in _sin_tildes(e).upper()]


# =====================================================================
# §4.5 — RECUBRIMIENTOS
# =====================================================================
@pytest.mark.parametrize("tipo", [
    "ZAPATA AISLADA", "ZAPATA COMBINADA", "ZAPATA DE MURO", "MURO DE CONTENCION",
])
def test_recubrimiento_zapatas_y_muro_contencion_0075(tipo):
    """§4.5: zapatas y muros de contención 0.075 m por lado."""
    assert ri.obtener_recubrimiento(tipo) == REC_ZAPATA_MURO_CONTENCION_M


@pytest.mark.parametrize("tipo", [
    "COLUMNA RECTANGULAR", "VIGA HORMIGON", "RIOSTRA", "MURO DE HORMIGON", "PORTICO",
])
def test_recubrimiento_columnas_vigas_riostras_muros_ha_0040(tipo):
    """§4.5: columnas, vigas, riostras y muros H.A. 0.040 m por lado (PÓRTICO aprobado en P3)."""
    assert ri.obtener_recubrimiento(tipo) == REC_COLUMNA_VIGA_RIOSTRA_MURO_HA_M


@pytest.mark.parametrize("tipo", [
    "LOSA ALIGERADA", "LOSA MACIZA", "RAMPA DE ESCALERA",
])
def test_recubrimiento_losas_y_escaleras_0025(tipo):
    """§4.5: losas y escaleras 0.025 m por lado."""
    assert ri.obtener_recubrimiento(tipo) == REC_LOSA_ESCALERA_M


def test_recubrimiento_platea_0075():
    """N15 (respuesta de Steven): la PLATEA es cimentación -> 0.075 m por lado (corrige P3)."""
    assert ri.obtener_recubrimiento("PLATEA") == REC_ZAPATA_MURO_CONTENCION_M
    assert ri.obtener_categoria_elemento("PLATEA") == "ZAPATAS Y MUROS DE CONTENCION"


# Categorías de §4.5 con su recubrimiento por lado (N3)
CATEGORIAS_CLAUDE_MD = {
    "ZAPATAS Y MUROS DE CONTENCION": REC_ZAPATA_MURO_CONTENCION_M,
    "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A.": REC_COLUMNA_VIGA_RIOSTRA_MURO_HA_M,
    "LOSAS Y ESCALERAS": REC_LOSA_ESCALERA_M,
}


def test_recubrimiento_tabla_categorias():
    """N3: la tabla categoría -> recubrimiento es exactamente la de §4.5 y todo tipo apunta a una categoría."""
    assert ri.RECUBRIMIENTO_POR_CATEGORIA_M == CATEGORIAS_CLAUDE_MD
    assert set(ri.CATEGORIA_POR_TIPO.values()) <= set(CATEGORIAS_CLAUDE_MD)
    for tipo, categoria in ri.CATEGORIA_POR_TIPO.items():
        assert ri.obtener_recubrimiento(tipo) == CATEGORIAS_CLAUDE_MD[categoria]


@pytest.mark.parametrize("tipo, categoria", [
    ("ZAPATA", "ZAPATAS Y MUROS DE CONTENCION"),
    ("COLUMNA", "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A."),
    ("VIGA", "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A."),
    ("MURO H.A.", "COLUMNAS, VIGAS, RIOSTRAS Y MUROS H.A."),
    ("LOSA", "LOSAS Y ESCALERAS"),
])
def test_recubrimiento_nombres_genericos(tipo, categoria):
    """N3 (respuesta de Steven): se aceptan ZAPATA, COLUMNA, VIGA, LOSA, MURO H.A.;
    el recubrimiento sale de su categoría de §4.5."""
    assert ri.obtener_categoria_elemento(tipo) == categoria
    assert ri.obtener_recubrimiento(tipo) == CATEGORIAS_CLAUDE_MD[categoria]
    assert ri.obtener_recubrimiento(tipo.lower()) == CATEGORIAS_CLAUDE_MD[categoria]


def test_recubrimiento_ignora_mayusculas_y_espacios():
    """§4.5: el tipo se normaliza (mayúsculas y espacios de borde)."""
    assert ri.obtener_recubrimiento("  losa maciza ") == REC_LOSA_ESCALERA_M


def test_recubrimiento_alias_escalera():
    """D3 / P3: 'ESCALERA' es categoría 'escaleras' de §4.5 -> 0.025."""
    assert ri.obtener_recubrimiento("ESCALERA") == REC_LOSA_ESCALERA_M


@pytest.mark.parametrize("tipo", ["COLUMNA CIRCULAR", "VIGA DE AMARRE"])
def test_recubrimiento_alias_columna_circular_viga_amarre(tipo):
    """D3 / P3: 'COLUMNA CIRCULAR' (columnas) y 'VIGA DE AMARRE' (vigas) -> 0.040."""
    assert ri.obtener_recubrimiento(tipo) == REC_COLUMNA_VIGA_RIOSTRA_MURO_HA_M


@pytest.mark.parametrize("tipo, esperado", [
    ("MURO DE CONTENCIÓN", REC_ZAPATA_MURO_CONTENCION_M),
    ("PÓRTICO", REC_COLUMNA_VIGA_RIOSTRA_MURO_HA_M),
])
def test_recubrimiento_normaliza_tildes(tipo, esperado):
    """D3 / P3: tildes normalizadas: 'MURO DE CONTENCIÓN' = 'MURO DE CONTENCION', 'PÓRTICO' = 'PORTICO'."""
    assert ri.obtener_recubrimiento(tipo) == esperado


def test_recubrimiento_tipo_desconocido_pendiente():
    """Regla de Oro #1: tipo sin regla -> ValueError 'pendiente de verificar'."""
    with pytest.raises(ValueError, match=PENDIENTE_RE):
        ri.obtener_recubrimiento("TIPO INEXISTENTE")


@pytest.mark.parametrize("tipo", [
    "PERFIL METALICO", "PERFIL METÁLICO", "CONEXION METALICA", "CONEXIÓN METÁLICA", "METALDECK",
])
def test_recubrimiento_metalicos_pendiente(tipo):
    """P3: perfiles, conexiones metálicas y metaldeck NO reciben recubrimiento -> 'pendiente de verificar'."""
    with pytest.raises(ValueError, match=PENDIENTE_RE):
        ri.obtener_recubrimiento(tipo)


# =====================================================================
# §4.5 — MEDIDA EN OBRA (sobre el acero) vs. PLANO
# =====================================================================
def test_medida_obra_sin_medida_conforme_valor_plano():
    """D1 (norma CATDIC, respuesta de Steven): sin medida en obra, OBRA = valor del plano y conforme."""
    r = ri.evaluar_medida_acero_obra("COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, None)
    assert r["valor_columna_obra_m"] == VALOR_PLANO_COLUMNA_M
    assert r["conforme"] is True


@pytest.mark.parametrize("tipo, plano, medida", [
    ("COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M),
    ("ZAPATA AISLADA", VALOR_PLANO_ZAPATA_M, MEDIDA_ACERO_ZAPATA_M),
    ("LOSA MACIZA", VALOR_PLANO_LOSA_M, MEDIDA_ACERO_LOSA_M),
])
def test_medida_obra_conforme_suma_2_recubrimientos(tipo, plano, medida):
    """§4.5 / error #12: medida + 2·rec == plano -> conforme y OBRA = valor del plano."""
    r = ri.evaluar_medida_acero_obra(tipo, plano, medida)
    assert r["conforme"] is True
    assert r["valor_columna_obra_m"] == plano
    assert r["recubrimiento_min_m"] == ri.obtener_recubrimiento(tipo)
    assert r["hallazgo_interno"] is None


def test_medida_obra_igualdad_exacta_sin_tolerancia():
    """D2 / P2: si la visita no trae tolerancia se compara con igualdad exacta (§4.5).
    0.323 + 0.08 = 0.403 ≠ 0.40 -> NO conforme (no hay tolerancia fija por defecto)."""
    r = ri.evaluar_medida_acero_obra(
        "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CASI_M
    )
    assert r["conforme"] is False
    assert r["valor_columna_obra_m"] != VALOR_PLANO_COLUMNA_M


def test_medida_obra_tolerancia_none_igualdad_exacta():
    """D2 / P2: tolerancia_m=None (la visita no la trae) -> igualdad exacta, sin excepción."""
    r = ri.evaluar_medida_acero_obra(
        "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CASI_M,
        tolerancia_m=None,
    )
    assert r["conforme"] is False
    r_ok = ri.evaluar_medida_acero_obra(
        "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M,
        tolerancia_m=None,
    )
    assert r_ok["conforme"] is True


def test_medida_obra_tolerancia_de_visita():
    """P2: la tolerancia llega como dato de la visita y se respeta."""
    amplia = ri.evaluar_medida_acero_obra(
        "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CASI_M,
        tolerancia_m=TOLERANCIA_VISITA_AMPLIA_M,
    )
    estricta = ri.evaluar_medida_acero_obra(
        "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CASI_M,
        tolerancia_m=TOLERANCIA_VISITA_ESTRICTA_M,
    )
    assert amplia["conforme"] is True
    assert amplia["valor_columna_obra_m"] == VALOR_PLANO_COLUMNA_M
    assert estricta["conforme"] is False


def test_medida_obra_discrepancia_no_conforme():
    """§4.5: si no cuadra, OBRA = medida corregida por recubrimiento, no conforme y con hallazgo."""
    r = ri.evaluar_medida_acero_obra(
        "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_DISCREPANTE_M
    )
    corregida = round(MEDIDA_ACERO_COLUMNA_DISCREPANTE_M + 2 * REC_COLUMNA_VIGA_RIOSTRA_MURO_HA_M, 4)
    assert r["conforme"] is False
    assert r["valor_columna_obra_m"] == corregida
    assert r["hallazgo_interno"]


@pytest.mark.parametrize("medida", [None, MEDIDA_ACERO_COLUMNA_CONFORME_M])
def test_medida_obra_sin_valor_plano_pendiente(medida):
    """NUEVA N1 / Regla de Oro #1: sin valor del plano no hay comparación ->
    ValueError 'pendiente de verificar' (D1 es medida ausente, no plano ausente)."""
    with pytest.raises(ValueError, match=PENDIENTE_RE):
        ri.evaluar_medida_acero_obra("COLUMNA RECTANGULAR", None, medida)


TOLERANCIA_NEGATIVA_M = -0.005  # SINTÉTICO: tolerancia inválida (T9 / O8)


@pytest.mark.parametrize("medida", [MEDIDA_ACERO_COLUMNA_CONFORME_M, MEDIDA_ACERO_COLUMNA_CASI_M])
def test_medida_obra_t9_tolerancia_negativa_pendiente(medida):
    """T9 / O8 (auditoría Gemini): tolerancia_m < 0 -> ValueError 'pendiente de verificar'
    (no se ignora ni se toma su valor absoluto)."""
    with pytest.raises(ValueError, match=PENDIENTE):
        ri.evaluar_medida_acero_obra(
            "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, medida, tolerancia_m=TOLERANCIA_NEGATIVA_M,
        )


@pytest.mark.parametrize("tolerancia", ["0.005", True])  # SINTÉTICO: tipos inválidos
def test_medida_obra_t9_tolerancia_no_numerica_pendiente(tolerancia):
    """T9 / O8 (auditoría Gemini): tolerancia que no es número -> ValueError 'pendiente de verificar',
    nunca TypeError."""
    with pytest.raises(ValueError, match=PENDIENTE):
        ri.evaluar_medida_acero_obra(
            "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M, tolerancia_m=tolerancia,
        )


def test_medida_obra_t9_tolerancia_cero_es_igualdad():
    """T9 / O8: tolerancia 0 es válida (>= 0) y equivale a igualdad exacta."""
    ok = ri.evaluar_medida_acero_obra(
        "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M, tolerancia_m=0,
    )
    casi = ri.evaluar_medida_acero_obra(
        "COLUMNA RECTANGULAR", VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CASI_M, tolerancia_m=0,
    )
    assert ok["conforme"] is True and casi["conforme"] is False


def test_recubrimiento_t9_mensaje_en_minuscula():
    """T9 / O10 (auditoría Gemini): el mensaje del recubrimiento usa la constante PENDIENTE
    ('pendiente de verificar', en minúscula) como el resto del motor."""
    with pytest.raises(ValueError) as exc:
        ri.obtener_recubrimiento("TIPO INEXISTENTE")
    assert PENDIENTE in str(exc.value)
    assert "Pendiente de verificar" not in str(exc.value)


# =====================================================================
# §4.4 — CAMPO EJES
# =====================================================================
def test_ejes_cruce_puntual_columna():
    """§4.4: columna / zapata puntual -> 'EJE F-11'."""
    assert ri.formatear_campo_ejes("cruce_puntual", eje_letra_1="F", eje_num_1="11") == "EJE F-11"


def test_ejes_cruce_puntual_letra_minuscula():
    """§4.4: la letra del eje se escribe en mayúscula."""
    assert ri.formatear_campo_ejes("cruce_puntual", eje_letra_1=" f ", eje_num_1=" 11 ") == "EJE F-11"


def test_ejes_muro_entre_letras_con_coma():
    """§4.4: muro entre dos ejes-letra sobre una fila -> 'EJE D-E,4'."""
    r = ri.formatear_campo_ejes("muro_entre_letras", eje_letra_1="D", eje_letra_2="E", eje_num_1="4")
    assert r == "EJE D-E,4"


def test_ejes_muro_sin_fila_ni_parentesis():
    """§4.4: en muros nunca aparecen 'FILA' ni paréntesis."""
    r = ri.formatear_campo_ejes("muro_entre_letras", eje_letra_1="D", eje_letra_2="E", eje_num_1="4")
    assert "FILA" not in r.upper()
    assert "(" not in r and ")" not in r


def test_ejes_viga_recta_sobre_letra():
    """§4.4: viga recta -> 'EJE C, ENTRE 2-3'."""
    r = ri.formatear_campo_ejes("viga_recta_sobre_letra", eje_letra_1="C", eje_num_1="2", eje_num_2="3")
    assert r == "EJE C, ENTRE 2-3"


def test_ejes_tramo_portico():
    """§4.4: tramo de pórtico -> 'EJE F ENTRE 10-11' (sin coma)."""
    r = ri.formatear_campo_ejes("tramo_portico", eje_letra_1="F", eje_num_1="10", eje_num_2="11")
    assert r == "EJE F ENTRE 10-11"


def test_ejes_losa_guion_largo():
    """§4.4 / error #11: losas SIEMPRE '—', aunque se pasen ejes."""
    assert ri.formatear_campo_ejes("losa") == GUION_LARGO
    assert ri.formatear_campo_ejes("losa", eje_letra_1="C", eje_num_1="2", eje_num_2="3") == GUION_LARGO


def test_ejes_viga_sin_eje_letra_guion_largo():
    """§4.4: vigas sin eje-letra -> '—'."""
    assert ri.formatear_campo_ejes("viga_sin_eje_letra") == GUION_LARGO


@pytest.mark.parametrize("caso, kwargs", [
    ("cruce_puntual", {"eje_letra_1": "F"}),
    ("cruce_puntual", {"eje_num_1": "11"}),
    ("muro_entre_letras", {"eje_letra_1": "D", "eje_num_1": "4"}),
    ("viga_recta_sobre_letra", {"eje_letra_1": "C", "eje_num_1": "2"}),
    ("tramo_portico", {"eje_num_1": "10", "eje_num_2": "11"}),
])
def test_ejes_faltan_datos_pendiente(caso, kwargs):
    """Regla de Oro #1: faltan ejes -> 'pendiente de verificar' (nunca deducir)."""
    assert ri.formatear_campo_ejes(caso, **kwargs) == PENDIENTE


def test_ejes_caso_desconocido_pendiente():
    """Regla de Oro #1: caso no previsto en §4.4 -> 'pendiente de verificar'."""
    assert ri.formatear_campo_ejes("caso_que_no_existe", eje_letra_1="F", eje_num_1="11") == PENDIENTE


@pytest.mark.parametrize("caso, kwargs", [
    ("cruce_puntual", {"eje_letra_1": "11", "eje_num_1": "F"}),
    ("muro_entre_letras", {"eje_letra_1": "4", "eje_letra_2": "E", "eje_num_1": "D"}),
    ("viga_recta_sobre_letra", {"eje_letra_1": "2", "eje_num_1": "C", "eje_num_2": "3"}),
    ("tramo_portico", {"eje_letra_1": "10", "eje_num_1": "F", "eje_num_2": "11"}),
])
def test_ejes_argumentos_invertidos_pendiente(caso, kwargs):
    """D4: en cruce y muro la letra debe ser letra y el número número (nunca 'EJE 11-F').
    T7 (auditoría Gemini): en viga y pórtico el principal puede ser número, pero los extremos
    deben ser de la otra familia o 'MC'; aquí uno es de la misma familia -> 'pendiente de verificar'."""
    assert ri.formatear_campo_ejes(caso, **kwargs) == PENDIENTE


# --- T7 (auditoría Gemini, CLAUDE.md §4.3): pórticos sobre ejes numéricos y extremos MC ---
@pytest.mark.parametrize("principal, ext_1, ext_2, esperado", [
    ("1", "MC", "A", "EJE 1 ENTRE MC-A"),    # NORMA: CLAUDE.md §4.3 ('P1 EJE 1 ENTRE MC-A')
    ("1", "B", "D", "EJE 1 ENTRE B-D"),      # NORMA: ejemplo de Gemini (auditoría Etapa 0)
    ("B", "MC", "1", "EJE B ENTRE MC-1"),    # NORMA: ejemplo de Gemini (auditoría Etapa 0)
    ("F", "10", "11", "EJE F ENTRE 10-11"),  # NORMA: CLAUDE.md §4.4 (formato sin cambios)
    ("B", "1", "MC", "EJE B ENTRE 1-MC"),    # SINTÉTICO: MC en el segundo extremo
    (" 1' ", "a'", "mc", "EJE 1' ENTRE A'-MC"),  # SINTÉTICO: prima, minúsculas y espacios
])
def test_ejes_t7_tramo_portico_principal_letra_o_numero(principal, ext_1, ext_2, esperado):
    """T7 (auditoría Gemini): en 'tramo_portico' eje_letra_1 es el eje principal (letra o número)
    y eje_num_1/2 los extremos (número, letra o 'MC', de la otra familia que el principal)."""
    r = ri.formatear_campo_ejes("tramo_portico", eje_letra_1=principal, eje_num_1=ext_1, eje_num_2=ext_2)
    assert r == esperado


@pytest.mark.parametrize("principal, ext_1, ext_2, esperado", [
    ("C", "2", "3", "EJE C, ENTRE 2-3"),     # NORMA: CLAUDE.md §4.4 (formato sin cambios)
    ("1", "MC", "A", "EJE 1, ENTRE MC-A"),   # SINTÉTICO: mismo criterio que el pórtico
    ("1", "B", "D", "EJE 1, ENTRE B-D"),     # SINTÉTICO: mismo criterio que el pórtico
    ("B", "MC", "1", "EJE B, ENTRE MC-1"),   # SINTÉTICO: mismo criterio que el pórtico
])
def test_ejes_t7_viga_recta_principal_letra_o_numero(principal, ext_1, ext_2, esperado):
    """T7 (auditoría Gemini): 'viga_recta_sobre_letra' sigue el criterio del pórtico con su
    formato 'EJE X, ENTRE a-b'."""
    r = ri.formatear_campo_ejes("viga_recta_sobre_letra", eje_letra_1=principal, eje_num_1=ext_1, eje_num_2=ext_2)
    assert r == esperado


@pytest.mark.parametrize("caso", ["tramo_portico", "viga_recta_sobre_letra"])
@pytest.mark.parametrize("principal, ext_1, ext_2", [
    ("1", "MC", "MC"),    # MC-MC
    ("B", "MC", "MC"),    # MC-MC
    ("1", "", "A"),       # extremo vacío
    ("1", "A", None),     # extremo ausente
    ("B", "  ", "1"),     # extremo en blanco
    ("1", "2", "A"),      # extremo de la misma familia que el principal (número)
    ("1", "2", "3"),      # ambos extremos de la misma familia
    ("B", "C", "1"),      # extremo de la misma familia que el principal (letra)
    ("B", "C", "D"),      # ambos extremos de la misma familia
    ("MC", "1", "2"),     # MC no es eje principal
    ("", "1", "2"),       # principal vacío
    ("1", "MC'", "A"),    # MC con prima no existe
    ("1", "A-B", "C"),    # token raro
    ("B", "1A", "2"),     # token raro
    ("B", "1''", "2"),    # prima doble
    ("A''", "1", "2"),    # principal con prima doble
    ("1", "A", "#"),      # token raro
])
def test_ejes_t7_extremos_incoherentes_pendiente(caso, principal, ext_1, ext_2):
    """T7 (auditoría Gemini) / Regla de Oro #1: extremos vacíos, 'MC-MC', de la misma familia que el
    eje principal o tokens inválidos -> 'pendiente de verificar' (se mantiene el rechazo útil)."""
    r = ri.formatear_campo_ejes(caso, eje_letra_1=principal, eje_num_1=ext_1, eje_num_2=ext_2)
    assert r == PENDIENTE


def test_ejes_t7_docstring_principal_y_extremos():
    """T7: el docstring documenta que eje_letra_1 es el principal y eje_num_1/2 los extremos (MC)."""
    doc = ri.formatear_campo_ejes.__doc__ or ""
    assert "T7" in doc and "PRINCIPAL" in doc and "EXTREMOS" in doc and "'MC'" in doc


def test_ejes_elemento_unico_en_planta_documentado():
    """P6: el caso 'elemento_unico_en_planta' se conserva; se prueba su comportamiento actual:
    devuelve la referencia en mayúsculas, o '—' si no hay referencia."""
    assert ri.formatear_campo_ejes("elemento_unico_en_planta", referencia_unica=" x1 ") == "X1"
    assert ri.formatear_campo_ejes("elemento_unico_en_planta") == GUION_LARGO


# --- T4b: ejes con prima, ejes leídos de la visita y área de platea ---
def test_ejes_cruce_puntual_letra_con_prima():
    """T4b (respuesta de Steven): existen ejes con prima, p. ej. A' -> 'EJE A'-1'."""
    assert ri.formatear_campo_ejes("cruce_puntual", "A'", eje_num_1="1") == "EJE A'-1"


def test_ejes_numero_con_prima():
    """T4b (respuesta de Steven): la prima también vale en el eje-número (2')."""
    assert ri.formatear_campo_ejes("cruce_puntual", "F", eje_num_1="2'") == "EJE F-2'"
    r = ri.formatear_campo_ejes("viga_recta_sobre_letra", eje_letra_1="C'", eje_num_1="2", eje_num_2="3'")
    assert r == "EJE C', ENTRE 2-3'"
    r = ri.formatear_campo_ejes("muro_entre_letras", eje_letra_1="D", eje_letra_2="E'", eje_num_1="4")
    assert r == "EJE D-E',4"
    r = ri.formatear_campo_ejes("tramo_portico", eje_letra_1="f'", eje_num_1="10", eje_num_2="11")
    assert r == "EJE F' ENTRE 10-11"


@pytest.mark.parametrize("letra, num", [("A''", "1"), ("'A", "1"), ("A", "1''"), ("A", "'1"), ("A'", "B")])
def test_ejes_prima_mal_formada_pendiente(letra, num):
    """T4b / Regla de Oro #1: solo una prima al final; otra cosa -> 'pendiente de verificar'."""
    assert ri.formatear_campo_ejes("cruce_puntual", letra, eje_num_1=num) == PENDIENTE


def test_ejes_prima_sigue_rechazando_invertidos():
    """T4b + D4: con prima, letra y número invertidos siguen siendo 'pendiente de verificar'."""
    assert ri.formatear_campo_ejes("cruce_puntual", "1'", eje_num_1="A'") == PENDIENTE


@pytest.mark.parametrize("texto, esperado", [
    ("A1", ("A", "1")),
    ("1A", ("A", "1")),
    ("a1", ("A", "1")),
    ("1a", ("A", "1")),
    (" F11 ", ("F", "11")),
    ("11F", ("F", "11")),
    ("A'1", ("A'", "1")),
    ("1A'", ("A'", "1")),
    ("A2'", ("A", "2'")),
    ("2'A", ("A", "2'")),
])
def test_interpretar_eje_de_visita_ambos_ordenes(texto, esperado):
    """T4b (respuesta de Steven): 'si el elemento en la visita dice solamente A1 o 1A, está en
    los ejes A, 1 o 1, A; estos órdenes comúnmente se cruzan'. Se aceptan ambos órdenes y prima."""
    assert ri.interpretar_eje_de_visita(texto) == esperado


@pytest.mark.parametrize("texto", [
    None, "", "   ", "A", "1", "A-1", "A 1", "1A1", "A1B", "A''1", "'A1", "EJE A-1", "A1,2", "Ñ",
])
def test_interpretar_eje_de_visita_ambiguo_pendiente(texto):
    """T4b / Regla de Oro #1: lo que no sea exactamente letra(s)+prima y número+prima -> 'pendiente
    de verificar' (no se adivina)."""
    assert ri.interpretar_eje_de_visita(texto) == PENDIENTE


def test_interpretar_eje_de_visita_alimenta_cruce_puntual():
    """T4b: el par leído de la visita produce el EJES de §4.4 ('1A' -> 'EJE A-1')."""
    letra, num = ri.interpretar_eje_de_visita("1A'")
    assert ri.formatear_campo_ejes("cruce_puntual", letra, eje_num_1=num) == "EJE A'-1"


def test_interpretar_eje_de_visita_docstring_con_regla_de_steven():
    """T4b: el docstring recoge la regla de Steven (ambos órdenes)."""
    doc = ri.interpretar_eje_de_visita.__doc__ or ""
    assert "A1" in doc and "1A" in doc and "Steven" in doc


def test_ejes_area_platea():
    """T4b (respuesta de Steven): EJES de la platea como área, ejemplo '(A-B),(1-2)'."""
    r = ri.formatear_campo_ejes("area", eje_letra_1="A", eje_letra_2="B", eje_num_1="1", eje_num_2="2")
    assert r == "(A-B),(1-2)"


def test_ejes_area_con_prima_y_minusculas():
    """T4b (respuesta de Steven): el área admite prima y escribe las letras en mayúscula."""
    r = ri.formatear_campo_ejes("area", eje_letra_1=" a' ", eje_letra_2="b", eje_num_1="1", eje_num_2="2'")
    assert r == "(A'-B),(1-2')"


@pytest.mark.parametrize("kwargs", [
    {},
    {"eje_letra_1": "A", "eje_letra_2": "B", "eje_num_1": "1"},
    {"eje_letra_1": "A", "eje_num_1": "1", "eje_num_2": "2"},
    {"eje_letra_1": "1", "eje_letra_2": "2", "eje_num_1": "A", "eje_num_2": "B"},
])
def test_ejes_area_faltan_datos_pendiente(kwargs):
    """T4b / Regla de Oro #1: área sin los 4 ejes válidos -> 'pendiente de verificar'."""
    assert ri.formatear_campo_ejes("area", **kwargs) == PENDIENTE


def test_ejes_area_en_docstring():
    """T4b: el caso 'area' queda documentado en el docstring."""
    assert "'area'" in (ri.formatear_campo_ejes.__doc__ or "")


def test_ejes_elemento_unico_en_planta_en_docstring():
    """D4 / P6: el caso 'elemento_unico_en_planta' queda documentado en el docstring."""
    assert "elemento_unico_en_planta" in (ri.formatear_campo_ejes.__doc__ or "")


# =====================================================================
# §4.6 — CUANTÍA
# =====================================================================
def _as_total_cm2(barras):
    return sum(cant * AREA_BARRA_CONFIRMADA_CM2[d] for cant, d in barras)


def test_cuantia_formula_as_total_sobre_bh():
    """§4.6 / error #12: cuantía = As_total / (b·h), decimal con 4 cifras (STP-MIVED)."""
    esperado = round(
        _as_total_cm2(BARRAS_SECCION) / ((B_SECCION_M * 100) * (H_SECCION_M * 100)),
        DECIMALES_CUANTIA_DECIMAL,
    )
    assert ri.calcular_cuantia_elemento(B_SECCION_M, H_SECCION_M, BARRAS_SECCION) == esperado


def test_cuantia_decimal_vs_porcentaje():
    """§4.6 / P5: STP-MIVED en decimal (4 cifras), CATDIC-STP en % (2 decimales)."""
    rho = _as_total_cm2(BARRAS_SECCION) / ((B_SECCION_M * 100) * (H_SECCION_M * 100))
    dec = ri.calcular_cuantia_elemento(B_SECCION_M, H_SECCION_M, BARRAS_SECCION)
    pct = ri.calcular_cuantia_elemento(B_SECCION_M, H_SECCION_M, BARRAS_SECCION, en_porcentaje=True)
    assert dec == round(rho, DECIMALES_CUANTIA_DECIMAL)
    assert pct == round(rho * 100, DECIMALES_CUANTIA_PORCENTAJE)
    assert pct == pytest.approx(dec * 100, abs=10 ** -DECIMALES_CUANTIA_PORCENTAJE)


def test_cuantia_simbolo_diametro_ignorado():
    """§4.6: el símbolo 'Ø' delante del diámetro no cambia el cálculo."""
    con_simbolo = [(c, "Ø" + d) for c, d in BARRAS_SECCION]
    assert ri.calcular_cuantia_elemento(B_SECCION_M, H_SECCION_M, con_simbolo) == \
        ri.calcular_cuantia_elemento(B_SECCION_M, H_SECCION_M, BARRAS_SECCION)


def test_cuantia_tabla_areas_confirmada():
    """P4: la tabla de áreas del motor es la confirmada por Steven (D5 cerrado)."""
    assert ri.AREA_BARRA_CM2 == AREA_BARRA_CONFIRMADA_CM2


def test_cuantia_diametro_desconocido_error():
    """§4.6 / Regla de Oro #1: diámetro fuera de la tabla -> ValueError 'pendiente de verificar'."""
    with pytest.raises(ValueError, match=PENDIENTE_RE):
        ri.calcular_cuantia_elemento(B_SECCION_M, H_SECCION_M, [(4, DIAMETRO_INEXISTENTE)])  # SINTÉTICO: no es dato de proyecto


@pytest.mark.parametrize("b, h", [
    (0, H_SECCION_M), (B_SECCION_M, 0), (-B_SECCION_M, H_SECCION_M), (B_SECCION_M, -H_SECCION_M),
])
def test_cuantia_dimensiones_no_positivas_error(b, h):
    """§4.6 / T9 / O9 (auditoría Gemini): dimensiones ≤ 0 -> ValueError con 'pendiente de verificar'."""
    with pytest.raises(ValueError, match=PENDIENTE):
        ri.calcular_cuantia_elemento(b, h, BARRAS_SECCION)


def test_cuantia_sin_barras_error():
    """NUEVA N2 / Regla de Oro #1: sin barras no se inventa cuantía 0.0 ->
    ValueError 'pendiente de verificar'."""
    with pytest.raises(ValueError, match=PENDIENTE_RE):
        ri.calcular_cuantia_elemento(B_SECCION_M, H_SECCION_M, [])


@pytest.mark.parametrize("cantidad", [0, -4])  # SINTÉTICO: cantidades inválidas
def test_cuantia_cantidad_no_positiva_error(cantidad):
    """NUEVA N2 / Regla de Oro #1: cantidad de barras ≤ 0 -> ValueError 'pendiente de verificar'."""
    with pytest.raises(ValueError, match=PENDIENTE_RE):
        ri.calcular_cuantia_elemento(B_SECCION_M, H_SECCION_M, [(cantidad, '#5')])  # SINTÉTICO: no es dato de proyecto


# =====================================================================
# §4.7 M1 — LOG FOTOGRÁFICO (convención confirmada en P9)
# =====================================================================
def test_log_etiqueta_abre_elemento():
    """§4.7 M1 / P9: la foto con etiqueta abre el elemento; las siguientes sin etiqueta le pertenecen."""
    log = _log(
        ("f01.jpg", "C1 A4", ""),
        ("f02.jpg", "", "lectura en cara 1"),
        ("f03.jpg", "", ""),
        ("f04.jpg", "M2 D-E", ""),
        ("f05.jpg", "", ""),
    )
    el = ri.agrupar_log_fotografico_visita(log)
    assert _ids(el) == ["C1", "M2"]
    assert el[0]["fotos"] == ["f01.jpg", "f02.jpg", "f03.jpg"]
    assert el[0]["leyendas_medicion"] == ["lectura en cara 1"]
    assert el[1]["fotos"] == ["f04.jpg", "f05.jpg"]
    assert [e["orden_en_log"] for e in el] == [1, 2]


def test_log_fotos_antes_de_primera_etiqueta_reportadas():
    """D6a: las fotos antes de la primera etiqueta no se pierden; quedan en un grupo marcado
    'pendiente de verificar' (para la bandeja 'Con dudas')."""
    log = _log(
        ("f00.jpg", "", ""),
        ("f01.jpg", "C1 A4", ""),
        ("f02.jpg", "", ""),
    )
    el = ri.agrupar_log_fotografico_visita(log)
    assert sorted(_todas_las_fotos(el)) == ["f00.jpg", "f01.jpg", "f02.jpg"]
    grupo = next(e for e in el if "f00.jpg" in e["fotos"])
    textos = " ".join(str(v) for v in grupo.values() if isinstance(v, str))
    assert PENDIENTE in textos.lower()
    assert "f01.jpg" not in grupo["fotos"]


def test_log_tramo_portico_id_formato():
    """§4.3 / P9: 'P eje X' + 'Tramo n-n' -> elemento singular con id 'A (2-3)'; cada tramo es otro elemento."""
    log = _log(
        ("f01.jpg", "P eje A", ""),
        ("f02.jpg", "", "Tramo 2 - 3"),
        ("f03.jpg", "", ""),
        ("f04.jpg", "Tramo 3-4", ""),
    )
    el = ri.agrupar_log_fotografico_visita(log)
    tramos = [e for e in el if e["es_portico_tramo"]]
    assert [e["id_sugerido"] for e in tramos] == ["A (2-3)", "A (3-4)"]
    assert tramos[0]["fotos"] == ["f02.jpg", "f03.jpg"]
    assert tramos[1]["fotos"] == ["f04.jpg"]


def test_log_portico_se_reinicia_con_otro_elemento():
    """D6b: tras abrir otro elemento, una leyenda con 'Tramo' ya no abre un tramo del pórtico anterior."""
    log = _log(
        ("f01.jpg", "P eje A", ""),
        ("f02.jpg", "", "Tramo 2-3"),
        ("f03.jpg", "C1 B4", ""),
        ("f04.jpg", "", "Tramo 5-6 vista lateral"),
    )
    el = ri.agrupar_log_fotografico_visita(log)
    assert "A (5-6)" not in _ids(el)
    assert el[-1]["id_sugerido"] == "C1"
    assert el[-1]["fotos"] == ["f03.jpg", "f04.jpg"]


def test_log_p_eje_sin_tramo_no_crea_id_p():
    """D6c: la etiqueta 'P eje A' sin tramo no crea un elemento con id 'P'; ninguna foto se pierde."""
    log = _log(
        ("f01.jpg", "P eje A", ""),
        ("f02.jpg", "", "Tramo 2-3"),
    )
    el = ri.agrupar_log_fotografico_visita(log)
    assert "P" not in _ids(el)
    assert sorted(_todas_las_fotos(el)) == ["f01.jpg", "f02.jpg"]


def test_log_p_eje_con_tramo_en_leyenda():
    """NUEVA N5: 'P eje A' en la etiqueta y 'Tramo 2-3' en la leyenda de la MISMA foto -> 'A (2-3)'
    (el tramo se busca en la etiqueta y en la leyenda)."""
    log = _log(
        ("f01.jpg", "P eje A", "Tramo 2-3"),
        ("f02.jpg", "", ""),
    )
    el = ri.agrupar_log_fotografico_visita(log)
    assert _ids(el) == ["A (2-3)"]
    assert el[0]["fotos"] == ["f01.jpg", "f02.jpg"]


def test_log_tramo_repetido_abre_elementos_separados():
    """N6 (respuesta de Steven: NO es error): un mismo tramo puede abrir varios elementos
    (elementos grandes o complejos). Protege el comportamiento actual."""
    log = _log(
        ("f01.jpg", "P eje A", ""),
        ("f02.jpg", "", "Tramo 2-3"),
        ("f03.jpg", "", "Tramo 2-3 vista lateral"),
    )
    el = ri.agrupar_log_fotografico_visita(log)
    tramos = [e for e in el if e["id_sugerido"] == "A (2-3)"]
    assert len(tramos) == 2
    assert tramos[0]["fotos"] == ["f02.jpg"]
    assert tramos[1]["fotos"] == ["f03.jpg"]


@pytest.mark.parametrize("log", [
    _log(("f01.jpg", "Tramo 2-3", ""), ("f02.jpg", "", "")),
    _log(("f01.jpg", "C1 B4", ""), ("f02.jpg", "Tramo 2 - 3", ""), ("f03.jpg", "", "")),
    _log(("f01.jpg", "P eje A", ""), ("f02.jpg", "C1 B4", ""), ("f03.jpg", "tramo 2-3", ""), ("f04.jpg", "", "")),
])
def test_log_t8_tramo_sin_portico_abierto_pendiente(log):
    """T8 / O5 (auditoría Gemini): una etiqueta 'Tramo n-n' sin 'P eje X' abierto abre un grupo con
    id_sugerido 'pendiente de verificar' y 'duda', igual que D6c; nunca id 'TRAMO' y sin perder fotos."""
    el = ri.agrupar_log_fotografico_visita(log)
    assert "TRAMO" not in [str(i).upper() for i in _ids(el)]
    grupo = el[-1]
    assert grupo["id_sugerido"] == PENDIENTE
    assert grupo["es_portico_tramo"] is False
    assert grupo["duda"] and PENDIENTE in grupo["duda"]
    assert grupo["fotos"] == [a["archivo"] for a in log[-2:]]
    assert sorted(_todas_las_fotos(el)) == sorted(a["archivo"] for a in log)


# =====================================================================
# §4.7 M1 — SELECCIÓN DE FOTOS
# =====================================================================
def _indices(seleccion, fotos):
    return [fotos.index(f) for f in seleccion]


def test_fotos_hvlev_todas():
    """§4.7 M1: en HV-LEV entran todas las fotos (salvo escaleras)."""
    fotos = _fotos(N_FOTOS_MUCHAS)
    assert ri.seleccionar_fotos_m1(fotos, "COLUMNA RECTANGULAR") == fotos


def test_fotos_escalera_max_9_primera_ultima_orden():
    """§4.7 M1: escaleras máx. 9 fotos repartidas, conservando primera, última y orden."""
    fotos = _fotos(N_FOTOS_ESCALERA)
    sel = ri.seleccionar_fotos_m1(fotos, "RAMPA DE ESCALERA")
    idx = _indices(sel, fotos)
    assert len(sel) == MAX_FOTOS_ESCALERA_HVLEV
    assert sel[0] == fotos[0] and sel[-1] == fotos[-1]
    assert idx == sorted(set(idx))


def test_fotos_escalera_pocas_fotos_todas():
    """§4.7 M1: si la escalera tiene ≤ 9 fotos entran todas."""
    fotos = _fotos(MAX_FOTOS_ESCALERA_HVLEV)
    assert ri.seleccionar_fotos_m1(fotos, "RAMPA DE ESCALERA") == fotos


def test_fotos_escalera_alias_escalera_max_9():
    """D7 / P3: el tope de 9 aplica también al tipo 'ESCALERA'."""
    fotos = _fotos(N_FOTOS_ESCALERA)
    assert len(ri.seleccionar_fotos_m1(fotos, "ESCALERA")) == MAX_FOTOS_ESCALERA_HVLEV


def test_fotos_stp_mived_pick4_repartidas():
    """D7 / §4.7 M1: STP-MIVED hoja fotográfica -> hasta 4 fotos repartidas en la secuencia (pick4),
    con seleccionar_fotos_pick4(fotos: List[str]) -> List[str]."""
    from reglas_ingenieria import seleccionar_fotos_pick4
    fotos = _fotos(N_FOTOS_STP)
    sel = seleccionar_fotos_pick4(fotos)
    idx = _indices(sel, fotos)
    assert len(sel) == MAX_FOTOS_STP_MIVED
    assert sel[0] == fotos[0] and sel[-1] == fotos[-1]
    assert idx == sorted(set(idx))
    saltos = [b - a for a, b in zip(idx, idx[1:])]
    assert max(saltos) - min(saltos) <= 1  # repartidas de forma pareja


def test_fotos_stp_mived_una_foto():
    """D7 / §4.7 M1: STP-MIVED con 1 sola foto -> 1 grande; con ≤ 4 entran todas."""
    from reglas_ingenieria import seleccionar_fotos_pick4
    assert seleccionar_fotos_pick4(["f01.jpg"]) == ["f01.jpg"]
    tres = _fotos(3)
    assert seleccionar_fotos_pick4(tres) == tres


# =====================================================================
# §4.7 M3 — GROSOR DEL RECUADRO ROJO (P8)
# Firma (D8 / P8):
#   calcular_grosor_recuadro_rojo(ancho_fuente_px, alto_fuente_px,
#                                 ancho_celda_px, alto_celda_px, grosor_deseado_px=4.5)
# El factor de reducción usa ancho y alto (el menor de los dos).
# =====================================================================
def _grosor_esperado(af, hf, ac, hc):
    factor = min(ac / af, hc / hf)
    return max(GROSOR_MINIMO_PX, round(GROSOR_DESEADO_PX / factor))


def test_grosor_formula_4_5_sobre_factor():
    """§4.7 M3 / D8: grosor_fuente = 4.5 / factor; en una planta de 200 dpi da ≈ 22 px."""
    g = ri.calcular_grosor_recuadro_rojo(
        PLANTA_200DPI_ANCHO_PX, PLANTA_200DPI_ALTO_PX,
        CELDA_200DPI_ANCHO_PX, CELDA_200DPI_ALTO_PX,
    )
    assert g == _grosor_esperado(
        PLANTA_200DPI_ANCHO_PX, PLANTA_200DPI_ALTO_PX, CELDA_200DPI_ANCHO_PX, CELDA_200DPI_ALTO_PX
    )
    assert g == GROSOR_TIPICO_200DPI_PX


def test_grosor_factor_min_ancho_alto():
    """D8 / P8: factor = el menor entre ancho_celda/ancho_fuente y alto_celda/alto_fuente
    (la planta se encaja completa)."""
    g = ri.calcular_grosor_recuadro_rojo(
        PLANTA_ANCHA_ANCHO_PX, PLANTA_ANCHA_ALTO_PX, CELDA_CUADRADA_PX, CELDA_CUADRADA_PX,
    )
    solo_por_alto = max(GROSOR_MINIMO_PX, round(GROSOR_DESEADO_PX / (CELDA_CUADRADA_PX / PLANTA_ANCHA_ALTO_PX)))
    assert g == _grosor_esperado(
        PLANTA_ANCHA_ANCHO_PX, PLANTA_ANCHA_ALTO_PX, CELDA_CUADRADA_PX, CELDA_CUADRADA_PX
    )
    assert g != solo_por_alto


def test_grosor_minimo_4px():
    """P8: se mantiene el mínimo de 4 px."""
    g = ri.calcular_grosor_recuadro_rojo(
        PLANTA_PEQUENA_PX, PLANTA_PEQUENA_PX, CELDA_GRANDE_PX, CELDA_GRANDE_PX,
    )
    assert g == GROSOR_MINIMO_PX


@pytest.mark.parametrize("args", [
    (0, PLANTA_200DPI_ALTO_PX, CELDA_200DPI_ANCHO_PX, CELDA_200DPI_ALTO_PX),
    (PLANTA_200DPI_ANCHO_PX, 0, CELDA_200DPI_ANCHO_PX, CELDA_200DPI_ALTO_PX),
    (PLANTA_200DPI_ANCHO_PX, PLANTA_200DPI_ALTO_PX, 0, CELDA_200DPI_ALTO_PX),
    (PLANTA_200DPI_ANCHO_PX, PLANTA_200DPI_ALTO_PX, CELDA_200DPI_ANCHO_PX, -CELDA_200DPI_ALTO_PX),
])
def test_grosor_datos_invalidos_error(args):
    """D8 / P8: dimensiones ≤ 0 -> ValueError 'pendiente de verificar', nunca un número fijo."""
    with pytest.raises(ValueError, match=PENDIENTE_RE):
        ri.calcular_grosor_recuadro_rojo(*args)


def test_grosor_deseado_no_positivo_error():
    """D8 / P8 (matriz T2): grosor_deseado_px ≤ 0 -> ValueError 'pendiente de verificar'."""
    with pytest.raises(ValueError, match=PENDIENTE_RE):
        ri.calcular_grosor_recuadro_rojo(
            PLANTA_200DPI_ANCHO_PX, PLANTA_200DPI_ALTO_PX,
            CELDA_200DPI_ANCHO_PX, CELDA_200DPI_ALTO_PX, grosor_deseado_px=0,
        )


# =====================================================================
# §5.2 — VERSIONADO SIN SOBRESCRITURA
# =====================================================================
def test_versionado_libre_mismo_nombre(tmp_path):
    """§5.2: si el nombre está libre se usa tal cual."""
    r = ri.obtener_ruta_salida_sin_sobrescribir(tmp_path, NOMBRE_STP_MIVED)
    assert r == tmp_path / NOMBRE_STP_MIVED
    assert not r.exists()


def test_versionado_existe_v2(tmp_path):
    """§5.2 / error #15: si existe, sufijo ' v2.pdf'."""
    (tmp_path / NOMBRE_STP_MIVED).write_bytes(b"x")
    r = ri.obtener_ruta_salida_sin_sobrescribir(tmp_path, NOMBRE_STP_MIVED)
    assert r.name == "Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026 v2.pdf"
    assert not r.exists()


def test_versionado_existe_v2_da_v3(tmp_path):
    """§5.2: si existen el original y v2, sufijo ' v3.pdf'."""
    (tmp_path / NOMBRE_STP_MIVED).write_bytes(b"x")
    (tmp_path / "Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026 v2.pdf").write_bytes(b"x")
    r = ri.obtener_ruta_salida_sin_sobrescribir(tmp_path, NOMBRE_STP_MIVED)
    assert r.name == "Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026 v3.pdf"


def test_versionado_mived_fi_extension_mayuscula(tmp_path):
    """§5.2: nombre MIVED FI conserva '.PDF' en mayúscula al versionar."""
    assert ri.obtener_ruta_salida_sin_sobrescribir(tmp_path, NOMBRE_MIVED_FI).name == NOMBRE_MIVED_FI
    (tmp_path / NOMBRE_MIVED_FI).write_bytes(b"x")
    r = ri.obtener_ruta_salida_sin_sobrescribir(tmp_path, NOMBRE_MIVED_FI)
    assert r.name == "MIVED - TERRA LIVING-LOSAS Y VIGAS PARCIAL SOTANO -3 v2.PDF"


def test_versionado_no_sobrescribe_existente(tmp_path):
    """§5.2 / error #15: consultar la ruta no toca el archivo existente."""
    original = tmp_path / NOMBRE_STP_MIVED
    original.write_bytes(b"contenido original")
    ri.obtener_ruta_salida_sin_sobrescribir(tmp_path, NOMBRE_STP_MIVED)
    assert original.read_bytes() == b"contenido original"


def test_versionado_no_crea_carpetas(tmp_path):
    """D9 / §5.2: consultar la ruta de salida no crea carpetas (no escribir en Dropbox)."""
    carpeta = tmp_path / "no_existe" / "INFORMES"
    r = ri.obtener_ruta_salida_sin_sobrescribir(carpeta, NOMBRE_STP_MIVED)
    assert r == carpeta / NOMBRE_STP_MIVED
    assert not carpeta.exists()
    assert not (tmp_path / "no_existe").exists()


# =====================================================================
# §5.2 — FECHA DD/MM/AAAA
# =====================================================================
def test_formatear_fecha_ddmmaaaa():
    """D10 / §5.2: formatear_fecha_ddmmaaaa(date) -> 'DD/MM/AAAA' (con ceros)."""
    from reglas_ingenieria import formatear_fecha_ddmmaaaa
    assert formatear_fecha_ddmmaaaa(date(2026, 9, 11)) == FECHA_EJEMPLO
    assert formatear_fecha_ddmmaaaa(date(2026, 1, 5)) == "05/01/2026"


# =====================================================================
# §6 — AUDITOR PRELIMINAR
# =====================================================================
def test_auditor_ficha_correcta_sin_errores():
    """§6: una ficha HV-LEV de columna correcta no genera errores."""
    assert _errores(_ficha()) == []


# --- Error #8 ---
@pytest.mark.parametrize("nombre", [
    "Terra Living Visita 3", "Terra Living Sotano S4", "Terra Living Nivel 2",
    "Terra Living Parcial", "Terra Living Completivo",
])
def test_auditor_8_nombre_con_sufijo(nombre):
    """Error #8: NOMBRE PROYECTO con sufijo de visita o nivel en HV-LEV."""
    assert _errores(_ficha(nombre_proyecto=nombre), contiene="#8")


def test_auditor_8_sotano_con_tilde():
    """D11 / error #8: 'Sótano' con tilde también es sufijo de nivel."""
    assert _errores(_ficha(nombre_proyecto="Terra Living Sótano S4"), contiene="#8")


def test_auditor_8_nombre_limpio_ok():
    """Error #8: nombre sin sufijos -> sin error."""
    assert not _errores(_ficha(nombre_proyecto="Terra Living"), contiene="#8")


def test_auditor_8_solo_aplica_a_hvlev():
    """Error #8 es propio de HV-LEV."""
    ficha = _ficha(nombre_proyecto="Terra Living Visita 3")
    assert not _errores(ficha, formato="STP-MIVED", contiene="#8")


# --- Error #9 ---
def test_auditor_9_corrido():
    """Error #9: prohibida la palabra 'CORRIDO' en acero."""
    ficha = _ficha(observaciones_texto="ACERO CORRIDO\nESTRIBOSS")
    assert _errores(ficha, contiene="CORRIDO")


def test_auditor_9_recorrido_no_es_corrido():
    """NUEVA N8 / error #9: 'RECORRIDO' no es la palabra 'CORRIDO' (sin falso positivo)."""
    ficha = _ficha(observaciones_texto="RECORRIDO DE INSPECCION\nESTRIBOSS")
    assert not _errores(ficha, contiene="CORRIDO")


@pytest.mark.parametrize("tipo", ["VIGA HORMIGON", "RIOSTRA", "PORTICO"])
def test_auditor_9_viga_sin_estribos(tipo):
    """Error #9 / §4.7 M2: viga, riostra y pórtico llevan obligatoriamente ESTRIBOS."""
    ficha = _ficha(tipo_elemento=tipo, ejes="EJE C, ENTRE 2-3",
                   observaciones_texto="ACERO SUPERIOR\nACERO INFERIOR")
    assert _errores(ficha, formato="STP-MIVED", contiene="ESTRIBOS")


def test_auditor_9_viga_con_estribos_al_final_ok():
    """Error #9: viga con ESTRIBOS en la última línea -> sin error #9."""
    ficha = _ficha(tipo_elemento="VIGA HORMIGON", ejes="EJE C, ENTRE 2-3",
                   observaciones_texto="ACERO SUPERIOR\nACERO INFERIOR\nESTRIBOS")
    assert not _errores(ficha, formato="STP-MIVED", contiene="#9")


def test_auditor_9_estribos_al_final():
    """D11 / §4.7 M2: ESTRIBOS debe ir AL FINAL; si aparece antes -> error #9."""
    ficha = _ficha(tipo_elemento="VIGA HORMIGON", ejes="EJE C, ENTRE 2-3",
                   observaciones_texto="ESTRIBOS\nACERO SUPERIOR\nACERO INFERIOR")
    assert _errores(ficha, formato="STP-MIVED", contiene="#9")


def test_auditor_9_portico_con_tilde():
    """NUEVA N10: 'PÓRTICO' con tilde sin ESTRIBOS también es error #9."""
    ficha = _ficha(tipo_elemento="PÓRTICO", ejes="EJE F ENTRE 10-11",
                   observaciones_texto="ACERO SUPERIOR\nACERO INFERIOR")
    assert _errores(ficha, formato="STP-MIVED", contiene="ESTRIBOS")


def test_auditor_9_acero_adicional_mas():
    """Error #9: ACERO ADICIONAL combinado con '+' en una línea."""
    ficha = _ficha(observaciones_texto="ACERO ADICIONAL IZQUIERDO + DERECHO\nESTRIBOSS")
    assert _errores(ficha, contiene="ACERO ADICIONAL")


def test_auditor_9_acero_adicional_lineas_separadas_ok():
    """Error #9: ACERO ADICIONAL IZQUIERDO y DERECHO en líneas separadas -> sin error."""
    ficha = _ficha(observaciones_texto="ACERO ADICIONAL IZQUIERDO\nACERO ADICIONAL DERECHO\nESTRIBOSS")
    assert not _errores(ficha, contiene="ACERO ADICIONAL")


# --- §4.7 M2: ESTRIBOSS en columnas HV-LEV ---
def test_auditor_estriboss_columna_hvlev():
    """§4.7 M2: en HV-LEV las columnas llevan el rótulo exacto 'ESTRIBOSS'."""
    assert _errores(_ficha(observaciones_texto="ACERO LONGITUDINAL\nESTRIBOS"), contiene="ESTRIBOSS")
    assert not _errores(_ficha(observaciones_texto="ACERO LONGITUDINAL\nESTRIBOSS"), contiene="ESTRIBOSS")


def test_auditor_estriboss_sin_distinguir_mayusculas():
    """D11: el chequeo 'ESTRIBOSS' no distingue mayúsculas (como los demás)."""
    ficha = _ficha(observaciones_texto="Acero longitudinal\nEstriboss")
    assert not _errores(ficha, contiene="ESTRIBOSS")


def test_auditor_estriboss_columna_circular():
    """NUEVA N11 / §4.7 M2: 'COLUMNA CIRCULAR' también exige 'ESTRIBOSS' en HV-LEV."""
    ficha = _ficha(tipo_elemento="COLUMNA CIRCULAR", observaciones_texto="ACERO LONGITUDINAL\nESTRIBOS")
    assert _errores(ficha, contiene="ESTRIBOSS")


def test_auditor_estriboss_no_aplica_fuera_de_hvlev():
    """§4.7 M2: la doble S es exclusiva de HV-LEV."""
    ficha = _ficha(observaciones_texto="ACERO LONGITUDINAL\nESTRIBOS")
    assert not _errores(ficha, formato="STP-MIVED", contiene="ESTRIBOSS")


# --- Error #10 ---
@pytest.mark.parametrize("frase", ["Referencia de Plano", "Fuente de los datos", "Verificación en campo"])
def test_auditor_10_cajas_prohibidas(frase):
    """Error #10: cajas editoriales prohibidas en la ficha."""
    ficha = _ficha(observaciones_texto=f"{frase}: algo\nESTRIBOSS")
    assert _errores(ficha, contiene="#10")


def test_auditor_10_verificacion_sin_tilde():
    """NUEVA N12 / error #10: 'Verificacion en campo' sin tilde también es caja prohibida."""
    ficha = _ficha(observaciones_texto="Verificacion en campo: algo\nESTRIBOSS")
    assert _errores(ficha, contiene="#10")


def test_auditor_10_nota_pendiente_permitida():
    """P7 / error #10: 'NOTA PENDIENTE' no es caja prohibida."""
    ficha = _ficha(observaciones_texto="NOTA PENDIENTE: revisar en la próxima visita\nESTRIBOSS")
    assert not _errores(ficha, contiene="#10")


# --- Error #11 ---
@pytest.mark.parametrize("tipo", ["LOSA MACIZA", "LOSA ALIGERADA"])
def test_auditor_11_losa_con_ejes(tipo):
    """Error #11: las losas nunca llevan ejes."""
    ficha = _ficha(tipo_elemento=tipo, ejes="EJE C, ENTRE 2-3", observaciones_texto="ACERO")
    assert _errores(ficha, formato="STP-MIVED", contiene="#11")


def test_auditor_11_losa_guion_largo_ok():
    """Error #11: losa con '—' -> sin error."""
    ficha = _ficha(tipo_elemento="LOSA MACIZA", ejes=GUION_LARGO, observaciones_texto="ACERO")
    assert not _errores(ficha, formato="STP-MIVED", contiene="#11")


def test_auditor_11_no_aplica_a_platea():
    """N15 + T4b (respuesta de Steven): la PLATEA no es losa; no se le exige '—'.
    Sus EJES van como área '(A-B),(1-2)' -> sin error #11."""
    ficha = _ficha(tipo_elemento="PLATEA", ejes="(A-B),(1-2)", observaciones_texto="ACERO")
    assert not _errores(ficha, formato="STP-MIVED", contiene="#11")


def test_auditor_11_platea_area_con_prima_ok():
    """T4b (respuesta de Steven): ejes con prima también valen en el área de la platea."""
    ficha = _ficha(tipo_elemento="PLATEA", ejes="(A'-B),(1-2')", observaciones_texto="ACERO")
    assert not _errores(ficha, formato="STP-MIVED", contiene="#11")


@pytest.mark.parametrize("ejes", [
    GUION_LARGO, PENDIENTE, "EJE A-1", "EJE D-E,4", "(A-B)", "(A-B), (1-2)", "(a-b),(1-2)", "(1-2),(A-B)", "",
])
def test_auditor_11_platea_sin_formato_area_rechazada(ejes):
    """T4b (respuesta de Steven): en PLATEA un EJES que no sea área '(L-L),(N-N)' es error #11
    y queda como 'pendiente de verificar' (incluido '—', que es solo de losas)."""
    ficha = _ficha(tipo_elemento="PLATEA", ejes=ejes, observaciones_texto="ACERO")
    errs = _errores(ficha, formato="STP-MIVED", contiene="#11")
    assert errs
    assert any(PENDIENTE in e for e in errs)


def test_auditor_11_losa_sigue_con_guion_largo_no_area():
    """T4b (respuesta de Steven): las losas no cambian; el formato de área en una losa es error #11."""
    ficha = _ficha(tipo_elemento="LOSA MACIZA", ejes="(A-B),(1-2)", observaciones_texto="ACERO")
    assert _errores(ficha, formato="STP-MIVED", contiene="#11")


def test_auditor_11_platea_no_cae_en_regla_de_muro():
    """T4b: la regla N13 de muros (sin paréntesis) no se aplica a la platea; su área sí lleva paréntesis."""
    ficha = _ficha(tipo_elemento="PLATEA", ejes="(A-B),(1-2)", observaciones_texto="ACERO")
    assert not any("muro" in e.lower() for e in _errores(ficha, formato="STP-MIVED", contiene="#11"))


def test_auditor_11_muro_con_fila_rechazado():
    """NUEVA N13 / §4.4: muro con 'FILA' o paréntesis en EJES es error #11."""
    ficha = _ficha(tipo_elemento="MURO DE HORMIGON", ejes="EJE D-E (FILA 4)", observaciones_texto="ACERO")
    assert _errores(ficha, formato="STP-MIVED", contiene="#11")


def test_auditor_11_muro_formato_correcto_ok():
    """§4.4: muro con 'EJE D-E,4' -> sin error #11."""
    ficha = _ficha(tipo_elemento="MURO DE HORMIGON", ejes="EJE D-E,4", observaciones_texto="ACERO")
    assert not _errores(ficha, formato="STP-MIVED", contiene="#11")


# --- Error #12: fecha ---
@pytest.mark.parametrize("fecha", [FECHA_EJEMPLO, "29/02/2028"])
def test_auditor_fecha_valida_11_09_2026(fecha):
    """§5.2 / error #12: 'DD/MM/AAAA' válida (incluido 29/02 de año bisiesto) -> sin error."""
    assert not _errores(_ficha(fecha=fecha), contiene="#12")


@pytest.mark.parametrize("fecha", ["9/11/2026", "09/11/26", "2026-09-11", "11-09-2026"])
def test_auditor_fecha_m_d_aaaa_rechazada(fecha):
    """§5.2 / error #12: formatos distintos de DD/MM/AAAA se rechazan."""
    assert _errores(_ficha(fecha=fecha), contiene="#12")


@pytest.mark.parametrize("fecha", ["31/02/2026", "29/02/2027", "31/04/2026"])
def test_auditor_fecha_imposible_31_02_rechazada(fecha):
    """D10 / error #12: fechas imposibles en el calendario se rechazan."""
    assert _errores(_ficha(fecha=fecha), contiene="#12")


def test_auditor_12_fecha_vacia_pendiente():
    """NUEVA N14 / Regla de Oro #1: ficha sin fecha -> error #12."""
    assert _errores(_ficha(fecha=""), contiene="#12")
    sin_clave = _ficha()
    del sin_clave["fecha"]
    assert _errores(sin_clave, contiene="#12")


@pytest.mark.parametrize("fecha", [date(2026, 9, 11), 11092026, 11.09])  # SINTÉTICO: tipos no str
def test_auditor_12_t9_fecha_no_str_pendiente(fecha):
    """T9 (auditoría Gemini): fecha que no es str (date, int, float) -> error #12 con
    'pendiente de verificar', sin TypeError; no se convierte en silencio."""
    errores = _errores(_ficha(fecha=fecha), contiene="#12")
    assert len(errores) == 1
    assert PENDIENTE in errores[0] and "fecha" in errores[0]


@pytest.mark.parametrize("campo, error", [
    ("nombre_proyecto", "#8"),
    ("ejes", "#11"),
    ("observaciones_texto", "#9"),
    ("tipo_elemento", "#9"),
])
@pytest.mark.parametrize("valor", [123, date(2026, 9, 11), ["EJE F-11"]])  # SINTÉTICO: tipos no str
def test_auditor_t9_campos_texto_no_str_pendiente(campo, error, valor):
    """T9 (auditoría Gemini): nombre_proyecto, ejes, observaciones_texto y tipo_elemento con un
    tipo que no es str -> error con 'pendiente de verificar' que nombra el campo, sin lanzar."""
    for formato in ("HV-LEV", "STP-MIVED", "CATDIC-STP"):
        errores = _errores(_ficha(**{campo: valor}), formato=formato, contiene=error)
        assert any(PENDIENTE in e and f"'{campo}'" in e for e in errores)


def test_auditor_t9_tipo_no_str_con_medidas_obra_controlado():
    """T9: tipo_elemento no str con 'medidas_obra' -> error #12 'pendiente de verificar' (recubrimiento
    no definido), sin TypeError."""
    ficha = _ficha(tipo_elemento=5, medidas_obra=[_medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M,
                                                          VALOR_PLANO_COLUMNA_M)])
    errores = _errores(ficha, formato="STP-MIVED", contiene="#12")
    assert any("OBRA" in e and PENDIENTE in e for e in errores)


# --- Error #16 ---
@pytest.mark.parametrize("campo", ["firma_inspector_imagen", "firma_texto_fabricado"])
def test_auditor_16_firma_fabricada(campo):
    """Error #16 / §3.1: las firmas nunca se fabrican."""
    assert _errores(_ficha(**{campo: "firma.png"}), contiene="#16")


def test_auditor_16_sin_firma_ok():
    """Error #16: sin campos de firma -> sin error."""
    assert not _errores(_ficha(), contiene="#16")


# =====================================================================
# T5 — Error #12: cuantía recalculada (§4.6) y columna OBRA (§4.5)
# =====================================================================
CUANTIA_COPIADA_OTRO_ELEMENTO = 0.0185  # NORMA: CLAUDE.md §4.6 (ejemplo; aquí hace de cuantía copiada)
PESO_LIMITE_PDF_BYTES = 30_000_000  # NORMA: CLAUDE.md §5.2 (< 30 MB; se toma 30 MB decimal, el más estricto)
PESO_PDF_PEQUENO_BYTES = 10  # SINTÉTICO: no es dato de proyecto


def _cuantia_esperada(en_porcentaje: bool) -> float:
    """Recalcula As_total/(b*h) con la tabla P4, sin usar el motor."""
    as_cm2 = sum(c * AREA_BARRA_CONFIRMADA_CM2[d] for c, d in BARRAS_SECCION)
    rho = as_cm2 / ((B_SECCION_M * 100) * (H_SECCION_M * 100))
    if en_porcentaje:
        return round(rho * 100, DECIMALES_CUANTIA_PORCENTAJE)
    return round(rho, DECIMALES_CUANTIA_DECIMAL)


def _ficha_cuantia(cuantia, **cambios):
    datos = dict(
        cuantia_declarada=cuantia,
        seccion_b_m=B_SECCION_M,
        seccion_h_m=H_SECCION_M,
        barras_longitudinales=BARRAS_SECCION,
    )
    datos.update(cambios)
    return _ficha(**datos)


def test_auditor_12_cuantia_recalculada_stp_mived_ok():
    """§4.6: STP-MIVED con la cuantía decimal recalculada -> sin error #12."""
    ficha = _ficha_cuantia(_cuantia_esperada(False))
    assert not _errores(ficha, formato="STP-MIVED", contiene="#12")


def test_auditor_12_cuantia_recalculada_catdic_stp_ok():
    """§4.6: CATDIC-STP con la cuantía en % recalculada (número o texto con '%') -> sin error #12."""
    pct = _cuantia_esperada(True)
    assert not _errores(_ficha_cuantia(pct), formato="CATDIC-STP", contiene="#12")
    assert not _errores(_ficha_cuantia(f"{pct}%"), formato="CATDIC-STP", contiene="#12")


def test_auditor_12_cuantia_no_recalculada():
    """Error #12 / §4.6: cuantía copiada de otro elemento -> 'cuantía no coincide con el cálculo'."""
    assert CUANTIA_COPIADA_OTRO_ELEMENTO != _cuantia_esperada(False)
    errores = _errores(_ficha_cuantia(CUANTIA_COPIADA_OTRO_ELEMENTO), formato="STP-MIVED", contiene="#12")
    assert len(errores) == 1
    assert "cuantia no coincide con el calculo" in _sin_tildes(errores[0]).lower()


@pytest.mark.parametrize("formato, en_porcentaje", [("STP-MIVED", True), ("CATDIC-STP", False)])
def test_auditor_12_cuantia_unidad_cambiada(formato, en_porcentaje):
    """§4.6: decimal en STP-MIVED y % en CATDIC-STP; la unidad cambiada es error #12."""
    ficha = _ficha_cuantia(_cuantia_esperada(en_porcentaje))
    errores = _errores(ficha, formato=formato, contiene="#12")
    assert errores and "no coincide" in errores[0]


@pytest.mark.parametrize("faltante", ["seccion_b_m", "seccion_h_m", "barras_longitudinales"])
def test_auditor_12_cuantia_sin_datos_pendiente(faltante):
    """Regla de Oro #1: sin b, h o barras no se recalcula ni se da por buena -> pendiente de verificar."""
    ficha = _ficha_cuantia(_cuantia_esperada(False))
    del ficha[faltante]
    errores = _errores(ficha, formato="STP-MIVED", contiene="#12")
    assert len(errores) == 1
    assert re.search(PENDIENTE_RE, errores[0])
    assert "no coincide" not in errores[0]


def test_auditor_12_cuantia_diametro_desconocido_pendiente():
    """Regla de Oro #1: diámetro fuera de la tabla P4 -> pendiente de verificar, sin excepción."""
    ficha = _ficha_cuantia(_cuantia_esperada(False), barras_longitudinales=[(4, DIAMETRO_INEXISTENTE)])  # SINTÉTICO: no es dato de proyecto
    errores = _errores(ficha, formato="STP-MIVED", contiene="#12")
    assert errores and re.search(PENDIENTE_RE, errores[0])


def test_auditor_12_cuantia_no_numerica_pendiente():
    """Regla de Oro #1: cuantía declarada no numérica -> pendiente de verificar."""
    errores = _errores(_ficha_cuantia(PENDIENTE), formato="STP-MIVED", contiene="#12")
    assert errores and re.search(PENDIENTE_RE, errores[0])


def test_auditor_12_cuantia_formato_sin_unidad_pendiente():
    """§4.6 solo define la unidad en STP-MIVED y CATDIC-STP; en otro formato -> pendiente de verificar."""
    errores = _errores(_ficha_cuantia(_cuantia_esperada(False)), formato="HV-LEV", contiene="#12")
    assert errores and re.search(PENDIENTE_RE, errores[0])


def test_auditor_12_sin_cuantia_no_se_revisa():
    """Una ficha que no imprime cuantía no genera error #12 por cuantía."""
    assert not _errores(_ficha(), formato="STP-MIVED", contiene="#12")


def _medida(plano, acero, obra, dimension="b"):
    return {"dimension": dimension, "valor_plano_m": plano, "medida_acero_campo_m": acero, "valor_obra_m": obra}


def test_auditor_12_obra_conforme_valor_plano_ok():
    """§4.5: acero + 2*rec = plano -> OBRA lleva el valor del plano, sin error."""
    ficha = _ficha(medidas_obra=[_medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M, VALOR_PLANO_COLUMNA_M)])
    assert not _errores(ficha, formato="STP-MIVED", contiene="#12")


def test_auditor_12_obra_sin_correccion_recubrimiento():
    """Error #12: OBRA con la medida sobre el acero (sin sumar 2*rec) -> error."""
    ficha = _ficha(medidas_obra=[_medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M,
                                         MEDIDA_ACERO_COLUMNA_CONFORME_M)])
    errores = _errores(ficha, formato="STP-MIVED", contiene="#12")
    assert len(errores) == 1
    assert "OBRA" in errores[0] and "recubrimiento" in errores[0]


def test_auditor_12_obra_discrepancia_corregida_ok():
    """§4.5: con discrepancia, OBRA = medida corregida (0.30 + 0.08 = 0.38) -> sin error de coherencia."""
    corregida = round(MEDIDA_ACERO_COLUMNA_DISCREPANTE_M + 2 * REC_COLUMNA_VIGA_RIOSTRA_MURO_HA_M, 4)
    ficha = _ficha(medidas_obra=[_medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_DISCREPANTE_M, corregida)])
    assert not _errores(ficha, formato="STP-MIVED", contiene="#12")


def test_auditor_12_obra_discrepancia_con_valor_plano_rechazada():
    """Error #12: hay discrepancia pero OBRA muestra el valor del plano -> error."""
    ficha = _ficha(medidas_obra=[_medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_DISCREPANTE_M,
                                         VALOR_PLANO_COLUMNA_M)])
    assert _errores(ficha, formato="STP-MIVED", contiene="#12")


def test_auditor_12_obra_sin_medida_d1():
    """D1: sin medida en campo, OBRA = valor del plano (ok); otro valor -> error."""
    ok = _ficha(medidas_obra=[_medida(VALOR_PLANO_COLUMNA_M, None, VALOR_PLANO_COLUMNA_M)])
    assert not _errores(ok, formato="STP-MIVED", contiene="#12")
    mal = _ficha(medidas_obra=[_medida(VALOR_PLANO_COLUMNA_M, None, MEDIDA_ACERO_COLUMNA_CONFORME_M)])
    assert _errores(mal, formato="STP-MIVED", contiene="#12")


def test_auditor_12_obra_respeta_tolerancia_visita():
    """P2: con la tolerancia de la visita, 0.403 vs 0.40 es conforme -> OBRA = plano; sin tolerancia no."""
    medidas = [_medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CASI_M, VALOR_PLANO_COLUMNA_M)]
    con_tol = _ficha(medidas_obra=medidas, tolerancia_visita_m=TOLERANCIA_VISITA_AMPLIA_M)
    assert not _errores(con_tol, formato="STP-MIVED", contiene="#12")
    sin_tol = _ficha(medidas_obra=medidas)
    assert _errores(sin_tol, formato="STP-MIVED", contiene="#12")


@pytest.mark.parametrize("tolerancia", [-0.005, "0.005"])  # SINTÉTICO: tolerancias inválidas
def test_auditor_12_t9_tolerancia_visita_invalida_controlada(tolerancia):
    """T9 / O8 (auditoría Gemini): tolerancia_visita_m negativa o no numérica -> error #12
    'pendiente de verificar' controlado (el auditor no lanza)."""
    medidas = [_medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M, VALOR_PLANO_COLUMNA_M)]
    errores = _errores(_ficha(medidas_obra=medidas, tolerancia_visita_m=tolerancia),
                       formato="STP-MIVED", contiene="#12")
    assert len(errores) == 1 and PENDIENTE in errores[0] and "tolerancia" in errores[0]


@pytest.mark.parametrize("tipo, plano, acero", [
    ("ZAPATA", VALOR_PLANO_ZAPATA_M, MEDIDA_ACERO_ZAPATA_M),
    ("LOSA", VALOR_PLANO_LOSA_M, MEDIDA_ACERO_LOSA_M),
])
def test_auditor_12_obra_usa_recubrimiento_del_tipo(tipo, plano, acero):
    """§4.5: el recubrimiento sale del tipo de la ficha (zapata 0.075, losa 0.025)."""
    ejes = GUION_LARGO if tipo == "LOSA" else "EJE F-11"
    ok = _ficha(tipo_elemento=tipo, ejes=ejes, observaciones_texto="ACERO",
                medidas_obra=[_medida(plano, acero, plano)])
    assert not _errores(ok, formato="STP-MIVED", contiene="#12")
    mal = _ficha(tipo_elemento=tipo, ejes=ejes, observaciones_texto="ACERO",
                 medidas_obra=[_medida(plano, acero, acero)])
    assert _errores(mal, formato="STP-MIVED", contiene="#12")


@pytest.mark.parametrize("cambio", [
    {"valor_plano_m": None}, {"valor_obra_m": None}, {"valor_obra_m": PENDIENTE},
])
def test_auditor_12_obra_sin_datos_pendiente(cambio):
    """Regla de Oro #1 / N1: falta plano u OBRA no es numérico -> pendiente de verificar."""
    m = _medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M, VALOR_PLANO_COLUMNA_M)
    m.update(cambio)
    errores = _errores(_ficha(medidas_obra=[m]), formato="STP-MIVED", contiene="#12")
    assert errores and re.search(PENDIENTE_RE, errores[0])


def test_auditor_12_obra_tipo_desconocido_pendiente():
    """§4.5 / P3: tipo sin recubrimiento definido (perfil metálico) -> pendiente de verificar, sin excepción."""
    ficha = _ficha(tipo_elemento="PERFIL W", observaciones_texto="ACERO",
                   medidas_obra=[_medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M,
                                         VALOR_PLANO_COLUMNA_M)])
    errores = _errores(ficha, formato="STP-MIVED", contiene="#12")
    assert errores and re.search(PENDIENTE_RE, errores[0])


def test_auditor_12_obra_varias_dimensiones():
    """Cada dimensión se revisa por separado; el error nombra la dimensión mal corregida."""
    ficha = _ficha(medidas_obra=[
        _medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M, VALOR_PLANO_COLUMNA_M, dimension="b"),
        _medida(VALOR_PLANO_COLUMNA_M, MEDIDA_ACERO_COLUMNA_CONFORME_M, MEDIDA_ACERO_COLUMNA_CONFORME_M,
                dimension="h"),
    ])
    errores = _errores(ficha, formato="STP-MIVED", contiene="#12")
    assert len(errores) == 1 and "'h'" in errores[0]


# =====================================================================
# T5 — Error #15: PDF generado (§5.2)
# =====================================================================
def _pdf_de_tamano(ruta, n_bytes):
    """Archivo disperso: truncate fija el tamaño sin escribir los bytes."""
    with open(ruta, "wb") as f:
        f.truncate(n_bytes)
    return ruta


def test_auditor_15_constante_peso_maximo():
    """§5.2: el límite del motor es 30 MB."""
    assert ri.PESO_MAXIMO_PDF_BYTES == PESO_LIMITE_PDF_BYTES


def test_auditor_15_pdf_bajo_limite_ok(tmp_path):
    """§5.2: PDF < 30 MB y destino nuevo -> sin errores."""
    pdf = _pdf_de_tamano(tmp_path / NOMBRE_STP_MIVED, PESO_LIMITE_PDF_BYTES - 1)
    assert ri.auditar_archivo_pdf_generado(pdf, destino_existia_antes=False) == []


@pytest.mark.parametrize("delta", [0, 1])
def test_auditor_15_pdf_mayor_30mb(tmp_path, delta):
    """Error #15 / §5.2: PDF de 30 MB o más -> error (debe ser < 30 MB)."""
    pdf = _pdf_de_tamano(tmp_path / NOMBRE_STP_MIVED, PESO_LIMITE_PDF_BYTES + delta)
    errores = ri.auditar_archivo_pdf_generado(pdf, destino_existia_antes=False)
    assert len(errores) == 1 and "#15" in errores[0] and "30 MB" in errores[0]


def test_auditor_15_destino_ya_existe(tmp_path):
    """Error #15: el destino existía antes de escribir -> sobrescritura sin v2."""
    pdf = _pdf_de_tamano(tmp_path / NOMBRE_STP_MIVED, PESO_PDF_PEQUENO_BYTES)
    errores = ri.auditar_archivo_pdf_generado(pdf, destino_existia_antes=True)
    assert len(errores) == 1 and "#15" in errores[0] and "v2" in errores[0]


def test_auditor_15_destino_desconocido_pendiente(tmp_path):
    """Regla de Oro #1: si no se registró si el destino existía -> pendiente de verificar."""
    pdf = _pdf_de_tamano(tmp_path / NOMBRE_STP_MIVED, PESO_PDF_PEQUENO_BYTES)
    errores = ri.auditar_archivo_pdf_generado(pdf, destino_existia_antes=None)
    assert errores and re.search(PENDIENTE_RE, errores[0])


def test_auditor_15_pdf_inexistente(tmp_path):
    """Error #15: si el PDF no existe se reporta y no se lanza excepción."""
    errores = ri.auditar_archivo_pdf_generado(tmp_path / NOMBRE_STP_MIVED, destino_existia_antes=False)
    assert errores and re.search(PENDIENTE_RE, errores[0])


def test_auditor_15_no_modifica_el_pdf(tmp_path):
    """El auditor solo lee: el PDF queda igual."""
    pdf = tmp_path / NOMBRE_STP_MIVED
    pdf.write_bytes(b"%PDF-1.7 contenido")  # SINTÉTICO: no es dato de proyecto
    ri.auditar_archivo_pdf_generado(pdf, destino_existia_antes=False)
    assert pdf.read_bytes() == b"%PDF-1.7 contenido"
