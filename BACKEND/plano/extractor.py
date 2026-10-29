# BACKEND/plano/extractor.py
# Etapa 2 · T6n — Extractor desde el vectorial (MVP: tablas de aplicación). PLANES/etapa-2.md, T6n; informe T3n;
# CLAUDE.md Regla de Oro #1, §4.1, §4.2, §4.4.
#
# - Lee SOLO el texto de las capas visibles del vectorial VIGENTE de la obra (T4n), en solo lectura: comprueba su
#   sha256 contra la tabla `planos` antes y después de leerlo.
# - Índice de hojas y niveles por el TÍTULO IMPRESO de cada planta. E-n ↔ nivel, L# → tipo y las plantas de título
#   repetido (dos 'DE TECHO') los da el usuario (`obra_datos_usuario`); si falta uno, el campo queda pendiente y se
#   abre una DUDA_BLOQUEANTE. Nada se deduce por cercanía ni por el orden de las hojas.
# - Tablas del MVP: acero en losa (tipos A/B/C), zapata de muro de lindero, f'c por rango E-n y la variante
#   'TABLA DE LOSA ALIGERADA (E9)' de P16.
# - PROPONE filas de `elementos_diseno`: cada valor con su fuente (archivo, revisión, página, hoja y bbox), TODOS los
#   campos `pendiente_de_verificar`, todo pasa por el validador de T2. Idempotente por la clave UNIQUE de T1; nunca
#   toca un campo ya confirmado; un choque con el UNIQUE abre una duda (nunca un IntegrityError).
# - Sus dudas llevan el prefijo 'T6n:' en campo_afectado; al volver a extraer se cierran (con auditoría) las que la
#   corrida ya no genera. Las de la obra (T4n) no se tocan.
# - Comprobaciones cruzadas por tabla (verde / rojo) guardadas en `tablas_extraidas` para la confirmación por lote
#   de T7n. Fuera de alcance: pórticos, fotos y visitas.
import hashlib
import json
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymupdf
from fastapi import APIRouter, HTTPException

from database import get_connection
from importadores.validador_diseno import CONFIRMADO, EJE_SIN_LETRA, PENDIENTE_ESTADO, validar_elemento_diseno
from obras import ErrorObra, _ahora, _proyecto, _transaccion, _usuario
from plano import lector_plano as lp
from reglas_ingenieria import PENDIENTE, _normalizar_texto

router = APIRouter()

EXTRACTOR = "T6n"
DIAMETROS_BARRA = {"1/4", "3/8", "1/2", "5/8", "3/4", "7/8", "1", "1 1/8", "1 1/4", "1 3/8"}  # pulgadas
METROS_MAX = 3.0          # una dimensión de tabla de aplicación (m) fuera de (0, 3] no está en metros
FC_RANGO = (100, 700)     # kg/cm² razonables para f'c
CAMPOS_ACERO_LOSA = ["H", "Bw1", "Bw2", "h1", "h2", "DIR. X", "DIR. Y", "AS. ADIC."]
CAMPOS_ZAPATA = ["B", "h", "Df", "ACERO Ast", "ACERO Asl"]
CAMPOS_ALIGERADA = lp.COLUMNAS_LOSA_ALIGERADA[1:]
METROS = {"H", "Bw1", "Bw2", "h1", "h2", "B", "h", "Df", "Ht(m)", "HB(m)"}
BARRAS = {"DIR. X", "DIR. Y", "AS. ADIC.", "ACERO Asl", "AsxC", "AsxB", "AsyC", "AsyB"}
SEPARACION = {"ACERO Ast"}
SIN_ACERO = "-"           # en la tabla de losa aligerada de P16, '-' es un valor impreso (sin acero en esa franja)

_RE_PREFIJO_PLANTA = re.compile(r"^PLANTA\s+(?:(?:ESTRUCTURAL|EST\.?)\s+)?(?:DE\s+)?")
_RE_NUM = re.compile(r"^\d+(?:\.\d+)?$")
_RE_BARRAS = re.compile(r'^(\d{1,3})\s*[∅Ø]\s*(\d(?:\s\d)?(?:/\d)?)"$')
_RE_SEPARACION = re.compile(r'^[∅Ø]\s*(\d(?:\s\d)?(?:/\d)?)"\s*@\s*(\d+\.\d+)$')
_RE_E = re.compile(r"\bE-?(\d{1,2})\b")
_RE_RANGO_NIVEL = re.compile(r"^(.*?)(\d{1,2})\s*@\s*(\d{1,2})$")


# ---------- Utilidades puras ----------

def nivel_de_titulo(titulo: str) -> Optional[str]:
    """Nivel tal como está impreso en el título de la planta: lo que sigue a 'PLANTA ESTRUCTURAL DE'."""
    resto = _RE_PREFIJO_PLANTA.sub("", " ".join(titulo.split()), count=1).strip()
    return resto or None


def _token_e(texto: str) -> Optional[int]:
    m = re.fullmatch(r"E-?(\d{1,2})", texto.strip().upper())
    return int(m.group(1)) if m else None


def expandir_rango_e(desde: str, hasta: str, equivalencias: Dict[str, str]) -> Tuple[Optional[List[str]], str]:
    """
    'E3' @ 'E10' → [E-3 … E-10]. Un extremo que no es E-n (FUND., TECHO) solo se resuelve si el usuario dio un E-n
    con ese nivel; si no, (None, motivo): el rango no se expande adivinando dónde empieza o termina.
    """
    extremos = []
    for t in (desde, hasta):
        n = _token_e(t)
        if n is None:
            clave = _normalizar_texto(t).rstrip(".")
            iguales = [k for k, v in equivalencias.items()
                       if _normalizar_texto(v) == clave or (clave == "FUND" and _normalizar_texto(v).startswith("FUNDACION"))]
            if len(iguales) != 1:
                return None, f"el extremo '{t}' no es un entrepiso E-n y no hay una equivalencia del usuario que lo fije"
            n = _token_e(iguales[0])
        extremos.append(n)
    a, b = extremos
    if a > b:
        return None, f"el rango {desde} @ {hasta} va de mayor a menor"
    return [f"E-{i}" for i in range(a, b + 1)], ""


def expandir_nivel(nivel: str) -> List[str]:
    """'NIVEL 4@8' → ['NIVEL 4' … 'NIVEL 8']; 'ENTREPISO E3 @ E8' → […E3 … E8]; un nivel sin rango → [nivel]."""
    m = re.match(r"^(.*?)E-?(\d{1,2})\s*@\s*E-?(\d{1,2})$", nivel)
    if m and int(m.group(2)) <= int(m.group(3)):
        return [f"{m.group(1)}E{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)]
    m = _RE_RANGO_NIVEL.match(nivel)
    if m and int(m.group(2)) <= int(m.group(3)):
        return [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)]
    return [nivel]


def e_de_nivel(nivel: str, equivalencias: Dict[str, str]) -> Optional[str]:
    """E-n de un nivel: el que trae impreso ('ENTREPISO E9') o la equivalencia del usuario cuyo nivel coincide."""
    tokens = _RE_E.findall(nivel.upper())
    if len(tokens) == 1:
        return f"E-{int(tokens[0])}"
    n = _normalizar_texto(nivel)
    iguales = [k for k, v in equivalencias.items()
               if _normalizar_texto(v) == n or re.search(rf"(?<![\w@]){re.escape(_normalizar_texto(v))}(?![\w@])", n)]
    return iguales[0] if len(iguales) == 1 else None


def _valor(celda: Dict) -> Optional[str]:
    return None if celda["bbox"] is None else celda["valor"]


def _comprobacion(nombre: str, fallos: List[str]) -> Dict:
    return {"comprobacion": nombre, "ok": not fallos, "detalle": fallos}


def comprobar_celdas(filas: List[Dict], descartadas: List[Dict], avisos: List[str]) -> List[Dict]:
    """Completas, unidades y barras de una tabla leída por `_tabla_por_encabezado`."""
    vacias, unidades, barras, totales = [], [], [], []
    for f in filas:
        et = f["etiqueta"]["valor"]
        total = 0
        for col, celda in f["celdas"].items():
            v = _valor(celda)
            if v is None:
                vacias.append(f"{et} / {col}")
                continue
            if col in METROS:
                if not _RE_NUM.match(v) or not 0 < float(v) <= METROS_MAX:
                    unidades.append(f"{et} / {col} = '{v}' no es una dimensión en metros")
            elif col in BARRAS and v != SIN_ACERO:
                m = _RE_BARRAS.match(v)
                if not m or not 1 <= int(m.group(1)) <= 200 or m.group(2) not in DIAMETROS_BARRA:
                    barras.append(f"{et} / {col} = '{v}' no es 'n ∅ diámetro\"' con un diámetro de barra conocido")
                else:
                    total += int(m.group(1))
            elif col in SEPARACION:
                m = _RE_SEPARACION.match(v)
                if not m or m.group(1) not in DIAMETROS_BARRA or not 0 < float(m.group(2)) <= 1.0:
                    barras.append(f"{et} / {col} = '{v}' no es '∅ diámetro\" @ separación (m)'")
        totales.append(total)
    etiquetas = [f["etiqueta"]["valor"] for f in filas]
    repetidas = sorted({e for e in etiquetas if etiquetas.count(e) > 1})
    return [
        _comprobacion("celdas_completas", vacias + [f"'{d['texto']}' fuera de la tabla ({d['motivo']})" for d in descartadas]
                      + avisos + ([] if filas else ["la tabla no tiene filas"])),
        _comprobacion("unidades", unidades),
        _comprobacion("total_de_barras", barras),
        _comprobacion("ids_duplicados", [f"la fila '{e}' está repetida" for e in repetidas]),
    ]


def comprobar_espesor(filas: List[Dict]) -> Dict:
    """Acero en losa: H = h1 + h2 (control cruzado de la sección, sin corregir nada)."""
    fallos = []
    for f in filas:
        h, h1, h2 = (_valor(f["celdas"].get(c, {"bbox": None, "valor": None})) for c in ("H", "h1", "h2"))
        if all(x is not None and _RE_NUM.match(x) for x in (h, h1, h2)) and abs(float(h) - float(h1) - float(h2)) > 0.001:
            fallos.append(f"{f['etiqueta']['valor']}: H {h} ≠ h1 {h1} + h2 {h2}")
    return _comprobacion("espesor_total", fallos)


def comprobar_fc(tabla: Dict, equivalencias: Dict[str, str]) -> Tuple[List[Dict], Dict[str, Tuple[str, Dict]]]:
    """
    f'c por rango: valores en kg/cm² razonables, rangos expandidos sin adivinar y sin un mismo E-n con dos f'c
    distintos. Devuelve (comprobaciones, {E-n: (f'c, fila)}) con los E-n que quedan con un único valor.
    """
    unidades, rangos, choques = [], [], []
    por_e: Dict[str, List[Tuple[str, Dict]]] = {}
    for f in tabla["filas"]:
        v = _valor(f["fc_kgcm2"])
        if v is not None and not FC_RANGO[0] <= int(v) <= FC_RANGO[1]:
            unidades.append(f"{f['rango']['valor']} = {v} kg/cm² fuera de {FC_RANGO[0]}-{FC_RANGO[1]}")
        lista, motivo = expandir_rango_e(f["desde"], f["hasta"], equivalencias)
        f["expandido"] = lista
        if lista is None:
            rangos.append(f"{f['rango']['valor']}: {motivo}")
            continue
        for e in lista:
            if v is not None:
                por_e.setdefault(e, []).append((v, f))
    unicos = {}
    for e, vals in por_e.items():
        if len({v for v, _ in vals}) > 1:
            choques.append(f"{e} está en {' y '.join(f['rango']['valor'] for _, f in vals)} con f'c "
                           f"{' y '.join(v for v, _ in vals)}")
        else:
            unicos[e] = vals[0]
    vacias = [f"{f['rango']['valor']} sin f'c" for f in tabla["filas"] if _valor(f["fc_kgcm2"]) is None]
    vacias += [f"'{d['texto']}' fuera de la tabla ({d['motivo']})" for d in tabla["descartadas"]]
    return [_comprobacion("celdas_completas", vacias + ([] if tabla["filas"] else ["la tabla no tiene filas"])),
            _comprobacion("unidades", unidades), _comprobacion("rangos_expandidos", rangos),
            _comprobacion("rangos_sin_choque", choques)], unicos


# ---------- Lectura del vectorial (sin BD) ----------

def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1024 * 1024), b""):
            h.update(trozo)
    return h.hexdigest()


def indice_de_niveles(indice: List[Dict], techos: Dict[str, str]) -> Tuple[Dict[int, Dict], List[Dict]]:
    """
    {pagina: {hoja, niveles (títulos de planta), nivel}} y las dudas. `nivel` es el único nivel impreso de la hoja;
    con varias plantas en la hoja, o con el mismo título en varias hojas sin que el usuario diga cuál es cuál
    (`techo`: página → nivel), queda PENDIENTE.
    """
    por_pagina, dudas = {}, []
    for e in indice:
        niveles = []
        for t in e["titulos"]:
            n = nivel_de_titulo(t["texto"]) if t["tipo"] == "planta" else None
            if n and n not in niveles:
                niveles.append(n)
        por_pagina[e["pagina"]] = {"hoja": e["hoja"], "niveles": niveles,
                                   "nivel": niveles[0] if len(niveles) == 1 else PENDIENTE}
    repetidos: Dict[str, List[int]] = {}
    for p, d in por_pagina.items():
        if d["nivel"] != PENDIENTE:
            repetidos.setdefault(d["nivel"], []).append(p)
    for nivel, paginas in repetidos.items():
        if len(paginas) < 2:
            continue
        for p in paginas:
            dado = techos.get(str(p))
            por_pagina[p]["nivel"] = dado or PENDIENTE
            if not dado:
                dudas.append({"id_elemento": "(obra)", "campo": f"nivel_hoja:p{p}",
                              "texto": f"La planta '{nivel}' está impresa en las páginas {', '.join(map(str, paginas))} del "
                                       f"vectorial; indica qué nivel es la página {p} ({PENDIENTE})."})
    return por_pagina, dudas


def leer_vectorial(ruta: Path, datos_usuario: Dict[str, Dict[str, str]]) -> Dict:
    """
    Lee el vectorial (solo lectura) y devuelve {indice, niveles, tablas, dudas, capas_ocultas}. Cada tabla trae lo
    leído por el lector, su nivel, sus comprobaciones y sus ids en planta. No toca la BD.
    """
    equivalencias = datos_usuario.get("equivalencia_nivel", {})
    with pymupdf.Document(str(ruta)) as doc:
        # MuPDF extrae solo el contenido de las capas visibles en la configuración por defecto (/D): no se cambia.
        capas_ocultas = sum(1 for c in (doc.layer_ui_configs() or []) if not c.get("on"))
        indice = lp.indice_hojas(doc)
        niveles, dudas = indice_de_niveles(indice, datos_usuario.get("techo", {}))
        tablas = []
        for p in range(1, len(doc) + 1):
            hallazgos = [t for t in (lp.tabla_acero_losa(doc, p), lp.tabla_zapata_lindero(doc, p),
                                     lp.tabla_fc_por_rango(doc, p)) if t] + lp.tablas_losa_aligerada(doc, p)
            if not hallazgos:
                continue
            notas = [n for n in lp.notas_de_modificacion(doc, p) if n["confianza"] == "alta"]
            ids = [i for i in lp.ids_en_planta(doc, p) if i["tipo"] == "losa"]
            for t in hallazgos:
                t["pagina"], t["hoja"] = p, niveles[p]["hoja"]
                t["notas_de_modificacion"] = notas
                if t["tabla"] == "fc_por_rango":
                    t["comprobaciones"], t["fc_por_e"] = comprobar_fc(t, equivalencias)
                    t["nivel"] = niveles[p]["nivel"]
                    t["clave"] = f"p{p}:fc_por_rango"
                else:
                    t["comprobaciones"] = comprobar_celdas(t["filas"], t["descartadas"], t["avisos"])
                    if t["tabla"] == "acero_en_losa":
                        t["comprobaciones"].append(comprobar_espesor(t["filas"]))
                        t["nivel"], t["ids_losa"] = niveles[p]["nivel"], ids
                        t["clave"] = f"p{p}:acero_en_losa"
                    elif t["tabla"] == "losa_aligerada":
                        t["nivel"] = _nivel_de_aligerada(t["nivel_impreso"], niveles[p])
                        t["clave"] = f"p{p}:losa_aligerada:{t['nivel_impreso']}"
                    else:
                        t["nivel"] = niveles[p]["nivel"]
                        t["clave"] = f"p{p}:{t['tabla']}"
                t["comprobaciones"].append(_comprobacion(
                    "sin_notas_de_modificacion", [f"'{n['texto'][:120]}…'" for n in notas]))
                tablas.append(t)
    _comparar_fc_entre_hojas([t for t in tablas if t["tabla"] == "fc_por_rango"])
    _marcar_copias([t for t in tablas if t["tabla"] == "acero_en_losa"], _firma_celdas)
    return {"indice": indice, "niveles": niveles, "tablas": tablas, "dudas": dudas, "capas_ocultas": capas_ocultas}


def _nivel_de_aligerada(impreso: str, hoja: Dict) -> str:
    """'(E9)' → la planta de la hoja cuyo título lo contiene ('ENTREPISO E9'); si no hay una sola, pendiente."""
    patron = re.compile(rf"(?<![\w-]){re.escape(impreso.upper())}(?![\w-])")
    iguales = [n for n in hoja["niveles"] if patron.search(n.upper())]
    return iguales[0] if len(iguales) == 1 else PENDIENTE


def _firma_fc(t: Dict) -> List:
    return [(f["rango"]["valor"], f["fc_kgcm2"]["valor"]) for f in t["filas"]] + [d["texto"] for d in t["descartadas"]]


def _firma_celdas(t: Dict) -> List:
    return [(f["etiqueta"]["valor"], sorted((c, v["valor"]) for c, v in f["celdas"].items())) for f in t["filas"]] \
        + [d["texto"] for d in t["descartadas"]]


def _marcar_copias(tablas: List[Dict], firma):
    """Una tabla con el mismo contenido que la primera de su clase queda `copia_de` esa página: sus dudas de contenido
    se abren una sola vez (en la primera); su resultado verde / rojo se calcula igual."""
    for t in tablas[1:]:
        if firma(t) == firma(tablas[0]):
            t["copia_de"] = tablas[0]["pagina"]


def _comparar_fc_entre_hojas(tablas: List[Dict]):
    """La tabla de f'c se repite en cada planta: si una hoja dice otra cosa, esa tabla y la primera quedan en rojo."""
    if not tablas:
        return
    base = tablas[0]
    _marcar_copias(tablas, _firma_fc)
    for t in tablas[1:]:
        t["comprobaciones"].append(_comprobacion("igual_en_todas_las_hojas", [] if t.get("copia_de") else [
            f"difiere de la tabla de la página {base['pagina']}"]))
    distintas = [t["pagina"] for t in tablas[1:] if not t.get("copia_de")]
    base["comprobaciones"].append(_comprobacion("igual_en_todas_las_hojas", [
        f"la tabla de las páginas {', '.join(map(str, distintas))} dice otra cosa"] if distintas else []))


# ---------- Propuestas de elementos ----------

def _fuente_celda(t: Dict, celda: Optional[Dict], columna: str, fila: str) -> Optional[Dict]:
    if celda is None or celda["bbox"] is None:
        return None
    return {"tabla": t["clave"], "pagina": t["pagina"], "hoja": t["hoja"], "fila": fila, "columna": columna,
            "bbox": celda["bbox"]}


def _propuesta(t: Dict, id_elemento: str, tipo: str, nivel: str, ejes: str, archivo: str) -> Dict:
    return {"id_elemento": id_elemento, "tipo_elemento": tipo, "nivel_rango": nivel, "ejes": ejes,
            "hoja_plano_origen": t["hoja"], "archivo_plano_origen": archivo, "datos": {}, "tabla": t["clave"],
            "explicados": set(), "bbox_id": []}


def _poner(prop: Dict, campo: str, valor: Optional[str], fuente: Optional[Dict]):
    prop["datos"][campo] = {"valor": valor if valor is not None else PENDIENTE, "fuente": fuente}


def _fc_para(prop: Dict, nivel: str, tablas_fc: List[Dict], equivalencias: Dict[str, str], dudas: List[Dict]):
    """f'c de la losa: E-n de cada nivel que cubre (rango expandido) y la fila de f'c que lo contiene sin choque."""
    if nivel == PENDIENTE or not tablas_fc:
        _poner(prop, "fc_kgcm2", None, None)
        prop["explicados"].add("fc_kgcm2")
        return
    es = []
    for n in expandir_nivel(nivel):
        e = e_de_nivel(n, equivalencias)
        if e is None:
            dudas.append({"id_elemento": "(obra)", "campo": f"equivalencia_nivel:{n}",
                          "texto": f"Falta el entrepiso E-n del nivel '{n}' (equivalencias de la obra): sin él no se "
                                   f"puede leer el f'c por rango ({PENDIENTE})."})
        es.append(e)
    t = tablas_fc[0]
    vals = {t["fc_por_e"][e][0] for e in es if e is not None and e in t["fc_por_e"]}
    if None in es or len(vals) != 1 or any(e not in t["fc_por_e"] for e in es):
        _poner(prop, "fc_kgcm2", None, None)
        prop["explicados"].add("fc_kgcm2")
        return
    fila = t["fc_por_e"][es[0]][1]
    _poner(prop, "fc_kgcm2", vals.pop(), _fuente_celda(t, fila["fc_kgcm2"], "f'c", fila["rango"]["valor"]))
    prop["niveles_cubiertos"] = es


def proponer(lectura: Dict, datos_usuario: Dict[str, Dict[str, str]], archivo: str) -> Tuple[List[Dict], List[Dict]]:
    """(propuestas, dudas) a partir de la lectura. Ningún valor se completa por vecindad ni se deduce."""
    equivalencias = datos_usuario.get("equivalencia_nivel", {})
    tipos_losa = datos_usuario.get("losa_tipo", {})
    dudas = list(lectura["dudas"])
    props: List[Dict] = []
    fc_por_pagina: Dict[int, List[Dict]] = {}
    for t in lectura["tablas"]:
        if t["tabla"] == "fc_por_rango":
            fc_por_pagina.setdefault(t["pagina"], []).append(t)
    for t in lectura["tablas"]:
        ref = f"pág. {t['pagina']} (hoja {t['hoja']})"
        copia = t.get("copia_de")  # mismo contenido que la tabla de otra página: sus dudas de contenido ya están allí
        for d in ([] if copia else t["descartadas"]):
            dudas.append({"id_elemento": "(obra)", "campo": f"{t['clave']}:celda:{d['bbox']}",
                          "texto": f"Texto '{d['texto']}' de la tabla {t['tabla']} en {ref} no encaja en la tabla "
                                   f"({d['motivo']}); no se asigna a ninguna fila ({PENDIENTE})."})
        for n in t["notas_de_modificacion"]:
            dudas.append({"id_elemento": "(obra)", "campo": f"{t['clave']}:nota",
                          "texto": f"Nota de modificación en {ref}, donde está la tabla {t['tabla']}: "
                                   f"'{n['texto'][:300]}'. Confirma que la tabla vale para el plano vigente ({PENDIENTE})."})
        for c in t["comprobaciones"]:
            if copia and c["comprobacion"] != "igual_en_todas_las_hojas":
                continue
            if not c["ok"] and c["comprobacion"] not in ("celdas_completas", "sin_notas_de_modificacion"):
                dudas.append({"id_elemento": "(obra)", "campo": f"{t['clave']}:{c['comprobacion']}",
                              "texto": f"Comprobación '{c['comprobacion']}' de la tabla {t['tabla']} en {ref}: "
                                       f"{'; '.join(c['detalle'])} ({PENDIENTE})."})
        if t["tabla"] in ("acero_en_losa", "zapata_muro_lindero", "losa_aligerada") and not copia:
            for f in t["filas"]:
                for col in f["pendientes"]:
                    dudas.append({"id_elemento": f["etiqueta"]["valor"], "campo": f"{t['clave']}:{col}",
                                  "texto": f"La celda {col} de la fila '{f['etiqueta']['valor']}' de la tabla {t['tabla']} "
                                           f"en {ref} está vacía o no se pudo leer ({PENDIENTE})."})
        if t["tabla"] == "fc_por_rango":
            continue
        if t["nivel"] == PENDIENTE and t["tabla"] != "zapata_muro_lindero":
            dudas.append({"id_elemento": "(obra)", "campo": f"{t['clave']}:nivel",
                          "texto": f"La tabla {t['tabla']} de {ref} no tiene un único nivel impreso "
                                   f"(plantas de la hoja: {', '.join(lectura['niveles'][t['pagina']]['niveles']) or 'ninguna'}) "
                                   f"({PENDIENTE})."})
        t["propuestas"] = []
        if t["tabla"] == "zapata_muro_lindero":
            # El ID se arma con el rótulo impreso de la tabla y la fila; nivel y ejes no están en la tabla: pendientes.
            for f in t["filas"]:
                et = f["etiqueta"]["valor"]
                p = _propuesta(t, f"ZAPATA MURO LINDERO {et}", "ZAPATA DE MURO", PENDIENTE, PENDIENTE, archivo)
                for col in CAMPOS_ZAPATA:
                    celda = f["celdas"].get(col)
                    _poner(p, col, _valor(celda) if celda else None, _fuente_celda(t, celda, col, et))
                    if celda is None or celda["bbox"] is None:
                        p["explicados"].add(col)
                p["bbox_id"] = [f["etiqueta"]["bbox"]]
                t["propuestas"].append(p)
        elif t["tabla"] == "acero_en_losa":
            filas = {f["etiqueta"]["valor"]: f for f in t["filas"]}
            vistos: Dict[str, List] = {}
            for i in t["ids_losa"]:
                vistos.setdefault(i["texto"], []).append(i["bbox"])
            for lid, cajas in vistos.items():
                if len(cajas) > 1:
                    dudas.append({"id_elemento": lid, "campo": f"id_duplicado@{t['nivel']}",
                                  "texto": f"La losa {lid} aparece {len(cajas)} veces en la planta de {ref} (nivel "
                                           f"'{t['nivel']}'): ¿son la misma losa o hay un error de rotulado? ({PENDIENTE})."})
                p = _propuesta(t, lid, "LOSA", t["nivel"], EJE_SIN_LETRA, archivo)
                p["bbox_id"] = cajas
                if t["nivel"] == PENDIENTE:
                    p["explicados"].add("nivel_rango")
                tipo = tipos_losa.get(lid)
                _poner(p, "tipo_losa", tipo, {"origen": "usuario", "dato": "losa_tipo", "clave": lid} if tipo else None)
                if tipo is None:
                    p["explicados"].add("tipo_losa")
                    dudas.append({"id_elemento": lid, "campo": "losa_tipo",
                                  "texto": f"Falta el tipo (A/B/C) de la losa {lid}: la tabla de acero en losa no dice a "
                                           f"qué L# corresponde ({PENDIENTE})."})
                fila = filas.get(tipo) if tipo else None
                if tipo and fila is None:
                    dudas.append({"id_elemento": lid, "campo": f"tipo_en_tabla@{t['nivel']}",
                                  "texto": f"El tipo '{tipo}' de la losa {lid} no está en la tabla de {ref} ({PENDIENTE})."})
                for col in CAMPOS_ACERO_LOSA:
                    celda = fila["celdas"].get(col) if fila else None
                    _poner(p, col, _valor(celda) if celda else None, _fuente_celda(t, celda, col, tipo or ""))
                    if celda is None or celda["bbox"] is None:
                        p["explicados"].add(col)
                _fc_para(p, t["nivel"], fc_por_pagina.get(t["pagina"], []), equivalencias, dudas)
                t["propuestas"].append(p)
            t["comprobaciones"] += [
                _comprobacion("nivel_impreso", [] if t["nivel"] != PENDIENTE else ["la hoja no tiene un único nivel impreso"]),
                _comprobacion("ids_en_planta_sin_duplicados",
                              [f"{lid} × {len(c)}" for lid, c in vistos.items() if len(c) > 1]),
                _comprobacion("losa_tipo_asignado", [lid for lid in vistos if lid not in tipos_losa]),
            ]
        elif t["tabla"] == "losa_aligerada":
            for f in t["filas"]:
                lid = f["etiqueta"]["valor"]
                if not re.fullmatch(r"L\d{1,3}", lid):
                    dudas.append({"id_elemento": lid, "campo": f"{t['clave']}:id",
                                  "texto": f"La fila '{lid}' de la tabla de losa aligerada de {ref} no es un ID de losa "
                                           f"(L#) ({PENDIENTE})."})
                    continue
                p = _propuesta(t, lid, "LOSA ALIGERADA", t["nivel"], EJE_SIN_LETRA, archivo)
                p["bbox_id"] = [f["etiqueta"]["bbox"]]
                if t["nivel"] == PENDIENTE:
                    p["explicados"].add("nivel_rango")
                for col in CAMPOS_ALIGERADA:
                    celda = f["celdas"].get(col)
                    _poner(p, col, _valor(celda) if celda else None, _fuente_celda(t, celda, col, lid))
                    if celda is None or celda["bbox"] is None:
                        p["explicados"].add(col)
                _fc_para(p, t["nivel"], fc_por_pagina.get(t["pagina"], []), equivalencias, dudas)
                t["propuestas"].append(p)
            t["comprobaciones"].append(_comprobacion(
                "nivel_impreso", [] if t["nivel"] != PENDIENTE else [f"'({t['nivel_impreso']})' no es una única planta de la hoja"]))
        props.extend(t["propuestas"])
    return props, dudas


def _validar(prop: Dict) -> Dict:
    """Pasa la propuesta por el validador de T2 y deja TODOS los campos pendientes de verificar."""
    r = validar_elemento_diseno({
        "id_elemento": prop["id_elemento"], "tipo_elemento": prop["tipo_elemento"], "nivel_rango": prop["nivel_rango"],
        "ejes": prop["ejes"], "hoja_plano_origen": prop["hoja_plano_origen"],
        "archivo_plano_origen": prop["archivo_plano_origen"],
        "datos_diseno": {c: d["valor"] for c, d in prop["datos"].items()}})
    estado = {c: PENDIENTE_ESTADO for c in r["estado_campos"]}  # T6n: nada queda confirmado sin el usuario (T7n)
    dudas = [d for d in r["dudas"] if d["campo_afectado"].removeprefix("datos_diseno.") not in prop["explicados"]
             and d["campo_afectado"] not in prop["explicados"]]
    return {"norm": r["elemento_normalizado"], "estado": estado, "dudas": dudas}


# ---------- Escritura en la BD ----------

ORIGEN_DUDA = f"{EXTRACTOR}:"  # prefijo de campo_afectado: distingue las dudas del extractor de las de la obra (T4n)


def _abrir_duda(conn, proyecto_id: str, id_elemento: str, campo: str, texto: str) -> bool:
    campo = ORIGEN_DUDA + campo
    ya = conn.execute("""SELECT 1 FROM dudas_y_hallazgos WHERE proyecto_id = ? AND visita_id IS NULL AND id_elemento = ?
                         AND campo_afectado = ? AND resuelta = 0""", (proyecto_id, id_elemento, campo)).fetchone()
    if ya:
        return False
    conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria, campo_afectado,
                    descripcion_pregunta, creado) VALUES (?, NULL, ?, 'DUDA_BLOQUEANTE', ?, ?, ?)""",
                 (proyecto_id, id_elemento, campo, texto, _ahora()))
    return True


def _cerrar_dudas_viejas(conn, proyecto_id: str, vigentes: set, usuario: str, ahora: str) -> List[int]:
    """Cierra las dudas del extractor abiertas en la obra que esta corrida ya no genera (el dato llegó o la causa
    desapareció). Las dudas de otro origen (p. ej. las de la obra de T4n) no se tocan."""
    cerradas = [r["id"] for r in conn.execute(
        """SELECT id, id_elemento, campo_afectado FROM dudas_y_hallazgos WHERE proyecto_id = ? AND visita_id IS NULL
           AND resuelta = 0 AND substr(campo_afectado, 1, ?) = ?""", (proyecto_id, len(ORIGEN_DUDA), ORIGEN_DUDA))
        if (r["id_elemento"], r["campo_afectado"]) not in vigentes]
    for i in cerradas:
        conn.execute("UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = ?, resuelto_en = ? WHERE id = ?",
                     (f"Resuelta por re-extracción ({usuario})", ahora, i))
    if cerradas:
        conn.execute("INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json) "
                     "VALUES (?, ?, 'EXTRACTOR', 'CERRAR_DUDAS_REEXTRACCION', ?, ?)",
                     (ahora, usuario, proyecto_id, json.dumps({"dudas_cerradas": cerradas})))
    return cerradas


def _datos_usuario(conn, proyecto_id: str) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for r in conn.execute("SELECT tipo, clave, valor FROM obra_datos_usuario WHERE proyecto_id = ? AND estado = 'confirmado'",
                          (proyecto_id,)):
        out.setdefault(r["tipo"], {})[r["clave"]] = r["valor"]
    return out


def _escribir_elemento(conn, proyecto_id: str, plano: Dict, prop: Dict, v: Dict, ahora: str) -> Tuple[str, Optional[str]]:
    """
    Inserta o actualiza una propuesta. Devuelve (resultado, uid): 'nuevo', 'actualizado', 'sin_cambios' o 'choque'.
    Un campo `confirmado` de la fila existente nunca se toca.
    """
    norm = v["norm"]
    clave = (proyecto_id, norm["id_elemento"], norm["nivel_rango"], norm["ejes"])
    datos = norm["datos_diseno_json"]
    fuente = {"extractor": EXTRACTOR, "plano_id": plano["id"], "archivo": plano["vectorial_archivo"],
              "revision": plano["revision"], "etiqueta_revision": plano["etiqueta_revision"],
              "sha256": plano["vectorial_sha256"], "tabla": prop["tabla"], "bbox_id": prop["bbox_id"],
              "valores": {c: d["fuente"] for c, d in prop["datos"].items()}}
    if prop.get("niveles_cubiertos"):
        fuente["niveles_cubiertos"] = prop["niveles_cubiertos"]
    previo = conn.execute("""SELECT * FROM elementos_diseno WHERE proyecto_id = ? AND id_elemento = ? AND nivel_rango = ?
                             AND ejes = ?""", clave).fetchone()
    if previo is None:
        uid = f"ed-{uuid.uuid4().hex[:12]}"
        try:
            conn.execute("""INSERT INTO elementos_diseno (uid, proyecto_id, id_elemento, nivel_rango, ejes, tipo_elemento,
                            hoja_plano_origen, archivo_plano_origen, datos_diseno_json, estado_campos_json, actualizado,
                            fuente_json, pendientes_json, plano_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (uid, *clave, norm["tipo_elemento"], norm["hoja_plano_origen"], norm["archivo_plano_origen"],
                          json.dumps(datos, ensure_ascii=False), json.dumps(v["estado"], ensure_ascii=False), ahora,
                          json.dumps(fuente, ensure_ascii=False), json.dumps(sorted(v["estado"]), ensure_ascii=False),
                          plano["id"]))
        except sqlite3.IntegrityError:
            return "choque", None
        return "nuevo", uid
    fuente_previa = json.loads(previo["fuente_json"] or "{}")
    if fuente_previa.get("extractor") != EXTRACTOR or fuente_previa.get("plano_id") != plano["id"] \
            or fuente_previa.get("tabla") != prop["tabla"]:
        return "choque", previo["uid"]
    estado_prev = json.loads(previo["estado_campos_json"] or "{}")
    datos_prev = json.loads(previo["datos_diseno_json"] or "{}")
    nuevos_datos, nuevo_estado, valores_fuente = dict(datos_prev), dict(estado_prev), dict(fuente_previa.get("valores", {}))
    for c, val in datos.items():
        k = f"datos_diseno.{c}"
        if estado_prev.get(k) == CONFIRMADO:
            continue
        nuevos_datos[c], nuevo_estado[k] = val, PENDIENTE_ESTADO
        valores_fuente[c] = fuente["valores"].get(c)
    columnas = {"tipo_elemento": norm["tipo_elemento"], "hoja_plano_origen": norm["hoja_plano_origen"],
                "archivo_plano_origen": norm["archivo_plano_origen"]}
    cambios = {c: val for c, val in columnas.items() if estado_prev.get(c) != CONFIRMADO and previo[c] != val}
    for c in v["estado"]:
        if not c.startswith("datos_diseno.") and estado_prev.get(c) != CONFIRMADO:
            nuevo_estado[c] = PENDIENTE_ESTADO
    fuente_nueva = {**fuente, "valores": valores_fuente}
    if not cambios and nuevos_datos == datos_prev and nuevo_estado == estado_prev and fuente_nueva == fuente_previa:
        return "sin_cambios", previo["uid"]
    sets = ", ".join(f"{c} = ?" for c in cambios)
    conn.execute(f"""UPDATE elementos_diseno SET {sets + ', ' if sets else ''}datos_diseno_json = ?, estado_campos_json = ?,
                     fuente_json = ?, pendientes_json = ?, actualizado = ? WHERE uid = ?""",
                 (*cambios.values(), json.dumps(nuevos_datos, ensure_ascii=False),
                  json.dumps(nuevo_estado, ensure_ascii=False), json.dumps(fuente_nueva, ensure_ascii=False),
                  json.dumps(sorted(c for c, e in nuevo_estado.items() if e != CONFIRMADO), ensure_ascii=False),
                  ahora, previo["uid"]))
    return "actualizado", previo["uid"]


def _resultado(t: Dict) -> str:
    return "verde" if all(c["ok"] for c in t["comprobaciones"]) else "rojo"


def _filas_para_guardar(t: Dict) -> List[Dict]:
    if t["tabla"] == "fc_por_rango":
        return [{"rango": f["rango"], "desde": f["desde"], "hasta": f["hasta"], "fc_kgcm2": f["fc_kgcm2"],
                 "expandido": f.get("expandido")} for f in t["filas"]]
    return [{"etiqueta": f["etiqueta"], "celdas": f["celdas"], "pendientes": f["pendientes"]} for f in t["filas"]]


def extraer_diseno(proyecto_id: str, usuario: Optional[str] = None) -> Dict:
    """Extrae del vectorial vigente las tablas del MVP y propone sus elementos (todo pendiente). Devuelve el resumen."""
    usuario = usuario or _usuario()
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
        plano = conn.execute("SELECT * FROM planos WHERE proyecto_id = ? AND estado = 'vigente'", (proyecto_id,)).fetchone()
        if plano is None:
            raise ErrorObra("La obra no tiene un plano vigente: sube primero el vectorial y el sellado.", 409)
        plano = dict(plano)
        datos_usuario = _datos_usuario(conn, proyecto_id)
    finally:
        conn.close()
    ruta = Path(plano["vectorial_ruta"])
    if not ruta.is_file():
        raise ErrorObra(f"No se encuentra el vectorial '{ruta.name}' en la carpeta de datos de la obra.", 409)
    sha_antes = _sha256(ruta)
    if sha_antes != plano["vectorial_sha256"]:
        raise ErrorObra(f"El vectorial '{ruta.name}' no coincide con el sha256 con que se subió: no se lee.", 409)
    lectura = leer_vectorial(ruta, datos_usuario)
    props, dudas = proponer(lectura, datos_usuario, plano["vectorial_archivo"])
    validados = [(p, _validar(p)) for p in props]
    sha_despues = _sha256(ruta)
    if sha_despues != sha_antes:
        raise ErrorObra(f"El vectorial '{ruta.name}' cambió durante la lectura: no se guarda nada.", 409)

    cuenta = {"nuevo": 0, "actualizado": 0, "sin_cambios": 0, "choque": 0}
    campos_propuestos = campos_vacios = dudas_creadas = 0
    ahora = _ahora()
    conn = get_connection()
    try:
        _transaccion(conn)
        try:
            claves_en_corrida = {}
            for p, v in validados:
                norm = v["norm"]
                clave = (norm["id_elemento"], norm["nivel_rango"], norm["ejes"])
                if clave in claves_en_corrida:
                    cuenta["choque"] += 1
                    dudas.append({"id_elemento": norm["id_elemento"], "campo": f"clave_unica@{norm['nivel_rango']}",
                                  "texto": f"Dos propuestas con la misma clave (ID {clave[0]}, nivel '{clave[1]}', ejes "
                                           f"'{clave[2]}'): tablas {claves_en_corrida[clave]} y {p['tabla']}. No se "
                                           f"fusionan ({PENDIENTE})."})
                    continue
                claves_en_corrida[clave] = p["tabla"]
                res, uid = _escribir_elemento(conn, proyecto_id, plano, p, v, ahora)
                cuenta[res] += 1
                if res == "choque":
                    dudas.append({"id_elemento": norm["id_elemento"], "campo": f"clave_unica@{norm['nivel_rango']}",
                                  "texto": f"Ya existe un elemento {clave[0]} (nivel '{clave[1]}', ejes '{clave[2]}', uid "
                                           f"{uid or '?'}) que no viene de esta tabla del plano vigente; no se toca "
                                           f"({PENDIENTE})."})
                    continue
                p["uid"] = uid
                for d in v["dudas"]:
                    dudas.append({"id_elemento": norm["id_elemento"], "campo": f"{d['campo_afectado']}@{norm['nivel_rango']}",
                                  "texto": d["descripcion_pregunta"]})
                obligatorios = [norm[c] for c in ("id_elemento", "tipo_elemento", "nivel_rango", "ejes",
                                                  "hoja_plano_origen", "archivo_plano_origen")]
                valores = obligatorios + list(norm["datos_diseno_json"].values())
                campos_propuestos += len(valores)
                campos_vacios += sum(1 for x in valores if x == PENDIENTE)
            for t in lectura["tablas"]:
                uids = [p["uid"] for p in t.get("propuestas", []) if p.get("uid")]
                conn.execute("""
                    INSERT INTO tablas_extraidas (proyecto_id, plano_id, clave, tabla, pagina, hoja, nivel_rango, resultado,
                        comprobaciones_json, filas_json, elementos_json, fuente_json, extraido_por, extraido_en)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(plano_id, clave) DO UPDATE SET resultado = excluded.resultado, nivel_rango = excluded.nivel_rango,
                        comprobaciones_json = excluded.comprobaciones_json, filas_json = excluded.filas_json,
                        elementos_json = excluded.elementos_json, fuente_json = excluded.fuente_json,
                        extraido_por = excluded.extraido_por, extraido_en = excluded.extraido_en
                """, (proyecto_id, plano["id"], t["clave"], t["tabla"], t["pagina"], t["hoja"], t["nivel"], _resultado(t),
                      json.dumps(t["comprobaciones"], ensure_ascii=False), json.dumps(_filas_para_guardar(t), ensure_ascii=False),
                      json.dumps(uids), json.dumps({**t["fuente"], "revision": plano["revision"], "sha256": sha_antes},
                                                   ensure_ascii=False), usuario, ahora))
            for d in dudas:
                dudas_creadas += _abrir_duda(conn, proyecto_id, d["id_elemento"], d["campo"], d["texto"])
            cerradas = _cerrar_dudas_viejas(conn, proyecto_id, {(d["id_elemento"], ORIGEN_DUDA + d["campo"]) for d in dudas},
                                            usuario, ahora)
            resumen = {
                "plano_id": plano["id"], "archivo": plano["vectorial_archivo"], "revision": plano["revision"],
                "sha256": sha_antes, "sha256_sin_cambios": sha_despues == sha_antes, "paginas": len(lectura["indice"]),
                "capas_ocultas": lectura["capas_ocultas"],
                "tablas": [{"clave": t["clave"], "tabla": t["tabla"], "pagina": t["pagina"], "hoja": t["hoja"],
                            "nivel_rango": t["nivel"], "resultado": _resultado(t),
                            "fallos": [c["comprobacion"] for c in t["comprobaciones"] if not c["ok"]]}
                           for t in lectura["tablas"]],
                "elementos": {"propuestos": len(validados), **cuenta},
                "campos": {"propuestos": campos_propuestos, "vacios": campos_vacios},
                "dudas_creadas": dudas_creadas, "dudas_cerradas": len(cerradas),
            }
            conn.execute("INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json) "
                         "VALUES (?, ?, 'EXTRACTOR', 'EXTRAER_DISENO', ?, ?)",
                         (ahora, usuario, proyecto_id, json.dumps({k: v for k, v in resumen.items() if k != "tablas"},
                                                                  ensure_ascii=False)))
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return resumen


def listar_tablas(proyecto_id: str) -> List[Dict]:
    """Tablas extraídas del plano vigente, con su resultado (verde / rojo) y comprobaciones, para T7n."""
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
        filas = conn.execute("""SELECT t.* FROM tablas_extraidas t JOIN planos p ON p.id = t.plano_id
                                WHERE t.proyecto_id = ? AND p.estado = 'vigente' ORDER BY t.pagina, t.clave""",
                             (proyecto_id,)).fetchall()
    finally:
        conn.close()
    out = []
    for f in filas:
        d = dict(f)
        for c in ("comprobaciones_json", "filas_json", "elementos_json", "fuente_json"):
            d[c.removesuffix("_json")] = json.loads(d.pop(c))
        out.append(d)
    return out


# ---------- API ----------

@router.post("/api/proyectos/{proyecto_id}/extraer-diseno")
def api_extraer_diseno(proyecto_id: str):
    try:
        return extraer_diseno(proyecto_id)
    except ErrorObra as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))


@router.get("/api/proyectos/{proyecto_id}/tablas-extraidas")
def api_tablas_extraidas(proyecto_id: str):
    try:
        return {"tablas": listar_tablas(proyecto_id)}
    except ErrorObra as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))
