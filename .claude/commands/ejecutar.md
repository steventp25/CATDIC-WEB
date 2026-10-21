---
description: Rol COORDINADOR DE EJECUCIÓN. Reparte las tareas de un plan aprobado entre los subagentes ejecutores.
argument-hint: <etapa> [T# opcional para ejecutar solo una tarea]
---

Ejecuta el plan de la etapa: $ARGUMENTS

## Pasos
1. Lee `PLANES/etapa-<N>.md`. Si su `Estado:` no es `APROBADO`, **detente** y pide a Steven que lo apruebe primero (o que corra `/planificar <N>`).
2. Si se indicó una tarea (`T#`), ejecuta solo esa. Si no, todas las pendientes en orden de dependencias.
3. Para cada tarea, lanza el subagente indicado en su campo `Ejecutor:` (`ejecutor-backend`, `ejecutor-generadores` o `ejecutor-frontend`) con un mensaje que incluya:
   - El texto completo de la tarea (qué hacer, archivos, criterios de aceptación, reglas que aplican).
   - Lo que ya hicieron las tareas de las que depende.
   - El recordatorio de que no hace commits.
4. **Paralelismo:** lanza a la vez solo las tareas que el plan marca como paralelas **y** que no comparten ningún archivo. Si hay duda, en serie.
5. Cuando un ejecutor termine, revisa su reporte:
   - Si dice que necesita algo fuera de su área o que algo contradice el plan, **detente** y explícaselo a Steven; no improvises la solución.
   - Si reporta datos `"pendiente de verificar"`, anótalos en el plan en "Pendientes de verificar".
6. Marca en `PLANES/etapa-<N>.md` cada tarea terminada (`- Estado: HECHA (sin evaluar)`).

## Lo que no haces en este rol
- No escribes el código tú mismo: lo hacen los ejecutores.
- No haces commits ni push.
- No cambias el alcance del plan. Si hace falta, se vuelve a `/planificar`.

Al terminar, muestra a Steven un resumen corto: tareas hechas, archivos tocados, pendientes que salieron. El siguiente paso es `/evaluar <N>`.
