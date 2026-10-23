# Etapa 3 · T0b — Inventario de las fuentes de la fábrica

Fecha: 23/10/2026. Autor: Ejecutor (Claude Code). Para: Planificador (ajusta T7, T8 y T9) y Steven.

## Alcance y método
- Las fuentes están en `G:\My Drive\CATDIC\FORMATO CLAUDE\New folder\` y se leyeron **en solo lectura**. Se copiaron **sin editar** a `FABRICA/fuentes/` (comprobado con `cmp`). `FABRICA/` está en `.gitignore`: las fuentes llevan datos del cliente (licencia, dirección, residente) y no deben ir a git (P10). `git status` no las muestra.
- Copiadas (5): `stp-mived-generador.py.md`, `stp-mived-generador-s5.py.md`, `catdic-stp-llenador.py.md`, `plantilla-datos-diseno.md`, `plantilla-visita-obra.md`. No se copió `catdic-stp-llenador.py (1).md` (idéntico, `cmp`) ni los `hv-informe-tecnico-*.md` (son de la Etapa 4).
- Las referencias `archivo:línea` son líneas de **esos `.md`** (cuentan la línea de cada bloque de código dentro del `.md`). Abreviaturas: **G** = `stp-mived-generador.py.md` (contiene `assets.py`, `stp.py`, `lib_pages.py`, `vert.py`, `pdf.py`, `fi02.py`); **S5** = `stp-mived-generador-s5.py.md` (`stp5.py`, `fi02_s5.py` y un bloque de `vert.py`); **C** = `catdic-stp-llenador.py.md` (`catdic_stp.py`).
- **CATDIC-STP (T9) aplazada** por decisión de Steven (23/10/2026): "ese formulario no lo hagas todavía, que ese no se está utilizando". `catdic_stp.py` (**C**) se clasifica igual en la tabla, marcado "T9 aplazada", sin más análisis. No hacen falta `FORMULARIOS MIVED.pdf` ni el logo CATDIC por ahora.
- Los FI de Serenity son ejemplos de los 3 formularios oficiales del MIVED (FI-01 cimentaciones, FI-02 losas y FI-03 verticales); su reconocimiento (Parte 2) es prioritario porque lo necesita T8.
- No se copió ningún PDF ni foto al repositorio. Los FI se abrieron en solo lectura con PyMuPDF.

## Parte 1 — Valores fijos de los scripts

Clases: **formato** (se conserva), **proyecto** (sale de `proyectos`), **diseño** (Capa 1, `elementos_diseno`), **visita** (Capa 2, `elementos_visita`/`visitas`), **coordenada** (posición en un plano de Terra Living), **foto** (número de foto del log), **rutas** (entorno Linux).

El destino "cálculo" significa `reglas_ingenieria.py`. **Regla de Oro #1:** ningún valor de las clases proyecto, diseño, coordenada o foto se porta desde los scripts; si falta en la BD queda `"pendiente de verificar"` + duda y no se genera la ficha.

### 1.1 Datos de proyecto (clase **proyecto**)

| archivo:línea | valor | clase | debe salir de | ¿existe hoy? |
|---|---|---|---|---|
| G:94 · G:390 · S5:12 | `PROY='TERRA LIVING'` | proyecto | `proyectos.nombre` | Sí (`nombre`) |
| G:94 · G:390 · S5:12 | `LIC='<licencia>'` (se usa como **No. de solicitud y como licencia**, G:227-228, G:484-485) | proyecto | `proyectos.no_solicitud` y `proyectos.no_licencia` (son dos campos) | Sí, ambas, vacías |
| G:94 · G:390 · S5:12 | `DIR='<dirección>'` | proyecto | `proyectos.direccion_obra` | **No** → T7a |
| G:265 · G:487 · S5:132 | `PROVINCIA = <provincia>` | proyecto | `proyectos.provincia` | **No** → T7a |
| G:266 · G:488 · S5:133 | `SECTOR = <sector>` | proyecto | `proyectos.sector` | **No** → T7a |
| G:269 · G:491 · S5:136 | residente `<residente + CODIA>` (nombre + colegiatura juntos) | proyecto | `proyectos.residente_obra` (texto único; la colegiatura no tiene columna propia) | Sí (`residente_obra`) |
| G:255 · G:477 · S5:122 | `Supervisor` vacío en portada e inspección (G:270) | proyecto | `proyectos.supervisor` | Sí (`supervisor`) |
| G:264 · G:486 · S5:131 | `INICIO DE OBRA` vacío | proyecto | no hay fuente | **No** (no existe la columna; queda vacío/pendiente) |
| G:258 · G:480 · S5:125 | `No. DE LA INSPECCION`, `NUMERO DE FORMULARIO`, `FECHA DEL INFORME` vacíos | visita | `visitas.numero` (No. de inspección es el de la visita); número de formulario y fecha del informe no tienen fuente | Parcial: solo `visitas.numero` |
| G:95 · G:93 · S5:13 | `ELEMS_TXT` (p. ej. `LOSA Y VIGAS ENTREPISO 3 (SOTANO S3)`), `FECHA`, `CLASE` | visita | `visitas.nombre_carpeta` (nivel/elementos), `visitas.fecha_visita`, `visitas.clase` | Sí; el texto "nivel/elementos" hoy sale del nombre de la carpeta (T3 saca el nivel solo si trae exactamente uno) |
| G:272 · G:494 · S5:139 | texto de observaciones `SE VERIFICO EL ARMADO DE …, ACORDE A PLANOS APROBADOS.` | formato + visita | plantilla fija con la lista de elementos/ clase de la visita; "ACORDE A PLANOS APROBADOS" solo si no hay discrepancias abiertas (CLAUDE.md §3.2) | Parcial (no hay campo de discrepancias abiertas) |
| G:532-534 · S5:145 | nombres de salida `Terra Living - STP - … - DD-MM-AAAA.pdf` | formato | `reglas_ingenieria.obtener_ruta_salida_sin_sobrescribir` + §5.2 | Sí (regla); armado del nombre por hacer |

### 1.2 Coordenadas y recortes de planos (clase **coordenada**) — no se portan

| archivo:línea | valor | clase | debe salir de | ¿existe hoy? |
|---|---|---|---|---|
| G:18-19 · G:25-29 | `PX=(1050,520,3720,3460)`, ejes `AX` y `AY`, `hbeam()`/`vbeam()` con `pad=55`, y `lw=22` (G:23) | coordenada | `elementos_diseno.recorte_planta_json` (recuadro rojo en la planta completa) | Sí (columna, vacía) |
| G:32-39 · G:55-57 · G:64-72 | `SRC`/`GEO` (recortes de elevaciones), `tab` y `ROWY` (tabla de losas), recortes del detalle de muro | coordenada | `elementos_diseno.recorte_detalle_json` | Sí (columna, vacía) |
| G:394-398 · S5:25-27 · S5:38-57 | `PLANS`, `crop`, `X`, `Y`, `MCN`, `elev5` | coordenada | ídem | ídem |
| G:409 · G:412-422 · S5:34-35 | `colbox(w=75)`, `det_mc`, ranuras de nivel (`2288`, `2028`) | coordenada | ídem | ídem |
| G:104-116 · S5:76-94 | `tx` (rangos en x), `box`, `k`, `cy`, `band` de cada tramo | coordenada | ídem | ídem |
| G:46 · G:51 · G:404-405 · S5:47 | grosor del recuadro rojo `width=8/22/40` y color `RED=(220,0,0)` | formato | `reglas_ingenieria.calcular_grosor_recuadro_rojo` y T6 (`localizacion.py`) | Sí (cálculo) |

Nota: T6 ya rasteriza la planta completa a 200 dpi y dibuja el recuadro con el grosor calculado; las coordenadas llegan como parámetro, nunca se deducen.

### 1.3 Datos de diseño (Capa 1, clase **diseño**) — no se portan

Todo esto debe venir de `elementos_diseno.datos_diseno_json`. Las listas de campos por tipo están en `plantilla-datos-diseno.md` (columnas por tipo). Hoy la columna existe pero **sus claves no están definidas**: falta la lista de campos por tipo (pendiente de T0 / Etapa 2).

| archivo:línea | valor | clase | debe salir de | ¿existe hoy? |
|---|---|---|---|---|
| G:99-117 · S5:67-95 | para cada tramo: `id`, eje, tramo, `L`, estribos nodos/centro, diámetro, barras top/bot, adicionales, `h` (peralte), `photos` | diseño + foto | `elementos_diseno` (L, peralte, barras, estribos, adicionales); las fotos, de `elementos_visita` | Columna sí; claves no |
| G:102 · S5:14 | `As={'3/4':2.85,'1/2':1.27}` | cálculo | `reglas_ingenieria.AREA_BARRA_CM2` (usa 2,84 y 1,29; **distinto**: la fuente usa 2.85/1.27) | Sí (regla) → **discrepancia, ver §1.6** |
| G:118-121 · S5:15-18 | `cuantia()` con ancho fijo `40` cm | cálculo | `reglas_ingenieria.calcular_cuantia_elemento(b, h, barras)` (con la sección real del elemento) | Sí (cálculo) |
| G:123-125 · G:129-139 · S5:19-20 · S5:96-110 | `MALLA='MALLA D2.3xD2.3-100x100'`, `BOT={'A':'3-Ø1/2"','B':'2-Ø1/2"'}`, apoyos `ad(...)` (`Ø3/8"@0.15`) y lista `LS` de losas (L1…L20) | diseño | `elementos_diseno` (tabla de acero de la losa + apoyos) | Columna sí; claves no |
| G:140 | `MU` (muro perimetral, `box`, fotos 69-72) | diseño + coordenada + foto | ídem | ídem |
| G:166-169 | `rows_viga`: resistencia `350`, ancho `0.40` y solape `/` (el `Ø3/8"` de estribos está en cada `V(...)`, G:104-116 y S5:76-94, no en `rows_viga`) | diseño | `elementos_diseno` | ídem |
| G:177-181 | `rows_losa`: resistencia `350`, espesor `0.25`, `Longitud X/Y` (vacías, G:181: sin fuente), `Calzos coloc.='SI'`, recubrimientos `0.025`/`0.025` | diseño | `elementos_diseno`; recubrimiento = `reglas_ingenieria.obtener_recubrimiento` (0.025 losas) | Parcial |
| G:185-187 | `rows_muro` (pantalla): resistencia `240`, espesor `0.25`, longitud `7.88`, recubrimientos `0.075`, `Ø1/2"@0.10` | diseño | `elementos_diseno`; recubrimiento 0.075 solo si es muro de contención (§4.5) | Parcial |
| G:435-446 | `rows_col`: `A1=5.07` para todas las barras; altura `H=2.95`; `Ø3/8"@0.10`; `ZONA CENTRAL / 1.08`; `Ø1"`; `COLS` (dimensiones y barras de C1…C5) | diseño | `elementos_diseno` (dimensiones, barras, estribos, solape); área de barra = `AREA_BARRA_CM2` | Columna sí; claves no |
| G:447-452 | `rows_mur`: `fc`, `esp`, `L`, `rec`, `asv`, `ash`; altura `2.95` | diseño | `elementos_diseno` | ídem |
| G:512-514 · G:521-523 · G:527-529 · S5:196-198 | listas `V16`, `V17`, `V17p`, `V14` con `fc`, espesores, longitudes, aceros de muros MH1/MH3/MH4 y columnas | diseño + foto | `elementos_diseno` + `elementos_visita` | ídem |
| G:535 · S5:183 | `Ø`, `@`, números de barras tal como están escritos | diseño | textos literales del plano (no se reformatean) | ídem |

### 1.4 Fotos (clase **foto**) y proceso de imagen

| archivo:línea | valor | clase | debe salir de | ¿existe hoy? |
|---|---|---|---|---|
| G:104-116 (`photos=rng(...)`) · S5 · G:509-529 (`COL(...,[2,3,4,5])`) | números de foto por elemento (`rng(2,5)`, `[6]`, …) | foto | `elementos_visita.fotos_json` (agrupación secuencial del log, T3) | Sí |
| G:84-91 · G:429-432 · S5:60-64 | `thumbnail((1000,1000))`, `quality=72`, `exif_transpose` | formato | T3 (caché) y T6 (`generators/comun/fotos.py`) | Sí |
| G:159-162 · G:288-291 | `pick4` | formato | `reglas_ingenieria.seleccionar_fotos_pick4` | Sí |
| G:201-214 · G:339-343 | `object-fit: contain` y cuadrícula 2×2 aunque haya 2 o 3 fotos | formato | se reemplaza por T6 (cover + gutter); 2 fotos en dos columnas y 3 fotos con una ancha arriba (P9) | Sí (T6) |

### 1.5 Formato visual y de salida (se **reutiliza**)

| archivo:línea | valor | clase | destino |
|---|---|---|---|
| G:191-220 (= G:320-349) | CSS completo: `@page Letter`, `.pg`, `.foot`, tablas, `.imgs`, `.cmp`, `.title`, `.toprow`, `.cover`, `.insp{background:#efefef}` | formato | `generators/plantillas/stp_mived.css` (T7); fuentes `Calibri`/`Arial` de Windows en vez de `Carlito`/`Liberation Sans` |
| G:221-250 (= G:350-379) | `page_cmp`, `page_fot`, rótulos exactos `IMAGEN DE PLANOS APROVADOS DTTL`, `IMFORMACION ARMADO EN OBRA`, filas `1.a … 2.q` | formato | T7 (sin cambiar rótulos ni ortografía) |
| G:251-273 · G:473-495 | portada y hoja de inspección | formato | T7 |
| G:538-548 | `pdf.py` (Playwright, Carta, sin márgenes) | formato | T7 (llamada directa, sin `os.system`) |
| G:194 · G:215 · G:323 · G:344 | familias `Carlito,Calibri,Arial` y `Liberation Sans` | formato | Calibri/Arial (P6: Arial) |

### 1.6 Rutas, sistema y discrepancias a resolver

Las filas con **C:** son de `catdic_stp.py` y quedan **T9 aplazada** (no se analizan más).

| archivo:línea | valor | clase | decisión |
|---|---|---|---|
| G:11 · G:387 · S5:10 | `W='/home/claude/w/'`; `exec(open('/home/claude/gen/...'))` | rutas | `pathlib` y módulos importables |
| G:501 · S5:148 | `os.system('python3 /home/claude/gen/pdf.py ...')` | rutas | llamada directa a Playwright |
| G:554-556 · S5:155-157 · C:11-12 | rutas `/mnt/user-data/uploads/...`, `/usr/share/fonts/...Carlito...` | rutas | rutas de Windows/Dropbox y Arial (P6); las de `C:` son de T9 aplazada |
| C:11 · C:93 | plantilla `plantilla_catdic_stp.pdf` y `logo_catdic.png` | formato | **T9 aplazada**: no hacen falta `FORMULARIOS MIVED.pdf` ni el logo por ahora |
| C:13 · **T9 aplazada** | `HOJA={'MURO':0,'LOSA':1,'FUNDACION':2,'VIGA':3,'COLUMNA':4,'ZAPATA':5,'PERFIL_W':6,'TUBO':7,'ANGULAR':8,'CANAL':9}` | formato | igual a CLAUDE.md §3.2 (hojas 0-9) |
| C:42-46 · C:53-59 · **T9 aplazada** | `_put` reduce la letra hasta 5 pt; `_bases` toma la línea base | formato | se reutiliza (valores en una línea, §3.2) |
| C:99-107 · **T9 aplazada** | coordenadas fijas de la portada (`cx=306`, `y` de los rótulos 161/274/381/502/615, logo `34..111`) | coordenada (de la plantilla) | se reutilizan solo con la plantilla real; **se verifican contra `FORMULARIOS MIVED.pdf` cuando llegue** |
| C:96 · C:93 · **T9 aplazada** | `Carlito-Bold`, `LiberationSans` | formato | Arial (P6) |
| G:435 (`A1=5.07`) vs `reglas_ingenieria.AREA_BARRA_CM2['1"']` | `Ø1"` = **5.07** (fuente, G:435) frente a 5.10 (motor) | cálculo | **Tercera discrepancia**: el motor usa áreas nominales ASTM A615 y las fuentes usan el área geométrica π·d²/4; decide Steven |
| G:102 vs `reglas_ingenieria.AREA_BARRA_CM2` | `3/4"` = **2.85** y `1/2"` = **1.27** (fuente) frente a 2.84 y 1.29 (motor) | cálculo | **Discrepancia**: manda el motor de reglas (Etapa 0); decidirlo Steven si prefiere los de la fuente |

### 1.7 Resumen de columnas que faltan

- **Faltan en `proyectos`** (T7a): `direccion_obra`, `provincia`, `sector`. Sin fuente por ahora: inicio de obra, número de formulario, fecha del informe, colegiatura aparte del nombre del residente.
- **Faltan las claves** de `elementos_diseno.datos_diseno_json` por tipo (la lista está en `plantilla-datos-diseno.md`).
- **No existen** campos de "discrepancias abiertas" que habiliten el texto `CONFORME A PLANOS APROBADOS` (CLAUDE.md §3.2).

## Parte 2 — Reconocimiento de los FI (solo lectura)

Archivos abiertos con PyMuPDF (sin guardar nada):
- Serenity RS (`ARCHIVOS DEL CLIENTE\FORMULARIO\EDIFICIA  A\`, la carpeta lleva dos espacios): `FI-01-26-STP-SERENITYRES EDF1.pdf` (3 pág.), `FI-02-25-STP-SERENITYR EDF A.pdf` (4 pág.), `FI-03-25-STP-SERENITYR EDF A.pdf` (3 pág.). Son los formularios en blanco con la estructura oficial.
- Terra Living (`FORMULARIOS\MIVED\FORMULARIOS NO FIRMADOS\`): los 12. Se leyeron en detalle el 1 (FI-01), el 12 (FI-02) y el 10 (FI-03); de los 12 se contaron las casillas marcadas.

Todas las coordenadas son puntos del PDF (A4: 595,32 × 841,92), origen arriba a la izquierda.

### ¿AcroForm o texto plano?
**Ninguno es AcroForm.** `is_form_pdf = False` y 0 widgets en las tres páginas de los tres formularios y en los 12 de Terra. Todo se rellena con **texto** (`insert_text`/redacción) y **dibujos** sobre el PDF. El método de `fi02.py` (buscar el span por su texto, tapar con redacción blanca y escribir en la línea base) sigue siendo el correcto.

### Encabezado de página (las 3 páginas)
Texto fijo: `FORMULARIO INSPECCIÓN` y el subtítulo del tipo, la fecha de impresión (`dd/mm/aaaa`, x 529,9 y 22,7), el consecutivo de página y el código `FI-0n-AA-STP-…` (x 443-466, y 50,5). Estos textos son del PDF de origen (no se llenan).

### Datos generales (solo página 1)
Rótulos y dónde se escribe el valor (línea base `origin`, medidas del FI-02 #12 de Terra):

| Campo | Rótulo (x, y de la línea base) | Valor escrito en Terra |
|---|---|---|
| Nombre del proyecto | (19,0 · 116,2) | `<nombre del proyecto>` en x 123,1, base 115,9 (Calibri) |
| Licencia No. | (438,9 · 116,2) | `<licencia>` en x 498,8, base 113,2 |
| **Nivel a inspeccionar** | (16,7 · 130,1) | **x 132,2, base 130,0** (Carlito 10,6) — este valor lo reescribe `fi02.py` |
| Sol. Licencia No. | (421,0 · 130,1) | sin valor en el ejemplo |
| Encargado de obra | (16,7 · 144,0) | `<encargado de obra>` en x 132,2, base 142,6 |
| **Fecha** (dd / mm / aaaa) | rótulo en (401,3 · 144,0) | **x 487,0, base 144,7** (`02/10/2026`, una sola cadena) |
| Dirección | (16,7 · 157,9) | en x 119,8, base 157,1 |

En el FI-01 y el FI-03 el rótulo "Sol.Licencia No." está en x 428,3 y "Fecha" en x 405,4; la fecha del FI-01 se llena con **tres textos** (dd en x 477,8; mm en 511,7; aaaa en 551,3; base 144,2-144,4) porque el rótulo trae `dd / mm / aaaa`. En el FI-02 de Terra la fecha ya viene como una sola cadena que `fi02.py` pone en x 487,0.

### Casillas Sí/No
- Cada fila de verificación termina con `Sí` (texto en x ≈ 525-532) y `No` (x ≈ 565-577) y una imagen de la caja a su izquierda: imagen de ≈ 48 × 9 pt en x 505-554 (en el FI-02 x 503,6-549,2; en el FI-03 x 503,8-548,5).
- **Marca de "Sí":** en los FI llenados de Terra es un dibujo vectorial (2 trazos, ancho 1,5, negro) en un cuadro de **12 × 12 pt** en x ≈ 499,6-516,2 (según el formulario) y con la misma `y` de la fila (p. ej. FI-01 p1: rect [504,2 · 183,5 · 516,2 · 195,5]; FI-02 p1: [499,6 · 184,1 · 511,7 · 196,2]).
- **Marca de "No":** en los 12 FI de Terra **no hay ninguna** en la columna del "No" (x ≥ 530). **No se puede saber** dónde caería sin un ejemplo; no se adivina.
- Las filas marcadas en los 12 FI de Terra son **casi siempre las mismas** por tipo. Conteo de marcas (dibujos de 12 × 12 pt) por página, medido sobre los dibujos:
  - FI-01 (cimentación): p1 9 marcas → 1a-1i; p2 11 marcas → 4a, 4c-4e, 7a-7f, 8a; p3 0.
  - FI-02 (losas y vigas): p1 10 marcas → 1a-1e y 2a-2e; p2 7 → 6a, 6b, 7a-7e; p3 7 → 11a-11f y 12a; p4 0. **Excepciones:** el FI-02 n.º 3 (losa de séptico) tiene 0 marcas en la p1, y el n.º 4 (losa sótano -7) tiene 6 en la p3 (le falta 12a).
  - FI-03 (verticales), los 5 iguales: p1 15 marcas → 1a-1e, 2a-2c, 4a-4f; p2 4 → 5a, 5c, 5d y una fila de 5; p3 9 → **10a-10e (SEGURIDAD)** y 11a-11d (PROBETAS), en y ≈ 100, 113, 128, 142, 157 y 191, 221, 243, 271.
- Coincide con CLAUDE.md §3.2: se marcan encofrados, armaduras, seguridad y probetas (FI-03: secciones 1, 2, 4, 5, 10 y 11; FI-02: 1, 2, 6, 7, 11 y 12). Mampostería nunca.

### ¿Cuáles casillas son de mampostería?
Solo en el **FI-03**:
- **Sección 8 "MAMPOSTERÍA (Mampostería no estructural, muros …)"**: filas 8a-8g, en la p2 (y ≈ 350-529). Nunca se marcan en los 12 de Terra.
- **Sección 9 "MUROS DE CERRAMIENTO Y PANDERETAS"**: filas 9a-9c (p2, y ≈ 529-598). Tampoco se marcan. **No está claro si Steven la considera mampostería**; por ser no estructural se propone tratarla igual (nunca marcar). Pendiente de verificar.
- En la **sección 11 PROBETAS** (p3): 11b "Etiquetado de los bloques de hormigón", 11c "Resistencia a compresión del mortero" y 11d "…hormigón de cámara del block". En los 12 de Terra **sí se marcan 11a-11d** aunque nombran bloques; son de probetas, no de mampostería (decisión de Steven: marcar probetas). Pendiente de verificar si 11b-11d deben marcarse.
- El FI-01 y el FI-02 no tienen sección de mampostería. En el FI-02, las secciones 8 "ENCOFRADO DE DINTELES" y 9 "ARMADURA DE DINTELES" (p2-p3) **no se marcan nunca** en los ejemplos; no se sabe si Steven las trata como mampostería.

### Observaciones y fechas de autorización
- **FI-02 y FI-01:** el cuadro "OBSERVACIONES" está en la **p3**, rótulo `13. OBSERVACIONES` en (194,6 · 484,8) en el FI-02 y `9. OBSERVACIONES` en (199,6 · 97,9) en el FI-01. Las observaciones de Terra se escriben en x **26,8** (FI-02) o **41,8** (FI-01) con bases 502,6 / 518,4 / 550,0 (FI-02) y 114,6 / 146,8 / 163,0 / 217,8 / 252,4 (FI-01). El cierre `Todo segun los planos estructurales.` va como última línea. Fuente: Carlito (FI-02) o Calibri 13,4 (FI-01) en los de Terra.
- **FI-03:** `12. OBSERVACIONES` en (195,1 · 302,6) y las observaciones se escriben desde x **39,3** con bases ≈ 337, 353, 369, … (p3).
- **Fechas de autorización de vaciado** (`NOMBRES Y FIRMAS (Autorización de Vaciado de Hormigón)`): cada fila lleva `dd / mm / aaaa` en tres textos. En el FI-02 de Terra:
  - fila "Director o encargado de obra": `02` en x 466,7 y `10` en x 500,6 (base 789,9), año `2026` en x 540,2;
  - fila de inspector: `02` en x 467,4, `10` en 501,2 (base 809,6), año en x 540,8.
  - Cada `/` es un texto aparte (x 487,6-494,1 y 518,5-525,0). `fi02.py` y `fi02_s5.py` reescriben solo día y mes (redactando el original y escribiendo con Carlito).
  - **Regla implícita pendiente de confirmar con Steven:** `fi02.py` (visita **parcial**) **borra** las tres cifras de las fechas de autorización (día, mes y año de la fila inferior) y no escribe nada nuevo, mientras que `fi02_s5.py` (visita **completiva**) borra solo día y mes y escribe el día y el mes del completivo (`02`, `09`) en la fila del inspector (x 467,4 y 501,2, base 809,6). Es decir: en un parcial la fecha de autorización queda en blanco y en un completivo se completa; no está escrito en ninguna especificación.
  - En el FI-03 las filas están en base 519,1 / 538,1 / 556,0 con `dd` en x 474,1 y `aaaa` en x 545,6.
- En el FI-02 la p4 (en los de Serenity) es una **hoja de inspectores adicionales**: `Inspectores` (63,1 · 97,4) con dos filas `dd/mm/aaaa` (bases 97,9 y 115,8). En los 12 de Terra el FI-02 también tiene 4 páginas.

### ¿La firma es una anotación?
**Sí.** En el FI-02 #12 y en el FI-03 #10 de Terra, en la página de firmas hay **una anotación `Square`** con título de autor (omitido aquí) y `/IT /SquareImage`, `/Subj (Image)` y una imagen de apariencia (`/AP /N`, `/Image`), caja roja sin relleno:
- FI-02 #12: rect `[329,6 · 796,5 · 365,8 · 816,2]` (columna `Firma`, x 298,7-400, fila del inspector).
- FI-03 #10: rect `[331,1 · 525,9 · 367,3 · 545,7]`.
`fi02.py` las elimina con `page.delete_annot` antes de guardar (CLAUDE.md §3.1: el sistema nunca fabrica firmas ni conserva las anteriores). El FI-01 #1 no trae anotaciones. Los nombres de los firmantes y sus códigos CODIA son **texto Calibri**, no anotación; son datos del ejemplo y no se portan.

### Diferencias entre FI-01, FI-02 y FI-03

| | FI-01 | FI-02 | FI-03 |
|---|---|---|---|
| Subtítulo | ELEMENTOS DE CIMENTACIÓN (ZAPATAS) | ELEMENTOS HORIZONTALES (LOSAS Y VIGAS) | ELEMENTOS VERTICALES (COLUMNAS Y MUROS) |
| Páginas | 3 | 4 (la 4 es de inspectores adicionales) | 3 |
| Secciones | 10: excavaciones, armaduras de zapatas y plateas (2 y 3), arranque de columnas, pilotes, vigas riostras, seguridad, probetas, observaciones, firmas | 14: encofrado y armadura de losas (1-3), escaleras (4-5), vigas (6-7), dinteles (8-9), arranque (10), seguridad (11), probetas (12), observaciones (13), firmas (14) | 13: encofrado y armadura de muros y columnas (1-5), dinteles (6-7), **mampostería (8)**, muros de cerramiento y pandereta (9), seguridad (10), probetas (11), observaciones (12), firmas (13) |
| Mampostería | no | no | **sí, 8 y 9** |
| Observaciones | p3 `9.` en y 97,9 | p3 `13.` en y 484,8 | p3 `12.` en y 302,6 |
| Firmas | p3, `10.` (y ≈ 370) | p3, `14.` (y ≈ 754) | p3, `13.` (y ≈ 487) |
| Código del archivo | `FI-01-26-STP-<PROY>` | `FI-02-26-STP-<PROY>` | `FI-03-26-STP-<PROY>` |

Las coordenadas **no son iguales entre formularios** (las filas, secciones y cajas cambian). Un generador de FI necesita una tabla de coordenadas **por formulario y por página**, no una común.

### Nombres de los archivos
Los 12 de Terra siguen `N. FI-0n-26-STP-TERRALIVING <ELEMENTOS NIVEL> <FECHA>.pdf` (numerados), no el patrón §5.2 `MIVED - <PROYECTO>-<ELEMENTOS NIVEL>.PDF`; el nombre nuevo (P5) se decide al implementar T8.

## Qué no se pudo saber sin adivinar
- Dónde cae la marca del "No" (no hay ningún ejemplo marcado).
- Si la sección 9 del FI-03 y las secciones 8-9 del FI-02 (dinteles) cuentan como mampostería.
- Si 11b-11d del FI-03 (bloques/mortero) deben marcarse siempre.
- La posición exacta de las filas de los formularios **en blanco de Terra** (`FORMULARIOS\FI-01|02|03-26-STP-TERRALIVING.pdf`): no se abrieron; se usaron los llenados.
- Cómo se numera el consecutivo `N.` de los archivos nuevos.
