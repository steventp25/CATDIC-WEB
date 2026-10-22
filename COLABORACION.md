# COLABORACION.md — Cómo trabajan juntos Claude Code y Codex en CATDIC-WEB

> Para Codex (y para Claude Code). Lo escribió Claude Code el 22/10/2026 a pedido de Steven. Steven es el dueño del proyecto y el único que decide.

## 1. La idea
Steven construye **CATDIC-WEB**, una aplicación local (FastAPI + SQLite + Vue) que genera los informes de supervisión y de levantamiento estructural de CATDIC y sustituye al viejo FileMaker. Hasta ahora:
- Claude Code desarrollaba;
- **Gemini** auditaba cada etapa en GitHub.

Desde hoy **Gemini sale del flujo** y entra **Codex como co-desarrollador**. Los dos agentes escriben código en el mismo repositorio y **cada uno revisa el trabajo del otro** antes de que llegue a `main`. Esa revisión cruzada reemplaza la auditoría externa de Gemini.

Los agentes no se hablan directamente. **El canal es GitHub**:
- **ramas**: cada agente trabaja en la suya;
- **Pull Requests**: el trabajo se entrega y se revisa ahí;
- **comentarios en el PR**: las observaciones y las respuestas;
- **archivos de `PLANES/`**: qué hay que hacer, quién lo hace y qué se decidió.

Repositorio: `https://github.com/steventp25/CATDIC-WEB`

## 2. Fuente de verdad
- **Especificación:** `CLAUDE.md`, y su copia para Codex, `AGENTS.md`. Las reglas de ingeniería (§4), las rutas y nombres de salida (§5) y los 18 errores (§6) son las mismas para los dos.
  - Si `CLAUDE.md` y `AGENTS.md` difieren en alguna regla, se avisa a Steven y no se elige una por cuenta propia.
- **Regla de Oro #1:** nunca inventar, estimar ni rellenar datos de ingeniería, dimensiones, ejes, aceros ni fechas. Lo que falte queda `"pendiente de verificar"` y va a `"Con dudas"` (`DUDA_BLOQUEANTE` en `dudas_y_hallazgos`).
- **Decisiones de Steven:** están en las secciones "Respuestas de Steven" de cada `PLANES/etapa-N.md` y mandan sobre cualquier tabla anterior. Ejemplos:
  - la platea va a 0.075 m;
  - la regla P3 es estricta;
  - todo se corre con `py -3.14`.

## 3. Estado al 22/10/2026
| Etapa | Estado | Dónde |
|---|---|---|
| 0 · Motor de reglas (`reglas_ingenieria.py`) | Cerrada y en `main` | `PLANES/etapa-0*.md` |
| 1 · Sincronizador de Dropbox + visitas | Cerrada y en `main` (`fdc9f44`); sin la auditoría de Gemini | `PLANES/etapa-1*.md` |
| 2 · Importador de datos de diseño | Plan **APROBADO**; esperando que Steven traiga los documentos fuente | `PLANES/etapa-2.md` |
| 3 · Fábrica de Supervisión (STP-MIVED, FI, CATDIC-STP) | Sin planificar | CLAUDE.md §7 |
| 4 · Fábrica de Levantamiento (HV) | Sin planificar | CLAUDE.md §7 |

Números de hoy:
- **482 pruebas** en verde (`cd BACKEND && py -3.14 -m pytest -q`);
- la BD real tiene 22 visitas de Terra Living: 12 Con dudas, 6 Procesada y 4 Sin procesar.

## 4. Reglas de convivencia (para no pisarnos)
1. **Nadie hace push directo a `main`.** Cada uno trabaja en su rama y abre un PR:
   - Claude Code: `claude/<etapa>-<tarea>`;
   - Codex: `codex/<etapa>-<tarea>`.
2. **Reparto por tarea, no por ganas.** En `PLANES/etapa-N.md` cada tarea dice quién la hace (`Agente: Claude Code | Codex`). Steven asigna; si no asignó, se pregunta antes de empezar.
3. **Un archivo, un dueño a la vez.** Si una tarea toca un archivo que está en un PR abierto del otro, se espera a que ese PR se fusione, o se pide a Steven que decida.
4. **Antes de empezar:** `git fetch` y partir del `main` actualizado.
5. **El PR lleva:**
   - la etapa y la tarea;
   - los criterios de aceptación del plan, marcados;
   - la salida real de `py -3.14 -m pytest -q`;
   - los datos que quedaron `"pendiente de verificar"`.
6. **Revisión cruzada:** el otro agente revisa el PR contra el plan, la Regla de Oro, §4–§6 y las pruebas. Deja un comentario con veredicto **APROBADO** o **BLOQUEADO**, y con los bloqueantes en formato `archivo:línea`.
   - Cada agente revisa con el formato de su evaluador interno: `.claude/agents/evaluador.md` para Claude Code y `.codex/agents/evaluador.toml` para Codex.
   - **Steven fusiona.**
7. **Nunca se commitean** `*.db` (incluidos los respaldos `catdic_local.backup-*.db`), PDFs, fotos, `.env` ni secretos.
8. **Dropbox:**
   - solo lectura, salvo `INFORMES\2.DATA PROCESADA\` y `FORMULARIOS\MIVED\FORMULARIOS NO FIRMADOS\`, y siempre con versión ` v2`/` v3`;
   - nunca se sobrescribe ni se borra nada.
9. **BD real** (`BACKEND/catdic_local.db`):
   - antes de cambiarla, se hace una copia de respaldo;
   - las pruebas usan `CATDIC_DB_PATH` con una BD temporal.
10. **Comunicación con Steven en español.** Lo que decida Steven se escribe en el plan, no solo en el chat.

## 5. Cómo arranca Codex
1. Leer `AGENTS.md` (especificación), este archivo y `PLANES/README.md` (ciclo planificar → ejecutar → evaluar).
2. Leer `PLANES/etapa-1-evaluacion.md`. Ahí están los pendientes abiertos y el contrato para la Etapa 3:
   - el generador debe escribir `origen_datos_json.estado`;
   - la Mesa de Dudas debe actualizar el origen de lo que responda Steven.
3. Correr las pruebas: `cd BACKEND && py -3.14 -m pytest -q`. `python` a secas abre Python 3.15, que no tiene las dependencias.
4. Primer trabajo propuesto: hacer la **revisión cruzada de la Etapa 1**, que quedó sin auditoría externa. Comparar `61e6ecb...fdc9f44` y dejar el veredicto en un issue o en `PLANES/etapa-1-evaluacion.md`, mediante un PR.

## 6. Pendiente de definir con Steven
- Qué etapas o tareas toma cada agente. Propuesta inicial: cada etapa la desarrolla un agente y la revisa el otro, para que no haya dos personas en los mismos archivos.
- Si activa la protección de rama en GitHub (exigir un PR para `main`) y el conector de Codex con el repositorio.
- Si `AGENTS.md` sigue siendo una copia completa del `CLAUDE.md` o pasa a apuntar a él, para que no se desincronicen.
