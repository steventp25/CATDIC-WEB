# BACKEND/plano/confirmacion.py
# Etapa 2 · T7n — Confirmación de los datos extraídos del plano (PLANES/etapa-2.md, T7n; CLAUDE.md Regla de Oro #1).
#
# Dos caminos, y ninguno deja un campo `confirmado` sin una acción explícita del usuario:
# - POR LOTE: el usuario confirma de una vez los campos de `elementos_diseno` que vienen de las celdas de UNA tabla
#   extraída (T6n), viendo el recorte del plano al lado. Solo con la tabla en verde y de la extracción vigente (mismo
#   plano, revisión y sha256, la última corrida y sin datos de la obra cambiados después); si no, 409. Atómico: o se
#   confirma todo el lote o nada. Un campo ya confirmado con otro valor no se toca: abre una duda (T7n:).
# - UNO POR UNO, por la Mesa de Dudas: la respuesta a una duda T6n: que apunta a un único campo de un elemento se valida
#   y queda confirmada (la fuente es el usuario).
# Auditoría por campo: usuario, lote, elemento, campo, valor y fuente (archivo, revisión, página, hoja y bbox).
# Lo que no viene de una celda de la tabla (ID, nivel, ejes, el L#→tipo dado en "Datos de la obra") no se confirma aquí.
import json
import re
import uuid
from typing import Dict, List, Optional, Tuple

import pymupdf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_connection
from importadores.validador_diseno import CONFIRMADO
from obras import ErrorObra, _ahora, _proyecto, _transaccion, _usuario
from plano import extractor as ex
from reglas_ingenieria import PENDIENTE

router = APIRouter()

MODULO = "CONFIRMACION"
ORIGEN_DUDA = "T7n:"           # dudas que abre la confirmación (un campo ya confirmado con otro valor)
MARGEN_RECORTE_PT = 12.0       # aire alrededor de la tabla en el recorte
MARGEN_SUPERIOR_PT = 45.0      # arriba, más: los rótulos de columna y el título quedan sobre la primera fila
COLUMNA_FC = "f'c"             # columna de la fuente del f'c (ver extractor._fc_para)


class ValorInvalido(ValueError):
    """La respuesta de la Mesa no es un valor válido para el campo; no se cambió nada."""


# ---------- Utilidades ----------

def _json(valor) -> str:
    return json.dumps(valor, ensure_ascii=False)


def _cargar(texto, defecto):
    try:
        return json.loads(texto) if texto else defecto
    except (TypeError, ValueError):
        return defecto


def _plano_vigente(conn, proyecto_id: str):
    return conn.execute("SELECT * FROM planos WHERE proyecto_id = ? AND estado = 'vigente'", (proyecto_id,)).fetchone()


def _tabla(conn, proyecto_id: str, tabla_id: int):
    fila = conn.execute("SELECT * FROM tablas_extraidas WHERE id = ? AND proyecto_id = ?", (tabla_id, proyecto_id)).fetchone()
    if fila is None:
        raise ErrorObra("Esa tabla extraída no existe en esta obra.", 404)
    return fila


def _celda_en_tabla(filas: List[Dict], fuente: Dict) -> Optional[Dict]:
    """La celda de `filas_json` que la fuente del valor cita (fila + columna), o None si no está."""
    for f in filas:
        if fuente.get("columna") == COLUMNA_FC and "fc_kgcm2" in f:
            if f["rango"]["valor"] == fuente.get("fila"):
                return f["fc_kgcm2"]
        elif "etiqueta" in f and f["etiqueta"]["valor"] == fuente.get("fila"):
            return f["celdas"].get(fuente.get("columna"))
    return None


def _elementos_del_plano(conn, proyecto_id: str, plano_id: int) -> List:
    return conn.execute("SELECT * FROM elementos_diseno WHERE proyecto_id = ? AND plano_id = ? ORDER BY id_elemento, nivel_rango",
                        (proyecto_id, plano_id)).fetchall()


def campos_de_tabla(conn, t) -> List[Dict]:
    """Campos de `elementos_diseno` cuyo valor viene de una celda de esta tabla (fuente.valores[c].tabla == clave)."""
    filas = _cargar(t["filas_json"], [])
    out = []
    for e in _elementos_del_plano(conn, t["proyecto_id"], t["plano_id"]):
        fuente = _cargar(e["fuente_json"], {})
        if fuente.get("extractor") != ex.EXTRACTOR:
            continue
        datos, estado = _cargar(e["datos_diseno_json"], {}), _cargar(e["estado_campos_json"], {})
        for campo, f in (fuente.get("valores") or {}).items():
            if not isinstance(f, dict) or f.get("tabla") != t["clave"]:
                continue
            celda = _celda_en_tabla(filas, f)
            out.append({"uid": e["uid"], "id_elemento": e["id_elemento"], "nivel_rango": e["nivel_rango"],
                        "ejes": e["ejes"], "campo": campo, "valor": datos.get(campo, PENDIENTE),
                        "estado": estado.get(f"datos_diseno.{campo}", ""),
                        "valor_tabla": celda["valor"] if celda and celda.get("bbox") else None,
                        "fuente": {"archivo": fuente.get("archivo"), "revision": fuente.get("revision"),
                                   "sha256": fuente.get("sha256"), "pagina": f.get("pagina"), "hoja": f.get("hoja"),
                                   "fila": f.get("fila"), "columna": f.get("columna"), "bbox": f.get("bbox")}})
    return out


def _bbox_tabla(filas: List[Dict]) -> Optional[List[float]]:
    cajas = []
    for f in filas:
        for celda in [f.get("etiqueta"), f.get("rango"), f.get("fc_kgcm2"), *(f.get("celdas") or {}).values()]:
            if celda and celda.get("bbox"):
                cajas.append(celda["bbox"])
    if not cajas:
        return None
    return [min(c[0] for c in cajas), min(c[1] for c in cajas), max(c[2] for c in cajas), max(c[3] for c in cajas)]


def _recorte(plano, pagina: int, caja: Optional[List[float]]) -> Optional[List[float]]:
    """Rect del recorte (pt, marco visual de la hoja) alrededor de la tabla, dentro de la hoja."""
    if caja is None or plano is None:
        return None
    try:
        with pymupdf.Document(plano["vectorial_ruta"]) as doc:
            hoja = doc[pagina - 1].rect
    except Exception:
        return None
    m = MARGEN_RECORTE_PT
    return [round(max(hoja.x0, caja[0] - m), 2), round(max(hoja.y0, caja[1] - MARGEN_SUPERIOR_PT), 2),
            round(min(hoja.x1, caja[2] + m), 2), round(min(hoja.y1, caja[3] + m), 2)]


# ---------- Lectura ----------

def _tabla_dict(t) -> Dict:
    d = dict(t)
    for c in ("comprobaciones_json", "filas_json", "elementos_json", "fuente_json"):
        d[c.removesuffix("_json")] = _cargar(d.pop(c), [] if c != "fuente_json" else {})
    return d


def detalle_tabla(proyecto_id: str, tabla_id: int) -> Dict:
    """La tabla, sus campos propuestos (con su valor en la tabla) y el recorte del plano donde está."""
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
        t = _tabla(conn, proyecto_id, tabla_id)
        plano = _plano_vigente(conn, proyecto_id)
        d = _tabla_dict(t)
        d["motivos_no_vigente"] = ex.vigencia_tabla(conn, t, plano)
        d["vigente"] = not d["motivos_no_vigente"]
        d["campos"] = campos_de_tabla(conn, t)
    finally:
        conn.close()
    d["recorte"] = _recorte(plano, t["pagina"], _bbox_tabla(d["filas"]))
    d["confirmable"], d["motivos_no_confirmable"] = _confirmable(d)
    return d


def _confirmable(d: Dict) -> Tuple[bool, List[str]]:
    motivos = list(d["motivos_no_vigente"])
    if d["resultado"] != "verde":
        motivos.append("la tabla está en rojo: " + ", ".join(c["comprobacion"] for c in d["comprobaciones"] if not c["ok"]))
    if not any(c["estado"] != CONFIRMADO for c in d["campos"]):
        motivos.append("no hay campos pendientes que vengan de esta tabla")
    return not motivos, motivos


# ---------- Confirmación por lote ----------

def confirmar_tabla(proyecto_id: str, tabla_id: int, extraido_en: Optional[str] = None,
                    usuario: Optional[str] = None) -> Dict:
    """
    Confirma, en una sola transacción, los campos que vienen de las celdas de la tabla. 409 si la tabla no está en
    verde, no es de la extracción vigente, o lo guardado ya no coincide con lo que se leyó de la tabla.
    """
    usuario = usuario or _usuario()
    conn = get_connection()
    try:
        _proyecto(conn, proyecto_id)
        _transaccion(conn)
        try:
            resumen = _confirmar(conn, proyecto_id, tabla_id, extraido_en, usuario)
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return resumen


def _confirmar(conn, proyecto_id: str, tabla_id: int, extraido_en: Optional[str], usuario: str) -> Dict:
    t = _tabla(conn, proyecto_id, tabla_id)
    plano = _plano_vigente(conn, proyecto_id)
    motivos = ex.vigencia_tabla(conn, t, plano)
    if motivos:
        raise ErrorObra("No se confirma: " + "; ".join(motivos) + ".", 409)
    if t["resultado"] != "verde":
        raise ErrorObra("No se confirma: la tabla está en rojo. Resuelve sus dudas una por una en la Mesa de Dudas.", 409)
    if extraido_en is not None and extraido_en != t["extraido_en"]:
        raise ErrorObra("No se confirma: la tabla se volvió a extraer mientras la revisabas. Ábrela de nuevo.", 409)
    campos = campos_de_tabla(conn, t)
    lote, ahora = f"lote-{uuid.uuid4().hex[:12]}", _ahora()
    por_uid: Dict[str, List[Dict]] = {}
    confirmados, ya, conflictos = [], [], []
    for c in campos:
        if c["valor_tabla"] is None or c["valor"] == PENDIENTE:
            raise ErrorObra(f"No se confirma: {c['id_elemento']} / {c['campo']} no tiene un valor leído de la tabla.", 409)
        if c["estado"] == CONFIRMADO:
            (ya if c["valor"] == c["valor_tabla"] else conflictos).append(c)
            continue
        if c["valor"] != c["valor_tabla"]:
            raise ErrorObra(f"No se confirma: {c['id_elemento']} / {c['campo']} = '{c['valor']}' ya no coincide con la "
                            f"tabla ('{c['valor_tabla']}'). Vuelve a extraer.", 409)
        por_uid.setdefault(c["uid"], []).append(c)
    if not por_uid and not conflictos:
        raise ErrorObra("No hay campos pendientes que vengan de esta tabla.", 409)

    for uid, lista in por_uid.items():
        e = conn.execute("SELECT * FROM elementos_diseno WHERE uid = ?", (uid,)).fetchone()
        estado, fuente = _cargar(e["estado_campos_json"], {}), _cargar(e["fuente_json"], {})
        for c in lista:
            estado[f"datos_diseno.{c['campo']}"] = CONFIRMADO
            fuente["valores"][c["campo"]]["confirmado"] = {"lote": lote, "por": usuario, "en": ahora}
            _auditar_campo(conn, usuario, ahora, uid, {"lote": lote, "tabla_id": tabla_id, "tabla": t["clave"],
                                                         "id_elemento": c["id_elemento"], "nivel_rango": c["nivel_rango"],
                                                         "ejes": c["ejes"], "campo": c["campo"], "valor": c["valor"],
                                                         "fuente": c["fuente"]})
            confirmados.append(c)
        conn.execute("""UPDATE elementos_diseno SET estado_campos_json = ?, pendientes_json = ?, fuente_json = ?,
                        actualizado = ? WHERE uid = ?""",
                     (_json(estado), _json(sorted(k for k, v in estado.items() if v != CONFIRMADO)), _json(fuente),
                      ahora, uid))

    abiertas = []
    for c in conflictos:
        campo = f"{ORIGEN_DUDA}{t['clave']}:{c['campo']}@{c['nivel_rango']}"
        ya_abierta = conn.execute("""SELECT 1 FROM dudas_y_hallazgos WHERE proyecto_id = ? AND visita_id IS NULL
                                     AND id_elemento = ? AND campo_afectado = ? AND resuelta = 0""",
                                  (proyecto_id, c["id_elemento"], campo)).fetchone()
        if not ya_abierta:
            conn.execute("""INSERT INTO dudas_y_hallazgos (proyecto_id, visita_id, id_elemento, categoria, campo_afectado,
                            descripcion_pregunta, creado) VALUES (?, NULL, ?, 'DUDA_BLOQUEANTE', ?, ?, ?)""",
                         (proyecto_id, c["id_elemento"], campo,
                          f"{c['campo']} de {c['id_elemento']} ({c['nivel_rango']}) ya está confirmado como '{c['valor']}', "
                          f"pero la tabla {t['clave']} (pág. {t['pagina']}, hoja {t['hoja']}) dice '{c['valor_tabla']}'. "
                          f"No se sobrescribe: indica cuál vale ({PENDIENTE}).", ahora))
            abiertas.append(c["id_elemento"] + " / " + c["campo"])
    cerradas = _cerrar_dudas_sin_causa(conn, proyecto_id, confirmados, t["clave"], usuario, ahora, lote)
    resumen = {"lote": lote, "tabla_id": tabla_id, "tabla": t["clave"], "confirmados": len(confirmados),
               "elementos": len(por_uid), "ya_confirmados": len(ya), "conflictos": len(conflictos),
               "dudas_abiertas": abiertas, "dudas_cerradas": cerradas}
    conn.execute("INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json) "
                 "VALUES (?, ?, ?, 'CONFIRMAR_LOTE', ?, ?)", (ahora, usuario, MODULO, proyecto_id, _json(resumen)))
    return resumen


def _auditar_campo(conn, usuario: str, ahora: str, uid: str, detalle: Dict):
    conn.execute("INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json) "
                 "VALUES (?, ?, ?, 'CONFIRMAR_CAMPO', ?, ?)", (ahora, usuario, MODULO, uid, _json(detalle)))


def _cerrar_dudas_sin_causa(conn, proyecto_id: str, confirmados: List[Dict], clave: str, usuario: str, ahora: str,
                            lote: Optional[str]) -> List[int]:
    """Cierra (con auditoría) las dudas T6n: abiertas de los campos que acaban de quedar confirmados con un valor: la
    del validador ('datos_diseno.<campo>@<nivel>', id = el elemento) y la de celda vacía ('<tabla>:<campo>', id = la
    etiqueta de la fila). Con el valor leído de la celda, ninguna de las dos tiene ya causa."""
    cerradas = []
    for c in confirmados:
        for id_duda, campo in ((c["id_elemento"], f"{ex.ORIGEN_DUDA}datos_diseno.{c['campo']}@{c['nivel_rango']}"),
                               (c["fuente"].get("fila") or "", f"{ex.ORIGEN_DUDA}{clave}:{c['campo']}")):
            for r in conn.execute("""SELECT id FROM dudas_y_hallazgos WHERE proyecto_id = ? AND visita_id IS NULL
                                     AND resuelta = 0 AND id_elemento = ? AND campo_afectado = ?""",
                                  (proyecto_id, id_duda, campo)).fetchall():
                conn.execute("UPDATE dudas_y_hallazgos SET resuelta = 1, respuesta_usuario = ?, resuelto_en = ? WHERE id = ?",
                             (f"Campo confirmado ({lote or 'Mesa de Dudas'}, {usuario})", ahora, r["id"]))
                cerradas.append(r["id"])
    if cerradas:
        conn.execute("INSERT INTO auditoria (fecha_hora, usuario, modulo, accion, entidad_id, detalle_json) "
                     "VALUES (?, ?, ?, 'CERRAR_DUDAS_CONFIRMACION', ?, ?)",
                     (ahora, usuario, MODULO, proyecto_id, _json({"lote": lote, "dudas_cerradas": cerradas})))
    return cerradas


# ---------- Uno por uno, desde la Mesa de Dudas ----------

def validar_valor(campo: str, valor: str) -> str:
    """El valor que escribe el usuario, con las mismas reglas de formato que las comprobaciones de la tabla (T6n)."""
    v = " ".join(str(valor or "").split())
    if not v or v.lower() == PENDIENTE:
        raise ValorInvalido("El valor no puede quedar vacío ni 'pendiente de verificar'.")
    if campo in ex.METROS:
        if not ex._RE_NUM.match(v) or not 0 < float(v) <= ex.METROS_MAX:
            raise ValorInvalido(f"{campo} es una dimensión en metros (p. ej. 0.25), mayor que 0 y hasta {ex.METROS_MAX}.")
    elif campo in ex.BARRAS:
        m = ex._RE_BARRAS.match(v)
        if v != ex.SIN_ACERO and (not m or not 1 <= int(m.group(1)) <= 200 or m.group(2) not in ex.DIAMETROS_BARRA):
            raise ValorInvalido(f"{campo} se escribe 'n Ø diámetro\"' con un diámetro de barra conocido (p. ej. 3Ø1/2\").")
    elif campo in ex.SEPARACION:
        m = ex._RE_SEPARACION.match(v)
        if not m or m.group(1) not in ex.DIAMETROS_BARRA or not 0 < float(m.group(2)) <= 1.0:
            raise ValorInvalido(f"{campo} se escribe 'Ø diámetro\" @ separación (m)' (p. ej. Ø1/2\" @ 0.20).")
    elif campo == "fc_kgcm2":
        if not v.isdigit() or not ex.FC_RANGO[0] <= int(v) <= ex.FC_RANGO[1]:
            raise ValorInvalido(f"El f'c va en kg/cm², un entero entre {ex.FC_RANGO[0]} y {ex.FC_RANGO[1]}.")
    elif campo == "tipo_losa":
        raise ValorInvalido("El tipo de losa (L# → A/B/C) se escribe en «Datos de la obra» y se vuelve a extraer.")
    return v


def campo_de_duda(conn, proyecto_id: str, id_elemento: str, campo_afectado: str) -> Optional[Tuple[str, str]]:
    """(uid, campo de datos_diseno) del ÚNICO campo de un elemento del plano vigente del que habla una duda T6n:, o
    None si la duda no apunta a un solo campo (dudas de la obra, de una tabla entera o de varias losas)."""
    if not campo_afectado.startswith(ex.ORIGEN_DUDA) or not id_elemento or id_elemento == "(obra)":
        return None
    plano = _plano_vigente(conn, proyecto_id)
    if plano is None:
        return None
    resto = campo_afectado[len(ex.ORIGEN_DUDA):]
    m = re.fullmatch(r"datos_diseno\.(.+)@(.*)", resto)
    if m:
        filas = conn.execute("""SELECT uid, datos_diseno_json FROM elementos_diseno WHERE proyecto_id = ? AND plano_id = ?
                                AND id_elemento = ? AND nivel_rango = ?""",
                             (proyecto_id, plano["id"], id_elemento, m.group(2))).fetchall()
        if len(filas) == 1 and m.group(1) in _cargar(filas[0]["datos_diseno_json"], {}):
            return filas[0]["uid"], m.group(1)
        return None
    candidatos = []
    for t in conn.execute("SELECT clave, elementos_json FROM tablas_extraidas WHERE plano_id = ?", (plano["id"],)):
        if not resto.startswith(t["clave"] + ":"):
            continue
        columna = resto[len(t["clave"]) + 1:]
        uids = _cargar(t["elementos_json"], [])
        for uid in uids:
            e = conn.execute("SELECT uid, id_elemento, datos_diseno_json FROM elementos_diseno WHERE uid = ?", (uid,)).fetchone()
            if e and e["id_elemento"] in (id_elemento, f"ZAPATA MURO LINDERO {id_elemento}") \
                    and columna in _cargar(e["datos_diseno_json"], {}):
                candidatos.append((e["uid"], columna))
    return candidatos[0] if len(candidatos) == 1 else None


def describir_campo(conn, proyecto_id: str, id_elemento: str, campo_afectado: str) -> Optional[Dict]:
    """Lo que la Mesa muestra de una duda T6n: confirmable: elemento, campo, valor y estado actuales."""
    r = campo_de_duda(conn, proyecto_id, id_elemento, campo_afectado)
    if r is None:
        return None
    e = conn.execute("SELECT * FROM elementos_diseno WHERE uid = ?", (r[0],)).fetchone()
    return {"uid": r[0], "id_elemento": e["id_elemento"], "nivel_rango": e["nivel_rango"], "campo": r[1],
            "valor": _cargar(e["datos_diseno_json"], {}).get(r[1]),
            "estado": _cargar(e["estado_campos_json"], {}).get(f"datos_diseno.{r[1]}")}


def aplicar_respuesta(conn, duda, respuesta: str, usuario: str) -> Optional[Dict]:
    """
    Si la duda T6n: apunta a un único campo, valida la respuesta y deja ese campo `confirmado` con la fuente
    "usuario" y auditoría por campo (dentro de la transacción de la Mesa). Devuelve el cambio, o None si la duda no
    apunta a un campo (la Mesa entonces solo guarda la respuesta). Lanza ValorInvalido sin tocar nada.
    """
    r = campo_de_duda(conn, duda["proyecto_id"], duda["id_elemento"], duda["campo_afectado"])
    if r is None:
        return None
    uid, campo = r
    valor = validar_valor(campo, respuesta)
    e = conn.execute("SELECT * FROM elementos_diseno WHERE uid = ?", (uid,)).fetchone()
    datos, estado = _cargar(e["datos_diseno_json"], {}), _cargar(e["estado_campos_json"], {})
    fuente = _cargar(e["fuente_json"], {})
    anterior = datos.get(campo)
    if estado.get(f"datos_diseno.{campo}") == CONFIRMADO and anterior != valor:
        raise ValorInvalido(f"{campo} de {e['id_elemento']} ya está confirmado como '{anterior}': no se sobrescribe.")
    ahora = _ahora()
    plano_fuente = (fuente.get("valores") or {}).get(campo)
    nueva = {"origen": "usuario", "via": "mesa_dudas", "duda_id": duda["id"], "por": usuario, "en": ahora,
             "valor_propuesto": anterior, "fuente_plano": plano_fuente}
    datos[campo] = valor
    estado[f"datos_diseno.{campo}"] = CONFIRMADO
    fuente.setdefault("valores", {})[campo] = nueva
    conn.execute("""UPDATE elementos_diseno SET datos_diseno_json = ?, estado_campos_json = ?, pendientes_json = ?,
                    fuente_json = ?, actualizado = ? WHERE uid = ?""",
                 (_json(datos), _json(estado), _json(sorted(k for k, v in estado.items() if v != CONFIRMADO)),
                  _json(fuente), ahora, uid))
    detalle = {"lote": None, "duda_id": duda["id"], "id_elemento": e["id_elemento"], "nivel_rango": e["nivel_rango"],
               "ejes": e["ejes"], "campo": campo, "valor": valor, "valor_anterior": anterior,
               "fuente": {"origen": "usuario", "archivo": fuente.get("archivo"), "revision": fuente.get("revision"),
                          "sha256": fuente.get("sha256"),
                          **({k: plano_fuente.get(k) for k in ("pagina", "hoja", "fila", "columna", "bbox")}
                             if isinstance(plano_fuente, dict) else {})}}
    _auditar_campo(conn, usuario, ahora, uid, detalle)
    return {"uid": uid, "campo": campo, "anterior": anterior, "nuevo": valor}


def campo_ya_confirmado(conn, proyecto_id: str, id_elemento: str, campo_afectado: str) -> bool:
    """Para el extractor: una duda T6n: de un campo que el usuario ya confirmó no se vuelve a abrir."""
    r = campo_de_duda(conn, proyecto_id, id_elemento, campo_afectado)
    if r is None:
        return False
    e = conn.execute("SELECT estado_campos_json FROM elementos_diseno WHERE uid = ?", (r[0],)).fetchone()
    return _cargar(e["estado_campos_json"], {}).get(f"datos_diseno.{r[1]}") == CONFIRMADO


# ---------- API ----------

class CuerpoConfirmar(BaseModel):
    confirmo: bool = False          # confirmación explícita del usuario (casilla de la pantalla)
    extraido_en: Optional[str] = None  # la extracción que el usuario revisó


def _http(exc: ErrorObra) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=str(exc))


@router.get("/api/proyectos/{proyecto_id}/tablas-extraidas/{tabla_id}")
def api_detalle_tabla(proyecto_id: str, tabla_id: int):
    try:
        return detalle_tabla(proyecto_id, tabla_id)
    except ErrorObra as exc:
        raise _http(exc)


@router.post("/api/proyectos/{proyecto_id}/tablas-extraidas/{tabla_id}/confirmar")
def api_confirmar_tabla(proyecto_id: str, tabla_id: int, cuerpo: CuerpoConfirmar):
    if not cuerpo.confirmo:
        raise HTTPException(status_code=422, detail="Falta la confirmación explícita ('confirmo': true).")
    try:
        return confirmar_tabla(proyecto_id, tabla_id, cuerpo.extraido_en)
    except ErrorObra as exc:
        raise _http(exc)
