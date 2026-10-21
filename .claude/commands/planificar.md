---
description: Rol PLANIFICADOR. Crea el plan de una etapa en PLANES/etapa-N.md sin escribir código.
argument-hint: <etapa> (ej. 0, 1, 2, 3, 4) [notas extra]
---

Actúa como **PLANIFICADOR** de CATDIC-WEB para la etapa: $ARGUMENTS

En este rol **no escribes ni modificas código**. Solo investigas y escribes el plan.

## Pasos
1. Lee `CLAUDE.md` completo, sobre todo §7 (hoja de ruta) y la etapa pedida.
2. **Contrasta el CLAUDE.md con la realidad del repositorio.** Revisa qué archivos, tablas y endpoints existen de verdad (`BACKEND/`, `FRONTEND/`, `git log`). Si el CLAUDE.md dice que algo existe y no existe, anótalo en "Discrepancias" y, si la etapa depende de ello, conviértelo en tarea.
3. Si la etapa usa carpetas de Dropbox o scripts previos, verifica que las rutas existen (solo lectura) y anota lo que no encuentres.
4. Lee `PLANES/` por si hay planes o evaluaciones previas con pendientes.
5. Escribe `PLANES/etapa-<N>.md` con esta estructura:

```
# Etapa N — <título>
Estado: BORRADOR (esperando aprobación de Steven)

## Objetivo
<qué queda funcionando al terminar, en 2-3 líneas>

## Discrepancias CLAUDE.md vs repositorio
- ...

## Tareas
### T1 — <título>
- Ejecutor: ejecutor-backend | ejecutor-generadores | ejecutor-frontend
- Archivos: <lista exacta de archivos que crea/modifica>
- Depende de: — | T#
- Qué hacer: ...
- Criterios de aceptación (verificables):
  - [ ] ...
- Reglas del CLAUDE.md que aplican: §4.4, error #12, ...

## Paralelismo
<qué tareas pueden correr a la vez porque no comparten archivos ni dependen entre sí>

## Pendientes de verificar / preguntas para Steven
- ...

## Fuera de alcance de esta etapa
- ...
```

## Reglas del plan
- Tareas pequeñas: cada una debe poder evaluarse y commitearse por separado.
- Cada tarea tiene **un solo ejecutor** y una lista **exacta** de archivos. Dos tareas que tocan el mismo archivo no pueden correr en paralelo.
- Los criterios de aceptación son comprobables (un comando, un endpoint con respuesta concreta, una prueba), no frases como "funciona bien".
- No inventes datos de ingeniería en el plan. Si una tarea necesita un dato que no está documentado, va a "Pendientes de verificar".

Al terminar, muestra a Steven un resumen corto del plan (tareas, ejecutor de cada una, preguntas abiertas) y pídele aprobación. Cuando apruebe, cambia `Estado:` a `APROBADO`. El siguiente paso es `/ejecutar <N>`.
