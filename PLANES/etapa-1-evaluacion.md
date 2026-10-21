# Evaluaciones — Etapa 1

## Evaluación del 21/10/2026

## Evaluación — Etapa 1: Sincronizador real de Dropbox + ingesta de visitas (T1–T7)
**Veredicto: BLOQUEADO**

Hay dos bloqueantes y los dos se corrigen rápido. La base (configuración, migración, escáner de solo lectura, sync idempotente, frontend) está bien hecha y verificada con datos reales.

### Bloqueantes

- **B1. `BACKEND/sync/sincronizador.py:105-139` (en concreto `:117` y `:127-128`), docstring `:11-12`; prueba que lo fija: `BACKEND/tests/test_sync_endpoint.py:440-444`.**
  - **Regla violada:** decisión del dueño P3 (PLANES/etapa-1.md:7): *"hay un STP con la misma fecha exacta… y, si la visita trae clase, con esa clase"*.
  - **Qué pasa:** el código aplica una regla más laxa, "sin la clase contraria". Un STP que no nombra ninguna clase cuenta como candidato. Además, para visitas `Mixta` no se comprueba la clase en absoluto.
  - **Efecto en la BD real:** la visita **#18** `18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026` (Completivo) quedó `Procesada` gracias a `Terra Living - STP - Losa y Vigas Entrepiso 4 Sotano S4 - 02-10-2026 v2.pdf`, cuyo nombre no dice "Completivo". `Procesada` está en `ESTADOS_AVANZADOS`, así que ningún sync posterior lo revisa. El cambio de regla no aparece en el Estado de T5 ni en las preguntas para Steven.
  - **Qué debe cambiar (una de dos):**
    - (a) Aplicar P3 al pie de la letra. Si la visita trae Parcial/Completivo, el STP debe nombrar esa clase. Un STP sin clase con la misma fecha manda la visita a `Con dudas`, con una `DUDA_BLOQUEANTE` en el campo `estado` que liste el candidato. Hay que definir el caso `Mixta`: lo prudente es que también vaya a duda.
    - (b) Que Steven acepte por escrito la regla laxa como enmienda de P3 en el plan.
    - En cualquiera de los dos casos hay que corregir la #18 en la BD real. Ejecutor: ejecutor-backend.

- **B2. `BACKEND/sync/parser_visitas.py:279-289` (fecha tomada del PDF) y `BACKEND/sync/sincronizador.py:200-204` y `:223-235`.**
  - **Regla violada:** Regla de Oro #1 (lo dudoso va a "Con dudas") y trazabilidad (§1.5).
  - **Qué pasa:** la visita **#9** `9 - LOSA S-6 PARCIAL` tomó la fecha `23/07/2026` del PDF `CORRECCIONES SUPERVISION 23-07-2026.pdf`. El propio plan (línea 192) pregunta a Steven si esa es la fecha de la visita o la de unas correcciones. Aun así, en la BD real quedó `fecha_visita='2026-07-23'`, `campos_pendientes_json='[]'`, `estado='Sin procesar'` y sin ninguna duda ni hallazgo.
  - **Por qué importa:** el origen de la fecha (`origen_fecha='pdf'`, `pdfs_origen`) no se guarda en `visitas`, solo sale en la respuesta del sync. En la Etapa 3 esa fecha llegaría al STP-MIVED como confirmada y sin rastro de dónde salió. La pregunta solo existe en un markdown, no en la Mesa de Dudas de la aplicación.
  - **Qué debe cambiar:**
    - Guardar el origen de la fecha y de la clase en la BD (en `nota` o en una columna JSON).
    - Para la #9, crear al menos una `DUDA_BLOQUEANTE` en `fecha_visita` hasta que Steven responda, o un `HALLAZGO_INTERNO` si Steven decide que no bloquea.
    - Si Steven responde antes del commit que 23-07-2026 sí es la fecha de la visita, basta con guardar el origen y documentar la respuesta en el plan.
    - Ejecutor: ejecutor-backend.

### Observaciones (no bloquean)

1. **Prioridad alta: "Procesar Cola" sigue simulado** (`BACKEND/main.py:109-125`, `FRONTEND/index.html:355-364`).
   - Ya existía y está fuera del alcance, pero ahora actúa sobre datos reales: pasaría #9, #11, #12 y #13 a `En revisión` sin generar nada.
   - Como el sync nunca toca estados avanzados, ese estado falso quedaría para siempre.
   - Recomendación: desactivar el botón o el endpoint hasta la Etapa 3, o avisar a Steven antes del commit.
2. La **#8** (carpeta COMPLETIVO frente a PDF "parcial") quedó como `HALLAZGO_INTERNO`. P1 respalda la prioridad de la carpeta, pero CLAUDE.md pide `DUDA_BLOQUEANTE` ante contradicciones. Ya está en las preguntas del plan; hoy no tiene efecto porque la #8 está `Con dudas` por la fecha.
3. **La migración falla si hay filas viejas con fecha no ISO.** `migrar_visitas` aborta con `IntegrityError` y el servidor no arranca si existen filas viejas con `fecha_visita` fuera de AAAA-MM-DD (por ejemplo `15/10/2026`). No se pierde nada (ROLLBACK), pero el mensaje debería decir qué filas son. En la BD real la tabla estaba vacía (0 filas conservadas), así que no aplica hoy.
4. **El plan no está al día:**
   - T5 "Qué hacer" (línea 135) todavía dice que `formatos_solicitados` sale de `formato_defecto` `["STP-MIVED","MIVED-FI"]`, que P4 dejó sin efecto.
   - El Estado de T3 dice "9 visitas siguen sin fecha"; el resultado real es 10 (T5 lo dice bien).
   - Los criterios de T1 a T4 siguen escritos con `python` en vez de `py -3.14`.
5. Dejan de estar `Con dudas` solo cuando se resuelve la Mesa de Dudas (Etapa 3): el sync nunca devuelve una visita de `Con dudas` a `Sin procesar`. Es una decisión prudente; conviene dejarla escrita.
6. En una visita ya avanzada (`Procesada`), el sync sigue actualizando `fecha_visita` y `clase` si cambian los nombres de los PDF (no si cambia la carpeta, porque eso crea otra ruta). Ese caso puede dejar `salida_json` desalineado con la fecha; no ocurre hoy.
7. Avisos de que `@app.on_event` está obsoleto y aviso de Starlette sobre `httpx`/`httpx2`. No afectan.
8. `archivos_json` guarda el mtime solo como dato informativo. Se verificó que ninguna fecha sale del mtime: `grep` en `sync/` muestra un único uso, en `escaner_dropbox.py:64`, y las pruebas `test_fecha_nunca_sale_de_mtime` y `test_fecha_nunca_sale_del_mtime` lo comprueban.

### Criterios de aceptación

**T1 — Configuración y BD probable**
- [x] Con `CATDIC_DB_PATH` en tmp, la BD real no se toca. Lo cubre `test_inicializar_bd_crea_la_bd_en_tmp_y_no_toca_la_real`. Además, el SHA-256 de `catdic_local.db` fue el mismo antes y después de toda la suite (`54d6c4e2…dd06`).
- [x] `py -3.14 -c "import fastapi.testclient"` funciona (httpx 0.28.1). `httpx>=0.28.1` está en `requirements-dev.txt`.
- [x] `py -3.14 -m pytest` en verde: 467 pruebas.

**T2 — Migración del esquema `visitas`**
- [x] La migración conserva la fila, los hijos y las FK, y el esquema nuevo acepta `pendiente de verificar` y `Mixta`. Lo cubren `test_migracion_conserva_fila_hijos_y_crea_respaldo` y `test_esquema_nuevo_acepta_pendiente_y_mixta_y_rechaza_otra`. Lo reproduje sobre una copia del respaldo real (esquema viejo).
- [x] Migrar dos veces no cambia nada: `{'migrada': False, 'motivo': 'ya migrada'}` y no crea un segundo respaldo.
- [x] Existe `BACKEND/catdic_local.backup-20261021-154317.db`, la auditoría tiene `MIGRACION_VISITAS` (id 2) y `/api/dashboard` responde 200 sobre una copia de la BD real.

**T3 — Lector de nombres de carpeta**
- [x] La prueba parametrizada recorre los 22 nombres reales. Los comparé uno a uno con `ls` del Dropbox real: coinciden carpetas y PDFs. Los 5 ejemplos del plan dan el resultado esperado.
- [x] pytest en verde.

**T4 — Escáner de Dropbox**
- [x] Pruebas con árbol falso en `tmp_path`: planos, visitas, carpeta sin PDF y ruta inexistente sin excepción.
- [x] El árbol no cambia tras escanear (`test_arbol_no_cambia_tras_escanear`), y `test_no_abre_ni_escribe_archivos` bloquea `open`/escrituras con monkeypatch.
- [x] Escaneo real en solo lectura: `supervision 5.1 22 [('TERRA LIVING -ESTRUCTURALES.pdf', 57692938)] 13`.

**T5 — Endpoint `POST /api/dropbox/sync`**
- [x] Primer sync crea N; el segundo crea 0 y no cambia estados (prueba). En una copia de la BD real contra el Dropbox real: 0 nuevas, 22 sin cambios, visitas y dudas idénticas.
- [x] Una visita `En revisión` sigue `En revisión`.
- [x] Una visita sin fecha queda `Con dudas` con `DUDA_BLOQUEANTE` en `fecha_visita`.
- [x] Una fila de auditoría por sync y proyecto. En la BD real: ids 9, 11, 12 y 13 con `SYNC/SINCRONIZAR_DROPBOX`.
- [x] Contra la BD real: auditoría id 9 registra `visitas_nuevas: 22`, y el dashboard devuelve 22.
- [ ] Regla P3 fiel a la decisión de Steven. **No cumplido**, ver B1.

**T6 — Rutas sembradas de P16 y Zoetry**
- [x] Las 3 `carpeta_dropbox` de la BD real existen en disco (`Path.exists()` da True las tres veces), con 2 correcciones auditadas (ids 4 y 5).
- [x] La ruta vieja se corrige una sola vez (`test_ruta_vieja_se_corrige_una_sola_vez`) y una ruta cambiada a mano no se toca.

**T7 — Botón real en el tablero**
- [?] El `POST` visible en la pestaña de red del navegador no lo pude comprobar (no arranqué el servidor, por la restricción). En el código está `fetch(\`${API}/api/dropbox/sync\`, { method: 'POST' })`.
- [x] Con el backend apagado: lo comprobé en el código, no en el navegador. Si `fetch` falla, se muestra `errorSync` ("El backend no responde…") en vez de "Sincronización completada". Los errores HTTP se leen con `leerError`.
- [x] Las fechas solo se muestran como DD/MM/AAAA (`formatearFecha`). Cualquier otro valor aparece como "pendiente de verificar"; la hora del sync también va en DD/MM/AAAA. No hay datos inventados en la interfaz.

**Reglas generales**
- [x] Dropbox en solo lectura: en `sync/` no hay `open`, escrituras, `rename`, `unlink`, `mkdir` ni `shutil`, y no se abren PDFs. Con el Dropbox real comparé `os.walk` + `stat` (tamaño y mtime_ns) de `LEVANTAMIENTO` e `INFORMES` antes y después de un sync: sin cambios.
- [x] Nada prohibido entra al commit:
  - `catdic_local.db` y `catdic_local.backup-*.db` (también la variante ` vN.db`) están ignorados por `*.db`; `__pycache__/` está ignorado.
  - No hay PDFs, fotos ni `.env`; `*.PDF` está ignorado gracias a `core.ignorecase=true`.
  - No hay secretos.
- [x] Arquitectura desacoplada: `config.py` + `sync/` separado de `main.py`. La raíz de Dropbox no aparece quemada fuera de `config.py`.

### Pruebas ejecutadas
- `py -3.14 -m pytest -q` (desde BACKEND/) → `467 passed, 3 warnings in 5.35s`. Sin pruebas saltadas: las de Dropbox real (Terra, P16, Zoetry) sí corrieron.
- `py -3.14 -c "import main"` → `import main OK`.
- `py -3.14 -c "import fastapi.testclient, httpx"` → `testclient OK 0.28.1` (con `StarletteDeprecationWarning` sobre `httpx2`).
- `sha256sum BACKEND/catdic_local.db` antes de pytest, después de pytest, después de `import main` y después del sync sobre la copia → siempre `54d6c4e28c1255ada07bc1718772bb3b7f836bef52710fec688153b9ed32dd06`. La BD real no cambió.
- Lectura de la BD real en solo lectura (`mode=ro`):
  - Visitas: 22, todas de `terra-living`.
  - Estados: `Con dudas` 11, `Procesada` 7, `Sin procesar` 4 (#9, #11, #12, #13).
  - Dudas: `DUDA_BLOQUEANTE` fecha_visita 10, clase 5, archivos_json 1 (la #19); `HALLAZGO_INTERNO` clase 1 (la #8). Todas sin resolver.
  - `elementos_visita` y `elementos_diseno` vacías (0 filas), sin violaciones de FK, `integrity_check` ok.
- Sync sobre una copia de la BD real (en el scratchpad) contra el Dropbox real con `TestClient` → `dashboard 200 22`, `sync 200`, `terra-living supervision 5.1 0 0 22 11 7 0 [] []`, P16 y Zoetry `no soportado en esta etapa`, `visitas iguales True dudas iguales True`, `dropbox sin cambios True True`.
- `migrar_visitas()` dos veces sobre una copia del respaldo real (esquema viejo) → `1a True 0 [clase_detalle_json, archivos_json, campos_pendientes_json]` / `2a {'migrada': False, 'motivo': 'ya migrada', 'respaldo': None}`.

### Pendientes de verificar (para la Mesa de Dudas)
- **#9:** ¿`CORRECCIONES SUPERVISION 23-07-2026.pdf` da la fecha de la visita o la de unas correcciones? (B2)
- **#18 y regla P3:** ¿un STP sin clase en el nombre, con la misma fecha, basta para marcar `Procesada`? ¿Qué se hace con las visitas `Mixta`? (B1)
- **#8:** carpeta COMPLETIVO frente a PDF "parcial": ¿`HALLAZGO_INTERNO` o `DUDA_BLOQUEANTE`?
- **#4:** ¿se acepta la fecha `06.05.2026` (formato `DD.MM.AAAA`) en nombres de PDF?
- **#19:** carpeta sin PDF de la visita.
- ¿Se desactiva "Procesar Cola" (simulado) hasta la Etapa 3, ahora que la cola tiene visitas reales?

---

## Reevaluación del 21/10/2026 (después de T8, T9 y T10)

## Evaluación — Etapa 1: Sincronizador real de Dropbox + ingesta de visitas (T1–T10)
**Veredicto: APROBADO**

B1 y B2 están resueltos. Procesar Cola quedó desactivado en el backend (T9) y en el tablero (T10). T1–T7 no tienen regresiones, la Regla de Oro se cumple y Dropbox no se modificó. No queda ningún bloqueante; las observaciones de abajo pueden quedar para la Etapa 3.

### Bloqueantes
- Ninguno.

### Cómo quedaron B1 y B2
- **B1 (regla P3).** `BACKEND/sync/sincronizador.py:154-196` (`evaluar_p3`):
  - La visita solo pasa a `Procesada` si hay **un** STP de su misma fecha y su nombre trae **solo** la clase de la visita (`g["clases"] == [clase]`, `:177`), sin otro STP de esa fecha sin clase.
  - Va a `Con dudas`, con `DUDA_BLOQUEANTE` en `estado` y la lista de candidatos, si se da cualquiera de estos casos:
    - la visita es `Mixta` (o su clase está pendiente) y hay algún STP de su fecha (`:171-175`);
    - hay un STP sin clase (`:185-186`);
    - hay varios STP de su clase.
  - Corrección única (`:456-526`):
    - solo entran las `Procesada` cuyo estado viene del sync: origen `sync_p3` sin la marca `regla_p3=estricta`, o sin origen y con `salida_json` exactamente `{"stp":[rutas en 2.DATA PROCESADA]}`;
    - no toca una `Procesada` que trae otro origen, ni una cuya duda `estado` ya respondió Steven;
    - por cada visita corregida escribe una fila `SYNC/CORREGIR_P3_ESTRICTA`;
    - guarda el estado y la salida anteriores en `origen_datos_json.correccion_p3`.
  - Es idempotente: lo prueba el test y lo verifiqué sobre una copia de la BD real.
- **B2 (fecha de la #9).**
  - `origen_datos_json` se añade con `ALTER TABLE` idempotente (`BACKEND/database.py:302-332`) y se audita una sola vez (`MIGRACION_VISITAS_ORIGEN`).
  - La #9 guarda `{"fecha":"pdf","pdfs_fecha":["CORRECCIONES SUPERVISION 23-07-2026.pdf"],"clase":"carpeta"}`.
  - La confirmación de Steven está escrita en `PLANES/etapa-1.md:214`.

### Observaciones (no bloquean)
1. **Las decisiones del ejecutor en T8:**
   - **STP solo de la clase contraria → `Sin procesar`** (`sincronizador.py:194-196`). Es defendible: así se separan las dos #17. Pero ante la contradicción entre carpeta e informe, §4.2 se inclinaría por la duda, y no hay ninguna duda que la avise. El caso queda anotado en `origen_datos_json.stp_otra_clase`. Hoy no ocurre en los datos reales: no hay STP del 23-07, 31-07, 17-08 ni 19-08-2026. **Conviene que Steven lo confirme.**
   - **STP de su clase + otro sin clase → `Con dudas`.** Correcto: es el caso "más de un candidato" de P3.
   - **STP que nombra las dos clases → se trata como sin clase → `Con dudas`.** Correcto y prudente.
   - **`Procesada` antigua cuyo STP ya no está → `Con dudas`** (`:493-495`). Prudente: no la devuelve a `Sin procesar` sin preguntar.
     - Es asimétrico con la visita nueva: una `Procesada` antigua con solo un STP de la clase contraria también va a `Con dudas`, mientras que una visita nueva en esa situación va a `Sin procesar`.
     - En estos dos casos la duda dice "indica si alguno corresponde…: **ninguno**" (`:204`, `:209-211`) y no nombra el STP de la otra clase. Lo comprobé con datos sintéticos en una BD temporal.
     - Esta rama no tiene prueba en `test_sync_endpoint.py`.
   - **Origen del estado no rellenado en las 15 visitas antiguas que no son `Procesada`.** El origen de fecha y clase sí está en las 22. Le falta la clave `estado` a 11 `Con dudas` y 4 `Sin procesar` (#9, #11, #12, #13). No inventa nada, pero el "Qué hacer" de T8 decía "rellenar el origen de las 22". Ese valor se puede calcular sin adivinar (`sync_dudas` o `sync_sin_stp`). No afecta el comportamiento.
2. **Riesgo para la Etapa 3.** La corrección corre en **cada** sync, no una sola vez en total, y reconoce como "del sync" toda `Procesada` sin origen cuya `salida_json` sea `{"stp":[…en 2.DATA PROCESADA]}` (`:479`). Si el generador de la Etapa 3 deja justo esa forma y no escribe `origen_datos_json.estado`, el sync podría reevaluar una visita generada de verdad y pasarla a `Con dudas`. **Contrato para la Etapa 3:** el generador debe escribir `origen_datos_json.estado` (por ejemplo `"generador_etapa3"`). La prueba `test_correccion_no_toca_procesada_con_origen_ajeno_al_sync` ya cubre ese caso.
3. Cuando Steven responda una fecha o una clase en la Mesa de Dudas, el origen viejo (`fecha: null`) se queda como estaba (`:421-423`). La Etapa 3 debería escribir algo como `"mesa_dudas"`.
4. El plan sigue sin actualizar en tres cosas que ya señaló la evaluación anterior:
   - T3 dice "9 visitas sin fecha" (`etapa-1.md:86`); son 10.
   - T5 "Qué hacer" sigue con `["STP-MIVED","MIVED-FI"]` (`:135`), que P4 dejó sin efecto.
   - Los criterios de T1–T4 siguen con `python`.
   Además, la pregunta de la #9 sigue abierta en "Pendientes" (`:192`) aunque Steven ya respondió (`:214`).
5. Siguen los avisos de obsolescencia (`@app.on_event`, `httpx`→`httpx2`). El mensaje 409 se ve con mojibake en la consola de Windows (cp1252); el JSON que se envía es correcto.
6. `.gitignore` no cubre `*.jpeg` (ya venía así). Hoy no hay ninguno en el diff.

### Criterios de aceptación
**T1–T7 (sin regresiones)**
- [x] T1: BD en `tmp` sin tocar la real. El SHA-256 de `catdic_local.db` (`d4b87ccd…4564`) fue el mismo antes y después de pytest y de `import main`. `httpx>=0.28.1` está en `requirements-dev.txt` y esa misma línea dice `py -3.14`.
- [x] T2: migración idempotente. Arrancar sobre la copia de la BD real no creó una segunda `MIGRACION_VISITAS` ni una segunda `MIGRACION_VISITAS_ORIGEN`.
- [x] T3/T4: las pruebas siguen en verde y no hay escrituras en `sync/`. `mtime` solo aparece en `escaner_dropbox.py:64`, como dato informativo.
- [x] T5: segundo sync sobre la copia real → 0 nuevas, 0 actualizadas, 22 sin cambios; visitas y dudas idénticas; una fila `SINCRONIZAR_DROPBOX` más.
- [x] T6: sin cambios.
- [?] T7: no comprobé en el navegador el POST en la pestaña de red. En el código está `fetch(\`${API}/api/dropbox/sync\`, { method: 'POST' })` (`index.html:332`). Las fechas solo se muestran como DD/MM/AAAA (`formatearFecha`) y la hora del sync también.

**T8**
- [x] Un STP sin clase de la misma fecha da `Con dudas`: `test_p3_estricta_stp_sin_clase_va_a_dudas` y `test_evaluar_p3_stp_sin_clase_no_basta`. Lo mismo para una visita `Mixta`: `test_p3_estricta_mixta_con_stp_de_su_fecha_va_a_dudas`.
- [x] En la BD real:
  - la #18 está `Con dudas` con su `DUDA_BLOQUEANTE` en `estado` (duda id 18, que lista `…Entrepiso 4 Sotano S4 - 02-10-2026 v2.pdf`);
  - siguen `Procesada` las otras 6: #14, #15, #16, las dos #17 y #20;
  - la #9 tiene `origen_datos_json.fecha = "pdf"`;
  - hay una fila de auditoría de la corrección (id 17).
- [x] Un segundo sync no cambia nada: lo muestra la auditoría id 20 (`sin_cambios: 22`, `corregidas_p3: []`) y mi sync sobre la copia.
- [x] `py -3.14 -m pytest -q` en verde: 482 pruebas.

**T9**
- [x] `POST /api/visitas/procesar-cola` → 409 sin abrir la BD (`main.py:113-116`). Lo cubren `test_procesar_cola_responde_409_y_no_toca_la_bd` y la prueba de repetición. Sobre la copia real también da 409 y las visitas y la auditoría quedan iguales.

**T10**
- [x] El botón tiene `disabled aria-disabled="true"` y la nota "Disponible en la Etapa 3" (`index.html:27-33`). No queda `fetch` a `procesar-cola`: los únicos `fetch` son `/api/dashboard` (`:310`) y `/api/dropbox/sync` (`:332`). El método `procesarCola` se eliminó.

**Reglas generales**
- [x] Regla de Oro #1: no hay datos inventados. Los datos de prueba están marcados `# SINTÉTICO`. El número de visita nunca se inventa. Lo que falta queda `pendiente de verificar` con su duda.
- [x] Dropbox en solo lectura: comparé `os.walk` + `stat` (1604 archivos de `LEVANTAMIENTO` e `INFORMES`) antes y después del sync sobre la copia: sin cambios.
- [x] Nada prohibido entra al commit:
  - `catdic_local.db`, `catdic_local.backup-*.db` y la variante ` vN.db` quedan ignorados por `*.db`;
  - también quedan ignorados `*.pdf` (con `ignorecase`), `*.jpg`, `*.png`, `.env` y `__pycache__/`;
  - en git no hay archivos `.db`, `.pdf`, imágenes ni `.env`, y no hay secretos.
- [x] La arquitectura sigue desacoplada (`config.py`, `sync/`, `main.py` fino). No se fabrican firmas ni se mezclan formatos (no aplica en esta etapa).
- Errores de §6 que aplican: #12 (fechas DD/MM/AAAA en la UI y en las dudas, nunca del mtime) → cumple. #15 (no sobrescribir): los respaldos llevan versión `vN` → cumple.

### Pruebas ejecutadas
- `py -3.14 -m pytest -q` (desde BACKEND/) → `482 passed, 3 warnings in 6.07s`.
- `py -3.14 -c "import main"` → `import main OK`.
- SHA-256 de `BACKEND/catdic_local.db` antes de pytest, después de pytest y después de `import main` → siempre `d4b87ccddc808c802523d4af1eee01809ceab66ffe80664b4df1cea139084564`.
- Lectura de la BD real con `mode=ro`:
  - Estados: `Con dudas` 12, `Procesada` 6, `Sin procesar` 4 (#9, #11, #12, #13).
  - Auditoría: `CORREGIR_P3_ESTRICTA` 1 (id 17, #18, `estado_anterior: Procesada`), `MIGRACION_VISITAS_ORIGEN` 1 (id 15, 22 filas existentes).
  - `integrity_check` ok, sin violaciones de FK.
- Copia de la BD real (en el scratchpad de la sesión), con `TestClient` contra el Dropbox real:
  - `sync 200`, `{'visitas_nuevas': 0, 'actualizadas': 0, 'sin_cambios': 22, 'con_dudas': 12, 'procesadas': 6, 'corregidas_p3': [], 'p3_confirmadas': []}`;
  - `visitas iguales True dudas iguales True`;
  - `procesar-cola 409`, `tras procesar-cola visitas iguales True True`;
  - `dashboard 200 22`;
  - `dropbox sin cambios True 1604`.
- `corregir_procesadas_p3` con datos sintéticos en una BD temporal:
  - Pasan a `Con dudas`, con duda y auditoría:
    - una `Procesada` sin STP de su fecha;
    - una con solo un STP de la clase contraria;
    - una `Mixta` con STP de su fecha.
  - Una `Procesada` con salida fuera de `2.DATA PROCESADA` no se toca.
  - Segunda pasada → `{'corregidas': [], 'confirmadas': []}`.
- `ls` en solo lectura de `INFORMES\2.DATA PROCESADA` (Terra Living): 7 STP y 6 MIVED. Ningún STP es del 23-07, 31-07, 17-08 ni 19-08-2026, así que las 4 `Sin procesar` están bien.

### Pendientes de verificar (para la Mesa de Dudas)
- **#18:** ¿`Terra Living - STP - Losa y Vigas Entrepiso 4 Sotano S4 - 02-10-2026 v2.pdf` es el STP de la visita Completivo del 02/10/2026? (duda `estado` id 18).
- **Regla de la clase contraria:** si solo hay un STP de la misma fecha con la clase contraria, ¿la visita queda `Sin procesar` (como ahora) o va a `Con dudas`?
- **#8:** carpeta COMPLETIVO frente a PDF "parcial": ¿`HALLAZGO_INTERNO` o `DUDA_BLOQUEANTE`? (sigue abierto)
- **#4:** ¿se acepta la fecha `06.05.2026` (`DD.MM.AAAA`) en nombres de PDF? (sigue abierto)
- **#19:** la carpeta no tiene PDF de la visita (sigue abierto).
- **Para la Etapa 3:** el generador debe escribir `origen_datos_json.estado`, y la Mesa de Dudas debe actualizar el origen de los campos que responda Steven.
