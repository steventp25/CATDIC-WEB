# Etapa 2 — Importador de datos de diseño (`elementos_diseno`)
Estado: REPLANTEADA y APROBADA (Steven, 24/10/2026: aprobó el plan obra + vectorial/sellado + visitas por subida o Dropbox). T1 y T2: APROBADAS (PR #4 y #3). T0 y T3–T6 originales: REEMPLAZADAS. Siguen abiertas las decisiones 1–3 de la sección nueva.

### Respuestas de Steven
- 22/10/2026: "Sí, manda T1 y T2 de la Etapa 2 al Ejecutor. Las hace Claude Code." → T1 y T2: Agente Claude Code.
- 22/10/2026, tras la Evaluación 1: T2 → "Sí, push y PR". T1, criterio 2 (BD real) → "Verificar al fusionar": se abre el PR con ese criterio pendiente; después de la fusión y del primer arranque se comprueban el respaldo, la fila `MIGRACION_ELEMENTOS_DISENO`, las 15 columnas y `/api/dashboard` 200.
- 22/10/2026, en la sesión del Ejecutor (antes de "Verificar al fusionar"): "Autorizo migrar la BD real catdic_local.db con respaldo previo, usando la rama claude/etapa2-t1-esquema, y verificar /api/dashboard." → la BD real se migró a las 09:54 y el Auditor lo reverificó (Evaluación 2).
- 23-24/10/2026, respuestas a P1–P3 (transmitidas por la sesión principal, con sus palabras):
  - P1: "creo que lo vamos a hacer que cada usuario vamos a decir que cree una obra y le coloque el plano en el programa el mismo. mas adelante podemos hacer la conexion en dropbox porque las carpetas no esta tambien organizado en el momento."
  - P2: "no, esos se tienen que generar con el plano estructural."
  - P3: "te lo subo cuando haga la prueba"
  - **Consecuencia:** cambia el enfoque de la etapa.
    - No hay documentos `datos-diseno-*.md` que importar: la obra y su plano se crean en el programa.
    - La conexión con Dropbox (Etapa 1) deja de ser el camino principal, pero no se borra.
    - T3, el lector de `.md`, sale del plan.
    - T1 y T2 siguen sirviendo: el esquema y el validador.
    - La etapa se reescribe en BORRADOR cuando Steven responda las preguntas Q1–Q3 (abajo).

- 24/10/2026, respuestas a Q1–Q3 (planificador):
  - Q1 "Lectura + confirmar". El programa lee los datos de diseño del PDF y **todos** quedan `pendiente de verificar` hasta que el usuario los confirma (Regla de Oro).
  - Q2 "Dibujar recuadro". El usuario dibuja los recuadros de LOCALIZACION y DETALLE sobre el plano en el tablero.
  - Q3 "Carpeta local". Los planos subidos se guardan en una carpeta local configurable, fuera de git y de Dropbox.

## Objetivo
Cargar en `elementos_diseno` (Capa 1, §4.1) los datos de planos **ya documentados** de Terra Living (S5, S4, S3: columnas, muros, pórticos, losas) y de Torre P16 (Losa E-9), con un importador que:
- valida cada elemento con el motor de reglas (EJES §4.4, tipo y recubrimiento §4.5, ID + Nivel + Ejes §4.2);
- marca cada campo como `confirmado` o `pendiente de verificar`;
- manda a la Mesa de Dudas, como `DUDA_BLOQUEANTE`, todo lo que falte o se contradiga.

Se puede repetir sin duplicar y queda registrado en `auditoria`. **Ningún valor de diseño sale del código ni del plan: todo viene del documento fuente.**

## Discrepancias CLAUDE.md vs repositorio (verificadas el 22/10/2026)

- **R1. Bloqueante: los datos "ya documentados" no están en el repositorio ni en el disco.**
  - La skill `informes-catdic` dice que viven en el **Proyecto CATDIC de claude.ai**, como `informes/datos-diseno-<proyecto>.md`. Su formato está en `informes/plantilla-datos-diseno.md` y en el manual `informes/manual-sistema-informes.md` (§2.2 lista los campos por tipo de elemento).
  - No encontré ninguno de esos archivos:
    - repo;
    - `C:\Users\Steve` (hasta 6 niveles);
    - Dropbox, incluidas `SISTEMAS CATDIC\IA` y `TERRA LIVING\INFORMES\1.SOFTWARE`. Ahí solo hay bases FileMaker `.fmp12`, un `ELEMENTOS.csv` que solo trae nombres de campos, sin datos, e imágenes `Untitled_N.jpg`.
  - Tampoco están los scripts antiguos (`stp.py`, `vert.py`, `fi02.py`, `catdic_stp.py`) que menciona la Etapa 3.
  - **Sin esos documentos, esta etapa no puede cargar datos reales sin inventarlos.** Por eso la tarea T0 es que Steven los traiga.
- **R2. Tabla `elementos_diseno`:** existe y está vacía (0 filas). Columnas:
  - `uid`, `proyecto_id`, `id_elemento`, `tipo_elemento`, `nivel_rango`, `ejes`;
  - `hoja_plano_origen`, `archivo_plano_origen`;
  - `datos_diseno_json`, `estado_campos_json`, `recorte_planta_json`, `recorte_detalle_json`;
  - `actualizado`.
  
  Problemas de esquema:
  - no tiene `UNIQUE(proyecto_id, id_elemento, nivel_rango, ejes)`, que es la regla §4.2;
  - no guarda de qué documento fuente sale cada elemento (trazabilidad);
  - su comentario de `ejes` aún cita el "Archivo 02".
- **R3. PyMuPDF (`fitz`) y Pillow no están instalados** en Python 3.14. Sin `fitz` no se puede comprobar que la hoja y las coordenadas de recorte existan dentro del PDF sellado (Terra Living: 57 692 938 bytes). Para ver los recortes en el navegador o generar fichas hará falta en la Etapa 3.
- **R4. Torre P16 no tiene `PLANOS SELLADOS`.** Sus planos están en `ARCHIVO DEL CLIENTE\Nueva carpeta\`, en varias versiones:
  - `PLANOS ESTRUCTURALES P16 RESELLADOS 11-08-2026.pdf`;
  - `PLANOS RESELLADOS DE P16 Y UNO AGREGADO DE ESCALERA_8 EN TOTAL.pdf` (está dos veces);
  - un `.zip`.
  
  No se sabe cuál está vigente (P3). `proyectos.planos_sellados` de P16 sigue vacío.
- **R5. Hay archivos nuevos sin trackear que no son de esta sesión:** `.codex/` y `AGENTS.md`, en la raíz del repo. No se tocan ni se commitean sin que Steven diga qué son (P5).
- **R6. Intérprete:** como en la Etapa 1, todo se corre con `py -3.14`. En esta sesión el comando `py` no aparece en el PATH de bash; desde PowerShell se usa `C:\Users\Steve\AppData\Local\Python\pythoncore-3.14-64\python.exe`.

## Tareas

### T0 — Traer los documentos fuente al repositorio (Steven) — REEMPLAZADA (24/10: ya no hay documentos .md; ver T3n–T8n)
- Ejecutor: **Steven** (no hay ejecutor automático: los archivos están en claude.ai)
- Archivos: `DATOS_DISENO/fuentes/datos-diseno-terra-living.md`, `DATOS_DISENO/fuentes/datos-diseno-torre-p16.md`, `DATOS_DISENO/fuentes/plantilla-datos-diseno.md` y, si se puede, `DATOS_DISENO/fuentes/manual-sistema-informes.md`, copiados tal cual, sin editar.
- Depende de: —
- Qué hacer: descargar esos archivos del Proyecto CATDIC de claude.ai y ponerlos en esa carpeta. Si los datos de alguno de los dos proyectos están en otro lugar (chat, Excel, FileMaker), decir dónde.
- Criterios de aceptación:
  - [ ] Los archivos existen en `DATOS_DISENO/fuentes/`.
  - [ ] El planificador los lee y actualiza este plan (tipos de elemento, campos y formato reales) **antes** de ejecutar T3 a T5.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §4.1.

### T1 — Esquema de `elementos_diseno` y trazabilidad
- Ejecutor: ejecutor-backend
- Agente: Claude Code
- Estado: APROBADA · rama `claude/etapa2-t1-esquema` · a1891ff (Evaluación 2, 22/10/2026) · PR #4 abierto. Historial: 486 pruebas en verde. El Auditor considera seguro el código para la BD real (etapa-2-evaluacion.md, Evaluación 1). 22/10 09:54: el Ejecutor migró la BD real y dice que Steven lo autorizó. Respaldo `catdic_local.backup-20261022-095419.db`, auditoría id 26, 15 columnas (lo comprobó el planificador en solo lectura). Pendiente: que el Auditor lo reverifique.
- Archivos: `BACKEND/database.py`, `BACKEND/tests/test_database.py`
- Depende de: —
- Qué hacer:
  - Migración idempotente, con respaldo previo como en la Etapa 1:
    - `UNIQUE(proyecto_id, id_elemento, nivel_rango, ejes)`;
    - columna `fuente_json`, con el documento fuente, su sección o línea y su hash SHA-256;
    - columna `pendientes_json`.
  - Conservar las filas existentes (hoy 0) y las FK de `elementos_visita.elemento_diseno_uid`.
  - Actualizar el comentario que cita el "Archivo 02".
  - Registrar la migración en `auditoria`.
- Criterios de aceptación:
  - [ ] Hay pruebas con BD temporal: migrar conserva las filas; migrar dos veces no cambia nada; el `UNIQUE` rechaza un duplicado.
  - [ ] Con la BD real, existe el respaldo y `/api/dashboard` responde 200.
  - [ ] `py -3.14 -m pytest -q` en verde.
- Reglas del CLAUDE.md que aplican: §4.1, §4.2, §1.5.

### T2 — Validador de elementos de diseño (contrato del importador)
- Ejecutor: ejecutor-backend
- Agente: Claude Code
- Estado: APROBADA · rama `claude/etapa2-t2-validador` · ceca410 · PR #3 abierto. 520 pruebas en verde (38 nuevas). Observaciones no bloqueantes y condiciones para T4 en etapa-2-evaluacion.md (Evaluación 1).
- Archivos: `BACKEND/importadores/__init__.py`, `BACKEND/importadores/validador_diseno.py`, `BACKEND/tests/test_validador_diseno.py` (todos nuevos)
- Depende de: —
- Qué hacer:
  - `validar_elemento_diseno(dict) -> {elemento_normalizado, estado_campos, dudas}`. Usa `reglas_ingenieria.py` para lo siguiente:
    - tipo con categoría y recubrimiento (`obtener_categoria_elemento`); un tipo desconocido o metálico → duda;
    - EJES con el formato §4.4 según el tipo: losas `—`, platea área, prima, cruce, muro, viga y tramo;
    - un EJES que no cumple el formato → `DUDA_BLOQUEANTE`; nunca se reformatea adivinando.
  - Campos obligatorios: `id_elemento`, `tipo_elemento`, `nivel_rango` (tal como está impreso en la hoja, §4.2), `ejes`, `hoja_plano_origen` y `archivo_plano_origen`. Si falta alguno → `pendiente de verificar` + duda.
  - En `datos_diseno_json` se guarda tal cual lo que trae la fuente. Cada valor queda `confirmado` si la fuente lo da, o `pendiente de verificar` si la fuente lo marca así o no lo trae.
  - **No calcula cuantías ni recubrimientos sumados**: eso es Capa 3 (§4.1) y se calcula al generar.
  - La lista de campos por tipo se fija después de T0, con el §2.2 del manual. Hasta entonces, las pruebas usan datos `# SINTÉTICO` y los ejemplos de EJES del CLAUDE.md.
- Criterios de aceptación:
  - [ ] Hay pruebas para estos casos: losa con EJES distinto de `—` → duda; muro con `FILA` → duda; falta `hoja_plano_origen` → pendiente + duda; tipo metálico → pendiente; elemento completo → 0 dudas.
  - [ ] `py -3.14 -m pytest -q` en verde.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §4.1, §4.2, §4.4, §4.5, error #11.

### T3 — Lector del documento `datos-diseno-<proyecto>.md` — REEMPLAZADA por T5n/T6n
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/importadores/lector_datos_diseno.py`, `BACKEND/tests/test_lector_datos_diseno.py` (nuevos)
- Depende de: T0 (formato real), T2
- Qué hacer:
  - Leer el formato de `plantilla-datos-diseno.md` y convertir cada elemento en el `dict` que espera T2. Se conservan la sección y la línea de origen, para `fuente_json`.
  - Lo que el documento marque como pendiente, o lo que no se pueda leer sin adivinar, queda `pendiente de verificar`.
  - Una contradicción dentro del documento (por ejemplo, planta contra detalle) → `DUDA_BLOQUEANTE` (§4.2).
- Criterios de aceptación:
  - [ ] Una prueba con el archivo real de Terra Living cuenta los elementos por tipo y nivel y los compara con los conteos que el propio documento declara (o con la lista que confirme Steven).
  - [ ] Ningún valor aparece en la salida si no está en el documento (prueba de ida y vuelta: cada valor de salida se encuentra en el texto fuente).
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §4.2.

### T4 — Importación idempotente y endpoints — REEMPLAZADA por T4n/T6n
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/importadores/importador_diseno.py` (nuevo), `BACKEND/main.py`, `BACKEND/tests/test_importador_diseno.py` (nuevo)
- Depende de: T1, T2, T3
- Qué hacer:
  - `importar_datos_diseno(proyecto_id, ruta_fuente)` hace un *upsert* por `(proyecto_id, id_elemento, nivel_rango, ejes)`.
  - No pisa un campo que Steven ya resolvió en la Mesa de Dudas.
  - Si el hash de la fuente no cambió, no toca nada.
  - Crea `DUDA_BLOQUEANTE` en `dudas_y_hallazgos`, con `id_elemento` y `campo_afectado`, sin duplicarlas.
  - Registra cada importación en `auditoria` (`IMPORTADOR`/`IMPORTAR_DISENO`), con conteos.
  - Comprueba que `archivo_plano_origen` coincide con un PDF de `PLANOS SELLADOS` del proyecto. Si no coincide → duda.
  - Endpoints:
    - `POST /api/proyectos/{id}/importar-diseno`;
    - `GET /api/proyectos/{id}/elementos-diseno`, que devuelve la lista con estado y pendientes.
- Criterios de aceptación:
  - [ ] Pruebas con BD temporal: la primera importación crea N elementos; la segunda crea 0 y no cambia nada; un campo pendiente produce una duda; una duda resuelta no se pisa.
  - [ ] Con la BD real y el documento real de Terra Living: el `POST` responde 200 y los conteos coinciden con T3; el `GET` devuelve los elementos.
  - [ ] Hay una fila de auditoría por importación.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §1.5, §4.1, §4.2.

### T5 — Torre P16 (Losa E-9) — REEMPLAZADA por T8n
- Ejecutor: ejecutor-backend
- Archivos: `BACKEND/tests/test_importador_diseno.py`, más un cambio de datos en la BD real hecho con el importador de T4 (no hay código nuevo, salvo lo que exija el formato de P16)
- Depende de: T4, P3
- Qué hacer:
  - Importar `datos-diseno-torre-p16.md`, solo la Losa E-9.
  - Fijar `proyectos.planos_sellados` de P16 con el PDF vigente que indique Steven (P3) y registrarlo en `auditoria`.
  - EJES de la losa: `—` (§4.4).
- Criterios de aceptación:
  - [ ] La Losa E-9 está en `elementos_diseno` con EJES `—`, su hoja de origen y su archivo vigente.
  - [ ] Sus pendientes están en la Mesa de Dudas.
- Reglas del CLAUDE.md que aplican: §4.4, §4.2, Regla de Oro #1.

### T6 — Vista de elementos de diseño en el tablero (solo lectura) — REEMPLAZADA por T7n
- Ejecutor: ejecutor-frontend
- Archivos: `FRONTEND/index.html`
- Depende de: T4 (contrato del `GET`)
- Qué hacer:
  - Sección "Elementos de diseño" por proyecto, con estas columnas: ID, tipo, nivel, EJES, hoja de origen, nº de pendientes.
  - Los campos `pendiente de verificar` van resaltados.
  - Botón "Importar datos de diseño" que llama al `POST` de T4 y muestra un resumen.
  - No se calculan valores ni se muestran datos de ejemplo.
- Criterios de aceptación:
  - [ ] Con el backend corriendo se ve la lista de Terra Living (comprobado en el navegador).
  - [ ] Con el backend apagado aparece un aviso de error.
- Reglas del CLAUDE.md que aplican: Regla de Oro #1, §5.2.

### Respuestas de Steven a las decisiones 1–3 y P3 (24/10/2026)
- 1. Confirmación por lote: "si".
- 2. Subir visita: "pdf siempre".
- 3. Sin vectorial de la misma versión: "se agrega el ocr o se procesa en el chat". Queda fuera del MVP; tarea futura.
- P3, plano de P16: Steven indicó `PROYECTO P16\ARCHIVO DEL CLIENTE\Nueva carpeta\PLANOS ESTRUCTURALES P16 APROBADOS MIVED.pdf`.
  - El planificador lo revisó en solo lectura: 17 hojas de 2592×1728, **todas imagen, sin texto** (iLovePDF, 01/07/2025).
  - En la misma carpeta, `PLANOS ESTRUCTURALES P16 PDF 26-09-2024 SIN SELLOS.pdf` es **vectorial**: 17 hojas y 14 714 palabras. Es candidato a vectorial equivalente; lo certifica el usuario.
  - También hay juegos **resellados** posteriores: `PLANOS RESELLADOS DE P16 Y UNO AGREGADO DE ESCALERA_8 EN TOTAL.pdf` (8 hojas, imagen) y `26.08.2026 PLANOS RESELLADOS\…RESELLADOS 11-08…` (5 hojas, imagen, RICOH). Pueden reemplazar hojas del aprobado.
  - 24/10: Steven señaló `PLANOS ESTRUCTURALES P16 PDF 26-09-2024 SIN SELLOS.pdf` como el vectorial de P16. Para T8n:
    - vectorial: SIN SELLOS;
    - sellado: APROBADOS MIVED;
    - la certificación se hace al subirlos en el programa (T4n).
  - Sigue pendiente saber qué hojas reemplazan los juegos resellados.

### Hechos y decisiones (24/10/2026)
- El PDF sellado de Terra Living es un **escaneo** (RICOH, 39 hojas, sin texto). El vectorial `PLANOS ESTRUCTURALES TERRALIVING.pdf` (41 hojas, 83 capas, del 10/03/2026) es idéntico a `2026.03.10 - EST - TERRA LIVING.pdf`.
Decisiones de Steven (24/10):
1. Está preguntando a su jefa si se pueden obtener **los PDF vectoriales de la misma versión que los sellados**. Si se puede, **solo se usa el vectorial** para extraer los datos. Además, **el plano de cada obra se puede cambiar**.
2. **La comprobación de que el vectorial corresponde al sellado la hace el usuario**, no el programa.
3. **Formulario de nueva obra:** plano vectorial, plano sellado y toda la información general del proyecto.
4. **Después de crear la obra, dos opciones para las visitas:** conectar con Dropbox o subir las visitas a la obra.

Consecuencias:
- Sale del plan la comparación automática hoja por hoja (SSIM, alineación).
- Sale el OCR del MVP.
- El sellado se guarda como documento legal de referencia, que se cita en los informes, y el vectorial es la fuente de lectura.

## Tareas nuevas (APROBADAS por Steven el 24/10/2026): obra con plano vectorial + sellado, extracción del vectorial, visitas por subida o Dropbox

### T3n — Reconocimiento del PDF vectorial (solo lectura, informe)
- Ejecutor: ejecutor-backend · Agente: Claude Code
- Estado: APROBADA (Evaluación 3 de etapa-2-evaluacion.md) · b2f2db7 · push hecho, PR por abrir · rama `claude/etapa2-t3n-reconocimiento-plano`
- Archivo: `PLANES/etapa-2-reconocimiento-plano.md`
- Sobre `PLANOS ESTRUCTURALES TERRALIVING.pdf`, que es idéntico a `2026.03.10 - EST - TERRA LIVING.pdf`.
- El informe responde:
  - cuál es el **título impreso de cada hoja** y su número "/36" (§4.2);
  - qué capas se ven al imprimir y cuáles están ocultas (solo se extrae de las visibles);
  - si las tablas de aplicación (columnas, zapatas, losas Asxi/Asyv, muros) se leen como texto con coordenadas, con filas literales de ejemplo;
  - si los globos de los ejes y los ID de la planta son texto;
  - si hay rótulos de detalle (S1, S2, "TIPICO");
  - cuáles son las 2 hojas de más frente al sellado, para avisar a Steven.
- No se copia nada al repo.

### T4n — Formulario "Nueva obra" (planos + datos del proyecto)
- **Backend:**
  - `POST /api/proyectos` crea la obra con los datos generales: nombre, licencia, solicitud, residente, dirección, provincia, sector e inicio de obra. Usa los campos de T7a más `inicio_obra`.
  - `POST /api/proyectos/{id}/planos` sube **dos archivos**:
    - el **vectorial** es obligatorio para extraer los datos;
    - el **sellado** es obligatorio como referencia legal.
  - Cada subida guarda la revisión y la fecha, más una **casilla obligatoria "Certifico que el vectorial corresponde a la versión sellada"**. Queda auditada con el usuario y la fecha (decisión 2: la comprobación la hace el usuario).
  - Se guarda en una carpeta local (`CATDIC_DATOS_RAIZ` o `<home>\CATDIC-DATOS\<obra>\planos\`), sin sobrescribir nunca y con sha256.
  - **Cambiar el plano** (decisión 1): una subida nueva queda como vigente, el anterior pasa a histórico y los elementos extraídos del plano anterior se marcan "plano cambiado: revisar".
- **Frontend:** formulario "Nueva obra" con los dos archivos y los datos, y un botón "Cambiar plano" en cada obra.
- **Datos del usuario, según T3n (el plano no los da):**
  - en la obra, una tabla de **equivalencias E-n ↔ nivel** (por ejemplo E-1 = SOTANO S7) y la **asignación de losas L# → tipo** (A/B/C);
  - el emparejamiento de las hojas vectorial ↔ sellado, con las hojas de más marcadas, y cuál de las dos plantas "DE TECHO" es cuál.

  Lo que Steven escribe queda `confirmado` por ser él la fuente, con auditoría. Lo que falte queda pendiente + `DUDA_BLOQUEANTE`.
- **Depende de:** PR #4 y T7a. Tabla nueva `planos`.

### T4v — Visitas de la obra: subir o conectar con Dropbox (decisión 4)
- Después de crear la obra se ofrecen dos opciones:
  - **(a) Subir visita:** el usuario sube el PDF de la visita, su fecha y su clase. Se guarda en la carpeta local de la obra y se registra en `visitas`.
  - **(b) Conectar con Dropbox:** el usuario indica la carpeta de visitas de esa obra en Dropbox. Se valida y se guarda con auditoría, como en D4 de Codex, y se reutiliza el sincronizador de la Etapa 1 sobre esa ruta.
- En los dos casos, al terminar se ejecuta el lector de visitas de T3 (Etapa 3). Si quedan dudas, se abre la Mesa de Dudas (T5b, respuesta 13 de Steven).
- **Depende de:** T3, T4 y T5b de la Etapa 3, y de T4n.

### T5n — Visor y recuadros
- El visor muestra el **vectorial**.
- Los recuadros de LOCALIZACION y DETALLE se **proponen**:
  - la localización, en el cruce de ejes leído de los globos o en el bbox del ID;
  - el detalle, por su rótulo.
- El usuario confirma o corrige los dos recuadros. Las coordenadas se guardan en puntos del vectorial.

### T6n-a — Núcleo del lector de planos (módulo puro, sin BD), según T3n
- Ejecutor: ejecutor-backend · Agente: Claude Code
- Estado: APROBADA (Evaluación 4) · 463c322 · rama `claude/etapa2-t6na-lector-plano`
- Archivos: `BACKEND/plano/__init__.py`, `BACKEND/plano/lector_plano.py` y `BACKEND/tests/test_lector_plano.py`, todos nuevos. Va en `plano/` para no depender del PR #3.
- Qué hacer: funciones puras que devuelven **candidatos** con su fuente (archivo, página, bbox y número de hoja). No escriben en la BD.
  1. **Índice de hojas:** número `NN` junto a `/36` del cajetín, con `rotation_matrix` en las hojas giradas, y los títulos impresos debajo de cada dibujo.
  2. **Tablas por posición:**
     - se anclan a su encabezado;
     - las filas se agrupan por `y` con tolerancia (±4 pt) y se ordenan por `x`;
     - una celda que no encaja en una columna → pendiente, nunca se rellena por vecindad;
     - para el MVP: la tabla de acero en losa (tipos A/B/C), la tabla de zapata de muro de lindero y la tabla de f'c por rango E-n.
  3. **Globos de eje:** solo el texto de 1 o 2 caracteres rodeado por un círculo vectorial en el margen de la planta, nunca una "A" cualquiera.
  4. **ID en planta** (C#, L#, MH#, V-…) con su bbox. **No** se asignan a un cruce de ejes en esta tarea.
  5. **Notas de modificación:** unir líneas y detectar "SE MODIFICO", "EN REEMPLAZO" y "PLANO ANTERIOR" → candidato a duda.
  6. **Rótulos S-1/S-2:** su clave lleva la hoja.
- **No resuelve** E-n ↔ nivel ni L# ↔ tipo: los da el usuario (T4n).
- Criterios:
  - [ ] pruebas `# SINTÉTICO` con PDF generados con PyMuPDF: tabla con celdas desalineadas ±3 pt, hoja girada 270°, una "A" suelta que no es un globo, nota partida en 3 líneas;
  - [ ] corrida de solo lectura sobre el vectorial de Terra Living, con un informe en el reporte (no en el repo): 41 hojas indexadas; las filas A, B y C de p10 y p26 y las de p6 coinciden con T3n; los globos de p26 salen A, B, C y 1-4; la nota de la p19 se detecta;
  - [ ] pytest en verde.

### T6n — Extractor desde el vectorial (MVP: tablas de aplicación)
- Solo lee texto de las **capas visibles**.
- Hace primero el índice de hojas y niveles por el título impreso, y después las tablas de aplicación.
- Cada valor lleva su fuente: archivo, revisión, hoja y bbox.
- Comprobaciones cruzadas: el total de barras, las unidades, los rangos de entrepiso expandidos sin adivinar y que no haya ID duplicados en el mismo nivel.
- **Todo queda `pendiente`.**
- Los pórticos (elevaciones por tramo, §4.3) quedan para una tarea posterior.

### T7n — Confirmación
- **Confirmación por lote** de una tabla completa, con el recorte del plano al lado, cuando las comprobaciones salen en verde.
- **Uno por uno**, a través de la Mesa de Dudas, cuando hay contradicciones o huecos.
- Auditoría con el usuario, el lote y los valores.

### T8n — Prueba completa con Torre P16, cuando Steven suba sus planos.

### Se eliminan
- La comparación automática vectorial/sellado (T4bn).
- El OCR. Si algún proyecto no tiene vectorial, se replanteará entonces.

## Riesgos que hay que vigilar (en el plan)
- **El mismo ID en varios niveles.** El nivel sale del título impreso de la hoja, nunca de la cercanía.
- **Detalle típico frente a detalle propio.** Si hay dos candidatos → duda.
- **Texto de capas ocultas** del vectorial. Solo se lee lo visible.
- **El vectorial cambia y el sellado no** (o al revés). La certificación del usuario queda auditada, y al cambiar el plano los datos se marcan para revisar.

## Decisiones que quedan para Steven
1. ¿Aceptas **confirmar por lote** una tabla completa, viendo el recorte al lado?
2. En "Subir visita", además del PDF de la visita, ¿quieres subir **fotos sueltas**, o siempre llega un PDF?
3. ¿Qué haces si la jefa **no** puede dar el vectorial de la misma versión: esa obra queda sin extracción automática (todo a mano) o se agrega el OCR más adelante?

## Verificación
- **T3n:** el Auditor contrasta el informe con el PDF real, en solo lectura.
- **T4n y T4v:** pruebas `# SINTÉTICO` y verificación en el navegador contra una copia de la BD:
  - crear la obra con los dos planos y la casilla;
  - cambiar el plano;
  - subir una visita y conectar una carpeta, comprobando que el panel de dudas se abre.
- **T6n:** con el vectorial real de Terra Living, cuenta de elementos propuestos frente a la tabla del plano. Ningún dato queda `confirmado` sin una acción del usuario.
- **T7n:** confirmar un lote deja auditoría por campo.

## Paralelismo (original, T1–T6)
- **T1 y T2** pueden correr ya, en paralelo: no comparten archivos y no dependen de T0.
- **T3** espera a T0 y T2. **T4** espera a T1, T2 y T3. **T5** espera a T4 y a la respuesta P3.
- **T6** espera a T4. Puede correr al mismo tiempo que T5, porque no comparten archivos.

## Pendientes de verificar / preguntas para Steven
- **P1 (bloquea T3–T5):** ¿puedes descargar del Proyecto CATDIC de claude.ai estos archivos y dejarlos en `DATOS_DISENO/fuentes/` (T0)?
  - `informes/datos-diseno-terra-living.md`
  - el de Torre P16
  - `informes/plantilla-datos-diseno.md`
  - `informes/manual-sistema-informes.md`
  
  Si los datos están en otro sitio (otro chat, Excel, FileMaker `SISTEMA STP-CATDIC 19-02-2026.fmp12`), ¿cuál es la fuente buena?
- **P2:** ¿esos documentos traen coordenadas de recorte (planta y detalle) en algún formato, por ejemplo página + rectángulo en puntos o píxeles a cierto dpi? Si no las traen, `recorte_planta_json` y `recorte_detalle_json` quedan `pendiente de verificar` y se definen en la Etapa 3.
- **P3:** ¿cuál es el plano vigente de Torre P16?
  - `PLANOS ESTRUCTURALES P16 RESELLADOS 11-08-2026.pdf`
  - `PLANOS RESELLADOS DE P16 Y UNO AGREGADO DE ESCALERA_8 EN TOTAL.pdf`
  
  ¿Los movemos o copiamos a una carpeta `PLANOS SELLADOS`? Si es así, lo haces tú: el sistema no escribe en Dropbox.
- **P4:** ¿instalo **PyMuPDF** (y Pillow) en Python 3.14? Con PyMuPDF el importador puede comprobar que la hoja citada existe en el PDF sellado y leer su título impreso (§4.2: "título impreso dentro de la hoja"). Sin él, esa comprobación queda para la Etapa 3.
- **P5:** en la raíz del repositorio aparecieron `.codex/` y `AGENTS.md`, que no creó esta sesión. ¿Son tuyos? ¿Se versionan o van al `.gitignore`?

## Fuera de alcance de esta etapa
- Extraer datos leyendo los planos PDF directamente (OCR o visión): solo se importan datos ya documentados.
- Generar recortes de imagen, fichas o PDFs (Etapa 3).
- Vincular `elementos_visita` con `elementos_diseno` (Etapa 3, Procesar Cola).
- Responder dudas desde el tablero (Mesa de Dudas, Etapa 3).
- Pendientes de la Etapa 1 (#18, #8, #4, #19, regla de la clase contraria): siguen en `etapa-1-evaluacion.md`.
