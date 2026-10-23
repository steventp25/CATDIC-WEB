# BACKEND/generators/stp_mived.py
# Etapa 3 · T7 — Generador STP-MIVED (HTML -> PDF con Playwright), CLAUDE.md §3.2.
#
# El generador NO lee la BD: recibe diccionarios (proyecto, visita, fichas) que arma T10.
# Regla de Oro #1: aquí no hay ningún dato fijo de proyecto, de diseño ni coordenada de ejes.
# Un campo de cabecera vacío, un valor de diseño ausente o un tipo no soportado => NO se genera el
# PDF y se devuelven errores y dudas (para la Mesa de Dudas). Maquetación y rótulos portados de
# lib_pages.py sin cambiar la ortografía del formato original (APROVADOS, IMFORMACION).
import base64
import html
import io
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

from generators.comun import detalle as m4_detalle
from generators.comun import fotos as m1_fotos
from generators.comun import localizacion as m3_localizacion
from generators.comun import salida
from reglas_ingenieria import (
    PENDIENTE,
    auditar_datos_ficha_antes_de_renderizar,
    calcular_cuantia_elemento,
    evaluar_medida_acero_obra,
    obtener_recubrimiento,
    _es_fecha_ddmmaaaa_valida,
    _normalizar_texto,
)

FORMATO = "STP-MIVED"
RUTA_CSS = Path(__file__).resolve().parent / "plantillas" / "stp_mived.css"
CELDA_LOC_PX = (750, 520)       # celda de LOCALIZACION / DETALLE en la hoja fotográfica (200 dpi)
ZONA_FOTOS_PX = (1530, 1310)    # 7,65 in x 6,55 in a 200 dpi
CLASES = ("Parcial", "Completivo")

CAMPOS_PROYECTO = ("nombre", "no_solicitud", "no_licencia", "direccion_obra", "provincia", "sector",
                   "residente_obra", "carpeta_planos")
CAMPOS_VISITA = ("fecha", "clase", "elementos_txt")

# Rótulos de las filas por tipo, tal como están en el formato (lib_pages.py)
ROTULOS = {
    "viga": [("a", "Tipo de Portico :"), ("b", "Resistencia (Kg/cm²):"), ("c", "Ancho Viga (m):"),
             ("d", "Altura Viga (m):"), ("e", "Long. Tramo L (m) :"), ("f", "Espc Estribos Nodos (m):"),
             ("g", "Espc Estribos Centro (m) :"), ("h", "Diam Est.(Ø):"), ("i", "Barras Top:"),
             ("j", "Barras Bot:"), ("k", "Adic. Top:"), ("m", "Adic Bot:"),
             ("n", "Ubic./Long Solape Bot:"), ("o", "Ubic./Long Solape Top:"), ("p", "Cuantia ()"),
             ("q", "%Acero Solap")],
    "losa": [("a", None), ("b", "b. Espesor Losa. (m):"), ("c", "c. Longitud X (m):"),
             ("d", "d. Longitud Y (m):"), ("e", "e. Calzos coloc."), ("f", "f. Recubrimiento Min (m):"),
             ("g", "g. Recubrimiento Max. (m) :"), ("h", "h. Barras Top X-X:"), ("i", "i. Barras Bot X-X:"),
             ("j", "j. Adic. Top X-X:"), ("k", "k. Adic. Bot X-X :"), ("m", "m. Barras Top Y-Y:"),
             ("n", "n. Barras Bot Y-Y:"), ("o", "o. Adic. Top Y-Y:"), ("p", "p. Adic. Bot Y-Y :")],
    "muro": [("a", "a. Resistencia esperada:"), ("b", "b. Espesor muro (m):"), ("c", "c. Longitud X (m):"),
             ("d", "d. Altura (m) :"), ("e", "e. Calzos coloc. (m):"), ("f", "f. Recub. Min (m):"),
             ("g", "g. Recub. Max (m) :"), ("h", "h. As Vert. Interno :"), ("i", "i. As Vert. Externo :"),
             ("j", "j. As Hor. Interno :"), ("k", "k. As Hor. Externo :")],
    "col": [("a", "a. Tipo de Portico :"), ("b", "b. Resist. esperada (Kg/Cm):"), ("c", "c. Dim LX (m):"),
            ("d", "d. Dim LY (m):"), ("e", "e. Altura col. H (m):"), ("f", "f. Espac. estribos en nodos (m):"),
            ("g", "g. Espac. estribos paño Central (m):"), ("h", "h. Diam. Est. (Ø):"),
            ("i", "i. Eje direccion x-x:"), ("j", "j. Eje direccion y-y:"), ("k", "k. Total barras:"),
            ("m", "m. Diametro barras nudos (Ø):"), ("n", "n. Diametro barras internas (Ø):"),
            ("o", "o. Solape zona Central y Long:"), ("p", "p. Cuantia ()"), ("q", "p. % Acero solap.")],
}
# Filas que el plano (Capa 1) debe traer; el resto puede quedar vacío si el plano no lo indica.
# "Calzos coloc." (e) es una comprobación de obra: no se exige en PLANOS. Los recubrimientos f/g de losa y
# muro, en la columna PLANOS, salen de la tabla de §4.5 (pendiente de que Steven lo confirme).
OBLIGATORIAS = {
    "viga": set("bcdefghij"),
    "losa": set("abhin"),
    "muro": set("abhijk"),
    "col": set("bcdefghijkmn"),
}
# Filas que, además de las obligatorias del plano, deben venir de la visita (columna OBRA): si faltan, la celda
# queda vacía y se crea una duda que no bloquea. Los recubrimientos de OBRA salen de la ficha, nunca de §4.5.
OBRA_EXTRA = {"losa": set("efg"), "muro": set("efg")}
# Filas dimensionales (se comparan plano vs. acero medido con evaluar_medida_acero_obra, §4.5)
DIMENSIONALES = {"viga": "cd", "col": "cd", "losa": "b", "muro": "b"}
CON_CUANTIA = {"viga", "col"}
TIPOS_NO_SOPORTADOS = "perfil o conexión metálica, zapata, platea u otro"


def _vacio(valor) -> bool:
    return valor is None or str(valor).strip() == "" or str(valor).strip().lower() == PENDIENTE


def _tipo_de_fila(tipo_elemento: str) -> Optional[str]:
    t = _normalizar_texto(tipo_elemento or "")
    if t.startswith(("VIGA", "RIOSTRA", "PORTICO")):
        return "viga"
    if t.startswith("COLUMNA"):
        return "col"
    if t.startswith("LOSA"):
        return "losa"
    if t.startswith("MURO"):  # incluye MURO DE CONTENCION (recubrimiento 0.075 de §4.5)
        return "muro"
    return None


def _esc(texto) -> str:
    return html.escape("" if texto is None else str(texto))


def _b64(img: Image.Image, calidad: int = 80) -> str:
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=calidad)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode()


def _fmt_m(valor: float) -> str:
    return f"{valor:.2f}"


# ---------- Validación de cabecera ----------

def _errores_cabecera(proyecto: Dict, visita: Dict) -> List[Dict[str, str]]:
    faltas = []
    for campo in CAMPOS_PROYECTO:
        if _vacio(proyecto.get(campo)):
            faltas.append({"id_elemento": "", "campo_afectado": f"proyecto.{campo}",
                           "descripcion_pregunta": f"Falta '{campo}' del proyecto para la cabecera: {PENDIENTE}."})
    for campo in CAMPOS_VISITA:
        if _vacio(visita.get(campo)):
            faltas.append({"id_elemento": "", "campo_afectado": f"visita.{campo}",
                           "descripcion_pregunta": f"Falta '{campo}' de la visita: {PENDIENTE}."})
    fecha = visita.get("fecha")
    if not _vacio(fecha) and not (isinstance(fecha, str) and _es_fecha_ddmmaaaa_valida(fecha)):
        faltas.append({"id_elemento": "", "campo_afectado": "visita.fecha",
                       "descripcion_pregunta": f"La fecha '{fecha}' no está en formato DD/MM/AAAA (§5.2)."})
    clase = visita.get("clase")
    if not _vacio(clase) and clase not in CLASES:
        faltas.append({"id_elemento": "", "campo_afectado": "visita.clase",
                       "descripcion_pregunta": f"La clase '{clase}' debe ser Parcial o Completivo."})
    return faltas


# ---------- Armado de las filas de una ficha ----------

def _filas_de_ficha(ficha: Dict, tipo_txt: str, kind: str, tolerancia) -> Tuple[Dict, List[Dict], Dict]:
    """
    Devuelve (resultado, dudas, auditoria). resultado = {plano, obra} (letra -> texto) o None si falta algo
    que bloquea la ficha. Los recubrimientos salen de §4.5; la cuantía, de calcular_cuantia_elemento;
    las filas dimensionales de OBRA, de evaluar_medida_acero_obra.
    """
    id_el = ficha.get("titulo") or PENDIENTE
    dudas, plano_in = [], dict(ficha.get("plano") or {})
    obra_in = dict(ficha.get("obra") or {})
    medidas = dict(ficha.get("medidas") or {})
    plano: Dict[str, str] = {}
    obra: Dict[str, str] = {}
    medidas_aud: List[Dict] = []
    discrepancias: List[str] = []

    def duda(campo, texto, bloquea=True):
        dudas.append({"id_elemento": id_el, "campo_afectado": campo, "descripcion_pregunta": texto,
                      "bloquea": bloquea})

    # Valores del plano (Capa 1): lo obligatorio no puede faltar
    for letra in OBLIGATORIAS[kind]:
        if letra in DIMENSIONALES[kind] and letra in medidas:
            continue  # la fila sale de la medida del plano
        if _vacio(plano_in.get(letra)):
            duda(f"plano.{letra}", f"Falta en el plano el valor de la fila '{letra}' de {tipo_txt}: {PENDIENTE}.")
    for letra in DIMENSIONALES[kind]:
        if letra not in medidas and (kind in CON_CUANTIA or letra in OBLIGATORIAS[kind]):
            duda(f"medidas.{letra}", f"Falta la dimensión '{letra}' del plano de {tipo_txt}: {PENDIENTE}.")
    if any(d["bloquea"] for d in dudas):
        return None, dudas, {}

    rec = None
    if kind in ("losa", "muro"):
        try:
            rec = _fmt_rec(obtener_recubrimiento(tipo_txt))
        except ValueError as exc:
            duda("tipo_elemento", f"Recubrimiento no definido para '{tipo_txt}': {exc}")
            return None, dudas, {}

    for letra, _ in ROTULOS[kind]:
        if letra in ("p", "q") and kind in CON_CUANTIA:
            continue
        plano[letra] = "" if _vacio(plano_in.get(letra)) else str(plano_in[letra])
        obra[letra] = "" if _vacio(obra_in.get(letra)) else str(obra_in[letra])
    if kind in ("losa", "muro"):
        plano["f"] = plano["g"] = rec  # PLANOS: §4.5; OBRA (f, g) sale de la visita, no de la tabla

    # Columnas: "k. Total barras" debe coincidir con la suma de las barras de la ficha
    if kind == "col":
        try:
            total_barras = sum(int(n) for n, _ in ficha.get("barras") or [])
            if int(str(plano_in.get("k")).strip()) != total_barras:
                duda("plano.k", f"'Total barras' ({plano_in.get('k')}) no coincide con la suma de las barras "
                                f"({total_barras}) de {id_el}: {PENDIENTE}.")
                return None, dudas, {}
        except (ValueError, TypeError):
            duda("plano.k", f"'Total barras' o las barras de {id_el} no son numéricas: {PENDIENTE}.")
            return None, dudas, {}

    # Filas dimensionales: plano = valor del plano; OBRA = evaluar_medida_acero_obra (§4.5)
    for letra, m in medidas.items():
        if letra not in DIMENSIONALES[kind]:
            continue
        try:
            ev = evaluar_medida_acero_obra(tipo_txt, m["valor_plano_m"], m.get("medida_acero_campo_m"), tolerancia)
        except (ValueError, KeyError, TypeError) as exc:
            duda(f"medidas.{letra}", f"No se pudo evaluar la medida '{letra}' de {tipo_txt}: {exc}")
            return None, dudas, {}
        plano[letra] = _fmt_m(m["valor_plano_m"])
        if m.get("medida_acero_campo_m") is None:
            # Sin medida de campo nadie midió nada: OBRA queda VACÍA (no se copia el valor del plano)
            obra[letra] = ""
            duda(f"medidas.{letra}", f"La fila '{letra}' de {id_el} no tiene medida de campo sobre el acero: la "
                                     f"celda de OBRA queda vacía ({PENDIENTE}).", bloquea=False)
            continue
        obra[letra] = _fmt_m(ev["valor_columna_obra_m"])
        medidas_aud.append({"dimension": letra, "valor_plano_m": m["valor_plano_m"],
                            "medida_acero_campo_m": m.get("medida_acero_campo_m"),
                            "valor_obra_m": ev["valor_columna_obra_m"]})
        if not ev["conforme"]:
            discrepancias.append(f"{id_el}: {ev['hallazgo_interno']}")

    # Cuantía (decimal, §4.6): siempre calculada, nunca copiada
    aud = {"tipo_elemento": tipo_txt, "ejes": ficha.get("ejes"), "medidas_obra": medidas_aud,
           "observaciones_texto": ""}
    if kind in CON_CUANTIA:
        try:
            b, h = medidas["c"]["valor_plano_m"], medidas["d"]["valor_plano_m"]
            barras = [(int(n), d) for n, d in ficha.get("barras") or []]
            cuantia = calcular_cuantia_elemento(b, h, barras)
        except (ValueError, KeyError, TypeError) as exc:
            duda("cuantia", f"No se pudo calcular la cuantía de {tipo_txt}: {exc}")
            return None, dudas, {}
        plano["p"] = f"{cuantia:.4f}"
        aud.update(cuantia_declarada=plano["p"], seccion_b_m=b, seccion_h_m=h, barras_longitudinales=barras)
        if ficha.get("barras_obra"):
            try:
                obra["p"] = f"{calcular_cuantia_elemento(b, h, [(int(n), d) for n, d in ficha['barras_obra']]):.4f}"
            except (ValueError, TypeError) as exc:
                obra["p"] = ""
                duda("cuantia_obra", f"No se pudo calcular la cuantía en obra: {exc}", bloquea=False)
        else:
            obra["p"] = ""
        plano["q"] = "" if _vacio(plano_in.get("q")) else str(plano_in["q"])
        obra["q"] = "" if _vacio(obra_in.get("q")) else str(obra_in["q"])
    if kind == "viga":
        # Error #9 (ESTRIBOS al final): esta línea solo existe para el auditor y se arma con las filas f, g y h,
        # que ya son obligatorias en PLANOS; por eso nunca se inventa un valor. No se imprime en las hojas.
        aud["observaciones_texto"] = (f"ESTRIBOS {plano['h']} {plano['f']} NODOS / {plano['g']} CENTRO")

    # OBRA vacío en filas que debe traer la visita: queda vacío y se crea una duda (no bloquea)
    for letra in sorted(OBLIGATORIAS[kind] | OBRA_EXTRA.get(kind, set())):
        if letra in DIMENSIONALES[kind] and letra in medidas:
            continue  # ya tiene su propia duda (medidas.<letra>) si falta la medida
        if not obra.get(letra):
            duda(f"obra.{letra}", f"La fila '{letra}' de OBRA de {id_el} no tiene dato de la visita: queda vacía "
                                  f"({PENDIENTE}).", bloquea=False)
    return {"plano": plano, "obra": obra, "discrepancias": discrepancias}, dudas, aud


def _fmt_rec(valor: float) -> str:
    return f"{valor:g}"  # 0.025, 0.04, 0.075 (§4.5)


def _rotulo(kind: str, letra: str, texto: Optional[str], lado: int) -> str:
    pre = "1" if lado == 1 else "2"
    if kind == "viga":
        sep = "." if letra in "fg" else ". "
        return f"{pre}.{letra}{sep}{texto}"
    if kind == "col":
        return f"{pre}.{texto}"
    if kind == "losa" and letra == "a":
        return "1.a. RESISTENCIA ESPERADA:" if lado == 1 else "2.a.RESISTENCIA OBTENIDA:"
    return f"{pre}.{texto}"


# ---------- Páginas ----------

def _cabecera_comun(proy: Dict, fecha: str) -> str:
    return (f'<table class=hd>'
            f'<tr><td style="width:24%">No. DE LA SOLICITUD :</td><td colspan=3>{_esc(proy["no_solicitud"])}</td></tr>'
            f'<tr><td>NO. LICENCIA&nbsp;&nbsp;:</td><td colspan=3>{_esc(proy["no_licencia"])}</td></tr>'
            f'<tr><td>NOMBRE DEL PROYECTO&nbsp;:</td><td colspan=3>{_esc(proy["nombre"].upper())}</td></tr>'
            f'<tr><td>DIRECCION :</td><td colspan=3 style="font-size:8.2pt">{_esc(proy["direccion_obra"])}</td></tr>'
            f'<tr><td>FECHA : &nbsp;{_esc(fecha)}</td><td style="width:14%">ELEMENTO &nbsp;&nbsp;:</td>')


def _pagina_cmp(proy, fecha, ficha, kind, filas, num, det_img, obra_img) -> str:
    r1 = [(_rotulo(kind, l, t, 1), filas["plano"].get(l, "")) for l, t in ROTULOS[kind]]
    r2 = [(_rotulo(kind, l, t, 2), filas["obra"].get(l, "")) for l, t in ROTULOS[kind]]
    cuerpo = "".join(
        f"<tr><td class=l>{_esc(a)}</td><td class=v>{_esc(b)}</td><td class=l>{_esc(c)}</td><td class=v>{_esc(d)}</td></tr>"
        for (a, b), (c, d) in zip(r1, r2))
    return (f'<div class=pg>{_cabecera_comun(proy, fecha)}'
            f'<td colspan=2 style="text-align:center">{_esc(ficha["titulo"])}</td></tr></table>'
            f'<table class=bar><tr><td style="width:40%">IMAGEN DE PLANOS APROVADOS DTTL</td><td>IMAGEN EN OBRA</td></tr></table>'
            f'<div class=imgs><div style="flex:1.35"><img src="{det_img}"></div><div><img src="{obra_img}"></div></div>'
            f'<table class=cmp style="margin-top:10px"><tr><td colspan=2>1.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;INFORMACION ARMADO EN PLANOS</td>'
            f'<td colspan=2>2.&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;IMFORMACION ARMADO EN OBRA</td></tr>{cuerpo}</table>'
            f'<div class=foot><span>{_esc(proy["nombre"].upper())}</span><span>{num}</span></div></div>')


def _pagina_fot(proy, ficha, num, loc_img, det_img, fotos_img) -> str:
    return (f'<div class=pg><div class=title>{_esc(ficha["titulo"])}</div>'
            f'<div class=toprow><div><img src="{loc_img}"></div><div><img src="{det_img}"></div></div>'
            f'<div class=fotos><img src="{fotos_img}"></div>'
            f'<div class=foot><span>{_esc(proy["nombre"].upper())}</span><span>{num}</span></div></div>')


def _portada(proy, visita) -> str:
    return ('<div class=pg><div class=cover>'
            f'<div class=k style="margin-top:0.85in">Proyecto</div><div class=v>{_esc(proy["nombre"].upper())}</div>'
            f'<div class=k>Licencia No.</div><div class=v style="font-weight:bold;font-size:13pt">{_esc(proy["no_licencia"])}</div>'
            f'<div class=k>Elementos</div><div class=v style="font-weight:bold;font-size:13pt">{_esc(visita["elementos_txt"])}</div>'
            f'<div class=k>Supervisor</div><div class=v>{_esc(proy.get("supervisor") or "")}&nbsp;</div>'
            f'<div class=k>Fecha de Inspeccion</div><div class=v>{_esc(visita["fecha"])}</div></div></div>')


def _inspeccion(proy, visita, texto_obs) -> str:
    return ('<div class="pg insp" style="background:#efefef">'
            f'<table><tr><td style="width:27%">No. DE LA INSPECCION :</td><td style="width:18%">{_esc(visita.get("numero_inspeccion") or "")}</td>'
            '<td style="width:20%">NUMERO DE FORMULARIO :</td><td></td></tr>'
            f'<tr><td>FECHA DE LA INSPECCION&nbsp;:</td><td>{_esc(visita["fecha"])}</td><td>FECHA DEL INFORME :</td><td></td></tr></table><br>'
            '<table>'
            f'<tr><td style="width:27%">NOMBRE DEL PROYECTO&nbsp;:</td><td>{_esc(proy["nombre"].upper())}</td></tr>'
            f'<tr><td>NO. SOLICITUD :</td><td>{_esc(proy["no_solicitud"])}</td></tr>'
            f'<tr><td>LICENCIA :</td><td>{_esc(proy["no_licencia"])}</td></tr>'
            f'<tr><td>INICIO DE OBRA :</td><td>{_esc(proy.get("inicio_obra") or "")}</td></tr>'
            f'<tr><td>PROVINCIA :</td><td>{_esc(proy["provincia"])}</td></tr>'
            f'<tr><td>SECTOR :</td><td>{_esc(proy["sector"])}</td></tr>'
            f'<tr><td>DIRECCION :</td><td>{_esc(proy["direccion_obra"])}</td></tr>'
            f'<tr><td>NIVEL/ELEMENTOS A INSPECCIONAR:</td><td>{_esc(visita["elementos_txt"])} - {_esc(visita["clase"].upper())}</td></tr>'
            f'<tr><td>NOMBRE Y COLEGIATURA DEL RESIDENTE DE OBRA :</td><td>{_esc(proy["residente_obra"])}</td></tr>'
            f'<tr><td>SUPERVISOR :</td><td>{_esc(proy.get("supervisor") or "")}</td></tr></table>'
            '<p style="text-align:center;font-weight:bold;text-decoration:underline;font-size:8pt;margin-top:34px">OBSERVACIONES DURANTE LA INSPECCION</p>'
            f'<div style="border:1px solid #000;height:4.6in;padding:18px 14px;font-size:8pt">{_esc(texto_obs)}</div>'
            '<p style="font-weight:bold;font-size:8pt;margin-top:12px">NOMBRE Y FIRMAS DE LOS INSPECTORES:</p></div>')


def _texto_observaciones(visita: Dict, discrepancias: List[str], pendientes: int = 0) -> str:
    """
    La conformidad solo va si no hay discrepancias abiertas NI datos de OBRA pendientes (celdas vacías por
    falta de medida o de dato de la visita, o elementos excluidos). Sin texto fijo de otro proyecto.
    """
    base = f"SE VERIFICO EL ARMADO DE LOS ELEMENTOS {visita['elementos_txt']} - {visita['clase'].upper()}"
    if discrepancias:
        return base + ". DISCREPANCIAS ABIERTAS: " + " | ".join(discrepancias)
    if pendientes:
        return base + f". DATOS DE OBRA PENDIENTES DE VERIFICAR: {pendientes}."
    return base + ", ACORDE A PLANOS APROBADOS."


def _imagen_foto_obra(fotos_prep: List[Image.Image]) -> Image.Image:
    return fotos_prep[1] if len(fotos_prep) > 1 else fotos_prep[0]


def renderizar_pdf(html_doc: str) -> bytes:
    """HTML -> PDF Carta sin márgenes con Chromium (Playwright). Funciona offline una vez instalado."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            pagina = navegador.new_page()
            pagina.set_content(html_doc, wait_until="load")
            return pagina.pdf(format="Letter", print_background=True,
                              margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        finally:
            navegador.close()


def nombre_archivo(proyecto: Dict, visita: Dict) -> str:
    """§5.2: <Proyecto> - STP - <Elementos nivel> - DD-MM-AAAA.pdf"""
    elementos = re.sub(r'[<>:"/\\|?*]', " ", visita["elementos_txt"])  # solo se limpian los inválidos de Windows
    elementos = " ".join(elementos.split())
    nombre = re.sub(r'[<>:"/\\|?*]', " ", proyecto["nombre"])
    return f"{' '.join(nombre.split())} - STP - {elementos} {visita['clase']} - {visita['fecha'].replace('/', '-')}.pdf"


def generar_stp_mived(proyecto: Dict, visita: Dict, fichas: List[Dict], carpeta_salida=None,
                      usuario: Optional[str] = None) -> Dict:
    """
    Genera el STP-MIVED de una visita. Devuelve {"ok", "ruta", "errores", "dudas", "discrepancias"}.
    Si hay cualquier error o duda bloqueante no se escribe ningún PDF. Las dudas no bloqueantes (p. ej. una
    fila de OBRA sin dato) se devuelven pero el PDF se genera con la celda vacía.
    """
    resultado = {"ok": False, "ruta": None, "errores": [], "dudas": [], "discrepancias": [], "excluidos": []}
    dudas = _errores_cabecera(proyecto, visita)
    if not fichas:
        dudas.append({"id_elemento": "", "campo_afectado": "fichas",
                      "descripcion_pregunta": f"La visita no trae elementos para el STP-MIVED ({PENDIENTE})."})
    armadas = []
    tolerancia = visita.get("tolerancia_m")
    if not dudas:
        for ficha in fichas:
            id_el = ficha.get("titulo")
            if _vacio(id_el) or _vacio(ficha.get("tipo_elemento")) or _vacio(ficha.get("ejes")):
                dudas.append({"id_elemento": str(id_el or PENDIENTE), "campo_afectado": "ficha",
                              "descripcion_pregunta": f"La ficha necesita titulo, tipo_elemento y ejes ({PENDIENTE})."})
                continue
            kind = _tipo_de_fila(ficha["tipo_elemento"])
            if kind is None:
                # Este elemento se EXCLUYE (con una duda que no bloquea) y el resto del STP se genera
                dudas.append({"id_elemento": id_el, "campo_afectado": "tipo_elemento", "bloquea": False,
                              "excluido": True,
                              "descripcion_pregunta": f"El tipo '{ficha['tipo_elemento']}' no se genera en STP-MIVED "
                                                      f"({TIPOS_NO_SOPORTADOS}); el elemento queda fuera del "
                                                      f"documento: {PENDIENTE}."})
                resultado["excluidos"].append(id_el)
                continue
            filas, d, aud = _filas_de_ficha(ficha, ficha["tipo_elemento"], kind, tolerancia)
            dudas.extend(d)
            if filas is None:
                continue
            aud.update(nombre_proyecto=proyecto["nombre"], fecha=visita["fecha"], tolerancia_visita_m=tolerancia)
            errores = auditar_datos_ficha_antes_de_renderizar(aud, FORMATO)
            if errores:
                resultado["errores"].extend(f"{id_el}: {e}" for e in errores)
                continue
            if not ficha.get("fotos"):
                dudas.append({"id_elemento": id_el, "campo_afectado": "fotos",
                              "descripcion_pregunta": f"El elemento no tiene fotos del log ({PENDIENTE}).",
                              "bloquea": True})
                continue
            armadas.append((ficha, kind, filas))
            resultado["discrepancias"].extend(filas["discrepancias"])
    discrepancias = resultado["discrepancias"] + list(visita.get("discrepancias_abiertas") or [])
    resultado["dudas"] = dudas
    if resultado["errores"] or any(d.get("bloquea", True) for d in dudas):
        return resultado
    if not armadas:
        resultado["errores"].append(f"Ningún elemento de la visita se puede generar en STP-MIVED ({PENDIENTE}).")
        return resultado
    pendientes = sum(1 for d in dudas if d.get("bloquea") is False)  # celdas de OBRA vacías o elementos excluidos

    # Imágenes (M1, M3, M4 de T6) y páginas
    paginas, num = [_portada(proyecto, visita), _inspeccion(proyecto, visita, _texto_observaciones(visita, discrepancias, pendientes))], 1
    carpeta_planos = proyecto["carpeta_planos"]
    try:
        for ficha, kind, filas in armadas:
            prep = [m1_fotos.preparar_foto(p) for p in m1_fotos.seleccionar_para_stp(list(ficha["fotos"]))]
            loc = ficha["localizacion"]
            _exigir_en_planos(loc["pdf"], carpeta_planos, "LOCALIZACION")
            loc_img = m3_localizacion.generar_localizacion(loc["pdf"], loc["pagina"], tuple(loc["caja"]), *CELDA_LOC_PX)
            det = ficha["detalle"]
            det_img = m4_detalle.recortar_detalle(det["pdf"], det["pagina"], tuple(det["region"]), carpeta_planos)
            loc_b64 = _b64(_acotar(loc_img, 1000))
            det_b64 = _b64(_acotar(det_img, 1000))
            grid_b64 = _b64(m1_fotos.armar_cuadricula(prep, *ZONA_FOTOS_PX))
            paginas.append(_pagina_cmp(proyecto, visita["fecha"], ficha, kind, filas, num, det_b64,
                                       _b64(_acotar(_imagen_foto_obra(prep), 1000))))
            paginas.append(_pagina_fot(proyecto, ficha, num + 1, loc_b64, det_b64, grid_b64))
            num += 2
    except (ValueError, KeyError, OSError) as exc:
        resultado["errores"].append(f"No se pudieron preparar las imágenes: {exc}")
        return resultado

    css = RUTA_CSS.read_text(encoding="utf-8")
    documento = f"<!doctype html><html><head><meta charset=utf-8><style>{css}</style></head><body>{''.join(paginas)}</body></html>"
    pdf = renderizar_pdf(documento)
    try:
        guardado = salida.guardar_pdf(nombre_archivo(proyecto, visita), pdf, carpeta=carpeta_salida,
                                      formato=FORMATO, entidad_id=visita.get("id", ""), usuario=usuario)
    except salida.SalidaInvalida as exc:
        resultado["errores"].append(str(exc))
        return resultado
    resultado.update(ok=True, ruta=guardado["ruta"], version_nueva=guardado["version_nueva"])
    return resultado


def _exigir_en_planos(ruta, carpeta_planos, que: str):
    """Errores #1/#2: LOCALIZACION, como DETALLE, solo sale de un plano que esté en la carpeta de planos."""
    try:
        Path(ruta).resolve().relative_to(Path(carpeta_planos).resolve())
    except ValueError:
        raise ValueError(f"{que} debe salir de un plano de la carpeta de planos, no de '{Path(ruta).name}'.") from None


def _acotar(img: Image.Image, lado: int) -> Image.Image:
    copia = img.copy()
    copia.thumbnail((lado, lado), Image.LANCZOS)
    return copia
