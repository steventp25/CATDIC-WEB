# BACKEND/tests/test_parser_visitas.py
# Etapa 1 · T3 — Lector de nombres de carpeta y de PDF de visita (PLANES/etapa-1.md,
# respuestas de Steven P1 y P2, discrepancia D2; CLAUDE.md §5.1, §5.2, Regla de Oro #1).
#
# Convención de datos:
#   - "# REAL: ..."      -> nombre copiado literalmente de Dropbox (listado en solo lectura
#                           el 21/10/2026). Solo se usan los nombres, no el contenido.
#   - "# SINTÉTICO: ..." -> dato inventado solo para probar la regla; no es dato de proyecto.
import os
from pathlib import Path

import pytest

from reglas_ingenieria import PENDIENTE
from sync.parser_visitas import (
    combinar_datos_visita,
    interpretar_nombre_carpeta_visita,
    interpretar_nombre_pdf_visita,
)

P = PENDIENTE
SUBRUTA_VISITAS_TERRA = Path("SUPERVISION", "EN CURSO", "TERRA LIVING", "LEVANTAMIENTO", "VISITA A OBRA")

# =====================================================================
# 22 CARPETAS REALES DE TERRA LIVING
# (nombre, numero, descripcion, clase, clase_detalle, fecha_iso, fecha_ddmmaaaa, pendientes)
# =====================================================================
CARPETAS_TERRA_LIVING = [  # REAL: …\TERRA LIVING\LEVANTAMIENTO\VISITA A OBRA\
    ("1. FONDO DE SEPTICO", 1, "FONDO DE SEPTICO", P, [], P, P, ["fecha_visita", "clase"]),
    ("1. FUNDACIONES PARCIAL", 1, "FUNDACIONES", "Parcial", [], P, P, ["fecha_visita"]),
    ("10 - LOSA S-6 COMPLETIVO", 10, "LOSA S-6", "Completivo", [], P, P, ["fecha_visita"]),
    ("11 - COLUMNAS S-5 31-07-2026", 11, "COLUMNAS S-5", P, [], "2026-07-31", "31/07/2026", ["clase"]),
    (
        "12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026",
        12, "COLUMNAS S-5 Y PORTICOS S-5", "Mixta",
        [{"elementos": "COLUMNAS S-5", "clase": "Completivo"},
         {"elementos": "PORTICOS S-5", "clase": "Parcial"}],
        "2026-08-17", "17/08/2026", [],
    ),
    ("13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026", 13, "LOSAS Y PORTICOS S-5", "Parcial", [],
     "2026-08-19", "19/08/2026", []),
    ("14. VERTICALES PARCIALES S-4 28-08-2026", 14, "VERTICALES S-4", "Parcial", [],
     "2026-08-28", "28/08/2026", []),
    ("15 LOSAS Y PORTICOS S-5 COMPLETIVO 02-09-2026", 15, "LOSAS Y PORTICOS S-5", "Completivo", [],
     "2026-09-02", "02/09/2026", []),
    ("16. VERTICALES PARCIAL S-4 11-09-2026", 16, "VERTICALES S-4", "Parcial", [],
     "2026-09-11", "11/09/2026", []),
    ("17. COMPLETIVO VERTICALES S-4 28-09-2026", 17, "VERTICALES S-4", "Completivo", [],
     "2026-09-28", "28/09/2026", []),
    ("17.PARCIAL VERTICALES S-3 28-09-2026", 17, "VERTICALES S-3", "Parcial", [],
     "2026-09-28", "28/09/2026", []),
    ("18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026", 18, "LOSA Y VIGA ENTREPISO S-4", "Completivo", [],
     "2026-10-02", "02/10/2026", []),
    ("19. VERTICALES S-3 COMPLETIVO 09-10-2026", 19, "VERTICALES S-3", "Completivo", [],
     "2026-10-09", "09/10/2026", []),
    ("2. MURO DE SEPTICO", 2, "MURO DE SEPTICO", P, [], P, P, ["fecha_visita", "clase"]),
    ("20. LOSA SOTANO 3 PARCIAL 15-10-2026", 20, "LOSA SOTANO 3", "Parcial", [],
     "2026-10-15", "15/10/2026", []),
    ("3. VERTICALES SOTANO -7", 3, "VERTICALES SOTANO -7", P, [], P, P, ["fecha_visita", "clase"]),
    ("4. FUNDACIONES COMPLETIVO", 4, "FUNDACIONES", "Completivo", [], P, P, ["fecha_visita"]),
    ("5. VERTICALES SOTANO -6 PARCIAL", 5, "VERTICALES SOTANO -6", "Parcial", [], P, P, ["fecha_visita"]),
    ("6. LOSA SEPTICO", 6, "LOSA SEPTICO", P, [], P, P, ["fecha_visita", "clase"]),
    ("7. LOSA SOTANO -7", 7, "LOSA SOTANO -7", P, [], P, P, ["fecha_visita", "clase"]),
    ("8 - COLUMNAS S-6 COMPLETIVO", 8, "COLUMNAS S-6", "Completivo", [], P, P, ["fecha_visita"]),
    ("9 - LOSA S-6 PARCIAL", 9, "LOSA S-6", "Parcial", [], P, P, ["fecha_visita"]),
]


def test_son_22_carpetas_reales():
    """D2: hay 22 carpetas de visita reales en Terra Living."""
    assert len(CARPETAS_TERRA_LIVING) == 22
    assert len({c[0] for c in CARPETAS_TERRA_LIVING}) == 22


@pytest.mark.parametrize(
    "nombre,numero,descripcion,clase,detalle,fecha_iso,fecha_dd,pendientes",
    CARPETAS_TERRA_LIVING,
    ids=[c[0] for c in CARPETAS_TERRA_LIVING],
)
def test_carpeta_real_terra_living(nombre, numero, descripcion, clase, detalle, fecha_iso, fecha_dd, pendientes):
    """§5.1 + D2 + P2: lectura literal del nombre; lo que falta queda pendiente de verificar."""
    r = interpretar_nombre_carpeta_visita(nombre)
    assert r["nombre_original"] == nombre
    assert r["numero"] == numero
    assert r["descripcion"] == descripcion
    assert r["clase"] == clase
    assert r["clase_detalle"] == detalle
    assert r["fecha_iso"] == fecha_iso
    assert r["fecha_ddmmaaaa"] == fecha_dd
    assert r["campos_pendientes"] == pendientes
    # Cada pendiente tiene su motivo (para la Mesa de Dudas) y nada más
    assert sorted(r["motivos"]) == sorted(pendientes)
    assert r["ambiguos"] == []


def test_lista_coincide_con_dropbox_si_esta_disponible():
    """Comprobación opcional, en solo lectura: los 22 nombres son los de la carpeta real."""
    config = pytest.importorskip("config")
    obtener_raiz = getattr(config, "obtener_dropbox_raiz", None)
    raiz = obtener_raiz() if obtener_raiz else Path(getattr(config, "DROPBOX_RAIZ", ""))
    carpeta = Path(raiz) / SUBRUTA_VISITAS_TERRA
    if not carpeta.is_dir():
        pytest.skip(f"Dropbox no disponible: {carpeta}")
    reales = sorted(e.name for e in os.scandir(carpeta) if e.is_dir())
    assert reales == sorted(c[0] for c in CARPETAS_TERRA_LIVING)


# ---- Ejemplos del plan (criterios de aceptación de T3) ----
def test_ejemplo_plan_20_parcial_sin_pendientes():
    r = interpretar_nombre_carpeta_visita("20. LOSA SOTANO 3 PARCIAL 15-10-2026")  # REAL
    assert (r["numero"], r["clase"], r["fecha_iso"], r["campos_pendientes"]) == (20, "Parcial", "2026-10-15", [])


def test_ejemplo_plan_11_clase_pendiente():
    r = interpretar_nombre_carpeta_visita("11 - COLUMNAS S-5 31-07-2026")  # REAL
    assert r["clase"] == PENDIENTE
    assert "clase" in r["campos_pendientes"]


def test_ejemplo_plan_3_fecha_y_clase_pendientes():
    r = interpretar_nombre_carpeta_visita("3. VERTICALES SOTANO -7")  # REAL
    assert r["fecha_iso"] == PENDIENTE and r["fecha_ddmmaaaa"] == PENDIENTE
    assert r["clase"] == PENDIENTE
    assert r["campos_pendientes"] == ["fecha_visita", "clase"]


def test_ejemplo_plan_17_parcial_sin_espacio():
    r = interpretar_nombre_carpeta_visita("17.PARCIAL VERTICALES S-3 28-09-2026")  # REAL
    assert (r["numero"], r["clase"]) == (17, "Parcial")


def test_ejemplo_plan_12_mixta():
    """P2: las dos clases se parten sin adivinar en un único ' Y '."""
    r = interpretar_nombre_carpeta_visita("12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026")  # REAL
    assert r["clase"] == "Mixta"
    assert r["clase_detalle"] == [
        {"elementos": "COLUMNAS S-5", "clase": "Completivo"},
        {"elementos": "PORTICOS S-5", "clase": "Parcial"},
    ]


# ---- Casos límite sintéticos de la carpeta ----
@pytest.mark.parametrize("nombre,motivo_contiene", [
    ("5. LOSA S-1 PARCIAL 31-02-2026", "no existe"),               # SINTÉTICO: fecha inexistente
    ("5. LOSA S-1 PARCIAL 29-02-2026", "no existe"),               # SINTÉTICO: 2026 no es bisiesto
    ("5. LOSA S-1 PARCIAL 01-10-2026 02-10-2026", "varias fechas"),  # SINTÉTICO: dos fechas
    ("5. LOSA S-1 PARCIAL 06.05.2026", "formato distinto"),        # SINTÉTICO: otro formato
])
def test_fecha_ambigua_queda_pendiente(nombre, motivo_contiene):
    """Regla de Oro #1 + error #12: no se corrige ni se adivina la fecha."""
    r = interpretar_nombre_carpeta_visita(nombre)
    assert r["fecha_iso"] == PENDIENTE and r["fecha_ddmmaaaa"] == PENDIENTE
    assert "fecha_visita" in r["campos_pendientes"]
    assert "fecha_visita" in r["ambiguos"]
    assert motivo_contiene in r["motivos"]["fecha_visita"]


def test_fecha_bisiesta_valida():
    r = interpretar_nombre_carpeta_visita("5. LOSA S-1 PARCIAL 29-02-2028")  # SINTÉTICO
    assert (r["fecha_iso"], r["fecha_ddmmaaaa"]) == ("2028-02-29", "29/02/2028")


@pytest.mark.parametrize("nombre", [
    "LOSA S-1 PARCIAL 15-10-2026",      # SINTÉTICO: sin número
    "15-10-2026 LOSA S-1 PARCIAL",      # SINTÉTICO: empieza por fecha, no por número
    "X. LOSA S-1 PARCIAL 15-10-2026",   # SINTÉTICO: número ilegible
])
def test_numero_ilegible_queda_pendiente(nombre):
    r = interpretar_nombre_carpeta_visita(nombre)
    assert r["numero"] == PENDIENTE
    assert "numero" in r["campos_pendientes"]


def test_empieza_por_fecha_conserva_la_fecha():
    r = interpretar_nombre_carpeta_visita("15-10-2026 LOSA S-1 PARCIAL")  # SINTÉTICO
    assert r["fecha_iso"] == "2026-10-15"
    assert r["clase"] == "Parcial"


@pytest.mark.parametrize("nombre", [
    "5. LOSA PARCIAL COMPLETIVO S-1 15-10-2026",                     # SINTÉTICO: sin conector
    "5. LOSA PARCIAL Y VIGA Y COLUMNA COMPLETIVO S-1 15-10-2026",    # SINTÉTICO: dos " Y " posibles
    "5. PARCIAL Y COMPLETIVO 15-10-2026",                            # SINTÉTICO: grupos sin elementos
    "5. LOSA PARCIAL Y VIGA COMPLETIVO Y COLUMNA PARCIAL 15-10-2026",  # SINTÉTICO: tres grupos
])
def test_mixta_que_no_se_puede_partir_queda_pendiente(nombre):
    """P2: si no se puede partir sin adivinar, clase pendiente y a dudas."""
    r = interpretar_nombre_carpeta_visita(nombre)
    assert r["clase"] == PENDIENTE
    assert r["clase_detalle"] == []
    assert "clase" in r["campos_pendientes"]
    assert "clase" in r["ambiguos"]


def test_misma_clase_repetida_no_es_mixta():
    r = interpretar_nombre_carpeta_visita("5. LOSAS PARCIAL Y VIGAS PARCIALES S-1 15-10-2026")  # SINTÉTICO
    assert r["clase"] == "Parcial"
    assert r["clase_detalle"] == []
    assert r["descripcion"] == "LOSAS Y VIGAS S-1"


def test_clase_no_se_lee_dentro_de_otra_palabra():
    """Solo palabras completas: 'PARCIALMENTE' no es la clase Parcial."""
    r = interpretar_nombre_carpeta_visita("5. LOSA PARCIALMENTE S-1 15-10-2026")  # SINTÉTICO
    assert r["clase"] == PENDIENTE


def test_sin_descripcion_queda_pendiente():
    r = interpretar_nombre_carpeta_visita("5. PARCIAL 15-10-2026")  # SINTÉTICO
    assert r["descripcion"] == PENDIENTE
    assert r["campos_pendientes"] == ["descripcion"]


# =====================================================================
# NOMBRES DE PDF (respuesta de Steven P1)
# (nombre_pdf, fecha_iso, fecha_ddmmaaaa, clase, pendientes, ambiguos)
# =====================================================================
PDFS_REALES = [
    # REAL: PDFs dentro de las carpetas de visita de Terra Living
    ("1. Platea.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("2. Zapata.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("LOSAS S-6.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("Pórticos S-6 Completivo.pdf", P, P, "Completivo", ["fecha_visita"], []),
    ("Verticales S-5 Parcial.pdf", P, P, "Parcial", ["fecha_visita"], []),
    ("Verticales parcial sótano -5.pdf", P, P, "Parcial", ["fecha_visita"], []),
    ("LOSAS S-5 PARCIAL.pdf", P, P, "Parcial", ["fecha_visita"], []),
    ("S-4 verticales parcial.pdf", P, P, "Parcial", ["fecha_visita"], []),
    ("Completivo Losa Sótano 5.pdf", P, P, "Completivo", ["fecha_visita"], []),
    ("TERRA LIVING Verticales S-4.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("VERTICALES S-4 COMPLETIVO.pdf", P, P, "Completivo", ["fecha_visita"], []),
    ("VERTICALES S-3 PARCIAL.pdf", P, P, "Parcial", ["fecha_visita"], []),
    ("Losa y viga entrepiso 4 completivo (1).pdf", P, P, "Completivo", ["fecha_visita"], []),
    ("3. Muro séptico.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("Losa S-3 parcial.pdf", P, P, "Parcial", ["fecha_visita"], []),
    ("4. Verticales Fundacion.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("5.  Platea 06.05.2026.pdf", P, P, P, ["fecha_visita", "clase"], ["fecha_visita"]),
    ("6.Verticales Sotano_1x1s.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("7. Muros y sépticos.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("8. Planta estructural losa de piso (S7).pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("CORRECIONES LOSA S-7.pdf", P, P, P, ["fecha_visita", "clase"], []),
    ("10.Columnas parcial S-6.pdf", P, P, "Parcial", ["fecha_visita"], []),
    ("CORRECCIONES SUPERVISION 23-07-2026.pdf", "2026-07-23", "23/07/2026", P, ["clase"], []),
    ("PÓRTICOS Y LOSAS S-6 PARCIAL.pdf", P, P, "Parcial", ["fecha_visita"], []),
    # REAL: …\PROYECTO P16\VISITAS\VISITA A OBRA\00. ZAPATAS\
    ("08-09-2025 Zapata parcial 3.pdf", "2025-09-08", "08/09/2025", "Parcial", [], []),
    ("11-08-2025 Zapata Z7.pdf", "2025-08-11", "11/08/2025", P, ["clase"], []),
    ("18-07-2025 Fundaciones.pdf", "2025-07-18", "18/07/2025", P, ["clase"], []),
    ("30-06-2025 Zapatas.pdf", "2025-06-30", "30/06/2025", P, ["clase"], []),
    ("Muro de contención.pdf", P, P, P, ["fecha_visita", "clase"], []),
]


@pytest.mark.parametrize(
    "nombre_pdf,fecha_iso,fecha_dd,clase,pendientes,ambiguos",
    PDFS_REALES,
    ids=[c[0] for c in PDFS_REALES],
)
def test_pdf_real(nombre_pdf, fecha_iso, fecha_dd, clase, pendientes, ambiguos):
    """P1: fecha DD-MM-AAAA y clase desde el nombre del PDF; otro formato no se interpreta."""
    r = interpretar_nombre_pdf_visita(nombre_pdf)
    assert r["nombre_original"] == nombre_pdf
    assert r["fecha_iso"] == fecha_iso
    assert r["fecha_ddmmaaaa"] == fecha_dd
    assert r["clase"] == clase
    assert r["campos_pendientes"] == pendientes
    assert r["ambiguos"] == ambiguos


def test_pdf_ejemplo_de_steven():
    """P1: '08-09-2025 Zapata parcial 3.pdf' -> 2025-09-08, Parcial."""
    r = interpretar_nombre_pdf_visita("08-09-2025 Zapata parcial 3.pdf")  # REAL (P16)
    assert (r["fecha_iso"], r["fecha_ddmmaaaa"], r["clase"]) == ("2025-09-08", "08/09/2025", "Parcial")


def test_pdf_no_devuelve_numero_de_visita():
    """El número de los PDFs es otra numeración ('4.' dentro de la carpeta '3.')."""
    r = interpretar_nombre_pdf_visita("4. Verticales Fundacion.pdf")  # REAL
    assert "numero" not in r


# =====================================================================
# COMBINACIÓN CARPETA + PDFs (regla de Steven P1)
# =====================================================================
def _carpeta(nombre):
    return interpretar_nombre_carpeta_visita(nombre)


def _pdfs(*nombres):
    return [interpretar_nombre_pdf_visita(n) for n in nombres]


def test_combinar_carpeta_completa_manda():
    c = combinar_datos_visita(
        _carpeta("20. LOSA SOTANO 3 PARCIAL 15-10-2026"),  # SINTÉTICO (combinación)
        _pdfs("01-01-2026 Losa completivo.pdf"),           # SINTÉTICO: el PDF discrepa
    )
    assert (c["fecha_iso"], c["origen_fecha"]) == ("2026-10-15", "carpeta")
    assert (c["clase"], c["origen_clase"]) == ("Parcial", "carpeta")
    assert c["campos_pendientes"] == []
    assert len(c["avisos"]) == 2  # se informan las discrepancias, no cambian el dato


def test_combinar_fecha_desde_pdf():
    c = combinar_datos_visita(
        _carpeta("5. LOSA S-1 PARCIAL"),       # SINTÉTICO
        _pdfs("08-09-2025 Losa S-1.pdf"),      # SINTÉTICO
    )
    assert (c["fecha_iso"], c["fecha_ddmmaaaa"], c["origen_fecha"]) == ("2025-09-08", "08/09/2025", "pdf")
    assert c["pdfs_origen"]["fecha_visita"] == ["08-09-2025 Losa S-1.pdf"]
    assert (c["clase"], c["origen_clase"]) == ("Parcial", "carpeta")
    assert c["campos_pendientes"] == []
    assert "fecha_visita" not in c["motivos"]


def test_combinar_clase_desde_pdf():
    c = combinar_datos_visita(
        _carpeta("11. COLUMNAS S-5 31-07-2026"),  # SINTÉTICO
        _pdfs("Verticales S-5 Parcial.pdf", "Anexo S-5.pdf"),  # SINTÉTICO: el anexo no trae clase
    )
    assert (c["clase"], c["origen_clase"]) == ("Parcial", "pdf")
    assert c["pdfs_origen"]["clase"] == ["Verticales S-5 Parcial.pdf"]
    assert c["campos_pendientes"] == []


def test_combinar_pdfs_coinciden():
    c = combinar_datos_visita(
        _carpeta("5. LOSA S-1"),  # SINTÉTICO
        _pdfs("08-09-2025 Losa parcial.pdf", "08-09-2025 Vigas parciales.pdf"),  # SINTÉTICO
    )
    assert (c["fecha_iso"], c["origen_fecha"]) == ("2025-09-08", "pdf")
    assert (c["clase"], c["origen_clase"]) == ("Parcial", "pdf")
    assert c["campos_pendientes"] == []


def test_combinar_pdfs_discrepan_queda_pendiente():
    c = combinar_datos_visita(
        _carpeta("5. LOSA S-1"),  # SINTÉTICO
        _pdfs("08-09-2025 Losa parcial.pdf", "09-09-2025 Vigas completivo.pdf"),  # SINTÉTICO
    )
    assert (c["fecha_iso"], c["fecha_ddmmaaaa"], c["origen_fecha"]) == (PENDIENTE, PENDIENTE, None)
    assert (c["clase"], c["origen_clase"]) == (PENDIENTE, None)
    assert c["campos_pendientes"] == ["fecha_visita", "clase"]
    assert "no coinciden" in c["motivos"]["fecha_visita"]
    assert "no coinciden" in c["motivos"]["clase"]


def test_combinar_pdf_con_fecha_ilegible_bloquea():
    c = combinar_datos_visita(
        _carpeta("5. LOSA S-1 PARCIAL"),  # SINTÉTICO
        _pdfs("08-09-2025 Losa.pdf", "Losa 06.05.2026.pdf"),  # SINTÉTICO: uno en otro formato
    )
    assert (c["fecha_iso"], c["origen_fecha"]) == (PENDIENTE, None)
    assert "fecha_visita" in c["campos_pendientes"]


def test_combinar_sin_pdfs_queda_pendiente():
    c = combinar_datos_visita(_carpeta("5. LOSA S-1"), [])  # SINTÉTICO
    assert (c["fecha_iso"], c["origen_fecha"], c["clase"], c["origen_clase"]) == (PENDIENTE, None, PENDIENTE, None)
    assert c["campos_pendientes"] == ["fecha_visita", "clase"]


def test_combinar_carpeta_ambigua_no_busca_en_pdf():
    """Si la carpeta trae el dato pero ilegible, lo decide Steven; no se toma el del PDF."""
    c = combinar_datos_visita(
        _carpeta("5. LOSA S-1 PARCIAL 31-02-2026"),  # SINTÉTICO
        _pdfs("08-09-2025 Losa.pdf"),               # SINTÉTICO
    )
    assert (c["fecha_iso"], c["origen_fecha"]) == (PENDIENTE, None)
    assert "no existe" in c["motivos"]["fecha_visita"]


def test_combinar_mixta_desde_pdf():
    c = combinar_datos_visita(
        _carpeta("5. COLUMNAS Y VIGAS S-1 15-10-2026"),  # SINTÉTICO
        _pdfs("COLUMNAS COMPLETIVO Y VIGAS PARCIAL.pdf"),  # SINTÉTICO
    )
    assert (c["clase"], c["origen_clase"]) == ("Mixta", "pdf")
    assert c["clase_detalle"] == [
        {"elementos": "COLUMNAS", "clase": "Completivo"},
        {"elementos": "VIGAS", "clase": "Parcial"},
    ]


def test_combinar_no_modifica_la_entrada():
    carpeta = _carpeta("5. LOSA S-1")  # SINTÉTICO
    copia = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
             for k, v in carpeta.items()}
    combinar_datos_visita(carpeta, _pdfs("08-09-2025 Losa parcial.pdf"))  # SINTÉTICO
    assert carpeta == copia


def test_combinar_no_usa_fecha_de_modificacion(tmp_path):
    """P1: nunca mtime. Un PDF real en disco sin fecha en el nombre no aporta fecha."""
    pdf = tmp_path / "Losa S-1.pdf"  # SINTÉTICO
    pdf.write_bytes(b"%PDF-1.4\n")
    c = combinar_datos_visita(_carpeta("5. LOSA S-1 PARCIAL"), _pdfs(pdf.name))  # SINTÉTICO
    assert (c["fecha_iso"], c["origen_fecha"]) == (PENDIENTE, None)


# ---- Casos reales de combinación (carpetas y PDFs reales de Terra Living) ----
def test_combinar_real_11_clase_desde_pdf():
    c = combinar_datos_visita(
        _carpeta("11 - COLUMNAS S-5 31-07-2026"), _pdfs("Verticales S-5 Parcial.pdf"),  # REAL
    )
    assert (c["clase"], c["origen_clase"], c["campos_pendientes"]) == ("Parcial", "pdf", [])


def test_combinar_real_8_carpeta_manda_con_aviso():
    c = combinar_datos_visita(
        _carpeta("8 - COLUMNAS S-6 COMPLETIVO"), _pdfs("10.Columnas parcial S-6.pdf"),  # REAL
    )
    assert (c["clase"], c["origen_clase"]) == ("Completivo", "carpeta")
    assert c["avisos"] and "Parcial" in c["avisos"][0]
    assert c["campos_pendientes"] == ["fecha_visita"]


def test_combinar_real_4_fecha_en_otro_formato_queda_pendiente():
    c = combinar_datos_visita(
        _carpeta("4. FUNDACIONES COMPLETIVO"), _pdfs("5.  Platea 06.05.2026.pdf"),  # REAL
    )
    assert (c["fecha_iso"], c["origen_fecha"]) == (PENDIENTE, None)
    assert "06.05.2026" in c["motivos"]["fecha_visita"]
