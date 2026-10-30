\# CLAUDE.md — Especificación Maestra del Sistema Web Local CATDIC 2.0



> \*\*ROL DE CLAUDE CODE:\*\* Eres co-desarrollador de `CATDIC-WEB` junto con Codex (ver `COLABORACION.md`).

> \*\*REVISIÓN CRUZADA (sustituye a Gemini):\*\* Claude Code y Codex son co-desarrolladores. Cada tarea la desarrolla uno y la revisa el otro en un Pull Request de GitHub, contra las reglas de ingeniería y los 18 errores recurrentes de este documento. Protocolo completo en `COLABORACION.md`.

> \*\*REGLA DE ORO #1:\*\* NUNCA inventar, estimar ni rellenar datos de ingeniería, dimensiones, ejes, aceros ni fechas. Lo que no esté en planos o en el reporte de visita se marca explícitamente como `"pendiente de verificar"` y se envía a la bandeja de `"Con dudas"`.



\---



\## 1. OBJETIVO Y DECISIONES DE ARQUITECTURA APROBADAS POR STEVEN



1\. \*\*Qué estamos construyendo:\*\* Una \*\*Aplicación Web Local-First Full-Stack\*\* que corre en la PC de Steven (`Windows`, ruta del proyecto `C:\\Users\\Steve\\OneDrive\\Desktop\\CATDIC-WEB`), diseñada para sustituir al 100% el uso de chats manuales de IA y reemplazar definitivamente el antiguo sistema FileMaker.

2\. \*\*Escalabilidad:\*\* Actualmente es de uso personal en la PC de Steven (`http://localhost:8000`), pero la arquitectura (`FastAPI` + `SQLite` + `Frontend Web`) debe mantenerse desacoplada para permitir acceso multiusuario en red local/nube más adelante.

3\. \*\*Acceso a Archivos (Velocidad Máxima):\*\* El backend lee y escribe directamente sobre las carpetas locales sincronizadas de Dropbox en el disco duro de la PC (`C:\\Users\\Steve\\CATDIC Dropbox\\...`), ya que los planos estructurales sellados pesan \~57 MB.

4\. \*\*Alcance Unificado ("Todo de un Golpe"):\*\* El sistema abarca de forma integral las dos líneas de negocio de CATDIC (Supervisión Estructural y Levantamiento Estructural) bajo una misma base de datos y una fábrica modular de documentos.

5\. \*\*Modo 100% Offline y Auditoría:\*\* Una vez extraídos/cargados los datos de diseño de un proyecto, la generación de informes (HTML->PDF con Playwright, edición PDF con PyMuPDF, generación Word `.docx` con lxml/python-docx y procesamiento de imágenes con Pillow) funciona 100% offline y registra cada acción en la tabla `auditoria`.

6\. \*\*Tipografía Oficial en Windows:\*\* Para el formato `CATDIC-STP` (que escribe sobre `FORMULARIOS MIVED.pdf`), usar la fuente nativa de Windows \*\*`Aptos Narrow`\*\* (o `Calibri`/`Arial` según corresponda al formato), sustituyendo las rutas Linux `/usr/share/fonts/.../Carlito` de los scripts antiguos.



\---



\## 2. ESTADO ACTUAL DEL REPOSITORIO (`CATDIC-WEB`)



Ya existen y están corriendo en la PC de Steven:

\- `BACKEND/database.py`: Base de datos SQLite (`catdic\_local.db`) con 7 tablas (`proyectos`, `elementos\_diseno`, `visitas`, `elementos\_visita`, `dudas\_y\_hallazgos`, `ordenes\_trabajo`, `auditoria`) y datos iniciales sembrados (`Terra Living`, `Torre P16`, `Hotel Zoetry Cap Cana · H2 y H5`, `OT-LEV-001`).

\- `BACKEND/reglas\_ingenieria.py`: Motor matemático y normativo (cálculo de recubrimientos, formateo estricto del campo `EJES`, cálculo real de cuantías por sección, agrupación secuencial del log fotográfico, grosor compensado de recuadros rojos, versionado sin sobrescritura `v2`/`v3` y auditor preliminar de los 18 errores).

\- `BACKEND/main.py`: Servidor FastAPI en puerto `8000` con endpoints `/api/dashboard`, `/api/proyectos/{id}` y `/api/visitas/procesar-cola`.

\- `FRONTEND/index.html`: Interfaz web en Vue 3 + Tailwind CSS del tablero \*\*Control Taller 2.0\*\*.



\*\*Regla de Git para Claude Code:\*\* Al finalizar cada submódulo o funcionalidad, haz commits atómicos y descriptivos en tu rama de feature y abre un Pull Request para que el otro agente lo revise (ver `COLABORACION.md`). Nadie hace push directo a `main`.



\---



\## 3. CONTEXTO DE NEGOCIO Y FLUJO DE TRABAJO DE CATDIC



\### 3.1 Quién es quién

\- \*\*CATDIC:\*\* Consultoría y Asistencia Técnica de Ingeniería Civil. Dirección fija en el pie de página de los informes: `Calle Proyecto No.10, Arroyo Hondo Viejo, Santo Domingo D.N.` (es la dirección de CATDIC, NUNCA la de la obra).

\- \*\*Ing. Heriberto Vásquez (HV):\*\* M.Sc., CODIA 27432. Su membrete, logos y estilo definen todos los formatos `HV` de levantamiento. Firma los informes técnicos HV.

\- \*\*MIVED:\*\* Ministerio de Vivienda y Edificaciones (República Dominicana). Recibe los informes de Supervisión Técnica Privada (`STP-MIVED`) y exige los formularios oficiales `FI-01`, `FI-02` y `FI-03`.

\- \*\*Firmas:\*\* El sistema JAMÁS fabrica firmas ni inserta imágenes de firmas manuscritas. Los espacios de firma quedan en blanco (y si se edita un PDF base que traía una firma como anotación, se elimina con PyMuPDF).



\### 3.2 Las 2 Líneas de Producción y sus 7 Formatos Activos



| ID Formato | Línea | Motor Técnico | Descripción y Reglas de Estructura |

|---|---|---|---|

| \*\*1. `STP-MIVED`\*\* | Supervisión | HTML -> PDF (`Playwright`) | Informe para el MIVED (1 PDF por visita). Orden: Portada centrada (sin logo, sin número de pág) + Hoja de Inspección gris claro `#efefef` (sin número de pág) + \*\*2 hojas por elemento\*\* numeradas `1..n` en el pie (Izq: nombre proyecto, Der: pág): \*\*(a) Hoja comparativa\*\* con barra `IMAGEN DE PLANOS APROVADOS DTTL \\| IMAGEN EN OBRA` y tabla `1. INFORMACION ARMADO EN PLANOS \\| 2. IMFORMACION ARMADO EN OBRA` (con esa ortografía exacta del formato original); \*\*(b) Hoja fotográfica\*\* con título `TIPO-ID-EJE...`, fila superior `LOCALIZACION + DETALLE` y debajo cuadrícula 2x2 de hasta 4 fotos (o 1 grande). |

| \*\*2. `CATDIC-STP`\*\* | Supervisión | Overlay vectorial (`PyMuPDF`) | Escribe directamente sobre la plantilla limpia `FORMULARIOS MIVED.pdf` (10 hojas Carta) usando tipografía \*\*`Aptos Narrow`\*\*. Hojas (0-based): `0=MURO`, `1=LOSA`, `2=FUNDACION`, `3=VIGA/PORTICO`, `4=COLUMNA`, `5=ZAPATA` (`2.a=Resistencia Obtenida`), `6=PERFIL\_W`, `7=TUBO`, `8=ANGULAR`, `9=CANAL`. Valores en una sola línea sobre la línea base del rótulo (reducir fuente si no cabe, nunca partir en 2 líneas). Orden: Portada con logo CATDIC arriba + por elemento: Hoja de tabla (plantilla) + Hoja fotográfica con logo CATDIC. |

| \*\*3. `MIVED FI-01/02/03`\*\* | Supervisión | Edición PDF (`PyMuPDF`) | Formularios oficiales MIVED: `FI-01` (cimentación), `FI-02` (losas, escaleras y vigas), `FI-03` (muros y columnas). \*\*Regla clave:\*\* Se genera/actualiza \*\*UN documento por nivel y tipo de elemento\*\* (NO uno por visita). Si ya existe en `FORMULARIOS/MIVED/FORMULARIOS NO FIRMADOS/`, se abre, se agrega la visita nueva en \*Observaciones\* (fecha, parcial/completiva) y se guarda como versión nueva (`v2`, `v3`). En visita completiva se cierra con `"CONFORME A PLANOS APROBADOS"` solo si no hay discrepancias abiertas. Marcar siempre `"Sí"` en encofrados, armaduras de columnas/losas/escaleras, seguridad y probetas; NUNCA marcar ítems de mampostería. |

| \*\*4. `HV-LEV`\*\* | Levantamiento | HTML -> PDF (`Playwright`) | Ficha `"LEVANTAMIENTO"` por defecto para refuerzo en H.A. (1 hoja Carta por elemento, márgenes \~10mm). Encabezado: Fila 1 con `\[Logo HV] \\| LEVANTAMIENTO \\| \[Logo HV]` (título centrado absoluto, logos alineados al eje vertical del título). Fila 2 (franja verde claro, 3 cols): Col 1 `NOMBRE PROYECTO` (sin sufijos de visita/nivel) y debajo `EJES`; Col 2 `FECHA` (`dd/mm/aaaa`) y \*\*debajo `NIVEL :`\*\*; Col 3 `ELEMENTO` y debajo `ID`. Cuerpo: \*\*Bloque 1\*\* (Izq: todas las fotos en cuadrícula con recorte cover individual y gutter; Der: texto plano apilado de OBSERVACIONES) con barra inferior `FOTO DEL LEVANTAMIENTO \\| OBSERVACIONES`. \*\*Bloque 2\*\* (Izq: planta completa LOCALIZACION; Der: DETALLE del plano) con barra inferior `LOCALIZACION \\| DETALLE`. \*\*Proporción estricta:\*\* `Bloque 1 : Bloque 2 ≈ 1.6 : 1` (42% vs 26% de la hoja). Pie: dirección fija de CATDIC. Incluye opción de \*\*Separador de visita\*\* para unir fichas con `pdfunite` en el orden del log. |

| \*\*5. `HV-LEVEVAL`\*\* | Levantamiento (Escáner) | Coordenadas fijas PDF (`PyMuPDF`/`Playwright`) | Para edificaciones existentes sobre planos de levantamiento con \*\*Profometer 650 AI\*\* (ej. Hotel Zoetry H-5). 1 Portada + 1 hoja por escaneo. \*\*Diferencia crítica con HV-LEV:\*\* En la franja verde (y 98-164), `NIVEL :` va en la Columna 3 \*\*junto a `ELEMENTO`\*\* (x≈519), mientras que debajo de `FECHA` va `EJES` (vacío). Bloque A (`LOCALIZACION \\| DETALLE`) arriba (y 167-295); Bloque B (captura Profometer + foto del técnico escaneando, n\_foto = n\_escaneo) en el medio (y 298-517); texto de observaciones debajo (desde y≈520, Arial Narrow 9, sin barra de rótulo). Columna = 3 hojas (`CARA FRONTAL`, `CARA LATERAL`, `ESTRIBOS`); Viga = 2 hojas (`As LONGITUDINAL`, `ESTRIBOS`); Losa maciza = 2 hojas (`DIR. XX`, `DIR. YY`); Muro H.A. = 1 hoja por dirección. |

| \*\*6. `HV-LEVEST`\*\* | Levantamiento (Escáner GPR) | Coordenadas fijas PDF | Para edificaciones con planos estructurales vigentes usando radar GPR \*\*Proceq GP8000\*\* (ej. Vista Bella III, E-11). Hereda el marco de `HV-LEVEVAL` pero con estos \*\*ajustes obligatorios\*\*: (1) `EJES` sí se llena; (2) Agrega barra verde `OBSERVACIONES` debajo del texto y encima del pie (y 721-740); (3) La barra del Bloque B se rotula \*\*`SCANNER`\*\* (izq.) y \*\*`FOTO DEL LEVANTAMIENTO`\*\* (der.); (4) Las capturas llegan de un PDF de \*Report \& Run\* (recorte x0-735, y30-625 sin panel de ajustes; si falta captura se pone texto `SCANNER <n>`); (5) Verifica cantidad de barras/estribos con `PROCEQ GP8000` y en elementos con ≥3 escaneos agrega al final `NOTA:` listando qué es cada escáner. |

| \*\*7. `HV-INFTEC`\*\* | Levantamiento (Informe Completo) | Plantilla `.docx` (`lxml`) + LibreOffice | Informe técnico completo entregado al cliente (ej. Hotel Zoetry H-2 y H-5). Usa `PLANTILLA\_INFORME\_TECNICO\_HV.docx` (conservando logo HV, imagen de fondo arquitectónico completa, marco verde oscuro `#003300` de 4 lados, pie con teléfono `809-794-6979` y barra inferior verde `#00B050`) y un `config.json`. Estructura: Portada -> TOC paginado -> `1.0 UBICACIÓN` -> `2.0 DESCRIPCIÓN` -> `3.0 OBJETIVO` (Variante A licencia o Variante B vulnerabilidad) -> `4.0 SISTEMA ESTRUCTURAL` -> `5.0 PROCEDIMIENTO` -> Divisorias `5.1 Visual`, `5.2 Dimensional`, `5.3 Refuerzo` (+ lámina equipo Profometer o GP8000), `5.4 Esclerometría` (+ lámina Silver Schmidt tipo N) -> `6.0 CONCLUSIONES` (solo discrepancias en dimensional/refuerzo) -> `7.0 ANEXOS`. Las fichas PDF se ensamblan detrás de cada divisoria del cap. 5. |



\---



\## 4. REGLAS INVIOLABLES DE INGENIERÍA Y DATOS (ARCHIVO 02)



1\. \*\*Separación de las 3 Capas:\*\*

&#x20;  - \*\*Capa 1 (Diseño):\*\* Extraída de los planos estructurales sellados una vez por proyecto (`elementos\_diseno`). Las fotos de campo JAMÁS son fuente de datos numéricos de diseño.

&#x20;  - \*\*Capa 2 (Campo):\*\* Extraída del PDF de visita a obra (`elementos\_visita`: ubicación, fotos agrupadas secuencialmente y mediciones en obra sobre el acero).

&#x20;  - \*\*Capa 3 (Cálculos del Programa):\*\* Recubrimientos sumados, cuantías calculadas y recuadros gráficos.

2\. \*\*Metodología de Identificación en Planos:\*\*

&#x20;  - Todo elemento se ubica por \*\*`ID + Nivel + Ejes`\*\* en la hoja de planos cuyo \*\*título impreso dentro de la hoja\*\* corresponda al rango de nivel (ej. `FUNDACIONES @ E-3`, `E3@E8`), nunca confiando a ciegas en el índice general `ES-01`.

&#x20;  - \*\*El detalle propio del elemento manda\*\* sobre cualquier rótulo suelto en la planta. Ante contradicción entre planta y detalle, o si falta una hoja/adenda, el sistema detiene el elemento y crea una `DUDA\_BLOQUEANTE`.

3\. \*\*Regla de Pórticos por Tramo:\*\*

&#x20;  - Un pórtico no tiene ID único; se identifica por su eje (`P1`, `PA`) y \*\*cada tramo entre ejes es un elemento singular con su propia ficha\*\* (ej. `A (2-3)`, `P1 EJE 1 ENTRE MC-A`).

&#x20;  - \*\*Excepción (decisión de Steven):\*\* un mismo tramo puede abrir varios elementos (varias fichas) en el log de la visita cuando el elemento es suficientemente grande o complejo; el sistema no los fusiona.

&#x20;  - El ancho del pórtico se obtiene de los \*callouts\* de sección (`S1`, `S2`...) verificando el control cruzado: `altura sección S + espesor losa contigua = altura total Hv en elevación`.

4\. \*\*Formato Estricto del Campo `EJES`:\*\*

&#x20;  - Columna / Zapata puntual: `EJE <LETRA>-<NÚMERO>` (ej. `EJE F-11`).

&#x20;  - Muro entre dos ejes-letra sobre una fila: `EJE <LETRA>-<LETRA>,<NÚMERO>` (ej. `EJE D-E,4` — con coma, SIN la palabra "FILA" ni paréntesis).

&#x20;  - Viga recta entre dos ejes-número: `EJE <LETRA>, ENTRE <N>-<N>` (ej. `EJE C, ENTRE 2-3`).

&#x20;  - Tramo de pórtico: `EJE <LETRA> ENTRE <N>-<N>` (ej. `EJE F ENTRE 10-11`).

&#x20;  - \*\*Losas (todas) y vigas sin eje-letra:\*\* SIEMPRE `—` (guion largo, sin excepción). En las visitas no se ubican las losas, porque en planta hay una sola de cada una por entrepiso.

&#x20;  - \*\*Platea:\*\* se define como un área: `(<LETRA>-<LETRA>),(<N>-<N>)` (ej. `(A-B),(1-2)`). No lleva `—`.

&#x20;  - \*\*Ejes con prima:\*\* existen ejes como `A'` (y números como `2'`); se escriben tal cual (ej. `EJE A'-1`), con comilla recta `'`.

&#x20;  - \*\*Ejes escritos en la visita:\*\* una etiqueta de visita con un solo token letra+número (`A1`, `1A`, `L5`, `C1`) NO se interpreta: puede ser un cruce de ejes o el ID del elemento (p. ej. `L5` = losa 5), así que ID y EJES quedan `"pendiente de verificar"` y van a la Mesa de Dudas (decisión de Steven, 23/10/2026). El cruce solo se lee cuando la etiqueta trae un ID seguido del cruce (`C1 A4` → ID `C1`, `EJE A-4`; el orden letra/número puede venir cruzado: `C1 4A` → `EJE A-4`). Antes de interpretar se normaliza la prima tipográfica `’` a `'` y se pasa a mayúsculas; la etiqueta original se conserva literal. Lo que no se pueda leer así sin adivinar queda `"pendiente de verificar"`.

5\. \*\*Física de Obra y Recubrimientos:\*\*

&#x20;  - En obra se mide sobre el acero. Para comparar con la dimensión de concreto del plano se suma `2 × recubrimiento`:

&#x20;    - Zapatas, plateas (cimentación) y muros de contención: \*\*0.075 m\*\* por lado (+0.15 m total).

&#x20;    - Columnas, vigas, riostras y muros H.A.: \*\*0.040 m\*\* por lado (+0.08 m total).

&#x20;    - Losas y escaleras: \*\*0.025 m\*\* por lado (+0.05 m total).

&#x20;  - Si `medida\_campo + 2\*rec == valor\_plano`, es \*\*conforme\*\* y en la columna `OBRA` se escribe el valor del plano.

6\. \*\*Cálculo de Cuantía:\*\*

&#x20;  - Siempre calculada matemáticamente por elemento: `As\_total / (b \* h)`. En `STP-MIVED` va en decimal (ej. `0.0185`); en `CATDIC-STP` va en porcentaje (`%`). Jamás copiar cuantías de otros elementos.

7\. \*\*Reglas de los 4 Módulos Visuales Comunes (`M1` a `M4`):\*\*

&#x20;  - \*\*M1 (Fotos):\*\* Agrupación secuencial del log (una foto con etiqueta abre el elemento; las siguientes sin etiqueta le pertenecen). Recorte individual \*cover\* con `Pillow (ImageOps.fit)` al aspecto de su celda con \*gutter\* blanco para no dejar franjas vacías. En `HV-LEV` entran todas las fotos (salvo escaleras: máx 9 repartidas); en `STP-MIVED` hoja fotográfica entran hasta 4 en cuadrícula 2×2 (`pick4` repartidas en la secuencia) o 1 grande.

&#x20;  - \*\*M2 (Observaciones / Tablas):\*\* Prohibida la palabra `"CORRIDO"` en rótulos de acero. Toda viga/riostra/pórtico lleva obligatoriamente `ESTRIBOS` al final. En `HV-LEV` las columnas llevan el rótulo exacto `ESTRIBOSS` (con doble S). En `HV-LEV` las losas aligeradas incluyen la imagen `LOSA TÍPICA` (\~150px) indicando `APOYO 1` (arriba), `APOYO 2` (abajo), `APOYO 3` (derecha), `APOYO 4` (izquierda).

&#x20;  - \*\*M3 (Localización):\*\* Planta estructural completa del nivel (nunca un zoom irreconocible), dibujando recuadro(s) rojo(s) `RGB(220,0,0)` cuyo grosor en la imagen fuente compense el factor de reducción (`grosor\_fuente = 4.5 px / factor\_escala`, típicamente `width=22` en plantas de 200 dpi).

&#x20;  - \*\*M4 (Detalle):\*\* Siempre recorte nítido del plano estructural (sección, elevación del tramo + banda inferior de estribos pegada debajo, o tabla de aplicación con la fila del elemento resaltada en rojo). En muros con elementos de borde, rotular `"1"`, `"2"` sobre la imagen. Nunca poner una foto de campo en `DETALLE`.



\---



\## 5. ESTRUCTURA DE CARPETAS DE DROPBOX Y NOMENCLATURA DE SALIDA



\### 5.1 Rutas Locales en la PC de Steven

\- Raíz Dropbox: `C:\\Users\\Steve\\CATDIC Dropbox\\`

\- Proyectos de Supervisión: `C:\\Users\\Steve\\CATDIC Dropbox\\SUPERVISION\\EN CURSO\\<PROYECTO>\\`

&#x20; - Planos sellados vigentes: `ARCHIVOS DEL CLIENTE\\PLANOS ESTRUCTURALES\\PLANOS SELLADOS\\`

&#x20; - Visitas a obra: `LEVANTAMIENTO\\VISITA A OBRA\\<N. ELEMENTOS NIVEL PARCIAL|COMPLETIVO DD-MM-AAAA>\\`

&#x20; - Salida de informes procesados: `INFORMES\\2.DATA PROCESADA\\`

&#x20; - Formularios MIVED no firmados: `FORMULARIOS\\MIVED\\FORMULARIOS NO FIRMADOS\\`

&#x20; - Formularios MIVED firmados: `FORMULARIOS\\MIVED\\FORMULARIOS FIRMADOS\\`



\### 5.2 Reglas de Nombres de Salida y Peso

\- \*\*Jamás sobrescribir un archivo existente:\*\* Si el archivo ya existe en `INFORMES\\2.DATA PROCESADA\\`, agregar sufijo ` v2.pdf`, ` v3.pdf`.

\- \*\*Nombre STP-MIVED:\*\* `<Proyecto> - STP - <Elementos nivel> - DD-MM-AAAA.pdf` (ej. `Terra Living - STP - Verticales Sotano S4 Parcial - 11-09-2026.pdf`).

\- \*\*Nombre MIVED FI:\*\* `MIVED - <PROYECTO>-<ELEMENTOS NIVEL>.PDF` (ej. `MIVED - TERRA LIVING-LOSAS Y VIGAS PARCIAL SOTANO -3.PDF`).

\- \*\*Peso máximo:\*\* Todo PDF generado debe pesar \*\*< 30 MB\*\* (redimensionar fotos de campo a máx `1000×1000 px`, `JPG quality=72`, con `ImageOps.exif\_transpose`).

\- \*\*Formato de fecha:\*\* Siempre `DD/MM/AAAA` en todos los informes.



\---



\## 6. CHECKLIST DE LOS 18 ERRORES QUE EL AUDITOR BLOQUEARÁ



El módulo `auditor\_18\_errores` debe verificar programáticamente antes de dar por bueno cualquier PDF:

1\. `LOCALIZACION` con recorte/zoom en vez de planta completa o nivel equivocado.

2\. `DETALLE` con foto de campo en vez de imagen del plano o recorte ilegible.

3\. Cuadrícula de fotos con franjas blancas, sin gutter o incompleta.

4\. Recuadro rojo de localización invisible a tamaño final.

5\. Título `LEVANTAMIENTO` descentrado o logos HV desalineados verticalmente.

6\. Bloques 1 y 2 de igual altura en `HV-LEV` (debe ser `1.6 : 1`).

7\. `NIVEL` mal ubicado (`bajo FECHA` en HV-LEV vs. `junto a ELEMENTO` en HV-LEVEVAL/LEVEST).

8\. `NOMBRE PROYECTO` con sufijos de visita o nivel en `HV-LEV`.

9\. Palabra `"CORRIDO"` en acero; viga sin `ESTRIBOS`; `ACERO ADICIONAL` combinado con `"+"`.

10\. Cajas editoriales prohibidas en la ficha (`"Referencia de Plano"`, `"Fuente de los datos"`, `"Verificación en campo"`).

11\. Ejes de losa distintos de `—` o eje deducido por proximidad visual.

12\. Cuantía copiada sin calcular; fecha en formato `M/D/AAAA`; columna `OBRA` sin corrección por recubrimiento.

13\. Mezclar cabeceras, rótulos u hojas entre formatos distintos (`HV`, `STP-MIVED`, `CATDIC-STP`, `HV-LEVEVAL`).

14\. Valores de cabecera en `CATDIC-STP` superpuestos al rótulo o partidos en dos líneas.

15\. PDF final `> 30 MB` o archivo existente sobrescrito sin crear `v2`.

16\. Firmas fabricadas o firmas previas no borradas en los `FI MIVED`.

17\. Ítems de mampostería marcados en los `FI MIVED` o falta de los `"Sí"` obligatorios.

18\. Rehacer desde cero un `FI MIVED` que ya existía para ese nivel/tipo en lugar de actualizarlo.



\---



\## 7. HOJA DE RUTA DE DESARROLLO PARA CLAUDE CODE (ORDEN DE EJECUCIÓN)



Trabajar por etapas verificables, con un Pull Request al terminar cada una, revisado por el otro agente (ver `COLABORACION.md`):

\- \*\*Etapa 1 (Sincronizador Real de Dropbox + Ingesta):\*\* Conectar el endpoint `/api/dropbox/sync` en `BACKEND/main.py` para que escanee las carpetas reales de `C:\\Users\\Steve\\CATDIC Dropbox\\SUPERVISION\\EN CURSO\\TERRA LIVING` (y demás proyectos), detecte automáticamente los planos sellados y pueble la tabla `visitas` con las visitas reales (#1 a #20) y sus estados en el Frontend.

\- \*\*Etapa 2 (Importador de Datos de Diseño):\*\* Crear el parser/importador que cargue en la tabla `elementos\_diseno` toda la información y coordenadas de planos ya documentadas de \*\*Terra Living\*\* (S5, S4, S3, columnas, muros, pórticos, losas) y \*\*Torre P16\*\* (Losa E-9).

\- \*\*Etapa 3 (Fábrica de Supervisión: `STP-MIVED` + `MIVED FI-01/02/03` + `CATDIC-STP`):\*\* Integrar como módulos limpios y parametrizados en `BACKEND/generators/` la lógica probada de `stp.py`, `vert.py`, `fi02.py` y `catdic\_stp.py` (con `Aptos Narrow`), conectada al botón \*\*"Procesar Cola"\*\* y a la \*\*"Mesa de Dudas"\*\* en la interfaz web.

\- \*\*Etapa 4 (Fábrica de Levantamiento: `HV-LEV` + `HV-LEVEVAL/LEVEST` + `HV-INFTEC`):\*\* Integrar el generador de fichas HV, el generador de parte teórica en Word (`generar\_informe\_hv.py`) y la pantalla \*\*"Estudio de Ensamble"\*\* para cerrar informes completos como \*\*Hotel Zoetry Cap Cana (H2 y H5)\*\*.

