# Fundación · contrato mínimo (F0.2–F0.3)

20/11/2026 · Director (Claude Code). Borrador sin commit. No contiene datos reales; los ejemplos son ficticios.

**Revisión 2 (20/11):** incorpora la auditoría de Codex (puntos 1–8) y sus cuatro precisiones (SQLite, CORS, Dropbox e IA). Lo corregido está marcado con «(rev. 2)».

**Revisión 3 (20/11):** cierra las tres precisiones de Codex sobre la rev. 2, marcadas con «(rev. 3)»:
1. confirmar revisiones exige `revisar_autorizar` y desaparece el permiso antiguo `administrar` (§3, §4); bloquea F2;
2. una revisión de plano une y conserva los dos archivos, vectorial y sellado, con su certificación (§2.2); debe estar cerrado antes de F3;
3. la versión elegida como fuente se protege antes de aprobar el pedido, y nunca se sustituye en silencio (§2.3); debe estar cerrado antes de F3.

Es el acuerdo común entre los ejecutores de F2, F3 y F4. Cada entidad dice qué tabla actual reutiliza, para no duplicar identidades ni hacer migraciones destructivas.
- **Las decisiones técnicas rutinarias** son del Director.
- **Las de producto** ya están en `fundacion-inicial.md` §2 y no se reabren.

## 1. Principios
- **Migración:** solo se añaden tablas y columnas, con respaldo automático. Lo que existe conserva sus id: `proyectos.id`, `planos.id`, `visitas.id` y `elementos_diseno.uid`.
- **Auditoría:** las filas históricas con `usuario='steven'` no se reescriben. Las nuevas guardan el `usuario_id` autenticado.
- **Estados separados:** documento, dato, pedido y emisión tienen cada uno su propio estado. «Procesado» nunca significa «correcto» ni «autorizado».
- **Permisos en el servidor:** cada ruta comprueba el permiso sobre la obra, y también las búsquedas, las vistas previas y los archivos. Esconder un botón no cuenta como permiso.
- **Sin dependencias nuevas** mientras la biblioteca estándar alcance. Por ejemplo, las contraseñas se guardan con `hashlib.scrypt`.
- **CORS no es seguridad (rev. 2):** restringirlo al mismo origen evita que otras páginas usen la sesión, pero no sustituye la autenticación ni los permisos. Ambos se comprueban en cada ruta.
- **Las mutaciones son atómicas (rev. 2):** el cambio, su control de versión y su fila de auditoría se escriben en la misma transacción.

## 2. Entidades

| Entidad | Tabla | Reutiliza | Campos clave | Nota |
|---|---|---|---|---|
| Obra | `proyectos` | sí, igual | `id`, `nombre`, cabecera de los informes | La identidad no cambia. `tipo` y `formato_defecto` quedan como servicio principal heredado |
| Servicio de la obra | `obra_servicios` (nueva) | migra 1 fila por proyecto desde `tipo` y `formato_defecto` | `obra_id`, `servicio` (Supervisión / Levantamiento), `formato_defecto`, `activo` | Resuelve H4: una obra puede tener los dos servicios sin duplicarse |
| Usuario | `usuarios` (nueva) | — | `id`, `nombre_visible`, `usuario` (login), `hash_contrasena`, `activo`, `creado_en` | Sin correos ni contraseñas inventados. El alta inicial es local y guiada; ningún secreto va al repo |
| Sesión | `sesiones` (nueva) | — | `token_hash`, `usuario_id`, `creada`, `ultimo_uso`, `expira`, `cerrada`, `motivo_cierre` | Ver §4.1 (rev. 2): obligaciones de la sesión |
| Membresía | `membresias` (nueva) | — | `usuario_id`, `obra_id`, `funciones` (conjunto: `administrar_obra`, `preparar`, `revisar_autorizar`, `consultar`) | Las funciones se combinan. La administración global es otra cosa, `usuarios.es_admin`; ver §4 (rev. 2) |
| Documento | `documentos` (nueva) | — | `id`, `obra_id`, `raiz` (alias configurado), `ruta_relativa`, `tipo`, `procedencia`, `disponibilidad` | La identidad técnica del archivo. No se fusionan dos documentos solo porque coincidan el nombre o el hash |
| Versión de archivo | `documento_versiones` (nueva) | — | `id`, `documento_id`, `sha256`, `bytes`, `mtime`, `visto_en`, `copia_conservada` (ruta en el archivo propio o vacío) | Cada contenido distinto observado. La vigencia nunca se deduce de la fecha. **La huella sola no conserva el documento**: ver §2.1 (rev. 2) |
| Revisión documental | `planos` (planos) / `documento_revisiones` (otros) | `planos`, igual | `revision`, `estado` (`vigente`/`histórico`), `documento_version_id`, confirmada por, fecha | Apunta a **una** versión de archivo concreta (rev. 2). En `planos` son **dos**: `vectorial_version_id` y `sellado_version_id`, más la certificación de correspondencia que ya existe (§2.2, rev. 3). La confirma una persona con `revisar_autorizar`; ni el nombre de la carpeta ni un cambio de tamaño prueban una revisión nueva |
| Visita | `visitas` | sí | Las de hoy | La secuencia y las asociaciones del Report and Run se conservan tal cual |
| Elemento de visita | `elementos_visita` | sí | — | Sin identificar elementos por adivinanza (Regla de Oro, CLAUDE.md §4.4) |
| Dato de diseño | `elementos_diseno` | sí | `estado_campos_json`, `fuente_json`, `revisar_motivo` | **Sin cambiar de forma (rev. 2):** `estado_campos_json` sigue guardando cadenas (`pendiente_de_verificar` o `confirmado`), porque las leen `confirmacion.py`, `extractor.py`, `procesador_cola.py` y sus pruebas. Quién y cuándo confirmó ya se guarda en `fuente_json.valores.<campo>.confirmado` = `{lote, por, en}` (`confirmacion.py:281`). F2 solo cambia `por`, que pasa a ser el `usuario_id` real |
| Pedido (el «trabajo» de la Fundación) | `pedidos` (nueva) | sustituye a D-c | `id`, `obra_id`, `proposito`, `responsable_id`, `estado`, `progreso_json`, `version` | Se llama `pedidos` porque `trabajos` ya es la ejecución del procesador (H5) |
| Fuentes del pedido | `pedido_fuentes` (nueva) | — | `pedido_id`, `documento_version_id` (y la revisión, si la hay), `seleccionado_por`, `seleccionado_en` | Se apunta a una versión concreta, no al archivo «actual» (rev. 2). Si la fuente cambia, se aplica §3 (aplicabilidad) |
| Cobertura del pedido | `pedido_cobertura` (nueva; se usa en la siguiente entrega) | — | `pedido_id`, `documento_version_id`, `unidad` (hoja o elemento), `estado` (`pedido`/`entregado`/`falta`/`duda`); única por `(pedido_id, documento_version_id, unidad)` | Evita que un plano leído en parte parezca completo, y la clave única impide duplicar al reimportar (rev. 2) |
| Ejecución del procesador | `trabajos` y `trabajo_eventos` | sí, igual | — | Se añade `usuario_id` en las filas nuevas |
| Duda | `dudas_y_hallazgos` | sí | Se añaden `origen` (`programa` / `ia` / `persona`), `autor_id` y `pedido_id` | Hoy el origen va como prefijo «IA:» en el texto: se conserva y se pasa a la columna |
| Emisión (se define ahora, se construye después) | `emisiones` + `emision_fuentes` | — | `obra_id`, `pedido_id`, `archivo` (copia conservada), `version`, `estado`, `autorizado_por`, `entregado_en`; en `emision_fuentes`, los `documento_version_id` usados, la plantilla y las reglas | Solo se puede reconstruir porque las versiones usadas tienen copia conservada (§2.1) |
| Auditoría | `auditoria` | sí | Se añade `usuario_id`; `usuario` se mantiene como texto histórico | No se guardan contraseñas, tokens ni contenido sensible |

### 2.1 Conservación de documentos (rev. 2)
- **Qué se copia:** Dropbox puede sustituir o borrar un archivo, y con solo la huella no se recupera el contenido anterior. Por eso se guarda una copia en el **archivo propio de la aplicación** (`<datos>/archivo/<sha256>`, fuera de git y de Dropbox) de cada versión que:
  1. sea una revisión documental confirmada;
  2. esté elegida como fuente de un pedido aprobado;
  3. se haya usado en una emisión.
- **Qué no se copia:** las demás versiones guardan solo la huella; se indexan, pero no se conservan.
- **Cómo se guarda la copia:**
  - se escribe en un archivo temporal y se renombra al terminar;
  - su sha256 se comprueba antes de marcar `copia_conservada`;
  - nunca se sobrescribe ni se borra mientras algo la referencie.
- **Si la copia falla** (disco lleno, archivo inaccesible):
  - la confirmación o aprobación que la exige no se completa;
  - el motivo se muestra.
- **Respaldo:** el archivo propio entra en la prueba de respaldo y restauración (escenario 9). Que Dropbox esté sincronizado no cuenta como respaldo de la aplicación.
- **Espacio:** un plano sellado pesa unos 57 MB. Se copia solo lo que cumple 1–3, no cada versión vista. F3 mide el espacio usado en el ensayo.

### 2.2 Revisión de plano: los dos archivos y su certificación (rev. 3)
- **Qué es una revisión de plano:** una fila de `planos` que une **dos versiones de archivo** y una certificación. Hoy `planos` ya guarda, para cada archivo, nombre, ruta, sha256, bytes y páginas, y además `certificado_por`, `certificado_en` y `certificacion_texto` (quien certifica que el vectorial corresponde al sellado).
- **Qué se añade (solo columnas nuevas):**
  - `vectorial_version_id` y `sellado_version_id`, que apuntan a `documento_versiones`;
  - `certificado_por_id`, el `usuario_id` de quien certifica. `certificado_por` se mantiene como texto histórico.
- **Coherencia obligatoria:** el sha256 de cada versión enlazada debe ser igual al `vectorial_sha256` o `sellado_sha256` de la fila. Si no coincide, la revisión no se confirma y se muestra el motivo.
- **Las filas que ya existen:** la migración las enlaza buscando versiones con ese mismo sha256. Si no encuentra la versión o el sha256 no coincide, el enlace queda vacío y la revisión se marca «pendiente de verificar». No se inventa ni se reescribe la certificación.
- **Conservación:** confirmar una revisión de plano copia **los dos** archivos al archivo propio (§2.1). Si falla cualquiera de las dos copias, la revisión no queda vigente. No existe una revisión con solo uno de los dos archivos.
- **Certificación:** forma parte de la revisión y no se separa de ella. Si cambia cualquiera de los dos archivos, la certificación deja de cubrir la versión nueva: hace falta una revisión nueva o una certificación nueva, siempre de una persona con `revisar_autorizar`.
- **Uso como fuente:** un pedido que usa un plano apunta a la revisión de plano. La lectura asistida usa el vectorial y la emisión cita el sellado, pero siempre los dos de la misma revisión. Nunca se mezcla el vectorial de una revisión con el sellado de otra.

### 2.3 Protección de la versión seleccionada (rev. 3)
- **Cuándo se conserva:** la versión elegida como fuente se copia al archivo propio **en cuanto se usa**, sin esperar a la aprobación:
  - al preparar el pedido (`solicitado` → `preparado`);
  - al exportar información de ella, por ejemplo el paquete de hojas para la IA;
  - como muy tarde, al aprobar el pedido.
  Las ya conservadas por ser revisión confirmada no se copian otra vez.
- **Antes de leerla o exportarla**, el servidor comprueba que el sha256 del archivo sigue siendo el de la versión elegida. Lo lee primero desde la copia conservada; si no hay copia, desde la ruta original.
- **Si ya no está disponible o cambió** (ausente, inaccesible, otro sha256, sin copia conservada):
  - el proceso **se detiene**: no prepara, no exporta y no aprueba;
  - se muestra qué versión falta y por qué;
  - el pedido no pierde nada de lo guardado;
  - la acción y su motivo quedan en la auditoría.
- **Nunca se usa otra versión en silencio.** Cambiar de versión es elegir de nuevo la fuente (`PUT /api/pedidos/{p}/fuentes`, con `version`), un acto de una persona con `preparar` que queda registrado.

## 3. Estados y transiciones

- **Documento (disponibilidad):** `disponible` → `modificado` (sha256 nuevo) · `movido_por_reconciliar` · `ausente` · `inaccesible`. Que un documento esté ausente o inaccesible no lo borra ni cambia su historial.
- **Revisión documental:** `sin_confirmar` → `vigente` → `histórica`. Lo confirma solo una persona con `revisar_autorizar` en esa obra (rev. 3). El permiso antiguo `administrar` desaparece. `administrar_obra` y `es_admin` no conceden aprobación técnica.
- **Dato:** `pendiente de verificar` → `confirmado`. Lo confirma una persona, y siempre se registra quién.
- **Aprobación histórica y aplicabilidad actual son dos cosas (rev. 2):**
  - **La aprobación** es un hecho del pasado y nunca se borra.
  - **La aplicabilidad** es `aplicable` o `reevaluar`.
  - **Qué la cambia:** cuando cambia una fuente de la que depende un dato confirmado, una revisión o un pedido aprobado, la aplicabilidad pasa a `reevaluar` (hoy `revisar_motivo`, que se convierte en ese estado).
  - **Qué bloquea:** mientras algo dependa de una fuente en `reevaluar`, **no se puede autorizar una emisión nueva** que lo use. Los trabajos que no dependen de esa fuente siguen. Lo ya emitido no se toca.
  - **Quién lo resuelve:** una persona con `revisar_autorizar`, de una de dos formas:
    - lo declara aplicable a la versión nueva, y queda registrado;
    - o vuelve a revisarlo.
- **Pedido:** `borrador` → `solicitado` → `preparado` → `en_revision` → `corregir` ↔ `en_revision` → `aprobado`.
  - Se puede guardar con dudas.
  - La emisión queda bloqueada si el informe afectado tiene una duda bloqueante.
- **Emisión:** `borrador` → `autorizada` → `entregada`. Son tres actos distintos, cada uno con su responsable.

## 4. Permisos por operación (se aplican en el servidor)

| Operación | Función mínima en la obra |
|---|---|
| Ver la obra, sus documentos, visitas, búsqueda y vista previa | `consultar` |
| Crear o editar un pedido, elegir sus fuentes, subir una visita, preparar el paquete para la IA | `preparar` |
| Confirmar datos o revisiones, cerrar una duda bloqueante, aprobar un pedido, autorizar una emisión | `revisar_autorizar` |
| Registrar la entrega | `revisar_autorizar` |
| Membresías **de esa obra** | `administrar_obra` |
| Altas y bajas de usuarios, `es_admin`, raíces de Dropbox, configuración global | solo `usuarios.es_admin` (no es una función de obra) |

- **Composición (rev. 2):**
  - `preparar`, `revisar_autorizar` y `administrar_obra` incluyen `consultar` en esa obra.
  - `preparar` y `revisar_autorizar` no se incluyen entre sí.
  - `administrar_obra` no da `preparar` ni `revisar_autorizar`, así que no permite confirmar revisiones, datos ni pedidos (rev. 3).
  - No hay ninguna función llamada `administrar`. Si aparece en datos o código anterior, se rechaza; no se traduce a otra (rev. 3).
  - `es_admin` no da acceso automático a los datos técnicos de una obra: para eso necesita una membresía, y así sus actos técnicos también quedan registrados.
- **Obras ajenas:** un usuario sin membresía recibe **404**, no 403, para no confirmar que la obra existe. Los listados nunca muestran nombres ni vistas previas de obras ajenas.
- **Prueba para Steven:** puede tener a la vez `preparar` y `revisar_autorizar`. Cada acto queda registrado por separado.

### 4.1 Obligaciones de la sesión (rev. 2)
- **Intentos de entrada:** después de 5 fallos seguidos, por usuario y por dirección, se espera cada vez más, empezando en 15 minutos. Cada intento queda en la auditoría, sin la contraseña.
- **Usuario desactivado:**
  - todas sus sesiones se cierran al instante;
  - su próxima petición recibe 401;
  - no puede volver a entrar.
- **Cerrar sesiones:** `DELETE /api/sesion` cierra la propia. Un `es_admin` puede cerrar todas las de un usuario.
- **Caducidad:** 12 h sin uso o 7 días en total; la vigencia se comprueba en el servidor en cada petición.
- **Contraseñas:** se guardan con `scrypt`, con su sal y parámetros, y no se envían nunca de vuelta. El alta inicial la escribe la persona, no se fabrica.
- **Mutaciones:** cookie con SameSite=Strict, comprobación del encabezado `Origin` y un encabezado propio obligatorio en todo `POST`, `PUT`, `PATCH` o `DELETE`. Sin eso, la respuesta es 403.
- **HTTPS:** mientras el servidor escuche solo en `127.0.0.1` no hace falta. **Abrirlo a la red exige HTTPS y la cookie `Secure`**, y esa apertura no la hace F2: es una decisión aparte de Steven (despliegue fuera de alcance).

## 5. API mínima

- **Sesión:** `POST /api/sesion` para entrar, `DELETE /api/sesion` para salir, `GET /api/sesion` para saber quién soy y qué funciones tengo.
- **Obras:** `GET /api/obras`, que devuelve solo las autorizadas. `GET /api/obras/{id}` da el resumen con sus servicios.
- **Documentos:**
  - `GET /api/obras/{id}/documentos?q=&tipo=&desde=` — búsqueda.
  - `GET /api/documentos/{doc}` — detalle, con sus revisiones y versiones.
  - `GET /api/documentos/{doc}/archivo` — el archivo original, con el permiso comprobado y la ruta dentro de una raíz autorizada.
- **Indexación:** `POST /api/obras/{id}/indexar` para lanzarla. `GET /api/obras/{id}/indexacion` da la última, si hay una en curso, los errores y el reintento.
- **Visitas:** las rutas de hoy se mantienen y pasan por el permiso.
- **Pedidos:**
  - `POST /api/obras/{id}/pedidos` crea uno.
  - `GET` y `PATCH /api/pedidos/{p}` lo leen y lo editan. El `PATCH` lleva `version` para detectar ediciones simultáneas y responde **409** si alguien cambió el pedido antes.
  - `PUT /api/pedidos/{p}/fuentes` fija las fuentes **con el mismo control de `version`**: responde 409 si cambió (rev. 2).
  - Toda mutación de un recurso compartido (pedido, sus fuentes, membresías, datos de la obra) lleva `version`. El cambio y su auditoría se guardan en la misma transacción.
- **Mi trabajo:** `GET /api/mi-trabajo` junta los pendientes del usuario desde las tablas existentes, sin copiarlos (es D-a adaptada).
- **Historial:** `GET /api/obras/{id}/historial`, la auditoría filtrada por obra.

Las rutas actuales siguen funcionando hasta que se sustituyan con revisión, y el tablero clásico depende de ellas.

## 6. Lo que la IA (siguiente entrega) usará de esta base

- **El contrato para la IA son cinco piezas (rev. 2); no se reduce a las tres necesidades del Líder A:**
  1. el pedido;
  2. sus fuentes, que apuntan a versiones y revisiones concretas;
  3. la cobertura por unidad;
  4. la importación sin duplicados (la clave única de `elementos_diseno` y la de `pedido_cobertura`, más la idempotencia que ya prueba `importar.py`);
  5. quién confirma.
- **Fuente que lee:** el `pedido` con sus `pedido_fuentes`, que fija la revisión y el sha256.
- **Lo que produce:**
  - propuestas en `elementos_diseno`, siempre como `pendiente de verificar`, con el `lector` (`<proveedor>:<modelo>`) en `fuente_json`;
  - cobertura en `pedido_cobertura`;
  - dudas con `origen='ia'`.
- **Quién actúa:** el usuario autenticado que prepara, importa y confirma. La IA nunca figura como quien confirma.
- **Permiso:** el paquete de hojas para la IA exige `preparar` en la obra y registra qué se exportó.
- **Rutas:** A5 se construye sobre esta API; las rutas de lectura asistida no se crean antes de F2.
- **Respuesta del Líder A (20/11): qué ya usa sin cambios.**
  - En `planos`: la fila vigente, con su `vectorial_sha256`. Sin plano vigente responde 409.
  - En `elementos_diseno`: la clave única, `fuente_json` con `valores.<campo>` y el `lector`, y `plano_id`.
  - En dudas: las `DUDA_BLOQUEANTE` con «IA:» en `campo_afectado`.
  - En `auditoria`: `ASISTIDO/IMPORTAR_PROPUESTA`.
  - Fuera de la base (nunca en git ni en Dropbox): `<datos>/<obra>/lectura-asistida/`.
- **Lo que esta base debe añadir para la IA:**
  - **quién revisó y confirmó cada valor**, no solo quién lo propuso: se reutiliza `fuente_json.valores.<campo>.confirmado = {lote, por, en}` con `por` = `usuario_id`. `estado_campos_json` no cambia de forma (rev. 2);
  - **la `zona` del elemento guardada como recorte de DETALLE** (`recorte_detalle_json`), para que M4 la use;
  - **el usuario real** en lugar del `steven` fijo.
  - La reutilización por revisión de plano (decisión 10) ya se apoya en `plano_id` y el sha256.

## 7. Escenarios de aceptación de la Fundación (pruebas de F2–F5)

1. **Acceso por obra:** el usuario A ve la obra X; el usuario B no la ve ni la abre aunque conozca su id, en la API, en la búsqueda y en los archivos.
2. **Revocación:** al quitarle la membresía a A, su próxima petición recibe 404.
3. **Funciones combinadas:** Steven prepara y autoriza el mismo pedido, y la auditoría muestra dos actos separados.
4. **Migración:** se aplica dos veces sobre una copia y el resultado es el mismo. Las filas e ids anteriores siguen intactos y hay un respaldo previo.
5. **Archivos, en carpeta temporal:** con documentos nuevos, movidos, modificados, ausentes e inaccesibles:
   - reindexar no duplica nada;
   - lo ausente no se borra;
   - lo movido queda «por reconciliar».
6. **Cambio de fuente:** cambia el sha256 de una fuente de un pedido aprobado. El pedido queda marcado para reevaluar y los datos confirmados no cambian.
7. **Edición simultánea:** dos `PATCH`, o dos `PUT` de fuentes, sobre el mismo pedido con la misma `version` dan uno 200 y otro 409. La auditoría registra solo el que entró (rev. 2).
8. **Retomar un pedido:** se reinicia el servidor y el pedido conserva fuentes y progreso.
9. **Respaldo y restauración:** se prueban en un entorno separado.
10. **Regla de Oro, firmas y versionado:** las pruebas existentes siguen en verde.
11. **Concurrencia en SQLite (rev. 2):** se prueba de verdad; no se da por resuelta con un ajuste.
    - **Escrituras a la vez:** varios hilos o procesos escriben al mismo tiempo (pedidos, Mesa de Dudas y procesador en segundo plano). Se mide si aparecen `database is locked` o esperas.
    - **Transacciones largas:** las del procesador no deben dejar sin servicio las lecturas.
    - **Corte a mitad de transacción:** si se interrumpe, la base se recupera sin datos a medias.
    - Hoy `sqlite3.connect()` ya espera 5 s por defecto, y WAL sigue admitiendo **un solo escritor**. Solo con estas mediciones se decide si WAL, el tiempo de espera o una cola de escritura bastan.
12. **Sesiones:** el bloqueo tras intentos fallidos, el cierre al desactivar, la caducidad y el 403 de una mutación sin `Origin` válido o sin el encabezado propio tienen cada uno su prueba.
13. **Fuente en reevaluación:** con una fuente en `reevaluar`, autorizar una emisión que la usa se rechaza. Una que no la usa se permite.
14. **Copia conservada:** se confirma una revisión, se sustituye el archivo en la carpeta temporal y la versión confirmada se sigue pudiendo abrir desde el archivo propio.
15. **Confirmar sin función técnica (rev. 3):** un usuario con solo `administrar_obra`, o un `es_admin` sin membresía, intenta confirmar una revisión. El primero recibe 403 y el segundo 404, y no cambia nada. Una función `administrar` en la base se rechaza.
16. **Plano con los dos archivos (rev. 3):**
    - Se confirma una revisión de plano y quedan conservados el vectorial y el sellado, con la certificación.
    - Si falla la copia de uno de los dos, o un sha256 no coincide, la revisión no queda vigente.
    - Al cambiar el sellado en la carpeta temporal, la certificación no cubre la versión nueva.
17. **Versión protegida (rev. 3):** se elige una versión como fuente y se prepara el pedido, que la conserva. Después se borra o se sustituye el original en la carpeta temporal:
    - exportar y aprobar leen la copia conservada;
    - con una versión sin copia y con el original cambiado, preparar, exportar y aprobar se detienen con su motivo;
    - en ningún caso se usa otra versión.
