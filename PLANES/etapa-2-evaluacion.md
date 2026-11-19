# Etapa 2 — Evaluaciones internas

## Evaluación 1 · 22/10/2026 · Auditor CATDIC · T1 y T2

### T1 — Esquema de `elementos_diseno` (rama `claude/etapa2-t1-esquema`, `a1891ff`)
**Veredicto: BLOQUEADO.** El código es seguro; lo único que falta es el criterio 2.

**Bloqueante**
- `PLANES/etapa-2.md`, T1, criterio 2. No se ha cumplido "con la BD real existe el respaldo y `/api/dashboard` responde 200".
  - No es un defecto del código.
  - El Ejecutor no pudo migrar la BD real: está en el checkout principal y él trabaja en su worktree.

**¿Se puede migrar la BD real sin riesgo? Sí.**
- *Respaldo:* `_respaldar_bd` usa la API de backup de SQLite antes de tocar nada. Nunca pisa un respaldo anterior: si ya existe, crea ` v2`.
- *Transacción:* los dos `ALTER TABLE ADD COLUMN`, el `CREATE UNIQUE INDEX` y la fila de `auditoria` van en un solo `BEGIN…COMMIT`. Si algo falla, `ROLLBACK`. Lo cubre la prueba `test_migrar_diseno_con_duplicados_previos_revierte`.
- *Estado de la BD real (consultado en solo lectura el 22/10):*
  - `elementos_diseno` y `elementos_visita` tienen 0 filas, así que no puede haber duplicados.
  - `PRAGMA foreign_key_check` devuelve `[]`.
  - Todavía no está migrada: tiene 13 columnas.
- *FK:* `ADD COLUMN` y `CREATE INDEX` no reconstruyen la tabla, así que `elementos_visita.elemento_diseno_uid` queda intacta.
- **Aviso:** `inicializar_bd()` corre la migración en cada arranque. En cuanto se fusione T1 en `main` y se arranque el servidor, la BD real se migra sola.
- *Cómo verificar que quedó migrada:*
  - existe `catdic_local.backup-AAAAMMDD-HHMMSS.db`;
  - hay una fila `MIGRACION_ELEMENTOS_DISENO` en `auditoria`;
  - la tabla tiene 15 columnas;
  - `/api/dashboard` responde 200.
- *Menor:* si la migración falla, el respaldo ya creado se queda en disco. No hace daño.

**UNIQUE con `CREATE UNIQUE INDEX`:** cumple §4.2 y el plan.
- Funciona igual que una restricción `UNIQUE`. `_diseno_tiene_unico` reconoce las dos formas.
- *NULL:* no aplica, porque las 4 columnas son `NOT NULL`.
- **Herencia para T4:** dos elementos distintos con el mismo ID y nivel y EJES `pendiente de verificar` chocan en el UNIQUE. El importador debe convertir ese choque en una `DUDA_BLOQUEANTE`, no dejar que salte un `IntegrityError`.
- **Herencia para T3/T4:** la comparación es literal (`'S-4'` ≠ `'S -4'`). La normalización del nivel la hacen T3/T4, sin adivinar.

**Criterios de aceptación**
- [x] Pruebas con BD temporal: conserva filas y FK; idempotente; el UNIQUE rechaza duplicados en BD migrada y en BD nueva; revierte si ya había duplicados.
- [ ] BD real con respaldo y `/api/dashboard` 200: no se ejecutó (bloqueante).
- [x] pytest: `486 passed, 3 warnings in 6.74s`. Corrido con `git archive` + `CATDIC_DB_PATH` temporal.

**Reglas**
- Pruebas `SINTETICO`.
- §1.5: queda registro en auditoría.
- Corregido el comentario "Archivo 02" → "CLAUDE.md §4.4".
- No hay `.db` ni secretos en el diff.

### T2 — Validador de elementos de diseño (rama `claude/etapa2-t2-validador`, `ceca410`)
**Veredicto: APROBADO**, con observaciones.

**Puntos revisados**
- `categoria` y `recubrimiento_por_lado_m` no chocan con §4.1. El plan pide justo esa consulta, y no suma 2×rec ni calcula cuantías (`test_no_calcula_cuantias_ni_recubrimientos_sumados`).
  - **Condición para T4:** son constantes del programa, no datos del plano. No se guardan dentro de `datos_diseno_json`.
- Tipos que no están en la tabla de formatos: no es adivinar, porque el texto de EJES pasa tal cual. Pero la validación es débil:
  - `MURO DE CONTENCION`, `ZAPATA COMBINADA` y `ZAPATA DE MURO` (sin formato en §4.4) aceptan cualquier formato y no generan dudas.
  - Recomendación: un `HALLAZGO_INTERNO` o una duda mientras Steven no fije el formato.
- Error #11 cubierto hoy: `_SOLO_GUION` coincide con la categoría "LOSAS Y ESCALERAS".
  - Riesgo: `_SOLO_GUION` y `_FORMATOS_POR_TIPO` (`validador_diseno.py:36-47`) duplican a mano `CATEGORIA_POR_TIPO`. Un tipo de losa nuevo en `reglas_ingenieria.py` aceptaría `EJE A-1`. Conviene derivar "solo `—`" de la categoría.
- Las claves de las dudas coinciden con `dudas_y_hallazgos` (CHECK y NOT NULL). T4 debe añadir `proyecto_id` y `creado`.
  - **Observación importante para T4:** `dudas_y_hallazgos` no guarda ni el nivel ni `elemento_diseno_uid`. Un `C1` de S-5, S-4 y S-3 no se distinguiría, y el dedupe por id + campo mezclaría niveles. T4 debe incluir nivel + EJES o una columna `elemento_diseno_uid`. Si T4 no lo resuelve, el Auditor lo bloqueará.
- No hay datos de diseño reales ni inventados: todo está marcado `# SINTÉTICO` o `# NORMA` (ejemplos de §4.4).

**Otras observaciones (no bloquean)**
- `validador_diseno.py:157-159`: si `datos_diseno` llega como lista o como texto, `.items()` lanza excepción. Mejor una duda.
- `validador_diseno.py:50-55`: una lista o dict vacío (`{"acero": []}`) queda `confirmado`. Conviene tratarlo como vacío.
- `estado_campos` usa `pendiente_de_verificar` y los valores usan `pendiente de verificar`. T4 y el frontend deben comparar contra la constante correcta.
- `elemento_unico_en_planta` (P6, Etapa 0) va a duda. Es lo prudente, pero falta confirmarlo con Steven.
- Comprobado: `PORTICO` + `EJE 1 ENTRE MC-A` → 0 dudas; `COLUMNA` con ese mismo texto → duda.

**Criterios de aceptación**
- [x] losa con EJES ≠ `—` → duda;
- [x] muro con `FILA` → duda;
- [x] falta `hoja_plano_origen` → pendiente + duda;
- [x] tipo metálico → pendiente;
- [x] elemento completo → 0 dudas;
- [x] pytest: `520 passed, 3 warnings in 6.59s`, más 8 casos a mano.

### Pendientes de verificar (para Steven)
- Formato de EJES para `MURO DE CONTENCION`, `ZAPATA COMBINADA` y `ZAPATA DE MURO`.
- Cómo se identifica el elemento en una duda de diseño: ¿nivel + EJES en el texto, o una columna `elemento_diseno_uid`?
- Cuándo se migra la BD real (al arrancar el servidor desde un `main` con T1).

## Evaluación 2 · 22/10/2026 · Auditor CATDIC · Reevaluación de T1 (`a1891ff`)
**Veredicto: APROBADO.** Queda levantado el bloqueante del criterio 2.

El Auditor lo verificó todo en solo lectura:
- [x] **Respaldo** `BACKEND/catdic_local.backup-20261022-095419.db` (110 592 bytes):
  - `integrity_check = ok`;
  - esquema previo (13 columnas);
  - 22 visitas.
- [x] **BD real:**
  - `elementos_diseno` con 15 columnas (`fuente_json`, `pendientes_json`);
  - índice único `ux_elementos_diseno_clave` sobre `proyecto_id, id_elemento, nivel_rango, ejes`.
- [x] **Auditoría:** una sola fila (id 26, `MIGRACION_ELEMENTOS_DISENO`, 2026-10-22T09:54:19), que apunta al respaldo correcto. La segunda ejecución fue "ya migrada" y no dejó otra fila.
- [x] **Integridad:**
  - `foreign_key_check = []`;
  - `elementos_diseno` con 0 filas;
  - las visitas no cambiaron: 12 Con dudas, 6 Procesada, 4 Sin procesar.
- [x] **Dashboard:** `curl /api/dashboard` → 200 (el servidor ya estaba arriba).

**Observaciones**
- Las condiciones para T4 de la Evaluación 1 siguen vigentes:
  - un choque del UNIQUE con EJES `pendiente de verificar` tiene que acabar en duda;
  - hay que normalizar el nivel.
- La BD real ya tiene el esquema de T1 y `main` todavía no. No rompe nada, pero conviene fusionar T1 pronto.

## Evaluación 3 · 24/10/2026 · Auditor CATDIC · T3n, reconocimiento del PDF vectorial (rama `claude/etapa2-t3n-reconocimiento-plano`, `b2f2db7`)
**Veredicto: APROBADO.** Todo se contrastó en solo lectura con PyMuPDF.

### Comprobaciones
- **Cajetín:** solo trae `NN/36`; la numeración real llega a 40/36. Los títulos de las hojas coinciden con la tabla del informe. El sellado no tiene texto (lo generó un RICOH).
- **Capas y texto:** 83 capas, ninguna apagada. Ninguno de los 31 084 trazos de texto es invisible.
- **Tablas:**
  - p6: zapata de lindero.
  - p10 y p26: losas A, B y C.
  - Las filas hay que agruparlas con tolerancia en `y` (±3-4 pt).
  - No hay tabla de columnas ni campos `Asxi`/`Asyv`.
  - Ningún texto cruza `L#` con el tipo A/B/C.
- **Ejes:** los globos `A`, `B` y `C` de la p26 se ubican bien, pero hay 19 textos "A" en la hoja, así que la ambigüedad es real.
- **Nota de la p19:** el texto está partido en varias líneas; hay que unirlas para detectarlo.
- **Emparejamiento:** las hojas extra son la 9 y la 10, con un corrimiento de +2. La comprobación es visual; la confirma el usuario.
- **Equivalencia E-n ↔ planta:** pendiente, porque no hay ningún texto que la indique.
- **Datos del cliente:** no hay imágenes. Detalle menor: `EXP. AX-24-01` y `AGOSTO 2024` siguen en claro.

### Qué implica para T6n (opinión del Auditor)
1. Leer por posición: agrupar por `y` con tolerancia y anclar cada tabla a su encabezado. Usar `rotation_matrix` en las hojas giradas. Nunca rellenar un dato por vecindad.
2. Hay tres cruces que el plano no da: (a) E-n ↔ nivel, (b) `L#` ↔ tipo, (c) ID ↔ cruce de ejes. Los dos primeros los da el usuario por obra. Mientras falten, el campo queda pendiente con `DUDA_BLOQUEANTE`.
3. Los ejes se leen solo de los globos (el círculo en el margen).
4. El armado de columnas y muros se lee de las llamadas que hay en la región de cada dibujo. El extractor propone candidatos y no escribe directamente en la BD.
5. Lo que se puede leer con confianza para empezar:
   - el índice de hojas;
   - las tablas de losas y de la zapata de lindero;
   - el f'c por rango E-n;
   - los ID en planta con su posición;
   - los espesores `H=`.
6. Las notas de modificación generan una `DUDA_BLOQUEANTE`; nunca se aplican solas.
7. Los rótulos S-1/S-2 se repiten en cada hoja, así que la clave debe incluir la hoja.
8. `fuente_json` guarda la hoja, la página, el bbox y la capa.
9. Al crear la obra hay que preguntar al usuario por las dos plantas de techo y por cómo emparejar las hojas.

## Evaluación 4 · 24/10/2026 · Auditor CATDIC · T6n-a, núcleo del lector de planos (rama `claude/etapa2-t6na-lector-plano`, `463c322`)
**Veredicto: APROBADO.** El Auditor repitió la corrida en solo lectura y confirmó que el PDF quedó con el mismo hash.

**Lo que se comprobó**
- Las 41 hojas están indexadas.
- Las losas de p10 y p26 coinciden con T3n. Las celdas desplazadas se asignaron bien y AS. ADIC. queda pendiente.
- La zapata de p6 coincide con T3n.
- El f'c de p20 sale por rango; el valor 240 sin rango se descarta.
- Los globos de eje (1-4 y A-D) salen con confianza alta. No hay falsos positivos en las hojas de detalle y ninguna "A" de apoyo se toma como eje.
- Se detectaron 55 IDs y la nota de p19.

**Hallazgo:** el lector encontró **7 notas de modificación**:
- p7: muro de contención;
- p11, p12 y p13: "SECCION AJUSTADA";
- **p14: "CORRECCION EN DIMENSION DE COLUMNA: PASA DE 1.20M A 1.50M"**;
- p19;
- un fragmento suelto en p8.

Todas deben ir a la Mesa de Dudas.

**Observaciones**
- Agregar las marcas `AJUSTAD`, `CORRECCION` y `CAMBIO DE`, y unir los fragmentos con su encabezado.
- Globos de confianza "media" (llamadas numeradas con círculo): confirmarlos o exigir que estén en el margen de la planta.
- Los títulos son solo candidatos; el nivel se decide con un patrón explícito o con la confirmación del usuario (T7n).
- `_abrir` no cierra los documentos.

**Pruebas:** `648 passed` + 1 fallo ajeno (#21).

## Evaluación 5 · 26/10/2026 · Auditor CATDIC · T6n-b corregida (rama `claude/etapa2-t6nb-lector-plano`: `c2cb89c`, `766be85`, `17d586a`, `ac0721b` sobre `origin/main`)
**Veredicto: APROBADO**

Revisión de los bloqueantes del informe de Codex (`PLANES/etapa-2-t6nb-evaluacion-codex.md`).

### Bloqueantes
Ninguno.

### Comprobaciones
1. **Globos agrupados como una sola unidad [x]** (`BACKEND/plano/lector_plano.py`, `globos_de_eje` y `_cadenas`).
   - Las cubetas fijas `round(c/3)` se cambiaron por cadenas: primero por diámetro (±1,5 pt) y después por centro (vecino a ≤ 3 pt).
   - La línea de eje se exige al grupo completo. Si un solo globo del grupo no la tiene, sale el grupo entero o no sale ninguno.
   - Hay una prueba nueva en el límite de cubeta, `test_una_fila_alineada_se_evalua_como_un_solo_grupo_aunque_cruce_el_limite_de_cubeta`: A y B con línea, C sin ella, y centros en y = 850,0 / 851,4 / 852,6. Ahora no sale ninguno; antes salía A.
   - Riesgos que quedan, y que no bloquean:
     - una cadena puede unir una alineación con otro círculo de la misma clase que caiga a ≤ 3 pt;
     - entonces, si el rótulo se repite o le falta la línea, se descarta el grupo entero. Es un falso negativo, que es el lado seguro.
2. **Pruebas contra el Dropbox real (T12) [x].** `17d586a` es idéntico a `39a7477`, ya APROBADO (Evaluación 19 de la Etapa 3): las listas fijas pasaron a subconjunto más "al menos". Si T12 se fusiona antes, este commit queda redundante.
3. **STP sin Chromium [x].** `ac0721b`: la fixture `entorno` hace `pytest.skip` con el mensaje "Chromium de Playwright no está instalado en esta máquina (python -m playwright install chromium)".
   - Lo comprobé con `PLAYWRIGHT_BROWSERS_PATH=/nonexistent`: `3 passed, 34 skipped`, sin fallos.
   - Con Chromium instalado, las pruebas STP se ejecutan normalmente (suite completa en verde).

### Contra el PDF vectorial real de Terra Living (solo lectura, hash sin cambios)
- Globos:
  - p20, p26 y p29 → `1-4` y `A-D`, todos con confianza alta;
  - p34 (pórtico girado) → `A-D`, alta;
  - p5, p14 y p16 (detalles) → ninguno, sin falsos positivos.
- Notas de modificación en las 41 hojas: 11 candidatas, con las marcas nuevas `AJUSTADA` / `CORRECCIÓN` / `CAMBIO DE`. Incluyen la de la p14 (columna de 1.20 a 1.50 m) y la de la p19.

### Regla de Oro, datos del cliente y Dropbox
- El lector sigue siendo puro: no usa la BD, no escribe en disco y no modifica el PDF (hay pruebas que lo comprueban).
- No hay celdas rellenadas por vecindad, y los globos sin línea de eje no salen.
- En el diff no hay datos del cliente: grep de `VUC`, `AYBAR`, `JAVIER`, `CODIA` y `48605` vacío.
- Las únicas escrituras (`.save`, `unlink`) están en las pruebas, sobre `tmp_path`. Nada escribe en Dropbox.

### Pruebas ejecutadas
- Rama extraída con `git archive`, Python 3.14, desde `BACKEND`: `659 passed, 3 warnings in 58.43s`, 0 fallos. Coincide con lo que reporta el Ejecutor.
- `tests/test_lector_plano.py` → `25 passed`.
- `tests/test_stp_mived.py` sin Chromium → `3 passed, 34 skipped`.

### Observaciones (no bloquean)
- La detección de la línea de eje se validó en Terra Living; sigue pendiente contrastarla con otros planos reales (T6n-c, P16), como señaló Codex.
- `py -3.14` no está en el PATH de las sesiones; se usó el ejecutable de Python 3.14 directamente.

## Evaluación 6 · 29/10/2026 · Auditor CATDIC · T4n "Nueva obra" (rama `claude/etapa2-t4n-nueva-obra`, `c99e019`, sobre `origin/main`)
**Veredicto: APROBADO**

### Bloqueantes
Ninguno.

### Comprobaciones
1. **Certificación obligatoria y auditada [x].**
   - `guardar_planos` falla sin la casilla y no guarda nada (prueba `test_sin_la_casilla_de_certificacion_no_se_guarda_nada`). El formulario envía `false` por defecto.
   - La tabla `planos` guarda `certificado_por` (`getpass.getuser()`), `certificado_en` y el texto literal.
   - La fila de auditoría `OBRAS/SUBIR_PLANOS` o `CAMBIAR_PLANO` repite la certificación con usuario y fecha.
2. **Sin sobrescribir y con sha256 [x].**
   - Cada revisión va en su propia carpeta `rNN` (`mkdir(exist_ok=False)`), y `_mover_sin_sobrescribir` añade ` v2`/` v3` si el nombre se repite.
   - El sha256 y el tamaño se calculan por trozos al copiar, y se rechaza un archivo de más de 300 MB, vacío, con contraseña o que no sea un PDF legible.
   - Si la BD falla, se hace rollback y se borra la carpeta de la revisión, sin dejar archivos ni filas (hay prueba). La carpeta temporal se elimina siempre.
3. **Carpeta de datos fuera de Dropbox y del repo [x].** `config.obtener_datos_raiz` usa `CATDIC_DATOS_RAIZ` o `<home>\CATDIC-DATOS`, y rechaza (409) una carpeta dentro de la raíz de Dropbox, dentro del repositorio o con "dropbox" en la ruta. Hay prueba.
4. **Cambiar plano [x].**
   - La revisión nueva queda vigente: el índice único parcial `ux_planos_vigente` impide que haya dos.
   - La anterior pasa a `historico`.
   - Los `elementos_diseno` del plano anterior, o sin `plano_id`, reciben `revisar_motivo = 'plano cambiado: revisar'`. La primera subida no marca nada. Hay pruebas.
5. **Migración `MIGRACION_COLUMNAS_T4N` [x].** Usa `ALTER TABLE ADD COLUMN` (`proyectos.inicio_obra`, `elementos_diseno.plano_id` y `revisar_motivo`): respalda antes, audita dentro de la misma transacción y es idempotente. La prueba de T7a sigue estricta: ahora exige exactamente 3 respaldos, ligados a sus 3 filas `MIGRACION_*`.
6. **`obra_datos_usuario` [x].**
   - Lo que escribe el usuario queda `confirmado`, con fuente `usuario`, y la auditoría `GUARDAR_DATOS_OBRA` guarda el valor anterior y el nuevo de cada dato.
   - La primera subida abre las 3 `DUDA_BLOQUEANTE` de la obra (`emparejamiento_hojas`, `equivalencias_en_nivel` y `losas_tipo`), sin duplicarlas.
   - Las cierra `completo=true` del tipo correspondiente.
7. **Un lote inválido no guarda nada [x].** Todos los elementos se validan antes de abrir la transacción: E-n, L# con A/B/C, hoja del vectorial y del sellado dentro de su rango o "sin pareja". Hay pruebas.
8. **Regla de Oro [x].**
   - Del plano solo se lee el número de páginas, para validar el emparejamiento y avisar si no coinciden.
   - No se deduce ningún nivel, tipo ni pareja.
   - Los campos vacíos de la obra quedan vacíos (hay prueba).
9. **Sin datos de clientes en git [x].** Grep de `VUC`, `AYBAR`, `JAVIER`, `CODIA`, `48605` y `TERRA` en el diff: vacío. Las pruebas usan PDF sintéticos y una carpeta temporal.
10. **Frontend [x].**
    - Hay un modal "Nueva obra" / "Cambiar plano" con los dos archivos.
    - La casilla de certificación es obligatoria también en la UI.
    - Si la obra se crea pero los planos fallan, el aviso lo dice.
    - Cada obra muestra la revisión vigente, quién la certificó y el sha256 abreviado.
    - El modal "Datos de la obra" tiene la casilla "Ya escribí todos los de esta lista".
    - No hay `v-html`.

### Pruebas ejecutadas
Rama extraída con `git archive`, Python 3.14, desde `BACKEND`, con BD y `CATDIC_DATOS_RAIZ` temporales: `1 failed, 666 passed, 3 warnings in 50.37s`. **El único fallo es `tests/test_parser_visitas.py::test_lista_coincide_con_dropbox_si_esta_disponible`**, el esperado (carpeta #21), que corrige T12. Las 21 pruebas nuevas de `test_obras.py` pasan.

### `python-multipart`
**Debe ir en las dependencias de ejecución, no solo en las de desarrollo.** FastAPI la exige al registrar rutas con `Form`/`File`: sin ella, `import main` falla y el servidor no arranca en una instalación limpia.
- Hoy `BACKEND/requirements.txt` no existe en `main`: lo crea T1 de la Etapa 3, que todavía no está fusionado.
- Cuando se fusione, hay que añadir `python-multipart==0.0.32` (la versión instalada).
- Mientras tanto, dejarla en `requirements-dev.txt` es aceptable.

### Observaciones (no bloquean)
- Las dudas de la obra usan `id_elemento = '(obra)'` y `visita_id` nulo. Cuando la Mesa de T4 llegue a `main`, su `PATCH` las trataría como "duda de elemento" y permitiría cerrarlas con un texto libre, sin que se escriban los datos. Conviene que la Mesa rechace (422) esas dudas y remita a "Datos de la obra", o que solo las cierre `completo=true`.
- `completo=true` se fía de la declaración del usuario. Es correcto, porque el usuario es la fuente, pero no se comprueba que estén todos los E-n o L# del plano. Cuando exista el lector (T6n), conviene avisar de los E-n o L# del plano que no tengan dato.
- El tipo `techo` no abre una duda propia: va dentro de la de `emparejamiento_hojas`. Es aceptable.

## Evaluación 7 · 29/10/2026 · Planificador (auditoría, skill auditar-catdic) · T5n "Visor y recuadros" (rama `claude/etapa2-t5n-visor`, `00de70f`, sobre T4n + T6n-b)
**Veredicto: APROBADO**

### Bloqueantes
Ninguno.

### Comprobaciones
- [x] **Regla de Oro:** toda propuesta sale con `estado = "pendiente de verificar"` y con su fuente: método, archivo, hoja, página y bbox de los globos, del ID o del rótulo.
  - Si los globos no son únicos, si el ID se repite, si no se halla la hoja o si falta el rótulo, devuelve `rect: null` con el motivo (`visor.py` `_vacia`). No deduce nivel ni usa E-n↔nivel.
- [x] **Recuadro guardado:** se guarda `{plano_id, pagina, rect en pt, origen, estado: confirmado, confirmado_por, confirmado_en}` en `recorte_planta_json` / `recorte_detalle_json`.
  - La auditoría `GUARDAR_RECUADRO` registra el valor anterior y el nuevo, en una transacción con ROLLBACK.
  - Se rechaza un recuadro fuera de la hoja o de menos de 5 pt.
- [x] **Error #2:** la vista previa del DETALLE usa `recortar_detalle` con `carpeta_planos` obligatorio (`<datos>/<obra>/planos`), así que un PDF de visita no puede entrar.
- [x] **Error #1:** la vista previa de LOCALIZACION es la hoja completa, a `DPI_PLANTA`, con el recuadro rojo de M3.
- [x] **Caché:** `obtener_cache_raiz` sigue la misma regla que la carpeta de datos (nunca Dropbox ni el repo). La validación quedó refactorizada en `_carpeta_local_valida`, sin cambiar su comportamiento.
- [x] **Conversión px↔pt:** se prueba de ida y vuelta, también en una hoja girada 270° (`test_visor.py`).
- [x] **Contenido del diff:** no tiene `v-html`, `innerHTML` ni `eval` en el frontend, ni PDF, PNG o BD, ni datos del cliente.

### Observaciones (no bloquean)
- **O1:** `rasterizar_hoja` usa un temporal fijo `pNN-dpi.tmp.png`. Si llegan dos peticiones simultáneas de la misma hoja, en Windows pueden chocar en el `replace`. Conviene un nombre temporal único cuando se habilite el uso multiusuario.
- **O2:** la propuesta de DETALLE es heurística (bloque contiguo sobre el rótulo, hueco de 25 pt). Es correcto que salga pendiente; hay que validarla con P16 en T8n.
- **O3:** el visor no comprueba que la hoja de LOCALIZACION sea una planta; lo confirma el usuario. Se puede reconsiderar en T7n, usando la clasificación `planta` del lector.
- **O4:** la rama incluye T6n-a, T6n-b y T4n. Se fusiona después de esas tres.

### Pruebas ejecutadas
- `python3.14 -m pytest -q` desde `BACKEND` en un worktree temporal de `00de70f` → `721 passed, 3 warnings in 54.73s`.
- Corrida real del Ejecutor (copia de la BD, Terra Living): C1 `EJE A-1` → p26 por cruce de ejes, y DETALLE en p14 por el rótulo «COLUMNA C1». La vista previa coincide con el recuadro guardado (fracciones iguales a ±0,0005). No se repitió en la auditoría.

## Evaluación 8 · 29/10/2026 · Planificador (auditoría, skill auditar-catdic) · T6n "Extractor desde el vectorial" (rama `claude/etapa2-t6n-extractor-d699d1`, `9438234`)
**Veredicto: BLOQUEADO** (1 bloqueante)

### Bloqueantes
- **B1. `BACKEND/plano/extractor.py:501-509` (`_abrir_duda`) y `extraer_diseno`: las `DUDA_BLOQUEANTE` del extractor no se cierran nunca.**
  - Regla: la Mesa de Dudas tiene que reflejar el estado real. Una bloqueante que sigue abierta sin causa frena T7n y T10 sin motivo.
  - Qué pasa: en Terra Living, sin datos del usuario, la corrida abre dudas por `equivalencia_nivel:<nivel>`, `losa_tipo` (por cada L#), `nivel_hoja:pNN`, etc. En la auditoría salieron 347 + 195 entradas antes de quitar duplicados. Cuando el usuario llena las equivalencias y los tipos en "Datos de la obra" (T4n) y se vuelve a extraer, las dudas viejas siguen abiertas: el código solo inserta y deduplica, nada las resuelve. Tampoco se distinguen de las 3 dudas de obra de T4n (mismo `visita_id NULL`).
  - Qué debe cambiar:
    - marcar las dudas del extractor con su origen (por ejemplo, un prefijo `T6n:` en `campo_afectado` o una columna de origen);
    - en cada extracción, cerrar con auditoría las dudas T6n abiertas de ese plano que ya no se generan (`resuelta = 1`, respuesta "resuelta por re-extracción", con el usuario y la fecha);
    - agregar una prueba: sin `losa_tipo`, se abre la duda; con `losa_tipo` y una nueva extracción, la duda queda cerrada y auditada, y las de T4n no se tocan.

### Comprobaciones
- [x] **Regla de Oro:**
  - todos los campos quedan `pendiente_de_verificar` (`_validar`);
  - en la corrida real, ningún valor no pendiente aparece sin fuente;
  - los rangos con extremo FUND./TECHO no se expanden sin una equivalencia (Terra: `FUND.@ E3` y `E16 @ TECHO` → `None`);
  - E-10 en dos rangos con f'c 350/280 → rojo + duda, sin elegir uno.
- [x] **Fuente por valor:** se guardan archivo, revisión, sha256, tabla, página, hoja y bbox de cada celda.
- [x] **Solo lectura del PDF:** se compara el sha256 antes y después, y la extracción se rechaza si no coincide con el de la subida.
- [x] **Idempotencia:**
  - un campo confirmado no se toca;
  - el choque con el UNIQUE, o con un elemento que no viene de T6n, abre una duda y no da `IntegrityError` (`test_un_choque_con_el_unique…`).
- [x] **Capas visibles:** hay una prueba con una capa oculta (`test_el_texto_de_una_capa_oculta_se_ignora`). Terra tiene 0 capas ocultas.
- [x] **EJES de losa:** `—` (`EJE_SIN_LETRA`). La zapata queda con nivel y EJES pendientes.
- [x] **Diff:** no incluye PDF, BD ni datos de cliente. La transacción es única, con ROLLBACK, y la corrida queda auditada (`EXTRAER_DISENO`).

### Observaciones (no bloquean)
- **O1:** `tablas_extraidas` no borra las tablas que desaparecen en una nueva extracción del mismo plano. Hoy no pasa, porque el plano no cambia. T7n debe confiar solo en las claves de la última corrida.
- **O2:** el tipo L#→A/B/C lo escribe el usuario en T4n (`confirmado`), pero en el elemento vuelve como `pendiente`. Hay que decidir en T7n si se hereda confirmado.
- **O3:** las dudas con `id_elemento '(obra)'` tienen que verse en la Mesa (T5b) y llevar a "Datos de la obra" (observación ya hecha en la Evaluación 6).
- **O4:** las 8 decisiones de la sesión necesitan el visto bueno de Steven (sobre todo la 1, la 4, la 5 y la 8).

### Pruebas ejecutadas
- `python3.14 -m pytest -q -p no:cacheprovider` desde `BACKEND` del worktree de `9438234` → `741 passed, 3 warnings in 60.90s`.
- Corrida real en solo lectura con `leer_vectorial` y `proponer` sobre `PLANOS ESTRUCTURALES TERRALIVING.pdf`, sin datos del usuario:
  - sha256 igual antes y después; 0 capas ocultas;
  - 38 tablas (21 de f'c, 16 de acero en losa y 1 de zapata de lindero), 1 en verde;
  - 197 propuestas; zapata `ZAPATA MURO LINDERO 6"` con B 0.60, h 0.30 y Df 0.80, tal como están impresos.

## Evaluación 9 · 29/10/2026 · Planificador (auditoría) · T6n con B1 corregido (`6359204` sobre `9438234`)
**Veredicto: APROBADO**

- **B1 resuelto:**
  - las dudas del extractor llevan el prefijo `T6n:` en `campo_afectado`;
  - `_cerrar_dudas_viejas` cierra, en cada extracción, las que la corrida ya no genera: `resuelta=1`, respuesta y fecha, con auditoría `CERRAR_DUDAS_REEXTRACCION`;
  - las de T4n no se tocan;
  - prueba nueva: `test_al_dar_el_dato_y_reextraer_la_duda_del_extractor_se_cierra_con_auditoria`.
- Suite en un worktree de `6359204`: `742 passed, 3 warnings in 62.40s`. La fusión con `origin/main` sale limpia.
- **Siguen pendientes de Steven:** las 8 decisiones de ingeniería de la sesión (O4 de la Evaluación 8). No bloquean el PR; si cambia alguna, se hace en una tarea aparte.

## Evaluación 10 · 29/10/2026 · Planificador (auditoría) · T6n-d (rama `claude/etapa2-t6nd-ajustes-ae5110`, `1b899a4` sobre `6359204`)
**Veredicto: APROBADO**

### Comprobaciones
- [x] **Regla de borde de Steven** (`comprobar_fc`): un E-n de borde toma el f'c del rango que empieza en él. Para eso, todas las filas que lo cubren deben empezar o terminar en él, al menos una empieza ahí y las que empiezan coinciden en el valor. Si no se cumple, hay choque.
  - La fuente guarda `borde_de_rango` (con la fila usada) y la fila que cede guarda `cede_a`.
  - Terra, en solo lectura: E-10 = 280 por «E10 @ E16»; E-3 = 350; `rangos_sin_choque` sale en verde en todas las tablas de f'c; sha256 igual.
- [x] **Lista `techo` en T4n:**
  - la página tiene que existir en el vectorial vigente y se guarda como entero;
  - sin plano vigente, responde 409;
  - un lote inválido no guarda nada.
  - No cierra dudas de T4n: la duda de cada planta repetida es del extractor (`T6n:nivel_hoja:pN`) y se cierra al volver a extraer. Es coherente con B1.
- [x] La prueba vieja E1@E3/E3@E6, que esperaba rojo, se reemplazó por solapes reales parametrizados. Es correcto: el caso de borde ya no es un choque, según la regla de Steven.
- [x] El diff no trae datos de cliente. Los valores "PRUEBA A/B" del navegador solo existieron en la copia de la BD.

### Pruebas ejecutadas
- Suite en un worktree de `1b899a4`: `748 passed, 3 warnings in 60.94s`. La fusión con `origin/main` sale limpia.

## Evaluación 11 · 29/10/2026 · Planificador (auditoría) · T7n confirmación (rama `claude/etapa2-t7n-confirmacion-8210cf`, `2f850fc`)
**Veredicto: APROBADO**

### Bloqueantes
- Ninguno.

### Observaciones (no bloquean)
- O1. En la Mesa, una duda `T6n:` que apunta a un solo campo exige un valor válido. El usuario no puede contestar con texto libre ("ver adenda"). Es seguro, pero puede estorbar; revisarlo con el uso.
- O2. `campo_de_duda` recorre también las filas de `tablas_extraidas` de extracciones anteriores. Si el mismo uid aparece dos veces, devuelve None y la duda solo guarda la respuesta. Es el lado seguro.
- O3. La auditoría usa dos usuarios distintos: "Steve" (el usuario de Windows) en el lote y "steven" (constante) en la Mesa. Ya pasaba antes de T7n; es decisión 5 de Steven.
- O4. Fusionar con la rama `etapa3-t1-dependencias` dará un conflicto add/add en `BACKEND/requirements.txt`. Hay que quedarse con la versión de T7n, que es la de T1 más python-multipart.

### Criterios de aceptación
- [x] Confirmación por lote, solo con la tabla en verde y de la extracción vigente: plano, revisión, sha256, última corrida y datos de la obra sin cambios. Pruebas 108–174; con lo real, la tabla roja da 409.
- [x] Lote atómico (lección 17): `test_si_falla_un_campo_no_se_guarda_nada`.
- [x] Lo ya confirmado con otro valor no se sobrescribe y abre una duda `T7n:` (prueba 216).
- [x] Auditoría por campo con usuario, lote, elemento, campo, valor y fuente (archivo, revisión, página, hoja y bbox). Con lo real: 10 filas `CONFIRMAR_CAMPO` y 1 `CONFIRMAR_LOTE`.
- [x] Las dudas `T6n:` se cierran con auditoría al confirmar (prueba 234) y no se reabren al volver a extraer (`campo_ya_confirmado` en el extractor).
- [x] Uno por uno en la Mesa: valida con las reglas de la tabla y confirma con auditoría (pruebas 263–330). Las dudas `(obra)` se ven con `sin_visita`.
- [x] Pantalla: recorte al lado, botón solo en verde y casilla explícita; el endpoint devuelve 422 sin `confirmo` y manda `extraido_en`. Verificado por el Ejecutor en el navegador sobre una copia.
- [x] Regla de Oro: nada queda confirmado sin una acción del usuario. Lo que no sale de una celda (ID, nivel, ejes, L#→tipo) no se confirma aquí.
- [x] No hay datos de cliente en el diff.

### Pruebas ejecutadas
- `pytest -q` en un worktree temporal → **880 passed**.
- `git merge-tree --write-tree main <rama>` → limpio.
- `auditar_t7n.py` sobre una copia de la BD preparada con T6n-d, con el vectorial real de Terra:
  - extracción: 38 tablas, 1 verde (`p6:zapata_muro_lindero`);
  - lote: 10 campos en 2 elementos; repetirlo da 409; la tabla roja da 409;
  - al volver a extraer, siguen 10 campos confirmados;
  - Mesa: 97 dudas de la obra abiertas, 0 confirmables una por una;
  - sha256 de la BD real y del PDF sin cambios.

### Pendientes de verificar (decisiones para Steven)
1. ¿El L#→tipo de "Datos de la obra" llega al elemento como confirmado?
2. ¿El lote confirma también la identidad del elemento (ID, nivel, ejes, hoja)?
3. ¿Una celda "AS. ADIC." vacía significa "sin acero adicional" o es una duda real?
4. Las notas "PLANO ANTERIOR": ¿basta con que el usuario certifique que la tabla vale para ponerla en verde?
5. ¿Un único nombre de usuario en la auditoría?

## Evaluación 12 · 30/10/2026 · Planificador (auditoría) · T7n-b decisiones (rama `claude/etapa2-t7nb-decisiones-7618b7`, `5bac472`)
**Veredicto: APROBADO**

### Bloqueantes
- Ninguno.

### Observaciones (no bloquean)
- O1. La tabla `certificaciones_tabla` nace en `inicializar_bd()`. El servidor la llama al arrancar (`main.py:37`), pero un script que use el extractor sin pasar por el arranque falla (me pasó en la auditoría). Hay que tenerlo en cuenta en T10.
- O2. Siguen usando el usuario de Windows tres sitios: `main.py`, `sync/lector_visita.py` y los generadores. Hay que pasarlos a `usuario_auditoria()` cuando se toquen (T10).
- O3. En Terra siguen 1 de 38 tablas en verde. Las de acero fallan porque la copia no tiene ningún L#→tipo y porque hay IDs repetidos en planta; las de f'c, porque faltan las equivalencias E-n↔nivel. Se resuelve cuando Steven llene "Datos de la obra", no con código.
- O4. El tipo de elemento no se confirma en el lote, porque la decisión 2 no lo nombra. Queda pendiente.

### Criterios de aceptación
- [x] D1: el L#→tipo llega confirmado, con referencia a la auditoría de "Datos de la obra" y una fila `CONFIRMAR_CAMPO`. Si el tipo cambia después de confirmar, se abre una duda y no se sobrescribe (`extractor._escribir_elemento`).
- [x] D2: la identidad se confirma en el lote, con una fila por campo. Lo pendiente no se confirma, y una hoja o un archivo distintos de la tabla dan 409. Con lo real: 16 `CONFIRMAR_CAMPO` (10 valores + 6 de identidad).
- [x] D3: una celda AS. ADIC. vacía se escribe como `-`. Su fuente marca `celda_vacia` y la regla, y no se aplica si hay texto descartado cerca. Otra columna vacía sigue abriendo duda (prueba con `Bw2`). Con lo real: se cierran 4 dudas (97 → 93).
- [x] D4: la certificación queda atada al plano y al sha256, con casilla explícita (422 sin ella). Se audita como `CERTIFICAR_NOTAS` y no se reabre al volver a extraer. Si cambia el sha256, se pierde.
- [x] D5: hay un solo usuario, "steven" (`database.usuario_auditoria()`), y no se tocaron las filas viejas.
- [x] Regla de Oro: lo único que se confirma sin el lote es lo que el usuario escribió o certificó, siempre auditado.

### Pruebas ejecutadas
- `pytest -q` en un worktree temporal → **892 passed**.
- `git merge-tree --write-tree main <rama>` → limpio.
- `auditar_t7n.py` sobre una copia, con el vectorial real de Terra:
  - extracción: 38 tablas, 1 verde;
  - lote: 10 valores y 6 de identidad;
  - repetir el lote → 409; la tabla roja → 409;
  - al volver a extraer siguen 16 campos confirmados;
  - sha256 de la BD real y del PDF sin cambios.

## Evaluación 13 · 30/10/2026 · Planificador (auditoría) · T4v visitas (rama `claude/etapa2-t4v-visitas-061a18`, `1da6332`)
**Veredicto: APROBADO**

### Bloqueantes
- Ninguno.

### Observaciones (no bloquean)
- O1. Una visita subida vive en `CATDIC_DATOS_RAIZ`. Si la misma obra también se sincroniza con Dropbox, el sincronizador la reporta como "desaparecida": solo es un aviso y no se borra nada. Hay que tenerlo en cuenta cuando una obra use las dos vías.
- O2. El usuario de la auditoría se cambió dentro del merge `261b7dc`, no en un commit aparte. El cambio es correcto (`usuario_auditoria()`).
- O3. `test_p16_real_no_soportado` fallaba porque hoy apareció `LEVANTAMIENTO\VISITA A OBRA` en el Dropbox de P16, no por T4v. Se corrigió en `1da6332` siguiendo la lección 15.

### Criterios de aceptación
- [x] Subir visita:
  - valida el número, la fecha (DD/MM/AAAA real) y la clase (Mixta → 422), y exige elementos y nivel;
  - guarda en `CATDIC_DATOS_RAIZ` sin sobrescribir (v2) y con el sha256 de cada archivo;
  - una subida fallida no deja carpeta ni fila (lección 17), con su prueba;
  - registra `SUBIR_VISITA` en la auditoría.
- [x] Conectar con Dropbox:
  - acepta solo una ruta absoluta, dentro de la raíz de Dropbox y que termine en `LEVANTAMIENTO\VISITA A OBRA`;
  - una misma carpeta no se conecta a dos obras (409);
  - registra `CONECTAR_DROPBOX` en la auditoría;
  - Dropbox solo se lee.
- [x] El lector T3 corre sobre las visitas nuevas. Si falla, la visita queda `Con dudas` con su duda (#1–#5, #7, #9 y #10 de Terra), y no queda nada sin leer en silencio.
- [x] La Mesa se abre en la visita, según el Ejecutor en el navegador (:8023).
- [x] Regla de Oro: la fecha y la clase vienen del usuario o del nombre del PDF (regla P1). Si faltan, quedan pendientes + duda.
- [x] No hay datos de cliente en el diff.

### Pruebas ejecutadas
- `pytest -q` en un worktree temporal → 916 passed, 1 failed (P16, entorno). Después de `1da6332`: `test_escaner_dropbox.py` → 22 passed; el Ejecutor reporta la suite en 917 passed.
- `git merge-tree --write-tree origin/main <rama>` → limpio.
- `auditar_t4v.py` sobre una copia de la BD, con una obra nueva conectada a la carpeta real de visitas de Terra:
  - 3 rutas malas rechazadas;
  - 25 visitas: 15 Con dudas y 10 Procesadas;
  - 103 dudas abiertas;
  - 8 visitas que el lector no pudo leer, todas con su duda;
  - la misma carpeta en otra obra → 409;
  - el listado con sha256 de Dropbox y el sha256 de la BD real, sin cambios.

### Decisiones para Steven
1. Número de visita repetido: se avisa sin bloquear.
2. Visitas ya Procesadas: el lector no las relee.
3. Carpeta con 2 PDF: elegir el PDF desde la Mesa.
4. Visitas viejas #1–#5: dejarlas en duda o marcarlas "fuera del sistema".
5. Carpetas que no siguen §5.1: se rechazan.
6. Elementos y nivel obligatorios al subir.
