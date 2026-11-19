# Etapa 5 — Claude razona los planos (sin llave) + rediseño total del tablero
Estado: **APROBADO** (Steven, 16/11/2026: "Apruebo con propuestas"). Sin llave de API, con su suscripción de Claude y sin ningún pago adicional.
**v3 APROBADA (Steven, 19/11/2026: "Apruebo y súbelo"):** incorpora la instrucción de Steven publicada en el PR 31 (organización de la Fase B) y el resultado de A1, con las propuestas D10–D14. Se reanudan las fases A y B.
**v4 APROBADA (Steven, 19/11/2026: "Apruebo y súbelo"):** incorpora el ajuste de alcance de Codex (PR 33, `PLANES/alcance-catdic-web-2026-11-19.md`) y las reglas de la memoria de la otra cuenta de Claude de Steven. Hay 4 cambios:
1. El anclaje admite evidencias además del texto literal.
2. El paquete de lectura sirve para la IA de cualquier compañero.
3. Hay un piloto con un informe ya entregado (Zoetry H2).
4. MIVED se genera solo al completar el entrepiso.

A5 y A4b quedan en pausa hasta aprobar la v4; la Fase B sigue.

Base del plan: `origin/main` en `b5f7d26` (no el checkout local, que está atrasado; ver "Puesta al día de git").
Método: skill `gestion-proyectos` (Director → Líderes de fase → Ejecutores), integrada con este sistema de `PLANES/` y con `COLABORACION.md`. No se crea `.proyecto/`: el estado vive aquí.

| Qué | Dónde |
|---|---|
| Plan y decisiones (lo que la skill llama `PLAN.md`) | este archivo |
| Estado de cada fase (lo escribe su Líder) | `PLANES/etapa-5-fase-A.md`, `PLANES/etapa-5-fase-B.md` |
| Reporte de cada tarea (máx. 15 líneas) | `PLANES/etapa-5-reportes/<tarea>.md` |
| Auditorías | `PLANES/etapa-5-evaluacion.md` (skill `auditar-catdic`) |

### Respuestas de Steven
- 16/11/2026, sobre el gasto (D3): "CLAUDE COBRA POR CLAVE API. SI ES ASI USAMOS UNA CLAVE DE GEMINI QUE VEO QUE NO ME COBRA" → se le explicó que la llave gratuita de Gemini permite a Google usar las hojas para mejorar sus productos y que su suscripción Gemini Pro no incluye la API.
- 16/11/2026: "SIN LLAVE, USA MI SUSCRIPCION DE CLAUDE. […] NO QUIERO PAGAR ADICIONAL. YA PAGO CLAUDE Y GEMINI."
  - **D3 resuelta:** no hay llave de API (ni de Claude ni de Gemini), no hay `.env`, no se agrega el SDK `anthropic`. La lectura de planos la hace una sesión de Claude Code con la suscripción.
  - **D2 resuelta:** los planos los lee Claude Code igual que hoy; no salen a ningún servicio nuevo.
  - Regla nueva de la etapa: **ninguna tarea puede introducir un servicio de pago**. El único consumo es el cupo de uso de la suscripción.
- 16/11/2026: "Apruebo con propuestas" → plan APROBADO con las propuestas del Director:
  - **D1:** puesta al día de git (respaldo → comparar → `main` al día). Hecha el 16/11; ver Bitácora.
  - **D4:** los planos escaneados quedan fuera de esta etapa.
  - **D5:** frontend sin compilación, con Vue y Tailwind copiados localmente. Ajuste del 19/11: solo Vue 3.5.13, cuya descarga autorizó Steven; Tailwind no hace falta porque el estilo Plano sellado usa variables CSS.
  - **D6:** sin referencia dada; B1 trae 2–3 maquetas.
  - **D7:** nadie más toca `FRONTEND/` durante la Fase B; T10b pasa a ser B3d.
  - **D8:** ejecutores "fresh" en esta etapa.
  - **D9:** orden columnas → muros y zapatas → pórticos → losas (A1 propone cambiarlo: ver D10).
- 16/11/2026: "Sí, Codex revisa" → **D7 completa:** Codex sigue revisando los PR.
- 16–17/11/2026: CATDIC-WEB es el sistema principal y GPR su herramienta de escaneos; primero se completa GPR y la integración viene después (`PLANES/alcance-gpr.md`). La Etapa 5 se detuvo mientras tanto.
- Instrucción publicada en el PR 31 (comentario de Steven): skills de diseño por momento, referencias oficiales (Procore, Autodesk, PlanRadar, Fieldwire) y **organización aprobada**. Se incorpora en la Fase B (abajo). Aclara que **no aprueba implementación ni fusión**.
- 19/11/2026, ajuste de alcance (PR 33 de Codex, que recoge lo que Steven le dijo). Lo confirmado por Steven está en el §2 de ese documento:
  - Claude ya le hace los informes completos y hay que llevar ese proceso a CATDIC-WEB.
  - Los planos los interpreta una IA, no patrones rígidos; el programa genera los informes.
  - En campo se usa Report and Run.
  - La cuenta es Claude Pro, sin pago adicional.
  - Los compañeros pueden usar su propia IA.
  - El objetivo es multiusuario para compañeros y jefes.
- 19/11/2026: "Sí, CATDIC-WEB" → CATDIC-WEB es el sistema principal. La nota de la otra cuenta que lo daba por cancelado está superada.
- 19/11/2026 (respuestas en la sesión del Director):
  - "Sí, ajusta a v4"
  - "Sí, descarga Vue": Vue 3.5.13 local en `FRONTEND/vendor/vue/`.
  - "Zoetry H2": informe de referencia del piloto.
  - "MIVED solo al completar": el formulario MIVED se genera una vez, cuando el elemento del entrepiso está completo, con todas sus visitas; no hay formulario por parcial.
  - Steven no eligió Arial: sigue `Aptos Narrow` de CLAUDE.md para CATDIC-STP.
  - **D6 sustituida:** ya hay referencia organizativa aprobada. Navegación: **Inicio · Mis obras · Bandeja de trabajo · Informes · Configuración**, con **Crear informe** siempre a mano. Dentro de cada obra: **Resumen · Visitas y trabajos · Planos y ficha · Avance · Informes · Cierre**. Las 3 maquetas del 16/11 fueron ilustrativas y con datos ficticios; el estilo visual se explora respetando esta organización.

## Objetivo (palabras de Steven)
1. Que **Claude razone los planos y extraiga toda la información** — ahora sin llave: con su suscripción.
2. **Cambiar totalmente cómo se presenta la página**, aplicando las skills de diseño instaladas (`impeccable`, `ui-ux-pro-max`, `emil-design-eng`, `apple-design`, `animate`, `break-ui`, etc.).

**Criterio de terminado:**
- Para una obra con plano vigente, Steven pide la lectura (desde el tablero se preparan las hojas; una sesión de Claude Code las lee) y al importar aparecen propuestas para columnas, muros, zapatas, pórticos por tramo y losas, cada valor con su hoja y recuadro de origen y **todas en `pendiente_de_verificar`**; lo que Claude no pudo anclar o dudó llega a la Mesa de Dudas. La app sigue funcionando sin internet y sin Claude igual que hoy.
- El tablero nuevo sigue la organización aprobada, cubre el 100 % del inventario funcional del actual (B0) y los criterios de las pantallas nuevas, funciona sin internet, en escritorio y en móvil, pasa `break-ui`, y la suite `py -3.14 -m pytest -q` no tiene más fallos que los 2 conocidos de Dropbox.

## Estado de partida (verificado el 16/11/2026 en `origin/main`)
- **Extracción actual, sin IA:** `BACKEND/plano/lector_plano.py` (módulo puro: texto visible del vectorial + bbox, con PyMuPDF) y `BACKEND/plano/extractor.py` (regex por posición). Solo cubre tablas de aplicación: acero en losa, zapata de muro de lindero, f'c por rango y losa aligerada de P16. Cada valor lleva fuente (archivo, revisión, página, hoja, bbox), queda `pendiente_de_verificar`, pasa por `importadores/validador_diseno.py` y se confirma por lote (`plano/confirmacion.py`, tabla `tablas_extraidas`) o uno por uno en la Mesa de Dudas.
- **Lo que no cubre:** columnas, muros, zapatas aisladas, pórticos por tramo (§4.3), detalles, y obras sin vectorial (decisión 3 de la Etapa 2: "se agrega el ocr o se procesa en el chat", tarea futura).
- **Frontend:** un solo `FRONTEND/index.html` (1.461 líneas, 125 KB), Vue 3 + Tailwind + Font Awesome **desde CDN**, tema oscuro, sin compilación; 86 ganchos `data-*`; 6 modales (Nueva obra, Subir visita/Dropbox, Visor y recuadros, Datos de la obra, Confirmar datos del plano, Mesa de Dudas). Habla con 29 rutas `/api/...`.
- **Trabajos en segundo plano:** ya existen `trabajos` y `trabajo_eventos` (Etapa 3 · T10a); la pantalla en vivo (T10b) está pendiente.

## Decisiones de diseño (propuestas del Director; se vuelven firmes al aprobar)

### Fase A — cómo entra Claude sin llave y sin romper la Regla de Oro
El trabajo se parte en tres piezas. Solo la del medio es Claude; las otras dos son código del backend que funciona sin internet.

| Paso | Quién | Qué hace |
|---|---|---|
| 1. Preparar | Backend (botón del tablero) | Por cada hoja del vectorial vigente guarda en la carpeta local de la obra una imagen de la hoja y la lista de textos visibles, cada uno con un número y su recuadro (los da `lector_plano`). |
| 2. Leer | Sesión de Claude Code (suscripción), con la skill `extraer-plano` | Mira la imagen y la lista, y escribe un archivo `propuesta.json` por hoja: qué texto corresponde a qué campo de qué elemento, **citando el número del texto**. No toca la BD. |
| 3. Importar | Backend (botón del tablero) | Comprueba cada valor contra el texto citado y carga las propuestas por el mismo camino que el extractor actual. |

1. **Claude razona; el valor lo pone el plano.** Al importar, el backend comprueba que el valor propuesto coincide con el texto citado del plano:
   - coincide → propuesta `pendiente_de_verificar` con su fuente (hoja + bbox del texto citado) y `extraido_por = "IA:claude-code"`;
   - no coincide, no cita, o Claude marca duda → el campo queda `"pendiente de verificar"` sin valor y se abre una duda con prefijo `IA:`.
2. **Nada de lo que proponga Claude nace `confirmado`.** Entra por el validador de T2, con clave UNIQUE idempotente, nunca toca un campo ya confirmado, se confirma por lote o por la Mesa de Dudas y deja auditoría por campo.
3. **Doble lectura donde ya hay extractor:** si el extractor por posición y Claude leen el mismo campo y difieren, se abre una duda; si coinciden, se anota como comprobación en verde (el campo sigue pendiente hasta que Steven confirme).
4. **Capas (§4.1):** Claude solo trabaja en la Capa 1 (planos). Nunca recibe fotos de campo como fuente de datos de diseño y no calcula cuantías ni recubrimientos (eso es `reglas_ingenieria.py`).
5. **Offline (§1.5):** la app no llama a ningún servicio. Preparar e importar funcionan sin internet; solo el paso 2 necesita una sesión de Claude Code. Generar informes sigue 100 % offline.
6. **Sin costo adicional:** no hay llave, ni `.env`, ni SDK de pago. El paso 2 consume cupo de la suscripción; A1 mide cuánto por hoja para que Steven sepa cuántas hojas caben en un día de trabajo. Se lee por lotes de hojas, nunca el PDF entero, y se puede retomar donde quedó.
7. **El plano no se modifica:** se comprueba el sha256 del vectorial al preparar y al importar; si el plano cambió, la propuesta no se importa.

**Ajustes v4 (PR 33), que sustituyen lo anterior donde choquen:**

8. **Anclaje con evidencias, no solo con el texto literal.** La fuente sigue siendo obligatoria. Un valor entra si trae una de estas evidencias:
   - (a) el texto citado tal cual (lo de hoy);
   - (b) varios textos citados que juntos lo dan;
   - (c) una zona o recorte de la hoja (cota dibujada, detalle), con su caja y la lectura propuesta;
   - (d) una conversión o suma que hace **el programa**, no la IA, guardando la entrada y la regla (por ejemplo `1.5` → `1.50 m`).

   Con (c), el valor queda pendiente y además abre una duda de revisión visual. Sin ninguna evidencia, no hay valor. **Que el número exista en la hoja no prueba que sea del elemento correcto**: la revisión mira identidad, nivel, ejes, detalle aplicable, unidades y contradicciones.
9. **Cualquier IA, no solo Claude Code.** El paquete de una hoja (`hoja.png`, `textos.txt`, recortes, instrucciones de la skill y el formato de `propuesta.json`) debe poder usarlo la IA de un compañero desde su propia cuenta. La propuesta registra el modelo o proveedor que la hizo y quién la revisó. No se usa la cuenta de Steven como servicio para otros ni se reutilizan sus sesiones o tokens.
10. **Leer una vez por revisión de plano:** lo revisado se reutiliza en todas las visitas, y solo se relee si cambia el sha256. Nunca se manda el plano entero a la IA en cada informe.
11. **No se borra el extractor por posición** (`lector_plano.py`, `extractor.py`) hasta que el camino con IA lo sustituya con una prueba real revisada. `lector_plano` sigue siendo la fuente del texto que se da a la IA.

### Fase B — cómo se rehace el tablero
1. **Primero inventario, luego diseño, luego código.** Nada del tablero actual se pierde: B0 lista cada pantalla, acción, ruta y gancho `data-*`, y esa lista es la prueba de paridad al final. Las necesidades nuevas (Inicio, Bandeja, Resumen de obra, Crear informe independiente) llevan sus propios criterios de aceptación, aparte de la paridad.
2. **La organización ya está aprobada** (D6, arriba). Lo que Steven elige en B1 es el **estilo visual** sobre esa organización. El resultado se fija en `DESIGN.md`.
3. **Se parte el archivo único** en módulos y componentes para que varias sesiones puedan trabajar sin pisarse, y **todo queda local** (sin CDN).
4. **Backend: sin cambios ocultos.** Lo que ya existe se usa por sus rutas actuales. Lo que necesite datos o rutas nuevas (indicadores, bandeja común, trabajos independientes) **no se simula**: se convierte en tarea de backend aparte (Fase D), coordinada por el Director. Mientras no exista, la pantalla muestra «pendiente de verificar» o «disponible más adelante», nunca un número inventado.
5. **Bandeja común sin duplicar:** Cola, Mesa de Dudas, extracción y Órdenes conservan sus pantallas especializadas, pero sus pendientes aparecen también en la Bandeja leyendo los mismos registros, no copias.
6. **Contexto de obra:** al navegar dentro de una obra no se pierde la obra elegida.
7. **Capacidades disponibles contra futuras:** los servicios previstos (supervisión STP, levantamiento de supervisión, estructural, visual, dimensional, esclerometría) se muestran distinguiendo lo que ya genera el sistema de lo que es desarrollo futuro. Esto **no** declara implementados los formatos HV ni amplía la Etapa 5.
8. **Skills de diseño por momento** (instrucción de Steven): organización y diseño con `impeccable` y `ui-ux-pro-max`; legibilidad e interacción con `emil-design-eng` y `apple-design`; movimiento, solo si ayuda, con `animate`, `choreograph` y `animation-performance`; validación con `break-ui` y las revisiones de `impeccable`. Cada propuesta dice **qué skills aplicó y qué decisión aportó cada una**; no basta con nombrarlas.
9. **Referencias** (adaptar patrones, no copiar funciones ajenas al alcance): Procore (resumen de obra y pendientes), Autodesk Project Home (trabajo asignado y acceso directo desde Inicio), PlanRadar (pendiente junto al plano; planos por edificio, nivel y versión), Fieldwire (expediente con fuentes, fotos, respuestas, estado y documentos). Cada propuesta explica qué patrón adapta y por qué ayuda al flujo CATDIC. Los enlaces están en el comentario de Steven en el PR 31.
10. La pantalla en vivo del procesador (Etapa 3 · T10b) y la pantalla de lectura asistida se construyen dentro del tablero nuevo, no en el viejo.

## Fases

| Fase | Alcance | Zona de archivos | Depende de | Modo | Estado |
|---|---|---|---|---|---|
| **0 · Cimientos** | git al día, ajuste de la especificación | `PLANES/`, `CLAUDE.md` + `AGENTS.md` | Aprobación de Steven | **directo** | T0.1 hecha · T0.2 no hace falta · T0.3 pendiente (no bloquea A ni B) |
| **P · Piloto con un informe entregado** | recorrer Zoetry H2 de punta a punta con el proceso actual de Claude como referencia y medir el camino nuevo contra su resultado | `PLANES/etapa-5-piloto.md` y carpeta local (nunca datos reales en git) | aprobación v4 | **directo** (Director, con Steven) | nueva (v4) |
| **A · La IA razona los planos** | reconocimiento, preparar hojas, importar con anclaje, skill `extraer-plano`, rutas, prueba real | `BACKEND/plano/asistido/**` (nuevo), `.claude/skills/extraer-plano/` (nuevo), `BACKEND/tests/test_asistido_*.py` | Fase 0 | **líder** (Opus) | A1, A2, A3 (a, b, c) y A4a hechas y auditadas · **A5 y A4b en pausa** hasta aprobar la v4 · siguen A3d y A4-paquete |
| **B · Rediseño del tablero** | inventario, estilo visual sobre la organización aprobada, base, pantallas, movimiento, prueba de rotura | `FRONTEND/**`, `DESIGN.md` | Fase 0 | **líder** (Opus) | B0 y B1 hechas · estilo **Plano sellado** (Steven, 19/11) · B2 en curso con Vue local, sin Tailwind |
| **C · Integración** | pantalla "Lectura asistida" contra las rutas reales, auditoría de integración, prueba completa en el navegador | `FRONTEND/**` (solo esa pantalla), `PLANES/` | A5 y B3 | **directo** | pendiente |
| **D · Datos nuevos del tablero** | lo que las pantallas nuevas necesitan del backend: bandeja común, indicadores, trabajos independientes | `BACKEND/tablero/**` (nuevo), pruebas | D-a: B1 elegida · D-b: D15 · D-c: B1 elegida | ejecutor-backend, coordinado por el Director | aprobada (D14); pendiente |

**Paralelismo:** **A y B corren a la vez**: no comparten ningún archivo (`main.py` solo recibe las líneas `include_router` de A5 y de la Fase D, que coordina el Director). La Fase C va al final. La Fase D no empieza hasta que Steven defina lo que le toca. Para cuidar el cupo de la suscripción: **máximo 3 sesiones trabajando a la vez en total**.

**Ramas de partida:** mientras el PR 31 no esté fusionado, toda rama de la etapa sale de `claude/etapa5-plan`; cuando Steven lo fusione, sale de `main`. Una tarea que depende de otra sale de la rama de la anterior.

**Pruebas:** la suite de referencia tiene 2 fallos conocidos que dependen del contenido de Dropbox (ver "Reglas de convivencia"). Esos dos no bloquean; **cualquier otro fallo sí bloquea** la tarea.

**Nadie más toca `FRONTEND/` mientras dure la Fase B** (ni Codex ni tareas de las Etapas 2–4); ver D7.

## Tareas

### Fase 0 — Cimientos (directo)

#### T0.1 — Puesta al día de git (Steven decide; ver D1)
- Ejecutor: Director, con permiso expreso de Steven para cada paso.
- Hecho cuando: existe una rama `claude/etapa5-plan` salida de `origin/main` con este plan; el checkout principal queda como Steven decida.

#### T0.2 — Estáticos y contrato — NO HACE FALTA (16/11/2026)
- Comprobado en `main`: `BACKEND/main.py:196` ya monta toda la carpeta `FRONTEND/` en `/` (`StaticFiles(..., html=True)`). El tablero nuevo puede repartirse en archivos sin tocar el backend, y el viejo puede vivir en `FRONTEND/clasico/index.html` (se abre en `/clasico/`).
- El contrato de rutas es el de A5 (abajo). El formato de `textos.json` y `propuesta.json` lo fija el Líder de la Fase A en `PLANES/etapa-5-contrato-asistido.md` después de A1.
- Única excepción a "nadie toca `main.py`": A5 agrega **una línea** `app.include_router(...)` para sus rutas.

#### T0.3 — Especificación
- Ejecutor: Director (texto) · rama `claude/etapa5-spec`
- Qué hacer: proponer a Steven el texto nuevo de `CLAUDE.md` y `AGENTS.md` (los dos iguales). Se aplica solo con su visto bueno. Incluye:
  - Una sección "Lectura de planos asistida por IA" con las decisiones 1–11 y la regla de que no se usan servicios de pago.
  - **v4, MIVED:** el formato 3 y el error 18 cambian a «un formulario por nivel y tipo, generado una sola vez cuando el elemento del entrepiso está completo, listando todas sus visitas; no hay formulario por parcial». Cada nivel usa su propio formulario en blanco (MIVED aprueba por nivel), nunca el de otro nivel.
  - **v4, reglas de la otra cuenta, a proponer una por una (D19):**
    - Licencia MIVED obligatoria en todo proyecto STP.
    - Carpetas `3.INFORME EN REVISION` y `4.INFORME LISTO`.
    - En las fichas, los valores como dicen los planos.
    - Muros de bloques: sin acero horizontal, bastones según el escáner y viga de amarre 2Ø3/8".
    - Un escaneo de columna de más de 1,50 m pasa a ficha de muro de bloques.
    - Las conclusiones HV solo con discrepancias.

#### T0.4 — Ajuste del generador FI a «MIVED solo al completar» (v4)
- Ejecutor: ejecutor-generadores (Sonnet) · `BACKEND/generators/` (FI) y sus pruebas, en una rama propia salida de `main`, fuera de las zonas de A y B.
- Qué hacer: el procesador no genera ni actualiza el FI con una visita parcial. Lo genera cuando Steven marca el elemento del entrepiso como completo, listando todas sus visitas en Observaciones. Se mantiene: nunca sobrescribir, `v2`/`v3` si ya existe, y los «Sí» obligatorios sin mampostería.
- Antes: el Director lee el generador actual y le propone a Steven el cambio exacto. Arranca solo con su sí.

#### T0.5 — Repasar las tareas de las Etapas 2–4 afectadas por el PR 33 (v4)
- Ejecutor: Director. Una tabla breve en este archivo con cada tarea abierta de las Etapas 2–4, su estado, su dependencia y si cambia. Por ejemplo:
  - extracción por patrones → camino IA;
  - Etapa 4 HV → medida en el piloto;
  - informes de cierre STP e informe semanal de avance → funciones nuevas pedidas, sin etapa todavía.
- Sin documentos largos (§10 del PR 33).

### Fase A — Claude razona los planos (líder)

#### A1 — Reconocimiento (solo lectura)
- Ejecutor: una sesión de Sonnet prepara las hojas a mano; el Líder (Opus) hace la lectura · informe `PLANES/etapa-5-reconocimiento-asistido.md`
- Qué hacer: con el vectorial vigente de Terra Living, probar 4–6 hojas elegidas con Steven: una tabla que el extractor actual ya lee y Steven ya confirmó (sirve de control) y hojas que hoy no se leen (cuadro de columnas, detalle de muro, elevación de un pórtico con su banda de estribos, zapatas). Probar 2–3 resoluciones de imagen. Medir por hoja: aciertos contra el plano, valores sin ancla, tiempo y consumo de cupo.
- Hecho cuando: el informe trae la tabla de resultados por hoja, la resolución recomendada, cuántas hojas caben razonablemente por sesión y la lista de tipos de elemento ordenada por fiabilidad. El Director lo contrasta con el plano real. Nada se escribe en la BD ni en Dropbox.
- **Puerta:** Steven ve el informe antes de A3 y A4.
- **Estado: HECHA (16/11)** · rama `claude/etapa5-fase-a-3da668` · informe `PLANES/etapa-5-reconocimiento-asistido.md`. El Director comprobó en el PDF real que los textos citados existen (pp. 7, 14, 21 y 34); no repasó valor por valor.
  - **Se lee bien, con todo anclado al texto del plano:** columnas (60/60 valores comprobados), losas por su etiqueta en planta (20/20, y la tabla de acero 22/22, igual que el extractor actual), muros (24/24 en MH4) y pórticos con recorte por nivel (16/16 en un nivel).
  - **Se lee mal:** fundaciones con *drops* (el mismo ID tiene distinto H1 y las secciones no nombran el *drop*).
  - **Hallazgos:** el cuadro de columnas no da ejes; los pórticos traen el nivel como `NPT= 3.60`, así que hace falta una equivalencia NPT ↔ nivel que dé Steven; en MH4 las cotas parciales suman 3.81 y el total dice 3.80 (irá como duda); 3 de 6 hojas traen notas de «plano anterior» (irán como duda, nunca se aplican).
  - **Resolución:** hoja a 72 ppp para orientarse y recortes a 150 ppp para leer.
  - **Cupo (cuenta Pro):** Terra Living completo cabe en unas 1,5–2 ventanas de 5 h; sesiones lectoras cortas y nuevas, un pórtico por sesión.
  - Las preguntas de la puerta están en D10–D13.

#### A2 — Preparar hojas
- Ejecutor: ejecutor-backend (Sonnet) · Archivos: `BACKEND/plano/asistido/__init__.py`, `preparar.py`, `BACKEND/tests/test_asistido_preparar.py`.
- Qué hacer: para una obra y una lista de páginas, escribir en la carpeta local de la obra (`CATDIC_DATOS_RAIZ`, nunca en Dropbox ni en el repositorio) `pNN/hoja.png` y `pNN/textos.json` (número, texto, bbox, hoja), más un `manifiesto.json` con el sha256 del vectorial. Reutiliza `lector_plano` sin modificarlo. Solo lee capas visibles.
- Hecho cuando: pruebas `# SINTÉTICO` con un PDF pequeño; preparar dos veces da el mismo resultado; el plano no cambia (sha256 antes y después).
- Puede ir en paralelo con A1.
- **Estado: HECHA (16/11)** · rama `claude/etapa5-a2-preparar-3d8018` (`41396f8`), 8 pruebas pasan según el Líder. **Ajustes tras la puerta:** 72 ppp, un `textos.txt` compacto, recortes en `zonas/` y un manifiesto que acumule lotes.

#### A3 — Importar con anclaje
- Ejecutor: ejecutor-backend (Sonnet) · Archivos: `BACKEND/plano/asistido/esquema.py`, `importar.py`, pruebas.
- Qué hacer: validar `propuesta.json` contra el esquema; aplicar las decisiones A1–A3 y A7; reutilizar `validador_diseno` y las funciones de escritura y de dudas de `plano/extractor.py` **sin modificarlas** (si hace falta abrir una función, se pide al Director).
- Reglas que se prueban: formato de `EJES` de §4.4 (losas siempre `—`; nada deducido por cercanía); planta contra detalle en contradicción → `DUDA_BLOQUEANTE` (§4.2); un valor sin texto citado nunca se guarda como valor; un archivo mal formado no carga nada.
- Hecho cuando: pruebas `# SINTÉTICO` con propuestas buenas, sin ancla, con valor distinto al texto, con plano cambiado y repetidas (idempotencia); 0 campos `confirmado`.

#### A4 — Skill `extraer-plano` (el procedimiento que sigue Claude al leer)
- Ejecutor: Líder de la fase (Opus) · Archivos: `.claude/skills/extraer-plano/SKILL.md` y sus referencias por tipo de elemento.
- Qué hacer: el procedimiento paso a paso para la sesión lectora: qué archivos abrir, cómo citar, qué hacer ante duda (marcarla, nunca rellenar), las reglas de §4.2–§4.4 y el formato exacto de salida. Un apartado por tipo, en el orden que decida Steven en D10. Propuesta tras A1: **A4a** columnas · **A4b** losas · **A4c** muros · **A4d** pórticos por tramo (§4.3, con el control cruzado `S + losa = Hv`) · fundaciones al final y según D12.
- Hecho cuando (cada apartado): una sesión nueva, solo con la skill, lee las hojas de A1 de ese tipo y al importar quedan 0 valores sin ancla guardados; el Director contrasta una muestra contra el plano.

#### Estado de A2–A4a (19/11, auditado por el Director)
- A2 unida a la rama de fase (`df7cb9a`).
- A3a: `60b3510` extractor con `origen` opcional y `831a10d` esquema.
- A3b: `184db80` importar.
- A3c: `f9df117`, la losa con nivel escrito distinto no se duplica y nada se descarta en silencio.
- A4a: `fccf736`, skill de columnas.
- Todo con 0 `confirmado` y sin tocar la BD real.

#### A3d — Anclaje con evidencias (v4, decisión 8)
- Ejecutor: ejecutor-backend (Sonnet), en la rama de fase. Archivos: `esquema.py`, `importar.py` y sus pruebas.
- Qué hacer: aceptar las evidencias (b), (c) y (d) de la decisión 8.
  - (c) guarda la zona como fuente y abre una duda `IA: revisión visual`.
  - (d) la hace el programa con una regla declarada y probada, nunca la IA.
  - El literal (a) se mantiene igual.
- Hecho cuando: pruebas `# SINTÉTICO` de cada tipo de evidencia, sin evidencia → pendiente, 0 `confirmado`, y las pruebas actuales pasan.

#### A4-paquete — El paquete sirve para cualquier IA (v4, decisión 9)
- Ejecutor: Líder A. Qué hacer:
  - Un `INSTRUCCIONES.md` autocontenido por lote, con lo esencial de la skill y del formato, que un compañero pueda pegar en su propia IA junto con las imágenes.
  - El campo `lector` de la propuesta registra modelo o proveedor.
  - Medir con una IA distinta de Claude Code solo si Steven lo pide y con una cuenta autorizada.
- Hecho cuando: una sesión nueva, solo con el paquete, produce una propuesta que pasa `revisar.py`.

#### A5 — Rutas (EN PAUSA hasta aprobar la v4; después, sin cambios de contrato)
- Ejecutor: ejecutor-backend (Sonnet) · Archivos: `BACKEND/plano/asistido/rutas.py`, pruebas.
- Contrato (se fija en T0.2):
  - `GET /api/proyectos/{id}/lectura-asistida` → estado por hoja: sin preparar / preparada / propuesta lista / importada / plano cambiado
  - `POST /api/proyectos/{id}/lectura-asistida/preparar` `{paginas?: [..]}`
  - `POST /api/proyectos/{id}/lectura-asistida/importar` `{paginas?: [..]}` → propuestas cargadas, dudas abiertas, valores rechazados por falta de ancla
  - los resultados se ven por las rutas actuales de `elementos`, `tablas-extraidas` y `dudas`.
- Hecho cuando: cada importación deja una fila en `auditoria`; importar dos veces no duplica.

#### A6 — Prueba real y cierre de fase
- Terra Living completo y Torre P16 (Losa E-9), por lotes de hojas. Informe: elementos propuestos por tipo, dudas abiertas, cupo consumido. El Director audita contra los planos.

#### A7 — (Opcional, por verificar) Botón que lanza a Claude desde el tablero
- Averiguar si Claude Code puede arrancarse desde el backend con la suscripción, sin llave y sin costo adicional, para que el paso 2 también sea un botón. Si no se puede garantizar que no cobra, **no se hace** y el paso 2 se sigue pidiendo a una sesión.

### Fase P — Piloto Zoetry H2 (v4; directo, Director con Steven)
Es lo que pide el §10 del PR 33: llevar a CATDIC-WEB el proceso con el que Claude ya entrega informes, partiendo de un caso que salió bien. Nada de sus archivos reales entra en git.
- **P1 · Reunir el caso:**
  - Steven indica dónde están el informe final de H2, los planos y su revisión, los reportes de visita (Report and Run), los escaneos y las instrucciones o chats de la otra cuenta («ensamble de informes»).
  - El Director arma un índice local, en solo lectura.
  - Hecho cuando: el índice dice qué hay y qué falta, y lo que falte queda «pendiente de verificar».
- **P2 · Recorrido en 1 página:** paso a paso, qué hizo la IA y qué el programa o Steven, qué salida mínima guarda datos con sus fuentes, y qué del informe H2 no puede generar hoy CATDIC-WEB.
  - Los formatos HV y la teoría Word son de la Etapa 4. El piloto los **mide**, no los construye.
- **P3 · Primer intercambio medido:** preparar → IA → importar → revisar, sobre un lote pequeño de H2. Se compara con el informe entregado:
  - omisiones;
  - datos mal asociados;
  - dudas omitidas;
  - esfuerzo y tiempo.

  No se presenta como aprobado ni como generalizable.
- **P4 · Visitas difíciles:** contrastar las visitas #17, #18 y #20 de Terra Living (contexto entre etiquetas, fotos sin rótulo, orden no cronológico, contradicciones) antes de generalizar la lectura de visitas con IA. Es solo medición; leer visitas sigue fuera de esta etapa.
- **Riesgo conocido:** H2 es un levantamiento de una edificación existente, con datos del escáner además de los planos. P1 debe decir qué parte del informe viene de planos (Fase A) y cuál del campo (Capa 2 y GPR).

### Fase B — Rediseño del tablero (líder)

#### B0 — Inventario funcional (solo lectura)
- Ejecutor: ejecutor-frontend (Sonnet) · informe `PLANES/etapa-5-inventario-ui.md`
- Hecho cuando: están listadas todas las pantallas, modales, acciones, estados (cargando, vacío, error), rutas que usa cada una y los 86 `data-*`. El Director lo contrasta con `index.html`.
- **Estado: HECHA (16/11)** · rama `claude/etapa5-fase-b-0020e1`. Se amplía en B1 con una sección de **necesidades nuevas** y sus criterios propios (Inicio, Bandeja, Resumen de obra, Crear informe independiente).

#### B1 — Estilo visual sobre la organización aprobada (puerta de Steven)
- Ejecutor: Líder de la fase (Opus), aplicando las skills del punto 8 de las decisiones de la Fase B.
- **Rehacer** las propuestas del 16/11 (A · Expediente, B · Plano, C · Obra): eran ilustrativas, con datos ficticios y otra navegación. Se conservan como antecedente; no se borran.
- Qué hacer: 2–3 estilos visuales, todos con la **misma organización aprobada** (D6), con estas pantallas:
  - **Inicio:** prioridades, dudas, revisiones, entregas y próximas acciones.
  - **Resumen de obra:** los tres indicadores y los pendientes.
  - **Bandeja:** pendientes de obras y de trabajos independientes.
  - **Revisión de planos:** lista de elementos propuestos a la izquierda, plano al centro, y a la derecha los datos propuestos con sus fuentes y acciones. Desde la revisión de visitas, acceso a la foto y la etiqueta originales.
  - **Crear informe independiente:** elegir servicios, aportar datos y fuentes, revisar el pedido y preparar el trabajo sin crear una obra de seguimiento.
- **Indicadores** (Resumen de obra):
  1. Avance por entrepisos = entrepisos ejecutados y confirmados / total previsto en planos.
  2. Expediente completo = unidades documentales completadas / alcance documental final confirmado.
  3. Documentación al día = unidades completadas y exigibles / total exigible hasta el avance actual.
  - Sus definiciones de fondo son de Steven (D15). Hasta entonces la maqueta los muestra «pendiente de verificar». **La falta de datos no se muestra como 0 %**, y no se usan número de archivos, versiones o visitas como sustituto.
- **Datos:** sintéticos y rotulados como tales. Cada pantalla muestra sus estados vacío, cargando, error y «pendiente de verificar».
- Cada propuesta explica qué skills aplicó, qué decisión aportó cada una y qué patrón adapta de las referencias.
- Adaptación responsive desde el principio (escritorio y móvil).
- **Puerta:** Steven elige el estilo. Sin elección no empieza B2. Después se escribe `DESIGN.md` con lo construido.

#### B2 — Base
- Ejecutor: ejecutor-frontend (Sonnet) · Archivos: estructura nueva de `FRONTEND/` (según D5), librerías locales en `FRONTEND/vendor/`, tokens de diseño, armazón con navegación, cliente de la API.
- Hecho cuando: el armazón abre en `http://localhost:8000` **sin internet** y el tablero viejo sigue disponible en `/clasico` hasta el cierre de la fase.

#### B3 — Pantallas (una tarea por pantalla, cada una en sus propios archivos)
- B3a Inicio y Mis obras · B3b Obra: Resumen, Planos y ficha, visor y recuadros · B3c Revisión de planos (confirmar datos del plano) · B3d Visitas y trabajos: cola, subir visita/Dropbox y avance del procesador (cubre T10b) · B3e Bandeja de trabajo y Mesa de Dudas · B3f Órdenes de trabajo · B3g Informes y Crear informe (solo con lo que ya genera el sistema; lo demás, «disponible más adelante»).
- Lo que dependa de la Fase D se construye con su estado «pendiente de verificar» y se conecta cuando D esté.
- Hecho cuando (cada una): todas sus filas del inventario B0 y sus criterios nuevos marcados y probados en el navegador contra una **copia** de la BD; cero errores en consola.

#### B4 — Movimiento y pulido
- Skills: `animate`, `choreograph`, `emil-design-eng`, `animation-performance`; revisión con `review` de `impeccable`. Respeta `prefers-reduced-motion`.

#### B5 — Prueba de rotura y cierre
- `break-ui` con datos extremos (nombres de obra larguísimos, 0 visitas, 500 dudas, IDs con prima `A'`, campos `"pendiente de verificar"`), teclado y contraste, en escritorio (1280 y 1920) y móvil (375), con los temas disponibles y sin conexión. Paridad completa con B0 más los criterios nuevos. Se retira `/clasico` solo con el visto bueno de Steven.

### Fase D — Datos nuevos del tablero (aprobada en D14)
- **D-a Bandeja común:** una ruta de solo lectura que junta los pendientes de Cola, Mesa de Dudas, extracción y Órdenes **desde sus tablas**, sin copiarlos.
- **D-b Indicadores:** las tres cuentas del Resumen de obra, **solo cuando Steven defina** qué cuenta como entrepiso ejecutado y qué es una unidad documental (D15). Sin definición, la ruta devuelve «pendiente de verificar», nunca 0.
- **D-c Trabajos independientes:** un trabajo sin obra de seguimiento que conserva fuentes, dudas, documentos, versiones e historial y que puede vincularse después a una obra. Necesita tablas nuevas: la BD real se respalda antes y las pruebas usan `CATDIC_DB_PATH`.
- Cada una con su PR, revisión de Codex y auditoría del Director.

### Fase C — Integración (directo)
- **C1** Pantalla "Lectura asistida": estado por hoja, botón Preparar, la frase exacta que hay que decirle a Claude Code para que lea, botón Importar, y el resultado que lleva a Confirmar datos y a la Mesa de Dudas. Las propuestas de Claude se distinguen a la vista de las del extractor por posición.
- **C2** Auditoría de integración del Director: recorrido completo en el navegador (obra → preparar → leer → importar → confirmar → procesar visita → PDF), suite completa y revisión contra los 18 errores.

## Modelos y sesiones (skill `gestion-proyectos` §3)
| Rol | Modelo | Esfuerzo |
|---|---|---|
| Director | `claude-opus-5-5` (desde el 17/11/2026) | alto |
| Líder de fase A y B | `claude-opus-5-5` | alto |
| Ejecutor estándar | `claude-sonnet-5-5` | medio |
| Ejecutor mecánico (mover archivos, librerías locales) | `claude-haiku-5-5` | bajo |

Cada ejecutor trabaja en su propio worktree salido de `origin/main`. Ver D8 sobre "fresh" contra "fork". Todo sale del cupo de la suscripción de Steven: si se agota, el trabajo se detiene hasta que se renueve; **no se activa el uso adicional de pago**.

## Reglas de convivencia (de `COLABORACION.md`, sin cambios)
- Ramas `claude/etapa5-<tarea>`; nadie hace push a `main`; un PR por tarea; **Steven fusiona**.
- Todas las ramas de la etapa salen de `claude/etapa5-plan` (trae este plan y los planes rescatados). Una tarea que depende de otra sale de la rama de la anterior.
- Los Líderes y Ejecutores solo hacen commits locales en su propia rama de tarea. **Ningún push, fusión ni cambio en el checkout principal sin permiso de Steven**; el push va después de la auditoría del Director.
- Suite de referencia en `main` (`b5f7d26`, 16/11/2026): 943 pasan, 3 saltadas y **2 fallan por el contenido actual de Dropbox**, no por el código (`test_escaner_dropbox.py::test_terra_living_real`: el PDF `TERRA LIVING -ESTRUCTURALES.pdf` pesa 57.692.301 bytes y la prueba espera 57.692.938; `test_parser_visitas.py::test_lista_coincide_con_dropbox_si_esta_disponible`: faltan 6 carpetas de visita con el nombre esperado). Pendiente de verificar con Steven; ninguna tarea de la Etapa 5 las toca.
- Antes de cambiar de rama, hacer commit, push o fusionar: se le pregunta a Steven.
- Nunca se suben `*.db`, PDFs, fotos ni las carpetas de hojas preparadas. Dropbox en solo lectura. La BD real se respalda antes de tocarla; las pruebas usan `CATDIC_DB_PATH`.
- Todo con `py -3.14`.

## Puesta al día de git (propuesta; no se ejecuta sin Steven)
Situación: el checkout principal está en `codex/planes-traspaso` (`bd197d0`), **97 commits detrás de `origin/main`**; `main` local está 11 detrás; hay 5 worktrees viejos; y hay cambios sin commitear en 4 archivos de `PLANES/` con unas **400 líneas que una comparación rápida no encontró en `origin/main`** (sobre todo `etapa-2-evaluacion.md`; por confirmar), más `.agents/`, `.claude/skills/` y `PLANES/referencia/` sin trackear.
1. Copiar esos 4 archivos y las 3 carpetas a una carpeta de respaldo fuera del repositorio.
2. Comparar el respaldo con `origin/main` y decirle a Steven qué texto se perdería; lo que valga se rescata en un PR de documentación.
3. `git switch main` y `git pull --ff-only`, para que `INICIAR_CATDIC.bat` arranque la versión actual.
4. Limpiar los worktrees viejos solo con su permiso.

Mientras tanto la Etapa 5 no depende de esto: todas las sesiones trabajan en worktrees salidos de `origin/main`.

## Riesgos que hay que vigilar
- **Claude inventa o lee mal un número.** Mitigación: anclaje al texto del plano, doble lectura, todo pendiente, confirmación humana. Se mide en A1 antes de construir.
- **Hojas donde el dato no es texto** (cotas dibujadas, planos escaneados): no hay ancla. Quedan fuera salvo D4.
- **El cupo de la suscripción se agota** a mitad de una lectura o del proyecto. Mitigación: lotes de hojas retomables, máximo 3 sesiones a la vez, Sonnet para lo mecánico.
- **El paso 2 no es un botón:** hay que pedírselo a una sesión de Claude Code. A7 estudia si puede serlo sin costo.
- **Perder funciones al rediseñar.** Mitigación: inventario B0, paridad en B5, tablero viejo en `/clasico` hasta el final.
- **Choque con Codex o con tareas de las Etapas 2–4** en `FRONTEND/` o `main.py`. Mitigación: congelación de D7 y Fase 0 primero.
- **`CLAUDE.md` y `AGENTS.md` desincronizados.** Se cambian juntos en T0.3.
- **Pantallas nuevas que aparentan funcionar sin datos detrás** (indicadores, bandeja, trabajos independientes). Mitigación: Fase D aparte, «pendiente de verificar» visible, falta de datos ≠ 0 %.
- **El alcance crece sin decidirlo** (formatos HV, GPR dentro del tablero). Mitigación: «Crear informe» solo ofrece lo que ya se genera; lo demás se rotula como futuro.

## Decisiones
Resueltas: D1 (git al día, hecha), D2, D3, D4 (escaneados fuera), D5 (sin compilación), D6 (organización aprobada en el PR 31), D7 (Codex revisa; nadie más toca `FRONTEND/`), D8 (fresh), D9 (sustituida por D10).
**D10–D14 aprobadas como se proponen abajo** (19/11/2026). **Sigue abierta: D15.**

- **D10 · Orden de lectura (Fase A):** A1 propone columnas → losas → muros → pórticos → fundaciones, en lugar de D9, porque las losas se leen mejor de lo esperado y las fundaciones peor.
- **D11 · Ejes de columnas y muros:** los detalles no los dan. Propuesta: guardar el diseño por ID + rango de nivel con EJES «pendiente de verificar», y cruzarlo con la visita por ID + nivel. La alternativa (que Claude deduzca el cruce mirando la planta) es cercanía visual: va contra el error 11 y la Regla de Oro.
- **D12 · Fundaciones con *drops*:** propuesta: en esta etapa solo el espesor de la platea y la tabla de f'c; los *drops* van a la Mesa de Dudas.
- **D13 · Cupo:** propuesta: la prueba real (A6) por lotes a lo largo de varios días, para no frenar la Fase B ni a GPR.
- **D14 · Fase D (datos nuevos del tablero):** ¿entra en la Etapa 5? Propuesta: **sí la bandeja común** (solo lee registros que ya existen); **los indicadores, solo cuando definas D15**; **los trabajos independientes, en la maqueta B1 ahora y en el backend después de que elijas el estilo**, porque necesitan tablas nuevas.
- **D16 · Piloto (resuelta, Steven 19/11):** Zoetry H2.
- **D17 · MIVED (resuelta, Steven 19/11):** el formulario se genera solo al completar el elemento del entrepiso (T0.3, T0.4).
- **D18 · Letra (resuelta, Steven 19/11):** no se cambia a Arial; sigue CLAUDE.md.
- **D19 · Reglas de la otra cuenta** (abierta): T0.3 las propone una por una para que Steven diga cuáles pasan a CLAUDE.md. Ninguna se aplica sin su sí.
- **D20 · Report and Run** (abierta, del PR 33): comprobar qué versión y qué exportaciones usa CATDIC (PDF u otra) antes de exigir campos nuevos. Se mira en P1 con los archivos de H2.
- **D15 · Definiciones de los indicadores** (las marcaste tú como pendientes; no se inventan): qué evidencia permite contar un entrepiso como ejecutado, qué es el cierre documental y cómo se definen y ponderan las unidades documentales. No bloquean B1: allí salen «pendiente de verificar».

## Verificación
- **Fase 0:** suite en verde; ninguna dependencia nueva en `requirements.txt`.
- **Fase A:** informe A1 contrastado con el plano; por apartado de A4, 0 valores sin ancla guardados y 0 `confirmado` sin acción del usuario; volver a importar es idempotente; el sha256 del plano no cambia.
- **Fase B:** paridad con B0 fila por fila en el navegador; sin peticiones a internet (pestaña de red); `break-ui` sin roturas abiertas.
- **Fase C:** recorrido completo y auditoría `auditar-catdic` con veredicto APROBADO antes de cada push.

## Fuera de alcance de esta etapa
- Cualquier llave de API o servicio de pago (Claude, Gemini u otro).
- Etapa 4 (formatos HV) y CATDIC-STP (T9, aplazada).
- La integración de GPR (sus resultados revisados entran por los formatos HV de la Etapa 4; ver `PLANES/alcance-gpr.md`).
- Que la IA lea visitas a obra o fotos de campo (Capa 2). En el piloto (P4) solo se mide.
- Usuarios y roles, alojamiento y despliegue (issue 32). El objetivo multiusuario está confirmado, pero no se construye en esta etapa.
- Un conector MCP o una IA central por API (PR 33 §6): son propuestas posteriores y no están autorizadas.
- Cambios en los generadores de PDF.

## Bitácora (lo más nuevo arriba)
- 19/11/2026 · Steven: "Apruebo y súbelo" → v4 aprobada.
- 19/11/2026 · Director: plan v4 en borrador.
  - Incorpora el PR 33 (Codex) y la memoria de la otra cuenta de Steven (`G:\My Drive\claude-memory-2026-11-18`).
  - Pausa A5 y A4b.
  - Abre la Fase P (piloto Zoetry H2), A3d, A4-paquete, T0.4 y T0.5.
  - Fase B: estilo Plano sellado elegido y Vue autorizado.
  - Ramas reducidas a main + plan + fase A + fase B, con respaldo en bundle `C:\Users\Steve\CATDIC-RESPALDOS\ramas-2026-11-19.bundle`.
- 19/11/2026 · Steven: "Apruebo y súbelo" → v3 aprobada con D10–D14; se reanudan las fases A y B.
- 19/11/2026 · Director: plan v3. Incorpora la instrucción de Steven del PR 31 (organización aprobada, pantallas de B1, indicadores, skills por momento, referencias, criterios de aceptación) y el resultado de A1. Nueva Fase D para los datos que el tablero nuevo necesita del backend. Abre D10–D15. Las fases A y B siguen detenidas hasta que Steven apruebe esta versión.
- 17/11/2026 · Steven: prioridad total a GPR; los frentes de CATDIC-WEB quedan detenidos.
- 16/11/2026 · Director: lanzados el Líder de la Fase A (`fase-a`, local_46deab67-ae1c-4dca-bfca-6f212dba54b4) y el de la Fase B (`fase-b`, local_2cc916eb-b786-4d9e-89da-18e171df236c), Opus, worktrees desde `claude/etapa5-plan`. Puertas pendientes: A1 (reconocimiento) y B1 (maquetas).
- 16/11/2026 · Director: T0.1 hecha. Respaldo en `C:\Users\Steve\CATDIC-RESPALDOS\etapa5-2026-11-16` (planes locales, skills, BD) y en `git stash` ("respaldo-etapa5-2026-11-16"). Los 4 archivos locales de `PLANES/` eran superconjuntos de `origin/main` (Evaluaciones 5–13 de la Etapa 2, 23 de la Etapa 3 y decisiones de Steven sin subir): se rescatan en la rama `claude/etapa5-plan`. Checkout principal en `main` = `b5f7d26`.
- 16/11/2026 · Steven aprueba el plan con las propuestas.
- 16/11/2026 · Director: plan v2. Steven decide sin llave y sin pago adicional; la Fase A pasa a preparar → leer con Claude Code → importar con anclaje. Sin sesiones lanzadas.
- 16/11/2026 · Director: plan en BORRADOR; lectura hecha sobre `origin/main` `b5f7d26`.
