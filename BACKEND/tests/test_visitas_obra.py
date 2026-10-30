# BACKEND/tests/test_visitas_obra.py
# Etapa 2 · T4v — Visitas de la obra: POST /api/proyectos/{id}/visitas (subir) y POST /api/proyectos/{id}/dropbox
# (conectar). PLANES/etapa-2.md, T4v; CLAUDE.md §1.3, §1.5, §5.1, Regla de Oro #1.
# Todo # SINTÉTICO: los PDF y las fotos se generan aquí; BD, Dropbox, datos y caché son carpetas temporales.
# La única prueba con el Dropbox real solo valida la ruta (lectura) y se salta si no está en esta máquina.
import hashlib
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
import visitas_obra
from reglas_ingenieria import PENDIENTE
from sync import lector_visita


def _jpeg(color=(120, 110, 100), tam=(400, 300)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", tam, color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _pdf_visita(etiquetas=("C1 A4", "", "MH4")) -> bytes:
    """PDF con la forma de una visita: una foto por página y debajo la etiqueta (12 pt negrita) y 'Creado el:'."""
    doc = pymupdf.open()
    for i, etiqueta in enumerate(etiquetas, start=1):
        hoja = doc.new_page(width=612, height=792)
        hoja.insert_image(pymupdf.Rect(56, 99, 465, 644), stream=_jpeg((100 + i * 20, 110, 100), (768, 1024)))
        y = 660
        if etiqueta:
            hoja.insert_text((56, y), etiqueta, fontname="hebo", fontsize=12)
            y += 20
        hoja.insert_text((56, y), "Creado el:", fontname="hebo", fontsize=10)
        hoja.insert_text((117, y), f"28/09/2026 11:{i:02d}", fontname="helv", fontsize=10)
    datos = doc.tobytes()
    doc.close()
    return datos


def _sha(datos: bytes) -> str:
    return hashlib.sha256(datos).hexdigest()


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    (tmp_path / "bd").mkdir()
    monkeypatch.setenv(config.ENV_DB_PATH, str(tmp_path / "bd" / "prueba.db"))
    monkeypatch.setenv(config.ENV_DROPBOX_RAIZ, str(tmp_path / "dropbox"))
    monkeypatch.setenv(config.ENV_DATOS_RAIZ, str(tmp_path / "datos"))
    monkeypatch.setenv(lector_visita.ENV_CACHE_RAIZ, str(tmp_path / "cache"))
    database.inicializar_bd()
    with TestClient(main.app) as c:   # el arranque siembra los 3 proyectos
        yield c, tmp_path


def _obra(c, nombre="Obra Sintetica", tipo="Supervisión"):
    r = c.post("/api/proyectos", json={"nombre": nombre, "tipo": tipo})
    assert r.status_code == 201, r.text
    return r.json()["proyecto"]["id"]


def _subir(c, pid, pdf=None, nombre_pdf="visita.pdf", fotos=(), **form):
    datos = {"numero": "17", "elementos": "VERTICALES", "nivel": "S-4", "fecha": "28/09/2026", "clase": "Parcial"}
    datos.update(form)
    archivos = [("pdf", (nombre_pdf, pdf if pdf is not None else _pdf_visita(), "application/pdf"))]
    archivos += [("fotos", (n, b, "image/jpeg")) for n, b in fotos]
    return c.post(f"/api/proyectos/{pid}/visitas", files=archivos, data=datos)


def _bd(sql, *args):
    conn = database.get_connection()
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def _carpeta_visitas(tmp, pid) -> Path:
    return tmp / "datos" / pid / "visitas"


def _listado(carpeta: Path) -> dict:
    """{ruta relativa: sha256} de todo lo que hay bajo `carpeta` (para comprobar que Dropbox no cambia)."""
    return {str(p.relative_to(carpeta)): _sha(p.read_bytes()) for p in sorted(carpeta.rglob("*")) if p.is_file()}


# ---------- (a) Subir visita ----------

def test_subir_visita_guarda_con_sha256_registra_y_lee(entorno):  # SINTÉTICO
    c, tmp = entorno
    pid = _obra(c)
    pdf, foto = _pdf_visita(), _jpeg()
    r = _subir(c, pid, pdf=pdf, fotos=[("foto 1.jpg", foto)])
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    nombre = "17. VERTICALES S-4 PARCIAL 28-09-2026"
    carpeta = _carpeta_visitas(tmp, pid) / nombre
    assert (carpeta / "visita.pdf").read_bytes() == pdf
    assert (carpeta / "fotos" / "foto 1.jpg").read_bytes() == foto
    assert not list(_carpeta_visitas(tmp, pid).glob(".subida-*"))   # no quedan temporales

    v = _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid)
    assert len(v) == 1
    v = v[0]
    assert (v["numero"], v["nombre_carpeta"], v["fecha_visita"], v["clase"]) == (17, nombre, "2026-09-28", "Parcial")
    assert v["ruta_carpeta"] == str(carpeta)
    archivos = json.loads(v["archivos_json"])
    assert [(a["nombre"], a["tipo"], a["sha256"]) for a in archivos] == [
        ("visita.pdf", "pdf", _sha(pdf)), ("foto 1.jpg", "foto", _sha(foto))]
    origen = json.loads(v["origen_datos_json"])
    assert origen["fuente"] == "subida" and origen["fecha"] == "usuario" and origen["clase"] == "usuario"
    assert origen["datos_usuario"]["nivel"] == "S-4"

    aud = _bd("SELECT * FROM auditoria WHERE accion = 'SUBIR_VISITA'")
    assert len(aud) == 1 and aud[0]["entidad_id"] == v["id"]
    detalle = json.loads(aud[0]["detalle_json"])
    assert {a["nombre"]: a["sha256"] for a in detalle["archivos"]} == {"visita.pdf": _sha(pdf), "foto 1.jpg": _sha(foto)}

    # El lector T3 corrió: 2 grupos (C1 A4 + su foto sin etiqueta, MH4); MH4 no se interpreta -> duda y Con dudas
    assert cuerpo["lector"]["ok"] and cuerpo["lector"]["grupos"] == 2
    elementos = _bd("SELECT etiqueta_original, id_elemento, ejes, nivel FROM elementos_visita WHERE visita_id = ? "
                    "ORDER BY orden_en_log", v["id"])
    assert elementos == [{"etiqueta_original": "C1 A4", "id_elemento": "C1", "ejes": "EJE A-4", "nivel": "S-4"},
                         {"etiqueta_original": "MH4", "id_elemento": PENDIENTE, "ejes": PENDIENTE, "nivel": "S-4"}]
    assert cuerpo["visita"]["estado"] == "Con dudas"
    assert [d["campo_afectado"] for d in cuerpo["dudas"]] == ["elemento_visita:p003"]
    assert (tmp / "cache" / pid / v["id"] / "p001.jpg").exists()


def test_subir_visita_rechaza_clase_mixta(entorno):  # SINTÉTICO
    c, tmp = entorno
    pid = _obra(c)
    for clase in ("Mixta", "MIXTO"):
        r = _subir(c, pid, clase=clase)
        assert r.status_code == 422 and "Mixta no se acepta" in r.json()["detail"]
    r = _subir(c, pid, clase="Parcialito")
    assert r.status_code == 422 and "Parcial o Completivo" in r.json()["detail"]
    assert _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid) == []
    assert not _carpeta_visitas(tmp, pid).exists()


@pytest.mark.parametrize("fecha", ["31/02/2026", "2026-09-28", "9/28/2026", "28-09-2026"])
def test_subir_visita_rechaza_fecha_mala(entorno, fecha):  # SINTÉTICO
    c, tmp = entorno
    pid = _obra(c)
    r = _subir(c, pid, fecha=fecha)
    assert r.status_code == 422 and "DD/MM/AAAA" in r.json()["detail"]
    assert _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid) == []
    assert not _carpeta_visitas(tmp, pid).exists()


def test_subir_visita_rechaza_datos_que_confunden_o_faltan(entorno):  # SINTÉTICO
    c, _ = entorno
    pid = _obra(c)
    assert "confunde" in _subir(c, pid, elementos="COLUMNAS COMPLETIVO").json()["detail"]
    assert "confunde" in _subir(c, pid, nivel="S-4 01-10-2026").json()["detail"]
    assert _subir(c, pid, numero="").status_code == 422
    assert _subir(c, pid, numero="abc").status_code == 422
    assert _subir(c, pid, nivel="").status_code == 422
    assert _subir(c, pid, elementos="A/B").status_code == 422
    assert _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid) == []


def test_subir_visita_no_sobrescribe_y_avisa_numero_repetido(entorno):  # SINTÉTICO
    c, tmp = entorno
    pid = _obra(c)
    primero, segundo = _pdf_visita(("C1 A4",)), _pdf_visita(("C2 B4",))
    assert _subir(c, pid, pdf=primero).status_code == 201
    r = _subir(c, pid, pdf=segundo)
    assert r.status_code == 201, r.text
    base = _carpeta_visitas(tmp, pid) / "17. VERTICALES S-4 PARCIAL 28-09-2026"
    assert (base / "visita.pdf").read_bytes() == primero                       # la primera no se tocó
    assert (Path(str(base) + " v2") / "visita.pdf").read_bytes() == segundo
    visitas = _bd("SELECT id, nombre_carpeta FROM visitas WHERE proyecto_id = ? ORDER BY nombre_carpeta", pid)
    assert [v["nombre_carpeta"] for v in visitas] == ["17. VERTICALES S-4 PARCIAL 28-09-2026",
                                                      "17. VERTICALES S-4 PARCIAL 28-09-2026 v2"]
    aviso = _bd("SELECT categoria FROM dudas_y_hallazgos WHERE visita_id = ? AND campo_afectado = 'numero'",
                visitas[1]["id"])
    assert aviso == [{"categoria": "HALLAZGO_INTERNO"}]   # se avisa, no se bloquea (Terra tiene dos #17)


def test_subida_fallida_no_deja_nada(entorno, monkeypatch):  # SINTÉTICO
    c, tmp = entorno
    pid = _obra(c)
    # 1. PDF ilegible
    r = _subir(c, pid, pdf=b"esto no es un pdf")
    assert r.status_code == 422 and "PDF legible" in r.json()["detail"]
    # 2. Una foto que no es imagen, después de un PDF bueno
    r = _subir(c, pid, fotos=[("buena.jpg", _jpeg()), ("mala.jpg", b"no es imagen")])
    assert r.status_code == 422 and "mala.jpg" in r.json()["detail"]
    # 3. Falla la BD a mitad de la transacción (después de mover la carpeta a su sitio)
    original = visitas_obra._auditar

    def _falla(*a, **k):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(visitas_obra, "_auditar", _falla)
    with pytest.raises(RuntimeError):
        _subir(c, pid)
    monkeypatch.setattr(visitas_obra, "_auditar", original)
    assert _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid) == []
    assert _bd("SELECT * FROM dudas_y_hallazgos WHERE proyecto_id = ? AND visita_id IS NOT NULL", pid) == []
    assert _bd("SELECT * FROM auditoria WHERE accion = 'SUBIR_VISITA'") == []
    assert not _carpeta_visitas(tmp, pid).exists() or not any(_carpeta_visitas(tmp, pid).iterdir())
    # Y después de fallar, la misma subida entra entera (sin v2: no quedó nada de antes)
    assert _subir(c, pid).status_code == 201
    assert [p.name for p in _carpeta_visitas(tmp, pid).iterdir()] == ["17. VERTICALES S-4 PARCIAL 28-09-2026"]


def test_subir_visita_sin_fecha_ni_clase_queda_pendiente_con_duda(entorno):  # SINTÉTICO
    c, _ = entorno
    pid = _obra(c)
    r = _subir(c, pid, fecha="", clase="", nombre_pdf="Fotos obra.pdf")
    assert r.status_code == 201, r.text
    v = _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid)[0]
    assert (v["fecha_visita"], v["clase"], v["estado"]) == (PENDIENTE, PENDIENTE, "Con dudas")
    assert v["nombre_carpeta"] == "17. VERTICALES S-4"
    bloqueantes = {d["campo_afectado"] for d in _bd(
        "SELECT campo_afectado FROM dudas_y_hallazgos WHERE visita_id = ? AND categoria = 'DUDA_BLOQUEANTE'", v["id"])}
    assert {"fecha_visita", "clase"} <= bloqueantes


def test_subir_visita_toma_fecha_y_clase_del_nombre_del_pdf(entorno):  # SINTÉTICO
    c, _ = entorno
    pid = _obra(c)
    r = _subir(c, pid, fecha="", clase="", nombre_pdf="VERTICALES S-4 COMPLETIVO 28-09-2026.pdf")
    assert r.status_code == 201, r.text
    v = _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid)[0]
    assert (v["fecha_visita"], v["clase"]) == ("2026-09-28", "Completivo")
    origen = json.loads(v["origen_datos_json"])
    assert origen["fecha"] == "pdf" and origen["clase"] == "pdf"


def test_subir_visita_pdf_que_contradice_al_usuario_deja_hallazgo(entorno):  # SINTÉTICO
    c, _ = entorno
    pid = _obra(c)
    r = _subir(c, pid, nombre_pdf="VISITA COMPLETIVO 01-10-2026.pdf")
    assert r.status_code == 201
    v = _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid)[0]
    assert (v["fecha_visita"], v["clase"]) == ("2026-09-28", "Parcial")   # manda lo que dio el usuario
    hallazgos = {d["campo_afectado"] for d in _bd(
        "SELECT campo_afectado FROM dudas_y_hallazgos WHERE visita_id = ? AND categoria = 'HALLAZGO_INTERNO'", v["id"])}
    assert hallazgos == {"fecha_visita", "clase"}


def test_subir_visita_obra_inexistente_o_de_levantamiento(entorno):  # SINTÉTICO
    c, _ = entorno
    assert _subir(c, "no-existe").status_code == 404
    pid = _obra(c, "Obra Lev", "Levantamiento")
    assert _subir(c, pid).status_code == 422


# ---------- (b) Conectar con Dropbox ----------

def _dropbox_obra(tmp, nombre="OBRA SINT") -> Path:
    """Árbol §5.1 de una obra en el Dropbox temporal, con dos visitas (# SINTÉTICO)."""
    obra = tmp / "dropbox" / "SUPERVISION" / "EN CURSO" / nombre
    v1 = obra / "LEVANTAMIENTO" / "VISITA A OBRA" / "1. VERTICALES S-4 PARCIAL 28-09-2026"
    v2 = obra / "LEVANTAMIENTO" / "VISITA A OBRA" / "2. LOSA S-4 COMPLETIVO"
    for carpeta in (v1, v2, obra / "INFORMES" / "2.DATA PROCESADA"):
        carpeta.mkdir(parents=True)
    (v1 / "visita 1.pdf").write_bytes(_pdf_visita(("C1 A4",)))
    (v2 / "visita 2.pdf").write_bytes(_pdf_visita(("L5",)))
    return obra


def test_conectar_dropbox_sincroniza_lee_y_no_escribe_en_dropbox(entorno):  # SINTÉTICO
    c, tmp = entorno
    pid = _obra(c)
    obra = _dropbox_obra(tmp)
    antes = _listado(tmp / "dropbox")
    ruta = obra / "LEVANTAMIENTO" / "VISITA A OBRA"
    r = c.post(f"/api/proyectos/{pid}/dropbox", json={"carpeta_visitas": f'"{ruta}"'})   # con comillas pegadas
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert _listado(tmp / "dropbox") == antes                                # Dropbox SOLO LECTURA

    assert _bd("SELECT carpeta_dropbox FROM proyectos WHERE id = ?", pid)[0]["carpeta_dropbox"] == str(obra)
    aud = _bd("SELECT * FROM auditoria WHERE accion = 'CONECTAR_DROPBOX' AND entidad_id = ?", pid)
    assert len(aud) == 1
    detalle = json.loads(aud[0]["detalle_json"])
    assert detalle["carpeta_dropbox_anterior"] == "" and detalle["carpeta_dropbox_nueva"] == str(obra)

    assert cuerpo["sync"]["visitas_nuevas"] == 2
    nuevas = {v["numero"]: v for v in cuerpo["visitas_nuevas"]}
    assert nuevas[1]["lector"]["ok"] and nuevas[1]["estado"] == "Sin procesar" and nuevas[1]["dudas"] == []
    # La #2 no trae fecha (pendiente) y su única etiqueta 'L5' no se interpreta: Con dudas
    assert nuevas[2]["estado"] == "Con dudas"
    assert {"fecha_visita", "elemento_visita:p001"} <= {d["campo_afectado"] for d in nuevas[2]["dudas"]}
    assert _bd("SELECT COUNT(*) AS n FROM elementos_visita")[0]["n"] == 2

    # Reconectar la misma carpeta: no hay visitas nuevas ni se repite el lector
    r = c.post(f"/api/proyectos/{pid}/dropbox", json={"carpeta_visitas": str(ruta)})
    assert r.status_code == 200 and r.json()["visitas_nuevas"] == [] and r.json()["sync"]["sin_cambios"] == 2
    assert _listado(tmp / "dropbox") == antes


def test_conectar_dropbox_rechaza_ruta_fuera_de_dropbox(entorno):  # SINTÉTICO
    c, tmp = entorno
    pid = _obra(c)
    fuera = tmp / "otra" / "OBRA" / "LEVANTAMIENTO" / "VISITA A OBRA"
    fuera.mkdir(parents=True)
    r = c.post(f"/api/proyectos/{pid}/dropbox", json={"carpeta_visitas": str(fuera)})
    assert r.status_code == 422 and "fuera de la raíz de Dropbox" in r.json()["detail"]
    # Con '..' se sale de Dropbox aunque empiece dentro
    truco = tmp / "dropbox" / ".." / "otra" / "OBRA" / "LEVANTAMIENTO" / "VISITA A OBRA"
    r = c.post(f"/api/proyectos/{pid}/dropbox", json={"carpeta_visitas": str(truco)})
    assert r.status_code == 422 and "fuera de la raíz de Dropbox" in r.json()["detail"]
    assert _bd("SELECT carpeta_dropbox FROM proyectos WHERE id = ?", pid)[0]["carpeta_dropbox"] == ""
    assert _bd("SELECT * FROM auditoria WHERE accion = 'CONECTAR_DROPBOX'") == []


def test_conectar_dropbox_rechaza_ruta_inexistente_relativa_o_sin_forma(entorno):  # SINTÉTICO
    c, tmp = entorno
    pid = _obra(c)
    obra = _dropbox_obra(tmp)
    casos = {
        "": "Indica la carpeta",
        "LEVANTAMIENTO\\VISITA A OBRA": "debe ser completa",
        str(obra / "LEVANTAMIENTO" / "NO EXISTE"): "no existe",
        str(obra / "LEVANTAMIENTO"): "forma esperada",
        str(obra): "forma esperada",
    }
    for ruta, texto in casos.items():
        r = c.post(f"/api/proyectos/{pid}/dropbox", json={"carpeta_visitas": ruta})
        assert r.status_code == 422 and texto in r.json()["detail"], (ruta, r.text)
    assert _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid) == []


def test_conectar_dropbox_no_conecta_una_carpeta_a_dos_obras(entorno):  # SINTÉTICO
    c, tmp = entorno
    ruta = _dropbox_obra(tmp) / "LEVANTAMIENTO" / "VISITA A OBRA"
    pid1, pid2 = _obra(c, "Obra Uno"), _obra(c, "Obra Dos")
    assert c.post(f"/api/proyectos/{pid1}/dropbox", json={"carpeta_visitas": str(ruta)}).status_code == 200
    r = c.post(f"/api/proyectos/{pid2}/dropbox", json={"carpeta_visitas": str(ruta)})
    assert r.status_code == 409 and "Obra Uno" in r.json()["detail"]
    assert _bd("SELECT * FROM visitas WHERE proyecto_id = ?", pid2) == []


def test_conectar_dropbox_obra_de_levantamiento(entorno):  # SINTÉTICO
    c, tmp = entorno
    ruta = _dropbox_obra(tmp) / "LEVANTAMIENTO" / "VISITA A OBRA"
    pid = _obra(c, "Obra Lev", "Levantamiento")
    r = c.post(f"/api/proyectos/{pid}/dropbox", json={"carpeta_visitas": str(ruta)})
    assert r.status_code == 422 and "Supervisión" in r.json()["detail"]


TERRA_VISITAS_REAL = ("SUPERVISION", "EN CURSO", "TERRA LIVING", "LEVANTAMIENTO", "VISITA A OBRA")


def test_validar_carpeta_real_de_terra(monkeypatch):
    """Solo lectura del Dropbox real: la carpeta de visitas de Terra Living pasa la validación."""
    monkeypatch.delenv(config.ENV_DROPBOX_RAIZ, raising=False)
    ruta = config.obtener_dropbox_raiz().joinpath(*TERRA_VISITAS_REAL)
    if not ruta.is_dir():
        pytest.skip(f"Dropbox real no disponible en esta máquina: {ruta}")
    rutas = visitas_obra.validar_carpeta_visitas(str(ruta))
    assert rutas["proyecto"] == config.obtener_dropbox_raiz().joinpath(*TERRA_VISITAS_REAL[:3]).resolve()


def test_conectar_dropbox_visita_con_dos_pdf_no_queda_sin_leer_en_silencio(entorno):  # SINTÉTICO
    """Como las #7, #9 y #10 reales de Terra: 2 PDF en la carpeta -> el lector no elige; duda y Con dudas."""
    c, tmp = entorno
    pid = _obra(c)
    obra = tmp / "dropbox" / "SUPERVISION" / "EN CURSO" / "OBRA DOS PDF"
    v = obra / "LEVANTAMIENTO" / "VISITA A OBRA" / "9 - LOSA S-6 PARCIAL 30-09-2026"
    v.mkdir(parents=True)
    (v / "parte 1.pdf").write_bytes(_pdf_visita(("C1 A4",)))
    (v / "parte 2.pdf").write_bytes(_pdf_visita(("C2 A4",)))
    antes = _listado(tmp / "dropbox")
    r = c.post(f"/api/proyectos/{pid}/dropbox", json={"carpeta_visitas": str(v.parent)})
    assert r.status_code == 200, r.text
    nueva = r.json()["visitas_nuevas"][0]
    assert not nueva["lector"]["ok"] and "2 PDF" in nueva["lector"]["error"]
    assert nueva["estado"] == "Con dudas"
    assert [d["campo_afectado"] for d in nueva["dudas"]] == ["lector_visita"]
    assert _bd("SELECT COUNT(*) AS n FROM auditoria WHERE accion = 'LECTOR_NO_LEYO_VISITA'")[0]["n"] == 1
    assert _listado(tmp / "dropbox") == antes
