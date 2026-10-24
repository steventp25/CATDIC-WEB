# BACKEND/importadores/validador_diseno.py
# Etapa 2 · T2 — Contrato del importador de datos de diseño (Capa 1, CLAUDE.md §4.1).
#
# validar_elemento_diseno(dict) -> {elemento_normalizado, estado_campos, dudas}
# Regla de Oro #1: nada se inventa ni se reformatea adivinando. Lo que falta o no cumple
# queda 'pendiente de verificar' y genera una DUDA_BLOQUEANTE para la Mesa de Dudas.
# No calcula cuantías ni recubrimientos sumados (Capa 3: se calculan al generar).
import re
from typing import Dict, List, Optional

import reglas_ingenieria as ri
from reglas_ingenieria import PENDIENTE

CONFIRMADO = "confirmado"
PENDIENTE_ESTADO = "pendiente_de_verificar"  # valor de estado_campos_json (database.py)
EJE_SIN_LETRA = "—"  # §4.4: losas y vigas sin eje-letra

CAMPOS_OBLIGATORIOS = (
    "id_elemento", "tipo_elemento", "nivel_rango", "ejes",
    "hoja_plano_origen", "archivo_plano_origen",
)

# Patrones de §4.4 con los grupos que recibe formatear_campo_ejes
_L = ri._PATRON_EJE_LETRA
_N = ri._PATRON_EJE_NUMERO
_FORMATOS_EJES = (
    ("cruce_puntual", re.compile(rf"EJE ({_L})-({_N})")),
    ("muro_entre_letras", re.compile(rf"EJE ({_L})-({_L}),({_N})")),
    ("viga_recta_sobre_letra", re.compile(r"EJE (\S+), ENTRE (\S+)-(\S+)")),
    ("tramo_portico", re.compile(r"EJE (\S+) ENTRE (\S+)-(\S+)")),
    ("area", re.compile(rf"\(({_L})-({_L})\),\(({_N})-({_N})\)")),
)

# Formatos de EJES admitidos por tipo. Un tipo no listado admite cualquier formato de §4.4
# salvo '—' y área. Los tipos de losa/escalera solo admiten '—' (error #11).
_SOLO_GUION = {"LOSA", "LOSA ALIGERADA", "LOSA MACIZA", "RAMPA DE ESCALERA", "ESCALERA"}
_VIGA = {"viga_recta_sobre_letra", "sin_eje_letra"}
_FORMATOS_POR_TIPO = {
    "PLATEA": {"area"},
    "COLUMNA": {"cruce_puntual"}, "COLUMNA RECTANGULAR": {"cruce_puntual"},
    "COLUMNA CIRCULAR": {"cruce_puntual"}, "ZAPATA": {"cruce_puntual"},
    "ZAPATA AISLADA": {"cruce_puntual"},
    "MURO H.A.": {"muro_entre_letras"}, "MURO DE HORMIGON": {"muro_entre_letras"},
    "VIGA": _VIGA, "VIGA HORMIGON": _VIGA, "VIGA DE AMARRE": _VIGA, "RIOSTRA": _VIGA,
    "PORTICO": {"tramo_portico"},
}
_FORMATOS_GENERICOS = {"cruce_puntual", "muro_entre_letras", "viga_recta_sobre_letra", "tramo_portico"}


def _vacio(valor: object) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        return not valor.strip() or valor.strip().lower() == PENDIENTE
    return False


def _formato_de_ejes(ejes: str) -> Optional[str]:
    """
    Nombre del formato de §4.4 que cumple 'ejes' EXACTAMENTE (idéntico al texto que produce
    formatear_campo_ejes), o None. No corrige ni normaliza el texto de entrada.
    """
    if ejes == EJE_SIN_LETRA:
        return "sin_eje_letra"
    for nombre, patron in _FORMATOS_EJES:
        m = patron.fullmatch(ejes)
        if not m:
            continue
        g = m.groups()
        if nombre == "cruce_puntual":
            args = dict(eje_letra_1=g[0], eje_num_1=g[1])
        elif nombre == "muro_entre_letras":
            args = dict(eje_letra_1=g[0], eje_letra_2=g[1], eje_num_1=g[2])
        elif nombre == "area":
            args = dict(eje_letra_1=g[0], eje_letra_2=g[1], eje_num_1=g[2], eje_num_2=g[3])
        else:
            args = dict(eje_letra_1=g[0], eje_num_1=g[1], eje_num_2=g[2])
        if ri.formatear_campo_ejes(nombre, **args) == ejes:
            return nombre
    return None


def validar_elemento_diseno(datos: Dict[str, object],
                            campos_esperados: Optional[List[str]] = None) -> Dict[str, object]:
    """
    Valida un elemento de diseño tal como lo entrega la fuente (con EJES ya escrito).

    datos: id_elemento, tipo_elemento, nivel_rango (como está impreso en la hoja, §4.2),
        ejes, hoja_plano_origen, archivo_plano_origen y datos_diseno (dict con lo que trae la
        fuente: dimensiones, acero, estribos...). Opcionales, pasados sin tocar: fuente,
        recorte_planta, recorte_detalle.
    campos_esperados: claves que datos_diseno debería traer para ese tipo. La lista por tipo
        aún no está fijada (T0); si no se pasa, solo se revisa lo que la fuente trae.

    Devuelve {elemento_normalizado, estado_campos, dudas}. Cada duda es un dict con
    categoria='DUDA_BLOQUEANTE', id_elemento, campo_afectado y descripcion_pregunta.
    categoria y recubrimiento_por_lado_m son solo consulta de tabla (None si el tipo no la tiene).
    """
    id_el = datos.get("id_elemento")
    etiqueta = str(id_el).strip() if not _vacio(id_el) else PENDIENTE
    dudas: List[Dict[str, str]] = []

    def duda(campo: str, texto: str):
        dudas.append({"categoria": "DUDA_BLOQUEANTE", "id_elemento": etiqueta,
                      "campo_afectado": campo, "descripcion_pregunta": texto})

    norm: Dict[str, object] = {}
    estado: Dict[str, str] = {}

    # --- Campos obligatorios ---
    for campo in CAMPOS_OBLIGATORIOS:
        valor = datos.get(campo)
        if _vacio(valor):
            norm[campo] = PENDIENTE
            estado[campo] = PENDIENTE_ESTADO
            duda(campo, f"Falta '{campo}' en la fuente: {PENDIENTE}.")
        else:
            norm[campo] = str(valor).strip()
            estado[campo] = CONFIRMADO

    # --- Tipo: categoría y recubrimiento por lado (consulta de tabla, sin sumar) ---
    norm["categoria"] = None
    norm["recubrimiento_por_lado_m"] = None
    tipo_norm = None
    if estado["tipo_elemento"] == CONFIRMADO:
        tipo = norm["tipo_elemento"]
        try:
            norm["categoria"] = ri.obtener_categoria_elemento(tipo)
            norm["recubrimiento_por_lado_m"] = ri.obtener_recubrimiento(tipo)
            tipo_norm = ri._normalizar_texto(tipo)
        except ValueError:
            estado["tipo_elemento"] = PENDIENTE_ESTADO
            duda("tipo_elemento",
                 f"Tipo '{tipo}' sin categoría ni recubrimiento definidos (perfil o conexión "
                 f"metálica, metaldeck o tipo desconocido): {PENDIENTE}.")

    # --- EJES: formato exacto de §4.4 según el tipo; nunca se reformatea ---
    if estado["ejes"] == CONFIRMADO:
        ejes = norm["ejes"]
        formato = _formato_de_ejes(ejes)
        if tipo_norm is None:
            # Tipo en duda: solo se exige que el texto sea un formato válido de §4.4
            valido = formato is not None
            esperado = "ningún formato de CLAUDE.md §4.4"
        else:
            permitidos = {"sin_eje_letra"} if tipo_norm in _SOLO_GUION \
                else _FORMATOS_POR_TIPO.get(tipo_norm, _FORMATOS_GENERICOS)
            valido = formato in permitidos
            esperado = "'—' (losas y escaleras, error #11)" if tipo_norm in _SOLO_GUION \
                else "el formato de CLAUDE.md §4.4 para ese tipo"
        if not valido:
            estado["ejes"] = PENDIENTE_ESTADO
            duda("ejes", f"EJES '{ejes}' no cumple {esperado}; no se corrige por adivinanza: "
                         f"{PENDIENTE}.")

    # --- datos_diseno: se guarda tal cual lo que trae la fuente ---
    fuente = datos.get("datos_diseno") or {}
    datos_diseno: Dict[str, object] = {}
    for clave, valor in fuente.items():
        if _vacio(valor):
            datos_diseno[clave] = PENDIENTE
            estado[f"datos_diseno.{clave}"] = PENDIENTE_ESTADO
            duda(f"datos_diseno.{clave}", f"La fuente no da '{clave}': {PENDIENTE}.")
        else:
            datos_diseno[clave] = valor
            estado[f"datos_diseno.{clave}"] = CONFIRMADO
    for clave in (campos_esperados or []):
        if clave not in datos_diseno:
            datos_diseno[clave] = PENDIENTE
            estado[f"datos_diseno.{clave}"] = PENDIENTE_ESTADO
            duda(f"datos_diseno.{clave}", f"La fuente no trae '{clave}': {PENDIENTE}.")
    norm["datos_diseno_json"] = datos_diseno

    for opcional in ("fuente", "recorte_planta", "recorte_detalle"):
        if opcional in datos:
            norm[opcional] = datos[opcional]

    return {"elemento_normalizado": norm, "estado_campos": estado, "dudas": dudas}
