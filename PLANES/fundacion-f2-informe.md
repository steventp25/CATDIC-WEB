# Fundación F2 · Informe del Líder de fase (identidad, permisos por obra, auditoría, migración y concurrencia)

Fecha: 20/11/2026 · Rama `claude/fundacion-f2-identidad-da1533` · **Sin commit** (lo autoriza Steven a través del Director).
Referencias: `PLANES/fundacion-contrato.md` (rev. 3) y `PLANES/fundacion-f0-inventario.md`.

## 1. Qué se hizo

### 1.1 Punto 1 de la rev. 3: confirmar exige `revisar_autorizar` (se hizo primero)
- Las funciones de obra son exactamente cuatro: `administrar_obra`, `preparar`, `revisar_autorizar` y `consultar`. La función `administrar` no existe:
  - La base la rechaza con un disparador (`RAISE ABORT` al insertar o al cambiar).
  - La API responde 422.
  - `permisos.componer()` ignora cualquier función que no conoce, así que no concede nada.
- Confirmar revisiones, subir planos, guardar datos de obra o recuadros, confirmar tablas, certificar notas, cerrar dudas y aprobar pedidos exigen `revisar_autorizar`:
  - Con solo `administrar_obra` → **403**.
  - Con `es_admin` sin membresía en la obra → **404**, porque la obra no se ve.
  - En ambos casos la prueba comprueba que no cambia nada.

### 1.2 Migración conservadora (`BACKEND/migracion_fundacion.py`)
- Es solo aditiva. Crea las tablas `usuarios`, `sesiones`, `membresias` y `obra_servicios`, y también:
  - `intentos_entrada`, para el bloqueo por intentos fallidos.
  - `pedidos` y `pedido_fuentes`, que hacían falta para probar el 409.
- Columnas nuevas: `auditoria.usuario_id`, `trabajos.usuario_id` y, en `dudas_y_hallazgos`, `origen`, `autor_id` y `pedido_id`.
- `estado_campos_json` no se toca.
- Cómo se aplica:
  - Hace un respaldo antes, solo si la base tiene datos.
  - Todo va en una sola transacción `BEGIN IMMEDIATE`.
  - Verifica que el número de filas no cambió y `foreign_key_check`, y deja una fila `MIGRACION_FUNDACION_F2` en la auditoría.
  - Es idempotente: la segunda vez responde «ya migrada», sin respaldo ni fila nueva.
- Rellena `obra_servicios` (1 por obra, desde `proyectos.tipo`) y `dudas.origen` (`ia` si el texto empieza por «IA:»). No modifica ningún texto.
- Corre sola al arrancar, desde `inicializar_bd()`.

### 1.3 Sesión (§4.1) — `identidad/sesiones.py`, `contrasenas.py`, `rutas.py`
- Contraseñas con `hashlib.scrypt` (N=2¹⁴, r=8, p=1, sal de 16 bytes) y un mínimo de 10 caracteres.
- Token con `secrets` en una cookie `catdic_sesion` `HttpOnly`, `SameSite=Strict`, `Path=/`. La base guarda solo el sha256 del token.
- Caducidad: 12 h sin uso o 7 días en total.
- Bloqueo: tras 5 fallos seguidos por (usuario, dirección), una espera de 15 min que se duplica con cada fallo nuevo, hasta 24 h. Responde 429 con `Retry-After`.
  - Un usuario que no existe responde igual que una contraseña mala, y tarda lo mismo.
  - La contraseña nunca va a la auditoría.
- Desactivar a un usuario cierra todas sus sesiones en la misma transacción. Nadie puede desactivarse ni quitarse la administración a sí mismo.
- Toda mutación exige el encabezado `X-CATDIC-Peticion: 1` y un `Origin` igual al servidor. Además, el `Host` debe ser localhost, 127.0.0.1 o [::1], lo que protege contra el rebinding de DNS.
- Se quitó el CORS abierto (`allow_origins=["*"]`).
- **Alta inicial local:** `py -3.14 -m identidad.alta_inicial`, desde `BACKEND/`. La contraseña se pide con `getpass`. La opción `--contrasena <usuario>` la cambia y cierra sus sesiones. No hay credenciales en el repositorio.

### 1.4 Permisos efectivos por obra y acción (§4) — `identidad/guardia.py`, `permisos.py`
- Una guardia global (`FastAPI(dependencies=[Depends(guardia)])`) corre en **toda** ruta. Una tabla `POLITICAS[(método, plantilla)]` dice qué función exige cada ruta y cómo se obtiene la obra:
  - Por la ruta, o por la visita, la duda, el pedido o el trabajo (todas las obras de sus visitas).
- Una ruta `/api` sin política responde 403. Una prueba exige que todas las rutas del esquema OpenAPI tengan su política.
- Una obra ajena o inexistente responde **404**, y una función que falta, **403**.
- Los listados se filtran: el tablero, `/api/obras`, la Mesa de Dudas, la sincronización sin obra y «Procesar Cola» sin obra solo usan las obras del usuario.
- `preparar`, `revisar_autorizar` y `administrar_obra` incluyen `consultar`. `preparar` y `revisar_autorizar` no se incluyen entre sí.
- Membresías:
  - Las gestiona `administrar_obra`, con `version` y 409.
  - Una lista vacía revoca la membresía, y la siguiente petición de esa persona recibe 404.
  - Nadie cambia su propia membresía, para que no pueda darse más funciones.
- Crear una obra es de `es_admin`. El creador recibe `administrar_obra`, `preparar` y `revisar_autorizar` de forma explícita y auditada.
- **H7 (visor):** solo se sirve un vectorial que esté dentro de `<datos>/<obra>/`, aunque la base apunte a otra ruta. La comprobación va antes de la caché.
- Las rutas que ya existían siguen igual, pasando por la guardia. El tablero clásico sigue funcionando gracias a dos cambios mínimos:
  - En `index.html`, un envoltorio de `fetch` que pone el encabezado propio, `credentials: 'same-origin'` y lleva a la entrada con 401. La API se sirve desde la misma dirección.
  - La página nueva `FRONTEND/entrar.html`.

### 1.5 Auditoría con identidad real
- Hay unos 25 `INSERT INTO auditoria` repartidos por el código. Para no tocarlos uno a uno, cada conexión instala disparadores TEMP. Estos copian el usuario de la petición (por un contextvar) en las filas nuevas de `auditoria` y `trabajos` (`usuario_id` y `usuario`) y de `dudas_y_hallazgos` (`autor_id`).
- Ocurre **en la misma transacción** que el cambio. Si la fila de auditoría falla, el cambio se deshace; está probado con un disparador que rompe la auditoría.
- El hilo del procesador hereda el usuario mediante `contextvars.copy_context()`.
- Las filas históricas con `usuario='steven'` no se tocan: siguen con ese texto y sin `usuario_id`.
- Las llamadas locales sin sesión (scripts) siguen escribiendo `steven`.
- `plano/confirmacion.py` guarda `por = usuario_id` cuando hay una sesión.

### 1.6 Conflictos de edición
- `PATCH /api/pedidos/{id}` y `PUT /api/pedidos/{id}/fuentes` exigen `version`. Hacen `UPDATE … WHERE version = ?` y, si nadie coincide, responden 409. El cambio y su auditoría van en una transacción.
- `PATCH /api/proyectos/{id}` acepta `version` opcional, para no romper el tablero clásico.
- Pedidos: cada transición exige su función y se audita con `funcion`. Un pedido aprobado no se edita.
- Antes de pasar a `preparado` o `aprobado` se comprueba el sha256 de los archivos de cada plano fuente. Si alguno cambió, se detiene con 409 y queda una fila `DETENIDO` con los motivos.
- En F2 las fuentes son solo `plano_id`: un `documento_version_id` responde 422 hasta F3.

## 2. Pruebas

Comando (desde `BACKEND/`, con una base de copia del scratchpad):

```
CATDIC_DB_PATH=<scratchpad>/suite3.db /c/Users/Steve/AppData/Local/Python/pythoncore-3.14-64/python.exe -m pytest -q -p no:cacheprovider
```

Resultado: **991 passed, 2 failed, 3 skipped** (210 s). Los 2 fallos son los dos conocidos de Dropbox, que ya fallan en `main`:
- `test_escaner_dropbox.py::test_terra_living_real`
- `test_parser_visitas.py::test_lista_coincide_con_dropbox_si_esta_disponible`

Antes de F2, la línea base era 943 passed, 2 failed y 3 skipped.

Pruebas nuevas de F2: 48, todas con la marca `seguridad_real`, es decir, con la guardia, los usuarios, las sesiones y los encabezados reales.

| Archivo | Pruebas | Escenarios §7 |
|---|---|---|
| `test_f2_permisos.py` | 14 | 1 (obra ajena → 404 en ≥20 rutas, en el visor PNG, en la duda, la visita, el trabajo y el pedido por id, y en los listados), 2 (revocación), 15 (`administrar_obra` → 403, `es_admin` → 404, `administrar` rechazada), 12 (sin encabezado, `Origin` ajeno o `null`, `Host` ajeno → 403), cobertura de rutas, sin sesión → 401, H7 |
| `test_f2_sesiones.py` | 10 | 12 (cookie, scrypt, bloqueo de 15 → 30 min con tope de 24 h, caducidad de 12 h y 7 días, desactivación, salida, cierre por el admin) |
| `test_f2_migracion.py` | 3 | 4 (aditiva, 1 respaldo, idempotente, ids y filas intactos, auditoría histórica igual; si falla, nada a medias) |
| `test_f2_pedidos.py` | 9 | 3 (preparar y autorizar como actos separados), 7 (dos ediciones a la vez → 200 + 409, repetido 5 veces; también en fuentes), 8 (el pedido sobrevive al reinicio), fuente cambiada → detenido |
| `test_f2_auditoria.py` | 6 | 10 (usuario_id en la misma transacción, atomicidad, autor y origen de las dudas, el hilo hereda el usuario, 409 en la obra) |
| `test_f2_concurrencia.py` | 4 | 11 (6 hilos por la API, 4 procesos + 1, transacción larga, proceso matado a mitad) |
| `test_f2_interfaz.py` | 2 | páginas servidas sin sesión y alta inicial local |

Las pruebas anteriores a F2 siguen probando su lógica. Para ellas, **y solo en `tests/conftest.py`**, la guardia se sustituye por un usuario de pruebas que ve todas las obras. El código de producción no tiene ningún atajo.

**Comprobación en el navegador:** servidor en `127.0.0.1:8765`, base temporal del scratchpad y un usuario de prueba creado en la sesión.
- Sin sesión → redirige a `/entrar.html`.
- Contraseña mala → «Usuario o contraseña incorrectos.»
- Al entrar, el tablero muestra solo la obra del usuario, y `document.cookie` está vacío porque la cookie es HttpOnly.
- `PATCH` de su obra → 200; de otra obra → 404.

## 3. Decisiones tomadas en F2 (para que el Director las valide)
1. El creador de una obra recibe `administrar_obra`, `preparar` y `revisar_autorizar`. Se puede cambiar con `funciones_creador`.
2. `PUT datos-obra` y `PUT recuadro` exigen `revisar_autorizar`, porque guardan valores como «confirmado». `PATCH dudas` también lo exige. `PATCH proyectos` exige `preparar`.
3. El bloqueo por intentos se cuenta por (usuario, dirección) y no solo por usuario, para que un tercero no pueda bloquear la cuenta de Steven desde otra máquina cuando la app se abra a la red.
4. La cookie no lleva `Secure`, porque el servidor solo escucha en 127.0.0.1. Abrirlo a la red exigirá HTTPS y `Secure`, y no se hace en F2.
5. Fuera de una petición HTTP (scripts y arranque) la auditoría sigue escribiendo `steven` o `sistema` sin `usuario_id`.

## 4. Concurrencia medida (SQLite 3.50.4, Python 3.14.7)

La herramienta es `BACKEND/tests/medir_concurrencia_f2.py`. Usa bases nuevas en el scratchpad, en disco local, y hace 3 rondas por caso. Cada escritura sigue el patrón de la app: `BEGIN IMMEDIATE`, leer la versión, `UPDATE … WHERE version`, `INSERT` en la auditoría y `COMMIT`.

**A) 4 hilos + 4 procesos escribiendo (60 transacciones cada uno, 480 en total) y 3 lectores a la vez**

| Diario | Espera | OK / 480 | «locked» | Escritura p50 / p95 / máx (ms) | Lectura p50 / p95 / máx (ms) | Escrituras/s |
|---|---|---|---|---|---|---|
| delete | 15 s | 480 · 480 · 480 | 0 | 8,5–8,8 / 24–26 / 4 424–4 771 | 0,3 / 263–364 / 518–640 | 84–90 |
| delete | 0,1 s | 440–443 | 37–40 (~8 %) | 8,5–9 / 24–25 / 364–436 | 65–123 / 380–456 / 448–493 | 88–92 |
| wal | 15 s | 480 · 480 · 480 | 0 | 2,4–2,5 / 4,8–6,6 / 1 189–1 410 | 0,1 / 0,2–0,3 / 5–14 | 271–303 |
| wal | 0,1 s | 445–454 | 26–35 (~6 %) | 2,5–2,7 / 6,6–7,1 / 153–178 | 0,1 / 0,2 / 5–10 | 248–283 |

En todas las rondas la integridad fue `ok` y hubo **0 pérdidas**: cambios confirmados = versiones = filas de auditoría.

**B) Transacción larga de escritura (3 s) mientras 2 lectores y 2 escritores trabajan:**
- Con una espera de 15 s, los escritores esperan hasta unos 3,2 s y todos entran, en los dos modos.
- Con 0,1 s, las 6 escrituras fallan con «locked».
- Los lectores nunca se bloquearon: máximo 46 ms en `delete` y 7 ms en `wal`.

**C) Caída a mitad de transacción** (proceso matado con 500 cambios sin confirmar):
- Integridad `ok`.
- 0 filas visibles de la transacción caída.
- La primera escritura posterior entra en 14–18 ms, y deshace el diario caliente en `delete` o recupera el WAL.

**Decisión:**
- Se mantiene el diario **`delete`** y una espera explícita de **15 s** (`database.ESPERA_BD_SEGUNDOS`). Antes eran 5 s implícitos.
- Con 15 s no hubo ningún «locked» en ningún caso. La espera más larga medida fue de 4,8 s con 8 escritores simultáneos, una carga muy por encima del uso real (1–3 personas), así que el margen es de unas 3 veces.
- WAL rinde unas 3 veces más y los lectores no esperan nunca. Aun así, **no se activa** mientras la base real esté en `BACKEND/catdic_local.db`, dentro de OneDrive: sincronizar el `.db` sin su `-wal` y su `-shm` puede dejar en la nube una copia incoherente, y el `-shm` mapeado en memoria no se lleva bien con la sincronización.
- Recomendación para F3/F5: mover la base fuera de OneDrive, por ejemplo junto a `CATDIC-DATOS`, y entonces activar WAL. El cambio es de una línea y la medición ya está hecha.

## 5. Pendiente
- **Historial y «mi trabajo»** (contrato §5): no implementados; se dejan para F4.
- **Documentos versionados como fuente** (`documento_version_id`), la copia conservada de las fuentes y el resto del ciclo de pedidos: F3, puntos 2 y 3 de la rev. 3.
- **Interfaz:** no hay botón «Salir» ni gestión de usuarios y membresías en el tablero. Por ahora están la API, la alta local y la entrada. La interfaz completa es del prototipo de F1 / F4.
- **Alta real de Steven:** la hace él en local con `py -3.14 -m identidad.alta_inicial`. Hasta entonces, el tablero lleva siempre a la entrada.
- `@app.on_event("startup")` está obsoleto en FastAPI (aviso que ya existía). No se tocó.

## 6. Riesgos
1. **Al desplegar esta rama, el tablero exige entrar.** Si Steven no hizo la alta inicial antes, ve la página de entrada y no puede pasar. Hay que hacer la alta justo después de fusionar, antes de abrir la app.
2. La base real está en OneDrive. Esto explica por qué se mantiene `delete` (ver §4) y es un riesgo de corrupción si OneDrive copia el archivo con una transacción abierta. El respaldo de la migración queda junto a la base, también en OneDrive.
3. La cobertura de permisos depende de la tabla `POLITICAS`. Una ruta nueva sin política se rechaza (403) y la prueba de cobertura falla, de modo que no puede quedar abierta por descuido. Aun así, al escribir rutas nuevas hay que elegir bien su función.
4. **`conftest.py` sustituye la guardia en las pruebas antiguas.** Una prueba nueva de seguridad que olvide la marca `seguridad_real` correría sin guardia. Por eso las pruebas de F2 la declaran a nivel de archivo (`pytestmark`).
5. Los disparadores TEMP dependen de que toda conexión salga de `database.get_connection()`. Una conexión `sqlite3.connect` directa en una ruta escribiría auditoría sin `usuario_id`; hoy no hay ninguna en rutas HTTP.
6. Una lectura durante una ráfaga de escrituras en `delete` puede tardar hasta unos 0,6 s (p95 de unos 360 ms con 8 escritores). Es aceptable para el uso actual.
