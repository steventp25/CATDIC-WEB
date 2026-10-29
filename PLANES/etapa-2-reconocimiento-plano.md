# Etapa 2 · T3n — Reconocimiento del PDF vectorial (solo lectura)

- Fecha: 24/10/2026 · Ejecutor: Claude Code · Rama `claude/etapa2-t3n-reconocimiento-plano`.
- Fuente leída en SOLO LECTURA: `PLANOS ESTRUCTURALES TERRALIVING.pdf` (41 hojas, 17,7 MB; idéntico a `2026.03.10 - EST - TERRA LIVING.pdf`, mismo tamaño y misma fecha de modificación). Del sellado (`TERRA LIVING -ESTRUCTURALES.pdf`, 39 hojas, escaneo) solo se usaron **miniaturas a ojo**.
- Herramienta: PyMuPDF (la misma del proyecto). Los scripts de la exploración quedaron en el scratchpad de la sesión; **no se copió ningún plano, imagen ni dato del cliente al repositorio**. Donde el plano trae nombres o números de licencia se usan marcadores (`[LICENCIA]`, `[PROPIETARIO]`…).
- Metadatos del PDF: creado con AutoCAD 2023 (`pdfplot16.hdi`), hojas de 2592 × 1728 pt (36 × 24 in); las 33 primeras en horizontal y las 8 últimas (34-41) en vertical con `rotation = 270`.

## Resumen para quien decide

| Pregunta | Respuesta corta |
|---|---|
| ¿El vectorial es texto real? | **Sí.** 206 422 caracteres y 31 084 trazos de texto; los 31 084 son visibles (negro, opacidad 1, sin texto invisible). |
| ¿Hay capas ocultas? | **No por defecto**: 83 capas, las 83 encendidas, `/OFF` vacío, sin `/Usage`. No hay "texto que solo esté en capas ocultas". |
| ¿Se leen las tablas como texto con coordenadas? | **Sí** (zapata de muro, tabla de acero en losa, f'c por nivel…), pero hay que reconstruir las filas por posición: no son objetos de tabla. |
| ¿Los IDs y los ejes en planta son texto? | **Sí** (`C5`, `L13`, `V-40X60`, `MH3`; ejes `1…4` y `A…D`), con ambigüedades que se explican en el punto 4. |
| ¿Qué dos hojas sobran frente al sellado? | **Páginas 9 y 10 del vectorial** (hojas `08/36` DETALLE DE SEPTICO y `09/36` DETALLE DE CISTERNA), comparadas a ojo con miniaturas. |
| Rapidez | Apertura 0,002 s; texto de las 41 hojas 1,1 s; rasterizar una hoja a 150 ppp ≈ 0,15 s. |

## 1. Título impreso de cada hoja y su número "/36"

El **cajetín** (franja derecha de la hoja) NO trae el título de la hoja: trae empresa, propietario, proyectista y, abajo, el **número `NN/36`**. El **título impreso** va **bajo cada dibujo**, dentro de la hoja; una hoja puede traer varios dibujos y varios títulos. Por eso la tabla lista los títulos que aparecen en cada hoja.

Hallazgo importante: **la numeración llega a `40/36`**. Las hojas 34 a 41 llevan `33/36 … 40/36`; el denominador del cajetín (`/36`) quedó desactualizado frente a las 41 hojas del archivo. La página 1 es la hoja `00/36`.

| Pág. | Nº hoja | Título(s) impreso(s) en la hoja | Niveles que cubre |
|---|---|---|---|
| 1 | 00/36 | CRITERIOS DE DISEÑO ESTRUCTURAL | general |
| 2 | 01/36 | ESPECIFICACIONES GENERALES DE MATERIALES I | general |
| 3 | 02/36 | ESPECIFICACIONES GENERALES DE MATERIALES II | general |
| 4 | 03/36 | ESPECIFICACIONES GENERALES DE ARMADO DE REFUERZO I | general |
| 5 | 04/36 | ESPECIFICACIONES GENERALES DE ARMADO DE REFUERZO II | general |
| 6 | 05/36 | DETALLES DESACOPLE DE MUROS DE CERRAMIENTO NO PORTANTES (+ muros de mampostería, paneles) | general |
| 7 | 06/36 | PLANTA ESTRUCTURAL DE FUNDACIONES · PLANTA ESTRUCTURAL REPLANTEO DE FUNDACIONES | fundaciones |
| 8 | 07/36 | PLANTA EST DE FUNDACIONES INDICATIVA DE ACERO ADICIONAL SUPERIOR · … EN DROPS | fundaciones |
| 9 | 08/36 | DETALLE DE SEPTICO | fundaciones (séptico) |
| 10 | 09/36 | DETALLE DE CISTERNA (+ DETALLE TIPICO SOLAPE ACERO EN VIGAS) | fundaciones (cisterna) |
| 11 | 10/36 | SECCION DE FUNDACIONES PROXIMA A EJE 4 · … EJE 2 | fundaciones |
| 12 | 11/36 | SECCION DE FUNDACIONES PROXIMA A EJE A · … EJE 1 | fundaciones |
| 13 | 12/36 | SECCION DE FUNDACIONES A-A' · … PROXIMA A EJE D | fundaciones |
| 14 | 13/36 | COLUMNA C1 · C2 · C3 (cada una con rótulos `FUNDACIONES @ E-2`, `FUNDACIONES @ E-3`, `E-3 @ E-8`, `E-2 @ E-8`, `E-13`) | fundaciones a E-13 |
| 15 | 14/36 | COLUMNA C4 · C5 (`FUNDACIONES @ E-3`, `E-3 @ E-8`, `E-8 @ E-12`, `E-12 @ TECHO`, `E-14`) | fundaciones a techo |
| 16 | 15/36 | MURO MH3 · MH1 · MH4 (`FUNDACIONES @ E-2`, `E-2 @ E-9`, `E-9 @ TECHO`, `E-15`, `FUNDACIONES @ E-1`) | fundaciones a techo |
| 17 | 16/36 | MURO MH2 (`FUNDACIONES @ E-1`, `E-1 @ E-2`, `E-2 @ E-8`, `E-8 @ TECHO`, `E-16`) + tabla de elementos de borde + SECCION VIGA DE ACOPLE | fundaciones a techo |
| 18 | 17/36 | RAMPA (arranque, descansos) y MURO MH2 (`E-17`); sin otro título de hoja | escaleras / rampas |
| 19 | 18/36 | PLANTA ESTRUCTURAL DE LOSA DE PISO (SOTANO S7) | S7 |
| 20-25 | 19-24/36 | PLANTA ESTRUCTURAL DE SOTANO S6, S5, S4, S3, S2, S1 (una por hoja) | S6 … S1 |
| 26 | 25/36 | PLANTA ESTRUCTURAL PRIMER NIVEL | nivel 1 |
| 27 | 26/36 | PLANTA ESTRUCTURAL NIVEL 2 | nivel 2 |
| 28 | 27/36 | PLANTA ESTRUCTURAL NIVEL 3 | nivel 3 |
| 29 | 28/36 | PLANTA ESTRUCTURAL NIVEL 4@8 | niveles 4 a 8 |
| 30 | 29/36 | PLANTA ESTRUCTURAL NIVEL 9@17 | niveles 9 a 17 |
| 31 | 30/36 | PLANTA ESTRUCTURAL NIVEL 18 | nivel 18 |
| 32 | 31/36 | PLANTA ESTRUCTURAL DE TECHO | techo |
| 33 | 32/36 | PLANTA ESTRUCTURAL DE TECHO (segundo dibujo del mismo título) | techo |
| 34-41 | 33-40/36 | PORTICO ESTRUCTURAL EJE 1, 2, 3, 4, A, B, D, C (en ese orden; la 40 es el eje D y la 41 el C) | todos los niveles |

Notas de lectura:
- "NIVEL 4@8" y "NIVEL 9@17" se leen como rango "4 a 8" y "9 a 17", igual que `E-3 @ E-8` en las columnas (§4.2). Es la convención de la hoja; conviene que el usuario la confirme.
- **Dos nomenclaturas de nivel conviven**: las plantas se titulan `SOTANO S7…S1`, `PRIMER NIVEL`, `NIVEL 2…18`, `TECHO`, y los detalles de columnas y muros usan `E-1 … E-17` (entrepisos). **No encontré ningún texto que diga qué `E-n` corresponde a qué planta**; sin esa tabla de equivalencia el cruce columna ↔ nivel quedaría *pendiente de verificar*.
- Las hojas 31/36 y 32/36 (págs. 32 y 33) se titulan igual (techo); el texto no dice cuál es cuál sin mirar el dibujo (la página 33 trae solo el núcleo de ascensor y escaleras).

## 2. Capas (OCG / contenido opcional)

- 83 capas (`/OCProperties`). **Las 83 están encendidas** en la configuración por defecto (`/D`), `/OFF` está vacío, no hay `/BaseState`, ni `/AS`, ni `/Usage` (impresión/visualización) en ninguna.
- Consecuencia: **lo que se ve al imprimir es todo lo que hay**; no hay texto que solo exista en capas ocultas. Ejemplos de lo que habría que descartar: **ninguno**. Tampoco hay texto invisible (modo de render 3), blanco ni transparente, ni texto fuera del área de la hoja. (Las páginas 34-41 parecen tener texto "fuera" solo porque `get_texttrace` entrega las coordenadas sin rotar; aplicando `rotation_matrix` ninguno queda fuera, comprobado.)
- El texto vive en 17 capas. Las que más: `TEXTOS` (18 440 trazos), `0` (4 981), `DIMLINE` (2 693), `TEXTOS SECCIONES` (1 456), `DIMENSIONES` (994), `G-ANNO-TTLB` (774, cajetín), `TITULOS` (706), `TEXTOS NOTAS` (418). Los dibujos están en capas de AutoCAD con nombres útiles (`BORDE LOSA`, `EJE VIGA`, `LOSA ALIGERADA`, `ACERO`, `COLUMNAS`, `MUROS`, `INDIC. EJES`, `ZAPATAS`…). Esto sirve para filtrar geometría, pero **el texto de ejes y de IDs no está en una capa exclusiva**: la capa `TEXTO EJES`/`INDIC. EJES` no trae texto en la hoja que probé (p. 26).

## 3. Tablas de aplicación

Se leen como **texto suelto con coordenadas**: cada celda es un trazo; las filas se reconstruyen agrupando por `y` y ordenando por `x`. No hay objetos "tabla". Filas literales (formato `texto [x0,x1]`, y de la fila entre paréntesis; unidades en puntos de la hoja):

**a) Tabla de aplicación de zapata de muro de lindero (p. 6):**
```
(y≈1201) MURO[2185,2208] | B[2224,2229] | h[2252,2257] | Df[2281,2289] | ACERO Ast[2310,2349] | ACERO Asl[2362,2400]
(y≈1219) 6"[2193,2200] | 0.60[2217,2232] | 0.30[2245,2260] | 0.80[2275,2289] | ∅ 3/8" @ 0.15[2302,2352] | 4 ∅ 3/8"[2364,2395]
(y≈1236) 8"[2193,2200] | 0.80[2217,2232] | 0.30[2245,2260] | (Df en la fila anterior: 1.00) | ∅ 3/8" @ 0.10[2302,2352] | 5 ∅ 3/8"[2364,2395]
```
Observación: el valor `1.00` (Df de la 2.ª fila) está desplazado verticalmente (y≈1232) respecto de su fila (y≈1236): **hay que agrupar con tolerancia**, no por igualdad de `y`.

**b) Tabla de acero en losa, con tipos A/B/C (p. 10, hoja de fundaciones):**
```
(y≈236) TIPO DE LOSA | H | Bw1 | Bw2 | h1 | h2 | ACERO INFERIOR CONTINUO (DIR. X / DIR. Y) | L/2 AS. ADIC.
(y≈257) A[2008] | 0.25[2036,2050] | 0.125[2063,2081] | 0.156[2093,2111] | 0.20[2123,2137] | 0.05[2152,2166] | 3∅1/2"[2188,2215] | 3∅1/2"[2244,2270]
(y≈272) B[2008] | 0.25 | 0.125 | 0.156 | 0.20 | 0.05 | 2∅1/2"[2188,2215] | 2∅1/2"[2244,2270]
(y≈287) C[2008] | 0.25 | 0.125 | 0.156 | 0.20 | 0.05 | 3∅3/8"[2188,2215] | 3∅3/8"[2243,2269] | 2∅3/8"[2306,2332]
```

**c) Tabla de acero en losa en las plantas de nivel (p. 26, planta del primer nivel):** mismas columnas; el rótulo `TIPO DE LOSA` y las letras `A`, `B`, `C` están **fuera de la tabla, a la izquierda** (x≈1857-1887), así que se leen como texto aparte.
```
(y≈294) 0.25[1899,1913] | 0.125[1926,1944] | 0.156[1956,1975] | 0.20[1986,2001] | 0.05[2015,2029] | 3∅1/2"[2052,2079] | 3∅1/2"[2108,2134]
(y≈324) 0.25 | 0.125 | 0.156 | 0.20 | 0.05 | 3∅3/8"[2052,2079] | 3∅3/8"[2106,2133] | 2∅3/8"[2170,2197]
```
Observación: **las losas en planta se rotulan `L1…L16`, no `A/B/C`**; el plano no trae en texto la correspondencia `L13 ↔ tipo A/B/C`. Ese cruce no se puede sacar del texto sin adivinar.

**d) Tabla de acero en losa nerviada (p. 26):** `H`, `Bw1`, `Bw2`, `h1`, `h2` y la malla (`MALLA ELECTROSOLDADA CORRUGADA D2.3xD2.3x150x150`, `∅3/8"@0.85`) como texto suelto alrededor de un dibujo, no como filas.

**e) Elementos de borde y pantalla de muros (p. 17):** solo los **encabezados** (`ACERO ELEMENTO DE BORDE`, `ACERO Asv ELEMENTO DE PANTALLA`) y un par de valores sueltos (`5∅1/2" (A.C)`, `0.20`, `0.40`) aparecen como texto; el resto del armado va como llamadas sobre los dibujos de cada muro (`MURO MH2`…).

**f) Columnas (pp. 14-15):** **no hay tabla de columnas**. Cada columna (`C1…C5`) es un dibujo de sección con llamadas de texto, p. ej. `9 EST. +GANCHO`, `∅3/8"@0.10`, `38∅1"`, `7 EST.`, `28∅1"`, dimensiones `0.52`, `0.14`… colocadas junto al dibujo, sin forma tabular.

**g) Otras tablas** (no usadas para Capa 1): longitud de desarrollo y de anclaje (p. 4), resistencias utilizadas (p. 2).

**No hay `Asxi`/`Asyv`** en este plano: las losas usan `ACERO INFERIOR CONTINUO DIR. X / DIR. Y` y `AS. ADIC.`; los muros, `ACERO Asv`.

## 4. Globos de ejes e IDs de elementos en planta

Ejemplo literal de la planta del primer nivel (p. 26), texto con coordenadas:
- **Ejes numéricos**: `4`[390,395] y≈387 · `3`[390,396] y≈609 · `2`[390,396] y≈705 · `1`[390,396] y≈935 (columna de globos a la izquierda).
- **Ejes de letra**: `A`[594,600] · `B`[808,814] · `C`[983,990] · `D`[1114,1121] en y≈1149 (fila de globos abajo).
- **IDs**: columnas `C5`[608,620] y≈398 · `C3`[823,834] · `C1`[1123,1135] · `C2`[1123,1135] y≈939 · `C4`[823,834] y≈962; vigas `V-40X60`[584,592] y≈295, `V-40X70`; losas `L13`[558,570] y≈326 … `L1`[561,569] y≈981 … `L16`; muros `MH3`[992,1011] y≈639, `MH1`, `MH2`, `MH4`; espesores `H=0.20M`, `H=0.25M`; `ASCENSOR`, `ESCALERA #1`, `ESCALERA #2`, `HUECO DE RPH`; cotas entre ejes (`7.88`, `19.40`, `3.40`, `8.13`…).

Cautelas:
- Los globos **sí** son texto, pero **no están marcados como "eje"**: la letra `A` también aparece decenas de veces como marca de apoyo de la losa aligerada (`A`[561,349], `A`[778,349]…). Distinguir el eje real exige usar la posición (fila/columna de globos fuera del dibujo) o el círculo vectorial que lo rodea.
- Los IDs de columna y muro están sueltos en planta; ubicarlos en un cruce de ejes requiere geometría (la caja del elemento), no solo el texto.
- En los pórticos (pp. 34-41) los ejes y niveles también son texto.

## 5. Rótulos de detalle, notas y adendas

- Llamadas de sección: `S-1`/`S-1'`, `S-2`/`S-2'`… en planta y alzado (pp. 5, 7, 9, 18, 19, 34-41) y los dibujos `SECCION 1-1'`, `SECCION 2-2'` … (pp. 9, 10, 18, 19, 37-41); `SECCION 1`, `SECCION 2` (p. 5). El mismo `S-1` se repite en cada hoja: **su sentido es local a cada hoja**.
- `TIPICO`: `DETALLE TIPICO SOLAPE ACERO` / `…EN NERVIOS DE LOSA` (pp. 10, 20-33, 36-41), `DETALLE TIPICO COLOCACION GANCHO` (p. 4), `SECCION TIPICA FUNDACIONES` (p. 3), `DETALLE DE SECCION TIPICA PLATEA/DROPS` (pp. 7-13).
- `VER DETALLE DE MUROS` (pp. 11-13) y `VER DETALLE` / `VER DETALLE MACIZADO` (pp. 20-33).
- **Notas con efecto sobre datos** (texto literal, parte):
  - Página 19 (hoja 18/36, losa de piso del sótano S7), `NOTA ESTRUCTURAL`: *"LA LOSA COMPRENDIDA ENTRE LOS NIVELES NPT = -19.05 Y NPT = -17.75 SE MODIFICO, SUSTITUYENDO LA LOSA APOYADA SOBRE RELLENO COMPACTADO POR UNA LOSA ESTRUCTURAL ALIGERADA APOYADA EN MUROS DE CONTENCIÓN, EN REEMPLAZO DE LA SOLUCIÓN INDICADA EN EL PLANO ANTERIOR APROBADO CON [LICENCIA]…"*. Es una **modificación respecto de un plano aprobado anterior**: debe llegar a la Mesa de Dudas, no leerse como dato.
  - `NOTA EMPALME EN VIGAS` / `NOTA EMPALME EN NERVIOS` (pp. 5-41), `NOTA LOSAS DE HORMIGON ARMADO` (pp. 9-33), `NOTA ESTRUCTURAL SOBRE CALIDAD DE HORMIGON` (pp. 7-13), `NOTA DE REFUERZO EN MAMPOSTERIA` y `NOTA SOBRE DESACOPLE SISMICO DE MUROS NO PORTANTES` (p. 6), `NOTA: "C" ES CONSIDERA…` (p. 4).
  - **Tabla de f'c por nivel** en cada hoja de planta (p. ej. p. 20): `FUND.@ E3 → 350 Kg/cm²`, `E3 @ E10 → 350`, `E10 @ E16 → 280`, … (de nuevo con la nomenclatura `E-n`).
- No hay un cuadro de revisiones/adendas con fecha: solo la fecha del cajetín (`AGOSTO 2024`) y `EXP. AX-24-01`.

## 6. Las 2 hojas de más del vectorial (41 frente a 39)

Emparejado **a ojo** con miniaturas (vectorial y sellado lado a lado, y las tres hojas dudosas a mayor tamaño):

- Vectorial 1-8 ↔ sellado 1-8 (criterios, materiales, armado, desacople, plantas de fundaciones).
- Vectorial **9 (`08/36` DETALLE DE SEPTICO)** y **10 (`09/36` DETALLE DE CISTERNA + solape)** **no tienen pareja** en el sellado.
- Vectorial 11, 12, 13 (secciones de fundaciones) ↔ sellado 9, 10, 11 (se comparó a mayor tamaño: mismos dibujos, mismos títulos).
- Vectorial 14-41 ↔ sellado 12-39 (columnas, muros, escaleras, plantas S7…techo y pórticos).

Conclusión: **las dos hojas extra son las páginas 9 y 10 del vectorial** (séptico y cisterna). Es una comparación visual de miniaturas, no una prueba exhaustiva hoja a hoja; si el sellado tuviera cambios internos de contenido, no los detecta. Deberá confirmarlo el usuario al certificar que el vectorial corresponde al sellado.

## 7. Tiempos (esta PC)

| Operación | Tiempo |
|---|---|
| Abrir el PDF de 17,7 MB | 0,002 s |
| Texto completo de las 41 hojas (`get_text`) | 1,1 s |
| Trazado de texto con capa y coordenadas, 41 hojas (`get_texttrace`) | 1,5 s |
| Abrir + texto con coordenadas de una hoja | 0,03 s |
| Rasterizar una hoja a 150 ppp (5400 × 3600 px) | 0,12–0,16 s (p. 26, 20 y 34); JPG de 1,6–1,9 MB |
| Miniaturas de las 41 hojas del vectorial / 39 del sellado | 3,2 s / 0,8 s |

## 8. Qué se puede extraer de forma fiable y qué no

**Fiable (texto con coordenadas, todo visible):**
- Número de hoja (`NN/36`) y títulos de dibujo por hoja.
- Tablas de acero en losa (tipo, H, Bw1, Bw2, h1, h2, acero X/Y y adicional) y la tabla de zapata de muro lindero, reconstruyendo filas por posición con tolerancia.
- Rótulos de IDs en planta (`C#`, `L#`, `V-bxh`, `MH#`), espesores de losa (`H=0.20M`/`0.25M`), cotas entre ejes, llamadas de acero de las columnas y los muros, tabla de f'c por nivel.
- Capas de AutoCAD como filtro de geometría (bordes de losa, ejes de viga, columnas, muros).

**No fiable sin ayuda o sin decisión:**
- **Equivalencia entre `E-n` (columnas y muros) y las plantas** (`SOTANO Sn`, `NIVEL n`): no está escrita.
- **Qué tipo A/B/C de losa corresponde a cada `L#`**: no está en texto.
- **Ejes**: el texto `A` es ambiguo (eje o marca de apoyo); la columna de la fila, el círculo vectorial o la posición deben decidir.
- Armados de columnas y muros: llamadas sueltas junto al dibujo; asignarlas a su elemento exige geometría (dentro de qué recuadro/sección cae cada texto), y las secciones `S-1` se repiten con otro sentido en cada hoja.
- **Notas de modificación** (p. ej. la de la losa S7): leerlas como aviso, nunca aplicarlas solas.
- **Las hojas 31/36 y 32/36** (págs. 32 y 33, dos plantas "DE TECHO"): requieren decidir cuál es cuál.
- Pórticos verticales (pp. 34-41): son páginas con `rotation = 270`; hay que usar la matriz de rotación de la página al convertir coordenadas.
- La **correspondencia con el sellado** (escaneo sin texto) solo se puede asegurar por el usuario, como decidió Steven.

## Criterio de aceptación

- [x] El informe responde los 8 puntos con ejemplos reales (títulos y números de las 41 hojas; capas; tablas con filas literales y bbox; ejes e IDs con coordenadas; rótulos y notas; las 2 hojas extra; tiempos; qué es fiable y qué no).
- [x] Nada del plano, ni imágenes, ni datos personales del cliente se copió al repositorio.
