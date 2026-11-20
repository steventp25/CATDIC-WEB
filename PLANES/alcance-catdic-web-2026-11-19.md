# CATDIC-WEB — ajustes de alcance y traspaso a Claude

Fecha: **19/11/2026**. Encargo de Steven a Codex: «todo lo que desarrollamos y analizamos lo coloques en el repo para explicarle a Claude los ajustes del alcance de CATDIC-WEB».

Este documento registra la conversación y la investigación. No acredita nuevas funciones implementadas ni autoriza despliegues, contrataciones, eliminación de código o reanudación automática de las fases detenidas. Su publicación está solicitada; la implementación de las propuestas se acuerda por el flujo de `PLANES/` y `COLABORACION.md`.

**Para Claude:** el punto de partida es trasladar a la aplicación el proceso con el que Claude ya entrega informes completos a Steven. No volver a definir el trabajo como si ese proceso no existiera.

## 1. Cómo leer este ajuste

- **Confirmado por Steven:** declaración explícita del usuario en esta conversación, o instrucción previa enlazada en GitHub.
- **Propuesta:** recomendación discutida; no equivale a aprobación de arquitectura o ejecución.
- **Verificado en código:** observación de `origin/main`, commit `b5f7d26`, tras `git fetch` del 19/11/2026. Las ramas y documentos locales pueden tener avances adicionales.
- **Investigación externa:** capacidad descrita por su proveedor; no es una prueba de precisión sobre los documentos CATDIC. Condiciones y disponibilidad deben comprobarse al implementar.

No usar las tablas de estado antiguas de `COLABORACION.md`, los borradores locales del mapa ni métricas históricas de GPR como certificación del estado actual. Este ajuste sustituye las premisas incompatibles de planes anteriores; no cambia las reglas de ingeniería, firmas, fuentes ni versionado.

## 2. Lo que Steven confirmó

**Corrección de Steven, 19/11/2026:** los puntos **1 y 3** son las bases que mantiene fijas. Los demás registran la orientación discutida y pueden variar; no tratarlos como decisiones irrevocables. Siguen vigentes las reglas de ingeniería y las restricciones de gasto mientras no se autorice cambiarlas.

1. **CATDIC-WEB es el sistema principal**, con herramientas especializadas, incluido GPR. La finalidad es que lo usen sus compañeros y jefes para organizar el trabajo y ampliarlo después con otros módulos.
2. Steven plantea distinguir **Gestión de proyectos, Generación de informes y Teoría/contenido técnico**. La separación exacta y sus límites siguen como propuesta de producto, no como módulos construidos.
3. **«Claude me hace mis informes completamente. Lo que quiero hacer es llevarlo a CATDIC-WEB».** La referencia funcional debe ser un trabajo completo que ya salió bien: entradas, instrucciones, preguntas, revisiones y documento final.
4. **La interpretación y extracción de datos de los planos la hará una IA.** Steven quiere retirar el enfoque de interpretar planos mediante patrones rígidos de texto o disposición, porque los planos no se organizan igual.
5. **El programa genera los informes** a partir de los datos extraídos y revisados. La IA participa en interpretar y preparar información; no sustituye las reglas matemáticas ni las comprobaciones del programa.
6. **En campo utilizan Report and Run.** Ya se identificaban elementos en el reporte o se ubicaban sobre una planta dibujando sus posiciones. No describir esas prácticas como funciones nuevas pendientes de introducir. Steven aportará un ejemplo para comprobar cómo se conservan las asociaciones en los archivos disponibles; su interpretación concreta queda pendiente de verificar.
7. **La cuenta de Claude de CATDIC es Claude Pro** y se usa para desarrollar. Steven quiere evitar que la producción de informes agote ese cupo. Se mantiene la restricción de **no pagar adicional**; no se autorizaron claves API ni servicios nuevos.
8. Steven propuso que los compañeros usen su propia IA con un prompt preparado por el programa, y contempló introducir información a mano, señalando la dificultad de transcribirla toda. Son alternativas a concretar; no se ha aprobado una conexión central compartida.
9. Steven indica que **el visor GPR seguirá actualizándose, pero tiene suficiente forma para evaluar una posible integración**. No exigir que cese su desarrollo para integrarlo ni presentar la integración como implementada o aprobada técnicamente por este documento.

**Cuenta de CATDIC:** su posible uso como IA del proyecto sigue abierto, ya que CATDIC paga la cuenta. No confundir titularidad o pago con el mecanismo técnico permitido para integrar una suscripción. Evaluar opciones y cupo; no dar por descartada esa cuenta ni por autorizados gasto adicional, API o uso compartido de credenciales.

## 3. Producto y módulos: organización propuesta

CATDIC-WEB se propone como **plataforma de trabajo de CATDIC**, que organiza proyectos y trabajos independientes, conserva fuentes, reúne resultados técnicos y permite preparar, revisar y entregar informes.

| Módulo propuesto | Responsabilidad | Qué comparte |
|---|---|---|
| Gestión de proyectos | Obras, clientes, responsables, tareas, fechas, pendientes, avances y cierre | Identidad del proyecto y trabajo |
| Planos y levantamientos | Planos y revisiones, visitas, fotos, elementos, mediciones y sus fuentes | Expediente técnico |
| GPR | Procesamiento, visualización e interpretación de escaneos; resultados revisados con procedencia | Evidencias que pueden incorporarse al informe |
| Teoría y contenido técnico | Objetivos, descripción, metodología y capítulos preparados desde textos aprobados, edición o IA | Secciones revisables y versionadas |
| Informes y ensamble | Fichas, formularios, teoría, evidencias, anexos, revisión y versiones de entrega | Documentos finales |

**Base común propuesta:** cuentas individuales, permisos por proyecto y acción, documentos, historial, versiones y auditoría por persona. Evitar registrar la misma obra o elemento de nuevo en cada módulo.

No confundir módulos de negocio con botones independientes ni con servidores obligatoriamente separados. Se recomendó evolucionar FastAPI/Vue conservando lo construido y conectar GPR gradualmente; no se aprobó migrar a otro framework, microservicios o una plataforma empresarial.

Teoría debe poder **preparar contenido**, no ser solo una biblioteca. Plantillas y datos conocidos pueden llenarse sin IA; descripciones particulares pueden escribirse o redactarse con ayuda. Interpretaciones y conclusiones requieren fuentes y revisión técnica. La forma concreta de edición está por acordar.

### Navegación anterior, abierta a revisión

La instrucción de Steven en el [PR 31](https://github.com/steventp25/CATDIC-WEB/pull/31#issuecomment-6927916623) establece:

- Principal: **Inicio · Mis obras · Bandeja de trabajo · Informes · Configuración**, con **Crear informe** permanente.
- Dentro de la obra: **Resumen · Visitas y trabajos · Planos y ficha · Avance · Informes · Cierre**.
- Bandeja común para los pendientes, sin duplicar registros.
- Informes y trabajos independientes, con fuentes, dudas, versiones e historial, vinculables posteriormente a una obra.
- Tres indicadores: avance por entrepisos, expediente completo y documentación al día. Sus evidencias y unidades siguen pendientes; no inventar porcentajes ni sustituir cobertura por número de archivos o visitas.

**Steven aclara que esta navegación puede variar:** la considera insuficientemente sólida. La lista anterior es un antecedente, no una restricción para el nuevo diseño. Proponer la estructura según los recorridos reales por obra, permisos y tareas. No se ha elegido una nueva maqueta ni se declaran implementadas esas pantallas.

## 4. IA para los planos: qué cambia y qué se conserva

**Alcance de la extracción solicitado por Steven:** la IA debe preparar lo que el usuario necesite, tanto de planos como de visitas disponibles. La interacción planteada es un diálogo que pregunte qué extraer y de qué fuentes o visitas; sus controles y límites siguen por diseñar. No limitar el producto a una extracción fija idéntica para todas las obras ni interpretar «lo que necesite» como autorización para inventar datos o extraer información no presente.

**Recorrido propuesto:** elegir obra → solicitar información → seleccionar o confirmar planos, revisiones y visitas → IA prepara datos y dudas con fuentes → revisión humana → reutilizar en visor, contenido técnico e informes. Mostrar lo ya preparado y los faltantes para evitar repetir análisis. Validar este recorrido con el ejemplo real de Report and Run cuando Steven lo aporte.

**Dirección confirmada:** reemplazar la interpretación basada en patrones de tablas, posiciones o expresiones regulares por interpretación de IA que pueda trabajar con hojas distintas, relaciones entre plantas/detalles y contexto.

**Conservar:** abrir archivos y leer su contenido, preparar imágenes y recortes, identificar revisión y páginas, guardar fuentes, importar resultados, mostrar dudas, aplicar validaciones y calcular. Extraer texto de un PDF como material para la IA no es lo mismo que interpretar su estructura mediante reglas rígidas.

No ejecutar ahora una eliminación indiscriminada de `lector_plano.py`, `extractor.py` o `reglas_ingenieria.py`. Claude debe identificar sus responsabilidades y proponer la sustitución del camino de interpretación con una prueba real antes de retirar código en uso.

La IA debe entregar propuestas ligadas al plano y su revisión, con evidencia localizable. El formato exacto queda por definir con el caso piloto. **Validar la estructura de una respuesta o que un número aparezca en una hoja no demuestra que corresponda al elemento correcto.** Revisar también identidad, nivel, ejes, detalle aplicable, unidades y contradicciones.

El enfoque antiguo de la Etapa 5 que limitaba toda interpretación a citar un token exacto debe revisarse: las fuentes siguen siendo obligatorias, pero no debe impedir trabajar con dibujos, varias cotas o referencias cruzadas. Una transformación de unidades o cálculo corresponde al programa y debe conservar su entrada y su regla; no se acepta un valor inventado.

**Propuesta de ahorro:** extraer y revisar una vez por revisión de plano, reutilizar lo aprobado en las visitas y reanalizar cuando cambie la fuente. No enviar todo el plano a la IA en cada informe ni suponer que un plano nuevo ya está revisado.

## 5. Visitas: conservar Report and Run y entender lo que ya registra

No pedir a Steven que sustituya Report and Run para empezar. El primer flujo debe recibir sus archivos actuales y reproducir la interpretación que Claude ya realiza.

### Lo que existe y sus límites

El lector `BACKEND/sync/lector_visita.py` recupera foto, etiqueta, nota y hora de un PDF con una estructura conocida. Agrupa la etiqueta de apertura con las fotos siguientes y reconoce pocos patrones de identificación. No hay una interpretación general con IA integrada.

El reconocimiento existente (`PLANES/etapa-3-reconocimiento-visita.md`) documenta:

- Etiquetas como «Pórtico eje 4» seguidas de «Tramo D-B», IDs como «Losa 13» y observaciones libres.
- Fotos sin etiqueta y etiquetas que no distinguen una ubicación de una instrucción.
- Una contradicción entre el cambio de peralte descrito en la etiqueta y en la nota.
- Horas que no son monótonas en una visita: **no reordenar el reporte por hora** y perder su secuencia editorial.

La IA puede proponer agrupaciones y relacionar el contexto entre etiquetas; lo ambiguo o contradictorio no queda confirmado por mera proximidad. Una foto de una columna no acredita por sí misma su ID, nivel ni ejes. Las fotos de campo nunca son fuente de datos numéricos de diseño.

### Recorrido futuro propuesto, no implementado

1. Elegir proyecto y nivel; identificar un elemento una vez por grupo de fotos, por selección, texto o ubicación confirmada.
2. Tomar las fotos y añadir notas del elemento; abrir otro grupo al pasar al siguiente, sin repetir todos los datos en cada foto.
3. Conservar revisitas al mismo elemento y el orden del recorrido, sin fusionar automáticamente grupos o fichas.
4. Revisar las propuestas de la IA y los faltantes antes de generar el informe.

Una ruta marcada y sus paradas pueden aportar contexto. Reconstruir automáticamente ubicación desde fotos sueltas es otra capacidad y no está demostrada. La ruta de la cámara tampoco identifica necesariamente el objeto al que apunta.

Comprobar la versión y las exportaciones de Report and Run: la documentación de **Cloud** describe propiedades personalizadas por imagen, pero no está confirmado que existan en la versión utilizada por CATDIC. Comparar el PDF y cualquier exportación disponible; elegir la que conserve fotos, texto, orden y asociaciones. No exigir campos o archivos que la aplicación actual no entregue.

## 6. Modelo de operación de IA y cupo de desarrollo

**Restricción vigente:** ninguna clave API, nuevo servicio de pago ni gasto adicional autorizado. No solicitar, copiar ni publicar credenciales. No habilitar consumo adicional ni usar una suscripción compartida como sustituto de una integración aprobada.

### Opciones discutidas

| Opción | Cómo se materializa | Estado y límite |
|---|---|---|
| Paquete de trabajo y propia IA | CATDIC-WEB prepara fuentes, instrucciones y salida esperada; el compañero usa su IA y devuelve el resultado | **Recomendación inicial** para probar; no consume la cuenta de desarrollo si se usa otra cuenta autorizada |
| Conector a la IA de cada usuario | Su Claude consulta herramientas y devuelve propuestas al sistema mediante MCP | **Propuesta posterior**; requiere construir conector, permisos y acceso al servidor; no equivale a un motor central en la web |
| IA central por API | El servidor ejecuta los análisis y contabiliza el consumo de la empresa | **Alternativa futura, no autorizada** bajo la restricción actual |
| Introducción manual | Completar y corregir datos o redactar secciones dentro del sistema | **Alternativa de apoyo**; no proponer transcribir todos los planos como recorrido principal |

La investigación confirma que Claude y Claude Code comparten límites dentro de una misma suscripción. Otro chat o proyecto no separa los cupos. La cuenta confirmada es **Claude Pro** y no tiene los créditos mensuales de API que la documentación actual ofrece a otros planes elegibles. No suponer que mejorar de plan, usar un conector o un SDK crea capacidad ilimitada.

Usar Claude Code personalmente para procesar archivos y convertir una sola cuenta en un servicio para todos son casos distintos. Las condiciones actuales restringen canalizar peticiones de otros mediante credenciales individuales. Los asientos Team también son nominales. No construir un proxy que reutilice sesiones o tokens de la cuenta de Steven.

Un conector MCP permitiría que cada usuario trabaje desde su propia IA y con sus permisos de CATDIC-WEB. Los conectores remotos de Claude se conectan desde la infraestructura de Anthropic: una dirección privada o `localhost` no basta. El mecanismo local de Claude Desktop es distinto. Evaluar ambas posibilidades, sin exponer el servidor ni prometer compatibilidad sin una prueba.

### El paquete debe ser un trabajo completo, no solo un prompt

**Propuesta:** incluir instrucciones derivadas del proceso de Steven, fuentes y revisión, lotes manejables de hojas/fotos y un formato de devolución que pueda importar el sistema. El usuario no debe reparar estructuras técnicas a mano ni reorganizar el expediente cada vez.

Tras importar, mostrar datos, fuentes y dudas. Conservar originales y registrar qué modelo/proveedor propuso el resultado y quién lo revisó. Importar un archivo válido no confirma la verdad de los valores. La compatibilidad con otras IA y su capacidad de leer documentos debe medirse; no asumir igual calidad entre modelos. Utilizar solo cuentas y proveedores autorizados para los datos de los clientes.

Reutilizar información ya revisada; no regenerar planos, notas y teoría sin necesidad. Conservar instrucciones y textos aprobados con versión para saber qué cambió.

## 7. Uso por compañeros y jefes

El objetivo multiusuario está confirmado; **no está construido**. En `main` la auditoría todavía utiliza un usuario fijo (`steven`), y la aplicación depende de archivos y configuración locales.

**Propuestas:** técnico con sus trabajos, revisor con sus pendientes y dirección con visión global de responsables, entregas y bloqueos. Los permisos concretos siguen por definir. No presentar como listo para empleados un tablero que solo cambia visualmente.

Preservar la generación sin IA una vez disponibles los datos revisados. Los pasos que requieren IA pueden necesitar conexión; esto no convierte todo el sistema en offline ni autoriza sustituir el funcionamiento local antes de evaluar el alojamiento.

La cuestión de servidor, persistencia, cuentas y publicación sigue registrada en el [issue 32](https://github.com/steventp25/CATDIC-WEB/issues/32). Evaluar el servidor de la empresa y la concurrencia antes de elegir alojamiento o migrar datos. Este documento no decide Vercel, una base nueva ni un despliegue.

## 7.1. Decisión de Steven: organización y trazabilidad comunes con Dropbox

**Actualización continua:** Steven señala que diariamente se incorporan archivos a Dropbox. La organización no puede ser una importación única. El diseño debe contemplar detectar incorporaciones y cambios, reconciliar el índice y señalar fuentes nuevas o modificadas y resultados afectados, sin aprobarlos automáticamente ni sobrescribir información revisada. Frecuencia, mecanismos de sincronización y gestión de conflictos quedan por definir; no se declara implementada esta capacidad.

**Confirmado el 19/11/2026:** aplicar en Dropbox y CATDIC-WEB una metodología común de organización y trazabilidad, tomando aspectos de ISO 19650, ISO 9001 y gestión documental. El objetivo es encontrar y utilizar información de las obras con la menor fricción posible. Esto no declara conformidad ni certificación con esas normas.

La obra es el contexto principal: sus planos, visitas, elementos, resultados e informes deben poder relacionarse. La organización debe aprovechar la adaptación BIM ya existente en Diseño y los circuitos de Supervisión y Levantamiento, sin exigir al usuario memorizar rutas de carpetas.

**Aplicación propuesta, pendiente de diseño y validación:**

- Identidad estable de obra y documentos, con equivalencias para nombres y códigos existentes; buscar por nombre conocido, elemento, nivel, ejes, fecha, tipo y estado cuando esos datos estén disponibles y verificados.
- Resultados de búsqueda con contexto, revisión, procedencia y acceso al original, respetando los permisos de cada persona. Distinguir documento vigente, histórico y pendiente de revisión sin deducir autorización únicamente de su carpeta.
- Relacionar fuente y revisión → interpretación o medición → revisión humana → resultado → informe emitido. Registrar quién cambió qué, cuándo y por qué; conservar lo emitido y permitir identificar qué resultados necesitan reevaluación si cambia una fuente.
- Diferenciar preparación, revisión, autorización de emisión y entrega. Registrar discrepancias, responsables, correcciones y cierre con evidencia.
- Evitar copias y captura duplicada. Indexar los archivos existentes y resolver cambios de ruta sin perder su historial; el mecanismo concreto queda por diseñar.

**Siguiente paso recomendado:** probar en una obra real un recorrido de búsqueda desde CATDIC-WEB hasta el documento original y desde un informe hasta sus evidencias. Comprobar recuperación de la revisión adecuada, contexto, permisos, tiempo de búsqueda y esfuerzo de mantenimiento. No fijar metas sin una línea base.

La decisión aprueba la dirección metodológica, no una migración masiva ni cambios de nombres o ubicaciones. Las reglas actuales de solo lectura de Dropbox permanecen vigentes hasta autorizar una intervención concreta. No se autoriza gasto, despliegue ni reanudación de fases detenidas.

## 8. Estado técnico que Claude debe distinguir del objetivo

| Área | Verificado en `main` | No afirmar como terminado |
|---|---|---|
| Obras, visitas, planos y dudas | Módulos y rutas existentes | Flujo empresarial multiusuario completo |
| Diseño | Extracción programada parcial y confirmación | Extracción general de planos con IA |
| Supervisión | Generadores STP-MIVED y FI; procesador de cola | Cobertura total de elementos/datos de diseño; `CATDIC-STP` sigue aplazado según su plan |
| Levantamiento y teoría | Especificación y hoja de ruta | Generadores HV, teoría Word y ensamble integrados |
| Interfaz | Tablero actual | Maquetas y organización propuesta como funciones ya implementadas |
| GPR | Proyecto separado; Steven lo considera básicamente completado | Integración con CATDIC-WEB o cierre técnico certificado por este traspaso |

La afirmación de Steven de que Claude ya hace sus informes describe su **flujo asistido actual**, no una función integrada que exista en `main`.

## 9. Investigación utilizada y límites

Consultada el 19/11/2026. Son referencias de comportamiento y condiciones, no herramientas contratadas ni garantía de precisión de ingeniería.

| Fuente oficial | Qué respalda y qué no demuestra |
|---|---|
| [Fieldwire: tareas y reportes](https://help.fieldwire.com/hc/en-us/articles/360040915311-Practical-Guide-How-to-configure-tasks-for-great-reports) | Ubicar una tarea en plano, reunir fotos/notas y generar reportes; no acredita extracción estructural automática |
| [Fieldwire: fotos y etiquetas IA](https://help.fieldwire.com/hc/en-us/articles/211358926-Introduction-to-the-Photos-Tab) | Clasificación visual genérica y fotos vinculadas; reconocer armaduras no identifica por sí solo ID y ejes |
| [PlanRadar SiteView](https://help.planradar.com/en/siteview/) y [captura](https://help.planradar.com/en/create-a-run-with-the-planradar-mobile-app/) | Reconstrucción de recorridos con captura 360°, plano y posición inicial; no extrapolar a fotos sueltas |
| [Report and Run: propiedades de imagen](https://docs.reportandrun.com/manual/readme/customization/custom-properties/add-custom-properties-to-images) | Campos personalizados en Cloud; verificar versión de CATDIC |
| [Claude: límites compartidos](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-max-or-ultra-plan) y [créditos de API](https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-ultra-and-team-plans) | Cupo compartido Claude/Code; Pro no es elegible para los créditos mensuales descritos |
| [Claude Code: condiciones](https://code.claude.com/docs/en/legal-and-compliance) y [asientos Team](https://support.claude.com/en/articles/12004354-purchase-and-manage-seats-on-team-plans) | Distinguir uso individual, autenticación admitida e intermediación; no prometer una cuenta común para todos |
| [Claude: conectores propios](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp) | Conectar herramientas a la IA del usuario; requiere configuración y red apropiadas |
| [PlanRadar MCP, beta](https://help.planradar.com/en/connect-your-ai-app-to-planradar/) | Precedente de aplicación de obra conectada a la IA del usuario con permisos; beta y sin garantía para nuestro caso |
| [Microsoft: organización de aplicaciones](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures), [OpenProject](https://www.openproject.org/docs/user-guide/) y [Frappe](https://docs.frappe.io/framework/user/en/introduction) | Referencias de aplicación modular, proyectos y permisos; no se aprobó adoptar esos productos ni reescribir CATDIC-WEB |

## 10. Próxima entrega solicitada a Claude

**Trabajo de definición e integración incremental, no otra ronda de documentos extensos.**

1. Localizar con Steven un informe que Claude ya haya resuelto bien: instrucciones utilizadas, planos y revisión, visita de Report and Run, dudas resueltas y resultado final. No inventar su procedimiento ni publicar archivos reales en Git.
2. Describir brevemente ese recorrido y qué hará la IA frente a qué hará el programa. Proponer la salida mínima que permita guardar datos con sus fuentes, corregirlos y generar el documento.
3. Presentar un primer intercambio concreto y revisable para un caso real: preparar trabajo → IA del usuario → importar propuesta → revisar → generar. Medir omisiones, datos mal asociados, dudas omitidas, esfuerzo del compañero y tiempo total frente al resultado ya conocido. No presentar este piloto como aprobado o ejecutado por este documento.
4. Contrastar también visitas difíciles (por ejemplo, las ya reconocidas #17, #18 y #20) antes de generalizar: contexto entre etiquetas, fotos sin rótulo, orden no cronológico y contradicciones. Una prueba inicial correcta no acredita todos los tipos de visita.
5. Actualizar las tareas afectadas de Etapas 2, 3, 4 y 5 con dependencias y estado explícito. Coordinar con el PR 31 sin sobrescribir el trabajo de sus ramas. Revisar la navegación anterior conforme a la aclaración de Steven y pedir decisiones solo cuando cambien el alcance.

**Pendientes reales:** caso de referencia y sus instrucciones; alcance exacto del primer piloto; IA/cuentas autorizadas de los compañeros; formato de intercambio y nivel de revisión; integración concreta de GPR; permisos y alojamiento; elección visual que siga pendiente. No volver a preguntar si se usa Report and Run, si Claude ya produce los informes, si Pro comparte cupo ni si se autoriza pagar adicional: esas respuestas ya constan.

**Límite de este encargo:** publicar este traspaso no reanuda por sí solo las fases detenidas, no elige maqueta, no autoriza eliminar la extracción existente sin sustitución revisada ni incorpora datos de clientes al repositorio. Claude debe proponer el siguiente cambio concreto aprovechando el trabajo ya desarrollado; Steven aprueba los cambios de alcance y fusiona los PR.
