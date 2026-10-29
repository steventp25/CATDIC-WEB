# Etapa 3 — Fábrica de Supervisión (STP-MIVED, MIVED FI-01/02/03, CATDIC-STP)
Estado: Bloque 3A TERMINADO (23/10/2026), sus PR esperan a Steven. Bloque 3B APROBADO (Steven, 23/10/2026). T9 (CATDIC-STP) APLAZADA por decisión de Steven: no se usa todavía.

### Respuestas de Steven
- 22/10/2026: "Apruebo el bloque 3A de la Etapa 3 con tus propuestas en P1–P7: instala las librerías, caché en C:\Users\Steve\CATDIC-CACHE, salida en carpeta de pruebas, visitas #18 #19 #20, y empieza por T1 y T4 con Claude Code."
  - P1: se instalan PyMuPDF, Pillow, Playwright con Chromium y pypdf. Con esto queda resuelta también la P4 de la Etapa 2.
  - P2: la caché va en `C:\Users\Steve\CATDIC-CACHE\<proyecto>\<visita>\`.
  - P3: mientras se prueba, los generadores escriben en una carpeta de pruebas, no en Dropbox.
  - P4: visitas #18, #19 y #20 para T2.
  - P7: T1 y T4 → Claude Code, primero. El resto se asigna al enviarlo; T5 o T6 pueden ir a Codex.
  - Siguen pendientes: P5, P6 y P8.
- 22/10/2026, tras la Evaluación 1:
  - Push de T1 y T4: "Sí, push".
  - Clase `Mixta` desde la Mesa (O3): "No aceptar Mixta". Desde la Mesa solo se admiten Parcial o Completivo; el cambio va en la tarea de correcciones (T4b).
  - T4b: "Haz T4b completa (a, b, c, d) y agrégale el cambio de no aceptar Mixta. Claude Code."
  - Push de T4b: "Sí, push de T4b."
- 23/10/2026: "YA, ACABA EL PROGRAMA ESTABLECIDO, PARA LOS PASOS EJECUTALO CON LA ESTRUCTURA QUE YA TIENES DE PLANIFICADOR, EJECUTOR Y AUDITADOR".
  - El resto del bloque 3A (T2, T6, T3, T5) lo hace Claude Code con el ciclo plan → Ejecutor → Auditor.
  - Cada tarea con APROBADO se sube a su rama sin volver a preguntar. Los PR los abre y los fusiona Steven.
  - El bloque 3B queda sin tocar: sigue bloqueado por T0, P5, P6 y la Etapa 2.
- 23/10/2026, tras la Evaluación 5 (T3):
  - Duda id 20, editada a mano (B3): "Registrar auditoría". Se agrega una fila `MANUAL/CORREGIR_TEXTO_DUDA` con el texto anterior y el nuevo.
  - Normalizar etiquetas (O3 de T2, O2 de T3): "Sí, normalizar".
    - Antes de interpretar, `’` → `'` y mayúsculas (`mc` → `MC`, `c1` → `C1`).
    - `etiqueta_original` se guarda siempre literal.
- 23/10/2026, tras la Evaluación 8: "Sí, que el Ejecutor actualice §4.4 de CLAUDE.md y AGENTS.md con la decisión de etiqueta suelta = pendiente, en una rama con PR." → tarea de documentación en la rama `claude/spec-ejes-visita`.
- 23/10/2026, transmitido por la sesión principal: "USA ARIAL, NO ENTENDI LA ULTIMA P5. NO HAY PROBLEMA ENTONCES".
  - P6 → Arial en CATDIC-STP.
  - "No hay problema" → da por buenas las decisiones sobre `L5` (etiqueta suelta pendiente) y la fila de auditoría 36.
  - P5 sigue abierta: hay una propuesta en "Pendientes".
  - T0, parcial: entregó los scripts y las plantillas en `G:\My Drive\CATDIC\FORMATO CLAUDE\New folder\`.
- 23/10/2026: "Apruebo el bloque 3B con tus propuestas en P5, P9, P10 y P11. Empieza por T0b y T7a con Claude Code."
  - P5: se actualiza el FI del mismo nivel y tipo (` v2`/` v3`); si no existe, se parte del FI en blanco del proyecto, nunca del de otro nivel.
  - P9: 2 fotos en dos columnas; 3 fotos con 1 ancha arriba y 2 abajo.
  - P10: las fuentes van en `FABRICA/`, fuera de git.
  - P11: Steven llena los datos de cabecera desde el tablero o la API (T7a).
- 23/10/2026: "ESE FORMULARIO NO LO HAGAS TODAVIA, QUE ESE NO SE ESTA UTILIZANDO". CATDIC-STP (T9) queda **APLAZADA** hasta que Steven la pida; ya no hacen falta `FORMULARIOS MIVED.pdf` ni el logo. Aclaró además que los FI de Serenity son ejemplos de los 3 formularios oficiales del MIVED (FI-01 cimentaciones, FI-02 losas, FI-03 verticales).
- 23/10/2026, respuestas a las 17 dudas (`dudas-para-steven-etapa3.md`), con sus palabras:
  1. Encargado de obra = residente: "si".
  2. Fechas de autorización: "la misma fecha de la visita". Se escribe la fecha de la visita (parcial y completiva) y se conservan las anteriores. → T8b
  3. Dinteles del FI-02 (secciones 8-9) y cerramiento del FI-03 (sección 9): "no, estos se ubican". **Por aclarar** si se marcan siempre o solo cuando la visita los incluye. Mientras tanto, siguen sin marcar.
  4. Cierre al final: "si". → T8b
  5. Recubrimiento en PLANOS: "es lo mismo, pero lo puedes tomar de la norma para mas facil". Se queda §4.5.
  6. Elemento no soportado: STP "sin ella". Se queda como está (línea visible de no incluidos).
  7. Filas obligatorias: "no entendi". **Hay que volver a explicarlo.**
  8. Áreas ASTM: "si".
  9. Nombre del archivo con la clase: "no, debes de unirlos". **Por aclarar**.
  10. Inicio de obra, número de formulario y fecha del informe: "eso se llena a mano, el numero de formulario lo suministra el MIVED si los formularios son cerrados. asi que por el momento se llena a mano". Hacen falta campos manuales. → tarea futura
  11. Usuario en la auditoría: "si, … uno tiene que ser administrador y otro es de empleado o procesador de data". **Requisito nuevo: usuarios con roles.** → etapa o tarea aparte, con plan propio
  12. Sin internet: "si es posible que no dependa de internet seria un exito, que se sincronize cuando se conecte". → T11
  13. Rótulos de la Mesa de Dudas: "si. quiero que el panel de dudas salga cuando se introduzca las datas o los enlaces de los archivos". → T5b
- 23/10/2026, aclaraciones de Steven:
  - (3) Dinteles y cerramiento: "solo cuando la visita lo incluye". → T8b. La mampostería del FI-03 (sección 8) sigue sin marcarse nunca (§3.2).
  - (7) Filas obligatorias: "que pregunte". Se confirma el comportamiento de T7: si falta un dato, no se genera la ficha y se crea una duda.
  - (9) "el informe final y en el formulario colocar las dos visitas". El STP final de un nivel junta la visita parcial y la completiva, y el FI lista las dos visitas. → T7b
  - (11) Roles: el administrador gestiona usuarios, aprueba "y la capacidad de modificar el programa si amerita". El empleado o procesador de datos hace todo lo demás. → etapa propia (Usuarios y roles)
- 23/10/2026, sobre un FI sin filas libres de autorización: "c." Se agrega una fila nueva debajo de las existentes. → T8b
- 23/10/2026, sobre la visita 21 nueva en Dropbox: "si, esto es lo normal, siempre se estara subiendo visitas". Las pruebas no deben depender de cuántas carpetas tenga el Dropbox real. → T12
- Ajustes del planificador:
  - T2: la #19 no tiene PDF (duda `archivos_json`), así que se reemplaza por la #17 `17. COMPLETIVO VERTICALES S-4 28-09-2026`.
  - D1 (PR #6, decisiones de Steven): las rutas de caché y de salida no se fijan al usuario `Steve`.
    - Se leen en `config.py` desde las variables de entorno `CATDIC_CACHE_RAIZ` y `CATDIC_SALIDA_PRUEBAS`.
    - Si no están definidas, se usan `<carpeta del usuario>\CATDIC-CACHE` y `<carpeta del usuario>\CATDIC-SALIDA-PRUEBAS`.

## Objetivo
Al cerrar la etapa, el botón **Procesar Cola** hace esto con una visita `Sin procesar`:
- lee su PDF de visita y carga `elementos_visita` (Capa 2);
- cruza cada elemento con `elementos_diseno` (Capa 1);
- manda a la **Mesa de Dudas** todo lo que no cuadre;
- con lo que sí cuadre, genera los formatos pedidos (`STP-MIVED`; `FI-01/02/03` actualizando el existente; `CATDIC-STP`), siempre pasando por el auditor de los 18 errores y sin sobrescribir nunca un archivo;
- registra cada acción en `auditoria`.

La etapa se divide en dos bloques:
- **3A (infraestructura).** Se puede empezar ya: no necesita datos de diseño ni scripts viejos.
- **3B (generadores).** Necesita la Etapa 2 con datos reales y las fuentes de T0.

## Discrepancias CLAUDE.md vs repositorio (verificadas el 22/10/2026, solo lectura)
- **R1. No existen los scripts "probados"** `stp.py`, `vert.py`, `fi02.py` ni `catdic_stp.py` (§7, Etapa 3). Los busqué en el repositorio, en `CATDIC Dropbox` (SUPERVISION, SISTEMAS CATDIC), en OneDrive, Descargas, Documentos y Escritorio. En `SISTEMAS CATDIC\IA\UTILIDADES GENERADAS` solo hay un proyecto Django de cubicaciones. Lo más probable es que estén en el Proyecto CATDIC de claude.ai, como los datos de diseño de la Etapa 2.
- **R2. No existe la plantilla limpia `FORMULARIOS MIVED.pdf`** (base de `CATDIC-STP`, 10 hojas Carta). Sin ella, `CATDIC-STP` no se puede hacer.
- **R3. La fuente `Aptos Narrow` no está instalada** en `C:\Windows\Fonts` ni en las fuentes del usuario. Sí están `Arial Narrow` (`ARIALN*.TTF`) y `Calibri`. §1.6 la exige para `CATDIC-STP`.
- **R4. Python 3.14 no tiene ninguna de las librerías de la fábrica:** faltan `fitz` (PyMuPDF), `PIL` (Pillow), `playwright`, `docx`, `lxml` y `pypdf`.
- **R5. Nadie extrae la Capa 2.** La Etapa 1 solo leyó nombres de carpeta (fecha y clase); su plan dejó "leer el contenido del PDF de visita y cargar `elementos_visita`" para la Etapa 3.
  - Cada visita es **un solo PDF muy pesado**. Ejemplo: la #18 es `Losa y viga entrepiso 4 completivo (1).pdf`, de 327 184 403 bytes.
  - No sé si las etiquetas de las fotos vienen como texto del PDF o dibujadas dentro de la imagen (P4).
- **R6. `elementos_diseno` está vacía** (la Etapa 2 espera T0). Sin la Capa 1 no se puede llenar ninguna ficha: todo elemento iría a dudas.
- **R7. Formularios FI reales en Dropbox (Terra Living):**
  - Plantillas `FORMULARIOS\FI-01|02|03-26-STP-TERRALIVING.pdf`.
  - 12 FI no firmados numerados en `FORMULARIOS\MIVED\FORMULARIOS NO FIRMADOS\`. Su nombre no sigue el patrón §5.2 (`MIVED - <PROYECTO>-<ELEMENTOS NIVEL>.PDF`); se llaman, por ejemplo, `12. FI-02-26-STP-TERRALIVING LOSAS Y VIGAS ENTREPISO SOTANO -4 02-10-2026.pdf`.
  - En `INFORMES\2.DATA PROCESADA\` hay otros 6 `MIVED - TERRA LIVING-….PDF`.
  - No está claro cuál de las dos carpetas es la "existente" que §3.2 manda actualizar (P5).
- **R8. Ya hay STP reales generados** en `INFORMES\2.DATA PROCESADA\` (7 PDF). Sirven como **referencia visual** de maquetación (solo lectura), no como fuente de datos.
- **R9. Contratos ya disponibles en `reglas_ingenieria.py` (Etapa 0):**
  - `agrupar_log_fotografico_visita`, `seleccionar_fotos_m1`, `seleccionar_fotos_pick4`;
  - `calcular_grosor_recuadro_rojo`, `obtener_ruta_salida_sin_sobrescribir`, `formatear_fecha_ddmmaaaa`;
  - `interpretar_eje_de_visita`, `formatear_campo_ejes`, `calcular_cuantia_elemento`, `evaluar_medida_acero_obra`;
  - `auditar_datos_ficha_antes_de_renderizar(ficha, formato)` y `auditar_archivo_pdf_generado(ruta, destino_existia_antes)`;
  - claves de ficha: `cuantia_declarada`, `seccion_b_m`, `seccion_h_m`, `barras_longitudinales`, `medidas_obra`, `tolerancia_visita_m`.

  El validador de diseño de la Etapa 2 (PR #3) también queda disponible. Errores #16, #17 y #18: no cubiertos; son de esta etapa.
- **R10. `main.py`:** `POST /api/visitas/procesar-cola` responde 409 (desactivado en la Etapa 1). No hay endpoints de dudas: el tablero muestra "Con dudas" sin el motivo.

## Tareas — Bloque 3A (sin datos de diseño)

### T0 — Fuentes de la fábrica (Steven)
- Ejecutor: **Steven**
- Archivos: `FABRICA/fuentes/` (nueva):
  - `stp.py`, `vert.py`, `fi02.py`, `catdic_stp.py`;
  - `FORMULARIOS MIVED.pdf`;
  - logo CATDIC (PNG o SVG).

  Todo copiado tal cual. La fuente `Aptos Narrow` se instala en Windows o se deja el `.ttf` en `FABRICA/fuentes/`.
- Depende de: —
- Criterios de aceptación:
  - [ ] Los archivos existen y el planificador actualiza las tareas T7 a T9 con lo que traen.
- Reglas: Regla de Oro #1, §1.6.

### T1 — Dependencias de la fábrica
- Ejecutor: ejecutor-backend
- Agente: Claude Code
- Estado: APROBADA · rama `claude/etapa3-t1-dependencias` · a467e21 (Evaluación 1). 488 pruebas en verde. PyMuPDF 2.0, Pillow 13.0.0, playwright 1.64.0 (chromium-1248), pypdf 6.21.2.
- Archivos: `BACKEND/requirements.txt` (nuevo), `BACKEND/requirements-dev.txt`, `BACKEND/tests/test_dependencias.py` (nuevo)
- Depende de: — (necesita el sí de Steven a P1)
- Qué hacer:
  - Instalar en `py -3.14`: `PyMuPDF`, `Pillow`, `playwright` (+ `playwright install chromium`) y `pypdf`. Fijar las versiones en `requirements.txt`.
  - Agregar una prueba de humo que importe cada librería y abra un PDF de 1 página creado en memoria.
- Criterios de aceptación:
  - [ ] `py -3.14 -c "import fitz, PIL, playwright, pypdf"` → OK.
  - [ ] La prueba de humo pasa y `py -3.14 -m pytest -q` sigue en verde.
- Reglas: §1.5 (offline una vez instalado).

### T2 — Reconocimiento del PDF de visita (solo lectura, informe)
- Ejecutor: ejecutor-backend
- Agente: Claude Code
- Estado: APROBADA (Evaluación 3) · rama `claude/etapa3-t2-reconocimiento` · 5873c95 · push hecho, PR por abrir (visitas #17, #18 y #20). Las etiquetas son texto libre, no tipo "C1 A4".
- Archivos: `PLANES/etapa-3-reconocimiento-visita.md` (nuevo; es documentación, sin código en el repo)
- Depende de: T1
- Qué hacer:
  - Con PyMuPDF, abrir **en solo lectura** 3 PDF de visita de Terra Living (P4 elige cuáles; propuesta: #18 losa, #19 verticales y #20 losa parcial).
  - Documentar:
    - cuántas páginas tiene y cuántas imágenes por página;
    - si las etiquetas (`C1 A4`, etc.) son texto extraíble y en qué posición respecto a la foto;
    - si hay medidas escritas;
    - cuánto pesa cada imagen y su resolución;
    - cuánto tarda en abrir.
  - No copiar fotos al repositorio.
- Criterios de aceptación:
  - [ ] El informe responde, para cada PDF: texto sí o no, orden de lectura de las fotos, cómo se distingue una foto con etiqueta de una sin etiqueta, y ejemplos literales de etiquetas.
  - [ ] El planificador ajusta T3 con ese informe antes de enviarla.
- Reglas: §4.1 (Capa 2), §4.7 M1.

### T3 — Lector de visita → `elementos_visita` (Capa 2)
- Ejecutor: ejecutor-backend
- Agente: Claude Code
- Estado: APROBADA (Evaluación 8) · rama `claude/etapa3-t3-lector-visita` · df25838 (538 pruebas) · push hecho, PR por abrir. Corrige el bloqueante de la Evaluación 7: las etiquetas de un solo token quedan pendientes. Corrige B1, B2, O1 y O5 y aplica la normalización; B3 quedó registrado en la auditoría id 36. Antes 3d0b54f (sale de origin/main). 510 pruebas en verde (27 nuevas). Corrida real de la #17: 3 grupos, 14 fotos, 3 dudas (ids 19–21). Respaldo previo `catdic_local.backup-20261023-082229.db`.
- Archivos (ajustados tras T2):
  - `BACKEND/sync/lector_visita.py` (nuevo);
  - `BACKEND/tests/test_lector_visita.py` (nuevo).

  Va en `sync/`, no en `importadores/`, para no depender del PR #3. Tampoco toca `config.py`: T6 ya lo modifica. La ruta de la caché la resuelve el propio módulo: `CATDIC_CACHE_RAIZ` o `<home>\CATDIC-CACHE` (D1).
- Depende de: T1 (librerías ya instaladas) y T2 (APROBADA, informe `PLANES/etapa-3-reconocimiento-visita.md` en la rama `claude/etapa3-t2-reconocimiento`).
- Qué hacer (según T2 y sus observaciones O1–O3):
  - **Recorrido.** Página a página, sin cargar todo el documento. La foto principal es la imagen más grande de la página; el logo se ignora. El orden lo da la página, nunca la hora de `Creado el:`.
  - **Etiqueta.** Es el texto de 12 pt en negrita entre el borde inferior de la foto y `Creado el:`. En la #20 comparte bloque con `Creado el:`, así que se separa por spans. Si solo aparece `Creado el:`, la foto no tiene etiqueta. El texto de la etiqueta se guarda tal cual en `etiqueta_original`. El texto libre que va debajo de `Creado el:` se guarda como nota de esa foto (dentro de `fotos_json`).
  - **Agrupación.** Se usa `agrupar_log_fotografico_visita`: cada etiqueta abre un grupo provisional y las fotos siguientes sin etiqueta le pertenecen. Si las primeras fotos no tienen etiqueta, forman un grupo `pendiente de verificar` con una duda.
  - **Interpretación sin adivinar (O1, O2).**
    - `id_elemento`, `tipo_elemento` y `ejes` solo se llenan cuando `interpretar_eje_de_visita` o una correspondencia exacta los da sin interpretar. Todo lo demás queda `pendiente de verificar`.
    - Ninguna etiqueta se descarta ni se fusiona por su cuenta: textos como `Garantizar recubrimiento`, `Tramo D-B` o `Muro perimetrale` quedan como grupo provisional.
    - El eje del pórtico de un `Tramo …` no se deduce del orden del log.
    - **Una sola `DUDA_BLOQUEANTE` por grupo no reconocido**, no una por campo. La duda cita la etiqueta literal y las páginas, y pregunta: "¿abre un elemento nuevo (tipo, ID, ejes) o pertenece al anterior?". Así la Mesa no se satura.
  - **Prima y mayúsculas (O3).** La prima `’` (U+2019) no se convierte en `'` ni `mc` en `MC` hasta que Steven lo apruebe. Por ahora esas etiquetas quedan pendientes.
  - **Nivel.** Se toma del nombre de la carpeta de la visita solo si trae exactamente un nivel legible (por ejemplo `S-4`). Si no, `pendiente de verificar`.
  - **Guardado.**
    - Se guarda en `elementos_visita` con `orden_en_log` = página de la etiqueta. Es idempotente por `(visita_id, orden_en_log)`: una segunda corrida no duplica filas ni dudas.
    - Antes de escribir en la BD real se saca un respaldo.
    - Cada acción queda en `auditoria`, con `getpass.getuser()`.
  - **Caché.** Cada foto se guarda en `<caché>\<proyecto>\<visita>\p<NNN>.jpg`: máximo 1000×1000, JPG q72, `exif_transpose`. Nunca se escribe en Dropbox; si la ruta de la caché cae dentro de Dropbox, se rechaza.
  - **Validación (O2 de T4b).** Si el PDF no tiene la estructura de visita (sin `Creado el:` ni fotos), da `ValueError` y una duda, y no se carga nada.
  - **Capa 1 intacta.** Nunca se sacan datos de diseño de las fotos ni de las notas (§4.1). Las medidas escritas en las notas no se convierten a números.
- Criterios de aceptación:
  - [ ] Pruebas con un PDF `# SINTÉTICO` generado en la prueba:
    - agrupación correcta;
    - primeras fotos sin etiqueta → duda;
    - `A1` → `EJE A-1`;
    - `Tramo D-B` → pendiente + 1 duda;
    - prima `’` → pendiente;
    - nota guardada tal cual;
    - segunda corrida sin duplicados;
    - un PDF que no es de visita → rechazado;
    - caché dentro de Dropbox → rechazada.
  - [ ] Corrida real **solo sobre la #17** (3 etiquetas y 14 fotos):
    - quedan 3 grupos con 14 fotos en total;
    - las etiquetas se ven literales (`Mh4`, `Mh1 pantalla eje 3`, `Pantalla eje B`);
    - hay respaldo previo;
    - en Dropbox no se escribió nada;
    - la caché pesa menos que el PDF.

    El Ejecutor reporta las filas y dudas creadas para que Steven las revise.
  - [ ] `py -3.14 -m pytest -q` en verde.
- Reglas: Regla de Oro #1, §4.1, §4.4 (ejes de visita), §4.7 M1, §5.2 (redimensionado).

### T4 — API de la Mesa de Dudas
- Ejecutor: ejecutor-backend
- Agente: Claude Code
- Estado: APROBADA · rama `claude/etapa3-t4-mesa-dudas` · aebab4e (Evaluación 1; O1 y O2 → T4b antes de T5). 505 pruebas en verde (22 nuevas). En la BD real solo se hizo GET.
- Archivos: `BACKEND/main.py`, `BACKEND/mesa_dudas.py` (nuevo), `BACKEND/tests/test_mesa_dudas.py` (nuevo)
- Depende de: — (puede correr en paralelo con T1 a T3)
- Contexto, BD real al 22/10 (`dudas_y_hallazgos` ya tiene `respuesta_usuario`, `resuelta` y `resuelto_en`): hay 17 dudas de la Etapa 1, todas a nivel de visita (`id_elemento` vacío).
  - `fecha_visita`: 10 bloqueantes;
  - `clase`: 5 bloqueantes y 1 hallazgo;
  - `estado`: 1 (la #18, P3 estricta);
  - `archivos_json`: 1 (la #19 sin PDF).

  El sincronizador (`_campos_resueltos`) ya deja de pedir un campo cuando su duda está `resuelta = 1`, pero **no aplica el valor**. Si la Mesa solo marcara resuelta la duda, la visita quedaría con `fecha_visita = pendiente de verificar` sin ninguna duda abierta.
- Qué hacer:
  - `GET /api/dudas?proyecto_id=&visita_id=&resuelta=&categoria=`: lista las dudas con visita (número y carpeta), elemento, campo, pregunta, respuesta y fechas.
  - `PATCH /api/dudas/{id}` con `{respuesta}`. Valida según el campo y **aplica** la respuesta de Steven, porque Steven es fuente válida:
    - `fecha_visita`: solo `DD/MM/AAAA` válida (`_es_fecha_ddmmaaaa_valida`). Se guarda `AAAA-MM-DD` en `visitas.fecha_visita` y se quita el campo de `campos_pendientes_json`.
    - `clase`: solo `Parcial`, `Completivo` o `Mixta` (constantes de `sync/parser_visitas.py`). Se guarda en `visitas.clase` y se quita de pendientes.
    - `estado` (P3): solo "corresponde" → `Procesada`, con el STP citado en `salida_json`; o "no corresponde" → `Sin procesar`.
    - `archivos_json` (falta el PDF): no se resuelve con texto → 422 "se resuelve al sincronizar cuando el PDF esté en la carpeta".
    - `HALLAZGO_INTERNO`: se puede marcar revisado (`resuelta = 1`) sin aplicar valor.
    - Dudas de elemento (con `id_elemento`; vienen después): solo se guarda la respuesta, no se aplica.
    - Una respuesta inválida → 422 y no cambia nada. Una duda ya resuelta → 409.
  - Todo en una transacción, con una fila en `auditoria` (valor anterior y nuevo).
  - Cuando una visita queda sin `DUDA_BLOQUEANTE` abiertas: si la última fue `estado`, queda en el estado elegido; si no, pasa a `Sin procesar`, **nunca** a `Procesada` por su cuenta.
  - Un sync posterior no debe volver a crear la duda ni pisar el valor respondido. Verificarlo con una prueba que corra el sincronizador después de responder.
- Criterios de aceptación:
  - [ ] Pruebas con BD temporal:
    - listar con filtros;
    - fecha válida aplicada y auditada;
    - fecha `5/3/2026` o `31/02/2026` → 422 sin cambios;
    - clase aplicada;
    - `estado` corresponde / no corresponde;
    - `archivos_json` → 422;
    - última duda → `Sin procesar`;
    - id inexistente → 404;
    - duda ya resuelta → 409;
    - un sync posterior no revierte nada.
  - [ ] Sobre la BD real, **solo `GET`**: `GET /api/dudas?visita_id=<id de la #19>` devuelve su duda `archivos_json`. No se responde ninguna duda real en esta tarea.
  - [ ] `py -3.14 -m pytest -q` en verde.
- Reglas: Regla de Oro #1, §1.5.

### T4b — Correcciones del sync y de la Mesa antes de T5
- Ejecutor: ejecutor-backend
- Agente: Claude Code
- Estado: APROBADA (Evaluación 2; O1–O3 antes de T10) · rama `claude/etapa3-t4b-correcciones` · 06051b6 (sale de T4, aebab4e). 513 pruebas en verde. Sync real sin cambios; respaldo `catdic_local.backup-20261022-133234.db`.
- Archivos: `BACKEND/sync/sincronizador.py`, `BACKEND/mesa_dudas.py`, `BACKEND/tests/test_sync_endpoint.py`, `BACKEND/tests/test_mesa_dudas.py`
- Depende de: T4 (sale de su rama o de `main` con T4 fusionado)
- Origen: Evaluación 1 de T4 (O1, O2, el punto 3 y el detalle del punto 2).
- Qué hacer:
  - (a) `_campos_resueltos` (`sincronizador.py:236-242`) cuenta solo las `DUDA_BLOQUEANTE` resueltas. Prueba: un hallazgo revisado no congela el campo.
  - (b) Cuando la carpeta ya tiene el PDF, el sync marca resuelta la duda `archivos_json`, con auditoría y `respuesta_usuario` = "resuelta por sincronización". Prueba con carpeta temporal.
  - (c) Prueba del camino diferido de `estado_mesa`: responder `estado` con otra bloqueante abierta y luego cerrar la última.
  - (d) "Corresponde" comprueba en solo lectura (`Path.exists()`) que el STP siga en `2.DATA PROCESADA`. Si ya no está → 422.
  - (e) Por decisión de Steven (O3), la Mesa no acepta `Mixta` como respuesta a `clase`: solo `Parcial` o `Completivo`. Cualquier otra → 422.
- Criterios de aceptación:
  - [ ] Las 5 pruebas nuevas (a–e) y `py -3.14 -m pytest -q` en verde.
  - [ ] Un sync real sin cambios en Dropbox deja la BD igual: 0 dudas cerradas y las mismas visitas.

### T5 — Mesa de Dudas en el tablero
- Ejecutor: ejecutor-frontend
- Agente: Claude Code
- Estado: APROBADA (Evaluación 6) · commit 5a8779e · push hecho, PR por abrir · rama `claude/etapa3-t5-mesa-ui`, que sale de `claude/etapa3-t4b-correcciones` (necesita la API de T4 y T4b, que todavía no están en `main`)
- Archivos: `FRONTEND/index.html`
- Depende de: T4 y T4b
- Qué hacer:
  - Al hacer clic en una visita con dudas abiertas se abre un panel con:
    - el elemento, el campo y la pregunta;
    - el control de respuesta según el campo:
      - `fecha_visita`: casilla DD/MM/AAAA;
      - `clase`: selector **solo Parcial / Completivo** (Mixta no, decisión de Steven);
      - `estado`: corresponde / no corresponde, eligiendo uno de los STP candidatos;
      - `archivos_json`: sin respuesta, con el texto "se cierra sola al sincronizar cuando el PDF esté en la carpeta";
      - hallazgo: "marcar revisado";
      - duda de elemento (T3): casilla de texto libre.
  - Guardar llama a `PATCH`. Los 422/409/404 de la API se muestran con su mensaje y no se cierra nada.
  - O3 de T4b: una visita `Procesada` con una bloqueante abierta también muestra el aviso de dudas.
  - Fechas en DD/MM/AAAA.
- Criterios de aceptación:
  - [ ] Verificado en el navegador:
    - con el backend contra la **BD real, solo lectura de pantalla**: se ven las dudas de la #19 y de la #18;
    - con el backend contra una **copia temporal de la BD** (`CATDIC_DB_PATH`): responder una fecha la marca resuelta, una fecha inválida muestra el error 422, y un `estado` corresponde muestra el STP;
    - con el backend apagado: sale un aviso de error.
  - [ ] **No se responde ninguna duda en la BD real.** Eso lo hace Steven.
  - [ ] pytest sigue en verde (no hay cambios de backend).
- Reglas: §5.2 (fechas).

### T6 — Módulos visuales comunes M1–M4 y salida segura
- Ejecutor: ejecutor-generadores
- Agente: Claude Code
- Estado: APROBADA (Evaluación 4) · rama `claude/etapa3-t6-comunes` · 33eb593 · push hecho, PR por abrir. 510 pruebas en verde.
- Archivos (todos nuevos):
  - `BACKEND/generators/__init__.py`;
  - `BACKEND/generators/comun/{__init__,fotos,localizacion,detalle,salida}.py`;
  - `BACKEND/tests/test_generadores_comun.py`.
- Depende de: T1
- Qué hacer:
  - `fotos.py` (M1): recorte cover con `ImageOps.fit` al aspecto de la celda, gutter blanco, cuadrícula 2×2 o 1 grande, y selección con `seleccionar_fotos_pick4` / `seleccionar_fotos_m1`.
  - `localizacion.py` (M3): rasteriza la página **completa** del plano a 200 dpi y dibuja el recuadro `RGB(220,0,0)` con el grosor de `calcular_grosor_recuadro_rojo`. Las coordenadas llegan como parámetro: nunca se deducen.
  - `detalle.py` (M4): recorte nítido de una región del plano. Rechaza una imagen que no venga del plano (#2).
  - `salida.py`:
    - ruta con `obtener_ruta_salida_sin_sobrescribir`;
    - comprueba que pese menos de 30 MB y corre `auditar_archivo_pdf_generado`;
    - registra en `auditoria`;
    - escribe solo en la carpeta de salida configurada (P3).
- Criterios de aceptación:
  - [ ] Pruebas con imágenes y PDF `# SINTÉTICO`: la cuadrícula no deja franjas (#3); el recuadro es visible a tamaño final (#4); la localización es la página completa (#1); no se sobrescribe un archivo existente y se crea `v2` (#15).
  - [ ] pytest en verde.
- Reglas: §4.7 M1–M4, §5.2, errores #1, #2, #3, #4 y #15.

## Tareas — Bloque 3B (BORRADOR, 23/10/2026; reescrito con las fuentes de T0)

### Fuentes recibidas (T0, parcial)
Steven las entregó en `G:\My Drive\CATDIC\FORMATO CLAUDE\New folder\`. El código viene dentro de archivos `.md`. El planificador las leyó en solo lectura.
- **`stp-mived-generador.py.md`** (592 líneas): contiene `assets.py`, `stp.py`, `lib_pages.py`, `vert.py`, `pdf.py` y `fi02.py`.
- **`stp-mived-generador-s5.py.md`**: contiene `stp5.py`, `fi02_s5.py` y un bloque de `vert.py` (visita 14).
- **`catdic-stp-llenador.py.md`**: contiene `catdic_stp.py`. El archivo `catdic-stp-llenador.py (1).md` es idéntico (comprobado con `cmp`).
- **`plantilla-datos-diseno.md`** y **`plantilla-visita-obra.md`**: definen las columnas de Capa 1 por tipo de elemento. Le sirven a la Etapa 2 (T2/T3).
- **`hv-informe-tecnico-*.md`**: son de la Etapa 4. No se usan aquí.
- **FI oficiales de ejemplo:**
  - `SERENITY RS\ARCHIVOS DEL CLIENTE\FORMULARIO\EDIFICIA  A\` (la carpeta lleva dos espacios): FI-01, FI-02 y FI-03.
  - Los 12 FI no firmados de Terra Living.
- **Siguen faltando:** `FORMULARIOS MIVED.pdf` (la plantilla de CATDIC-STP) y el logo CATDIC. T9 sigue bloqueada.

### Qué traen las fuentes (lo que se reutiliza y lo que NO)
- **Se reutiliza (formato):**
  - el CSS y la maquetación HTML de `lib_pages.py`: `page_cmp`, `page_fot`, portada y hoja de inspección `#efefef`, los rótulos exactos (`APROVADOS`, `IMFORMACION`) y `pick4`;
  - en `pdf.py`, la impresión Carta sin márgenes de Playwright;
  - en `fi02.py` y `fi02_s5.py`, el método: buscar el span por su texto, tapar con redacción blanca, escribir en la línea base, borrar las anotaciones de firma y guardar con `garbage=3`;
  - de `catdic_stp.py`, la detección de geometría de la plantilla (`_geom`, `_bases`), el ajuste de la fuente a una sola línea (`_put`) y la portada.
- **NO se reutiliza (datos fijos de Terra Living, Regla de Oro):**
  - los datos de proyecto escritos a mano: `LIC`, `DIR`, `PROY`, el sector, la provincia y el residente con su colegiatura;
  - las coordenadas de ejes y los recortes (`GEO`, `AX`, `AY`, `PX`, `hbeam`, `colbox`);
  - las listas de elementos con aceros, L, h y fotos;
  - en `rows_viga`, `rows_losa`, `rows_muro` y `rows_col`, los valores de diseño fijos: resistencia 350/240, ancho 0.40, espesor 0.25, recubrimientos, `MALLA`, `Ø1/2"@0.10`, H = 2.95, `Ø1"`;
  - `cuantia()`, que usa un ancho 40 fijo, y `rows_col`, que usa `A1 = 5.07` para todas las barras. Se reemplazan por `calcular_cuantia_elemento`.
  - Todo eso tiene que venir de `elementos_diseno` (Capa 1), de `elementos_visita` (Capa 2) o de `proyectos`. Si falta → `"pendiente de verificar"` + duda, y **no se genera la ficha**.
- **Rutas Linux y `os.system`:** se reemplazan por `pathlib` y llamadas directas. La fuente Carlito pasa a la de Windows (P6).
- **`page_fot` antiguo** usaba `object-fit: contain` y una cuadrícula 2×2 aunque hubiera 2 o 3 fotos. Se reemplaza por T6 (cover + gutter); la maquetación de 2 y 3 fotos la decide Steven (P9).

### T0b — Inventario de las fuentes y copia de referencia (solo documentación)
- Ejecutor: ejecutor-generadores
- Agente: Claude Code
- Estado: APROBADA (Evaluación 12) · push hecho, PR por abrir · rama `claude/etapa3-t0b-inventario` · 5e6e115 (un solo commit, sin datos del cliente). Los FI no son AcroForm; la firma es una anotación Square; la mampostería está en la sección 8 del FI-03.
- Archivos:
  - `PLANES/etapa-3-inventario-fuentes.md` (nuevo);
  - copia **sin editar** de las fuentes en `FABRICA/fuentes/`, **fuera de git**: se agrega `FABRICA/` a `.gitignore`, porque contienen datos del cliente (licencia, dirección, residente) (P10).
- Qué hacer:
  - Clasificar cada valor fijo de los scripts en una tabla con columnas: archivo:línea · valor · clase (formato / dato de proyecto / dato de diseño / coordenada / foto) · de dónde debe salir en CATDIC-WEB (`proyectos`, `elementos_diseno`, `elementos_visita`, cálculo de `reglas_ingenieria`) · ¿existe hoy esa columna?
  - Reconocimiento de los FI en solo lectura, con los ejemplos de Serenity y los 12 de Terra Living:
    - ¿son AcroForm o texto plano?
    - posición de los rótulos: nivel, fecha, Observaciones, fechas de autorización, casillas Sí/No;
    - qué casillas son de mampostería;
    - dónde está la firma y si es una anotación;
    - diferencias entre FI-01, FI-02 y FI-03.
  - No copiar fotos ni PDF al repositorio.
- Criterios:
  - [ ] El inventario cubre `stp.py`, `lib_pages.py`, `vert.py`, `fi02.py`, `fi02_s5.py`, `stp5.py` y `catdic_stp.py`.
  - [ ] El informe de los FI responde todas las preguntas anteriores con coordenadas reales.
  - [ ] `FABRICA/` está en `.gitignore` y `git status` no la muestra.

### T7a — Datos de proyecto para las cabeceras
- Ejecutor: ejecutor-backend
- Agente: Claude Code
- Estado: APROBADA (Evaluaciones 11 y 12) · push hecho, PR por abrir · 8e5f6a9 (merge de main 1a40abf) · 493 pruebas · BD real migrada (respaldo 133140, auditoría 37) · rama `claude/etapa3-t7a-proyecto`, que sale de `claude/etapa2-t1-esquema` (PR #4), porque las dos tocan las migraciones de `database.py`
- Archivos: `BACKEND/database.py`, `BACKEND/main.py` (ampliar `ProyectoUpdate`), `BACKEND/tests/test_database.py`
- Depende de: T0b (confirma la lista de campos)
- Qué hacer:
  - Migración idempotente con respaldo. A `proyectos` se le agregan `direccion_obra`, `provincia` y `sector`. Ya existen `no_solicitud`, `no_licencia` y `residente_obra`, hoy vacíos.
  - Los valores **no se siembran desde los scripts**. Steven los llena desde el tablero o la API, porque son datos del cliente. Mientras estén vacíos, el generador pone `"pendiente de verificar"` y crea una duda de proyecto.
- Criterios:
  - [ ] Pruebas de migración (conserva filas e idempotente).
  - [ ] `PATCH /api/proyectos/{id}` acepta los campos nuevos y lo audita.
  - [ ] pytest en verde.

### T7 — Generador `STP-MIVED` (HTML → PDF con Playwright)
- Ejecutor: ejecutor-generadores
- Agente: Claude Code
- Estado: APROBADA (Evaluación 17) · 4c83e2e (547 pruebas) · push hecho, PR por abrir · rama `claude/etapa3-t7-stp-mived`, que sale de `claude/etapa3-t6-comunes` (33eb593)
- Archivos (nuevos): `BACKEND/generators/stp_mived.py`, `BACKEND/generators/plantillas/stp_mived.css`, `BACKEND/tests/test_stp_mived.py`
- Depende de: T0b, T6 y T7a. Las pruebas usan datos `# SINTÉTICO`; la corrida real espera a la Etapa 2.
- Ajuste del planificador:
  - El generador **no lee la BD**. Recibe diccionarios ya armados: proyecto (con los campos de T7a), visita y una lista de fichas (Capa 1 + Capa 2). T10 los arma desde la BD.
  - Así T7 sale de la rama de T6 y no se apila sobre T7a.
  - Un campo de cabecera vacío → `"pendiente de verificar"` + error (no se genera).
  - Áreas de barra: las del motor, nominales ASTM (pendiente de que Steven lo confirme).
  - P9: 2 fotos en dos columnas; 3 fotos con 1 ancha arriba y 2 abajo.
- Qué hacer:
  - Portar la maquetación de `lib_pages.py` (CSS, `page_cmp`, `page_fot`, portada, inspección `#efefef`) sin cambiar rótulos ni ortografía. Las fuentes de Windows son `Calibri` y `Arial`.
  - Entrada: la visita, sus `elementos_visita` cruzados con `elementos_diseno` y los datos de `proyectos`.
  - Filas por tipo (viga, losa, muro, columna): cada valor sale de Capa 1 (columna "1. PLANOS") o de Capa 2 (columna "2. OBRA").
    - Si `OBRA` no tiene medida → se usa el valor del plano solo cuando §4.5 lo permite (medida + 2·rec = plano). Si no, queda vacío y se crea una duda.
    - La cuantía se calcula con `calcular_cuantia_elemento` y va en decimal.
  - Fotos con T6 (M1 cover + gutter). LOCALIZACIÓN y DETALLE con T6 (M3/M4), con `carpeta_planos` = la carpeta PLANOS SELLADOS exacta del proyecto.
  - Antes de renderizar: `auditar_datos_ficha_antes_de_renderizar(ficha, "STP-MIVED")`. Si hay errores → no se genera y se crean dudas.
  - Salida con T6 (`guardar_pdf`) en la carpeta de pruebas. Nombre §5.2: `<Proyecto> - STP - <Elementos nivel> - DD-MM-AAAA.pdf`.
  - La hoja de inspección **no** lleva texto de conformidad fijo. "SE VERIFICO… ACORDE A PLANOS APROBADOS" solo va si no hay discrepancias abiertas en la visita.
- Criterios:
  - [ ] Pruebas `# SINTÉTICO`:
    - orden de las hojas y numeración (portada e inspección sin número; 1..n en el pie);
    - rótulos literales;
    - un valor de diseño ausente → no genera y crea una duda;
    - cuantía recalculada;
    - fecha DD/MM/AAAA;
    - el PDF pesa menos de 30 MB y crea `v2` si ya existe;
    - ninguna cadena fija de Terra Living en el código (comprobación con grep).
  - [ ] pytest en verde.
- Reglas: §3.2 (STP-MIVED), §4.5, §4.6, §4.7, §5.2, errores #1–#4 y #9–#15.

### T8 — Actualizador `MIVED FI-01/02/03` (PyMuPDF)
- Ejecutor: ejecutor-generadores
- Agente: Claude Code
- Estado: APROBADA (Evaluación 16) · 7751e57 (548 pruebas) · push hecho, PR por abrir · PDF de prueba en CATDIC-SALIDA-PRUEBAS · rama `claude/etapa3-t8-fi-mived`, que sale de `claude/etapa3-t6-comunes` (33eb593)
- Archivos (nuevos): `BACKEND/generators/fi_mived.py`, `BACKEND/tests/test_fi_mived.py`
- Depende de: T0b (el reconocimiento de los FI), T6, T7a y P5.
- Ajustes del planificador, con el reconocimiento de T0b:
  - **Los FI no son AcroForm.** Se escribe en coordenadas medidas y localizadas por el texto de los rótulos, nunca con coordenadas fijas a ciegas:
    - nivel en la línea base de "Nivel a inspeccionar";
    - fecha en (487,0 · 144,7);
    - Observaciones según el formulario: FI-01 "9." x 41,8; FI-02 "13." x 26,8; FI-03 "12." x 39,3.
  - **La marca "Sí"** es un dibujo de 12×12 pt con trazo de 1,5, en x≈500-516, a la izquierda del texto "Sí". Se dibuja igual. La marca "No" nunca se dibuja (no hay ningún ejemplo).
  - **Filas que se marcan**: las mismas que en los FI de Terra (tabla de T0b).
    - FI-03 p3: 10a-10e (SEGURIDAD) y 11a-11d (PROBETAS).
    - Nunca la sección 8 del FI-03 (MAMPOSTERÍA) ni la 9 (CERRAMIENTO/PANDERETAS).
    - Nunca las secciones 8-9 del FI-02 (dinteles), pendiente de que Steven lo confirme.
  - **Firma:** se borran todas las anotaciones (`Square`/`SquareImage`) de todas las páginas.
  - **Fechas de autorización:** quedan **en blanco** hasta que Steven confirme la regla implícita de los scripts (parcial = en blanco; completiva = día/mes del inspector). La regla queda en la lista de dudas.
  - El generador no lee la BD: recibe proyecto, visita, nivel, tipo y la lista de elementos supervisados como diccionarios.
  - Cabecera vacía → pendiente + error.
- Qué hacer, con el método de `fi02.py` y `fi02_s5.py`:
  - **Un documento por nivel y tipo** (FI-01 cimentación, FI-02 losas, escaleras y vigas, FI-03 muros y columnas).
  - Si ya existe uno para ese nivel y tipo (P5) → se abre y se guarda como versión nueva (` v2`, ` v3`), nunca encima. Si no existe → se parte del FI en blanco del proyecto (`FORMULARIOS\FI-0X-26-STP-<PROYECTO>.pdf`). Nunca de un FI de otro nivel.
  - Observaciones: se **agrega** la visita (fecha, parcial/completiva, elementos), sin borrar las anteriores.
  - Cierre "CONFORME A PLANOS APROBADOS" solo en una visita completiva sin discrepancias abiertas.
  - Las casillas "Sí" obligatorias van marcadas (encofrados, armaduras de columnas, losas y escaleras, seguridad, probetas). Las de mampostería, nunca.
  - Se borran todas las anotaciones de firma y no se inserta ninguna firma.
  - Fuente Calibri (P6 es solo para CATDIC-STP).
  - Salida en la carpeta de pruebas, con nombre §5.2 `MIVED - <PROYECTO>-<ELEMENTOS NIVEL>.PDF`.
- Criterios:
  - [ ] Pruebas con un FI `# SINTÉTICO` que reproduce la geometría del reconocimiento:
    - agrega la observación sin borrar las anteriores;
    - `v2` sin sobrescribir;
    - firma eliminada (#16);
    - mampostería sin marcar y los "Sí" presentes (#17);
    - el existente se actualiza en lugar de rehacerlo (#18);
    - el cierre de conformidad solo si se cumplen las condiciones.
  - [ ] Corrida de prueba sobre una **copia** del FI-02 #12 de Terra, en la carpeta de pruebas, con datos `# SINTÉTICO` de visita. Se comprueba con PyMuPDF que:
    - la observación nueva aparece;
    - las anteriores siguen;
    - hay 0 anotaciones;
    - el número de marcas es igual al de la tabla de T0b;
    - el original no cambió (hash).

    Steven la revisa a ojo.
  - [ ] pytest en verde.
- Reglas: §3.2 (FI), errores #15–#18.

### T9 — Generador `CATDIC-STP` (overlay sobre `FORMULARIOS MIVED.pdf`)
- Ejecutor: ejecutor-generadores · **APLAZADA (Steven, 23/10/2026)**: el formato CATDIC-STP no se está usando. No se ejecuta hasta que Steven lo pida.
- Depende de: T0 (la plantilla y el logo), T6 y T7a.
- Se porta `catdic_stp.py` (`_geom`, `_bases`, `_put` en una sola línea reduciendo la fuente, `ficha`, `portada`):
  - **fuente Arial** (P6: "USA ARIAL");
  - hojas 0–9 por tipo;
  - cuantía en %;
  - logo arriba en la portada.
- Error #14.

### T8b — Ajustes del FI según las respuestas de Steven (23/10)
- Ejecutor: ejecutor-generadores · Agente: Claude Code
- Estado: APROBADA (Evaluación 22) · 8a3c61f · push hecho, PR por abrir · rama `claude/etapa3-t8b-fi-ajustes`, que sale de `claude/etapa3-t8-fi-mived` (7751e57)
- Archivos: `BACKEND/generators/fi_mived.py`, `BACKEND/tests/test_fi_mived.py`
- Qué hacer:
  - **Fechas de autorización** (respuesta 2): se escribe la fecha de la visita (día/mes/año) en la siguiente fila de autorización libre, localizada por su rótulo. Las fechas anteriores se conservan. Si no queda ninguna fila libre → error, no se sobrescribe.
  - **Cierre al final** (respuesta 4): si la observación nueva queda después de un cierre anterior ("Todo segun los planos estructurales." u otro texto que empiece por "Todo segun"), ese cierre se tapa con redacción blanca y se vuelve a escribir, sin cambios, después de la observación nueva. No se pierde ningún texto, y lo que se movió queda en el resultado.
- Criterios:
  - [ ] Pruebas `# SINTÉTICO`: fecha en la fila libre, anteriores intactas, sin filas libres → error; el cierre queda al final con el mismo texto.
  - [ ] Se regenera la salida de prueba del FI-02 #12.
  - [ ] pytest en verde.

  - **Dinteles y cerramiento** (aclaración 3): las filas de las secciones 8-9 del FI-02 (dinteles) y de la sección 9 del FI-03 (muros de cerramiento/panderetas) se marcan "Sí" **solo** si la lista de elementos de la visita trae un elemento de ese tipo (`tipo_elemento` DINTEL o MURO DE CERRAMIENTO/PANDERETA). La sección 8 del FI-03 (MAMPOSTERÍA) no se marca nunca.

  - **FI sin fila libre de autorización** (respuesta "c."):
    - se agrega una fila nueva debajo de la última fila de NOMBRES Y FIRMAS;
    - se copia la geometría de la fila anterior (misma altura, mismas líneas y mismas posiciones de `dd / mm / aaaa`, Calibri, gris como el original), y ahí se escribe la fecha;
    - si no cabe en la hoja antes del pie, se agrega en la hoja siguiente y, si tampoco hay espacio, da error;
    - prueba con copias del FI-01 #1 y del FI-03 #10, que hoy no tienen fila libre.

### T12 — Pruebas que no dependan del contenido actual de Dropbox
- Ejecutor: ejecutor-backend · Agente: Claude Code
- Estado: APROBADA (Evaluación 20) · 39a7477 · push hecho, PR por abrir · rama `claude/etapa3-t12-pruebas-dropbox`, desde `origin/main`
- Archivos: `BACKEND/tests/test_parser_visitas.py`, `BACKEND/tests/test_escaner_dropbox.py`
- Qué hacer:
  - Las pruebas contra el Dropbox real no deben exigir cantidades ni listas exactas, porque siempre se suben visitas nuevas. Deben comprobar propiedades:
    - las carpetas conocidas (#1 a #20) siguen y conservan su lectura;
    - una carpeta nueva se lee sin errores;
    - el escaneo no escribe nada.
  - `test_lista_coincide_con_dropbox_si_esta_disponible` y `test_terra_living_real` pasan a "al menos" o se comparan contra un subconjunto conocido.
- Criterios:
  - [ ] pytest en verde con la carpeta 21 presente.
  - [ ] Las pruebas siguen detectando que falte una carpeta conocida o que se lea mal.

### T7b — STP final con las dos visitas del nivel (aclaración 9)
- Ejecutor: ejecutor-generadores · Agente: Claude Code
- Estado: APROBADA (Evaluación 19) · 0b3b828 · push hecho, PR por abrir · rama `claude/etapa3-t7b-stp-dos-visitas`, que sale de `claude/etapa3-t7-stp-mived` (4c83e2e)
- Archivos: `BACKEND/generators/stp_mived.py`, `BACKEND/tests/test_stp_mived.py`
- Qué hacer:
  - `generar_stp_mived` acepta **una o varias visitas del mismo nivel** (parcial + completiva). Cada ficha indica de qué visita sale.
  - Portada y hoja de inspección: "Fecha de Inspección" con las fechas de todas las visitas (DD/MM/AAAA, separadas por " y "), y clase "PARCIAL Y COMPLETIVO".
  - Las fichas van en el orden de las visitas y luego del log.
  - Propuesta del planificador, que Steven valida al ver el PDF de prueba: el nombre de archivo lleva la fecha de la **última** visita y la clase "Completivo".
  - Con una sola visita, el comportamiento es el de hoy.
  - Si las visitas son de niveles distintos → error.
- Criterios:
  - [ ] Pruebas `# SINTÉTICO`: dos visitas → las dos fechas en portada e inspección, fichas de ambas visitas, nombre con la fecha última; niveles distintos → error; una sola visita sin cambios.
  - [ ] pytest en verde.

### T5b — Mesa de Dudas: rótulos de las etiquetas de foto
- Ejecutor: ejecutor-frontend · Agente: Claude Code
- Estado: APROBADA (Evaluación 18) · 3d3a90c · push hecho, PR por abrir · los disparadores al cargar visita (T3) y con enlaces (D4) quedan para T10/D4 · rama `claude/etapa3-t5b-mesa-rotulos`, que sale de `claude/etapa3-t5-mesa-ui` (5a8779e)
- Archivos: `FRONTEND/index.html`
- Qué hacer (respuesta 13):
  - Si `campo_afectado` empieza por `elemento_visita:`:
    - rotular "Etiqueta en la visita: <etiqueta>" en lugar de "Elemento";
    - traducir el campo a "Fotos p. N–M", sacando las páginas de la pregunta o del número de `pNNN`;
    - bajo la casilla, el aviso "Esta respuesta se guarda; se aplicará al cruzar con los planos".
  - O2 de T5: tras un 409, recargar las dudas de la visita.
  - **Aparición automática del panel** (respuesta 13, segunda parte: "que salga cuando se introduzcan los datos o los enlaces de los archivos"):
    - al terminar una sincronización que deja visitas nuevas con dudas, se abre la Mesa de Dudas de la primera visita con dudas nuevas;
    - lo mismo cuando se carga una visita (T3) o se guardan datos del proyecto que generen dudas.

    Lo de los "enlaces de archivos" depende de la decisión D4 de Codex (carpeta elegida por el usuario), que todavía no existe; se hará cuando exista.
- Criterios:
  - [ ] Verificado en el navegador contra una **copia** de la BD: la duda 19 (#17) dice "Etiqueta en la visita: Mh4 · Fotos p. 1–6".
  - [ ] Un sync de prueba con dudas nuevas abre el panel.
  - [ ] Tras un 409, el panel se recarga.
  - [ ] No se responde nada en la BD real.

### T10 — Procesar Cola real
- Ejecutor: ejecutor-backend (endpoint) + ejecutor-frontend (botón). Archivos: `BACKEND/main.py`, `BACKEND/procesador_cola.py` (nuevo), `FRONTEND/index.html`, pruebas.
- Depende de: T3, T4 y al menos un generador (T7).
- Para cada visita `Sin procesar`:
  1. corre el lector (T3);
  2. cruza `elementos_visita` con `elementos_diseno` por ID + Nivel + Ejes (§4.2), sin adivinar;
  3. si hay dudas, la visita queda `Con dudas`;
  4. si no, genera los `formatos_solicitados`, pasa el auditor y queda `Procesada`.

  Se reactiva el botón.

## Paralelismo
- **Ya mismo:** T1 (backend) y T4 (backend, `main.py`) no comparten archivos y pueden correr a la vez.
  - T4 toca `main.py`. Ninguna otra tarea de 3A lo toca.
  - El PR #2 de Codex (ya fusionado en `main`) también tocó `main.py`, así que hay que partir de `main` actualizado (`c310efa`).
- **Luego:** T2 → T3 en serie. T6 en paralelo con T2 y T3 (otro ejecutor, otros archivos). T5 en cuanto termine T4.
- **Codex:** T5 (frontend) o T6 (generadores) se le pueden asignar a Codex para avanzar en paralelo (P7).
- T3 necesita el PR #3 (Etapa 2, T2) fusionado, porque crea `BACKEND/importadores/`.

## Pendientes de verificar / preguntas para Steven
- **P1:** ¿instalo PyMuPDF, Pillow, Playwright (con Chromium, unos 150 MB) y pypdf en Python 3.14? Es la misma pregunta que la P4 de la Etapa 2; con un sí se resuelven las dos.
- **P2:** ¿dónde va la caché de fotos redimensionadas de las visitas? Propuesta: `C:\Users\Steve\CATDIC-CACHE\<proyecto>\<visita>\`, fuera de Dropbox y de OneDrive para no sincronizar cientos de MB.
- **P3:** ¿los generadores escriben directo en Dropbox (`INFORMES\2.DATA PROCESADA\`, como dice §5.1) o, mientras probamos, en una carpeta de pruebas? Propuesta: carpeta de pruebas hasta que apruebes el primer PDF de cada formato.
- **P4:** ¿qué 3 visitas uso para el reconocimiento (T2)? Propuesta: #18, #19 y #20.
- **P5:** para los FI, ¿cuál es el "existente" que se actualiza?
  - ¿el de `FORMULARIOS\MIVED\FORMULARIOS NO FIRMADOS\`, numerado tipo `12. FI-02-26-STP-TERRALIVING …`?
  - ¿o el de `INFORMES\2.DATA PROCESADA\`, tipo `MIVED - TERRA LIVING-….PDF`?

  ¿Y qué nombre lleva la versión nueva?
  - **Propuesta (23/10, según los scripts):**
    - `fi02_s5.py` actualizó el FI del **mismo** nivel (S-5) como ` v2`.
    - `fi02.py` partió del FI del S-4 para hacer el del S-3, es decir, de **otro** nivel.
    - Propongo esta regla:
      - el "existente" es el FI de ese mismo nivel y tipo, en `FORMULARIOS NO FIRMADOS` o, si hay uno más nuevo, en `2.DATA PROCESADA`;
      - si existe → copia con ` v2`/` v3`;
      - si no existe → se parte del FI en blanco del proyecto (`FORMULARIOS\FI-0X-26-STP-<PROYECTO>.pdf`), nunca del de otro nivel.
    - Pendiente de la confirmación de Steven.
- **P6:** RESUELTA (23/10). Steven: "USA ARIAL".
  - CATDIC-STP usa Arial (`ARIAL.TTF`, no Arial Narrow). `_put` reduce la fuente si el texto no cabe en una línea.
  - Si con Arial salen valores ilegibles por quedar demasiado pequeños, se le avisa a Steven antes de fijarlo.
- **P7:** resuelta; ver Respuestas de Steven.
- **P8 (T0):** PARCIAL. Steven entregó los scripts y las plantillas (ver "Fuentes recibidas"). **Siguen faltando `FORMULARIOS MIVED.pdf` y el logo CATDIC.**
- **P9:** maquetación de la hoja fotográfica STP con 2 o 3 fotos. T6 propone:
  - 2 fotos → dos columnas;
  - 3 fotos → 1 ancha arriba y 2 abajo.

  El formato antiguo dejaba una celda vacía en la 2×2, lo que es el error #3. ¿Se acepta?
- **P10:** las copias de las fuentes (scripts con licencia, dirección y residente de Terra Living) ¿se guardan **fuera de git** (`FABRICA/` en `.gitignore`, propuesta) o se versionan para que Codex también las vea?
- **P11:** los datos de cabecera del proyecto (licencia, dirección, provincia, sector, residente) ¿los llenas tú desde el tablero (T7a, propuesta)? ¿O se toman de un FI o STP ya entregado, que tú confirmas?

## Fuera de alcance de esta etapa
- Formatos HV (`HV-LEV`, `HV-LEVEVAL`, `HV-LEVEST`, `HV-INFTEC`): Etapa 4.
- Extraer datos de diseño leyendo planos con OCR o visión: la Capa 1 sale solo de la Etapa 2.
- Firmar formularios o insertar firmas: está prohibido (§3.1).
- Acceso multiusuario o en red.
