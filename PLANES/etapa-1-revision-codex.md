# Revisión cruzada de Codex — Etapa 1

**Rango revisado:** `61e6ecb...fdc9f44`  
**Fecha:** 22/10/2026  
**Revisor:** Codex  
**Veredicto: BLOQUEADO**

## Motivo del bloqueo

No pude reproducir las dos verificaciones operativas obligatorias en la PC:

- El terminal de PowerShell falla antes de ejecutar comandos por una restricción de registro de Windows. Por eso no fue posible ejecutar `cd BACKEND && py -3.14 -m pytest -q`.
- El tablero indicado, `http://localhost:5510`, responde `ERR_CONNECTION_REFUSED`. No fue posible comprobar el POST real ni la presentación de la cola.

No hay bloqueante de código encontrado en la revisión estática. Cuando el entorno local vuelva a estar disponible, esta revisión se puede cerrar ejecutando:

```powershell
cd C:\Users\Steve\OneDrive\Desktop\CATDIC-WEB\BACKEND
py -3.14 -m pytest -q
py -3.14 -c "import main"
```

Y levantando el servidor del tablero en el puerto 5510 para probar:

1. carga inicial de `/api/dashboard`;
2. botón **Sincronizar desde Dropbox**;
3. resumen de sincronización y 22 visitas;
4. botón **Procesar Cola** deshabilitado.

## Revisión estática

- [x] Regla de Oro #1: el parser toma fecha y clase solo del nombre de carpeta o del PDF; los valores no legibles quedan como `pendiente de verificar` y generan `DUDA_BLOQUEANTE`.
- [x] Dropbox: `sync/escaner_dropbox.py` usa lectura de directorios y `stat`; no hay operaciones de escritura, movimiento, borrado ni apertura de PDFs.
- [x] P3 estricta: `sincronizador.py` requiere un único STP de la misma fecha y clase. STP sin clase, visita Mixta o candidatos ambiguos pasan a `Con dudas`.
- [x] Idempotencia: el upsert usa `(proyecto_id, ruta_carpeta)`; los estados avanzados y respuestas de Mesa de Dudas se preservan.
- [x] Etapa 3: la corrección P3 evita visitas cuyo `origen_datos_json.estado` no es del sincronizador. El contrato del generador sigue documentado.
- [x] Procesar Cola: backend responde 409 sin tocar la BD y el botón está deshabilitado en el frontend.
- [x] Formatos: esta etapa no genera PDFs ni firmas; los errores de formato no aplican.
- [x] Archivos prohibidos: el rango no añade BD, PDFs, fotos, `.env` ni secretos.

## Observaciones no bloqueantes

- [ ] `PLANES/README.md` todavía describe a Gemini como auditor externo. `COLABORACION.md` ya establece correctamente la revisión cruzada Claude Code ↔ Codex. Conviene actualizarlo en una tarea documental.
- [ ] La etapa conserva avisos de obsolescencia de `@app.on_event` y el aviso de Starlette sobre `httpx`; no afectan la funcionalidad actual.
- [ ] La decisión sobre un STP de la clase contraria sigue pendiente de Steven y está registrada en `PLANES/etapa-1-evaluacion.md`.

## Resultado esperado para desbloquear

- `py -3.14 -m pytest -q` desde `BACKEND` debe informar **482 passed** o más, sin fallos.
- `py -3.14 -c "import main"` debe finalizar correctamente.
- El tablero debe volver a responder en `http://localhost:5510` y la sincronización debe mostrar 22 visitas sin errores de fecha visibles.
