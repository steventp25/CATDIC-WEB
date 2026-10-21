# Etapa 0 · T2 — Matriz de cobertura de reglas

Fuente: `CLAUDE.md` §4.4–§4.7, §5.2 y §6, contrastado contra `BACKEND/reglas_ingenieria.py` (325 líneas, versión del commit `d8e332c`) y las **Respuestas de Steven (21/10/2026)** de `PLANES/etapa-0.md`, que mandan sobre D1–D11.
Los hallazgos marcados como verificados se comprobaron ejecutando las funciones con valores sintéticos (sin modificar el código ni la BD).

**Actualización tras T4 / T4b / T5 (21/10/2026, observación O3 de `etapa-0-evaluacion.md`):** se conserva el historial de T2 y se anota el estado nuevo de cada hallazgo. Las columnas "Líneas" de T2 se refieren a la versión original de 325 líneas; las líneas marcadas "(actual)" se refieren a la versión corregida (654 líneas). Suite actual: 234 pruebas en verde. El estado final de los 18 errores está en el §7.

**Estados:** `cubierta` (el código cumple la regla) · `parcial` (existe código pero no cubre toda la regla o tiene defectos) · `falta` (no hay código y corresponde a Etapa 0) · `fuera de etapa` (no hay código y corresponde a otra etapa).
**Etapa responsable:** `E0-T4` / `E0-T4b` / `E0-T5` = esta etapa; `E3` = generadores de supervisión; `E4` = generadores de levantamiento.
**NUEVA** = discrepancia que no está en D1–D11 (detalle en §4 de este documento).

---

## 1. Confirmación de D1–D11

| # | ¿Se confirma? | Líneas (T2) | Nota tras las respuestas de Steven | Acción | Estado tras T4/T4b/T5 |
|---|---|---|---|---|---|
| D1 | Confirmado el comportamiento; **ya no es error** | 42-49 | Norma CATDIC: sin medida → OBRA = plano, conforme. Ver NUEVA N1 (plano ausente) y N19 (texto del hallazgo). | T3 lo prueba tal cual; T4 no lo cambia. | Sin cambios (decisión de Steven). `test_medida_obra_sin_medida_conforme_valor_plano`, `test_auditor_12_obra_sin_medida_d1`. |
| D2 | Confirmado | 35, 54 | `tolerancia_m = 0.005` fijo. P2: llega de la visita; sin ella, igualdad exacta (comparar valores ya redondeados, línea 51-52). | T4 | **Corregido (T4).** `tolerancia_m=None` por defecto → igualdad exacta. `test_medida_obra_igualdad_exacta_sin_tolerancia`, `test_medida_obra_tolerancia_none_igualdad_exacta`, `test_medida_obra_tolerancia_de_visita`. Queda O9 (tolerancia negativa sin validar). |
| D3 | Confirmado y **ampliado** | 9-23, 26 | 0.075/0.040/0.025 correctos; PLATEA 0.025 y PORTICO 0.040 aprobados (P3). Faltan `ESCALERA`, `COLUMNA CIRCULAR`, `VIGA DE AMARRE` y tildes. Nombres genéricos de §4.5 tampoco entran: NUEVA N3. | T4 (solo alias de P3) | **Corregido (T4).** Alias de P3 y tildes normalizadas. PLATEA **corregida a 0.075** por N15 (Steven corrigió su respuesta a P3). Tabla tipo → categoría por N3. |
| D4 | Confirmado | 98-116 | `elemento_unico_en_planta` (114-115) se **documenta** (P6), no se elimina. Falta validar letra/número (98-113). | T4 | **Corregido (T4).** Valida letra/número y documenta `elemento_unico_en_planta`. `test_ejes_argumentos_invertidos_pendiente`, `test_ejes_elemento_unico_en_planta_en_docstring`. |
| D5 | **Cerrado** | 122-157 | Tabla de áreas confirmada (P4); % con 2 decimales (P5). Nuevos defectos de entrada: NUEVA N2. | Ninguna en D5 | Cerrado. N2 corregido en T4. |
| D6 | Confirmado (a, b, c, d) | 208-213 (a), 172/182 (b), 202 (c) | P9: convención `P eje X` + `Tramo n-n` correcta. Se suman NUEVA N5, N6, N7. | T4 | **Corregido (T4)** a, b, c; d documentado en el docstring. N5 corregido; N6 **no es error** (se mantiene); N7 sin tocar. |
| D7 | Confirmado | 218-228 | Sin parámetro de formato: no puede hacer `pick4` STP-MIVED; solo `RAMPA DE ESCALERA` exacto (no `ESCALERA`). | T4 | **Corregido (T4).** `seleccionar_fotos_pick4` y `TIPOS_ESCALERA`. |
| D8 | Confirmado | 239-243 | Verificado: `calcular_grosor_recuadro_rojo(0,100)` → `20`. P8: datos inválidos → `ValueError`; factor = min(ancho, alto); mínimo 4 px se mantiene. Tampoco valida `grosor_deseado_px ≤ 0`. | T4 | **Corregido (T4).** Nueva firma con ancho y alto de fuente y celda. |
| D9 | Confirmado | 254 | `mkdir` al consultar. | T4 | **Corregido (T4).** Ya no crea carpetas. `test_versionado_no_crea_carpetas`. |
| D10 | Confirmado | 318 | No hay `formatear_fecha_ddmmaaaa`; regex acepta `31/02/2026`. Fecha vacía pasa: NUEVA N14. | T4 | **Corregido (T4).** `formatear_fecha_ddmmaaaa` y validación de calendario real. Queda O8 (fecha que no es texto lanza `TypeError`). |
| D11 | Confirmado y **ampliado** | 285, 293-300, 308 | `NOTA PENDIENTE` se quita (P7). Además: N8, N9, N10, N11, N12, N13. | T4 | **Corregido (T4)** salvo N9 (parcial, E3). |

---

## 2. Matriz §4.4–§4.7 y §5.2

La columna "Estado" conserva el estado de T2 y, tras la flecha, el estado después de T4/T4b/T5.

### §4.4 — Formato estricto del campo `EJES`

| Regla | Función (líneas) | Estado | Etapa | Prueba |
|---|---|---|---|---|
| Columna / zapata puntual `EJE F-11` | `formatear_campo_ejes` caso `cruce_puntual` (98-101) | cubierta | E0-T3 | `test_ejes_cruce_puntual_columna` |
| Muro entre letras `EJE D-E,4` (coma, sin `FILA` ni paréntesis) | `formatear_campo_ejes` `muro_entre_letras` (102-105) | cubierta (generación); el auditor no valida formato: N13 → **cubierta** (N13 corregido en T4) | E0-T3 / E0-T4 | `test_ejes_muro_entre_letras_con_coma`, `test_ejes_muro_sin_fila_ni_parentesis`, `test_auditor_11_muro_con_fila_rechazado` |
| Viga recta `EJE C, ENTRE 2-3` | `viga_recta_sobre_letra` (106-109) | cubierta | E0-T3 | `test_ejes_viga_recta_sobre_letra` |
| Tramo de pórtico `EJE F ENTRE 10-11` | `tramo_portico` (110-113) | cubierta | E0-T3 | `test_ejes_tramo_portico` |
| Losas (todas) y vigas sin eje-letra → `—` | `losa`, `viga_sin_eje_letra` (96-97) | cubierta | E0-T3 | `test_ejes_losa_guion_largo`, `test_ejes_viga_sin_eje_letra_guion_largo` |
| Datos faltantes → `"pendiente de verificar"` | (99-100, 103-104, 107-108, 111-112, 116) | cubierta | E0-T3 | `test_ejes_faltan_datos_pendiente`, `test_ejes_caso_desconocido_pendiente` |
| Letra es letra y número es número | — (no se valida) | parcial (D4) → **cubierta** | E0-T4 | `test_ejes_argumentos_invertidos_pendiente` |
| Caso `elemento_unico_en_planta` (no está en CLAUDE.md) | (114-115) | parcial: se documenta (P6) → **cubierta** (documentado) | E0-T4 | `test_ejes_elemento_unico_en_planta_documentado`, `test_ejes_elemento_unico_en_planta_en_docstring` |
| **(T4b)** EJES de la PLATEA como área `(A-B),(1-2)`; las losas siguen con `—` | `formatear_campo_ejes` caso `area` (217-223 actual), `_RE_EJES_AREA` (133-135 actual), auditor #11 de platea (595-601 actual) | **cubierta** | E0-T4b | `test_ejes_area_platea`, `test_ejes_area_con_prima_y_minusculas`, `test_ejes_area_faltan_datos_pendiente`, `test_ejes_area_en_docstring`, `test_auditor_11_no_aplica_a_platea`, `test_auditor_11_platea_area_con_prima_ok`, `test_auditor_11_platea_sin_formato_area_rechazada`, `test_auditor_11_losa_sigue_con_guion_largo_no_area`, `test_auditor_11_platea_no_cae_en_regla_de_muro` |
| **(T4b)** Ejes con prima (`A'`, `2'`) en letra y número | `_PATRON_EJE_LETRA` / `_PATRON_EJE_NUMERO` (130-131 actual), `_es_eje_letra` / `_es_eje_numero` (138-145 actual) | **cubierta**; salvedades sin respuesta de Steven: ejes de varias letras y `Ñ` (O6), solo comilla recta `'` (O7) | E0-T4b | `test_ejes_cruce_puntual_letra_con_prima`, `test_ejes_numero_con_prima`, `test_ejes_prima_mal_formada_pendiente`, `test_ejes_prima_sigue_rechazando_invertidos` |
| **(T4b)** Lectura del cruce en la visita: `A1` o `1A` = ejes A y 1 (ambos órdenes); lo ambiguo → `"pendiente de verificar"` | `interpretar_eje_de_visita` (148-172 actual) | **cubierta** | E0-T4b | `test_interpretar_eje_de_visita_ambos_ordenes`, `test_interpretar_eje_de_visita_ambiguo_pendiente`, `test_interpretar_eje_de_visita_alimenta_cruce_puntual`, `test_interpretar_eje_de_visita_docstring_con_regla_de_steven` |

### §4.5 — Física de obra y recubrimientos

| Regla | Función (líneas) | Estado | Etapa | Prueba |
|---|---|---|---|---|
| Zapatas y muros de contención 0.075 m/lado | `RECUBRIMIENTO_POR_LADO_M` (10-13), `obtener_recubrimiento` (25-29) | cubierta | E0-T3 | `test_recubrimiento_zapatas_y_muro_contencion_0075` |
| Columnas, vigas, riostras, muros H.A. 0.040 m/lado | (14-18) | parcial: falta `COLUMNA CIRCULAR`, `VIGA DE AMARRE` (D3); nombres genéricos N3 → **cubierta** | E0-T4 | `test_recubrimiento_columnas_vigas_riostras_muros_ha_0040`, `test_recubrimiento_alias_columna_circular_viga_amarre` |
| Losas y escaleras 0.025 m/lado | (19-22) | parcial: falta `ESCALERA` (D3) → **cubierta** | E0-T4 | `test_recubrimiento_losas_y_escaleras_0025`, `test_recubrimiento_alias_escalera` |
| Tildes (`MURO DE CONTENCIÓN`, `PÓRTICO`) | (26) | falta (D3) → **cubierta** (`_normalizar_texto`) | E0-T4 | `test_recubrimiento_normaliza_tildes` |
| **(N3)** Nombres genéricos `ZAPATA`, `COLUMNA`, `VIGA`, `LOSA`, `MURO H.A.` con tabla tipo → categoría de §4.5 | `RECUBRIMIENTO_POR_CATEGORIA_M` (23-27 actual), `CATEGORIA_POR_TIPO` (30-52 actual), `obtener_categoria_elemento` (63-68 actual) | **cubierta** | E0-T4 | `test_recubrimiento_tabla_categorias`, `test_recubrimiento_nombres_genericos` |
| **(N15)** PLATEA = cimentación, 0.075 m/lado | `CATEGORIA_POR_TIPO["PLATEA"]` (36 actual) | **cubierta** en código; su redacción en el CLAUDE.md §4.5 corresponde al planificador / Steven (O1) | E0-T4 | `test_recubrimiento_platea_0075` |
| Tipo desconocido / metálicos → `ValueError` "pendiente de verificar" | (27-28) | cubierta (mensaje con "P" mayúscula: N4, sin unificar, O10) | E0-T3 | `test_recubrimiento_tipo_desconocido_pendiente`, `test_recubrimiento_metalicos_pendiente` |
| `medida_campo + 2·rec == valor_plano` → conforme, OBRA = plano | `evaluar_medida_acero_obra` (51-61) | parcial: tolerancia fija 0.005 (D2) → **cubierta** | E0-T4 | `test_medida_obra_igualdad_exacta_sin_tolerancia`, `test_medida_obra_tolerancia_none_igualdad_exacta`, `test_medida_obra_tolerancia_de_visita`, `test_medida_obra_conforme_suma_2_recubrimientos` |
| Sin medida en obra → OBRA = plano, conforme (norma CATDIC, D1) | (42-49) | cubierta (decisión Steven) | E0-T3 | `test_medida_obra_sin_medida_conforme_valor_plano` |
| Discrepancia → OBRA = medida corregida, no conforme, hallazgo | (62-73) | cubierta | E0-T3 | `test_medida_obra_discrepancia_no_conforme` |
| Valor del plano ausente → `"pendiente de verificar"` (Regla de Oro) | — | falta (**NUEVA N1**) → **cubierta** | E0-T4 | `test_medida_obra_sin_valor_plano_pendiente` |

### §4.6 — Cálculo de cuantía

| Regla | Función (líneas) | Estado | Etapa | Prueba |
|---|---|---|---|---|
| `As_total / (b·h)` calculada por elemento | `calcular_cuantia_elemento` (134-157) | cubierta | E0-T3 | `test_cuantia_formula_as_total_sobre_bh` |
| STP-MIVED decimal (`0.0185`), CATDIC-STP % (`1.85`, 2 decimales P5) | (157) | cubierta | E0-T3 | `test_cuantia_decimal_vs_porcentaje` |
| Tabla de áreas de barras (P4 confirmada) | `AREA_BARRA_CM2` (122-132) | cubierta | E0-T3 | `test_cuantia_tabla_areas_confirmada` |
| Diámetro desconocido → `ValueError` | (152-153) | cubierta | E0-T3 | `test_cuantia_diametro_desconocido_error` |
| Dimensiones ≤ 0 → `ValueError` | (146-147) | cubierta (mensaje sin "pendiente de verificar": N4 / O10) | E0-T3 | `test_cuantia_dimensiones_no_positivas_error` |
| Sin barras o cantidades ≤ 0 → no inventar 0.0 | — | falta (**NUEVA N2**) → **cubierta** | E0-T4 | `test_cuantia_sin_barras_error`, `test_cuantia_cantidad_no_positiva_error` |
| Jamás copiar cuantías (auditor compara contra recálculo) | — | falta → **cubierta** (`_auditar_cuantia_ficha`, 468-494 actual) | E0-T5 | `test_auditor_12_cuantia_no_recalculada` y demás `test_auditor_12_cuantia_*` |

### §4.7 — Módulos visuales M1–M4

| Regla | Función (líneas) | Estado | Etapa | Prueba |
|---|---|---|---|---|
| M1 agrupación secuencial (etiqueta abre; siguientes sin etiqueta le pertenecen) | `agrupar_log_fotografico_visita` (163-215) | cubierta en lo básico | E0-T3 | `test_log_etiqueta_abre_elemento` |
| M1 fotos antes de la primera etiqueta no se pierden | (208-213) | falta (D6a) → **cubierta** (grupo con `duda`) | E0-T4 | `test_log_fotos_antes_de_primera_etiqueta_reportadas` |
| M1 pórtico: se reinicia al abrir otro elemento | (172, 182) | falta (D6b) → **cubierta** | E0-T4 | `test_log_portico_se_reinicia_con_otro_elemento` |
| M1 pórtico: tramo con id `A (2-3)` | (184-197) | cubierta | E0-T3 | `test_log_tramo_portico_id_formato` |
| M1 `P eje X` sin tramo no crea id `P` | (198-202) | falta (D6c); causa extra **NUEVA N5** → **cubierta** | E0-T4 | `test_log_p_eje_sin_tramo_no_crea_id_p`, `test_log_p_eje_con_tramo_en_leyenda` |
| M1 tramo repetido en fotos siguientes. *Propuesta T2 (superada): no duplicar el elemento.* **Decisión de Steven (N6): NO es error; un mismo tramo puede abrir varios elementos (elementos grandes o complejos).** | (184-197); docstring de `agrupar_log_fotografico_visita` (284-286 actual) | **cubierta** (se mantiene el comportamiento original) | E0-T4 | `test_log_tramo_repetido_abre_elementos_separados` |
| M1 HV-LEV: todas las fotos; escaleras máx. 9 repartidas | `seleccionar_fotos_m1` (218-228) | parcial: solo `RAMPA DE ESCALERA` exacto (D7) → **cubierta** | E0-T4 | `test_fotos_hvlev_todas`, `test_fotos_escalera_max_9_primera_ultima_orden`, `test_fotos_escalera_alias_escalera_max_9` |
| M1 STP-MIVED: `pick4` hasta 4 repartidas o 1 grande | — | falta (D7) → **cubierta** (`seleccionar_fotos_pick4`) | E0-T4 | `test_fotos_stp_mived_pick4_repartidas`, `test_fotos_stp_mived_una_foto` |
| M1 recorte *cover* `ImageOps.fit` con gutter blanco | — (sin código) | fuera de etapa | E3 / E4 | — (generadores) |
| M2 prohibido `CORRIDO` en rótulos de acero | auditor (289) | parcial (N8, N9) → **cubierta** para N8; N9 sigue parcial | E0-T4 / E3 | ver error #9 |
| M2 viga/riostra/pórtico con `ESTRIBOS` **al final** | auditor (293-295) | parcial (D11, N10) → **cubierta** | E0-T4 | ver error #9 |
| M2 HV-LEV columnas: rótulo exacto `ESTRIBOSS` | auditor (298-300) | parcial (D11, **NUEVA N11**) → **cubierta** | E0-T4 | `test_auditor_estriboss_columna_hvlev`, `test_auditor_estriboss_columna_circular`, `test_auditor_estriboss_sin_distinguir_mayusculas` |
| M2 HV-LEV losa aligerada: imagen `LOSA TÍPICA` con APOYO 1–4 | — (sin código) | fuera de etapa | E4 | — |
| M3 planta completa del nivel (nunca zoom) | — (sin código) | fuera de etapa | E3 / E4 | — |
| M3 recuadro `RGB(220,0,0)` | — (no hay constante) | fuera de etapa | E3 / E4 | — |
| M3 grosor `4.5 px / factor` (≈22 px en plantas de 200 dpi) | `calcular_grosor_recuadro_rojo` (234-243) | parcial (D8) → **cubierta** (cálculo) | E0-T4 | `test_grosor_formula_4_5_sobre_factor`, `test_grosor_factor_min_ancho_alto`, `test_grosor_minimo_4px`, `test_grosor_datos_invalidos_error`, `test_grosor_deseado_no_positivo_error` |
| M4 detalle = recorte del plano; rotular `"1"`, `"2"` en muros con borde; nunca foto de campo | — (sin código) | fuera de etapa | E3 / E4 | — |

### §5.2 — Nombres de salida y peso

| Regla | Función (líneas) | Estado | Etapa | Prueba |
|---|---|---|---|---|
| Jamás sobrescribir: ` v2.pdf`, ` v3.pdf` | `obtener_ruta_salida_sin_sobrescribir` (249-266) | cubierta (sufijos); mantiene `.PDF` en mayúscula | E0-T3 | `test_versionado_libre_mismo_nombre`, `test_versionado_existe_v2`, `test_versionado_existe_v2_da_v3`, `test_versionado_mived_fi_extension_mayuscula`, `test_versionado_no_sobrescribe_existente` |
| Consultar la ruta no escribe en disco | (254) | falta (D9) → **cubierta** | E0-T4 | `test_versionado_no_crea_carpetas` |
| Nombre STP-MIVED `<Proyecto> - STP - <Elementos nivel> - DD-MM-AAAA.pdf` | — (sin función que lo construya) | fuera de etapa (**NUEVA N16**) | E3 | En E0 solo se usa como nombre de ejemplo en las pruebas de versionado |
| Nombre MIVED FI `MIVED - <PROYECTO>-<ELEMENTOS NIVEL>.PDF` | — | fuera de etapa (**NUEVA N16**) | E3 | ídem |
| PDF < 30 MB | — | falta → **cubierta** (`auditar_archivo_pdf_generado`, 632-654 actual; límite 30 000 000 bytes, pendiente confirmar frente a 30 MiB) | E0-T5 | `test_auditor_15_constante_peso_maximo`, `test_auditor_15_pdf_bajo_limite_ok`, `test_auditor_15_pdf_mayor_30mb` |
| Fotos máx. 1000×1000, JPG q72, `exif_transpose` | — (sin código) | fuera de etapa (**NUEVA N17**) | E3 / E4 | — |
| Fecha siempre `DD/MM/AAAA` | — (solo regex del auditor, 318) | falta (D10) → **cubierta** (`formatear_fecha_ddmmaaaa`, `_es_fecha_ddmmaaaa_valida`) | E0-T4 | `test_formatear_fecha_ddmmaaaa`, `test_auditor_fecha_valida_11_09_2026`, `test_auditor_fecha_m_d_aaaa_rechazada`, `test_auditor_fecha_imposible_31_02_rechazada` |

---

## 3. Matriz de los 18 errores de §6 (corrige la tabla del plan)

Estado **en T2** (historial). El estado final tras T4/T4b/T5 está en el §7.

| # | Error | Función (líneas) | Estado | Etapa | Prueba T3/T5 propuesta | Corrección respecto al plan |
|---|---|---|---|---|---|---|
| 1 | LOCALIZACION con recorte o nivel equivocado | — | fuera de etapa | E3 / E4 | — | = |
| 2 | DETALLE con foto de campo / recorte ilegible | — | fuera de etapa | E3 / E4 | — | = |
| 3 | Cuadrícula de fotos con franjas, sin gutter o incompleta | apoyo: `seleccionar_fotos_m1` (218-228) elige las fotos, no la cuadrícula | fuera de etapa | E3 / E4 | — | = |
| 4 | Recuadro rojo invisible a tamaño final | apoyo: `calcular_grosor_recuadro_rojo` (234-243) | parcial (cálculo E0; verificación visual E3/E4) | E0-T4 / E3 / E4 | pruebas de grosor de §4.7 | Plan decía "no cubierto": hay apoyo de cálculo |
| 5 | `LEVANTAMIENTO` descentrado / logos HV desalineados | — | fuera de etapa | E4 | — | = |
| 6 | Bloques 1 y 2 de igual altura (debe ser 1.6 : 1) | — | fuera de etapa | E4 | — | = |
| 7 | `NIVEL` mal ubicado según formato | — | fuera de etapa | E4 | — | = |
| 8 | NOMBRE PROYECTO con sufijos en HV-LEV | auditor (285) | parcial: `SÓTANO` con tilde no se detecta (D11) | E0-T4 | `test_auditor_8_nombre_con_sufijo`, `test_auditor_8_sotano_con_tilde`, `test_auditor_8_nombre_limpio_ok` | = |
| 9 | `CORRIDO`; viga sin `ESTRIBOS`; `ACERO ADICIONAL` con `+` | auditor (289, 293-295, 303-305) | **parcial** (no "cubierto"): `ESTRIBOS` no se verifica al final (D11); `PÓRTICO` con tilde (N10); falso positivo `RECORRIDO` (N8); solo revisa `observaciones_texto` (N9) | E0-T4 | `test_auditor_9_corrido`, `test_auditor_9_recorrido_no_es_corrido`, `test_auditor_9_viga_sin_estribos`, `test_auditor_9_estribos_al_final`, `test_auditor_9_portico_con_tilde`, `test_auditor_9_acero_adicional_mas`, `test_auditor_9_acero_adicional_lineas_separadas_ok` | Plan decía "Cubierto" → Parcial |
| 10 | Cajas editoriales prohibidas | auditor (308-311) | **parcial**: `NOTA PENDIENTE` sobra (P7); `Verificacion en campo` sin tilde no se detecta (N12) | E0-T4 | `test_auditor_10_cajas_prohibidas`, `test_auditor_10_verificacion_sin_tilde`, `test_auditor_10_nota_pendiente_permitida` | Plan decía "Cubierto" → Parcial |
| 11 | Ejes de losa ≠ `—` o eje por proximidad visual | auditor (314) | parcial: proximidad visual no verificable con datos; formato EJES de no-losas sin validar (N13); ¿PLATEA? (N15, respondida después: no es losa, EJES como área) | E0-T4 | `test_auditor_11_losa_con_ejes`, `test_auditor_11_losa_guion_largo_ok`, `test_auditor_11_muro_con_fila_rechazado` | Se añade N13/N15 |
| 12 | Cuantía copiada; fecha M/D/AAAA; OBRA sin corrección | auditor (318) | parcial: solo fecha, regex débil (D10), fecha vacía pasa (N14) | E0-T4 (fecha) / E0-T5 (cuantía, OBRA) | `test_auditor_fecha_*` (ver §5.2), `test_auditor_12_fecha_vacia_pendiente`, `test_auditor_12_cuantia_no_recalculada`, `test_auditor_12_obra_sin_correccion_recubrimiento` | Se añade N14 |
| 13 | Mezclar cabeceras/rótulos entre formatos | — (`formato` no se valida contra lista cerrada) | fuera de etapa | E3 / E4 | — | = |
| 14 | Cabeceras CATDIC-STP superpuestas o en 2 líneas | — | fuera de etapa | E3 | — | = |
| 15 | PDF > 30 MB o sobrescritura sin `v2` | `obtener_ruta_salida_sin_sobrescribir` (249-266) evita sobrescribir; el auditor no revisa | parcial | E0-T4 (D9) / E0-T5 (auditor) | pruebas de versionado de §5.2, `test_auditor_15_pdf_mayor_30mb`, `test_auditor_15_destino_ya_existe` | Plan decía "No cubierto": la función de versionado sí existe |
| 16 | Firmas fabricadas o previas no borradas en FI | auditor (322-323) | parcial (campos del diccionario); borrado en PDF base es E3 | E0-T3 / E3 | `test_auditor_16_firma_fabricada`, `test_auditor_16_sin_firma_ok` | = |
| 17 | Mampostería marcada / faltan `"Sí"` obligatorios en FI | — | fuera de etapa | E3 | — | = |
| 18 | Rehacer un FI MIVED existente en vez de actualizarlo | — (no hay función que localice la última versión existente: N18) | fuera de etapa | E3 | — | Se añade N18 |

---

## 4. Discrepancias NUEVAS (no están en D1–D11)

Todas verificadas leyendo el código; las marcadas "(verificado)" además se ejecutaron con valores sintéticos. Las líneas son de la versión T2 (325 líneas). La última columna anota el estado tras las respuestas de Steven y T4/T4b/T5.

| ID | Línea(s) | Hallazgo | Regla | Propuesta (T2) | Estado tras T4/T4b/T5 |
|---|---|---|---|---|---|
| **NUEVA N1** | 31-49, 51-52 | `valor_plano_m` no se valida. Con `valor_plano_m=None` y sin medida devuelve `valor_columna_obra_m=None, conforme=True` (verificado); con medida lanza `TypeError`. | Regla de Oro #1, §4.5 | T4: plano ausente → `ValueError` "pendiente de verificar". No contradice D1 (D1 es *medida* ausente, no *plano* ausente). | **Corregido (T4).** `test_medida_obra_sin_valor_plano_pendiente`. |
| **NUEVA N2** | 149-157 | `barras=[]` devuelve cuantía `0.0` y una cantidad negativa da cuantía negativa (`-0.0088`, verificado). Un 0.0 es un dato inventado. | Regla de Oro #1, §4.6 | T4: lista vacía o cantidad ≤ 0 → `ValueError` "pendiente de verificar". | **Corregido (T4).** `test_cuantia_sin_barras_error`, `test_cuantia_cantidad_no_positiva_error`. |
| **NUEVA N3** | 9-23 (16) | Los nombres genéricos de §4.5 no se reconocen: `ZAPATA`, `COLUMNA`, `VIGA`, `LOSA`, `MURO H.A.` lanzan `ValueError` (verificado). Además `VIGA HORMIGON` no lleva "DE" mientras `MURO DE HORMIGON` sí: `VIGA DE HORMIGON` falla (verificado). | §4.5 | *Propuesta T2 (superada):* no corregir en T4 hasta que Steven decidiera, por el límite de alias de P3. | **Respondida y corregida (T4).** Steven: sí se aceptan `ZAPATA`, `COLUMNA`, `VIGA`, `LOSA`, `MURO H.A.`. T4 agregó la tabla explícita tipo → categoría de §4.5 (`CATEGORIA_POR_TIPO` → `RECUBRIMIENTO_POR_CATEGORIA_M`) y el recubrimiento sale de la categoría. `VIGA DE HORMIGON` no fue pedido: sigue en "pendiente de verificar". `test_recubrimiento_tabla_categorias`, `test_recubrimiento_nombres_genericos`. |
| **NUEVA N4** | 28, 147 | El mensaje de `obtener_recubrimiento` dice "Pendiente de verificar" (P mayúscula) y el de dimensiones de cuantía (147) no contiene "pendiente de verificar". | Regla de Oro #1 (texto estándar) | T3 compara sin distinguir mayúsculas; T4 puede unificar el texto en minúsculas. | **Sin tocar** (observación O10 de la evaluación; a revisar antes de enrutar a "Con dudas" en E3). |
| **NUEVA N5** | 184 | `re.search(..., etiqueta or leyenda)`: si la foto trae etiqueta, la leyenda no se mira. `P eje A` con leyenda `Tramo 2-3` en la misma foto crea un elemento `P` (verificado). Es una causa distinta de D6c. | §4.3, §4.7 M1, P9 | T4: buscar `Tramo` en etiqueta **y** leyenda. | **Corregido (T4).** `test_log_p_eje_con_tramo_en_leyenda`. |
| **NUEVA N6** | 184-197 | Cada foto sin etiqueta cuya leyenda contiene `Tramo n-n` abre un tramo nuevo, aunque sea el mismo tramo: `A (2-3)` sale duplicado (verificado). | §4.3 (cada tramo es **un** elemento), §4.7 M1 | *Propuesta T2 (superada):* si el tramo es el mismo que el abierto, agregar la foto al elemento actual. | **NO es error (respuesta de Steven).** Un mismo tramo puede abrir varios elementos (elementos grandes o complejos). Se mantiene el comportamiento original y lo protege `test_log_tramo_repetido_abre_elementos_separados` (la prueba de T3 que exigía no duplicar el tramo se invirtió y se renombró en T4). La excepción a §4.3 se documenta en el CLAUDE.md (O2, a cargo del planificador / Steven). |
| **NUEVA N7** | 195 | El texto `Tramo 2-3 ...` se guarda en `leyendas_medicion` como si fuera una medición. | §4.1 (capa 2: mediciones en obra) | T4: separar el rótulo de tramo de la medición. Menor. | **Sin tocar** (menor; queda para E3 junto con el log real, P9). |
| **NUEVA N8** | 289 | `"CORRIDO" in texto` da falso positivo con `RECORRIDO` (verificado: "recorrido de inspeccion" → Error #9). | Error #9 | T4: buscar la palabra completa (`\bCORRIDOS?\b`). | **Corregido (T4).** `test_auditor_9_recorrido_no_es_corrido`. No cubre `CORRIDA` (O11). |
| **NUEVA N9** | 279, 289-305 | Los chequeos de acero (#9) solo leen `observaciones_texto`. En STP-MIVED y CATDIC-STP el acero va en la tabla `INFORMACION ARMADO`, que el auditor no revisa. | Error #9, §4.7 M2 | Parcial. Definir en E3 qué campos de la ficha son "rótulos de acero"; en E0 se deja documentado. | **Parcial** (sin cambio; E3). |
| **NUEVA N10** | 293 | `"PORTICO" in tipo` no detecta `PÓRTICO` con tilde: un pórtico sin estribos pasa sin error (verificado). | Error #9 | T4: normalizar tildes del tipo antes de comparar (mismo normalizador que D3). | **Corregido (T4).** `test_auditor_9_portico_con_tilde`. |
| **NUEVA N11** | 298 | `ESTRIBOSS` solo se exige si `tipo == "COLUMNA RECTANGULAR"`. `COLUMNA CIRCULAR` (alias que T4 agrega por P3) quedaría sin chequeo (verificado). | §4.7 M2 ("las columnas") | T4: aplicar a todo tipo que empiece por `COLUMNA`. | **Corregido (T4).** `test_auditor_estriboss_columna_circular`. |
| **NUEVA N12** | 308 | La lista tiene `VERIFICACIÓN EN CAMPO` con tilde: `Verificacion en campo` sin tilde no se detecta (verificado). | Error #10 | T4: comparar sin tildes. | **Corregido (T4).** `test_auditor_10_verificacion_sin_tilde`. |
| **NUEVA N13** | 313-315 | El auditor solo revisa EJES en losas. No detecta `FILA` ni paréntesis en muros (`EJE D-E (FILA 4)` pasa, verificado) ni formatos fuera de los 4 de §4.4. | §4.4, error #11 | T4: validar con las mismas reglas de `formatear_campo_ejes` cuando el tipo lo permita. | **Corregido (T4)** para muros (`FILA` y paréntesis); no aplica a la platea (T4b). `test_auditor_11_muro_con_fila_rechazado`, `test_auditor_11_muro_formato_correcto_ok`, `test_auditor_11_platea_no_cae_en_regla_de_muro`. |
| **NUEVA N14** | 318 | `if fecha and ...`: una ficha sin fecha no genera error (verificado). | Regla de Oro #1, error #12 | T4: fecha vacía → error "pendiente de verificar". | **Corregido (T4).** `test_auditor_12_fecha_vacia_pendiente`. |
| **NUEVA N15** | 21, 314 | `PLATEA` usa recubrimiento de losa (0.025) pero el chequeo #11 solo mira `"LOSA" in tipo`. No está definido si la platea es "losa" a efectos de `EJES = —`. | §4.4, error #11 | *Propuesta T2 (superada):* pendiente de verificar con Steven, sin cambios hasta su respuesta. | **Respondida y corregida (T4 / T4b).** Steven: la PLATEA es cimentación → **0.075 m** (corrige P3) y no es losa, así que no se le exige `—`. Sus EJES van como **área `(A-B),(1-2)`** (`formatear_campo_ejes` caso `area`); el auditor rechaza en platea todo EJES que no sea de área. `test_recubrimiento_platea_0075`, `test_ejes_area_platea`, `test_auditor_11_no_aplica_a_platea`, `test_auditor_11_platea_sin_formato_area_rechazada`. Redacción en CLAUDE.md §4.5: O1. |
| **NUEVA N16** | — (sin código) | No hay función que construya los nombres de salida de §5.2 (STP-MIVED y MIVED FI). | §5.2 | Fuera de etapa: E3. | Fuera de etapa (E3). |
| **NUEVA N17** | — (sin código) | No hay función para redimensionar fotos (1000×1000, q72, `exif_transpose`). | §5.2 | Fuera de etapa: E3 / E4. | Fuera de etapa (E3 / E4). |
| **NUEVA N18** | 249-266 | Para el error #18 hace falta localizar la **última versión existente** de un FI (para abrirla y actualizarla); la función solo da la siguiente ruta libre. Además, si el nombre base ya trae ` v2`, el resultado sería ` v2 v2`. | Error #18, §3.2 formato 3 | Fuera de etapa: E3 (función hermana `obtener_ultima_version`). | Fuera de etapa (E3). |
| **NUEVA N19** | 48 | Sin medida (D1), el hallazgo dice "Pendiente de verificación de medida en campo" con `conforme=True`. Si en E3 todo texto "pendiente" se envía a "Con dudas", contradiría la decisión D1. | D1 (respuesta de Steven) | Observación para E3; T4 no lo cambia (D1 queda como está). | **Sin tocar** (observación O12 para E3). |


---

## 5. Índice de pruebas propuestas para T3 / T5

Todas en `BACKEND/tests/test_reglas_ingenieria.py`, con valores sintéticos marcados `# SINTÉTICO: no es dato de proyecto` (P11). Los nombres coinciden con los implementados; la suite tiene además pruebas añadidas en T4/T4b/T5 (ver §2 y §7).

- **Recubrimientos (§4.5):** `test_recubrimiento_zapatas_y_muro_contencion_0075`, `test_recubrimiento_columnas_vigas_riostras_muros_ha_0040`, `test_recubrimiento_losas_y_escaleras_0025`, `test_recubrimiento_alias_escalera`, `test_recubrimiento_alias_columna_circular_viga_amarre`, `test_recubrimiento_normaliza_tildes`, `test_recubrimiento_tipo_desconocido_pendiente`, `test_recubrimiento_metalicos_pendiente`. Añadidas en T4 (N3, N15): `test_recubrimiento_tabla_categorias`, `test_recubrimiento_nombres_genericos`, `test_recubrimiento_platea_0075`.
- **Medida en obra (§4.5):** `test_medida_obra_sin_medida_conforme_valor_plano`, `test_medida_obra_igualdad_exacta_sin_tolerancia`, `test_medida_obra_tolerancia_de_visita`, `test_medida_obra_discrepancia_no_conforme`, `test_medida_obra_sin_valor_plano_pendiente` (N1).
- **EJES (§4.4):** `test_ejes_cruce_puntual_columna`, `test_ejes_muro_entre_letras_con_coma`, `test_ejes_muro_sin_fila_ni_parentesis`, `test_ejes_viga_recta_sobre_letra`, `test_ejes_tramo_portico`, `test_ejes_losa_guion_largo`, `test_ejes_viga_sin_eje_letra_guion_largo`, `test_ejes_faltan_datos_pendiente`, `test_ejes_caso_desconocido_pendiente`, `test_ejes_argumentos_invertidos_pendiente`, `test_ejes_elemento_unico_en_planta_documentado`. Añadidas en T4b: ver §4.4 (prima, `interpretar_eje_de_visita`, caso `area`).
- **Cuantía (§4.6):** `test_cuantia_formula_as_total_sobre_bh`, `test_cuantia_decimal_vs_porcentaje`, `test_cuantia_tabla_areas_confirmada`, `test_cuantia_diametro_desconocido_error`, `test_cuantia_dimensiones_no_positivas_error`, `test_cuantia_sin_barras_error` (N2), `test_cuantia_cantidad_no_positiva_error` (N2).
- **Log y fotos (§4.7 M1):** `test_log_etiqueta_abre_elemento`, `test_log_fotos_antes_de_primera_etiqueta_reportadas`, `test_log_portico_se_reinicia_con_otro_elemento`, `test_log_tramo_portico_id_formato`, `test_log_p_eje_sin_tramo_no_crea_id_p`, `test_log_p_eje_con_tramo_en_leyenda` (N5), `test_log_tramo_repetido_abre_elementos_separados` (N6, protege la decisión de Steven), `test_fotos_hvlev_todas`, `test_fotos_escalera_max_9_primera_ultima_orden`, `test_fotos_stp_mived_pick4_repartidas`, `test_fotos_stp_mived_una_foto`.
- **Grosor (§4.7 M3):** `test_grosor_formula_4_5_sobre_factor`, `test_grosor_factor_min_ancho_alto`, `test_grosor_minimo_4px`, `test_grosor_datos_invalidos_error`.
- **Versionado y fecha (§5.2):** `test_versionado_libre_mismo_nombre`, `test_versionado_existe_v2`, `test_versionado_existe_v2_da_v3`, `test_versionado_mived_fi_extension_mayuscula`, `test_versionado_no_crea_carpetas`, `test_formatear_fecha_ddmmaaaa`.
- **Auditor (§6):** `test_auditor_8_nombre_con_sufijo`, `test_auditor_8_sotano_con_tilde`, `test_auditor_8_nombre_limpio_ok`, `test_auditor_9_corrido`, `test_auditor_9_recorrido_no_es_corrido` (N8), `test_auditor_9_viga_sin_estribos`, `test_auditor_9_estribos_al_final`, `test_auditor_9_portico_con_tilde` (N10), `test_auditor_9_acero_adicional_mas`, `test_auditor_9_acero_adicional_lineas_separadas_ok`, `test_auditor_estriboss_columna_hvlev`, `test_auditor_estriboss_columna_circular` (N11), `test_auditor_10_cajas_prohibidas`, `test_auditor_10_verificacion_sin_tilde` (N12), `test_auditor_10_nota_pendiente_permitida`, `test_auditor_11_losa_con_ejes`, `test_auditor_11_losa_guion_largo_ok`, `test_auditor_11_muro_con_fila_rechazado` (N13), `test_auditor_fecha_valida_11_09_2026`, `test_auditor_fecha_m_d_aaaa_rechazada`, `test_auditor_fecha_imposible_31_02_rechazada`, `test_auditor_12_fecha_vacia_pendiente` (N14), `test_auditor_16_firma_fabricada`, `test_auditor_16_sin_firma_ok`.
- **T5:** `test_auditor_12_cuantia_no_recalculada`, `test_auditor_12_obra_sin_correccion_recubrimiento`, `test_auditor_15_pdf_mayor_30mb`, `test_auditor_15_destino_ya_existe` (más las demás `test_auditor_12_*` y `test_auditor_15_*` de la suite).

## 6. Preguntas que deja esta matriz para Steven

Preguntas de T2 (todas **respondidas** el 21/10/2026, ver `PLANES/etapa-0.md`):
- ~~**N3:** ¿Se aceptan como alias `ZAPATA`, `COLUMNA`, `VIGA`, `VIGA DE HORMIGON`, `LOSA`, `MURO H.A.`?~~ **Respondida:** sí para `ZAPATA`, `COLUMNA`, `VIGA`, `LOSA`, `MURO H.A.`, con tabla tipo → categoría de §4.5 (hecho en T4). `VIGA DE HORMIGON` no se mencionó y sigue en "pendiente de verificar".
- ~~**N15:** ¿La `PLATEA` cuenta como losa para `EJES = —`?~~ **Respondida:** no; la platea es cimentación (0.075 m) y sus EJES van como área `(A-B),(1-2)` (hecho en T4 / T4b).

Preguntas abiertas que quedan tras la evaluación (detalle en `PLANES/etapa-0-evaluacion.md`, "Pendientes de verificar"):
- Límite de peso: 30 000 000 bytes (el usado) o 30 MiB = 31 457 280 bytes.
- ¿CATDIC escribe decimales con coma (`0,40`)? Hoy van a "pendiente de verificar".
- ¿Existen ejes de varias letras (`AB`) o con `Ñ`? El código los acepta (O6).
- ¿Solo comilla recta `'` como prima, o también `’` y `′`? (O7).
- Una etiqueta `Tramo n-n` sin `P eje X` previo, ¿va a "Con dudas"? (O5).
- N19: cómo se enruta en la Etapa 3 el texto "Pendiente de verificación de medida en campo" con `conforme=True` (D1).

---

## 7. Estado tras T4/T4b/T5

Cobertura final del auditor preliminar (`auditar_datos_ficha_antes_de_renderizar` y `auditar_archivo_pdf_generado`) y de las funciones de apoyo frente a los 18 errores del CLAUDE.md §6. Coherente con la evaluación del 21/10/2026 (`PLANES/etapa-0-evaluacion.md`). Actualiza la tabla "Cobertura actual del auditor preliminar" de `PLANES/etapa-0.md` (líneas 48-60, que no se edita aquí), que refleja el estado anterior a T4 (p. ej. allí #15 figura como "No cubierto").

| # | Error | Estado | Qué lo cubre en E0 (función / prueba) | Lo que falta | Etapa responsable |
|---|---|---|---|---|---|
| 1 | LOCALIZACION con recorte o nivel equivocado | fuera de etapa | — | Todo (requiere imagen) | E3 / E4 |
| 2 | DETALLE con foto de campo / recorte ilegible | fuera de etapa | — | Todo (requiere imagen) | E3 / E4 |
| 3 | Cuadrícula de fotos con franjas, sin gutter o incompleta | fuera de etapa | Apoyo indirecto: `seleccionar_fotos_m1`, `seleccionar_fotos_pick4` eligen qué fotos entran | Recorte *cover* y cuadrícula | E3 / E4 |
| 4 | Recuadro rojo invisible a tamaño final | parcial (solo apoyo de cálculo) | `calcular_grosor_recuadro_rojo` (`test_grosor_*`) | Dibujar el recuadro y verificar su visibilidad en el PDF | E3 / E4 |
| 5 | `LEVANTAMIENTO` descentrado / logos HV desalineados | fuera de etapa | — | Todo (maquetación) | E4 |
| 6 | Bloques 1 y 2 de igual altura (debe ser 1.6 : 1) | fuera de etapa | — | Todo (maquetación) | E4 |
| 7 | `NIVEL` mal ubicado según formato | fuera de etapa | — | Todo (maquetación) | E4 |
| 8 | NOMBRE PROYECTO con sufijos en HV-LEV | parcial | Lista de sufijos sin tildes (`test_auditor_8_*`) | No detecta códigos de nivel tipo `S4` o `E-9` (`"Terra Living S4"` pasa, O11) | E3 |
| 9 | `CORRIDO`; viga sin `ESTRIBOS`; `ACERO ADICIONAL` con `+` | cubierto en lo verificable por datos | Palabra completa `CORRIDO(S)`, `ESTRIBOS` obligatorio y al final, `PÓRTICO` con tilde, `ACERO ADICIONAL` + `"+"`, `ESTRIBOSS` en columnas HV-LEV (`test_auditor_9_*`, `test_auditor_estriboss_*`) | Solo lee `observaciones_texto` (N9); no cubre `CORRIDA` (O11) | E3 (campos de la tabla de armado) |
| 10 | Cajas editoriales prohibidas | cubierto en lo verificable por datos | Las 3 frases del §6 sin tildes; `NOTA PENDIENTE` permitida (P7) (`test_auditor_10_*`) | — | — |
| 11 | Ejes de losa ≠ `—` o eje por proximidad visual | cubierto en lo verificable por datos | Losa = `—`; muro sin `FILA` ni paréntesis (N13); platea con área `(A-B),(1-2)` (T4b) (`test_auditor_11_*`) | "Eje deducido por proximidad visual" no es verificable con datos | E3 (origen de los ejes en la ingesta) |
| 12 | Cuantía copiada; fecha M/D/AAAA; OBRA sin corrección | cubierto | Fecha obligatoria y real `DD/MM/AAAA` (D10, N14); cuantía recalculada con unidad por formato (T5); columna OBRA coherente con `evaluar_medida_acero_obra` y la tolerancia de la visita (T5) (`test_auditor_fecha_*`, `test_auditor_12_*`) | Observación O8: una fecha que no es texto lanza `TypeError` en vez de reportar #12 | E3 (conectar al generador) |
| 13 | Mezclar cabeceras/rótulos entre formatos | fuera de etapa | — | `formato` no se valida contra los 7 IDs (O11); maquetación | E3 / E4 |
| 14 | Cabeceras CATDIC-STP superpuestas o en 2 líneas | fuera de etapa | — | Todo (overlay PDF) | E3 |
| 15 | PDF > 30 MB o sobrescritura sin `v2` | cubierto | `obtener_ruta_salida_sin_sobrescribir` (sin `mkdir`, D9) y `auditar_archivo_pdf_generado`: peso ≥ 30 000 000 bytes, destino que ya existía, destino no registrado → pendiente, PDF inexistente (`test_versionado_*`, `test_auditor_15_*`) | Confirmar 30 MB frente a 30 MiB (pregunta abierta) | E3 / E4 (llamarlo tras generar) |
| 16 | Firmas fabricadas o previas no borradas en FI | parcial | Campos de firma en la ficha (`test_auditor_16_*`) | Borrar firmas previas del PDF base con PyMuPDF | E3 |
| 17 | Mampostería marcada / faltan `"Sí"` obligatorios en FI | fuera de etapa | — | Todo (generador FI) | E3 |
| 18 | Rehacer un FI MIVED existente en vez de actualizarlo | fuera de etapa | — | Localizar la última versión existente (N18) | E3 |

**Resumen:** cubiertos #12 y #15; cubiertos en lo verificable por datos #9, #10 y #11; parciales #8, #16 y #4 (este solo con el apoyo del cálculo de grosor); fuera de etapa #1–#3, #5–#7, #13, #14, #17 y #18 (Etapas 3 y 4).
