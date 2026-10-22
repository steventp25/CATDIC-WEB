# Etapa 2 — Evaluaciones internas

## Evaluación 1 · 22/10/2026 · Auditor CATDIC · T1 y T2

### T1 — Esquema de `elementos_diseno` (rama `claude/etapa2-t1-esquema`, `a1891ff`)
**Veredicto: BLOQUEADO.** El código es seguro; lo único que falta es el criterio 2.

**Bloqueante**
- `PLANES/etapa-2.md`, T1, criterio 2. No se ha cumplido "con la BD real existe el respaldo y `/api/dashboard` responde 200".
  - No es un defecto del código.
  - El Ejecutor no pudo migrar la BD real: está en el checkout principal y él trabaja en su worktree.

**¿Se puede migrar la BD real sin riesgo? Sí.**
- *Respaldo:* `_respaldar_bd` usa la API de backup de SQLite antes de tocar nada. Nunca pisa un respaldo anterior: si ya existe, crea ` v2`.
- *Transacción:* los dos `ALTER TABLE ADD COLUMN`, el `CREATE UNIQUE INDEX` y la fila de `auditoria` van en un solo `BEGIN…COMMIT`. Si algo falla, `ROLLBACK`. Lo cubre la prueba `test_migrar_diseno_con_duplicados_previos_revierte`.
- *Estado de la BD real (consultado en solo lectura el 22/10):*
  - `elementos_diseno` y `elementos_visita` tienen 0 filas, así que no puede haber duplicados.
  - `PRAGMA foreign_key_check` devuelve `[]`.
  - Todavía no está migrada: tiene 13 columnas.
- *FK:* `ADD COLUMN` y `CREATE INDEX` no reconstruyen la tabla, así que `elementos_visita.elemento_diseno_uid` queda intacta.
- **Aviso:** `inicializar_bd()` corre la migración en cada arranque. En cuanto se fusione T1 en `main` y se arranque el servidor, la BD real se migra sola.
- *Cómo verificar que quedó migrada:*
  - existe `catdic_local.backup-AAAAMMDD-HHMMSS.db`;
  - hay una fila `MIGRACION_ELEMENTOS_DISENO` en `auditoria`;
  - la tabla tiene 15 columnas;
  - `/api/dashboard` responde 200.
- *Menor:* si la migración falla, el respaldo ya creado se queda en disco. No hace daño.

**UNIQUE con `CREATE UNIQUE INDEX`:** cumple §4.2 y el plan.
- Funciona igual que una restricción `UNIQUE`. `_diseno_tiene_unico` reconoce las dos formas.
- *NULL:* no aplica, porque las 4 columnas son `NOT NULL`.
- **Herencia para T4:** dos elementos distintos con el mismo ID y nivel y EJES `pendiente de verificar` chocan en el UNIQUE. El importador debe convertir ese choque en una `DUDA_BLOQUEANTE`, no dejar que salte un `IntegrityError`.
- **Herencia para T3/T4:** la comparación es literal (`'S-4'` ≠ `'S -4'`). La normalización del nivel la hacen T3/T4, sin adivinar.

**Criterios de aceptación**
- [x] Pruebas con BD temporal: conserva filas y FK; idempotente; el UNIQUE rechaza duplicados en BD migrada y en BD nueva; revierte si ya había duplicados.
- [ ] BD real con respaldo y `/api/dashboard` 200: no se ejecutó (bloqueante).
- [x] pytest: `486 passed, 3 warnings in 6.74s`. Corrido con `git archive` + `CATDIC_DB_PATH` temporal.

**Reglas**
- Pruebas `SINTETICO`.
- §1.5: queda registro en auditoría.
- Corregido el comentario "Archivo 02" → "CLAUDE.md §4.4".
- No hay `.db` ni secretos en el diff.

### T2 — Validador de elementos de diseño (rama `claude/etapa2-t2-validador`, `ceca410`)
**Veredicto: APROBADO**, con observaciones.

**Puntos revisados**
- `categoria` y `recubrimiento_por_lado_m` no chocan con §4.1. El plan pide justo esa consulta, y no suma 2×rec ni calcula cuantías (`test_no_calcula_cuantias_ni_recubrimientos_sumados`).
  - **Condición para T4:** son constantes del programa, no datos del plano. No se guardan dentro de `datos_diseno_json`.
- Tipos que no están en la tabla de formatos: no es adivinar, porque el texto de EJES pasa tal cual. Pero la validación es débil:
  - `MURO DE CONTENCION`, `ZAPATA COMBINADA` y `ZAPATA DE MURO` (sin formato en §4.4) aceptan cualquier formato y no generan dudas.
  - Recomendación: un `HALLAZGO_INTERNO` o una duda mientras Steven no fije el formato.
- Error #11 cubierto hoy: `_SOLO_GUION` coincide con la categoría "LOSAS Y ESCALERAS".
  - Riesgo: `_SOLO_GUION` y `_FORMATOS_POR_TIPO` (`validador_diseno.py:36-47`) duplican a mano `CATEGORIA_POR_TIPO`. Un tipo de losa nuevo en `reglas_ingenieria.py` aceptaría `EJE A-1`. Conviene derivar "solo `—`" de la categoría.
- Las claves de las dudas coinciden con `dudas_y_hallazgos` (CHECK y NOT NULL). T4 debe añadir `proyecto_id` y `creado`.
  - **Observación importante para T4:** `dudas_y_hallazgos` no guarda ni el nivel ni `elemento_diseno_uid`. Un `C1` de S-5, S-4 y S-3 no se distinguiría, y el dedupe por id + campo mezclaría niveles. T4 debe incluir nivel + EJES o una columna `elemento_diseno_uid`. Si T4 no lo resuelve, el Auditor lo bloqueará.
- No hay datos de diseño reales ni inventados: todo está marcado `# SINTÉTICO` o `# NORMA` (ejemplos de §4.4).

**Otras observaciones (no bloquean)**
- `validador_diseno.py:157-159`: si `datos_diseno` llega como lista o como texto, `.items()` lanza excepción. Mejor una duda.
- `validador_diseno.py:50-55`: una lista o dict vacío (`{"acero": []}`) queda `confirmado`. Conviene tratarlo como vacío.
- `estado_campos` usa `pendiente_de_verificar` y los valores usan `pendiente de verificar`. T4 y el frontend deben comparar contra la constante correcta.
- `elemento_unico_en_planta` (P6, Etapa 0) va a duda. Es lo prudente, pero falta confirmarlo con Steven.
- Comprobado: `PORTICO` + `EJE 1 ENTRE MC-A` → 0 dudas; `COLUMNA` con ese mismo texto → duda.

**Criterios de aceptación**
- [x] losa con EJES ≠ `—` → duda;
- [x] muro con `FILA` → duda;
- [x] falta `hoja_plano_origen` → pendiente + duda;
- [x] tipo metálico → pendiente;
- [x] elemento completo → 0 dudas;
- [x] pytest: `520 passed, 3 warnings in 6.59s`, más 8 casos a mano.

### Pendientes de verificar (para Steven)
- Formato de EJES para `MURO DE CONTENCION`, `ZAPATA COMBINADA` y `ZAPATA DE MURO`.
- Cómo se identifica el elemento en una duda de diseño: ¿nivel + EJES en el texto, o una columna `elemento_diseno_uid`?
- Cuándo se migra la BD real (al arrancar el servidor desde un `main` con T1).

## Evaluación 2 · 22/10/2026 · Auditor CATDIC · Reevaluación de T1 (`a1891ff`)
**Veredicto: APROBADO.** Queda levantado el bloqueante del criterio 2.

El Auditor lo verificó todo en solo lectura:
- [x] **Respaldo** `BACKEND/catdic_local.backup-20261022-095419.db` (110 592 bytes):
  - `integrity_check = ok`;
  - esquema previo (13 columnas);
  - 22 visitas.
- [x] **BD real:**
  - `elementos_diseno` con 15 columnas (`fuente_json`, `pendientes_json`);
  - índice único `ux_elementos_diseno_clave` sobre `proyecto_id, id_elemento, nivel_rango, ejes`.
- [x] **Auditoría:** una sola fila (id 26, `MIGRACION_ELEMENTOS_DISENO`, 2026-10-22T09:54:19), que apunta al respaldo correcto. La segunda ejecución fue "ya migrada" y no dejó otra fila.
- [x] **Integridad:**
  - `foreign_key_check = []`;
  - `elementos_diseno` con 0 filas;
  - las visitas no cambiaron: 12 Con dudas, 6 Procesada, 4 Sin procesar.
- [x] **Dashboard:** `curl /api/dashboard` → 200 (el servidor ya estaba arriba).

**Observaciones**
- Las condiciones para T4 de la Evaluación 1 siguen vigentes:
  - un choque del UNIQUE con EJES `pendiente de verificar` tiene que acabar en duda;
  - hay que normalizar el nivel.
- La BD real ya tiene el esquema de T1 y `main` todavía no. No rompe nada, pero conviene fusionar T1 pronto.
