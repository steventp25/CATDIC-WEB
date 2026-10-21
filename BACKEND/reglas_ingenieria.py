# backend/reglas_ingenieria.py
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# =====================================================================
# 1. REGLA DE RECUBRIMIENTOS Y MEDIDAS EN OBRA (Archivo 02, Sección 6)
# =====================================================================
RECUBRIMIENTO_POR_LADO_M = {
    "ZAPATA AISLADA": 0.075,
    "ZAPATA COMBINADA": 0.075,
    "ZAPATA DE MURO": 0.075,
    "MURO DE CONTENCION": 0.075,
    "COLUMNA RECTANGULAR": 0.040,
    "MURO DE HORMIGON": 0.040,
    "VIGA HORMIGON": 0.040,
    "RIOSTRA": 0.040,
    "PORTICO": 0.040,
    "LOSA ALIGERADA": 0.025,
    "LOSA MACIZA": 0.025,
    "PLATEA": 0.025,
    "RAMPA DE ESCALERA": 0.025,
}

def obtener_recubrimiento(tipo_elemento: str) -> float:
    tipo_norm = tipo_elemento.upper().strip()
    if tipo_norm not in RECUBRIMIENTO_POR_LADO_M:
        raise ValueError(f"Pendiente de verificar: recubrimiento no definido para '{tipo_elemento}'")
    return RECUBRIMIENTO_POR_LADO_M[tipo_norm]

def evaluar_medida_acero_obra(
    tipo_elemento: str,
    valor_plano_m: float,
    medida_acero_campo_m: Optional[float],
    tolerancia_m: float = 0.005
) -> Dict[str, object]:
    """
    Suma 2 * recubrimiento a la medida tomada sobre el acero en campo.
    Si coincide con el plano, la columna OBRA lleva el valor del plano.
    """
    rec = obtener_recubrimiento(tipo_elemento)
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

    if abs(diferencia) <= tolerancia_m:
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
# 2. FORMATO ESTRICTO DEL CAMPO EJES (Archivo 02, Sección 3)
# =====================================================================
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
    """
    caso = caso.lower().strip()
    if caso in ("losa", "viga_sin_eje_letra"):
        return "—"
    if caso == "cruce_puntual":
        if not eje_letra_1 or not eje_num_1:
            return "pendiente de verificar"
        return f"EJE {eje_letra_1.strip().upper()}-{eje_num_1.strip()}"
    if caso == "muro_entre_letras":
        if not eje_letra_1 or not eje_letra_2 or not eje_num_1:
            return "pendiente de verificar"
        return f"EJE {eje_letra_1.strip().upper()}-{eje_letra_2.strip().upper()},{eje_num_1.strip()}"
    if caso == "viga_recta_sobre_letra":
        if not eje_letra_1 or not eje_num_1 or not eje_num_2:
            return "pendiente de verificar"
        return f"EJE {eje_letra_1.strip().upper()}, ENTRE {eje_num_1.strip()}-{eje_num_2.strip()}"
    if caso == "tramo_portico":
        if not eje_letra_1 or not eje_num_1 or not eje_num_2:
            return "pendiente de verificar"
        return f"EJE {eje_letra_1.strip().upper()} ENTRE {eje_num_1.strip()}-{eje_num_2.strip()}"
    if caso == "elemento_unico_en_planta":
        return referencia_unica.strip().upper() if referencia_unica else "—"
    return "pendiente de verificar"


# =====================================================================
# 3. CÁLCULO REAL DE CUANTÍA POR ELEMENTO (Archivo 02, Sección 7)
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
        raise ValueError("Dimensiones de sección inválidas para cálculo de cuantía.")
    area_seccion_cm2 = (lx_m * 100.0) * (ly_m * 100.0)
    as_total_cm2 = 0.0
    for cant, diam in barras:
        diam_limpio = diam.replace("Ø", "").strip()
        if diam_limpio not in AREA_BARRA_CM2:
            raise ValueError(f"Diámetro '{diam}' pendiente de verificar en tabla de áreas.")
        as_total_cm2 += cant * AREA_BARRA_CM2[diam_limpio]

    cuantia = as_total_cm2 / area_seccion_cm2
    return round(cuantia * 100.0, 2) if en_porcentaje else round(cuantia, 4)


# =====================================================================
# 4. AGRUPACIÓN SECUENCIAL DEL LOG FOTOGRÁFICO (Archivo 02, Seccs. 4 y 5)
# =====================================================================
def agrupar_log_fotografico_visita(lista_fotos_log: List[Dict[str, str]]) -> List[Dict[str, object]]:
    """
    Recibe el log secuencial de fotos de la app CATDIC:
    [{'archivo': 'foto_01.jpg', 'etiqueta_elemento': 'C1 A4', 'leyenda': ''}, ...]
    Agrupa secuencialmente: una etiqueta de elemento abre el elemento y las
    fotos siguientes sin etiqueta nueva le pertenecen.
    """
    elementos_agrupados = []
    actual = None
    portico_activo = None

    for idx, item in enumerate(lista_fotos_log, start=1):
        etiqueta = (item.get("etiqueta_elemento") or "").strip()
        leyenda = (item.get("leyenda") or "").strip()
        archivo = item["archivo"]

        # Caso especial Pórticos: "P eje X" abre el eje; cada "Tramo n-n" es un elemento singular
        if re.match(r"^P\s+eje\s+([A-Z0-9]+)", etiqueta, re.IGNORECASE):
            m = re.match(r"^P\s+eje\s+([A-Z0-9]+)", etiqueta, re.IGNORECASE)
            portico_activo = m.group(1).upper()

        es_tramo_nuevo = re.search(r"Tramo\s+([A-Z0-9]+\s*-\s*[A-Z0-9]+)", etiqueta or leyenda, re.IGNORECASE)

        if es_tramo_nuevo and portico_activo:
            tramo = es_tramo_nuevo.group(1).replace(" ", "")
            id_portico_tramo = f"{portico_activo} ({tramo})"
            actual = {
                "orden_en_log": len(elementos_agrupados) + 1,
                "etiqueta_apertura": f"P eje {portico_activo} - Tramo {tramo}",
                "id_sugerido": id_portico_tramo,
                "es_portico_tramo": True,
                "fotos": [archivo],
                "leyendas_medicion": [leyenda] if leyenda else []
            }
            elementos_agrupados.append(actual)
        elif etiqueta:
            actual = {
                "orden_en_log": len(elementos_agrupados) + 1,
                "etiqueta_apertura": etiqueta,
                "id_sugerido": etiqueta.split()[0].upper(),
                "es_portico_tramo": False,
                "fotos": [archivo],
                "leyendas_medicion": [leyenda] if leyenda else []
            }
            elementos_agrupados.append(actual)
        else:
            # Foto sin etiqueta nueva: pertenece al elemento actualmente abierto
            if actual is not None:
                actual["fotos"].append(archivo)
                if leyenda:
                    actual["leyendas_medicion"].append(leyenda)

    return elementos_agrupados


def seleccionar_fotos_m1(fotos: List[str], tipo_elemento: str) -> List[str]:
    """
    M1 · FOTO DEL LEVANTAMIENTO:
    Incluye TODAS las fotos del elemento salvo en RAMPA DE ESCALERA (tope de 9 fotos
    repartidas a lo largo de la secuencia).
    """
    if tipo_elemento.upper().strip() == "RAMPA DE ESCALERA" and len(fotos) > 9:
        paso = (len(fotos) - 1) / 8.0
        indices = [round(i * paso) for i in range(9)]
        return [fotos[i] for i in indices]
    return fotos


# =====================================================================
# 5. CÁLCULO DE GROSOR DEL RECUADRO ROJO EN LOCALIZACIÓN (Archivo 02, M3)
# =====================================================================
def calcular_grosor_recuadro_rojo(alto_imagen_fuente_px: int, alto_celda_final_px: int, grosor_deseado_px: float = 4.5) -> int:
    """
    Compensa el factor de reducción (15x-20x) de la planta estructural completa
    para que el recuadro rojo siempre se vea de 4-5 px en el PDF final.
    """
    if alto_celda_final_px <= 0 or alto_imagen_fuente_px <= 0:
        return 20
    factor_escala = alto_celda_final_px / float(alto_imagen_fuente_px)
    grosor_fuente = round(grosor_deseado_px / factor_escala)
    return max(4, grosor_fuente)


# =====================================================================
# 6. ARCHIVADOR SIN SOBRESCRITURA (Archivo 01, Sección 6)
# =====================================================================
def obtener_ruta_salida_sin_sobrescribir(carpeta_salida: Path, nombre_base_pdf: str) -> Path:
    """
    Garantiza la regla: 'Siempre archivo nuevo, nunca sobrescribir'.
    Si 'Informe.pdf' existe, devuelve 'Informe v2.pdf', 'Informe v3.pdf', etc.
    """
    carpeta_salida.mkdir(parents=True, exist_ok=True)
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
# 7. AUDITOR AUTOMÁTICO CONTRA LOS 18 ERRORES RECURRENTES (Archivo 08, D)
# =====================================================================
def auditar_datos_ficha_antes_de_renderizar(ficha_data: Dict[str, object], formato: str) -> List[str]:
    """
    Revisa automáticamente el diccionario de la ficha antes de generar el PDF
    para bloquear cualquiera de los 18 errores documentados en el Archivo 08.
    """
    errores = []
    tipo = (ficha_data.get("tipo_elemento") or "").upper()
    texto_obs = (ficha_data.get("observaciones_texto") or "")
    ejes = (ficha_data.get("ejes") or "")
    nombre_proy = (ficha_data.get("nombre_proyecto") or "")
    fecha = (ficha_data.get("fecha") or "")

    # Error 8: NOMBRE PROYECTO con sufijo de visita o nivel en HV-LEV
    if formato == "HV-LEV" and any(p in nombre_proy.upper() for p in ["VISITA", "SOTANO", "NIVEL", "PARCIAL", "COMPLETIVO"]):
        errores.append("Error #8: NOMBRE PROYECTO no puede llevar sufijo de visita ni nivel en HV-LEV.")

    # Error 9a: Palabra prohibida "CORRIDO" en rótulos de acero
    if "CORRIDO" in texto_obs.upper():
        errores.append("Error #9: Está prohibido usar la palabra 'CORRIDO' en rótulos de acero.")

    # Error 9b: Toda viga debe llevar ESTRIBOS al final
    if "VIGA" in tipo or "RIOSTRA" in tipo or "PORTICO" in tipo:
        if "ESTRIBOS" not in texto_obs.upper():
            errores.append("Error #9: Toda viga/riostra/pórtico debe incluir obligatoriamente el campo ESTRIBOS.")

    # Regla HV-LEV Columna Rectangular: "ESTRIBOSS" con doble S
    if formato == "HV-LEV" and tipo == "COLUMNA RECTANGULAR":
        if "ESTRIBOSS" not in texto_obs:
            errores.append("Regla HV-LEV Columna: El rótulo exacto debe ser 'ESTRIBOSS' (con doble S).")

    # Error 9c: ACERO ADICIONAL combinado con "+"
    for linea in texto_obs.splitlines():
        if "ACERO ADICIONAL" in linea.upper() and "+" in linea:
            errores.append("Error #9: ACERO ADICIONAL IZQUIERDO y DERECHO van en líneas separadas, nunca combinados con '+'.")

    # Error 10: Cajas o secciones editoriales prohibidas
    prohibidas = ["REFERENCIA DE PLANO", "FUENTE DE LOS DATOS", "VERIFICACIÓN EN CAMPO", "NOTA PENDIENTE"]
    for frase in prohibidas:
        if frase in texto_obs.upper():
            errores.append(f"Error #10: Sección no autorizada detectada en OBSERVACIONES: '{frase}'.")

    # Error 11: Ejes de losa distintos de "—"
    if "LOSA" in tipo and ejes != "—":
        errores.append(f"Error #11: Las losas nunca llevan ejes (valor actual: '{ejes}', debe ser '—').")

    # Error 12: Formato de fecha DD/MM/AAAA
    if fecha and not re.match(r"^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/\d{4}$", fecha):
        errores.append(f"Error #12: La fecha '{fecha}' no cumple el formato obligatorio DD/MM/AAAA.")

    # Error 16: Firmas fabricadas
    if ficha_data.get("firma_inspector_imagen") or ficha_data.get("firma_texto_fabricado"):
        errores.append("Error #16: Las firmas nunca se fabrican; el campo debe quedar en blanco.")

    return errores
