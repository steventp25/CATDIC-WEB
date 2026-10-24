# Evaluación Codex — Etapa 2, T6n-b

**Cambio evaluado:** commit `a8de848` (`claude/etapa2-t6nb-lector-plano`).

**Veredicto: BLOQUEADO por la suite global.** Las pruebas específicas del lector pasan, pero la suite completa de esta rama termina con 17 fallos en `tests/test_stp_mived.py`; el criterio del evaluador exige la suite completa en verde. El commit T6n-b solo cambia `BACKEND/plano/lector_plano.py` y `BACKEND/tests/test_lector_plano.py`, así que los fallos aparecen en un módulo que no forma parte de este diff. No se concluye que T6n-b los haya causado; se deja constancia de que no se pudo certificar la rama con la suite global en verde.

## Alcance y criterios

- [x] El diff contiene solo el lector y sus pruebas.
- [x] Las pruebas específicas del lector pasan: `24 passed`.
- [ ] Suite completa en verde: `640 passed, 17 failed, 3 warnings`.
- [x] La lectura de PDF acepta una ruta o un documento abierto; las pruebas comprueban que no se cierre el documento recibido y que los archivos abiertos por ruta se cierren.
- [x] Las nuevas notas de modificación reconocen `AJUSTADA`, `CORRECCIÓN` y `CAMBIO DE`; `CAMBIO DE` se marca con confianza baja.
- [x] El título de planta se clasifica sin deducir nivel ni hoja.
- [?] La detección de líneas en globos reales: las pruebas cubren líneas de ejes sintéticas y llamadas circuladas sin líneas; falta validación contra una colección real de planos en T6n-c.

## Pruebas ejecutadas

- `python 3.14 -m pytest BACKEND/tests/test_lector_plano.py -q` → `24 passed in 2.61s`.
- `python 3.14 -m pytest -q` desde `BACKEND` en el worktree T6n-b → `640 passed, 17 failed, 3 warnings in 32.86s`, código de salida `1`. Los 17 fallos están en `tests/test_stp_mived.py`.

El lanzador `py -3.14` no está disponible en esta sesión; se usó el ejecutable Python 3.14 instalado en Windows. Una primera ejecución global desde la raíz del worktree no resolvió imports; el resultado citado arriba corresponde a la repetición desde `BACKEND`, tal como indica `COLABORACION.md`.

## Bloqueantes y observaciones

- **Bloqueante de certificación:** reparar o explicar los 17 fallos globales de STP y volver a ejecutar la suite antes de considerar T6n-b aprobado. Los fallos están fuera del diff de T6n-b.
- **Observación:** la detección geométrica de la línea de eje se probó con dibujos sintéticos, pero debe contrastarse con hojas reales. T6n-c registra esa comprobación en P16.
- No se observaron datos de ingeniería añadidos, cambios de base de datos, PDFs ni archivos de Dropbox modificados en el diff de T6n-b.

