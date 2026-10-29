# TRASPASO A CODEX — 24/10/2026

Lo escribió el Planificador de Claude Code. Steven: "quiero que codex lo haga que ya no tenemos tokens hasta el martes. todo lo que se vaya a hacer".

**Reglas:** COLABORACION.md · Regla de Oro (CLAUDE.md/AGENTS.md) · ramas `codex/...` · nadie hace push a main; Steven fusiona · `py -3.14` · revisión con `.codex/agents/evaluador.toml`.

- **Ramas de Claude subidas** (PR por abrir o fusionar; orden):
  - **Etapa 2:**
    - PR #3 (T2 validador) y PR #4 (T1 esquema);
    - `claude/etapa2-planes` (PR #5);
    - `claude/etapa2-t3n-reconocimiento-plano`;
    - `claude/etapa2-t6na-lector-plano`.
  - **Etapa 3:**
    - sin dependencias entre sí: T1 `etapa3-t1-dependencias`, T2 `etapa3-t2-reconocimiento`, T6 `etapa3-t6-comunes`, T0b `etapa3-t0b-inventario` y T12 `etapa3-t12-pruebas-dropbox`;
    - T7a `etapa3-t7a-proyecto`, después del PR #4;
    - T4 → T4b → T5 → T5b (`etapa3-t4-mesa-dudas`, `-t4b-correcciones`, `-t5-mesa-ui`, `-t5b-mesa-rotulos`);
    - T3 `etapa3-t3-lector-visita`;
    - T7 → T7b (`-t7-stp-mived`, `-t7b-stp-dos-visitas`), después de T6;
    - T8 → T8b (`-t8-fi-mived`, `-t8b-fi-ajustes`), después de T6.
  - Los cuerpos de los PR están en la carpeta de notas de Claude.
- **Rama local SIN subir y SIN auditar:** `claude/etapa2-t6nb-lector-plano` (`a8de848`): mejoras al lector (notas AJUSTAD/CORRECCION/CAMBIO DE, globos con línea de eje, tipo planta). Codex la revisa con su evaluador y, si la aprueba, Steven la sube.
- **Pendiente, en orden:**
  1. Revisar T6n-b.
  2. T6n-c: el lector contra el vectorial de P16 (`PLANOS ESTRUCTURALES P16 PDF 26-09-2024 SIN SELLOS.pdf`), en solo lectura y con un informe. Hay que ubicar la Losa E-9.
  3. Después de las fusiones: T4n (Nueva obra: vectorial + sellado + certificación + datos del proyecto + equivalencias E-n↔nivel y L#→tipo).
  4. T4v (visitas: subir PDF o conectar Dropbox).
  5. T5n (visor y recuadros).
  6. T6n y T7n (extracción y confirmación por lote).
  7. T8n (P16).
  8. T10 de la Etapa 3 (Procesar Cola).
  9. Más adelante: usuarios y roles (admin y procesador de datos), sin depender de internet (Vue y Tailwind locales), campos manuales (inicio de obra, número de formulario y fecha del informe), CATDIC-STP (aplazado), y OCR o proceso en el chat para los planos sin vectorial.
- **Preguntas abiertas para Steven:**
  - qué hojas reemplazan los resellados de P16;
  - en el FI-02, si la fecha va en la p4 "Inspectores";
  - si el nombre de STP de dos visitas usa el texto de la última;
  - el uso de la fila vacía del bloque de firmas (confirmar).
- **Evaluaciones:** `PLANES/etapa-2-evaluacion.md` y `PLANES/etapa-3-evaluacion.md`.
- **Aviso:** los cambios de `PLANES/` en el checkout principal no están commiteados. Codex debe commitearlos en una rama `codex/planes-traspaso` antes de empezar.


Carpeta de notas de Claude (cuerpos de PR): C:\Users\Steve\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\side-session-notes\local_f4445ee8-5382-4f9e-9e90-73f5e22f7178\
