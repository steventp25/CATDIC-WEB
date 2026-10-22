# PLANES — Flujo de trabajo por roles

Esta carpeta guarda los planes y evaluaciones de cada etapa. Es el registro que comparten el planificador, los ejecutores, el evaluador interno y la revisión cruzada entre Claude Code y Codex (ver `../COLABORACION.md`).

## Ciclo por etapa

| Paso | Comando | Rol | Resultado |
|---|---|---|---|
| 1 | `/planificar <N>` | Planificador | `PLANES/etapa-N.md` en estado BORRADOR |
| 2 | Steven revisa y aprueba | Steven | Estado → APROBADO |
| 3 | `/ejecutar <N>` | Ejecutores (`ejecutor-backend`, `ejecutor-generadores`, `ejecutor-frontend`) | Código hecho, sin commit |
| 4 | `/evaluar <N>` | Evaluador interno (solo lectura) | `PLANES/etapa-N-evaluacion.md` con APROBADO / BLOQUEADO |
| 5 | Si APROBADO: commit + push (con confirmación de Steven) | — | Commit en GitHub |
| 6 | Se abre un Pull Request y el otro agente (Codex o Claude Code) lo revisa | Revisión cruzada | Steven fusiona y da el visto bueno para la siguiente etapa |

Si el evaluador BLOQUEA, se corrige con `/ejecutar <N> T#` y se vuelve a `/evaluar <N>`.

## Áreas de cada ejecutor

- **ejecutor-backend:** `BACKEND/` excepto `BACKEND/generators/` (API, BD, sincronizador Dropbox, importadores, `reglas_ingenieria.py`).
- **ejecutor-generadores:** `BACKEND/generators/` (los 7 formatos de documentos).
- **ejecutor-frontend:** `FRONTEND/`.

Las definiciones están en `.claude/agents/` y los comandos en `.claude/commands/`.

## Etapas
- **Etapa 0:** Motor de reglas `BACKEND/reglas_ingenieria.py` (el archivo existe: llegó sin trackear y se commiteó tal cual en `d8e332c` como base); la etapa consiste en auditarlo, probarlo con pytest y corregirlo. Plan: [etapa-0.md](etapa-0.md).
- **Etapa 1–4:** según CLAUDE.md §7.
