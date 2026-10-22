# Decisiones operativas de Steven — 22/10/2026

Estas decisiones mandan sobre propuestas anteriores de planificación. Se registran antes de iniciar nuevos módulos.

## D1 — Varios usuarios

CATDIC-WEB debe prepararse para varios usuarios.

La primera instalación puede funcionar en una computadora anfitriona de CATDIC, con Dropbox sincronizado y el backend ejecutándose allí. Los demás usuarios entrarán desde sus navegadores a la dirección de esa computadora en la red local.

Consecuencias para las siguientes etapas:

- No se deben amarrar pantallas, rutas ni datos al usuario `Steve`.
- La selección y lectura de carpetas de Dropbox ocurre en la computadora anfitriona, porque allí están los archivos reales.
- Las acciones importantes deben conservar auditoría: quién ejecutó la acción, cuándo y qué cambió.
- SQLite sirve para el arranque local; antes de uso simultáneo intensivo se planificará el paso a una base de datos compartida apta para varios usuarios.

## D2 — Acceso directo

El usuario debe abrir el sistema desde un acceso directo, sin comandos ni abrir `index.html`.

La ruta de producto será un único servidor local que entregue interfaz y API desde la misma dirección. El acceso inicial previsto es `http://localhost:8000`; en red local cambiará a la dirección de la computadora anfitriona.

El PR `codex/arranque-local` contiene el lanzador inicial `INICIAR_CATDIC.bat` y el frontend servido por FastAPI.

## D3 — Orden de negocio

La prioridad es terminar primero **Supervisión Estructural**:

1. estabilizar acceso y sincronización;
2. importar datos de diseño de Supervisión;
3. construir los formatos STP-MIVED, MIVED FI y CATDIC-STP;
4. después continuar con Levantamiento e informes HV.

La Etapa 4 no inicia hasta que Steven indique que Supervisión tiene el alcance necesario.

## D4 — Carpetas de visitas

El sistema tendrá dos maneras de ubicar una visita:

1. **Ruta estándar:** leer las carpetas organizadas según la estructura CATDIC definida en AGENTS.md §5.1.
2. **Ruta elegida por el usuario autorizado:** un botón permitirá indicar la carpeta exacta de visitas cuando un proyecto no siga todavía la estructura estándar.

La ruta elegida se validará antes de leerla y se guardará con auditoría. No se moverán, renombrarán ni borrarán archivos de Dropbox.

Para uso multiusuario, la ruta elegida debe existir y ser legible desde la computadora anfitriona. No se asumirá que una carpeta de la computadora personal de otro usuario está disponible para el servidor.

## Pendiente para decidir más adelante

- Qué personas tendrán permiso de registrar o cambiar rutas de carpetas.
- Si la primera versión multiusuario será solo red local o también acceso remoto por internet.
- Qué pantallas de trabajo diario deben construirse primero: tablero, visitas, Mesa de Dudas, importación de diseño, generación de informes u otras.
- En qué momento pasar de SQLite a una base de datos compartida.
