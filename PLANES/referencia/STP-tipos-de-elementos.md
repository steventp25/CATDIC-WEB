# Formatos STP — Tipos de elementos y campos

> Fuente: `formato-stp-mived.md`, `formato-catdic-stp.md`, `filemaker-mapeo-campos.md` y `manual-sistema-informes.md` del Proyecto CATDIC.
> Hay **dos formatos STP** que no se mezclan: **STP-MIVED** y **CATDIC STP**. Ambos comparan "Información en planos" (1.x) vs. "Información en obra" (2.x).

---

## 0. Resumen de los dos formatos

| | **STP-MIVED** | **CATDIC STP** |
|---|---|---|
| Qué es | Supervisión técnica privada para el MIVED | Formulario propio de CATDIC (plantilla `FORMULARIOS MIVED.pdf`, 10 hojas) |
| Identificación visual | Sin logo; pie con nombre del proyecto y nº de página | Logo CATDIC arriba a la izquierda |
| Orden del informe | Portada → hoja de inspección → por elemento: hoja comparativa + hoja fotográfica | Portada → por elemento: hoja de tabla (plantilla) + hoja de localización y fotos |
| Cómo se genera | HTML → PDF | Se escribe sobre la plantilla PDF |
| Cuantía | Columna sin % | Cuantía en % |
| Tipos de elemento | Concreto armado | Concreto armado + perfiles metálicos |

**Formatos identificados y no preparados:** STP-DATA (Ficha de Supervisión — Data Supervisión) y STP-MET (Levantamiento de Estructura Metálica).

---

## 1. Estructura de cada hoja

### 1.1 Hoja comparativa (ambos formatos)
- **Cabecera:** No. DE LA SOLICITUD · No. LICENCIA · NOMBRE DEL PROYECTO · DIRECCION · FECHA | ELEMENTO
- **Barra de imágenes:** `IMAGEN DE PLANOS APROVADOS DTTL` | `IMAGEN EN OBRA` (se escribe "APROVADOS" con v, tal cual el original)
- **Barra de tabla:** `1. INFORMACION ARMADO EN PLANOS` | `2. IMFORMACION ARMADO EN OBRA` (con "IMFORMACION" con m, tal cual el original)
- Los campos llevan las mismas letras en ambos lados (1.a… / 2.a…). Las letras se reproducen tal cual, incluyendo saltos (no existe 1.l) y repeticiones.
- Celdas sin dato: vacías, "-" o "/".

### 1.2 Hoja fotográfica
- Recuadro de título arriba: `TIPO-ID-EJE…`
- Primera fila: **LOCALIZACIÓN** (planta con recuadro rojo) | **DETALLE** (detalle o tabla del plano con la fila resaltada)
- Debajo: fotos de campo en cuadrícula 2×2, o una sola foto grande.
- Pie: nombre del proyecto a la izquierda, nº de página a la derecha.

### 1.3 Portada (ambos formatos)
Proyecto · Licencia No. · Elementos (título grande, p. ej. "LOSA Y VIGAS SOTANO S-4") · Supervisor · Fecha de Inspección. En CATDIC STP lleva el logo CATDIC centrado arriba.

### 1.4 Hoja de inspección (solo STP-MIVED)
- Bloque 1: No. DE LA INSPECCION · NUMERO DE FORMULARIO · FECHA DE LA INSPECCION · FECHA DEL INFORME
- Bloque 2: NOMBRE DEL PROYECTO · NO. SOLICITUD · LICENCIA · INICIO DE OBRA · PROVINCIA · SECTOR · DIRECCION · NIVEL/ELEMENTOS A INSPECCIONAR · NOMBRE Y COLEGIATURA DEL RESIDENTE DE OBRA · SUPERVISOR
- Recuadro "OBSERVACIONES DURANTE LA INSPECCION" y línea "NOMBRE Y FIRMAS DE LOS INSPECTORES".
- El formulario oficial MIVED escaneado y firmado **no** va en lo que genera el sistema.

---

## 2. Tipos de elementos y sus campos

Nomenclatura del campo **ELEMENTO:** `TIPO-ID` (p. ej. `ZAPATA AISLADA-Z4`, `COLUMNA RECTANGULAR-C2`, `RIOSTRA-VF`, `VIGA HORMIGON-P4`, `MURO DE HORMIGON-MH02`, `LOSA MACIZA-L10`, `LOSA ALIGERADA 2D-L4`, `LOSA NERVADA-L14`, `ZAPATA DE MUROS DE HORMIGON-MURO PERIMETRAL`).

### 2.1 ZAPATA AISLADA
(En STP-MIVED también se usó para Z4, que en HV es "zapata combinada".)

| Campo | Rótulo |
|---|---|
| 1.a | RESISTENCIA ESPERADA (en obra: **2.a RESISTENCIA OBTENIDA**) |
| 1.b | Espesor fund. (m) |
| 1.c | Longitud X (m) |
| 1.d | Longutud Y (m) *(sic)* |
| 1.e | Calzos coloc. (SI/NO) |
| 1.f | Recubrimiento Min (m) |
| 1.g | Recubrimiento Max. (m) |
| 1.h | Barras Top X-X |
| 1.i | Barras Bot X-X |
| 1.j | Adic. Top X-X |
| 1.k | Adic. Bot X-X |
| 1.m | Barras Top Y-Y |
| 1.n | Barras Bot Y-Y |
| 1.o | Adic. Top Y-Y |
| 1.p | Adic. Bot Y-Y |

Ejemplo Z4: 210 · 0.90 · 7.40 · 4.50 · SI · 0.075 · 0.075 · Top Ø3/4"@0.15M · Bot Ø3/4"@0.10M.
En CATDIC STP la hoja ZAPATA es igual a FUNDACION pero con 2.a = "Resistencia Obtenida".

### 2.2 COLUMNA RECTANGULAR

| Campo | Rótulo |
|---|---|
| 1.a | Tipo de Pórtico |
| 1.b | Resist. esperada (Kg/cm²) |
| 1.c | Dim LX (m) |
| 1.d | Dim LY (m) |
| 1.e | Altura col. H (m) |
| 1.f | Espac. estribos en nodos (m) |
| 1.g | Espac. estribos paño central (m) |
| 1.h | Diam. Est. (Ø) — p. ej. `4Ø3/8"` o `4 EST + 1 GANCHO Ø3/8"` |
| 1.i | Eje dirección X-X (p. ej. 9-Ø1") |
| 1.j | Eje dirección Y-Y |
| 1.k | Total de barras |
| 1.m | Diámetro barras nudos (Ø) |
| 1.n | Diámetro barras internas (Ø) |
| 1.o | Solape zona central y long. |
| 1.p | Cuantía (STP-MIVED: sin %; CATDIC STP: %) |
| 1.q | % Acero solape *(en STP-MIVED aparece como segundo "1.p")* |

Cuantía: As total / (LX·LY) con el área real de las barras, calculada para cada elemento (no se copia la de los ejemplos).

### 2.3 VIGA HORMIGON / RIOSTRA / PÓRTICO (por tramo)
Mismo juego de campos para vigas, riostras y pórticos por tramo.

| Campo | Rótulo |
|---|---|
| 1.a | Tipo de Pórtico |
| 1.b | Resistencia (Kg/cm²) |
| 1.c | Ancho Viga (m) |
| 1.d | Altura Viga (m) |
| 1.e | Long. Tramo L (m) |
| 1.f | Espac. estribos nodos / esquina (m) |
| 1.g | Espac. estribos centro / paño central (m) |
| 1.h | Diam. Est. (Ø) |
| 1.i | Barras Top |
| 1.j | Barras Bot |
| 1.k | Adic. Top |
| 1.m | Adic. Bot |
| 1.n | Ubic./Long. Solape Bot |
| 1.o | Ubic./Long. Solape Top |
| 1.p | Cuantía |
| 1.q | % Acero solape |

Para vigas de pórtico, la IMAGEN DE PLANOS es el recorte del tramo en la elevación con el tramo resaltado y, debajo, la banda de estribos.

### 2.4 ZAPATA DE MUROS DE HORMIGON (muro perimetral)

| Campo | Rótulo |
|---|---|
| 1.a | Resistencia esperada |
| 1.b | Espesor (m) |
| 1.c | Longitud (m) |
| 1.d | Ancho zap. (m) |
| 1.e | Calzos coloc. |
| 1.f | Recub. Min |
| 1.g | Recub. Max |
| 1.h | As Transversal superior |
| 1.i | As Longitudinal |
| 1.j | As Transversal inferior |
| 1.k | As Longitudinal |

### 2.5 MURO DE HORMIGON

| Campo | Rótulo |
|---|---|
| 1.a | Resistencia esperada (Kg/cm²) |
| 1.b | Espesor muro (m) |
| 1.c | Longitud X (m) |
| 1.d | Altura (m) |
| 1.e | Calzos coloc. |
| 1.f | Recub. Min (m) |
| 1.g | Recub. Max (m) |
| 1.h | As Vert. Interno |
| 1.i | As Vert. Externo |
| 1.j | As Hor. Interno |
| 1.k | As Hor. Externo |

### 2.6 LOSA MACIZA y LOSA ALIGERADA 2D (también LOSA NERVADA)
Mismo juego de campos que la zapata aislada, con "Espesor Losa".

| Campo | Rótulo |
|---|---|
| 1.a | RESISTENCIA ESPERADA |
| 1.b | Espesor Losa (m) |
| 1.c | Longitud X |
| 1.d | Longitud Y |
| 1.e | Calzos coloc. |
| 1.f / 1.g | Recubrimiento Min / Max |
| 1.h | Barras Top X-X |
| 1.i | Barras Bot X-X |
| 1.j | Adic. Top X-X |
| 1.k | Adic. Bot X-X |
| 1.m | Barras Top Y-Y |
| 1.n | Barras Bot Y-Y |
| 1.o | Adic. Top Y-Y |
| 1.p | Adic. Bot Y-Y |

- En la **aligerada**: Top = malla del topping (p. ej. `MALLA D2.9xD2.9- 10x10`) y Bot = acero de nervio (p. ej. `3-Ø1/2"`).
- La imagen de planos es la tabla de losas con la fila resaltada en rojo.
- **Adicionales de losa:** se escriben por el eje de cada apoyo, en la fila de su dirección. Los apoyos sin adicional no se listan.
  - `1.j Adic. Top X-X : APOYO EJE A: Ø3/8"@0.15 / APOYO EJE B: Ø3/8"@0.15`
  - `1.n/1.o Adic. Top Y-Y : APOYO EJE 4: Ø3/8"@0.15 / APOYO EJE 3: Ø3/8"@0.15`
- En CATDIC STP la hoja LOSA numera: 1.a … 1.k (X-X) y 1.l Barras Top Y-Y, 1.m Barras Bot Y-Y, 1.n Adic. Top Y-Y, 1.o Adic. Bot Y-Y.

### 2.7 FUNDACION (losa de fundación o platea) — solo CATDIC STP
Igual que LOSA, con "Espesor de Fundación".

### 2.8 Perfiles metálicos — solo CATDIC STP (hojas 7 a 10)

| Hoja | Elemento | Campos |
|---|---|---|
| 7 | **PERFIL W / I** | 1.a Tipo Elemento · 1.b Elemento · 1.c Ancho Ala (b) · 1.d Peralte (h) · 1.e Espesor del Ala (tf) · 1.f Espesor del Alma (tw) |
| 8 | **TUBO (HSS rectangular)** | 1.a Tipo Elemento · 1.b Elemento · 1.c Ancho (b) · 1.d Peralte (h) · 1.e Espesor (t) |
| 9 | **ANGULAR (L)** | 1.a Tipo Elemento · 1.b Elemento · 1.c Ancho (b) · 1.d Peralte (h) · 1.e Espesor (t) |
| 10 | **CANAL (C)** | 1.a Tipo Elemento · 1.b Elemento · 1.c Ancho (b) · 1.d Peralte (h) · 1.e Espesor (t) |

La plantilla trae el esquema del perfil impreso. Decisión del usuario: si los planos traen el detalle del perfil se coloca ese detalle; si no, se le pide al usuario (no se deja el esquema genérico por defecto).

### 2.9 Mapa de hojas de la plantilla CATDIC STP

| # | Hoja |
|---|---|
| 1 | MURO |
| 2 | LOSA |
| 3 | FUNDACION |
| 4 | VIGA / PÓRTICO |
| 5 | COLUMNA |
| 6 | ZAPATA |
| 7 | PERFIL W / I |
| 8 | TUBO (HSS) |
| 9 | ANGULAR (L) |
| 10 | CANAL (C) |

---

## 3. Reglas de llenado

- **Columna OBRA:** si el elemento está conforme, repite el valor del plano. Solo una diferencia real se escribe con el valor medido.
- **Recubrimientos (se suman por lado antes de comparar con el plano):**
  - Zapatas y muros de contención (en contacto con el suelo): 7.5 cm → Min/Max = 0.075
  - Columnas y vigas: 4 cm → 0.04
  - Losas: 2.5 cm → 0.025
  - Ejemplo: una zapata de 4.00 m en plano mide 3.85 m de parrilla en obra y está conforme.
- **Fechas:** DD/MM/AAAA (no copiar el M/D/AAAA de los ejemplos).
- **ELEMENTO en la hoja de tabla = ID completo**, igual que el título de la hoja de localización: `TIPO-ID-EJE…` (p. ej. `VIGA HORMIGON-P4-EJE 4 ENTRE D-MC`). Para losas sin ejes, solo `TIPO-ID` (sin guion final).
- **Formato del campo Ejes** cuando el elemento corre entre dos ejes-letra: `EJE D-E,4` (no `EJE D-E (FILA 4)`).
- **Valores en una sola línea**, en la línea base del rótulo; si no caben, se reduce la letra (no se parte en dos líneas).
- **Identificación de elementos:** siempre por ID + Nivel + Ejes tomados de planos; la foto nunca es fuente de datos numéricos. Nunca inventar valores: lo que falte se marca como pendiente.

---

## 4. Anexo: mapeo FileMaker (SISTEMA STP-CATDIC)

- Tabla única con campos genéricos DATA1…DATA35; el significado de cada DATA depende de ELEMENTO.
- **"Campo Copy"** = INFORMACIÓN EN PLANOS (1.x). **Campo sin Copy** = INFORMACIÓN EN OBRA (2.x).
- Imágenes: LOCALIZACION, DETALLE, FOTO, FOTO2, FOTO4, FOTO3 (en ese orden; no salen al exportar a Excel).
- Campos generales: ELEMENTO, ID, NIVEL, EJEA / EJEB, IDVISITA / ID_PROYECTO, PROYECTO.
- Elementos con mapeo parcial: VIGA HORMIGON, LOSA ALIGERADA 2D, LOSA ALIGERADA 1D, MURO DE HORMIGON, LOSA MACIZA.
- **No importar** los campos calculados (VIGAS_ACERO_TOP, ESTRIBOS_NUDOS, ZAP_*, COL_TOTAL BARRAS, etc.) ni los relacionados (PROYECTO::…, VISITA::FECHA).
- Por confirmar: si OBSERVACIONES se escribe o lo calcula FileMaker.

| Elemento | Campo | Significado | Estado |
|---|---|---|---|
| VIGA HORMIGON | DATA33 | 1.b Resistencia | Confirmado |
| VIGA HORMIGON | DATA1 / DATA2 | 1.c Ancho / 1.d Altura | Confirmado |
| VIGA HORMIGON | DATA34 | 1.e Long. tramo L | Confirmado |
| VIGA HORMIGON | DATA3 / DATA4 | Barras Top: cantidad / diámetro | Confirmado |
| VIGA HORMIGON | DATA8 / DATA9 | Barras Bot: cantidad / diámetro | Confirmado |
| VIGA HORMIGON | DATA13–16 | Adicional apoyo 1: existe / cant. / diám. / long. | Confirmado |
| VIGA HORMIGON | DATA17–20 | Adicional apoyo 2 | Inferido |
| VIGA HORMIGON | DATA21–23 / DATA24 | Solape superior / inferior | Inferido |
| VIGA HORMIGON | DATA25 / DATA26 | Estribos en nodos: diámetro / separación | Confirmado |
| VIGA HORMIGON | DATA29 / DATA30 | Estribos centro: diámetro / separación | Confirmado |
| VIGA HORMIGON | DATA27 / DATA28 / DATA31 | Longitudes de zonas de estribos | Inferido |
| VIGA HORMIGON | DATA35 | 1.p Cuantía | Confirmado |
| LOSA ALIGERADA 2D | DATA16 / DATA3 / DATA15 | Resistencia / espesor total / recubrimiento | Confirmado |
| LOSA ALIGERADA 2D | DATA6 | Barras Top X-X (malla topping) | Confirmado |
| LOSA ALIGERADA 2D | DATA7 / DATA8 | Bot X-X: cantidad / diámetro | Confirmado |
| LOSA ALIGERADA 2D | DATA9 / DATA10 | Bot Y-Y: cantidad / diámetro | Confirmado |
| LOSA ALIGERADA 2D | DATA12 / DATA13 | Longitud X / Y | Inferido |
| LOSA ALIGERADA 2D | DATA1/2/4/5/11 | Bovedilla, nervio, topping, calzos | Inferido |
| LOSA ALIGERADA 1D | DATA16 / DATA3 / DATA15 | Igual que 2D (en L13 hay campos corridos una posición) | Confirmado |
| MURO DE HORMIGON | DATA1 | 1.a Resistencia | Confirmado |
| MURO DE HORMIGON | DATA4 / DATA5 / DATA6 | Espesor / Altura / Longitud | Confirmado |
| MURO DE HORMIGON | DATA8 / DATA9 | As vertical interno: diám. / sep. | Confirmado |
| MURO DE HORMIGON | DATA10 / DATA11 | As horizontal interno: diám. / sep. | Confirmado |
| MURO DE HORMIGON | DATA12 / DATA13 | As vertical externo: diám. / sep. | Confirmado |
| MURO DE HORMIGON | DATA14 / DATA15 | As horizontal externo: diám. / sep. | Confirmado |
| LOSA MACIZA | DATA28 | 1.a Resistencia | Confirmado |
| LOSA MACIZA | DATA1 / DATA2 / DATA3 | Long. X / Long. Y / Espesor | Confirmado |
| LOSA MACIZA | DATA4 | 1.e Calzos | Confirmado |
| LOSA MACIZA | DATA6–13 | Barras X-X / Y-Y, camadas 1 y 2 (diám. / sep.) | Inferido |

---

## 5. Pendientes / lo que no está definido

- **Escalera, columna metálica con conexiones, pernos de anclaje:** no hay ficha STP definida (solo existen en HV o están por preparar).
- **STP-DATA** y **STP-MET:** identificados, sin preparar.
- **CATDIC STP:** todavía no se ha generado un informe completo; hojas 5 a 10 identificadas por sus campos, no marcadas por el usuario.
- Posibles errores de origen en los ejemplos P16 (VF 0.30×0.60 vs 0.40×1.20; L10 maciza vs aligerada; L4 Bot Y-Y; resistencia 210 vs 280 en C1/C2 de fundación): el usuario indicó que "el STP está bien" salvo VF y L4, pendientes de aclarar.
