# BACKEND/tests/test_escaner_dropbox.py
# Etapa 1 · T4 — Escáner de carpetas de Dropbox en solo lectura (PLANES/etapa-1.md, D1-D4,
# P1, P5; CLAUDE.md §1.3, §5.1, Regla de Oro #1).
#
# Convención de datos:
#   - "# REAL: ..."      -> nombre copiado literalmente de Dropbox (listado en solo lectura
#                           el 21/10/2026). Solo se usan los nombres; el contenido es falso.
#   - "# SINTÉTICO: ..." -> dato inventado solo para probar la regla; no es dato de proyecto.
import builtins
import io
import json
import os
import pathlib
from pathlib import Path

import pytest

import config
from reglas_ingenieria import PENDIENTE
from sync.escaner_dropbox import (
    LAYOUT_NO_SOPORTADO,
    LAYOUT_SUPERVISION,
    SUBRUTA_INFORMES_PROCESADOS,
    SUBRUTA_PLANOS_SELLADOS,
    SUBRUTA_VISITAS,
    escanear_proyecto,
)

CONTENIDO_FALSO = b"%PDF-1.4 contenido sintetico de prueba\n"  # SINTÉTICO

# REAL: …\TERRA LIVING\LEVANTAMIENTO\VISITA A OBRA\<carpeta>\<PDFs>
VISITAS_TERRA_LIVING = {
    "1. FONDO DE SEPTICO": ["1. Platea.pdf"],
    "1. FUNDACIONES PARCIAL": ["2. Zapata.pdf"],
    "10 - LOSA S-6 COMPLETIVO": ["LOSAS S-6.pdf", "Pórticos S-6 Completivo.pdf"],
    "11 - COLUMNAS S-5 31-07-2026": ["Verticales S-5 Parcial.pdf"],
    "12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026": ["Verticales parcial sótano -5.pdf"],
    "13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026": ["LOSAS S-5 PARCIAL.pdf"],
    "14. VERTICALES PARCIALES S-4 28-08-2026": ["S-4 verticales parcial.pdf"],
    "15 LOSAS Y PORTICOS S-5 COMPLETIVO 02-09-2026": ["Completivo Losa Sótano 5.pdf"],
    "16. VERTICALES PARCIAL S-4 11-09-2026": ["TERRA LIVING Verticales S-4.pdf"],
    "17. COMPLETIVO VERTICALES S-4 28-09-2026": ["VERTICALES S-4 COMPLETIVO.pdf"],
    "17.PARCIAL VERTICALES S-3 28-09-2026": ["VERTICALES S-3 PARCIAL.pdf"],
    "18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026": ["Losa y viga entrepiso 4 completivo (1).pdf"],
    "19. VERTICALES S-3 COMPLETIVO 09-10-2026": [],  # REAL: carpeta sin PDF
    "2. MURO DE SEPTICO": ["3. Muro séptico.pdf"],
    "20. LOSA SOTANO 3 PARCIAL 15-10-2026": ["Losa S-3 parcial.pdf"],
    "3. VERTICALES SOTANO -7": ["4. Verticales Fundacion.pdf"],
    "4. FUNDACIONES COMPLETIVO": ["5.  Platea 06.05.2026.pdf"],
    "5. VERTICALES SOTANO -6 PARCIAL": ["6.Verticales Sotano_1x1s.pdf"],
    "6. LOSA SEPTICO": ["7. Muros y sépticos.pdf"],
    "7. LOSA SOTANO -7": ["8. Planta estructural losa de piso (S7).pdf", "CORRECIONES LOSA S-7.pdf"],
    "8 - COLUMNAS S-6 COMPLETIVO": ["10.Columnas parcial S-6.pdf"],
    "9 - LOSA S-6 PARCIAL": ["CORRECCIONES SUPERVISION 23-07-2026.pdf", "PÓRTICOS Y LOSAS S-6 PARCIAL.pdf"],
}
PLANO_SELLADO_TERRA = "TERRA LIVING -ESTRUCTURALES.pdf"  # REAL
INFORMES_TERRA = [  # REAL: …\TERRA LIVING\INFORMES\2.DATA PROCESADA\
    "MIVED - TERRA LIVING-LOSAS Y VIGAS PARCIAL SOTANO -3.PDF",
    "Terra Living - STP - Verticales Sotano S3 Parcial - 28-09-2026.pdf",
    "Terra Living - STP - Verticales Sotano S4 Completivo - 28-09-2026.pdf",
    "Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026.pdf",
]


def _crear_terra_living(raiz: Path) -> Path:
    """Árbol falso con el layout §5.1 y los nombres reales de Terra Living."""
    proyecto = raiz / "SUPERVISION" / "EN CURSO" / "TERRA LIVING"
    planos = proyecto / SUBRUTA_PLANOS_SELLADOS
    planos.mkdir(parents=True)
    (planos / PLANO_SELLADO_TERRA).write_bytes(CONTENIDO_FALSO)
    visitas = proyecto / SUBRUTA_VISITAS
    for carpeta, pdfs in VISITAS_TERRA_LIVING.items():
        (visitas / carpeta).mkdir(parents=True)
        for pdf in pdfs:
            (visitas / carpeta / pdf).write_bytes(CONTENIDO_FALSO)
    informes = proyecto / SUBRUTA_INFORMES_PROCESADOS
    informes.mkdir(parents=True)
    for nombre in INFORMES_TERRA:
        (informes / nombre).write_bytes(CONTENIDO_FALSO)
    return proyecto


def _foto_arbol(raiz: Path):
    """Ruta relativa -> (es_dir, tamaño, st_mtime_ns) de todo el árbol."""
    foto = {}
    for actual, dirs, archivos in os.walk(raiz):
        for nombre in dirs + archivos:
            ruta = Path(actual) / nombre
            st = ruta.stat()
            foto[str(ruta.relative_to(raiz))] = (ruta.is_dir(), st.st_size, st.st_mtime_ns)
    return foto


@pytest.fixture
def terra(tmp_path):
    return _crear_terra_living(tmp_path)


def _por_nombre(resultado):
    return {v["nombre_carpeta"]: v for v in resultado["visitas"]}


# =====================================================================
# LAYOUT §5.1 CON NOMBRES REALES
# =====================================================================
def test_planos_sellados_detectados(terra):
    r = escanear_proyecto(terra)
    assert r["layout"] == LAYOUT_SUPERVISION
    assert [p["nombre"] for p in r["planos_sellados"]] == [PLANO_SELLADO_TERRA]
    plano = r["planos_sellados"][0]
    assert plano["tamano_bytes"] == len(CONTENIDO_FALSO)
    assert Path(plano["ruta"]) == terra / SUBRUTA_PLANOS_SELLADOS / PLANO_SELLADO_TERRA
    assert plano["mtime"]  # informativo, ISO


def test_visitas_listadas_las_22(terra):
    r = escanear_proyecto(terra)
    assert len(r["visitas"]) == 22
    assert set(_por_nombre(r)) == set(VISITAS_TERRA_LIVING)
    for v in r["visitas"]:
        assert Path(v["ruta_carpeta"]) == terra / SUBRUTA_VISITAS / v["nombre_carpeta"]
        assert [a["nombre"] for a in v["archivos"]] == sorted(
            VISITAS_TERRA_LIVING[v["nombre_carpeta"]], key=lambda n: (n.casefold(), n)
        )
        for a in v["archivos"]:
            assert a["tamano_bytes"] == len(CONTENIDO_FALSO)
            assert Path(a["ruta"]).parent == Path(v["ruta_carpeta"])


def test_orden_estable_por_nombre_de_carpeta(terra):
    r1 = escanear_proyecto(terra)
    r2 = escanear_proyecto(str(terra))  # también acepta str
    nombres = [v["nombre_carpeta"] for v in r1["visitas"]]
    assert nombres == sorted(nombres, key=lambda n: (n.casefold(), n))
    assert json.dumps(r1, ensure_ascii=False) == json.dumps(r2, ensure_ascii=False)


def test_interpretacion_usa_parser_t3_y_regla_p1(terra):
    v = _por_nombre(escanear_proyecto(terra))
    # REAL: la carpeta trae todo
    i20 = v["20. LOSA SOTANO 3 PARCIAL 15-10-2026"]["interpretacion"]
    assert (i20["numero"], i20["clase"], i20["fecha_iso"]) == (20, "Parcial", "2026-10-15")
    assert i20["campos_pendientes"] == [] and i20["origen_fecha"] == "carpeta"
    # REAL: la clase sale del PDF (P1)
    i11 = v["11 - COLUMNAS S-5 31-07-2026"]["interpretacion"]
    assert i11["clase"] == "Parcial" and i11["origen_clase"] == "pdf"
    assert i11["pdfs_origen"]["clase"] == ["Verticales S-5 Parcial.pdf"]
    # REAL: la fecha sale del PDF (P1)
    i9 = v["9 - LOSA S-6 PARCIAL"]["interpretacion"]
    assert i9["fecha_iso"] == "2026-07-23" and i9["origen_fecha"] == "pdf"
    # REAL: sin fecha ni clase en carpeta ni PDF -> pendiente
    i3 = v["3. VERTICALES SOTANO -7"]["interpretacion"]
    assert i3["fecha_iso"] == PENDIENTE and i3["clase"] == PENDIENTE
    assert i3["campos_pendientes"] == ["fecha_visita", "clase"]
    # REAL: clase mixta (P2)
    i12 = v["12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026"]["interpretacion"]
    assert i12["clase"] == "Mixta" and len(i12["clase_detalle"]) == 2


def test_fecha_nunca_sale_de_mtime(terra):
    """P1: una visita sin fecha en carpeta ni PDF sigue pendiente aunque el PDF tenga mtime."""
    v = _por_nombre(escanear_proyecto(terra))["1. FONDO DE SEPTICO"]  # REAL
    assert v["archivos"][0]["mtime"]
    assert v["interpretacion"]["fecha_iso"] == PENDIENTE
    assert "fecha_visita" in v["interpretacion"]["campos_pendientes"]


def test_carpeta_sin_pdf_reportada(terra):
    r = escanear_proyecto(terra)
    v = _por_nombre(r)["19. VERTICALES S-3 COMPLETIVO 09-10-2026"]  # REAL: sin PDF
    assert v["archivos"] == [] and v["sin_pdf"] is True
    assert "la carpeta no tiene PDF de la visita" in v["avisos"]
    assert any("19. VERTICALES S-3 COMPLETIVO 09-10-2026" in a and "no tiene PDF" in a for a in r["avisos"])
    # La interpretación se hace igual, solo con el nombre de la carpeta
    assert v["interpretacion"]["fecha_iso"] == "2026-10-09"
    # Las demás sí tienen PDF
    assert sum(1 for x in r["visitas"] if x["sin_pdf"]) == 1


def test_aviso_de_discrepancia_del_pdf_llega_al_proyecto(terra):
    """REAL: #8 carpeta COMPLETIVO y PDF parcial -> manda la carpeta y queda aviso."""
    r = escanear_proyecto(terra)
    assert any(a.startswith("visita '8 - COLUMNAS S-6 COMPLETIVO'") and "10.Columnas parcial S-6.pdf" in a
               for a in r["avisos"])


def test_informes_procesados_listados(terra):
    r = escanear_proyecto(terra)
    nombres = [i["nombre"] for i in r["informes_procesados"]]
    assert sorted(nombres) == sorted(INFORMES_TERRA)
    for i in r["informes_procesados"]:
        assert Path(i["ruta"]).parent == terra / SUBRUTA_INFORMES_PROCESADOS


def test_sin_avisos_de_estructura_en_layout_completo(terra):
    r = escanear_proyecto(terra)
    assert all(r["rutas"][k]["existe"] for k in ("planos_sellados", "visitas", "informes_procesados"))
    assert not any(a.startswith(PENDIENTE) for a in r["avisos"])


def test_otros_archivos_y_subcarpetas_en_visita(terra):
    visita = terra / SUBRUTA_VISITAS / "6. LOSA SEPTICO"  # REAL
    (visita / "notas.txt").write_text("x")          # SINTÉTICO
    (visita / "FOTOS").mkdir()                     # SINTÉTICO
    (visita / "desktop.ini").write_text("x")       # archivo de sistema: se ignora sin aviso
    (terra / SUBRUTA_VISITAS / "suelto.pdf").write_bytes(CONTENIDO_FALSO)  # SINTÉTICO
    r = escanear_proyecto(terra)
    v = _por_nombre(r)["6. LOSA SEPTICO"]
    assert [a["nombre"] for a in v["archivos"]] == ["7. Muros y sépticos.pdf"]
    assert any("notas.txt" in a for a in v["avisos"])
    assert any("FOTOS" in a for a in v["avisos"])
    assert not any("desktop.ini" in a for a in v["avisos"])
    assert len(r["visitas"]) == 22  # el PDF suelto no es una visita
    assert any("suelto.pdf" in a for a in r["avisos"])


# =====================================================================
# RUTAS INEXISTENTES Y LAYOUT NO SOPORTADO (sin excepción)
# =====================================================================
def test_carpeta_de_proyecto_inexistente(tmp_path):
    r = escanear_proyecto(tmp_path / "SUPERVISION" / "EN CURSO" / "TORRE P16")  # REAL: ruta sembrada vieja (D3)
    assert r["layout"] == PENDIENTE
    assert r["planos_sellados"] == [] and r["visitas"] == [] and r["informes_procesados"] == []
    assert any(a.startswith(PENDIENTE) and "TORRE P16" in a for a in r["avisos"])


def test_sin_planos_sellados_ni_informes(terra):
    import shutil
    shutil.rmtree(terra / "ARCHIVOS DEL CLIENTE")
    shutil.rmtree(terra / "INFORMES")
    r = escanear_proyecto(terra)
    assert r["layout"] == LAYOUT_SUPERVISION
    assert r["planos_sellados"] == [] and r["informes_procesados"] == []
    assert len(r["visitas"]) == 22
    assert r["rutas"]["planos_sellados"]["existe"] is False
    assert any(a.startswith(PENDIENTE) and "planos sellados" in a for a in r["avisos"])
    assert any(a.startswith(PENDIENTE) and "informes procesados" in a for a in r["avisos"])


def test_planos_sellados_vacia(terra):
    (terra / SUBRUTA_PLANOS_SELLADOS / PLANO_SELLADO_TERRA).unlink()
    r = escanear_proyecto(terra)
    assert r["planos_sellados"] == []
    assert any(a.startswith(PENDIENTE) and "no tiene PDF" in a for a in r["avisos"])


def test_layout_p16_no_soportado(tmp_path):
    proyecto = tmp_path / "PROYECTO P16"  # REAL (D3)
    zapatas = proyecto / "VISITAS" / "VISITA A OBRA" / "00. ZAPATAS"  # REAL
    zapatas.mkdir(parents=True)
    (zapatas / "08-09-2025 Zapata parcial 3.pdf").write_bytes(CONTENIDO_FALSO)  # REAL
    (proyecto / "ARCHIVO DEL CLIENTE").mkdir()  # REAL
    r = escanear_proyecto(proyecto)
    assert r["layout"] == LAYOUT_NO_SOPORTADO
    assert r["visitas"] == [] and r["planos_sellados"] == []
    assert any(LAYOUT_NO_SOPORTADO in a for a in r["avisos"])


def test_layout_zoetry_no_soportado(tmp_path):
    proyecto = tmp_path / "ZOETRY CAP CANA"  # REAL (D4)
    for sub in ("01. ARCHIVOS DEL CLIENTE", "02. EVALUACION", "03. LEVANTAMIENTO", "04. COMPARTIDO"):  # REAL
        (proyecto / sub).mkdir(parents=True)
    r = escanear_proyecto(proyecto)
    assert r["layout"] == LAYOUT_NO_SOPORTADO
    assert any(LAYOUT_NO_SOPORTADO in a for a in r["avisos"])


def test_carpeta_visitas_vacia(tmp_path):
    proyecto = tmp_path / "PROYECTO SINTETICO"  # SINTÉTICO
    (proyecto / SUBRUTA_VISITAS).mkdir(parents=True)
    r = escanear_proyecto(proyecto)
    assert r["layout"] == LAYOUT_SUPERVISION and r["visitas"] == []
    assert any(a.startswith(PENDIENTE) and "no tiene carpetas de visita" in a for a in r["avisos"])


def test_error_de_lectura_no_lanza(terra, monkeypatch):
    original = pathlib.Path.iterdir
    bloqueada = terra / SUBRUTA_VISITAS / "13. LOSAS Y PORTICOS S-5 PARCIAL 19-08-2026"  # REAL

    def iterdir_falla(self):
        if self == bloqueada:
            raise PermissionError("sintetico")
        return original(self)

    monkeypatch.setattr(pathlib.Path, "iterdir", iterdir_falla)
    r = escanear_proyecto(terra)
    v = _por_nombre(r)[bloqueada.name]
    assert v["archivos"] == [] and v["sin_pdf"] is True
    assert any(a.startswith(PENDIENTE) and "no se pudo leer" in a for a in v["avisos"])


# =====================================================================
# SOLO LECTURA
# =====================================================================
def test_arbol_no_cambia_tras_escanear(terra, tmp_path):
    antes = _foto_arbol(tmp_path)
    escanear_proyecto(terra)
    escanear_proyecto(terra)
    assert _foto_arbol(tmp_path) == antes


def test_no_abre_ni_escribe_archivos(terra, monkeypatch):
    """El escáner no abre PDFs ni llama a ninguna operación de escritura."""
    def prohibido(*args, **kwargs):
        raise AssertionError(f"operación prohibida en el escáner: {args!r}")

    for nombre in ("open", "write_text", "write_bytes", "read_bytes", "read_text", "mkdir",
                   "touch", "unlink", "rmdir", "rename", "replace", "chmod"):
        monkeypatch.setattr(pathlib.Path, nombre, prohibido)
    monkeypatch.setattr(builtins, "open", prohibido)
    monkeypatch.setattr(io, "open", prohibido)
    for nombre in ("open", "remove", "unlink", "rename", "replace", "rmdir", "mkdir", "makedirs"):
        monkeypatch.setattr(os, nombre, prohibido)
    r = escanear_proyecto(terra)
    assert len(r["visitas"]) == 22


# =====================================================================
# DROPBOX REAL (solo lectura; se salta si la carpeta no existe en esta PC)
# =====================================================================
def _real(*partes) -> Path:
    return config.obtener_dropbox_raiz().joinpath(*partes)


TERRA_REAL = ("SUPERVISION", "EN CURSO", "TERRA LIVING")
P16_REAL = ("SUPERVISION", "EN CURSO", "PROYECTO P16")
ZOETRY_REAL = ("LEVANTAMIENTO", "LEV Y EVA", "EN CURSO", "ZOETRY CAP CANA")


@pytest.mark.skipif(not _real(*TERRA_REAL).is_dir(), reason="Dropbox real de Terra Living no disponible")
def test_terra_living_real():
    carpeta = _real(*TERRA_REAL)
    antes = _foto_arbol(carpeta / SUBRUTA_VISITAS)
    r = escanear_proyecto(carpeta)
    assert r["layout"] == LAYOUT_SUPERVISION
    # D1: el plano sellado vigente (si cambia, hay que revisarlo a propósito)
    planos = {p["nombre"]: p["tamano_bytes"] for p in r["planos_sellados"]}
    assert planos.get(PLANO_SELLADO_TERRA) == 57_692_938
    # D2: las 22 carpetas conocidas siguen ahí (pueden aparecer visitas nuevas)
    assert set(VISITAS_TERRA_LIVING) <= set(_por_nombre(r))
    assert _foto_arbol(carpeta / SUBRUTA_VISITAS) == antes


@pytest.mark.skipif(not _real(*P16_REAL).is_dir(), reason="Dropbox real de P16 no disponible")
def test_p16_real_no_soportado():
    r = escanear_proyecto(_real(*P16_REAL))
    assert r["layout"] == LAYOUT_NO_SOPORTADO and r["visitas"] == []


@pytest.mark.skipif(not _real(*ZOETRY_REAL).is_dir(), reason="Dropbox real de Zoetry no disponible")
def test_zoetry_real_no_soportado():
    r = escanear_proyecto(_real(*ZOETRY_REAL))
    assert r["layout"] == LAYOUT_NO_SOPORTADO and r["visitas"] == []
