# Evaluación Codex — Etapa 2, T6n-b

**Cambio evaluado:** commit `a8de848` (`claude/etapa2-t6nb-lector-plano`).

**Veredicto: BLOQUEADO.** Hay un defecto en la agrupación geométrica de ejes y la suite completa tampoco queda en verde.

## Alcance y criterios

- [x] El diff contiene solo el lector y sus pruebas.
- [x] Las pruebas específicas del lector pasan: `24 passed`.
- [ ] Suite completa en verde: `640 passed, 17 failed, 3 warnings`.
- [x] La lectura de PDF acepta una ruta o un documento abierto; las pruebas comprueban que no se cierre el documento recibido y que los archivos abiertos por ruta se cierren.
- [x] Las nuevas notas de modificación reconocen `AJUSTADA`, `CORRECCIÓN` y `CAMBIO DE`; `CAMBIO DE` se marca con confianza baja.
- [x] El título de planta se clasifica sin deducir nivel ni hoja.
- [ ] Todos los globos alineados se evalúan como un grupo: en `lector_plano.py:371`, volver a agrupar con cubetas de 3 pt puede dividir una misma fila/columna; un subgrupo con línea podría salir aunque otro globo alineado no tenga línea.
- [?] La detección de líneas en globos reales: las pruebas cubren líneas de ejes sintéticas y llamadas circuladas sin líneas; falta validación contra una colección real de planos en T6n-c.

## Pruebas ejecutadas

- `python 3.14 -m pytest BACKEND/tests/test_lector_plano.py -q` → `24 passed in 2.61s`.
- `python 3.14 -m pytest -q` desde `BACKEND` en el worktree T6n-b → `640 passed, 17 failed, 3 warnings`, código de salida `1`: 16 fallos de `tests/test_stp_mived.py` porque Playwright no encuentra Chromium y 1 de `tests/test_parser_visitas.py::test_lista_coincide_con_dropbox_si_esta_disponible` porque Dropbox contiene una carpeta adicional a la lista esperada.

El lanzador `py -3.14` no está disponible en esta sesión; se usó el ejecutable Python 3.14 instalado en Windows. Una primera ejecución global desde la raíz del worktree no resolvió imports; el resultado citado arriba corresponde a la repetición desde `BACKEND`, tal como indica `COLABORACION.md`.

## Bloqueantes y observaciones

- **Bloqueante técnico, `BACKEND/plano/lector_plano.py:371`:** el agrupamiento final de globos mediante `round(centro/3)` puede separar globos alineados en cubetas diferentes. El programa puede emitir el subgrupo cuyos globos sí tienen línea de eje aunque otro globo de esa misma fila/columna no tenga línea, en contra del criterio de exigir el grupo completo. Agrupar y verificar cada grupo alineado como una unidad; añadir una prueba con centros a ambos lados del límite de cubeta.
- **Bloqueante de certificación:** la suite global termina con 17 fallos. Los 16 fallos STP reportan que Playwright no encuentra Chromium; el fallo de parser depende de que la carpeta de Dropbox cambie respecto de la lista esperada. Aunque no están en los archivos del diff T6n-b, deben quedar explicados o aislados para que la suite global pueda certificarse.
- **Observación:** la detección geométrica de la línea de eje se probó con dibujos sintéticos, pero debe contrastarse con hojas reales. T6n-c registra esa comprobación en P16.
- No se observaron datos de ingeniería añadidos, cambios de base de datos, PDFs ni archivos de Dropbox modificados en el diff de T6n-b.

