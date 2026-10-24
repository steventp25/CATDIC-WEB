# Etapa 2 — T6n-c: lector frente al vectorial de Torre P16

**Resultado: Losa E-9 localizada en el PDF.** El lector reconoce la hoja estructural de entrepiso E9 y la búsqueda textual confirma que en esa misma página está la tabla de losa aligerada E9 con una fila `L9`. El extractor de acero actualmente no interpreta esa variante de tabla.

## Fuente y método

- Archivo leído: `C:\Users\Steve\CATDIC Dropbox\SUPERVISION\EN CURSO\PROYECTO P16\ARCHIVO DEL CLIENTE\Nueva carpeta\PLANOS ESTRUCTURALES P16 PDF 26-09-2024 SIN SELLOS.pdf`.
- Se abrió en modo de lectura con PyMuPDF; no se guardó, anotó ni alteró el PDF. No se modificó la base de datos ni se importaron datos de diseño.
- Integridad antes y después de la lectura: SHA-256 `56699cc2e0ec25ad589f4707d99ecab06d5a4b960353c8b7617a3993bdfe9082` en ambos casos.
- Inventario leído: 17 páginas y 14 714 palabras extraíbles. La página 10 contiene 24 723 objetos vectoriales según PyMuPDF.
- Código contrastado: lector de `a8de848` (`claude/etapa2-t6nb-lector-plano`).

## Evidencia de ubicación

- El índice del lector devuelve, para la página 10 del archivo, el título `PLANTA ESTRUCTURAL DE ENTREPISO E9`, clasificado como `planta`.
- En esa página el texto del plano incluye el encabezado `TABLA DE LOSA ALIGERADA (E9)` y la fila identificada `L9`.
- El índice no identificó el número impreso de la hoja: `hoja = "pendiente de verificar"`. Por eso el resultado verificable aquí es **página 10 del PDF**, no un número de lámina.
- La función `tabla_acero_losa(documento, 10)` devolvió `None`. La razón observable es que el lector busca el ancla `TABLA DE ACERO EN LOSA`, mientras que este plano rotula la tabla `TABLA DE LOSA ALIGERADA (E9)`.

## Conclusión y siguiente decisión

La ubicación de Losa E-9 queda establecida mediante el título impreso de la hoja y el rótulo explícito de la tabla. La extracción de sus datos de diseño **no queda validada**: esta variante requiere un lector de tabla específico y confirmación contra la geometría/celdas del vectorial. No se copió ni interpretó ningún valor estructural, no se asignaron ejes y no se cargó la losa en la base de datos.

Para continuar con importación haría falta extender el lector para esta tabla, probarlo con el PDF y mantener los datos como pendientes hasta la revisión/confirmación prevista por el flujo del sistema.

