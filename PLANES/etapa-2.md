# Etapa 2 — Importador de datos de diseño (`elementos_diseno`)
Estado: APROBADO (Steven, 22/10/2026). Respuestas a P1–P5: pendientes.

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

### T0 — Traer los documentos fuente al repositorio (Steven)
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

### T3 — Lector del documento `datos-diseno-<proyecto>.md`
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

### T4 — Importación idempotente y endpoints
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

### T5 — Torre P16 (Losa E-9)
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

### T6 — Vista de elementos de diseño en el tablero (solo lectura)
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

## Paralelismo
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
