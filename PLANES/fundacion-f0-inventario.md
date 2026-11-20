# Fundación · F0 — inventario y reconciliación

20/11/2026 · Director (Claude Code).

Steven aprobó el 20/11 empezar F0 con estos ajustes:
1. La Fundación dirige el trabajo inicial.
2. La Etapa 5 se reconcilia tarea por tarea.
3. A y B quedan pausadas.
4. La IA operativa pasa a la siguiente entrega, pero F0 revisa ahora qué necesita de la base.
5. Se conserva el tablero clásico; su eliminación no está autorizada.
6. No se toca código funcional, Dropbox ni la base real.

Este archivo está escrito en el checkout principal y **todavía no tiene commit**. Plan maestro: `PLANES/fundacion-inicial.md`, en la rama `codex/alcance-catdic-web-2026-11-19` (PR 33). Contrato mínimo: `PLANES/fundacion-contrato.md`.

## 1. Ramas y estado de git (20/11)

| Rama | Commits sobre `main` | Qué contiene | Push |
|---|---|---|---|
| `main` (`b5f7d26`) | — | Etapas 1–3 fusionadas (hasta T10a) | — |
| `claude/etapa5-plan` (`e20c7e5`, PR 31) | 5 | Plan de la Etapa 5 v4, más un ajuste local sin commit (D21 y el lote de P3) | sí, sin el ajuste |
| `claude/etapa5-fase-a-3da668` (`32cd8e1`) | 32 | `BACKEND/plano/asistido/` (esquema, preparar, importar, paquete), skill `extraer-plano`, 5 archivos de pruebas `test_asistido_*`, contrato y reconocimiento | no |
| `claude/etapa5-fase-b-0020e1` (`e371f59`) | 36 | Tablero nuevo en módulos (`FRONTEND/js/…`), Vue local en `vendor/`, maquetas B1, `DESIGN.md`, inventario de UI B0, clásico en `/clasico/` sin enlaces, B3a | no |
| `codex/alcance-catdic-web-2026-11-19` (`1540fd7`, PR 33) | 2 | Alcance, auditoría y Fundación inicial. `5ff4e2d` también añade 2 líneas a `CLAUDE.md` y 2 a `AGENTS.md` (rev. 2: antes decía «solo `PLANES/`») | sí |

- **Choques entre ramas:** las ramas A y B no tocan los mismos archivos de código.
  - Comparten `PLANES/etapa-2*.md`, `etapa-3*.md`, `etapa-5.md` y `referencia/`, que vienen de la rama del plan.
  - La rama de Codex toca `PLANES/`, `CLAUDE.md` y `AGENTS.md`. Se tienen en cuenta al reconciliar la especificación (T0.3).
- **Archivos sueltos en el checkout principal, sin commit:** `.agents/`, `.claude/launch.json`, `.claude/skills/`, `PLANES/alcance-gpr.md`, `PLANES/mapa-proyectos.md`, `PLANES/referencia/` y una copia local de `PLANES/etapa-5.md`.

## 2. Qué hay en `main`

**Backend (FastAPI + SQLite):**
- **Arranque y tablero general:** `main.py` sirve `/api/dashboard` (global), `PATCH /api/proyectos/{id}`, `/api/dropbox/sync`, el procesador de la cola (`/api/visitas/procesar-cola`, `/api/visitas/{id}/procesar`) y los trabajos del procesador (`/api/trabajos/{id}` y sus `/eventos`).
- **Obras:** `obras.py` crea obras, sube y lista los planos (vectorial + sellado, con revisión y sha256) y guarda los datos de la obra (`obra_datos_usuario`).
- **Visor:** `visor.py` ofrece índice, hojas en PNG, elementos, propuesta, recuadro y vista previa.
- **Visitas y Dropbox:**
  - `visitas_obra.py` sube una visita o la trae de Dropbox;
  - `sync/` contiene el escáner de Dropbox, el lector y el parser de visitas (Report and Run) y el sincronizador.
- **Mesa de Dudas:** `mesa_dudas.py` (`GET /api/dudas`, `PATCH /api/dudas/{id}`).
- **Lectura de planos por posición:** `plano/` (`lector_plano`, `extractor`, `confirmacion`), con las tablas `tablas_extraidas` y `certificaciones_tabla`.
- **Generadores:** `generators/` hace STP-MIVED y FI MIVED, con los módulos comunes de detalle, fotos, localización y salida (`v2`/`v3`).
- **Reglas:** `reglas_ingenieria.py` (recubrimientos, EJES, cuantías, auditor preliminar).
- **Tablas:** `proyectos`, `elementos_diseno`, `visitas`, `elementos_visita`, `dudas_y_hallazgos`, `ordenes_trabajo`, `auditoria`, `planos`, `obra_datos_usuario`, `tablas_extraidas`, `certificaciones_tabla`, `trabajos` y `trabajo_eventos`.
- **Migraciones:** idempotentes, con respaldo automático `catdic_local.backup-AAAAMMDD-HHMMSS.db`, que nunca pisa uno existente.
- **Pruebas:** 21 archivos en `main`; 26 en la rama A.

**Frontend:** `FRONTEND/index.html`, un solo archivo con Vue 3 desde CDN, Tailwind CDN y Font Awesome CDN («Control Taller 2.0»).

## 3. Hallazgos para la Fundación (comprobados en el código)

| # | Hallazgo | Dónde | Efecto en la Fundación |
|---|---|---|---|
| H1 | La auditoría registra siempre al usuario fijo `steven` | `database.py:47`, columna `auditoria.usuario` con valor por defecto `'steven'` | F2.4: las acciones nuevas deben registrar al usuario autenticado; las filas viejas se conservan |
| H2 | CORS `allow_origins=["*"]` con `allow_credentials=True` | `main.py:29` | F2.4: con sesiones, restringir al mismo origen. **Esto no sustituye** la autenticación ni los permisos (rev. 2) |
| H3 | Sin autenticación ni permisos; `/api/dashboard` devuelve todas las obras; las rutas reciben `proyecto_id` sin comprobar acceso | todas las rutas | F2.2: hace falta una dependencia común «usuario + permiso sobre la obra» en cada router |
| H4 | `proyectos.tipo` admite Supervisión **o** Levantamiento, nunca ambos | `CHECK` en `proyectos` | F2.3: los servicios de una obra van aparte, sin duplicar la obra |
| H5 | El nombre `trabajos` ya está ocupado por las ejecuciones del procesador de la cola | tablas `trabajos` y `trabajo_eventos` | El «trabajo» de la Fundación (pedido con propósito y fuentes) se llama `pedidos`, para no mezclar los dos conceptos (ver contrato) |
| H6 | SQLite sin WAL ni `busy_timeout` explícitos; una conexión por llamada | `get_connection()` | **(rev. 2, corrige un diagnóstico exagerado):** `sqlite3.connect()` ya espera 5 s por defecto. WAL mejora las lecturas junto a una escritura, pero sigue habiendo **un solo escritor**. No se sabe aún si habrá bloqueos con varios usuarios: F2 lo mide (contrato, escenario 11) antes de decidir. No hay motivo para cambiar de base |
| H7 | Archivos servidos por ruta absoluta guardada en la base (`vectorial_ruta`) | `visor.py` | F2.2/F3: comprobar el permiso de la obra antes de servirlos, y que la ruta esté dentro de una raíz autorizada |
| H8 | El frontend de `main` depende de 3 CDN | `FRONTEND/index.html:7-9` | Sin modo offline completo. B2 ya lo resuelve para el tablero nuevo (Vue local); el clásico sigue con CDN |
| H9 | `planos` ya es una «revisión documental» con su par vectorial/sellado, sha256, certificación del usuario e historial vigente/histórico | `planos` | F3.2: se reutiliza como el caso «plano» de la revisión de documento; no se rehace |
| H10 | `elementos_diseno` ya guarda la fuente con sha256, los pendientes y el aviso «plano cambiado: revisar» | columnas `fuente_json`, `pendientes_json`, `plano_id`, `revisar_motivo` | Es la señal de reevaluación que pide la Fundación para el caso plano; se generaliza a otras fuentes |
| H11 | `ordenes_trabajo` y el campo `tipo` repiten el servicio de forma excluyente | `ordenes_trabajo` | Encaja como «servicio» de la obra; no se migra en F0 |

## 4. Suite base (base temporal, 20/11)

Ejecutada con `CATDIC_DB_PATH` apuntando a una base temporal en el scratch. La base real no se tocó.

- **Comando**, en `BACKEND/` de cada checkout: `CATDIC_DB_PATH=<scratch>/f0/test-<rama>.db python -m pytest -q -p no:cacheprovider`, con Python 3.14.
- **Resultados**, fuera del repo: `C:\WINDOWS\TEMP\claude\2057be99c537ee72\f427adf6-e60b-4f06-852d-dc8700f989b9\scratchpad\f0\suite-{main,fase-a,fase-b}.txt`.
- **Commits distintos de la §1 (rev. 2):** las pruebas corrieron después de que los líderes anotaran la pausa. A pasó de `32cd8e1` a `1efae5e` y B de `e371f59` a `5a41a97`; esos commits nuevos solo tocan `PLANES/`, así que el código probado es el mismo que en la §1.

| Código | Pasan | Fallan | Omitidas |
|---|---|---|---|
| `main` (`b5f7d26`) | 943 | 2 | 3 |
| Rama A (`1efae5e`) | 1081 | 2 | 3 |
| Rama B (`5a41a97`) | 944 | 2 | 3 |

Los 2 fallos son los mismos en las tres ramas y son **dos fallos distintos** (rev. 2): uno por el tamaño del plano y otro por las carpetas de visitas. Los dos dependen del contenido real de Dropbox. Se registran, no se arreglan:
- **`test_escaner_dropbox.py::test_terra_living_real`:**
  - la prueba espera que `TERRA LIVING -ESTRUCTURALES.pdf` pese 57 692 938 bytes;
  - en Dropbox ahora pesa 57 692 301;
  - **el archivo de planos sellados de Terra Living cambió de tamaño.** Eso **no demuestra** una revisión nueva (rev. 2): puede ser otra exportación del mismo plano. Queda «pendiente de verificar» con Steven. Es justo el caso que F3 debe señalar sin declarar nada.
- **`test_parser_visitas.py::test_lista_coincide_con_dropbox_si_esta_disponible`:** la lista de visitas de la prueba ya no coincide con las carpetas de Dropbox. La diferencia está en la visita «COLUMNAS S-5 PARCIALES Y PORTICOS».

## 5. Reconciliación de la Etapa 5, tarea por tarea

Estados: **completada** (hecha y auditada, se conserva), **reutilizable** (hecha; entra en una fase de la Fundación), **adaptar** (sirve, pero cambia de forma), **pausada** (sigue válida y espera su entrega), **sustituida** (la cubre una tarea de la Fundación), **sin autorizar**.

| Tarea Etapa 5 | Estado | Destino en la Fundación | Dependencia o nota |
|---|---|---|---|
| T0.1 git al día + respaldo | completada | — | Respaldo en `CATDIC-RESPALDOS\etapa5-2026-11-16` |
| T0.3 ajuste de la especificación (regla MIVED, D19) | pausada | Siguiente entrega (informes) | D17 resuelta; D19 abierta: no se aplica ninguna regla sin el sí de Steven |
| T0.4 FI MIVED «solo al completar» | pausada | Siguiente entrega | Toca generadores; fuera de la Fundación |
| T0.5 tabla de las Etapas 2–4 | sustituida | F0.1 (este archivo, §2 y §3) | — |
| P1 índice del caso Zoetry H2 | completada | Siguiente entrega (§6 de la Fundación) | Índice en las notas compartidas, fuera de git |
| P2 recorrido en 1 página (H2) | pausada | Siguiente entrega | Faltan los chats de la otra cuenta |
| P3 intercambio medido (Terra Living, D21) | pausada | Siguiente entrega | Requiere registrar el plano vigente y respaldar la base |
| P4 visitas difíciles #17, #18, #20 | pausada | Siguiente entrega | Solo medición |
| A1 reconocimiento | completada | Insumo de la siguiente entrega | Resultados en el scratch del Líder A, fuera de la base |
| A2 preparar hojas | reutilizable | Siguiente entrega; necesita `documento_revision` (contrato §2) | `plano/asistido/preparar.py` |
| A3a–A3d importar con anclaje, reglas de conversión | reutilizable | Siguiente entrega; necesita `pedido`, usuario autenticado y permiso «preparar» | `plano/asistido/importar.py`, `esquema.py` |
| A4a skill de columnas | reutilizable | Siguiente entrega | `.claude/skills/extraer-plano/` |
| A4-paquete (`python -m plano.asistido.paquete`) | reutilizable | Siguiente entrega | Prueba a ciegas pendiente (tarjeta de Steven). El paquete saca hojas del plano: con la Fundación pasa por el permiso de la obra |
| A4b–A4d (muros, pórticos, fundaciones) | pausada | Siguiente entrega | — |
| A5 rutas de la lectura asistida | pausada | Siguiente entrega; se construye sobre el contrato de F2 (usuario y permisos) | Toca `main.py`: se coordina con F2 |
| A6 prueba real por lotes | pausada | Siguiente entrega | D13 |
| B0 inventario de UI y paridad | reutilizable | F1 (insumo) y retiro futuro del clásico (lista de paridad) | `PLANES/etapa-5-inventario-ui.md` |
| B1 maquetas + estilo «Plano sellado» | reutilizable | F1: el estilo es **una opción**, no una elección; F1 evalúa qué sirve | `FRONTEND/maquetas/`, `DESIGN.md` |
| B2 base: Vue local, rutas por hash, temas, componentes | reutilizable | F1/F4: base técnica (resuelve H8 en lo nuevo) | La navegación de B2 (Inicio, Mis obras, Bandeja, Informes) se corrige en F1 |
| B3a Inicio + Mis obras | adaptar | F1/F4: «Mis obras» encaja en Obras. Las prioridades de Inicio pasan a «Mi trabajo» (decisión de producto ya contestada) | Rama B, commits `30bea9a`, `6f6d73a`, `77afd26` |
| Quitar del tablero nuevo los enlaces al clásico (`ddca35f`) | completada | — | Conserva `FRONTEND/clasico/`, su ruta y su prueba |
| B3b–B3g resto de pantallas | pausada | F1 decide la estructura, F4 implementa | — |
| B3h retiro del clásico | **sin autorizar** | — | Requiere equivalencia funcional, que nada dependa de él y aprobación de Steven |
| B4 movimiento, B5 paridad y rotura | pausada | F4.4 / F5.1 | — |
| C1–C2 integración de la lectura asistida | pausada | Siguiente entrega | Depende de A5 |
| D-a bandeja común | adaptar | F4: «Mi trabajo». Necesita usuario (F2) para saber «mío» | Solo lee registros existentes |
| D-b indicadores | pausada | — | D15 abierta; la Fundación no pide indicadores |
| D-c trabajos independientes | sustituida | F2.3 + F4.2 (`pedidos` con propósito y fuentes) | — |
| Ajuste local del plan (D21, lote de P3) | pausada | — | Escrito en `claude/etapa5-plan`, sin commit |

Las decisiones D1–D21 se conservan.
- **D6 (organización):** la sustituye en parte la navegación decidida por Steven en la Fundación §2 (Obras → Resumen, Documentos y planos, Visitas y elementos, Informes, Historial; «Mi trabajo»).
- **D7 (congelar `main.py` y `FRONTEND/`):** sigue valiendo, ahora entre F2, F3 y F4.

## 6. Qué necesita la IA (siguiente entrega) de la Fundación

Ver el contrato, §6. En resumen:
- **Revisión de documento con sha256:** el plano ya la tiene en `planos`.
- **Un `pedido` con cobertura:** qué hojas o elementos se pidieron, cuáles se entregaron y qué faltó. Así un plano leído en parte no parece completo.
- **El usuario autenticado,** registrado como quien prepara, quien importa y quien confirma.
- **El permiso de la obra** antes de sacar hojas en el paquete que va a la IA.
- **Las dudas con su origen** (`IA:` hoy va en el texto) y el `lector` (`<proveedor>:<modelo>`) guardado aparte del usuario.

## 7. Siguiente trabajo concreto

Se propone a Steven al cerrar F0:
1. **F1 · prototipo del recorrido** (directo, Director):
   - sobre la base técnica B2, con datos ficticios rotulados;
   - navegación de la Fundación §2 y los estados de F1.2;
   - «Plano sellado» como opción de partida y, si aporta algo, una variante;
   - se presenta en el panel del navegador.
2. **F2 en paralelo** (líder de backend). Es todo F2.1–F2.4 contra el contrato rev. 2, no solo entrada, CORS y SQLite. Incluye pruebas de:
   - acceso directo a la API y a los archivos;
   - revocación;
   - concurrencia;
   - migraciones conservadoras;
   - conflictos de edición.
   - propuesta de autenticación local sin dependencias nuevas;
   - permisos por obra y acción en una dependencia común de FastAPI;
   - WAL y `busy_timeout`;
   - CORS al mismo origen.
   - Todo sobre una copia de la base.
3. **Después de F1 y F2:** F3 (documentos e índice de Dropbox, solo lectura).
