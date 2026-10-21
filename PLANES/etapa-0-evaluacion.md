# Evaluaciones — Etapa 0

## Evaluación del 21/10/2026

## Evaluación — Etapa 0: Auditoría y pruebas del motor de reglas `BACKEND/reglas_ingenieria.py` (T1, T2, T3, T4, T4b, T5, T6)
**Veredicto: APROBADO**

No hay bloqueantes: no hay datos de ingeniería inventados, la suite pasa en verde, `import main` funciona y nada prohibido entra al commit. Hay observaciones que conviene resolver antes del commit (sobre todo O1 y O2), porque son lo primero que Gemini vería al contrastar con el CLAUDE.md.

### Bloqueantes
- Ninguno.

### Observaciones (no bloquean)
- **O1 [`BACKEND/reglas_ingenieria.py:36`] PLATEA = 0.075 no figura en CLAUDE.md §4.5.** La decisión de Steven (N15) solo está en `PLANES/etapa-0.md`. El §4.4 sí se actualizó con el formato de área de la platea, pero el §4.5 no. Gemini audita contra el CLAUDE.md y puede marcarlo como "recubrimiento no documentado". Recomendación: con el visto bueno de Steven, añadir "Platea (cimentación): 0.075 m" al §4.5. Ejecutor: planificador o Steven (es el CLAUDE.md).
- **O2 [N6 frente a CLAUDE.md §4.3] El mismo tramo puede abrir varios elementos.** `test_log_tramo_repetido_abre_elementos_separados` protege que `A (2-3)` salga dos veces. Es decisión válida de Steven, pero el texto literal de §4.3 dice "cada tramo entre ejes es un elemento singular". Sin nota en el CLAUDE.md, Gemini lo leerá como violación de §4.3. Recomendación: documentar la excepción en §4.3 (o citar el plan en el docstring de `agrupar_log_fotografico_visita`, que ya menciona N6).
- **O3 [`PLANES/etapa-0-matriz-reglas.md`] La matriz T2 quedó desactualizada frente a las respuestas de Steven:**
  - N3 dice "No se corrige en T4", pero Steven dijo que sí y T4 lo hizo.
  - N6 propone "si el tramo es el mismo se agrega al elemento actual", lo contrario de lo decidido.
  - N15 sigue en "PLATEA 0.025 / pendiente".
  - La línea 80 y el §5 citan `test_log_tramo_repetido_no_duplica`, que ya no existe (se renombró a `..._abre_elementos_separados`).
  - El §6 lista preguntas ya respondidas.
  - No recoge los 3 puntos nuevos del §4.4 (platea como área, ejes con prima, lectura A1/1A).

  Tampoco hay una tabla final de cobertura de los 18 errores después de T4/T5. El objetivo del plan pide dejar "documentado qué errores de los 18 cubre el auditor"; hoy eso se deduce de la columna "Etapa", y la tabla del plan (líneas 48-60) sigue diciendo "#15 No cubierto". Recomendación: añadir al final de la matriz una sección "Estado tras T4/T5/T4b". Ejecutor: ejecutor-backend (solo documentación).
- **O4 [`BACKEND/tests/test_reglas_ingenieria.py`] Docstrings obsoletos.** Unas 40 pruebas dicen "Falla hasta T4", "hoy default 0.005", "Firma propuesta para T4" o "Todas fallan por firma hasta T4 (hoy recibe solo altos)" (p. ej. líneas 218, 224, 278, 288, 330, 409, 517, 610, 640, 730, 753-756, 805, 862, 875, 900, 923, 944, 951, 977, 983, 1003, 1009, 1066, 1092, 1097). Ya no es cierto: confunde a quien audite. Ejecutor: ejecutor-backend.
- **O5 [`BACKEND/reglas_ingenieria.py:318-333`] Etiqueta `Tramo 3-4` sin pórtico abierto.** Crea un elemento con `id_sugerido = "TRAMO"` y `duda = None` (verificado). Es un identificador sin base que no va a "Con dudas". Ya pasaba en el original y no está en D6, pero va contra el espíritu de D6c y de la Regla de Oro. Sugerencia: tratarlo como D6c (`id = PENDIENTE` con duda). Puede quedar para cuando haya un log real (P9).
- **O6 [`BACKEND/reglas_ingenieria.py:130`] Ejes más amplios que lo que dijo Steven.** `_PATRON_EJE_LETRA = r"[A-ZÑ]+'?"` acepta ejes de varias letras (`AB`) y `Ñ`, y por eso `interpretar_eje_de_visita("AB12")` devuelve `("AB","12")`. Steven solo dio ejemplos de una letra (`A1`, `1A`, `A'`). Es una decisión del ejecutor: está anotada en el estado de T4b, pero no tiene respuesta de Steven. Pasa a la Mesa de Dudas.
- **O7 [`CLAUDE.md` §4.4, regla "Ejes con prima"] "con comilla recta `'`" es elección del ejecutor.** El código rechaza `’` y `′`. En las respuestas de Steven del plan solo consta "sí existen (`A'`)". Si eso quedó en el CLAUDE.md, conviene que Steven lo confirme expresamente.
- **O8 [`BACKEND/reglas_ingenieria.py:558, 610`] Fecha que no es texto hace fallar el auditor.** Si `fecha` llega como objeto `date`, el auditor lanza `TypeError: expected string or bytes-like object` en lugar de reportar el error #12 (verificado). Conviene devolver "Error #12 … pendiente de verificar" para tipos que no sean `str`.
- **O9 [`BACKEND/reglas_ingenieria.py:103`] `tolerancia_m` negativa no se valida.** Con `-1` y diferencia 0 devuelve `conforme: False` (verificado). Si la tolerancia llega de la visita, un valor < 0 debería dar "pendiente de verificar".
- **O10 [`BACKEND/reglas_ingenieria.py:67`] N4 sin unificar.** El mensaje dice "Pendiente de verificar" con P mayúscula, y el error de dimensiones de cuantía (línea 257) no contiene "pendiente de verificar". Las pruebas lo toleran porque comparan sin distinguir mayúsculas. Si en la Etapa 3 se enruta a "Con dudas" buscando el texto exacto, se pierde.
- **O11 Cobertura del auditor que sigue parcial (dentro de lo esperado, para la Etapa 3):**
  - #8 no detecta códigos de nivel tipo `S4` ni `E-9`: `"Terra Living S4"` pasa sin error (verificado).
  - `formato` no se valida contra los 7 IDs (relacionado con #13): `"FORMATO-INVENTADO"` pasa sin error.
  - #9 solo lee `observaciones_texto` (N9).
  - `\bCORRIDOS?\b` no cubre `CORRIDA`.
- **O12 N19 (para la Etapa 3).** En el caso D1 el hallazgo dice "Pendiente de verificación de medida en campo" con `conforme=True`. Si la Etapa 3 manda a "Con dudas" todo texto que diga "pendiente", contradiría la decisión D1.
- **O13 `BACKEND/catdic_local.db`.** Sigue trackeado desde el commit base y no está en `.gitignore`. No se modificó en esta etapa. Es un tema aparte, ya anotado en el plan.

### Criterios de aceptación

**T1 — Entorno de pruebas**
- [x] `python -m pytest --version` imprime una versión → `pytest 9.1.1`.
- [x] Desde `BACKEND/`, `python -m pytest` encuentra `tests/` sin errores de configuración. `pytest.ini` tiene `testpaths = tests` y `pythonpath = .`; `requirements-dev.txt` tiene `pytest>=9.1`.

**T2 — Matriz de cobertura**
- [x] Los 18 errores del §6 y cada punto del §4.4–§4.7 y §5.2 (del CLAUDE.md vigente cuando se hizo T2) aparecen con estado y etapa responsable. Salvedad (O3): no incluye los 3 puntos del §4.4 añadidos después, y tiene notas desactualizadas.
- [x] Las discrepancias nuevas están marcadas `NUEVA` (N1–N19).

**T3 — Pruebas pytest**
- [x] `python -m pytest -v` ejecuta todas las pruebas.
- [x] Cada prueba que fallaba corresponde a un D#, N#, P#, T4b o T5. Verificado corriendo las pruebas actuales contra el original de `d8e332c` en el scratchpad: 126 fallan, 108 pasan, y todas las que fallan citan D2–D11, N1–N15, P3–P8, T4b o T5. Las pruebas de D1 y N6 pasan contra el original, lo que confirma que T4 no cambió esos comportamientos.
- [x] Ningún valor de ingeniería sin marca. Todas las constantes numéricas están marcadas `# SINTÉTICO: no es dato de proyecto` o `# NORMA: CLAUDE.md §x / respuesta de Steven Px`. Los literales en línea (`'#12'`, `[0, -4]`, `b"%PDF-1.7 …"`) también. Los ejes y nombres son ejemplos del CLAUDE.md o de Steven.

**T4 — Correcciones**
- [x] `python -m pytest -v` en verde: 234 passed.
- [x] `git diff d8e332c -- BACKEND/reglas_ingenieria.py` es trazable: cada bloque cita D2/D3/D4/D6a-c/D7/D8/D9/D10/D11, N1/N2/N3/N5/N8/N10–N15, P2/P3/P5/P6/P7/P8/P9/P12, T4b o T5. Las referencias "Archivo 01/02/08" se cambiaron por secciones del CLAUDE.md (P12). D1 sigue sin cambios. Salvedades sin respuesta de Steven: ejes de varias letras y `Ñ` (O6), y comilla recta solamente (O7).
- [x] `python -c "import main"` → `import main OK`.

**T4b — Ejes con prima, lectura de la visita y platea**
- [x] `formatear_campo_ejes("cruce_puntual", "A'", eje_num_1="1")` → `EJE A'-1` (`test_ejes_cruce_puntual_letra_con_prima`, PASSED).
- [x] `interpretar_eje_de_visita("A1")` y `("1A")` → `("A", "1")` (`test_interpretar_eje_de_visita_ambos_ordenes`, PASSED).
- [x] Caso `area` con A, B, 1, 2 → `(A-B),(1-2)` (`test_ejes_area_platea`, PASSED). El auditor no exige `—` a la platea y rechaza los formatos que no son de área.
- [x] pytest en verde; `import main` OK.

**T5 — Auditor ampliado**
- [x] Pruebas de #12 (cuantía recalculada, unidad por formato, columna OBRA con recubrimiento y tolerancia de la visita) y de #15 (PDF disperso de 30 000 000 y 30 000 001 bytes, destino que ya existía, destino no registrado → pendiente, PDF inexistente, solo lectura): todas PASSED.
- [x] `python -m pytest -v` en verde.

**T6 — README**
- [x] `grep "no está en el repositorio" PLANES/README.md` → sin resultados.
- [x] La línea de Etapa 0 enlaza a `[etapa-0.md](etapa-0.md)`.

**Reglas del CLAUDE.md revisadas en el código tocado**
- [x] Regla de Oro #1: no hay datos inventados. Lo que falta devuelve `"pendiente de verificar"`: plano ausente (N1), sin barras o cantidad ≤ 0 (N2), tipo sin regla (metálicos, P3), grosor con datos ≤ 0 (P8), ejes inválidos, fecha vacía (N14), cuantía u OBRA no recalculables.
- [x] Recubrimientos 0.075 / 0.040 / 0.025 por categoría del §4.5 (con la salvedad O1 para PLATEA).
- [x] EJES: los 4 formatos, `—` en losas y vigas sin eje-letra, sin `FILA` ni paréntesis en muros.
- [x] Cuantía calculada `As_total/(b*h)` (decimal con 4 cifras / % con 2), nunca copiada; el auditor la recalcula.
- [x] Versionado ` v2` / ` v3` con espacio, conserva `.PDF` en mayúscula y no crea carpetas (D9).
- [x] `DD/MM/AAAA` con validación de calendario real (`31/02/2026` y `29/02/2027` rechazadas).
- [x] Firmas: nada las fabrica; el auditor marca los campos de firma (#16 parcial; el borrado en el PDF base es de la Etapa 3).
- [x] Formatos: los IDs usados (`STP-MIVED`, `CATDIC-STP`, `HV-LEV`) son exactos; `ESTRIBOSS` solo en HV-LEV para todo tipo `COLUMNA*`.
- [x] Arquitectura: no se tocaron `main.py`, `database.py` ni `FRONTEND/`; el motor sigue sin conectar (Etapa 3).

**Errores del §6 que el auditor afirma cubrir**
- #8 parcial (O11).
- #9, #10 y #11 cubiertos en lo verificable por datos (#11 no puede detectar un "eje por proximidad visual").
- #12 cubierto: fecha, cuantía y OBRA.
- #15 cubierto: peso y sobrescritura.
- #16 parcial.
- #4: solo el apoyo de cálculo del grosor.
- #1–#3, #5–#7, #13, #14, #17 y #18 quedan para las Etapas 3 y 4, como dice el plan.

**Calidad básica**
- [?] Arranque real del servidor con uvicorn: no lo ejecuté, porque el `startup` de `main.py` llama a `inicializar_bd()` y `sembrar_datos_iniciales_catdic()` y modificaría el `catdic_local.db` trackeado. El criterio del plan (`import main`) sí se cumple.
- [x] Sin secretos, PDFs, fotos ni `.env` en el diff. `catdic_local.db` no aparece modificado en `git status`. `__pycache__/` y `.pytest_cache/` están ignorados.

### Pruebas ejecutadas
- `python -m pytest --version` (en BACKEND/) → `pytest 9.1.1`
- `python -m pytest -v` (en BACKEND/) → `============================= 234 passed in 0.47s =============================`
- `python -c "import main"` (en BACKEND/) → `import main OK`
- Pruebas actuales contra el `reglas_ingenieria.py` de `d8e332c` (copias en el scratchpad, `-p no:cacheprovider`) → `126 failed, 108 passed in 2.81s`. Todas las que fallan son de D#, N#, P#, T4b o T5; D1 y N6 pasan.
- `git status --short --ignored` → solo los 8 archivos de la etapa, más `!! BACKEND/.pytest_cache/` y `!! BACKEND/__pycache__/` (ignorados). `BACKEND/catdic_local.db` no está modificado.
- Pruebas de casos borde con `python -c` (solo lectura):
  - `Tramo 3-4` sin pórtico → `id_sugerido 'TRAMO'`, `duda None` (O5)
  - `interpretar_eje_de_visita('AB12')` → `('AB','12')` (O6)
  - `tolerancia_m=-1` → `conforme False` con dif 0 (O9)
  - `fecha=date(...)` → `EXC TypeError expected string or bytes-like object, got 'datetime.date'` (O8)
  - `'Terra Living S4'` en HV-LEV → `[]` (O11)
  - formato `'FORMATO-INVENTADO'` → `[]` (O11)
  - `A’` con comilla curva → `'pendiente de verificar'` (O7)
  - `PLATEA` 0.60 / 0.45 → conforme con rec 0.075

### Pendientes de verificar (para la Mesa de Dudas)
- Límite de peso: 30 000 000 bytes (lo que se usa ahora, el más estricto) o 30 MiB = 31 457 280 bytes.
- ¿CATDIC escribe decimales con coma (`0,40`)? Hoy el auditor los manda a "pendiente de verificar".
- ¿Existen ejes de varias letras (`AB`) o con `Ñ`? El código los acepta (O6).
- ¿Solo comilla recta `'` como prima, o también `’` y `′`? Ya está escrito en el CLAUDE.md §4.4 (O7).
- ¿Se documenta en el CLAUDE.md la PLATEA = 0.075 (§4.5) y la excepción N6 de tramos repetidos (§4.3)? (O1, O2)
- Una etiqueta `Tramo n-n` sin `P eje X` previo, ¿va a "Con dudas"? (O5)
- N19: el texto "Pendiente de verificación de medida en campo" con `conforme=True` en el caso D1, ¿cómo se enruta en la Etapa 3?

Archivos revisados:
- `BACKEND/reglas_ingenieria.py`
- `BACKEND/tests/test_reglas_ingenieria.py`
- `BACKEND/pytest.ini`
- `BACKEND/requirements-dev.txt`
- `PLANES/etapa-0.md`
- `PLANES/etapa-0-matriz-reglas.md`
- `PLANES/README.md`
- `CLAUDE.md`
