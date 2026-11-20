# Fundación inicial de CATDIC-WEB — plan de ejecución para Claude

Fecha: 19/11/2026. Responsable de ejecución propuesto: Claude Code. Revisión cruzada: Codex. Steven decide producto y fusiona.

**Estado: PLAN REDACTADO A SOLICITUD DE STEVEN; implementación no iniciada por este documento.** Las decisiones de producto siguientes están confirmadas; el desglose técnico es una propuesta ejecutable. No presentar este plan como aprobación de gasto, despliegue, migración de Dropbox, maqueta ni integración central de IA. Solicitar aprobación del plan antes de lanzar ejecutores; no repetir el cuestionario de producto.

## 1. Objetivo y frontera de esta entrega

Construir la base compartida de la plataforma interna de CATDIC: obras, usuarios, documentos y revisiones, búsqueda, trazabilidad y una interfaz elegida por Steven. Prepararla para que una petición de información llegue, en una entrega posterior, a datos revisados y a un informe de supervisión.

**Fundación terminada:** Steven puede seguir una guía para entrar, abrir una obra autorizada, buscar y abrir sus fuentes, distinguir revisiones y cambios, consultar visitas existentes y guardar un trabajo con propósito y fuentes seleccionadas. Otra identidad ve únicamente las obras y acciones permitidas. Un cambio de fuente queda señalado sin alterar aprobaciones ni documentos anteriores. Respaldo y recuperación se han probado.

La prueba completa del informe no se exige al terminar la fundación: corresponde a la siguiente entrega. Tampoco se declara listo para toda la oficina ni para producción por superar una demostración local.

## 2. Decisiones de Steven consolidadas — no volver a preguntar

- Plataforma técnica interna por obra para compañeros y jefes, ampliable por módulos. Fuera de la primera versión: contabilidad, nómina, facturación, compras y gestión comercial.
- Trasladar el proceso con el que Claude ya produce informes completos; no inventar un proceso de ingeniería nuevo.
- IA dentro de acciones como Preparar información y Actualizar obra; sin sección principal obligatoria de chat. Preguntar propósito y fuentes; extracción variable de planos y visitas.
- Programa organiza, valida, calcula y genera; la persona autorizada aprueba información técnica y emisión. Nunca inventar ingeniería ni firmas.
- Navegación inicial para prototipo: Obras; dentro, Resumen, Documentos y planos, Visitas y elementos, Informes e Historial. Pendientes personales en Mi trabajo, fuera de Inicio. Se corrige si el prototipo evidencia problemas.
- Aprovechar Dropbox y Report and Run existentes. En los reportes ya se identificaban elementos o ubicaciones dibujadas en planta; ejemplo específico pendiente de verificar. No exigir recapturar visitas.
- Dropbox: lectura e indexación inicial, sin reorganización automática. Escrituras solo en salidas previamente autorizadas, con versión nueva. Nuevos archivos y revisiones se señalan; no reemplazan automáticamente datos revisados ni informes anteriores.
- Usuarios con funciones combinables: administración, preparación, revisión/autorización y consulta; acceso por obra. Steven puede preparar y autorizar en su primera prueba, registrando ambas acciones.
- Separar borrador, autorización de emisión y entrega. Guardar borradores con dudas; impedir emisión ante dudas técnicas bloqueantes del informe afectado. No bloquear trabajos independientes.
- Revisión de datos junto a evidencia; selección de elementos, fotos y evidencias; previsualización antes de guardar versión. Reutilizar lo aprobado mientras siga siendo aplicable.
- Aprobar primero estructura visual mediante prototipo navegable. Pruebas técnicas internas durante el desarrollo. Primera prueba operativa de Steven con tutorial y un caso conocido; después otra visita; luego un compañero.
- Guardar progreso y mostrar cómo continuar ante errores o falta de cupo de IA. Ayudas en pantalla, no dependencia de instrucciones externas del desarrollador.
- GPR seguirá evolucionando y puede evaluarse para integración. Su visor completo no bloquea esta fundación.
- Cuenta Claude Pro de CATDIC como posible IA sigue abierta. Ninguna API, pago adicional ni exposición de credenciales autorizados. No convertir una suscripción en servicio multiusuario sin comprobar un mecanismo permitido.

## 3. Arranque y reutilización obligatoria

Leer este plan, `alcance-catdic-web-2026-11-19.md`, su auditoría, `CLAUDE.md`, `AGENTS.md`, `COLABORACION.md` y las etapas/evaluaciones existentes. Usar `PLANES/` como estado; no crear un sistema paralelo `.proyecto/`.

Antes de cambios: comprobar rama, cambios locales, remotos, PR 31 y PR 33 y trabajos activos. Pedir a Steven autorización antes de cambiar rama, hacer commits, push o fusionar; nunca push a main. No mezclar ni borrar trabajo ajeno. `etapa-5.md` no existe en este checkout: localizar su rama/PR antes de inventar otra Etapa 5 o concluir que no hay avances.

Inspección puntual de este checkout: FastAPI y Vue/Tailwind existentes; `BACKEND/obras.py`, `visor.py`, `visitas_obra.py`, `sync/`, generadores y Mesa de Dudas reutilizables. `database.py` contiene auditoría fija `steven`; `main.py` permite CORS amplio y expone dashboard global; la tabla proyectos distingue Supervisión/Levantamiento de forma excluyente. Son puntos que requieren revisión para multiusuario, no una auditoría exhaustiva actual de todas las ramas. El frontend local usa dependencias CDN: no afirmar modo offline completo mientras permanezca así.

No aprobar reescritura, framework nuevo, microservicios o migración de base por comodidad. Proponer cambios mínimos compatibles; comprobar concurrencia y límites de SQLite antes de decidir otra base. Una obra debe poder vincular servicios sin duplicar identidad: definir correspondencia con proyectos actuales sin migración destructiva.

## 4. Fases, dependencias y puertas

| Fase | Tareas | Zona principal propuesta | Depende de | Modo | Cierre |
|---|---|---|---|---|---|
| F0 Reconcilación y contrato | F0.1–3 | PLANES y lectura del repo | — | directo | Inventario y modelo común comprobables |
| F1 Prototipo del recorrido | F1.1–3 | FRONTEND/prototipo-fundacion/ | F0 | directo | Steven elige/corrige estructura |
| F2 Identidad y expediente | F2.1–4 | BACKEND: acceso, persistencia, obras | F0; UI espera F1 | líder | Permisos efectivos y migración probada |
| F3 Documentos y actualización | F3.1–4 | BACKEND: documentos, sync, búsqueda | F2 | líder | Índice recuperable y cambios controlados |
| F4 Interfaz integrada | F4.1–4 | FRONTEND y contrato API acordado | F1 elegida + F2/F3 | líder | Recorrido real sin pantallas simuladas |
| F5 Auditoría y entrega | F5.1–3 | pruebas, tutorial, evaluación | F4 | directo | Evidencia de aceptación y límites |

F1 y F2 pueden avanzar en paralelo tras F0; la implementación visual final espera elección de Steven. F3 espera identidades y permisos de F2; F4 puede integrar endpoints ya aceptados por lotes, sin declarar cierre antes de F3. No paralelizar ediciones de `main.py`, `database.py` o el mismo frontend. Un responsable por archivo; cambios compartidos integrados secuencialmente. Máximo inicial recomendado: dos ejecutores simultáneos, ampliable solo si hay zonas independientes claras.

### F0 — reconciliar y cerrar contrato mínimo

**F0.1:** inventariar módulos, rutas, migraciones, pruebas, generadores y avances de otras ramas. Clasificar reutilizar/adaptar/falta. Ejecutar suite base en BD temporal; registrar fallos ambientales aparte sin ocultarlos ni arreglarlos fuera de alcance.

**F0.2:** definir entidades y relaciones de obra, servicio, usuario, membresía, documento/revisión, visita/elemento, trabajo/pedido, resultado y emisión. Reutilizar IDs existentes y planear equivalencias; no diseñar todas las funciones futuras. Separar estados de documento, dato, trabajo y entrega.

**F0.3:** acordar contrato de API mínimo entre ejecutores, permisos por operación y escenarios de aceptación de este plan. Documentar en un anexo breve `fundacion-contrato.md`: entidades, acciones y ejemplos sin datos reales. Las decisiones técnicas rutinarias corresponden a Claude; consultar solo cambios de alcance o riesgos que no pueda resolver bajo las restricciones.

**Cierre:** inventario y dependencias actuales, contrato coherente y suite base registrada. Si el primer formato soportado no puede verificarse, dejarlo pendiente para la siguiente entrega; no bloquea el expediente.

### F1 — prototipo antes de interfaz definitiva

**F1.1:** prototipo navegable de Obras, expediente, documentos, visita, selección de fuentes y trabajo guardado. Usar datos ficticios marcados; sin conectarse a BD real. Aplicar skills de diseño pertinentes y mantener textos comprensibles para técnicos.

**F1.2:** incluir estados vacío, carga, error, sin permiso, revisión histórica, cambio detectado y trabajo guardado. Mostrar contexto y siguiente acción; no métricas inventadas ni prioridades en Inicio.

**F1.3:** presentar recorrido breve para elección de Steven. Una propuesta principal coherente; variantes solo si resuelven una decisión visual relevante. No reutilizar una maqueta previa como aprobada.

**Puerta:** Steven acepta o corrige la estructura. Mientras espera, continuar backend independiente, no consolidar frontend definitivo.

### F2 — usuarios y expediente común

**F2.1:** elegir mecanismo local de autenticación seguro y mantenible; cuentas individuales, cierre de sesión y desactivación. No usar nombre escrito en un campo como identidad ni fabricar correo/contraseñas de empleados. Documentar alta inicial segura; excluir secretos del repo.

**F2.2:** permisos por obra y acción, aplicados en servidor a listados, búsqueda, visor, archivos y mutaciones. Prevenir acceso cambiando un ID o ruta; no filtrar nombres o vistas previas de obras no autorizadas. Probar revocación y administración. Crear identidades de prueba sin datos personales.

**F2.3:** expediente por obra y relación con servicios existentes. Guardar responsable y contexto de trabajo sin duplicar obra por módulo. Migración incremental en copia temporal; conservar datos y autoría histórica, registrar autor real en acciones nuevas. Probar actualización y reejecución de migración.

**F2.4:** auditoría transaccional de acciones y cambios relevantes, incluyendo autorización; no registrar contraseñas, tokens ni contenido sensible innecesario. Detectar edición concurrente y evitar pérdida silenciosa de cambios. Revisar CORS y rutas de archivos según el mecanismo elegido.

**Cierre:** dos usuarios con acceso diferente, combinaciones de funciones y pruebas directas de API; usuario no autorizado no accede aunque conozca un ID. Historial previo conservado.

### F3 — documentos, revisiones y Dropbox

**F3.1:** vincular carpetas existentes mediante configuración fuera de lógica de negocio. Primer proveedor recomendado: lector local ya existente, con diagnóstico de disponibilidad; decidir alternativa API solo mediante propuesta autorizada. No convertir nombres de carpetas en prueba de aprobación técnica.

**F3.2:** indexar documentos con identidad, ruta, tipo, procedencia, revisión cuando esté confirmada y estado de disponibilidad. Diferenciar identidad técnica del archivo y revisión documental aprobada. No deducir vigencia por fecha de modificación ni borrar historial por ausencia. Movimiento ambiguo queda por reconciliar; no fusionar archivos solo por nombre o hash.

**F3.3:** actualización manual y periódica configurable en el entorno de prueba; incremental cuando sea viable. Mostrar última actualización, en curso, errores y reintento. Repetición no duplica documentos. Permisos se vuelven a comprobar; pérdida de acceso no equivale a borrado. Indexar no llama a IA automáticamente.

**F3.4:** búsqueda por nombre y alias, tipo, fecha y metadatos verificados de elemento/nivel/ejes cuando existan. Mostrar evidencia disponible sin prometer búsqueda semántica ni inventar etiquetas. Abrir original/vista previa autorizada. Registrar qué selección de revisiones utiliza cada trabajo; cambio de fuente señala reevaluación sin cambiar aprobaciones.

**Cierre:** escenarios nuevo/movido/modificado/ausente/inaccesible, reindexación sin duplicados, búsqueda con permisos y recorrido hasta original. Ensayos en carpeta temporal representativa; comprobación real solo lectura donde esté autorizada. No modificar Dropbox para simular fallos.

### F4 — recorrido funcional y conexión futura

**F4.1:** implementar prototipo elegido sobre datos reales de la API; conservar funciones existentes hasta sustitución revisada. Las secciones sin motor no mostrarán éxito ficticio: indicar alcance pendiente o función disponible.

**F4.2:** guardar trabajo: obra, propósito, fuentes/revisiones seleccionadas, responsable, estado y progreso. Reabrir tras reinicio sin perder selección; comprobar permisos de fuentes nuevamente. Preparar interfaz que permita luego indicar información solicitada, cobertura y faltantes sin marcar todo el plano como procesado.

**F4.3:** consultar visitas existentes y sus archivos, preservando secuencia y asociaciones registradas; no inventar identificación de elementos. Enlaces de GPR/IA solo si existe función verificada; de lo contrario dejar contrato de integración, no construir un simulador que parezca operativo.

**F4.4:** ayuda contextual y guía breve dentro del recorrido; carga, errores y recuperación claros; verificar navegación con teclado, tamaños habituales de pantalla y nombres largos. Proteger progreso al salir. Las prioridades permanecen en Mi trabajo.

**Cierre:** crear, guardar y retomar trabajo; buscar, seleccionar y abrir fuentes; navegar historial y detectar cambio. Sin cambiar de aplicación para interpretar errores técnicos.

### F5 — aceptación y entrega a siguiente etapa

**F5.1:** auditoría integrada de permisos, fuentes, historial, migración y regresiones pertinentes. Probar respaldo consistente y restauración de BD y archivos necesarios en entorno separado. No confundir sincronización Dropbox con respaldo completo de la aplicación.

**F5.2:** tutorial de fundación: entrar → obra → fuentes → visita → selección → guardar → continuar → revisar cambios. Datos reales permanecen fuera de Git; capturas compartidas deben estar autorizadas o usar datos ficticios.

**F5.3:** evaluación `fundacion-inicial-evaluacion.md`, con evidencia de cada criterio, limitaciones y siguiente entrega. Presentar resultado a Steven sin pedirle probar un sistema incompleto como si pudiera emitir informes.

## 5. Criterios globales de aceptación

- [ ] Navegación elegida por Steven, integrada sin datos simulados encubiertos.
- [ ] Identidades individuales y permisos efectivos en servidor y archivos; revocación probada.
- [ ] Obra común para servicios, fuentes y trabajos, sin duplicados nuevos ni pérdida de IDs anteriores.
- [ ] Originales y revisiones distinguibles; movimientos ambiguos no se reconcilian inventando identidad.
- [ ] Indexación repetible; actualización visible; errores recuperables y acceso respetado.
- [ ] Cambio de fuente señala impacto conservador, sin modificar datos revisados ni documentos emitidos.
- [ ] Trabajo y progreso recuperables tras reinicio; cambios concurrentes no se pisan silenciosamente.
- [ ] Regla de Oro, separación diseño/campo/cálculos, firmas y versionado preservados.
- [ ] Migración y restauración probadas con copias; BD real sin modificación no autorizada.
- [ ] Suite base y pruebas pertinentes registradas, fallos no resueltos explicitados.
- [ ] Tutorial reproducible y evaluación cruzada; ninguna afirmación de despliegue multiusuario productivo.

## 6. Siguiente entrega: primer informe completo, no parte de esta fundación

Usar un informe de supervisión conocido y verificar el formato realmente soportado. Integrar solicitud → IA autorizada → propuesta con fuente → revisión junto a evidencia → correcciones/dudas → selección de contenido → previsualización → autorización → versión nueva → registro de entrega. Conservar procedimiento/plantilla y fuentes utilizados para reconstruir la emisión. No equiparar generado con autorizado o entregado.

Puerta previa a integrar el motor IA: resolver modalidad permitida y cuenta autorizada sin gasto nuevo. Puede investigarse en paralelo sin bloquear la fundación, pero no mostrar preparación automática funcional hasta probarla. Corregir manualmente es apoyo; no convertir transcripción completa en requisito.

Validación posterior: Steven reproduce caso conocido siguiendo tutorial, luego otra visita; después un compañero. La prueba completa espera interfaz coherente y recorrido funcional; las pruebas internas se realizan desde F0. El ejemplo Report and Run y el caso de referencia se solicitan solo cuando hagan falta; no inventarlos ni publicar sus documentos.

## 7. Coordinación, evidencia y autoridad

Este archivo es el plan maestro de fundación; conserva la historia de las etapas anteriores, no las reemplaza ni reanuda enteras. Tareas de etapa anterior necesarias se referencian por ID y se concilian en F0. Claude registra tarea/ejecutor/estado/evidencia en este archivo o en una tabla breve enlazada; máximo un reporte corto por tarea si hay varios ejecutores. No crear nuevos documentos extensos por cada decisión.

Estados: pendiente → en curso → en revisión → aceptada, o bloqueada con causa y siguiente acción. Solo cerrar contra código y evidencia. Responsables técnicos propuestos: backend para F2/F3, frontend para F1/F4, generadores como revisión de compatibilidad y siguiente entrega. Director coordina y audita; Codex revisa PR. No asumir disponibilidad de agentes/modelos ni lanzar sesiones desde este encargo de redacción.

En cada entrega: qué cambió, cómo se verificó y qué sigue pendiente. Commits/ramas/push/merge requieren autorización previa de Steven. Sin PDFs, fotos, BD, credenciales ni paquetes de planos en Git. El plan no autoriza desplegar, contratar ni ampliar escrituras de Dropbox.

## Bitácora

- 19/11/2026: plan redactado tras cerrar la entrevista de producto (respuestas 1–24); sin implementación, commits ni cambios de Dropbox.
