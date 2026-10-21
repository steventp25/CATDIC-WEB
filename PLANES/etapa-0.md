# Etapa 0 — Auditoría y pruebas del motor de reglas `BACKEND/reglas_ingenieria.py`
Estado: APROBADO (Steven, 21/10/2026) · Evaluación interna: APROBADO (21/10/2026, etapa-0-evaluacion.md).

## Respuestas de Steven (21/10/2026)
- **D1 → NO es error.** Norma de trabajo CATDIC: sin medida en obra, OBRA = valor del plano y se da por conforme; las incongruencias se registran en la visita. T3 prueba el comportamiento actual y T4 **no** lo cambia.
- **P1:** sí, commit del archivo original antes de T4.
- **P2:** la tolerancia se define en cada visita. T4: `tolerancia_m` deja de tener valor fijo de 0.005 y llega como dato de la visita; si la visita no la trae, se compara con igualdad exacta (§4.5).
- **P3:** PLATEA 0.025 y PÓRTICO 0.040 son correctos. Falta aclarar la lista de nombres de tipo (pregunta reformulada abajo).
- **P5:** sí, cuantía en % con 2 decimales.
- **P6:** se documenta el caso `elemento_unico_en_planta` (docstring + prueba) en lugar de eliminarlo.
- **P8:** a criterio del planificador. Decisión: con datos inválidos → `ValueError` ("pendiente de verificar"), sin número fijo; factor = el menor entre ancho y alto (planta encajada completa); se mantiene el mínimo de 4 px.
- **P10 / T1:** pytest 9.1.1 instalado en el Python global (verificado). No hace falta más instalación; T1 solo crea `requirements-dev.txt` y `pytest.ini`.
- **P3 (nombres de tipo):** faltan tipos y se irán agregando con el tiempo. En esta etapa T4 solo agrega los que caben en una categoría que §4.5 ya define: `ESCALERA` (escaleras, 0.025), `COLUMNA CIRCULAR` (columnas, 0.040), `VIGA DE AMARRE` (vigas, 0.040), y normaliza tildes (`MURO DE CONTENCIÓN` = `MURO DE CONTENCION`, `PÓRTICO` = `PORTICO`). Perfiles metálicos, conexiones metálicas y metaldeck **no** reciben recubrimiento: siguen devolviendo "pendiente de verificar" hasta que se definan sus reglas (fuera de alcance).
- **P4:** la tabla de áreas de barras (3/8" 0.71 … 1-3/8" 10.06 cm²) es correcta. D5 queda cerrado.
- **P7:** se quita `"NOTA PENDIENTE"` de la lista de cajas prohibidas (T4).
- **P9:** la convención del log es correcta: la etiqueta abre el elemento y en pórticos se usa `P eje X` + `Tramo n-n`.
- **P11:** se aceptan valores sintéticos en las pruebas, marcados `# SINTÉTICO: no es dato de proyecto`.
- **P12:** no hay "Archivos 01/02/08"; la única fuente es el CLAUDE.md. T4 cambia esas referencias en los comentarios por la sección del CLAUDE.md que corresponde.
- **Todas las preguntas quedan respondidas.**

## Objetivo
Que `BACKEND/reglas_ingenieria.py` (ya existente, 325 líneas) quede **contrastado contra el CLAUDE.md §4, §5 y §6**, cubierto por pruebas `pytest` basadas solo en ejemplos del CLAUDE.md, y corregido donde las pruebas demuestren que se aparta de la especificación. Al terminar, `python -m pytest` en `BACKEND/` pasa en verde y está documentado qué errores de los 18 cubre el auditor preliminar y cuáles quedan para las etapas 3 y 4.

## Discrepancias CLAUDE.md vs repositorio

### Estado del repositorio
- **R1.** El CLAUDE.md §2 da `reglas_ingenieria.py` por existente y `PLANES/README.md` dice que "no está en el repositorio". Realidad: el archivo **sí existe en disco pero está sin trackear** en git (`?? BACKEND/reglas_ingenieria.py`). No lo escribió Claude.
- **R2.** Nadie lo importa todavía: `BACKEND/main.py` no usa el motor de reglas (línea 110: "Aquí se conectará el motor de reglas…"). Conectarlo queda para la Etapa 3.
- **R3.** No existe `BACKEND/tests/`, ni `requirements*.txt`, ni configuración de pytest. **`pytest` no está instalado** (`No module named pytest`). Python real: **3.14.7** (único intérprete, `py -0`). FastAPI 0.156.8 sí está instalado.
- **R4.** Los comentarios del archivo citan "Archivo 01 / 02 / 08" (documentos externos que no están en el repo). La fuente de verdad para esta etapa es el CLAUDE.md.

### Contraste función por función (lo que ya se ve al leer el código)

| # | Función | Regla CLAUDE.md | Hallazgo |
|---|---|---|---|
| D1 | `evaluar_medida_acero_obra` | §4.5, Regla de Oro, error #12 | **Grave.** Si `medida_acero_campo_m is None` devuelve `conforme: True` y `valor_columna_obra_m = valor_plano`. Sin medida no hay conformidad: debe quedar `"pendiente de verificar"` (y no copiar el valor del plano a OBRA). |
| D2 | `evaluar_medida_acero_obra` | §4.5 (`medida_campo + 2*rec == valor_plano`) | Usa `tolerancia_m = 0.005` por defecto. El CLAUDE.md pide igualdad; la tolerancia no está documentada → pregunta P2. |
| D3 | `RECUBRIMIENTO_POR_LADO_M` | §4.5 | Los valores 0.075 / 0.040 / 0.025 coinciden. Pero: `PLATEA` = 0.025 y `PORTICO` = 0.040 no están listados en el CLAUDE.md (P3); "escaleras" solo existe como `RAMPA DE ESCALERA`; las claves no admiten tildes (`MURO DE CONTENCIÓN`, `PÓRTICO` lanzarían error). |
| D4 | `formatear_campo_ejes` | §4.4, error #11 | Los 4 formatos y el `—` de losas / vigas sin eje-letra coinciden con los ejemplos. Sobra el caso `elemento_unico_en_planta`, que **no existe en el CLAUDE.md** (P6). No valida que la letra sea letra y el número sea número (argumentos invertidos pasan sin aviso). |
| D5 | `calcular_cuantia_elemento` | §4.6, error #12 | Fórmula `As_total/(b*h)` correcta; decimal con 4 cifras (`0.0185`) y % con 2 (`1.85`). La tabla `AREA_BARRA_CM2` **no está en el CLAUDE.md** (coincide con áreas nominales ASTM, pero hay que confirmarla: P4). Decimales del % sin documentar (P5). |
| D6 | `agrupar_log_fotografico_visita` | §4.7 M1 | Agrupación secuencial correcta en lo básico, pero: (a) las fotos **antes de la primera etiqueta se descartan en silencio** (deberían reportarse como duda); (b) `portico_activo` **nunca se reinicia**: tras un pórtico, una leyenda con "Tramo" en otro elemento abre un tramo falso; (c) una etiqueta `P eje X` sin tramo crea un elemento con `id_sugerido = "P"`; (d) el formato del log (`archivo`, `etiqueta_elemento`, `leyenda`) y la convención `P eje X` / `Tramo n-n` no están documentados (P9). |
| D7 | `seleccionar_fotos_m1` | §4.7 M1 | Cubre HV-LEV (todas; escaleras máx. 9 repartidas). **Falta `pick4` de STP-MIVED** (hasta 4 repartidas en la secuencia, o 1 grande). Solo reconoce el tipo exacto `RAMPA DE ESCALERA`. |
| D8 | `calcular_grosor_recuadro_rojo` | §4.7 M3, error #4 | Fórmula `4.5 / factor` correcta. Pero con datos inválidos **devuelve 20** (número no documentado) y aplica un mínimo de 4 px no documentado (P8). El factor se calcula solo por alto; si la planta se encaja por ancho, el grosor sale mal. |
| D9 | `obtener_ruta_salida_sin_sobrescribir` | §5.2, error #15 | Sufijos ` v2` / ` v3` correctos. Efecto secundario: **crea la carpeta** (`mkdir`) al solo consultar la ruta, lo que escribiría en Dropbox. |
| D10 | Fechas | §5.2, error #12 | No hay función que formatee `DD/MM/AAAA`; solo se valida en el auditor, con una regex que acepta fechas imposibles (`31/02/2026`). |
| D11 | `auditar_datos_ficha_antes_de_renderizar` | §6 | Cobertura parcial (ver tabla siguiente). Además: `"NOTA PENDIENTE"` está en la lista de cajas prohibidas sin estar en el error #10 (P7); el error #8 no detecta `SÓTANO` con tilde; el chequeo `ESTRIBOSS` distingue mayúsculas y los demás no; "ESTRIBOS al final" solo comprueba que aparezca, no que sea lo último. |

### Cobertura actual del auditor preliminar frente a los 18 errores
> Tabla de la planificación (antes de T4). El estado final tras T4/T4b/T5 está en `etapa-0-matriz-reglas.md` §7 (#12 y #15 ya cubiertos).


| Error | Estado | Nota |
|---|---|---|
| #8 | Parcial | Lista de palabras; falla con tildes. |
| #9 | Cubierto | `CORRIDO`, `ESTRIBOS`, `ACERO ADICIONAL` + `"+"`. Falta comprobar que `ESTRIBOS` va al final. |
| #10 | Cubierto (+1 extra no documentado) | `NOTA PENDIENTE` (P7). |
| #11 | Parcial | Losa ≠ `—`. El "eje deducido por proximidad visual" no es verificable con datos. |
| #12 | Parcial | Solo fecha. Faltan cuantía recalculada y columna OBRA corregida por recubrimiento (verificables con datos → T5). |
| #15 | No cubierto | Peso > 30 MB y sobrescritura: verificable sobre el archivo → T5. |
| #16 | Parcial | Solo marca campos de firma en el diccionario; borrar firmas del PDF base es del generador FI (Etapa 3). |
| #1–#7, #13, #14 | No cubiertos | Requieren imagen/maquetación: Etapas 3–4 (generadores). |
| #17, #18 | No cubiertos | Dependen del generador FI MIVED: Etapa 3. |

## Tareas

### T1 — Entorno de pruebas
- Estado: APROBADA · commit 633e5ac. `pytest.ini` carga bien; el aviso "No files were found in testpaths" desaparecerá cuando T3 cree `BACKEND/tests/` (re-verificar tras T3).
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/requirements-dev.txt` (nuevo), `BACKEND/pytest.ini` (nuevo)
- Depende de: — (y de la respuesta a P10)
- Qué hacer: instalar `pytest` en el Python 3.14.7 (o en el entorno que Steven indique en P10); listar `pytest` en `requirements-dev.txt`; crear `pytest.ini` con `testpaths = tests` y `pythonpath = .` (el backend usa imports planos como `from database import …`).
- Criterios de aceptación:
  - [ ] `python -m pytest --version` imprime una versión.
  - [ ] Desde `BACKEND/`, `python -m pytest` arranca y encuentra la carpeta `tests` (sin errores de configuración).
- Reglas del CLAUDE.md que aplican: §1.5 (offline).

### T2 — Matriz de cobertura de reglas
- Estado: APROBADA · commit "Etapa 0 · T2/T6" (este mismo cambio de PLANES/). 19 discrepancias NUEVAS (N1–N19) en `etapa-0-matriz-reglas.md`; las marcadas "T4" requieren visto bueno de Steven para entrar en T4 (amplían su alcance).
- Ejecutor: ejecutor-backend
- Archivos: `PLANES/etapa-0-matriz-reglas.md` (nuevo)
- Depende de: —
- Qué hacer: confirmar o corregir, leyendo el código, la tabla D1–D11 y la de cobertura de los 18 errores de este plan; por cada regla de §4, §5.2 y §6 indicar función que la implementa, estado (cubierta / parcial / falta / fuera de etapa) y la prueba de T3 que la verificará. No modifica código.
- Criterios de aceptación:
  - [ ] Cada uno de los 18 errores de §6 y cada punto de §4.4–§4.7 y §5.2 aparece en la matriz con estado y etapa responsable.
  - [ ] Toda discrepancia nueva que no esté en D1–D11 queda marcada como `NUEVA`.
- Reglas del CLAUDE.md que aplican: §4, §5.2, §6.

### T3 — Pruebas `pytest` del motor de reglas
- Estado: APROBADA · commit 3b8393a (234 pruebas en verde al cerrar la etapa). 141 pruebas: 93 pasan, 48 fallan; todas las que fallan citan su D#/P#/N# y se corrigen en T4. Valores marcados `SINTÉTICO` o `NORMA: CLAUDE.md §x / respuesta Px`. Sin pruebas para N3 y N15 (pendientes de Steven).
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/tests/test_reglas_ingenieria.py` (nuevo)
- Depende de: T1, T2
- Qué hacer: escribir pruebas que expresen **lo que exige el CLAUDE.md** (no lo que hace el código hoy). Casos tomados solo del CLAUDE.md:
  - Recubrimientos: zapatas y muros de contención 0.075; columnas, vigas, riostras, muros H.A. 0.040; losas y escaleras 0.025; tipo desconocido → `ValueError` con "pendiente de verificar".
  - EJES: `EJE F-11`, `EJE D-E,4`, `EJE C, ENTRE 2-3`, `EJE F ENTRE 10-11`; losa y viga sin eje-letra → `—`; faltan datos → `"pendiente de verificar"`; nunca aparecen `FILA` ni paréntesis en muros.
  - Medida en obra: sin medida → OBRA = valor del plano, conforme (norma CATDIC, ver respuesta a D1); tolerancia recibida de la visita y, si no llega, igualdad exacta (P2); con medida que más `2*rec` iguala el plano → conforme y OBRA = valor del plano.
  - Cuantía: relación decimal ↔ % (`0.0185` ↔ `1.85`), fórmula `As_total/(b*h)`, diámetro desconocido → `ValueError`, dimensiones ≤ 0 → `ValueError`.
  - Log fotográfico: una etiqueta abre el elemento y las fotos siguientes sin etiqueta le pertenecen; fotos antes de la primera etiqueta no se pierden (D6a); el pórtico se reinicia al abrir otro elemento (D6b); tramo de pórtico con id del estilo `A (2-3)`.
  - Selección de fotos: HV-LEV todas; escaleras máx. 9 conservando primera, última y orden; STP-MIVED hasta 4 repartidas (D7).
  - Grosor: `grosor_fuente = 4.5 / factor`; datos inválidos → error, no un número fijo (D8, según P8).
  - Versionado (con `tmp_path`): nombres de ejemplo `Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026.pdf` y `MIVED - TERRA LIVING-LOSAS Y VIGAS PARCIAL SOTANO -3.PDF`; libre → mismo nombre; existe → ` v2`; existe v2 → ` v3`; consultar no crea carpetas (D9).
  - Auditor: cada chequeo existente en positivo y negativo; fecha `11/09/2026` válida, `9/11/2026` y `31/02/2026` rechazadas.
  - Para dimensiones y barras se usan **valores sintéticos de prueba** declarados como tales en constantes con comentario `# SINTÉTICO: no es dato de proyecto` (ver P11); nada se guarda en la BD.
  - Los casos siguen las respuestas de Steven de este plan (D1, P2–P9, P11).
- Criterios de aceptación:
  - [ ] `python -m pytest -v` desde `BACKEND/` ejecuta todas las pruebas; el reporte lista cuáles fallan.
  - [ ] Cada prueba que falla corresponde a una discrepancia D# de este plan o a una `NUEVA` de T2 (se anota en el reporte).
  - [ ] `grep` sobre el archivo de pruebas no encuentra valores de ingeniería sin el comentario `SINTÉTICO`.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §4.4–§4.7, §5.2, errores #9–#12, #15.

### T4 — Correcciones del motor de reglas
- Estado: APROBADA · commit 3b8393a. 148 pruebas en verde; `import main` OK. Cambio de interfaz: `calcular_grosor_recuadro_rojo` ahora recibe ancho y alto de fuente y celda; `obtener_ruta_salida_sin_sobrescribir` ya no crea la carpeta (la creará el generador). Sin tocar: N4, N7, N19.
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/reglas_ingenieria.py`, `BACKEND/tests/test_reglas_ingenieria.py` (solo para N3, N6 y N15 según respuestas de Steven)
- Depende de: T3 y respuestas de Steven a P1–P9 (y del commit previo del archivo original si P1 = sí)
- Qué hacer: corregir solo lo que las pruebas de T3 demuestran fuera de especificación (D1 queda como está por decisión de Steven): D2 (tolerancia como dato de la visita), D3 (normalizar tildes / alias de tipo), D4 (quitar o documentar `elemento_unico_en_planta` según P6), D6 a–c, D7 (`pick4` para STP-MIVED), D8, D9 (sin `mkdir` al consultar), D10 (función `formatear_fecha_ddmmaaaa` y validación real de fecha), D11 (tildes en #8, `ESTRIBOSS` sin distinguir mayúsculas, `ESTRIBOS` al final, quitar `"NOTA PENDIENTE"` por P7). D3 con los alias de P3. Referencias "Archivo 01/02/08" → sección del CLAUDE.md (P12). Mantener nombres de funciones y estilo existentes (español, `snake_case`).
- Criterios de aceptación:
  - [ ] `python -m pytest -v` desde `BACKEND/` en verde (0 fallos).
  - [ ] `git diff BACKEND/reglas_ingenieria.py` solo contiene cambios trazables a un D# o a una respuesta P#.
  - [ ] `BACKEND/main.py` sigue arrancando: `python -c "import main"` desde `BACKEND/` sin error.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §4.4–§4.7, §5.2, errores #8–#12, #15.

### T4b — Ejes con prima, ejes leídos de la visita y EJES de platea
- Estado: APROBADA · commit 3b8393a. 234 pruebas en verde. Solo acepta la comilla recta `'` como prima (la curva `’` y `′` → "pendiente de verificar"); admite ejes de varias letras (`AB`).
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/reglas_ingenieria.py`, `BACKEND/tests/test_reglas_ingenieria.py`
- Depende de: T4, T5 (mismos archivos) y respuestas de Steven (ejes con prima, platea)
- Qué hacer: (1) aceptar prima en los ejes (`A'`, y también en números, p. ej. `2'`) en `formatear_campo_ejes`; (2) función `interpretar_eje_de_visita("A1" | "1A" | "A'1")` → (letra, número) para el cruce puntual, aceptando ambos órdenes; lo ambiguo → "pendiente de verificar"; (3) caso de EJES `area` → `(A-B),(1-2)` para PLATEA; el auditor no exige `—` a la platea y rechaza en platea un formato que no sea de área.
- Criterios de aceptación:
  - [ ] `formatear_campo_ejes("cruce_puntual", "A'", eje_num_1="1")` → `EJE A'-1`.
  - [ ] `interpretar_eje_de_visita("A1")` y `("1A")` → `("A", "1")`.
  - [ ] Caso `area` con A, B, 1, 2 → `(A-B),(1-2)`.
  - [ ] `python -m pytest` desde `BACKEND/` en verde; `import main` OK.
- Reglas del CLAUDE.md que aplican: §4.4, error #11; respuestas de Steven.

### T5 — Ampliar el auditor preliminar con errores verificables por datos
- Estado: APROBADA · commit 3b8393a. 181 pruebas en verde. Nuevas: chequeos #12 (cuantía recalculada, columna OBRA) dentro del auditor y `auditar_archivo_pdf_generado(ruta_pdf, destino_existia_antes)` para #15. Claves nuevas de ficha (contrato para Etapa 3): `cuantia_declarada`, `seccion_b_m`, `seccion_h_m`, `barras_longitudinales`, `medidas_obra`, `tolerancia_visita_m`.
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/reglas_ingenieria.py`, `BACKEND/tests/test_reglas_ingenieria.py`
- Depende de: T4
- Qué hacer: añadir al auditor (o a una función hermana `auditar_archivo_pdf_generado`) los chequeos que se pueden hacer sin imagen: #12 cuantía de la ficha = cuantía recalculada con `calcular_cuantia_elemento`; #12 columna OBRA coherente con `evaluar_medida_acero_obra`; #15 PDF > 30 MB y archivo destino ya existente. Cada chequeo con su prueba.
- Criterios de aceptación:
  - [ ] Pruebas nuevas para #12 (cuantía y OBRA) y #15 (peso con archivo temporal > 30 MB simulado y existencia previa) pasan.
  - [ ] `python -m pytest -v` en verde.
- Reglas del CLAUDE.md que aplican: §4.5, §4.6, §5.2, errores #12 y #15.

### T6 — Actualizar la línea de Etapa 0 en `PLANES/README.md`
- Estado: APROBADA · commit "Etapa 0 · T2/T6" (este mismo cambio de PLANES/).
- Ejecutor: ejecutor-backend
- Archivos: `PLANES/README.md`
- Depende de: —
- Qué hacer: cambiar la línea "Etapa 0" para decir que el archivo existe (llegó sin trackear) y que la etapa consiste en auditarlo, probarlo y corregirlo, con enlace a `PLANES/etapa-0.md`.
- Criterios de aceptación:
  - [ ] `grep "no está en el repositorio" PLANES/README.md` no devuelve nada.
  - [ ] La línea enlaza a `etapa-0.md`.
- Reglas del CLAUDE.md que aplican: §2 (estado del repositorio).

## Paralelismo
- **T1, T2 y T6** pueden correr a la vez (archivos distintos, sin dependencias).
- **T3** espera a T1 y T2.
- **T4** espera a T3 y a las respuestas de Steven. **T5** espera a T4 (mismo archivo).
- T4 y T5 tocan `reglas_ingenieria.py`, y T3 y T5 tocan el archivo de pruebas: nunca en paralelo.

## Pendientes de verificar / preguntas para Steven
- **Surgidas en T2 — respuestas de Steven (21/10/2026):**
  - **N6 → NO es error:** se mantiene que un mismo tramo pueda abrir varios elementos (hay elementos grandes o complejos). La prueba `test_log_tramo_repetido_no_duplica` se invierte en T4 para proteger ese comportamiento.
  - **N3 → sí:** se aceptan `ZAPATA`, `COLUMNA`, `VIGA`, `LOSA`, `MURO H.A.`; "hay que definir qué tipo son": T4 agrega una tabla explícita tipo → categoría de §4.5 (zapatas/muros de contención 0.075; columnas/vigas/riostras/muros H.A. 0.040; losas/escaleras 0.025) y el recubrimiento sale de la categoría.
  - **N15 → PLATEA = 0.075 m** (cimentación), corrige la respuesta anterior a P3. Al no ser losa, el error #11 no le aplica. Formato de EJES de la platea: no definido en el CLAUDE.md → pendiente de verificar.
  - **Ejes con prima → sí existen** (`A'`). Respuesta de Steven: si en la visita el elemento dice solo `A1` o `1A`, significa que está en el cruce de los ejes A y 1 (el orden letra/número suele venir cruzado). → T4b.
  - **EJES de la PLATEA → como área**, ejemplo de Steven: `(A-B),(1-2)`. Las losas siguen con `—`: en las visitas no se ubican porque en planta hay una sola por entrepiso. → T4b.
  - **Pendiente (salió en T5):** límite de peso tomado como 30 000 000 bytes (lectura estricta de "30 MB"); ¿o 30 MiB = 31 457 280?
  - **Pendiente (salió en T5):** ¿CATDIC escribe valores con coma decimal (`0,40`)? Hoy van a "pendiente de verificar".
  - Las demás NUEVAS marcadas T4 (N1, N2, N5, N8, N10–N14) entran en T4 (Steven no objetó ninguna al revisar la lista).

- **P1.** ¿Commiteamos primero `reglas_ingenieria.py` **tal cual llegó** (antes de T4), para que Gemini vea en el diff exactamente qué se corrigió? (Recomendado: sí.)
- **P2.** Tolerancia de comparación medida-en-obra vs. plano: el código usa ±0.005 m y el CLAUDE.md dice igualdad. ¿Qué tolerancia usa CATDIC?
- **P3.** `PLATEA` está con 0.025 m (como losa) y `PORTICO` con 0.040 m; ninguno aparece en §4.5. ¿Son correctos? ¿Qué otros nombres de tipo usan (p. ej. `ESCALERA`, `COLUMNA CIRCULAR`)?
- **P4.** La tabla de áreas de barras (`#3` 0.71 cm² … `#11` 10.06 cm²) no está en el CLAUDE.md. ¿Es la tabla oficial a usar, o hay otra fuente?
- **P5.** Cuantía en `CATDIC-STP`: ¿2 decimales en % (`1.85`)?
- **P6.** El caso de EJES `elemento_unico_en_planta` no existe en el CLAUDE.md. ¿Se elimina o se documenta (y cómo se formatea)?
- **P7.** `"NOTA PENDIENTE"` está como caja prohibida pero no figura en el error #10. ¿Se mantiene?
- **P8.** Grosor del recuadro rojo: con datos inválidos el código devuelve 20 y aplica mínimo 4 px. Propuesta: lanzar error con datos inválidos y calcular el factor con ancho y alto. ¿De acuerdo? ¿Se mantiene el mínimo?
- **P9.** ¿Existe una muestra real del log fotográfico de la app CATDIC (claves, convención `P eje X` / `Tramo n-n`)? Sin ella, las pruebas del log solo verifican la estructura con nombres de archivo ficticios.
- **P10.** ¿Instalo `pytest` en el Python global 3.14.7 o prefieres un entorno virtual (`.venv`) en el proyecto?
- **P11.** Para probar medida en obra y cuantía no hay valores de ejemplo en el CLAUDE.md. ¿Aceptas valores sintéticos marcados `SINTÉTICO` en las pruebas, o prefieres darme un caso real (p. ej. un elemento de Terra Living con plano, medida y barras)?
- **P12.** Los comentarios citan "Archivo 01 / 02 / 08". ¿Existen esos documentos en algún lugar para contrastar?

## Fuera de alcance de esta etapa
- Reglas para perfiles metálicos, conexiones metálicas y metaldeck (P3): se agregarán cuando Steven las defina.
- Conectar el motor de reglas a `main.py` / "Procesar Cola" (Etapa 3).
- Errores #1–#7, #13, #14, #16 (parte PDF), #17, #18: dependen de los generadores (Etapas 3 y 4).
- Sincronizador de Dropbox e importador de diseño (Etapas 1 y 2).
- `BACKEND/catdic_local.db` está trackeado en git y no está en `.gitignore`; decidir si debe versionarse es otro tema.
- Commits y push: los hace `/evaluar` con confirmación de Steven.
