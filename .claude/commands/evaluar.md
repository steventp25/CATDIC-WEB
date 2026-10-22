---
description: Rol EVALUADOR. Audita el trabajo de una etapa con el subagente evaluador y, si aprueba, prepara el commit y el Pull Request para la revisión cruzada.
argument-hint: <etapa> [T# opcional]
---

Evalúa el trabajo de la etapa: $ARGUMENTS

## Pasos
1. Lanza el subagente **`evaluador`** indicándole:
   - La etapa (y la tarea, si se indicó) y la ruta `PLANES/etapa-<N>.md`.
   - Que revise el diff actual del repositorio contra los criterios de aceptación del plan y el CLAUDE.md.
2. Guarda su informe tal cual en `PLANES/etapa-<N>-evaluacion.md` (si ya existe, agrega una sección nueva con fecha `DD/MM/AAAA`; no borres evaluaciones previas).
3. Según el veredicto:

### BLOQUEADO
- Muestra a Steven los bloqueantes.
- **No hagas commit.**
- Propón qué ejecutor debe corregir cada bloqueante; con su visto bueno, se corrige con `/ejecutar <N> T#` y se vuelve a `/evaluar <N>`.

### APROBADO
- Muestra a Steven el resumen y las observaciones no bloqueantes.
- Propón un commit **atómico por tarea** (o por submódulo) con mensajes en español con este formato:
  ```
  Etapa N · T#: <qué hace>

  - <cambio principal>
  - Criterios cumplidos: ...
  - Evaluación interna: APROBADO (PLANES/etapa-N-evaluacion.md)
  ```
- Verifica antes de cada `git add` que no entran `catdic_local.db`, PDFs, fotos ni `.env`.
- **Pide confirmación a Steven antes de hacer el commit**, y otra vez antes del `git push`.
- Después del push, dale a Steven el enlace del Pull Request para la revisión cruzada (ver `COLABORACION.md`).
- Marca las tareas en el plan como `- Estado: APROBADA · commit <hash corto>`.
