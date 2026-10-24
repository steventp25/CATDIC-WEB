# Etapa 3 — Evaluaciones internas

## Evaluación 1 · 22/10/2026 · Auditor CATDIC · T1 y T4 (bloque 3A)

### T1 — Dependencias de la fábrica (rama `claude/etapa3-t1-dependencias`, `a467e21`)
**Veredicto: APROBADO.** Sin bloqueantes.

**Versiones**
- `pip list` de Python 3.14 coincide con `BACKEND/requirements.txt`: fastapi 0.156.8, uvicorn 0.54.0, pymupdf 2.0, pillow 13.0.0, playwright 1.64.0 y pypdf 6.21.2.
- Fijar fastapi y uvicorn es razonable: son las versiones que ya corrían y el archivo es nuevo.
- `import fitz` da un DeprecationWarning. **En T6–T9, el código nuevo usa `import pymupdf`.**

**Observaciones (no bloquean)**
- No se fijan las dependencias transitivas (pydantic, starlette). Si hace falta, más adelante se puede hacer un `pip freeze` aparte.
- `requirements-dev.txt` no cambió; no hacía falta.
- Si el Dropbox no está disponible, se saltan las 4 pruebas que lo usan.

**Criterios**
- [x] `import fitz, PIL, playwright, pypdf` → OK.
- [x] La prueba de humo pasa.
- [x] pytest: `484 passed, 4 skipped` con un Dropbox falso, que equivale a 488 con el real.

### T4 — API de la Mesa de Dudas (rama `claude/etapa3-t4-mesa-dudas`, `aebab4e`)
**Veredicto: APROBADO.** Sin bloqueantes. O1 y O2 tienen que pasar a tareas antes de T5.

**Puntos revisados**
- **"Corresponde" no inventa un STP** (`mesa_dudas.py:142-165`).
  - Solo acepta un grupo de `origen_datos_json.stp_candidatos`, que escribió `evaluar_p3`.
  - Nunca ofrece los STP de la otra clase (P3 estricta).
  - Si hay varios candidatos, exige `stp`. Si no hay ninguno, responde 422.
  - Detalle `:164-165`: no comprueba que el archivo siga existiendo. Se recomienda `Path.exists()` y 422 si no está.
- **`estado_mesa` diferido:** un sync no lo pisa.
  - Se conserva en `{**origen_viejo, …}`.
  - `Procesada` queda protegida por `ESTADOS_AVANZADOS` y por `origen.estado = "mesa_dudas"` (`sincronizador.py:477`).
  - **Falta una prueba del camino diferido** (0 referencias a `estado_mesa` en las pruebas).
- **Transacción y auditoría:**
  - `BEGIN IMMEDIATE` + `ROLLBACK`.
  - Fila `MESA_DUDAS/RESPONDER_DUDA` con los valores y estados anterior y nuevo.
- **Fecha:** DD/MM/AAAA estricta (`5/3/2026` y `31/02/2026` → 422). Error #12 cubierto.
- **Estado:** solo pasa a `Procesada` tras un "corresponde" con un STP candidato; si no, queda `Sin procesar`.
- **BD real, solo lectura:**
  - 0 filas `MESA_DUDAS` en auditoría;
  - 18 dudas, ninguna resuelta;
  - visitas sin cambios: 12 Con dudas, 6 Procesada, 4 Sin procesar.

**Observaciones**
- **O1.** La duda `archivos_json` de la #19 no se puede cerrar nunca.
  - `mesa_dudas.py:39-40` dice "se resuelve al sincronizar", pero el sincronizador no cierra dudas: no hay ningún `UPDATE … resuelta` en `BACKEND/sync/`.
  - Hay que hacer una tarea antes de T5.
- **O2 (CONFIRMADO, defecto de la Etapa 1).** `BACKEND/sync/sincronizador.py:236-242` (`_campos_resueltos`) no filtra por categoría.
  - Un `HALLAZGO_INTERNO` marcado como revisado congela el campo: el sync deja de actualizarlo (`:407-411`) y no vuelve a crear su duda (`:418`).
  - Caso real: la #8 (hallazgo de clase y bloqueante de fecha).
  - Arreglo: `AND categoria = 'DUDA_BLOQUEANTE'`, más una prueba. Debe estar antes de T5.
- **O3.** `Mixta` desde la Mesa deja `clase_detalle_json = []`. Pregunta para Steven.
- **O4.** Las dudas de elemento se cierran sin aplicar el valor. T3 o T10 deben leer `respuesta_usuario`, o T10 no debe procesar esos elementos.
- **O5 (para T10).** Al responder las fechas de las visitas #1 a #10, pasan a `Sin procesar` sin que se reevalúe P3. Procesar Cola podría regenerar informes antiguos.
- **O6.** Un `categoria` inválido en `GET` devuelve una lista vacía. Es aceptable.

**Criterios**
- [x] Las 22 pruebas del plan.
- [?] El GET real de la #19 no se pudo reproducir por HTTP, porque el servidor activo es `main`, que no tiene T4. En la BD (solo lectura), la #19 tiene 1 duda: id 5, `archivos_json`, sin resolver. Coincide con el reporte del Ejecutor.
- [x] pytest: `501 passed, 4 skipped` con un Dropbox falso, que equivale a 505.

**Reglas**
- Regla de Oro: datos `SINTÉTICO`.
- §1.5: hay auditoría.
- Sin `.db` ni secretos.
- El router se registra antes del montaje estático.

## Evaluación 2 · 22/10/2026 · Auditor CATDIC · T4b (rama `claude/etapa3-t4b-correcciones`, `06051b6`, sale de T4 `aebab4e`)
**Veredicto: APROBADO.** Sin bloqueantes. Hay dos observaciones (O1 y O2) que deben resolverse antes de T10.

### Decisiones del Ejecutor
1. **Quitar el 409 de hallazgos** (`mesa_dudas.py:217-220`): correcto. Con (a) ya no hace falta, y queda cubierto por pruebas tanto en la Mesa como en el sync.
2. **`estado_tras_cerrar_bloqueantes` compartida** (`sincronizador.py:255-273`): correcto.
   - Una sola regla para todos.
   - Solo actúa sobre visitas `Con dudas` que ya no tienen dudas abiertas.
   - Nunca pasa una visita a `Procesada` por su cuenta.
   - Se ejecuta después de insertar las dudas nuevas de la pasada.
3. **Reabrir `archivos_json`** (`:300-316`, `:504-509`): es seguro.
   - Solo reabre lo que cerró el sync ("resuelta por sincronización").
   - Una visita `Procesada` no vuelve a `Con dudas` (`:507`, `ESTADOS_ABIERTOS`). Lo que ocurre es que queda `Procesada` con una bloqueante abierta.
4. **`_campos_resueltos` excluye la duda cerrada por el sync** (`:247-252`): correcto.
5. **El paso a `Procesada` por `estado_mesa` no vuelve a comprobar (d)** (`:270-272`): no bloquea, porque la decisión es explícita de Steven y la ventana es pequeña. Queda como O1.

### Observaciones
- **O1 (antes de T10).** Repetir el `Path.exists()` de (d) dentro de `estado_tras_cerrar_bloqueantes`. Si el STP ya no existe, la visita sigue `Con dudas` con una nueva duda `estado`. Agregar la prueba correspondiente.
- **O2 (antes de T10 / T3).** Al cerrar `archivos_json` se acepta cualquier PDF que aparezca en la carpeta. T3 debe comprobar que el PDF se puede leer como visita.
- **O3.** Falta la prueba de reapertura sobre una visita `Procesada` (debe seguir `Procesada` con la duda abierta). T5 tiene que mostrar ese caso.
- **O4.** El cierre por sync queda auditado (`SYNC/CERRAR_DUDA_ARCHIVOS`, con estado anterior y nuevo).
- **O5.** (e) rechaza `Mixta`, `mixta`, `Parciales`, `Final` y vacío. Las visitas que ya son Mixta (#12) no se tocan.

### Criterios
- [x] Pruebas (a)–(e). pytest: `513 passed, 3 warnings in 12.18s`.
- [x] Sync real sin cambios: la BD coincide con el respaldo `20261022-133234` en visitas (22) y dudas (18, 0 resueltas). En auditoría solo se agregó la fila 31 `SINCRONIZAR_DROPBOX`. Estados 12 / 6 / 4.

## Evaluación 3 · 23/10/2026 · Auditor CATDIC · T2 y T6

### T2 — Reconocimiento del PDF de visita (rama `claude/etapa3-t2-reconocimiento`, `5873c95`)
**Veredicto: APROBADO.** Sin bloqueantes.

**El informe coincide con los PDF reales.** El Auditor recorrió las 3 visitas completas en solo lectura, sin decodificar imágenes.

| Visita | PDF | Con etiqueta / sin etiqueta | Etiquetas literales verificadas |
|---|---|---|---|
| #17 | 14 pp, fotos de 768×1024 | 3/11 | `Mh4`, `Mh1 pantalla eje 3`, `Pantalla eje B` |
| #18 | 70 pp, 327 MB, iOS | 30/40 (pp. 1–2 sin etiqueta) | `Pórtico eje 4 tramos MC-D`, `Tramo D-B`, `MC- A`, `Losa 13`, `Muro perimetrale`, `Losa 12` |
| #20 | 72 pp | 31/41 (p. 1 sin etiqueta) | `P eje 1`, `P eje C corregir Peralte de 0.60 a 0.70m`, `Garantizar recubrimiento`, `L 11`, `Mc eje A’ Tramo 3-4’` |

- En la #20, la prima de `Mc eje A’ Tramo 3-4’` es el carácter U+2019 (`’`), no la comilla recta.
- Notas de la #20: p. 35, el peralte cambió de 0.70 a 0.60; p. 52, `1 cm más de eso 0.26`.
- Las 64 etiquetas empiezan en x = 56,0 pt, justo debajo de la foto.

**Las propuestas para T3 no inventan datos.**

**Observaciones para T3:**
- **O1. No toda etiqueta es un elemento.** Hay etiquetas que son instrucciones u observaciones: `Garantizar recubrimiento`, `As infiernos 5-3/4 continuaron armado`, `Muro perimetrale`. T3 no decide si abren elemento: guarda el texto original y crea una `DUDA_BLOQUEANTE`.
- **O2. Tramos sin pórtico.** En `Tramo D-B` o `MC- A` no se deduce el eje del pórtico por el orden del log: queda `pendiente de verificar`. Además, §4.3 permite varias fichas por tramo.
- **O3. Normalizar `’` → `'` y `mc` → `MC`.** Es determinista, pero tiene que aprobarlo Steven por escrito. Mientras tanto, la prima `’` queda pendiente, como hace hoy `interpretar_eje_de_visita`.

### T6 — Módulos visuales comunes y salida segura (rama `claude/etapa3-t6-comunes`, `ab66691`)
**Veredicto: BLOQUEADO.**

**Bloqueante**
- `BACKEND/generators/comun/detalle.py:19` y `:29-34`, error #2.
  - `carpeta_planos` es opcional, así que sin ella el único filtro es la extensión `.pdf`. Eso deja pasar un PDF de visita (fotos de campo) como DETALLE.
  - Corrección: hacer `carpeta_planos` obligatorio y agregar una prueba que rechace un `.pdf` que imite un PDF de visita sin pasar ese argumento.

**Puntos revisados**
1. **Cuadrícula de 2 y 3 fotos** (`fotos.py:63-79`). Con 3 fotos usa 1 ancha arriba y 2 abajo; con 2, dos columnas. Evita el error #3, pero el CLAUDE.md no describe esa maquetación. Decide Steven antes de T7, comparando con un STP real.
2. **Modo `"x"` y retiro del PDF rechazado** (`salida.py:62-75`): aceptable. Solo borra el archivo que acaba de crear él mismo, en la carpeta de pruebas, y queda auditado.
   - Mejora: comprobar el tamaño antes de escribir.
   - `existia_antes` (`:63`) siempre vale False; la protección real la da el modo `"x"`.
3. **Errores cubiertos por pruebas:** #1, #3, #4 y #15 [x]. El #2 [ ] es el bloqueante.
4. **Nunca escribe en Dropbox** [x] (4 pruebas).
5. **D1:** usa `getpass.getuser()` [x]. Pero el sincronizador y la Mesa siguen con `USUARIO = "steven"` fijo, y eso queda para una tarea aparte.
6. **Coordenadas solo por parámetro** [x]. Las inválidas dan `ValueError` "pendiente de verificar".

**Observaciones**
- Memoria de M3: rasterizar a 200 ppp un plano de 24×36″ ocupa unos 100 MB, y se duplica con `.copy()`. Medirlo con el plano real antes de T7.
- M4 todavía no tiene la banda de estribos, la fila en rojo ni los rótulos "1"/"2". Va en T7/T9.
- `test_terra_living_real` depende del Dropbox real (22 carpetas). Conviene que use "al menos" o marcarla como prueba de integración.

**Pruebas:** `508 passed, 3 warnings in 12.25s`.

## Evaluación 4 · 23/10/2026 · Auditor CATDIC · Reevaluación de T6 (`33eb593`, diff `ab66691..33eb593`)
**Veredicto: APROBADO.** El bloqueante del error #2 quedó resuelto.

**Cómo se resolvió (`detalle.py:18-38`):**
- `carpeta_planos` ahora es obligatorio:
  - si no se pasa → `TypeError`;
  - si llega vacío → `ValueError` "pendiente de verificar";
  - si el PDF está fuera de esa carpeta → "Error #2".
- Pruebas nuevas:
  - `test_detalle_rechaza_un_pdf_de_visita_fuera_de_la_carpeta_de_planos_error_2`
  - `test_detalle_exige_la_carpeta_de_planos`
- Fuera de las pruebas, nadie más llama a `recortar_detalle`.

**Mejoras:**
- `salida.py:63-70` comprueba el peso antes de escribir (≥ 30 MB): registra `RECHAZAR_PDF` en la auditoría y no crea ningún archivo.
- La auditoría registra `version_nueva` en lugar de `existia_antes`.

**Observaciones:**
- T7 y T9 deben pasar exactamente `ARCHIVOS DEL CLIENTE\PLANOS ESTRUCTURALES\PLANOS SELLADOS\`, nunca una carpeta más amplia. Conviene que T7 lo pruebe.
- Siguen abiertas:
  - la maquetación de 2 y 3 fotos (decide Steven);
  - medir la memoria de M3 con el plano real;
  - `test_terra_living_real`;
  - `USUARIO = "steven"` fijo (D1).

**Pruebas:** `510 passed, 3 warnings in 8.80s`.

## Evaluación 5 · 23/10/2026 · Auditor CATDIC · T3 (rama `claude/etapa3-t3-lector-visita`, `3d0b54f`)
**Veredicto: BLOQUEADO** (3 bloqueantes)

### Bloqueantes
- **B1. La hora de `Creado el:` se guarda como nota** (`BACKEND/sync/lector_visita.py:95-102`). En la #17, `Creado el:` y la hora son líneas distintas a la misma `y`. El código busca la hora solo en la misma línea y, al no encontrarla, guarda la hora como `nota`.
  - Efecto en la BD real: las 14 fotos tienen `hora = null` y `nota = '28/09/2026 11:03'`, etc.
  - La prueba sintética pone las dos cosas en un solo span (`test_lector_visita.py:46`), por eso no lo detecta.
  - Corrección:
    - tomar la hora por su `y`;
    - agregar una prueba con `Creado el:` y la hora en líneas separadas;
    - volver a correr la #17.
- **B2. Rechaza la #18 entera** (`:89`, `:125-133`). En las páginas 22–23 hay fotos apaisadas de 3840×2160 y el texto `Creado` / `el:` / fecha va **a la derecha** de la foto (x≈407-528, y≈68-92), no debajo.
  - Esto corrige también el informe de T2, que decía "debajo de la foto, verificado en las tres". Los conteos no cambian: esas dos páginas no tienen etiqueta.
  - Corrección:
    - buscar `Creado el:` en la zona de la foto (debajo o a la derecha), sin contar cabecera ni pie;
    - aceptar `Creado` y `el:` partidos en dos líneas;
    - agregar una prueba sintética con foto apaisada;
    - criterio nuevo: la #18 da 70 páginas y 30 etiquetas (verificar en solo lectura).
- **B3. Edición a mano de la duda id 20 en la BD real, sin auditoría** (§1.5).
  - El texto nuevo coincide con el que genera el código final.
  - La edición se hizo a las 08:23, después de la fila de auditoría 33, y no quedó ni respaldo ni rastro.
  - Propuesta: con el visto bueno de Steven, agregar una fila `MANUAL/CORREGIR_TEXTO_DUDA` (entidad 20) con el texto anterior y el nuevo.
  - De aquí en adelante, ningún cambio a mano en la BD real.

### Puntos revisados
- La #17 sigue `Procesada` con 3 bloqueantes: es coherente con O3 de T4b. Visitas sin cambios respecto al respaldo.
- Encaja con la Mesa de Dudas:
  - `id_elemento` no vacío → solo se guarda la respuesta;
  - `campo_afectado = elemento_visita:pNNN` no choca con el sync.
  - T5 debe mostrar ese valor como "etiqueta", y T10 no debe usarlo como ID.
- Cruce de una sola letra (`:45`, `:169-176`): correcto y prudente.
- No hay deducciones de `agrupar_log_fotografico_visita`: solo usa `g["fotos"]`.
  - #20: 32 grupos, notas de p35 y p52 literales.
  - #17: 3 grupos.
- Caché:
  - lado máximo de 1000 px, q72;
  - ocupa menos que el PDF;
  - nunca dentro de Dropbox;
  - Dropbox intacto (mtime sin cambios).
- Nivel solo si es `S-\d+` y único: #17 y #18 dan S-4; la #20 queda pendiente.
- Respaldo previo, auditoría con getpass y la segunda corrida da 0 nuevas.

### Observaciones
- **O1.** El lector no pasa una visita `Sin procesar` a `Con dudas` cuando le crea bloqueantes, como sí hace el sync. Riesgo: T10 la tomaría para procesar.
- **O2.** `tokens[0].upper()` (`:185`) pasa el ID a mayúsculas. Es una normalización que debe aprobar Steven; mientras tanto, se guarda tal cual.
- **O3.** `reconocido` no exige `tipo_elemento`. Un `C1 A4` queda sin duda pero con tipo pendiente; se resuelve al cruzar con la Capa 1.
- **O4.** La caché no se regenera si el PDF cambia. Conviene invalidarla por tamaño y mtime del PDF.
- **O5.** `respaldar=False` por defecto (`:260`), y la rama de rechazo (`:278-285`) escribe una duda sin respaldo.

**Pruebas:** `510 passed, 3 warnings in 10.80s`.

## Evaluación 6 · 23/10/2026 · Auditor CATDIC · T5 (rama `claude/etapa3-t5-mesa-ui`, `5a8779e`, sale de T4b `06051b6`)
**Veredicto: APROBADO.** Sin bloqueantes.

**Cómo se verificó:** en el navegador, con uvicorn apuntando a una **copia** de la BD real. La copia se hizo con la API de respaldo y la BD real se abrió en `mode=ro`.

**Puntos revisados**
- Mixta, `archivos_json` y `lector_visita`:
  - el selector de clase solo ofrece Parcial y Completivo;
  - la #19 no tiene ningún control, solo el texto de cierre por sincronización;
  - los campos desconocidos muestran "no se responde desde la Mesa".
- Errores y caídas:
  - una respuesta inválida da 422 con el mensaje de la API y la duda sigue abierta;
  - responder una duda ya resuelta da 409 ("La duda 7 ya está resuelta.") y el panel sigue abierto;
  - con el backend caído aparece el aviso y no se cierra nada.
- Todas las fechas se muestran en DD/MM/AAAA, también las de creación y resolución.
- El frontend no valida reglas: solo envía texto. Los STP salen de `stp_candidatos`.
- XSS: no hay `v-html`, `innerHTML` ni `eval`.
  - Una duda sintética con `<img onerror>` y `{{ 7*7 }}` se pintó como texto literal.
  - `visita_id` va con `encodeURIComponent`.
- O3 de T4b cubierto: la #17 muestra "Procesada con N dudas bloqueantes abiertas".
- BD real intacta: 0 filas `MESA_DUDAS`, 21 dudas sin resolver, estados 12/6/4.
- No hay ningún `.db` versionado.

**Observaciones (no bloquean)**
- **O1.** Las dudas de elemento de T3 aparecen como `Elemento: Mh4 · Campo: elemento_visita:p001`. Conviene:
  - rotularlas "Etiqueta en la visita";
  - traducir el campo a "Fotos p. 1–6";
  - avisar que esa respuesta se guarda pero no se aplica.
- **O2.** Después de un 409, recargar las dudas de la visita.
- **O3 (de antes).** `index.html:7-8` carga Tailwind y Vue desde un CDN sin versión fija, así que el tablero no funciona sin internet. Hay que fijar la versión o servirlos en local.
- **O4 (de antes).** `API` está fijo en `localhost:8000`; con varios usuarios dejará de servir.

**Pruebas:** `513 passed, 3 warnings in 9.73s`.

## Evaluación 7 · 23/10/2026 · Auditor CATDIC · Reevaluación de T3 (`f209037`, diff `3d0b54f..f209037`)
**Veredicto: BLOQUEADO.** 1 bloqueante nuevo. Ya existía en 3d0b54f y se pasó por alto en la Evaluación 5.

### Bloqueante
- **`BACKEND/sync/lector_visita.py:207-210`: una etiqueta de un solo token (letra+número) se toma como cruce de ejes.** Viola la Regla de Oro, el error #11 y §4.4 (losas `—`).
  - En la #20 real (solo lectura), los grupos `L5`, `L8`, `L7`, `L6`, `L2` y `L1` quedan con `EJE L-n`. Pero `L5` es la losa 5, no un cruce. Lo mismo pasaría con `C1` o `Z4`.
  - Sin la Capa 1 no se puede distinguir un ID de un cruce, así que elegir "cruce" es adivinar.
  - La BD real no está afectada: la #20 no se ha cargado y la #17 no tiene etiquetas así.

### Bloqueantes anteriores: resueltos
- **B1 (hora por la `y`):** 0 fotos sin hora y 0 notas falsas en la #17, en la BD real.
- **B2 (texto a la derecha):**
  - #18: 70 páginas, 30 etiquetas, 31 grupos.
  - #20: 32 grupos, con notas solo en p35 y p52.
  - #17: 3 grupos.
- **B3:** la fila 36 coincide con el texto anterior (8fadaf3) y con el nuevo.

### Cambios nuevos
- **O1:** `_marcar_con_dudas` (`:288-309`) sigue la misma regla que el sync. Correcto.
- **O5:** respalda por defecto, también antes del rechazo. Correcto.
- **Normalización** `’`→`'` y mayúsculas, solo para interpretar: `etiqueta_original` queda literal y no inventa nada más.
  - Efecto a tener en cuenta: `Mh4 A1` → ID `MH4` + `EJE A-1`.

### BD real
- Idéntica al respaldo 084531, salvo la fila 36.
- 0 `MESA_DUDAS`, 21 dudas sin resolver.

### Criterios
- [ ] Falta la prueba con un ID de un solo token.
- [x] Corrida real de la #17.
- [x] pytest `528 passed`.

### Decisión de Steven (23/10/2026)
- Pregunta: "¿Una etiqueta que es SOLO letra+número (L5, C1, A1) se toma como cruce de ejes o como ID?"
- Respuesta: **"Dejar pendiente"**. Una etiqueta de un solo token deja `ejes = pendiente de verificar`, y la duda del grupo pregunta qué es. Esto **acota la regla §4.4** "A1 = cruce A-1" para el lector de visitas: el cruce solo se lee cuando la etiqueta trae un ID y luego el cruce (`C1 A4`).

## Evaluación 8 · 23/10/2026 · Auditor CATDIC · Reevaluación de T3 (`df25838`, diff `f209037..df25838`)
**Veredicto: APROBADO.** Queda resuelto el bloqueante de la Evaluación 7.

**Qué cambió**
- `lector_visita.py:209-212`: se eliminó la rama que interpretaba un token suelto. Ahora `ejes` e `id` solo se llenan con el patrón de dos tokens `ID letras+número` + `cruce de una letra`.
- No queda otro camino de deducción:
  - la única asignación distinta de "pendiente" es `:212`;
  - `tipo_elemento` nunca se llena;
  - no se usan ni `id_sugerido` ni `etiqueta_apertura`.

**Casos probados**
- Quedan todos pendientes: `A1`, `1A`, `L5`, `C1`, `A’1`, `L 3` y `Tramo D-B`.
- `c1 a4` → C1 + `EJE A-4`.
- `C1 A’4` → C1 + `EJE A'-4`.
- `Mh4 A1` → MH4 + `EJE A-1`.

**PDF reales (solo lectura)**
- #17: 3 grupos.
- #18: 31 grupos.
- #20: 32 grupos.
- Ninguno queda con ejes, id o tipo. Todas las fotos tienen hora. Las notas solo aparecen en la #20, páginas 35 y 52.
- La BD real no se tocó: la última fila de auditoría sigue siendo la 36.

**Observaciones**
- CLAUDE.md/AGENTS.md §4.4 ("A1 = cruce") ya no coincide con la decisión de Steven. Hay que actualizarlo; lo decide Steven.
- El docstring de `interpretar_eje_de_visita` debe aclarar que solo se usa dentro del patrón ID + cruce.
- Siguen abiertas:
  - O3 y O4 de la Evaluación 5;
  - el rótulo "Elemento" en la Mesa (T5).

**Pruebas:** `538 passed, 3 warnings in 16.09s`.

## Evaluación 9 · 23/10/2026 · Auditor CATDIC · Spec §4.4 (rama `claude/spec-ejes-visita`, `cef959b`)
**Veredicto: APROBADO.**
- Solo cambia la línea 149 de CLAUDE.md y de AGENTS.md. El texto es idéntico byte a byte en los dos archivos y la diferencia previa entre ellos (nombre del agente) sigue igual.
- Coincide con el código de T3 (`df25838`):
  - token suelto → pendiente;
  - `C1 A4` y `C1 4A` → C1 + `EJE A-4`;
  - normalización con la etiqueta original literal.
- No contradice el resto de §4.4: prima recta, losas `—`, platea.
- Formato intacto: LF, sin BOM, escapes conservados.
- Observación: el código solo lee cruces de una letra (`C1 AA4` queda pendiente). El texto no lo dice explícitamente, pero lo cubre "lo que no se pueda leer… pendiente".

## Evaluación 10 · 23/10/2026 · Auditor CATDIC · T0b (rama `claude/etapa3-t0b-inventario`, `8ca5e3f`)
**Veredicto: BLOQUEADO** (2 bloqueantes)

**B1.** `PLANES/etapa-3-inventario-fuentes.md:141-142, :186`: el informe dice que el FI-03 no marca la sección SEGURIDAD, y es **falso**. En los 5 FI-03 de Terra, la página 3 tiene 9 marcas: 10a-10e (SEGURIDAD) y 11a-11d (PROBETAS).
- Hay que corregirlo y quitar la duda falsa.
- La frase "siempre las mismas" pasa a "casi siempre", listando las excepciones: FI-02 #4 (6 marcas) y FI-02 #3 (p1 sin marcas).

**B2.** `PLANES/etapa-3-inventario-fuentes.md:22-26, 125, 128`: el inventario copia a git datos del cliente (licencia, dirección, sector, residente y su CODIA), contra lo decidido en P10.
- Sustituirlos por marcadores.
- También se quitan el autor "Steve" de la anotación y los nombres de los firmantes.
- El planificador ya limpió esos mismos valores de `PLANES/etapa-3.md`.

**Puntos revisados**
- **Cobertura de valores fijos:** correcta en lo esencial, con tres imprecisiones:
  - O1: el valor `Ø3/8"` está en `V(...)`, no en `rows_viga`.
  - O2: falta nombrar `rows_losa` Longitud X/Y.
  - O3: `fi02.py` (parcial) **borra** las fechas de autorización, mientras que `fi02_s5.py` (completivo) escribe día y mes. Esto parece una regla implícita de negocio, pendiente de que Steven la confirme.
- **Coordenadas de los FI:** son reales, verificadas en el FI-02 #12 y el FI-03 #10.
  - Ninguno es AcroForm.
  - Las marcas son de 12×12 pt.
  - La firma es una anotación Square.
- **Mampostería:** está en el FI-03, secciones 8 y 9, sin marcar. La marca del "No" no se adivina. Los dinteles del FI-02 (secciones 8-9) quedan como duda para Steven.
- **Áreas de barra:** el motor usa las áreas nominales ASTM A615 (1.29 / 2.84 / 5.10). Las fuentes usan el área geométrica π·d²/4 (1.27 / 2.85 / 5.07). Falta registrar la tercera discrepancia: `A1 = 5.07` para Ø1".
  - Recomendación: mantener las del motor, con la confirmación de Steven.
- **`FABRICA/`:** está en `.gitignore`, pero el worktree del Ejecutor, en otra rama, la muestra como sin seguimiento. Hay que agregarla a `.git/info/exclude`.

## Evaluación 11 · 23/10/2026 · Auditor CATDIC · T7a (rama `claude/etapa3-t7a-proyecto`, `e0112db`, sale de `a1891ff`)
**Veredicto: APROBADO.** Sin bloqueantes.

**Migración**
- Es idempotente: saca un respaldo antes y deja la auditoría en la misma transacción.
- No reconstruye la tabla ni siembra valores.
- Una BD nueva no genera ni respaldo ni auditoría.
- Detalle: la auditoría de la migración pone el usuario `"steven"` fijo (lista D1).

**PATCH**
- Acepta los 6 campos de cabecera (P11).
- El SQL dinámico se arma solo con los campos del modelo, así que no admite inyección.
- Registra la auditoría con el valor anterior y el nuevo y con `getpass.getuser()`.
- Un 404 o un 400 no dejan auditoría.
- Mejora posible: no auditar un PATCH que no cambia nada.

**Prueba de migración**
- La prueba de respaldo quedó algo más floja: ya no detecta respaldos de más.
- Propuesta: exigir 2 respaldos, cada uno ligado a su fila `MIGRACION_*`.

**Fusión**
- Hay un conflicto mecánico en `BACKEND/main.py`, con `origin/main` y con T4, en dos lugares: los imports y el cuerpo de `actualizar_proyecto`.
- La causa: T7a sale de `a1891ff`, que es anterior a `c310efa`.
- Se resuelve fusionando `origin/main` en la rama: imports de los dos lados y el cuerpo de T7a.

**BD real** (comparada con el respaldo 133140)
- Solo hay 3 columnas nuevas vacías, la fila 37 y una fila 38 `SISTEMA/INICIALIZACION_BD`. La 38 viene del arranque del servidor, es inocua y no cambió ningún dato.

**Pruebas:** `492 passed`.

## Evaluación 12 · 23/10/2026 · Auditor CATDIC · Reevaluación de T0b (`5e6e115`) y T7a (`1a40abf` + `8e5f6a9`)

### T0b — APROBADO
- **B1 resuelto.** En el FI-03, la página 3 tiene 9 marcas (10a-10e y 11a-11d). Se quitó la duda falsa y se cambió "siempre" por "casi siempre", con sus excepciones.
- **B2 resuelto.**
  - La rama tiene un solo commit sobre `c912661`, y su parche no contiene ningún dato del cliente: solo marcadores.
  - Los commits aplastados (8ca5e3f, 6fea96c, 27c645f) no están en ninguna rama remota ni en ningún `refs/pull/*`.
  - El árbol es idéntico al de 27c645f.
- **Observaciones:**
  - O1, O2 y la tercera discrepancia de área quedaron resueltas.
  - O3 tiene un residuo: la línea 162 conserva la frase vieja "fi02.py reescribe solo día y mes", que contradice la línea 163. Se corrige en un retoque.
  - `FABRICA/` queda excluida en todas las ramas.

### T7a — APROBADO
- La resolución de `main.py` contra `origin/main` solo trae lo de T7a; se conservan StaticFiles y CORS.
- `database.py` y los tests incluyen también la Etapa 2 T1: el PR #4 va antes o junto con este.
- La prueba quedó reforzada: exige 2 respaldos ligados a `MIGRACION_VISITAS` y `MIGRACION_PROYECTOS_CABECERA`, sin respaldos huérfanos.
- `merge-tree` sale limpio contra main, T3, T4, T4b, T5, T6 y T0b.
- **Pruebas:** `493 passed`.

## Evaluación 13 · 23/10/2026 · Auditor CATDIC · T7 (rama `claude/etapa3-t7-stp-mived`, `54aa156`, sale de T6 `33eb593`)
**Veredicto: BLOQUEADO** (3 bloqueantes). El Auditor lo comprobó generando un PDF sintético.

### Bloqueantes
- **B1** `stp_mived.py:183-197`: sin medida de campo, la columna OBRA copia el valor del plano. `evaluar_medida_acero_obra` con `None` devuelve el valor del plano y `conforme = True`, y deja un aviso que el generador ignora.
  - En el PDF sintético salió `2.c 0.40`, `2.d 0.60` y `2.b 0.25`, valores que nadie midió.
  - Corrección: la celda queda vacía y se crea una duda `medidas.<letra>`. Agregar la prueba correspondiente.
- **B2** `:179-180`: OBRA f/g (recubrimiento) toma el valor de la norma §4.5, como si se hubiera medido en obra. Esos valores deben salir de la Capa 2; si no están, la celda queda vacía y se crea una duda no bloqueante.
- **B3** `:316-321` y `:392-398`: la hoja de inspección dice "ACORDE A PLANOS APROBADOS" aunque toda la columna OBRA esté sin verificar. La conformidad debe exigir también 0 dudas de OBRA y 0 medidas pendientes.

### Puntos revisados
- No quedan valores fijos de diseño ni de proyecto (búsqueda con grep), salvo lo de B2. La cabecera vacía bloquea la generación.
- Las filas obligatorias son razonables. **O1:** `e. Calzos coloc.` es una comprobación de obra, así que en PLANOS no debe ser obligatoria.
- Recubrimiento en PLANOS: tomarlo de §4.5 se puede defender como norma. Pregunta para Steven: ¿va el de §4.5 o el que indique el plano?
- La línea de ESTRIBOS no inventa datos, pero sirve para pasar el control #9. **O2:** el auditor necesita una regla propia para STP-MIVED.
- La cuantía se calcula siempre con 4 decimales y áreas ASTM. **O3:** en columnas, comprobar que el total de barras coincida con la lista `barras`.
- Los rótulos son literales. "Cuantia ()" ya era así en la fuente: no se perdió ninguna ρ.
- Orden y numeración de páginas correctos (verificados en el PDF).
- El nombre del archivo cumple §5.2. **O4:** `.title()` escribe "Y" en mayúscula.
- Usa T6. **O5:** LOCALIZACION debe validar que su PDF esté dentro de `carpeta_planos`.
- **O6:** `MURO DE CONTENCION`, `ZAPATA` y `PLATEA` dan "tipo no soportado" y bloquean el STP completo. Las visitas reales tienen "Muro perimetral".

**Pruebas:** `536 passed`.

## Evaluación 14 · 23/10/2026 · Auditor CATDIC · T8 (rama `claude/etapa3-t8-fi-mived`, `e7faa13`, sale de T6 `33eb593`)
**Veredicto: BLOQUEADO** (1 bloqueante)

### Bloqueante
- **`fi_mived.py:156-174` (`_escribir_cabecera`) y `:280-282`: al partir de la plantilla en blanco, la cabecera sale vacía.**
  - Las plantillas no traen Nombre del proyecto, Licencia No., Sol. Licencia No., Encargado de obra ni Dirección.
  - Corrección:
    - escribir esos 5 campos, localizándolos por su rótulo;
    - si alguno falta, `"pendiente de verificar"` + error;
    - agregar una prueba con una plantilla en blanco;
    - confirmar con Steven que "Encargado de obra" = `residente_obra`.

### Puntos revisados
- **Localización por rótulos:** probada en los 18 FI disponibles (12 de Terra llenos, 3 de Serenity y 3 en blanco de Terra). Encuentra todas las filas de `FILAS_SI`.
- **Marcas "Sí":** la tabla coincide con los PDF reales.
  - FI-03 incluye 2a-2d y 5e.
  - No hay ninguna fila 8x ni 9x.
  - Nunca se marca "No".
  - No duplica marcas: `_ya_marcada` con tolerancia de ±6 pt.
  - Si falta una fila → error.
- **Anotaciones:** se borran todas; no se inserta ninguna firma.
  - **[?] para Steven:** `_blanquear_fechas_autorizacion` (`:216-225`) también **borra las fechas de autorización que ya existían** (en el FI-02 #12 desaparece `02 / 10`).
- **Observaciones:** la nueva se agrega debajo de las existentes. CONFORME solo va en una visita Completivo sin discrepancias.
  - O2: T10 debe pasarle las discrepancias y dudas de los elementos.
- **P5 / #18:** el `nivel_clave` es obligatorio y el original no cambia (comprobado con sha256). Dropbox sin tocar.
  - O3: la comparación es por subcadena (`SOTANO -3` también encaja en `SOTANO -30`). Usar límites de palabra.
- `limpiar_extraido` solo afecta a la comparación de nivel.
- No hay valores fijos de Terra.
- El PDF de prueba se ve fiel al original.

### Observaciones
- **O1:** la fila 7c del FI-02 no tiene caja propia, así que la marca usa una posición de reserva y queda 4,5 pt a la izquierda. Corrección: usar la x de las cajas vecinas.

**Pruebas:** `536 passed`.

## Evaluación 15 · 23/10/2026 · Auditor CATDIC · Reevaluación de T7 (`476cf3e`, diff `54aa156..476cf3e`)
**Veredicto: BLOQUEADO** (1 bloqueante nuevo, pequeño)

**Bloqueante:** `stp_mived.py:339-349` y `:400-409`. Un elemento excluido (zapata o platea) desaparece del PDF sin decir cuál es.
- El "DATOS DE OBRA PENDIENTES DE VERIFICAR: N" mezcla las celdas vacías con los elementos excluidos.
- Corrección: agregar una línea explícita "ELEMENTOS NO INCLUIDOS EN ESTE INFORME (pendientes de verificar): …" y una prueba.
- Para T10: una visita con elementos excluidos no pasa a `Procesada`.

**Ya resuelto:**
- B1: sin medida, la columna OBRA queda vacía y se crea una duda (verificado en el PDF).
- B2: OBRA f/g sale de la visita.
- B3: la conformidad solo aparece si hay 0 pendientes.
- O1 a O5.
- O6: el muro de contención usa recubrimiento 0.075. Si todos los elementos quedan excluidos, no se genera el PDF.

**Pruebas:** `546 passed`.

## Evaluación 16 · 23/10/2026 · Auditor CATDIC · Reevaluación de T8 (`7751e57`, diff `e7faa13..7751e57`)
**Veredicto: APROBADO.**

**Cabecera**
- La cabecera de 5 campos (`_campos_de_proyecto`, `:179-215`) se probó en los 18 FI:
  - en las 6 plantillas en blanco escribe los 5 valores en las posiciones de T0b, sin avisos;
  - en los 12 FI de Terra no sobrescribe ningún valor ya escrito: deja 4 avisos y solo escribe "Sol. Licencia No.", que estaba vacío.
- El rótulo no se confunde con el valor.
- Detalle: en los FI-03 el valor anterior aparece duplicado dentro del aviso, porque el PDF trae dos capas de texto.

**PDF de prueba**
- La plantilla en blanco sale completa y la marca de 7c queda alineada (O1).
- La copia del FI-02 #12 conserva las fechas de autorización `02/10/2026`.
- Ninguno de los dos tiene anotaciones.

**Fechas de autorización:** ya no se borran; solo no se escriben fechas nuevas. Pendiente de que Steven lo confirme.

**Clave de nivel (O3):** se exigen límites de palabra y se rechazan las claves genéricas.
- Observación: una clave como `-4` todavía se acepta. T10 debe pasar siempre la clave completa (por ejemplo `SOTANO -4`).

**Dropbox:** el hash y las fechas de modificación de los archivos no cambiaron.

**Pruebas:** `548 passed`.

## Evaluación 17 · 23/10/2026 · Auditor CATDIC · Reevaluación de T7 (`4c83e2e`, diff `476cf3e..4c83e2e`)
**Veredicto: APROBADO.**

Casos sintéticos regenerados:

| Caso | Hoja de inspección |
|---|---|
| Viga sin medidas + ZAPATA-Z1 | "CELDAS O MEDIDAS DE OBRA PENDIENTES DE VERIFICAR: 9" + "ELEMENTOS NO INCLUIDOS…: ZAPATA-Z1" |
| Viga completa + ZAPATA-Z1 | Sin conformidad, con la línea de excluidos |
| Viga completa sola | "ACORDE A PLANOS APROBADOS" |

**Pruebas:** `547 passed`. El Ejecutor reportó 548, pero 547 es lo esperado (546 + 1).

**Recordatorio para T10:** una visita con elementos excluidos o con dudas de OBRA no pasa a `Procesada`.

## Evaluación 18 · 23/10/2026 · Auditor CATDIC · T5b (rama `claude/etapa3-t5b-mesa-rotulos`, `3d3a90c`, sale de T5)
**Veredicto: APROBADO.** Verificado en el navegador contra una copia de la BD.

**Lo que se comprobó:**
- Rótulos de la #17: "Etiqueta en la visita: Mh4 · Fotos p. 1–6", y así las demás. Cada una lleva su aviso.
- Si al guardar se recibe un 409, aparece el aviso, se recargan las dudas y el panel sigue abierto.
- Panel automático:
  - Se abre solo al sincronizar cuando hay dudas nuevas (verificado con la #2 recreada en la copia).
  - No se abre si no hay dudas nuevas ni si ya hay un panel abierto.
- XSS: no hay `v-html`.
- BD real intacta: 0 filas `MESA_DUDAS`.

**Pendiente:** los disparadores al cargar una visita (T3) y al registrar enlaces de archivos (D4) quedan para cuando existan esos endpoints (T10 o D4). Hoy no hay nada que los dispare.

**pytest:** `1 failed, 512 passed`. El fallo es de `test_parser_visitas.py:105` y no tiene que ver con esta tarea: viene de la carpeta #21, que es nueva. Lo corrige T12.

**Datos reales** (vistos en la copia; la BD real todavía no los tiene):
- La #19 ya tiene su PDF: con T4b, el próximo sync cierra su duda `archivos_json`.
- La #21 entra como `Sin procesar`.

## Evaluación 19 · 23/10/2026 · Auditor CATDIC · T7b (rama `claude/etapa3-t7b-stp-dos-visitas`, `0b3b828`, sale de T7 `4c83e2e`)
**Veredicto: APROBADO.**
- Con una sola visita, el resultado es idéntico al de T7.
- Las fechas se unen con " y " y se ordenan por fecha. La clase es "PARCIAL Y COMPLETIVO" y cada ficha lleva la fecha de su visita.
- Errores comprobados: niveles distintos, ids repetidos, visita sin nivel y `visita_id` desconocido o ausente.
- Las discrepancias, los pendientes de OBRA y los elementos excluidos se suman en todas las visitas.
- El PDF de 8 páginas se ve bien.

**Observación (para Steven):** si las visitas traen `elementos_txt` distintos, el nombre del archivo los concatena. Propuesta: usar el de la última visita.

**Pruebas:** `553 passed`, más 1 fallo ajeno (carpeta #21, se corrige en T12).

## Evaluación 20 · 23/10/2026 · Auditor CATDIC · T8b (`af14c13`) y T12 (`39a7477`)

### T8b: BLOQUEADO (1 bloqueante)
**Bloqueante:** `fi_mived.py:153-160` (`_redactar`, `fill=(1,1,1)`). La redacción blanca borra un tramo de la línea de la tabla del FI-01, en la página 3, cuando se mueve el cierre.
- Corrección:
  - redactar con `fill=False`, también en la cabecera y en `dd/mm/aaaa`;
  - agregar una prueba que compruebe que las líneas de la zona siguen iguales.

**Lo que funciona bien:**
- Las fechas anteriores se conservan en los 3 FI y la nueva fecha va en su fila.
- El cierre se mueve sin perder texto.
- Dinteles y cerramiento se marcan solo si la visita los incluye. La mampostería nunca se marca.
- La fila nueva copia la geometría de la anterior.
- Los originales no cambian (hash).

**Observaciones:**
- "CONFORME A PLANOS APROBADOS", escrito por el sistema en una visita anterior, no se reconoce como cierre. Conviene tratarlo como cierre.
- En el FI-02 #12, la fecha va en la página 4 ("Inspectores", hoja de inspectores adicionales). Pregunta para Steven: ¿va ahí o en la página 3?
- Opinión del Auditor sobre las filas vacías del FI-01 y del FI-03: son filas previstas para más inspectores, dentro del bloque "Inspectores". Es más correcto usarlas antes de agregar una fila nueva.

**Pruebas:** `562 passed` + 1 fallo ajeno.

### T12: APROBADO
- Detecta una carpeta conocida que falte; verificado con una mutación.
- La lectura de las 22 carpetas sigue fijada.
- Las carpetas nuevas se leen sin error.
- El escaneo no cambia el árbol.

**Pruebas:** `596 passed`, con la carpeta 21.

## Evaluación 21 · 23/10/2026 · Auditor CATDIC · Reevaluación de T8b (`4710729`)
**Veredicto: BLOQUEADO** (1 bloqueante, que vino de una recomendación equivocada del propio Auditor en la Evaluación 20)

**Bloqueante:** `fi_mived.py:316` (`INICIOS_DE_CIERRE` incluye "CONFORME A PLANOS APROBADOS"), visible en `:281`. Al mover el CONFORME de la visita anterior al final:
- si después de una completiva viene una parcial, el documento termina declarando conforme la visita parcial (contra §3.2);
- si vienen dos completivas, queda un CONFORME duplicado.

Corrección:
- usar solo `("TODO SEGUN",)`;
- agregar dos pruebas encadenadas: Completivo→Parcial (el Parcial queda sin CONFORME) y Completivo→Completivo (un CONFORME por cada visita).

**Lo que ya está bien:**
- Las rayas quedan enteras (FI-01 v2, FI-03 v2 y FI-02) y hay una prueba que lo comprueba.
- La fecha va en la primera fila vacía del bloque "Inspectores", en el FI-01 y en el FI-03, sin agregar filas nuevas.
- Ninguna salida tiene anotaciones.

## Evaluación 22 · 23/10/2026 · Auditor CATDIC · Reevaluación de T8b (`8a3c61f`)
**Veredicto: APROBADO.**
- `INICIOS_DE_CIERRE = ("TODO SEGUN",)`.
- Encadenado sobre una copia del FI-02 #12 real:
  - Completivo → Parcial: el CONFORME queda junto al Completivo y el Parcial no lleva CONFORME.
  - Completivo → Completivo: queda un CONFORME por cada visita.
  - En los dos casos, "Todo segun" queda al final.
- Siguen vigentes lo de las rayas (enteras) y lo de la fila vacía del bloque "Inspectores".
- **Pruebas:** `566 passed`, más el fallo ajeno de Dropbox.
- **Pendiente con Steven:** en el FI-02, ¿la fecha va en la p4 "Inspectores"?
