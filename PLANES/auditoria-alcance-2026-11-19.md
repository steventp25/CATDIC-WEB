# Auditoría del alcance de CATDIC-WEB

19/11/2026. Auditoría del documento `alcance-catdic-web-2026-11-19.md`, con comparación de documentación oficial pública. No es una auditoría del código, una certificación ISO ni una prueba de los productos citados. Hallazgos y recomendaciones no equivalen a aprobación de implementación. Dropbox no se ha modificado.

## Veredicto

El documento sirve de traspaso de intención, pero todavía no es un plan ejecutable y verificable. Su mayor riesgo es construir pantallas y módulos antes de cerrar el recorrido compartido: pedido → fuentes y revisiones → preparación → revisión → emisión → seguimiento de cambios. No hace falta redefinir todo el producto: cerrar ese recorrido en una entrega pequeña y conservar el resto como evolución.

## Lagunas y correcciones propuestas

| Prioridad | Hallazgo en el documento | Consecuencia | Corrección propuesta |
|---|---|---|---|
| Alta | §2 mezcla bases firmes, hechos y orientaciones que pueden variar; §4 y §7.1 agregan decisiones actuales | Un ejecutor puede tratar necesidades actuales como opcionales o soluciones propuestas como fijas | Separar bases del producto, necesidades vigentes, hechos observados y soluciones abiertas. Que una decisión pueda revisarse no significa que deje de orientar el trabajo actual |
| Alta | §4 permite pedir cualquier extracción, pero no define cuándo se completó el pedido | Un popup termina convertido en chat sin resultado comprobable | Registrar propósito, resultado esperado, fuentes seleccionadas, cobertura entregada, faltantes y dudas. Proponer tipos reutilizables de pedido, conservando solicitudes libres |
| Alta | §4 propone extraer una vez por revisión | Un plano parcialmente analizado podría parecer completamente preparado | Registrar cobertura por pedido, elemento y fuente; reutilizar lo revisado y analizar lo que falta |
| Alta | §7.1 pide sincronización continua, sin recorrido de fallos | Archivos nuevos, movidos o inaccesibles pueden dejar datos viejos sin aviso | Distinguir nuevo contenido, nueva revisión, movimiento, ausencia y falta de permisos; mostrar última sincronización y errores; reconciliar sin confirmar datos ni borrar historial |
| Alta | §7 no define quién puede preparar, revisar, autorizar, entregar o administrar acceso | Personalizar visibilidad podría quedar reducido a ocultar botones | Definir permisos efectivos por obra y acción, también en búsquedas, vistas previas, descargas y paquetes enviados a IA; comprobar revocaciones |
| Alta | Estados de datos, trabajos y documentos no están separados | «Procesado» puede confundirse con «correcto» o «autorizado» | Definir estados distintos y transiciones con responsables. Propuesta de trabajo: solicitado → preparado → en revisión → corregir/aprobado; emisión y entrega se registran aparte |
| Alta | §10 prueba principalmente generar un informe | Puede pasar el piloto sin demostrar colaboración ni continuidad documental | Añadir segundo revisor, reimportación, cambio de fuente y recuperación de evidencia de lo emitido |
| Alta | Operación de IA sigue abierta; no hay recorrido ante cupo agotado o resultado incompleto | La plataforma podría depender de una integración inexistente | Probar un modo autorizado concreto; guardar progreso, permitir continuar y corregir, evitar duplicados y no exigir reextraer todo. No prometer automatización central con Pro |
| Media | §5 describe una captura futura junto a la importación actual | Riesgo de pedir al técnico repetir Report and Run | Importar primero el reporte existente y pedir solo aclaraciones. Evaluar nueva captura como propuesta separada |
| Media | §2.9 y §8 resumen de forma distinta la madurez GPR | Confundir visor preparado para evaluación con integración concluida | Usar la aclaración más reciente: visor evolucionando y suficientemente formado para evaluar integración. Definir evidencia mínima y permisos antes de acoplar toda su interfaz |
| Media | No se especifica qué conserva una emisión | Historial que apunta al archivo actual no permite reconstruir una entrega pasada | Conservar datos aprobados, fuentes/revisiones, plantilla y reglas utilizadas, revisor y documento emitido; resolver conservación autorizada de las fuentes sin publicar datos reales en Git |
| Media | Teoría, gestión y búsqueda son categorías amplias | El desarrollo puede abarcar un ERP o generar textos sin respaldo | Acotar primer servicio e informe, capítulos necesarios y búsqueda verificable. No incluir contabilidad, CRM o calendario general sin encargo |
| Media | Respaldo, recuperación y ediciones simultáneas quedan fuera del recorrido | Trazabilidad aparente si se pierde la base o se pisan correcciones | Definir y probar recuperación de archivos y metadatos, conflictos de edición y continuidad cuando Dropbox o la IA no estén disponibles |

Un archivo modificado no implica que todo informe anterior sea incorrecto: señalar dependencias afectadas y registrar una evaluación humana. Tampoco se debe sustituir automáticamente lo emitido por contenido nuevo.

## Comparación con experiencias similares

| Referencia consultada | Comportamiento documentado | Patrón aplicable a CATDIC | Límite |
|---|---|---|---|
| [Fieldwire: tareas](https://help.fieldwire.com/hc/en-us/articles/360003458332-Introduction-to-Tasks) y [reportes](https://help.fieldwire.com/hc/en-us/articles/360040915311-Practical-Guide-How-to-configure-tasks-for-great-reports) | Tareas con ubicación, fotos, archivos, historial y atributos; reportes filtrados desde esa información | Registrar una observación una vez y reutilizarla en revisión e informe | No demuestra interpretación estructural de planos ni formatos CATDIC |
| [PlanRadar: formularios](https://help.planradar.com/en/create-edit-forms/) y [reportes](https://help.planradar.com/en/ticket-reports/) | Formularios configurables, campos compartidos y condicionales; reportes desde registros seleccionados | Pedidos guiados por propósito, controles comunes y salida reutilizable, sin formularios gigantes | Es un patrón funcional, no propuesta de compra o de copiar sus campos |
| [Autodesk Docs: revisión](https://help.autodesk.com/cloudhelp/ENU/Docs-Reviews/files/getting-started-reviews/Reviews_Create_Edit.html) | Flujos de uno o varios pasos, con revisión y aprobación diferenciadas; cambios de flujo aplican a nuevas revisiones iniciadas | Responsables y criterios explícitos; conservar qué procedimiento rigió una aprobación pasada | No obliga a muchos pasos para cada trabajo ni prueba cumplimiento ISO |
| [Dropbox: detectar cambios](https://docs.dropboxapi.com/dropbox-api/docs/detecting-changes) | Cursores para cambios, longpoll y webhooks; notificaciones de archivos no cubren por sí solas cambios de permisos | Actualización incremental y reconciliación, con tratamiento separado de acceso | API es una opción técnica aún no elegida; lectura local necesita diseño propio equivalente |
| [Microsoft: evaluación de extracción](https://learn.microsoft.com/en-us/legal/cognitive-services/document-intelligence/characteristics-and-limitations) | Recomienda pruebas representativas del caso y revisión humana según resultados evaluados | Conjunto de casos reales, medir omisiones, asociaciones erróneas y esfuerzo de corrección | Sus métricas OCR no validan razonamiento estructural ni se transfieren a Claude; no adoptar umbrales genéricos |

El patrón común es información reutilizable con contexto, revisión y salida controlada. La IA puede aportar interpretación flexible, pero no reemplaza identidad, permisos, historial y reglas verificables. No se propone sustituirla por patrones rígidos de lectura.

## Metodología mínima propuesta

- ISO 19650: distinguir trabajo en elaboración, compartido y uso autorizado; adaptar equivalencias a los circuitos actuales, sin mover carpetas por defecto.
- ISO 9001: preparación, revisión, liberación, control de cambios y discrepancias. [Guía oficial de información documentada](https://www.iso.org/files/live/sites/isoorg/files/standards/docs/en/iso_9001_2015_guidance_documented_information.pdf).
- ISO 15489: preservar registros, contexto, metadatos y responsabilidades. [Referencia del comité oficial](https://committee.iso.org/sites/tc46sc11/home/projects/published/iso-15489-records-management.html).
- Aplicación propuesta: expediente por obra, trabajo con resultado esperado, fuentes versionadas, revisión con responsable y emisión recuperable. Es una adaptación de producto, no una declaración de cumplimiento normativo.

## Próxima entrega concreta propuesta

Una obra, una visita existente de Report and Run, una revisión de plano, un elemento y una ficha de formato ya soportado. Primero un recorrido completo y después su prueba de continuidad; no integrar todos los módulos a la vez.

1. Buscar fuentes dentro de la obra mostrando revisión, procedencia y acceso; conservar la secuencia del reporte y las ubicaciones que incluya. El ejemplo que Steven ofrecerá sigue pendiente de verificar.
2. Pedir una extracción concreta; confirmar qué falta, qué ya está revisado y qué fuentes se utilizarán. Usar una modalidad de IA autorizada sin gasto nuevo.
3. Importar propuesta parcial o completa, con evidencia localizable y dudas; corregir sin transcribir todo; comprobar importación repetida y rechazo de resultados de otra obra o revisión incompatible.
4. Registrar autor y revisor con identidades diferenciadas; comprobar acceso por obra. Generar una versión sin sobrescribir y bloquear la emisión ante dudas bloqueantes.
5. En copias de prueba, añadir una fuente, mover otra y modificar contenido. Comprobar actualización, conservación de identidad, señal de reevaluación y recuperación intacta de la entrega anterior.
6. Medir omisiones, asociaciones incorrectas, dudas no detectadas, correcciones, tiempo completo y esfuerzo de mantenimiento frente al caso conocido. No fijar porcentajes de aceptación sin evidencia.

GPR puede probarse como evidencia externa revisada cuando exista una salida autorizada disponible; no condicionar este primer recorrido a integrar todo el visor. La integración completa sigue siendo un trabajo separado.

## Decisiones de alcance que sí requieren a Steven

1. Primer servicio, formato y caso real que representen el trabajo que quiere trasladar de Claude.
2. Quién puede aprobar datos y autorizar emisión, y qué entregas requieren otra persona revisora.
3. Modalidad de IA y cuentas autorizadas para ese primer recorrido, manteniendo gasto adicional no autorizado.

Los mecanismos internos de sincronización, identificadores y diseño de formularios deben proponerse concretamente por los desarrolladores; no trasladar cada elección técnica a Steven. La navegación se valida con estos recorridos, no se considera cerrada por el documento anterior.

## Consejo y límites

Cinco lecturas independientes coincidieron en que el piloto actual puede probar generación sin probar plataforma. La revisión anónima contrastó jerarquía de decisiones, cobertura por pedido, trabajos independientes, continuidad documental e integración GPR. No apareció desacuerdo sustantivo sobre los vacíos centrales; no se presenta esa coincidencia como cinco pruebas independientes del comportamiento del software. El alcance de esta auditoría es documental.

Recomendación: conservar la visión y corregir el siguiente corte verificable antes de ampliar módulos o rehacer el layout completo. Confianza alta en los vacíos del documento; limitada respecto de funciones actuales del código, que no se reauditaron aquí. Un ejemplo real de Report and Run y una demostración actual de GPR podrían cambiar detalles de integración y esfuerzo.
