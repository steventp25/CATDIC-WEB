# Etapa 3 · T2 — Reconocimiento del PDF de visita (solo lectura)

Fecha: 23/10/2026. Autor: Ejecutor (Claude Code). Para: Planificador, que ajusta T3 con este informe.

## Alcance y método
- Se abrieron **en solo lectura** con PyMuPDF 2.0 (`import pymupdf`) tres PDF de visita de Terra Living. No se guardó, copió ni extrajo ninguna foto; el repositorio no recibió imágenes.
- Rutas (`C:\Users\Steve\CATDIC Dropbox\SUPERVISION\EN CURSO\TERRA LIVING\LEVANTAMIENTO\VISITA A OBRA\`):
  - #17 `17. COMPLETIVO VERTICALES S-4 28-09-2026\VERTICALES S-4 COMPLETIVO.pdf`
  - #18 `18. LOSA Y VIGA ENTREPISO S-4 COMPLETIVO 02-10-2026\Losa y viga entrepiso 4 completivo (1).pdf`
  - #20 `20. LOSA SOTANO 3 PARCIAL 15-10-2026\Losa S-3 parcial.pdf`
  - La #19 no tiene PDF (duda `archivos_json`), por eso se usó la #17 (ajuste del planificador).
- Qué se leyó: estructura del PDF (páginas, imágenes, texto con posición, fuente y tamaño). **No se miró el contenido visual de las fotos** (no hay OCR ni visión): lo que está escrito *dentro* de una foto no se pudo conocer.
- Los scripts de inspección quedaron fuera del repo (scratchpad de la sesión).

## Resumen comparativo

| | #17 Verticales S-4 completivo | #18 Losa y viga entrepiso 4 completivo | #20 Losa S-3 parcial |
|---|---|---|---|
| Peso del archivo | 4 572 622 B (4,4 MB) | 327 184 403 B (312 MB) | 26 942 481 B (25,7 MB) |
| Páginas | 14 | 70 | 72 |
| Tamaño de página (pt) | 612 × 792 (Carta) | 595 × 841 (A4) | 595,3 × 841,9 (A4) |
| Generador (metadatos) | iOS 27.0, Quartz PDFContext | iOS 26.5.2, Quartz PDFContext; pie "Generado por 'Report & Run'" | sin generador en los metadatos (PDF 1.7) |
| Imágenes por página | 2 (logo 512×512 + foto) | 2 (logo 150×150 + foto) | 1 (solo la foto) |
| Foto (px) | 768 × 1024 (14) | 4032 × 3024 (68) y 3840 × 2160 (2) | 768 × 1024 (58) y 1024 × 768 (14) |
| Peso medio por foto (stream) | 176 251 B (mín. 30 666 es el logo; máx. 383 262) | 2 340 626 B (mín. 8 885 es el logo; máx. 5 782 173) | 372 570 B (mín. 225 179; máx. 499 958) |
| Resolución efectiva de la foto en la página | ≈ 135 ppp | ≈ 582 ppp | ≈ 111 ppp |
| Tiempo de apertura (`pymupdf.open`) | 0,007 s | 0,001 s | 0,001 s |
| Tiempo de recorrer todas las páginas (texto + imágenes + pesos) | 0,31 s | 17,2 s | 1,29 s |
| Anotaciones | 0 | 0 | 0 |
| Texto extraíble | **Sí** | **Sí** | **Sí** |

Notas:
- La apertura es casi instantánea incluso en el PDF de 312 MB: PyMuPDF no lee las imágenes hasta que se piden. El costo real está en recorrer o decodificar las fotos (17 s para leer las 70 páginas de la #18 con toda su información; no se midió la decodificación a píxeles).
- Cada página es **una foto** (más el logo del generador en #17 y #18). Una foto nunca comparte página con otra.

## Respuestas por visita

### Estructura común de la página
Verificada en las tres:
- Cabecera con datos de la visita (empresa/contacto/grupo/título y "Nro. de elementos" = número de páginas = número de fotos).
- A la izquierda de la foto, un número entre paréntesis: `(1)`, `(2)`, … igual al número de página.
- La foto.
- Debajo de la foto, un bloque de texto: opcionalmente la **etiqueta** (negrita, 12 pt) y siempre `Creado el: …` (negrita, 10 pt). Una línea libre adicional (10 pt, regular) puede aparecer debajo, ver "notas".
- Pie con `Id. de doc.` y `página N de M`.

### ¿Las etiquetas son texto extraíble y dónde están?
**Sí, en las tres.** Son texto vectorial (no dibujado dentro de la imagen), en el bloque inmediatamente **debajo** de la foto, alineado al borde izquierdo de la foto (x ≈ 56 pt).
- #17: la etiqueta es un bloque propio de 12 pt (p. ej. `Mh4`, bbox [56,0 · 651,8 · 80,7 · 666,1]) y `Creado el: …` va en otro bloque debajo (y ≈ 672).
- #18: etiqueta de 12 pt en su bloque propio (p. ej. `Pórtico eje 4 tramos MC-D`, bbox [56,0 · 686,4 · 208,7 · 700,7]) y `Creado el: vie, 2/10/2026` debajo (y ≈ 706,7).
- #20: etiqueta y `Creado el:` dentro del **mismo** bloque (p. ej. `P eje 1 Creado el:  15/10/2026 09:56`; la etiqueta va en 12 pt y la fecha en 10 pt). Para separar etiqueta de fecha hay que trabajar con los *spans* (tamaño de letra) o cortar en `Creado el:`.
- La posición vertical de la etiqueta depende del alto de la foto (foto vertical o apaisada); no es una coordenada fija. La referencia estable es: *texto que empieza justo debajo del borde inferior de la imagen*.

### Cómo se distingue una foto con etiqueta de una sin etiqueta
- **Con etiqueta:** debajo de la foto hay un bloque de 12 pt (negrita) antes de `Creado el:`.
- **Sin etiqueta:** el único texto debajo de la foto es `Creado el: …` (10 pt). En esos casos el bloque ocupa una sola línea (alto ≈ 12–14 pt) en vez de dos.
- Conteo (etiqueta / sin etiqueta): #17 = 3 / 11; #18 = 30 / 40; #20 = 31 / 41.
- Consistente con la regla M1 (CLAUDE.md §4.7): una foto con etiqueta abre el elemento y las siguientes sin etiqueta le pertenecen.
- **Excepción a decidir:** la primera foto de la #18 (p. 1, 2) y de la #20 (p. 1) **no tiene etiqueta**, así que no hay elemento al que asignarla. Sin adivinar, esas fotos quedan sin elemento ("pendiente de verificar").

### Orden de lectura de las fotos
- El orden del log es el **orden de las páginas** (y el número `(n)` a la izquierda de cada foto). No hay fotos fuera de orden dentro del PDF.
- La hora `Creado el:` **no es monótona** en la #20 (p. 41 = 10:27, p. 42 = 11:02, p. 43 = 10:29, p. 46 = 10:32, p. 47 = 10:30). No debe usarse para ordenar: manda el orden de páginas.

### Ejemplos LITERALES de etiquetas (copiados tal cual del texto del PDF)
- #17 (3 etiquetas): `Mh4` (p. 1) · `Mh1 pantalla eje 3` (p. 7) · `Pantalla eje B` (p. 8).
- #18 (30 etiquetas): `Pórtico eje 4 tramos MC-D` (p. 3) · `Tramo D-B` (p. 8) · `Tramo B-A` (p. 11) · `Tramo A - MC` (p. 14) · `Pórtico eje 3` (p. 15) · `MC- A` (p. 16) · `Tramo B- C` (p. 20) · `Tramo D- MC` (p. 26) · `Pórtico eje D` (p. 29) · `Tramo 3-4` (p. 30) · `Pórtico eje B` (p. 36) · `Pórtico eje A` (p. 42) · `Tramo 4-3` (p. 46) · `Losa 13` (p. 49) · `Losa 17` (p. 52) · `Muro perimetrale` (p. 63) · `Losa 12` (p. 70).
- #20 (31 etiquetas): `P eje 1` (p. 2) · `Tramo mc -A` (p. 3) · `Tramo A- C` (p. 6) · `Tramo B -D` (p. 7) · `P eje 2 tramo E-D` (p. 10) · `Tramo A-mc` (p. 18) · `As infiernos 5-3/4 continuaron armado` (p. 19) · `P eje A tramo 2-1` (p. 20) · `Tramo mc - 1` (p. 27) · `P eje C corregir Peralte de 0.60 a 0.70m` (p. 35) · `L5` (p. 43) · `L8` (p. 46) · `L12 arranque vaciado a 1m` (p. 50) · `Garantizar recubrimiento` (p. 52) · `L 3` (p. 54) · `L 11` (p. 66) · `Mc eje A’ Tramo 3-4’` (p. 69; la prima es el carácter `’` U+2019, no la comilla recta `'`).
- **Ninguna de estas tres visitas trae etiquetas con el patrón `C1 A4` (ID + ejes).** Las etiquetas son texto libre del técnico: mezclan tipo y eje (`Pórtico eje 4 tramos MC-D`), solo el ID (`L5`, `Losa 13`), solo el tramo (`Tramo D-B`, `MC- A`) o instrucciones (`Garantizar recubrimiento`).

### Variaciones de escritura observadas (relevantes para interpretar ejes y tramos)
- Espacios irregulares alrededor del guion: `Tramo A - MC`, `Tramo B- C`, `Tramo mc -A`, `Tramo B -D`, `MC- A`, `L 3`, `L 11`.
- `MC`/`mc`/`Mc` (muro de contención) en mayúsculas y minúsculas.
- Eje con prima tipográfica: `A’` (U+2019).
- Palabras que no son ejes ni ID: `Muro perimetrale`, `As infiernos 5-3/4 continuaron armado`.
- Un tramo puede estar en etiqueta de un pórtico (`Pórtico eje 3`) y los tramos siguientes en etiquetas aparte (`Tramo A-B`, `Tramo B- C`…) sin repetir el eje del pórtico: el eje del pórtico al que pertenece cada `Tramo …` no está en esa misma etiqueta; **no se puede saber sin adivinar** más allá de que viene después del pórtico en el log.

### ¿Hay medidas escritas?
- Como texto del PDF, solo en **texto libre** y en la #20:
  - etiqueta de p. 35: `P eje C corregir Peralte de 0.60 a 0.70m`;
  - nota de p. 35 (debajo de `Creado el:`, 10 pt regular, bbox [56,0 · 639,3 · 471,2 · 652,9]): `Conforme. Ing de obra se realizó un cambio en el peralte de 0.70 a 0.60 debido a espacio.`;
  - etiqueta de p. 50: `L12 arranque vaciado a 1m`;
  - nota de p. 52: `1 cm más de eso 0.26`.
- Las medidas están **mezcladas con instrucciones y comentarios** en lenguaje natural, sin unidades ni campos fijos, y la etiqueta de la p. 35 contradice en sentido a la nota (0.60→0.70 vs. 0.70→0.60): **no se pueden convertir en dato sin interpretar**. Regla de Oro #1: quedarían como "pendiente de verificar"/duda.
- En #17 y #18 no hay medidas como texto.
- Medidas escritas **dentro de la imagen** (cinta métrica, pizarra, marcas a mano) no se pudieron determinar: no se miró el contenido de las fotos.

### Notas (texto libre debajo de `Creado el:`)
Solo en la #20, dos casos (p. 35 y p. 52, ver arriba). Son bloques de 10 pt regular, con inicio alineado a la izquierda (x = 56) y debajo del bloque de etiqueta. Tendrían que tratarse como observaciones (campo distinto de la etiqueta).

### Datos de cabecera útiles para la visita
- #17: `Título: VERTICALES S-4 COMPLETIVO`, `Nro. de elementos: 14`, `Creado el: 28/09/2026 11:02`.
- #18: `Título: Losa y viga  entrepiso 4 completivo` (dos espacios entre "viga" y "entrepiso"), `Nro. de elementos: 70`, `Creado el: vie, 2/10/2026` (formato distinto: día de la semana y `D/M/AAAA` sin cero).
- #20: `Título: Losa S-3 parcial`, `Nro. de elementos: 72`, `Creado el: 15/10/2026 09:50`.
- "Nro. de elementos" cuenta **fotos/páginas**, no elementos de ingeniería. Coincide con el número de páginas en las tres.
- Las fechas de cabecera tienen formatos distintos entre generadores (#18 vs. las otras dos): el lector debe tolerarlos o marcar pendiente.

## Qué no se pudo saber (sin adivinar)
- Qué elemento de diseño (ID del plano) corresponde a cada etiqueta: eso no está en el PDF de la visita (la Capa 1 sale solo de los planos, §4.1).
- El contenido visual de las fotos (medidas escritas dentro de la imagen, nitidez, orientación real).
- Si las fotos sin etiqueta del inicio del PDF (#18 p. 1–2; #20 p. 1) pertenecen a un elemento anterior no incluido o son de contexto.
- Si el *Report & Run* de #18 y el generador de #20 mantienen el mismo diseño de página en otras visitas (solo se vieron tres PDF; #19 sin PDF).
- La decodificación a píxeles (memoria/tiempo de reducir 70 fotos de 4032×3024): solo se midió el recorrido de la estructura.

## Consecuencias para T3 (propuestas; las decide el Planificador)
1. **Orden:** usar el orden de páginas del PDF; no usar la hora de `Creado el:`.
2. **Etiqueta:** tomar el texto de 12 pt (negrita) situado entre el borde inferior de la imagen principal y `Creado el:`; si solo hay `Creado el:`, la foto es "sin etiqueta" y se agrega al elemento abierto. La imagen principal es la de mayor tamaño de la página; el logo (512×512 o 150×150) se ignora.
3. **Primeras fotos sin etiqueta:** sin elemento al que asignarlas → duda `DUDA_BLOQUEANTE` con `visita_id`, no inventar elemento.
4. **Ejes y tipos:** las etiquetas son texto libre; solo se interpretan las que `interpretar_eje_de_visita` puede leer sin adivinar (`A1`, `1A`). El resto (`Pórtico eje 4 tramos MC-D`, `Tramo B- C`, `L5`) queda como texto original + "pendiente de verificar" hasta que la Etapa 2 y la Mesa de Dudas permitan cruzarlo con el plano.
5. **Notas y medidas:** guardar el texto libre tal cual como observación; no convertirlo en número.
6. **Rendimiento:** abrir el PDF es instantáneo; la reducción a 1000×1000/q72 es el costo (hasta 70 fotos de ≈ 5 MB en la #18). Procesar página a página sin cargar todo el documento en memoria.
7. **Cabeceras:** tolerar el formato de fecha de la #18 (`vie, 2/10/2026`) o marcarlo pendiente; la fecha oficial de la visita sigue saliendo de la carpeta o del PDF según la Etapa 1.
