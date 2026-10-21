# Etapa 1 — Sincronizador real de Dropbox + ingesta de visitas
Estado: APROBADO (Steven, 21/10/2026) · Evaluación interna: BLOQUEADO (B1, B2) → corregido en T8–T10 → APROBADO en la reevaluación del 21/10/2026.

## Respuestas de Steven (21/10/2026)
- **P1:** los PDF de visita siempre traen en su nombre lo que pone la app con la que se hace la visita. Regla: la fecha se toma del nombre de la carpeta; si no está, del nombre del PDF (p. ej. `08-09-2025 Zapata parcial 3.pdf`); si tampoco, `"pendiente de verificar"` y la visita va a la Mesa de Dudas. Nunca de la fecha de modificación del archivo. Aplica igual a la clase. → T3 (ahora también lee el nombre del PDF) y T4.
- **P2 (a criterio del planificador):** si el nombre trae las dos clases, como `12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026`, se guarda `clase = 'Mixta'` y una columna nueva `clase_detalle_json` con cada grupo leído del nombre, sin deducir nada: `[{"elementos": "COLUMNAS S-5", "clase": "Completivo"}, {"elementos": "PORTICOS S-5", "clase": "Parcial"}]`. Si no se puede partir sin adivinar, `clase = 'pendiente de verificar'` y va a dudas. → T2 (CHECK con `'Mixta'` + columna) y T3.
- **P3: sí.** Una visita se marca `Procesada` si en `INFORMES\2.DATA PROCESADA\` hay un STP con **la misma fecha exacta** `DD-MM-AAAA` en el nombre y, si la visita trae clase, con esa clase (`Parcial`/`Completivo`). Así se separan las dos #17 del 28-09-2026: S4 Completivo y S3 Parcial. Si aun así hay más de un STP candidato, la visita va a `Con dudas` y se listan los candidatos. Las rutas encontradas se guardan en `salida_json`. → T5.
- **P4:** `formatos_solicitados = ["STP-MIVED"]` para las visitas de Terra Living. No van ni CATDIC-STP ni el FI MIVED: el FI se genera por nivel y tipo, no por visita (§3.2, fila 3). → T5.
- **P5: sí**, las rutas son `…\SUPERVISION\EN CURSO\PROYECTO P16` y `…\LEVANTAMIENTO\LEV Y EVA\EN CURSO\ZOETRY CAP CANA`. → T6.
- **P6:** Steven instaló `httpx`, pero quedó en un **Python 3.15.1 nuevo**, que ahora es el `python` por defecto y **no tiene fastapi, pydantic, uvicorn ni pytest**. El backend y las pruebas están en Python 3.14.7, que no tiene httpx. Pendiente: decidir el intérprete del proyecto (pregunta abajo). Mientras tanto, T1 no se puede cerrar.
- **P7: sí**, por ahora solo los 3 proyectos sembrados.

- **Intérprete → Python 3.14** (decisión de Steven). Se instaló `httpx` 0.28.1 con `py -3.14 -m pip install httpx`; `fastapi.testclient` importa y las 306 pruebas pasan con `py -3.14 -m pytest`. **Todos los comandos del proyecto se corren con `py -3.14`**, no con `python`, que ahora es 3.15 y no tiene las dependencias. T1 debe dejarlo escrito en `requirements-dev.txt` (`httpx`) y en los criterios. Aviso: Starlette marca como obsoleto usar `httpx` con `TestClient` y sugiere `httpx2`; no bloquea.

## Objetivo
Que el botón **"Sincronizar desde Dropbox"** llame a un endpoint real `POST /api/dropbox/sync`. Ese endpoint lee en **solo lectura** las carpetas de cada proyecto, detecta los planos sellados y carga en la tabla `visitas` las visitas reales de Terra Living (#1 a #20), con número, fecha, clase (Parcial/Completivo), PDF de la visita y estado. Lo que no se pueda leer del nombre de la carpeta queda en `"pendiente de verificar"` y la visita va a **"Con dudas"**, con su duda en `dudas_y_hallazgos`. La sincronización se puede repetir sin duplicar y queda en `auditoria`.

## Discrepancias CLAUDE.md vs repositorio (y vs Dropbox real)

### Repositorio
- **R1.** No existe `/api/dropbox/sync`. `main.py` solo tiene `/api/dashboard`, `PATCH /api/proyectos/{id}` y `POST /api/visitas/procesar-cola` (este último es una simulación: pasa todo a "En revisión").
- **R2.** En el frontend, `sincronizarDropbox()` (`FRONTEND/index.html:144-150`) es falso: espera 800 ms, recarga el tablero y muestra "¡Sincronización completada…!" sin llamar a ningún endpoint.
- **R3.** La tabla `visitas` está vacía: la siembra no inserta visitas. Su esquema no admite datos incompletos:
  - `fecha_visita TEXT NOT NULL`
  - `clase CHECK IN ('Parcial','Completivo')`, sin valor para "pendiente de verificar"
  - `formatos_solicitados NOT NULL`
- **R4.** `DB_PATH` está fijo en `database.py`, así que no se puede probar contra una BD temporal.
- **R5.** No está instalado `httpx`, que necesita el `TestClient` de FastAPI para probar endpoints.
- **R6.** No hay ningún archivo de configuración. La raíz de Dropbox solo existe dentro de las rutas sembradas en `database.py`.

### Rutas de Dropbox (verificadas en solo lectura el 21/10/2026)
- **D1. Terra Living: existe.** `…\SUPERVISION\EN CURSO\TERRA LIVING`:
  - Planos sellados: `ARCHIVOS DEL CLIENTE\PLANOS ESTRUCTURALES\PLANOS SELLADOS\TERRA LIVING -ESTRUCTURALES.pdf`, 57 692 938 bytes, como dice §1.3.
  - `INFORMES\2.DATA PROCESADA\` y `FORMULARIOS\MIVED\FORMULARIOS NO FIRMADOS\` existen.
- **D2. Las carpetas de visita de Terra Living no siguen siempre el patrón de §5.1** (`<N. ELEMENTOS NIVEL PARCIAL|COMPLETIVO DD-MM-AAAA>`). Hay 22 carpetas reales y estas son las variantes:
  - Separador después del número: `1. `, `10 - `, `17.PARCIAL` (sin espacio) y `15 LOSAS` (sin punto).
  - **Sin fecha**: `1. FONDO DE SEPTICO`, `1. FUNDACIONES PARCIAL`, `2. MURO DE SEPTICO`, `3. VERTICALES SOTANO -7`, `4. FUNDACIONES COMPLETIVO`, `5. …`, `6. …`, `7. …`, `8 - …`, `9 - …`, `10 - LOSA S-6 COMPLETIVO`.
  - **Sin clase**: `11 - COLUMNAS S-5 31-07-2026`, `3. VERTICALES SOTANO -7`, `6. LOSA SEPTICO`.
  - **Clase mixta**: `12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026` (además lleva doble espacio).
  - **Número repetido**: hay dos `1.` (`FONDO DE SEPTICO` y `FUNDACIONES PARCIAL`) y dos `17` (`17. COMPLETIVO VERTICALES S-4 28-09-2026` y `17.PARCIAL VERTICALES S-3 28-09-2026`).
  - La clase a veces va antes de los elementos (`17. COMPLETIVO VERTICALES…`).
  - Cada carpeta trae **un PDF** de la visita, con nombre libre (`Losa S-3 parcial.pdf`, `4. Verticales Fundacion.pdf`; este último está dentro de la carpeta `3.`).
- **D3. Torre P16: la ruta sembrada no existe.** `…\EN CURSO\TORRE P16` no está; la carpeta real es `…\EN CURSO\PROYECTO P16`. Además su estructura es **otra**:
  - `VISITAS\VISITA A OBRA\<NN. NIVEL>\` (p. ej. `00. ZAPATAS`, `09. ENTREPISO E-9`) y, dentro, PDFs con la fecha delante (`08-09-2025 Zapata parcial 3.pdf`) o subcarpetas `01. ELEMENTOS VERTICALES` / `02. ELEMENTOS HORIZONTALES`.
  - No hay `PLANOS SELLADOS`: los planos están en `ARCHIVO DEL CLIENTE\Nueva carpeta\…PLANOS RESELLADOS…\` (hay varias versiones, del 11-08-2026 y del 2026.06.016).
- **D4. Hotel Zoetry: la ruta sembrada no existe.** `…\LEVANTAMIENTO\HOTEL ZOETRY` no está; la carpeta real es `…\LEVANTAMIENTO\LEV Y EVA\EN CURSO\ZOETRY CAP CANA`, con otra estructura (`01. ARCHIVOS DEL CLIENTE`, `02. EVALUACION`, `03. LEVANTAMIENTO`, `04. COMPARTIDO`).
- **D5. Estado de cada visita.** §7 pide "sus estados", pero el estado no está en la carpeta. Lo único que hay son los informes ya generados en `INFORMES\2.DATA PROCESADA\` (STP con la fecha en el nombre, p. ej. `Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026.pdf`) y en `4.INFORME LISTO\` (FI con fecha). Los nombres de esos informes no siguen un patrón uniforme (pregunta P3).

## Tareas

### T1 — Configuración y BD probable
- Estado: APROBADA · commit f63d859. `config.obtener_db_path()` / `obtener_dropbox_raiz()` leen la variable de entorno en cada llamada; `database.DB_PATH` ya no existe. 315 pruebas en verde con `py -3.14`. Nota para T2/T5: el `startup` de FastAPI solo corre con `with TestClient(app)`.
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/config.py` (nuevo), `BACKEND/database.py`, `BACKEND/requirements-dev.txt`, `BACKEND/tests/test_database.py` (nuevo)
- Depende de: —
- Qué hacer:
  - Crear `config.py` con `DROPBOX_RAIZ` (por defecto `C:\Users\Steve\CATDIC Dropbox`, que se puede cambiar con la variable de entorno `CATDIC_DROPBOX_RAIZ`) y `DB_PATH` (cambiable con `CATDIC_DB_PATH`).
  - Que `database.py` tome `DB_PATH` de `config.py`.
  - Añadir `httpx` a `requirements-dev.txt` e instalarlo, según P6.
- Criterios de aceptación:
  - [ ] Con `CATDIC_DB_PATH` apuntando a un `tmp_path`, `inicializar_bd()` crea la BD allí y no toca `BACKEND/catdic_local.db` (lo comprueba una prueba).
  - [ ] `py -3.14 -c "import fastapi.testclient"` funciona.
  - [ ] `py -3.14 -m pytest` desde `BACKEND/` sigue en verde.
- Reglas del CLAUDE.md que aplican: §1.2 (desacoplado), §1.3.

### T2 — Migración del esquema `visitas`
- Estado: APROBADA · commit f63d859. Migración aplicada a la BD real; respaldo `BACKEND/catdic_local.backup-20261021-154317.db`. 414 pruebas en verde. `fecha_visita` tiene CHECK (AAAA-MM-DD o pendiente). Nota para T5: `numero` sigue `INTEGER NOT NULL`; si una carpeta no trae número legible, T5 no debe inventarlo (hoy las 22 carpetas reales lo traen).
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/database.py`, `BACKEND/tests/test_database.py`
- Depende de: T1 (mismos archivos)
- Qué hacer:
  - Migración idempotente de `visitas`. SQLite no permite cambiar un `CHECK`, así que hay que reconstruir la tabla y copiar los datos.
    - `fecha_visita` y `clase` deben aceptar `'pendiente de verificar'`; `clase` también, si P2 lo pide, el valor `'Mixta'`.
    - Columna nueva `archivos_json` (PDF(s) de la visita, con tamaño y fecha de modificación).
    - Columna nueva `campos_pendientes_json`.
    - Restricción `UNIQUE(proyecto_id, ruta_carpeta)`: así no se duplica nada aunque se repita el número de visita.
  - Antes de migrar la BD real, copiarla a `catdic_local.backup-AAAAMMDD-HHMMSS.db` (queda ignorada por `*.db`).
  - Registrar la migración en `auditoria`.
- Criterios de aceptación:
  - [ ] Con una BD temporal con el esquema viejo y una visita de prueba, la migración conserva la fila y el esquema nuevo acepta `clase = 'pendiente de verificar'`.
  - [ ] Ejecutar la migración dos veces no cambia nada la segunda vez.
  - [ ] Con la BD real, existe el archivo de respaldo y `/api/dashboard` sigue respondiendo 200.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §1.5 (auditoría), §5.2 (no sobrescribir: respaldo).

### T3 — Lector de nombres de carpeta de visita
- Estado: APROBADA · commit 9948abb. 90 pruebas nuevas (405 en total). Con los PDF: 10 visitas siguen sin fecha (contando la #4, cuyo PDF trae `06.05.2026`) y 5 sin clase; la #11 toma la clase y la #9 la fecha de su PDF; la #12 queda `Mixta`.
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/sync/__init__.py` (nuevo), `BACKEND/sync/parser_visitas.py` (nuevo), `BACKEND/tests/test_parser_visitas.py` (nuevo)
- Nota (P1, P2): también interpreta el nombre del PDF de la visita como respaldo de fecha y clase, y devuelve `clase = "Mixta"` con `clase_detalle` cuando el nombre trae las dos clases.
- Depende de: —
- Qué hacer:
  - Crear `interpretar_nombre_carpeta_visita(nombre) -> dict` con `numero`, `descripcion` (elementos y nivel, en limpio), `clase`, `fecha_iso` (`AAAA-MM-DD`), `fecha_ddmmaaaa` (`DD/MM/AAAA`, §5.2) y `campos_pendientes`.
  - Debe aceptar los separadores reales (`.`, ` - `, `.` pegado al texto, sin punto) y fechas `DD-MM-AAAA`, y validar que la fecha exista en el calendario.
  - Lo que falte o sea ambiguo (sin fecha, sin clase, clase mixta, número ilegible) queda `"pendiente de verificar"` y se lista en `campos_pendientes`. No se deduce nada por proximidad. Si la carpeta no trae fecha o clase, se toman del nombre del PDF (P1); nunca de la fecha de modificación.
  - Reutilizar `PENDIENTE` de `reglas_ingenieria.py`.
- Criterios de aceptación:
  - [ ] Una prueba parametrizada recorre los **22 nombres reales** de Terra Living (copiados literalmente de la carpeta, no inventados). Por ejemplo:
    - `20. LOSA SOTANO 3 PARCIAL 15-10-2026` → número 20, Parcial, `2026-10-15`, sin pendientes.
    - `11 - COLUMNAS S-5 31-07-2026` → clase pendiente.
    - `3. VERTICALES SOTANO -7` → fecha y clase pendientes.
    - `17.PARCIAL VERTICALES S-3 28-09-2026` → número 17, Parcial.
    - `12. COLUMNAS  S-5 COMPLETIVO Y PORTICOS PARCIALES S-5 17-08-2026` → clase según P2.
  - [ ] `py -3.14 -m pytest` en verde.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §5.1, §5.2 (`DD/MM/AAAA`), error #12.

### T4 — Escáner de carpetas de Dropbox (solo lectura)
- Estado: APROBADA · commit 9948abb. Terra Living: 22 visitas (10 con pendientes), 1 plano sellado de 57 692 938 bytes, 13 informes en `2.DATA PROCESADA`. P16 y Zoetry: layout no soportado, sin excepción. 439 pruebas en verde.
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/sync/escaner_dropbox.py` (nuevo), `BACKEND/tests/test_escaner_dropbox.py` (nuevo)
- Depende de: T1, T3
- Qué hacer:
  - Crear `escanear_proyecto(carpeta_proyecto) -> dict` con el layout de Supervisión de §5.1:
    - planos sellados: PDFs de `ARCHIVOS DEL CLIENTE\PLANOS ESTRUCTURALES\PLANOS SELLADOS\`, con nombre, tamaño y fecha de modificación;
    - visitas: subcarpetas de `LEVANTAMIENTO\VISITA A OBRA\`, cada una con su interpretación (T3) y sus PDFs;
    - informes existentes en `INFORMES\2.DATA PROCESADA\`.
  - Si una ruta no existe, se reporta como `"pendiente de verificar"`, sin excepción.
  - **Nunca escribe, mueve ni borra** en Dropbox: solo usa `iterdir`/`stat`.
  - Si un layout no es el de §5.1 (P16, Zoetry), devuelve el aviso "layout no soportado en esta etapa".
- Criterios de aceptación:
  - [ ] Pruebas con una estructura falsa en `tmp_path` que copia los nombres reales: planos detectados, visitas listadas, carpeta sin PDF reportada, ruta inexistente reportada sin excepción.
  - [ ] Una prueba confirma que, tras escanear, el árbol de `tmp_path` no cambió (mismos archivos y fechas de modificación).
  - [ ] Escaneo de la carpeta real de Terra Living desde `py -3.14 -c` (solo lectura): 22 visitas y 1 plano sellado de 57 692 938 bytes.
- Reglas del CLAUDE.md que aplican: §1.3, §5.1, Regla de Oro #1.

### T5 — Endpoint `POST /api/dropbox/sync`
- Estado: APROBADA · commit 57e262f. Sync real de Terra Living: 22 visitas nuevas (7 Procesada, 11 Con dudas, 4 Sin procesar), 16 DUDA_BLOQUEANTE (10 fecha, 5 clase, 1 sin PDF) y 1 HALLAZGO_INTERNO (#8). 467 pruebas en verde. Respaldo previo en el scratchpad (`catdic_local.antes-T5.db`). `formatos_solicitados = ["STP-MIVED"]` (P4).
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/sync/sincronizador.py` (nuevo), `BACKEND/main.py`, `BACKEND/tests/test_sync_endpoint.py` (nuevo)
- Depende de: T2, T4
- Qué hacer:
  - Recorrer los proyectos de la tabla (o uno solo con `?proyecto_id=`), escanear y hacer *upsert* en `visitas` por `(proyecto_id, ruta_carpeta)`.
  - **Visita nueva:** sin pendientes, `estado = 'Sin procesar'`; con pendientes, `'Con dudas'` y una `DUDA_BLOQUEANTE` por campo en `dudas_y_hallazgos`.
  - **Visita existente:** solo se actualizan los datos leídos (archivos, nombre). **No se pisan** `estado` ni `salida_json` si ya avanzó (`En proceso`, `En revisión`, `Procesada`). Tampoco se pisa un campo que Steven ya respondió en la Mesa de Dudas.
  - Si una visita desapareció de Dropbox, no se borra: se informa en la respuesta.
  - `formatos_solicitados = ["STP-MIVED"]` (P4: el FI MIVED va por nivel y tipo, no por visita).
  - Actualizar `proyectos.planos_sellados`.
  - Registrar todo en `auditoria`: módulo `SYNC`, acción `SINCRONIZAR_DROPBOX`, conteos.
  - Respuesta: `{proyectos: [{id, visitas_nuevas, actualizadas, con_dudas, desaparecidas, avisos}]}`.
  - Estado `Procesada` deducido de los informes existentes: solo si P3 = sí.
- Criterios de aceptación:
  - [ ] Con una BD temporal y un Dropbox falso: el primer sync crea N visitas; el segundo crea 0 y no cambia ningún `estado`.
  - [ ] Una visita en `En revisión` sigue en `En revisión` después de sincronizar.
  - [ ] Una visita sin fecha queda en `Con dudas` y tiene su fila `DUDA_BLOQUEANTE` con `campo_afectado = 'fecha_visita'`.
  - [ ] Hay una fila nueva en `auditoria` por cada sync.
  - [ ] Contra la BD real y el Dropbox real: `POST /api/dropbox/sync?proyecto_id=terra-living` responde 200 con 22 visitas nuevas, y `/api/dashboard` devuelve esas visitas.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §1.3, §1.5, §2, §5.1.

### T6 — Corregir las rutas sembradas de P16 y Zoetry
- Estado: APROBADA · commit f63d859. Las 3 `carpeta_dropbox` de la BD real existen en disco; 2 correcciones registradas en `auditoria`. 417 pruebas en verde.
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/database.py`, `BACKEND/tests/test_database.py`
- Depende de: T2 (mismo archivo); sujeta a P5
- Qué hacer:
  - Cambiar `carpeta_dropbox` en la siembra:
    - `torre-p16` → `…\SUPERVISION\EN CURSO\PROYECTO P16`
    - `hotel-zoetry-h2-h5` → `…\LEVANTAMIENTO\LEV Y EVA\EN CURSO\ZOETRY CAP CANA`
  - En la BD existente aplicar un `UPDATE` (idempotente), porque `INSERT OR IGNORE` no corrige filas ya creadas. Registrarlo en `auditoria`.
  - La raíz sale de `config.DROPBOX_RAIZ`, sin rutas quemadas repetidas.
- Criterios de aceptación:
  - [ ] Tras arrancar, las 3 `carpeta_dropbox` de la BD existen en disco (`Path.exists()`; lo comprueba un `py -3.14 -c`).
  - [ ] Una prueba con BD temporal muestra que la ruta vieja se corrige una sola vez.
- Reglas del CLAUDE.md que aplican: §1.3, §5.1.

### T7 — Botón real de sincronización en el tablero
- Estado: APROBADA · commit 902e850. POST real verificado en el navegador (200, tabla con 22 visitas, 11 con dudas); con el backend apagado sale aviso de error. Fechas en DD/MM/AAAA. Segundo sync real: 0 nuevas, 22 sin cambios.
- Ejecutor: ejecutor-frontend
- Archivos: `FRONTEND/index.html`
- Depende de: T5 (contrato de la respuesta)
- Qué hacer:
  - `sincronizarDropbox()` hace `POST http://localhost:8000/api/dropbox/sync` y muestra un resumen por proyecto (nuevas, actualizadas, con dudas, avisos), en lugar del aviso falso.
  - Muestra el error si el backend no responde.
  - En la cola de visitas: número, nombre de carpeta, fecha en `DD/MM/AAAA` (o "pendiente de verificar"), clase y estado. Las visitas `Con dudas` se marcan de forma visible.
- Criterios de aceptación:
  - [ ] Con el backend corriendo, al pulsar el botón se ve un `POST /api/dropbox/sync` en la pestaña de red del navegador y la tabla muestra las visitas de Terra Living.
  - [ ] Con el backend apagado, aparece un mensaje de error en lugar de "Sincronización completada".
  - [ ] Ninguna fecha se muestra en formato `AAAA-MM-DD` ni `M/D/AAAA`.
- Reglas del CLAUDE.md que aplican: §5.2 (`DD/MM/AAAA`), error #12.

## Paralelismo
- **T1 y T3** pueden correr a la vez: no comparten archivos.
- **T2** va después de T1 (mismo `database.py`). **T6** va después de T2 (mismo archivo).
- **T4** espera a T1 y T3. **T5** espera a T2 y T4.
- **T7** espera a T5. Puede correr al mismo tiempo que T6, porque no comparten archivos.

## Pendientes de verificar / preguntas para Steven
- **Salidos en T5/T7 (pendientes):**
  - **#8:** la contradicción carpeta (Completivo) / PDF (parcial) queda como HALLAZGO_INTERNO y no bloquea. ¿Debe ser DUDA_BLOQUEANTE?
  - **Mesa de Dudas en el tablero:** el dashboard no devuelve las dudas por visita (p. ej. la #19 se ve "Con dudas" sin motivo). Mostrar las dudas y responderlas es trabajo de la Mesa de Dudas (Etapa 3).
  - **Vista angosta (~800 px):** los botones del encabezado se salen; ya pasaba antes de esta etapa.
- **Salidos en T3 (pendientes):**
  - **#4 FUNDACIONES COMPLETIVO:** su PDF `5.  Platea 06.05.2026.pdf` trae la fecha con puntos (`DD.MM.AAAA`). ¿Se acepta ese formato en los nombres de PDF?
  - **#9 LOSA S-6 PARCIAL:** la fecha sale de `CORRECCIONES SUPERVISION 23-07-2026.pdf`. → **Respondida:** Steven confirma que 23/07/2026 es la fecha de la visita.
  - **#8 COLUMNAS S-6 COMPLETIVO:** la carpeta dice COMPLETIVO y el PDF `10.Columnas parcial S-6.pdf` dice parcial. Manda la carpeta y queda un aviso. ¿Cuál es la correcta?
  - **#19 VERTICALES S-3 COMPLETIVO 09-10-2026:** la carpeta no tiene PDF.
- **P1. Visitas sin fecha en el nombre** (11 carpetas de Terra Living, de la #1 a la #10). ¿Quedan "pendiente de verificar" y van a la Mesa de Dudas para que pongas la fecha a mano? Propuesta: sí. No se toma la fecha del archivo PDF, porque Dropbox la cambia al sincronizar.
- **P2. Clase mixta**, como `12. COLUMNAS S-5 COMPLETIVO Y PORTICOS PARCIALES S-5`. ¿Es una visita con dos clases (columnas completivo + pórticos parcial)? ¿Se guarda como `Mixta` o queda pendiente para que la definas?
- **P3. Estado inicial de las visitas antiguas.** ¿Marco como `Procesada` las visitas que ya tienen su STP en `INFORMES\2.DATA PROCESADA\` (coincidencia exacta por fecha `DD-MM-AAAA` en el nombre del informe)? Si no, todas entran como `Sin procesar` y la cola mostraría 22 visitas pendientes que ya se hicieron.
- **P4. `formatos_solicitados`** para las visitas de Terra Living: ¿`["STP-MIVED", "MIVED-FI"]` según su `formato_defecto`? ¿Y `CATDIC-STP`?
- **P5. Rutas reales de P16 y Zoetry:** ¿confirmas `…\EN CURSO\PROYECTO P16` y `…\LEVANTAMIENTO\LEV Y EVA\EN CURSO\ZOETRY CAP CANA`?
- **P6. Instalar `httpx`** en el Python global, para probar los endpoints: ¿de acuerdo?
- **P7.** ¿Hay otros proyectos de `SUPERVISION\EN CURSO` (son 164 carpetas) que deban entrar ya en la tabla `proyectos`? Propuesta: no en esta etapa; solo los 3 sembrados.

## Fuera de alcance de esta etapa
- **Layout de visitas de Torre P16** (carpetas por nivel con PDFs fechados) y **Hotel Zoetry**: el escáner los reporta como "layout no soportado". Se planifican aparte cuando definas sus reglas.
- Leer el **contenido** de los PDFs de visita (log fotográfico, etiquetas, medidas) y cargar `elementos_visita`: va con la Etapa 3 (Procesar Cola).
- Importar `elementos_diseno` desde los planos: es la Etapa 2.
- Escribir en Dropbox, en cualquier forma.
- Pendientes de la Etapa 0 (extremos iguales `10-10`, `C1 Tramo 2-3` con pórtico abierto, §4.4 con eje principal numérico y `MC`, tolerancia como texto, 30 MB/MiB, coma decimal): siguen en `etapa-0-evaluacion.md`.
- Push del commit de cierre de la Etapa 0 (`61e6ecb`): espera la confirmación de Steven.

## Correcciones tras la evaluación interna (21/10/2026)
La evaluación (`etapa-1-evaluacion.md`) BLOQUEÓ la etapa por B1 y B2. Decisiones de Steven:
- **B1 / P3 estricta:** para marcar `Procesada`, el nombre del STP debe traer **la misma clase** que la visita. Un STP de la misma fecha sin clase en el nombre, o una visita `Mixta`, van a `Con dudas` con `DUDA_BLOQUEANTE` en `estado` que lista los candidatos. La #18 se corrige en la BD real.
- **B2 / #9:** Steven confirma que **23/07/2026 es la fecha de la visita #9** (sale de `CORRECCIONES SUPERVISION 23-07-2026.pdf`). Se mantiene y se guarda de dónde salió.
- **Procesar Cola:** se desactiva hasta la Etapa 3 (sigue simulado y cambiaría visitas reales a `En revisión`).

### T8 — P3 estricta, origen de los datos y corrección de la #18
- Estado: APROBADA · commit 57e262f. BD real: la #18 pasó a `Con dudas` (duda `estado`, auditoría `CORREGIR_P3_ESTRICTA`); las otras 6 siguen `Procesada`; la #9 tiene origen `pdf`. Estados finales: 12 Con dudas, 6 Procesada, 4 Sin procesar. 482 pruebas en verde. Decisión del ejecutor: si solo hay STP de la clase contraria, la visita queda `Sin procesar`.
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/sync/sincronizador.py`, `BACKEND/database.py`, `BACKEND/tests/test_sync_endpoint.py`, `BACKEND/tests/test_database.py`
- Qué hacer:
  - P3 estricta.
  - Guardar en `visitas` el origen de la fecha, de la clase y del estado (columna nueva `origen_datos_json`, añadida de forma idempotente). Ejemplo: `{"fecha": "pdf", "pdfs_fecha": [...], "clase": "carpeta", "estado": "sync_p3", "stp": [...]}`.
  - Revisar con la regla estricta, una sola vez y con auditoría, las visitas que el sync marcó `Procesada`: la #18 pasa a `Con dudas` con su duda `estado`.
  - Rellenar el origen de las 22 visitas existentes. La #9 queda con fecha 23/07/2026 y origen `pdf`, como confirmó Steven.
- Criterios de aceptación:
  - [ ] Una prueba muestra que un STP sin clase con la misma fecha da `Con dudas` y no `Procesada`; también para una visita `Mixta`.
  - [ ] En la BD real: la #18 está en `Con dudas` con su `DUDA_BLOQUEANTE` en `estado`; las otras 6 siguen `Procesada`; la #9 tiene `origen_datos_json.fecha = "pdf"`; hay una fila de auditoría con la corrección.
  - [ ] Un segundo sync no cambia nada.
  - [ ] `py -3.14 -m pytest -q` en verde.

### T9 — Desactivar "Procesar Cola" (backend)
- Estado: APROBADA · commit 57e262f. El endpoint responde 409 sin abrir la BD; 2 pruebas en `test_procesar_cola.py`.
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/main.py`, `BACKEND/tests/test_procesar_cola.py` (nuevo)
- Qué hacer: `POST /api/visitas/procesar-cola` responde `409` con el mensaje "Procesar Cola se habilita en la Etapa 3" y no cambia ninguna visita.
- Criterios de aceptación:
  - [ ] Una prueba con BD temporal confirma el `409` y que ninguna fila cambió.

### T10 — Desactivar "Procesar Cola" (tablero)
- Estado: APROBADA · commit 902e850. Botón deshabilitado con la nota "Disponible en la Etapa 3"; ya no hay `fetch` a `procesar-cola`.
- Ejecutor: ejecutor-frontend
- Archivos: `FRONTEND/index.html`
- Qué hacer: el botón "Procesar Cola" aparece deshabilitado, con la nota "Disponible en la Etapa 3", y no hace ninguna llamada.
- Criterios de aceptación:
  - [ ] `grep` muestra que el botón está `disabled` y que no queda `fetch` a `procesar-cola`.

Paralelismo: T8, T9 y T10 no comparten archivos y pueden correr a la vez.
