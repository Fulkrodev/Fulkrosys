# Inventario del bloque Q

**Este fichero es el alcance del bloque.** Lo que no está numerado aquí no se
trabaja en Q. Lo que apareció *después* de congelarlo está al final, en
[Hallazgos nuevos](#hallazgos-nuevos), y se declara con su medición sin
arreglarse. Sin esa regla el bloque no termina nunca.

Congelado el **2026-09-12**, contra `ec6ec3f`. Estados actualizados al cierre
(`07efe5f`, 2026-09-15).

---

## Cómo leer esto

**Estados.** Sólo hay dos, por exigencia del propio bloque: **ARREGLADO** (existe
el arreglo, existe el test que falla en el padre y pasa en el hijo) y **CERRADO
CON MOTIVO** (se decidió no arreglarlo, y el motivo está escrito). No hay estado
intermedio y no aparece la palabra «pendiente».

**Categorías.** El bloque organiza el trabajo en tres, y cada defecto cae en una:

| | categoría | criterio |
|---|---|---|
| **A** | Falsedad dentro de un documento firmable | el defecto produce una afirmación falsa en algo que el cliente o el auditor firma o lee como verdad |
| **B** | Corrompe o pierde datos en silencio | el sistema descarta, duplica o corrompe sin decirlo |
| **C** | El resto | todo lo demás, ordenado por daño: lo que impide completar el ciclo antes que lo cosmético |

Los defectos de la batería de tests llevan además la subcategoría que les asigna
Q3: **C1** falta un recurso que el repo no trae · **C2** el test asevera el
defecto · **C3** fallo real.

**Los números de línea** son los del commit en que se congeló el inventario
(`ec6ec3f`). Varios de esos ficheros han cambiado desde entonces —arreglarlos era
el objeto del bloque— así que las coordenadas apuntan a la función, no
necesariamente a la línea exacta del árbol de hoy.

**Las cuatro fuentes**, y cómo se resolvió cada una:

| fuente | de dónde sale | cuántos |
|---|---|---:|
| Los 44 fallos y los 5 errores de la batería | `pytest backend/tests -q` sobre `ec6ec3f` | 49 → §1-§6 |
| Los frentes abiertos del README | recuperados de `a5b28f7^:README.md` (la sección se retiró del README en `a5b28f7`) | 11 → §7-§17 |
| Los graves de O2 que no se arreglaron | `docs/audit/AUDITORIA_2026-09.md`, 68 bloques de hallazgo, 15 marcados «(corregido)» en el propio informe | 12 vivos → §18-§29 |
| Lo que quede de los 21 | `70342a1` *fix(audit-wave1): 21 bugs reales*, del 2026-06-14 | 1 vivo → §30 |

> **Sobre «los 16 graves de O2».** El informe de O2 no clasifica por severidad más
> allá de su sección A1 (4 BLOQUEANTE, 4 GRAVE, 3 MENOR); el resto de sus 68
> bloques va sin etiqueta. Su recuento propio es «30 confirmados, 16 corregidos
> por mal etiquetado, 22 sin verificar». No hay, por tanto, una lista de 16
> graves que se pueda citar literalmente. Lo que se ha hecho en su lugar es
> **comprobar uno a uno, con un comando, cuáles siguen vivos hoy**: son 12, y
> están en §18-§29. Los que el informe daba por abiertos y ya no lo están se
> declaran resueltos con la medición que lo demuestra (§26, §29).

> **Sobre «lo que quede de los 21».** Los 21 de `70342a1` se arreglaron en junio.
> Lo que queda de ellos no es un arreglo sin hacer: es que **uno de sus tres
> defectos de clase «no hacía commit» volvió a aparecer en un hermano** que aquel
> barrido no tocó (§10). Eso es §30, y es la entrada más informativa del
> inventario, porque dice que el barrido de junio arregló los casos y no la
> clase.

---

## A · Falsedad dentro de un documento firmable

### 1 · Las 12 de 13 justificaciones de «no aplica» de la DdA · ARREGLADO
**Categoría A.** La justificación de exclusión que lee el auditor salía de una
plantilla fija que citaba **siempre** el eje «categoría» del Anexo II, con el
dato tomado de `ens_measures.categoria_minima` —una columna denormalizada que no
es la que decide la aplicabilidad—.

*Dónde:* `backend/app/motors/m03_dda/service.py`, generación de
`justificacion_no_aplica`.

*Reproducción:*
```bash
docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro -c \
  "SELECT justificacion_no_aplica FROM dda_entries
   WHERE aplicabilidad='no_aplica' AND justificacion_no_aplica IS NOT NULL LIMIT 5;"
```
Medido sobre el proyecto MEDIA del demo: 12 de 13 exclusiones son de eje
«dimensión» y la frase les atribuía un motivo falso. En cuatro (`mp.eq.2`,
`mp.if.6`, `mp.s.4`, `op.cont.1`) `categoria_minima` valía MEDIA **y el sistema
era MEDIA**: el documento que firma el cliente decía que la medida no aplica
porque aplica.

*Arreglo* (`3447b8e`): el motivo se deriva de la misma tabla que decide la
exclusión. 13 de 13 justificaciones cambian ·
`dda_matriz.xlsx` `58657fc3…` → `2aaa49de…`.

### 2 · El acta E-012 se contradice consigo misma en su JSON · ARREGLADO
**Categoría A.** `it.valoracion_d or "BAJO"`, cinco veces y en dos sitios: la
tabla de tipos de información declaraba BAJO una dimensión que el bloque
`result` del **mismo documento** daba por no afectada.

*Dónde:* `backend/app/motors/m01_categorization/api.py:1081-1098`.

*Reproducción:*
```bash
curl -s -b cookies.txt "$API/api/v1/categorization/systems/$SID/acta-e012.json" \
  | jq '.result.dimensiones'
```

*Arreglo* (`3447b8e`): y debajo había un defecto que no se ve leyendo código —
`information_types` y `services` declaraban las cinco columnas como
`VARCHAR(10)`, y `NO_AFECTADA` tiene 12 caracteres—. Migración
`no_afectada_cabe_001`.

### 3 · La ficha E-001 afirmaba que su próxima actualización era hoy · ARREGLADO
**Categoría A.** `date.today().replace(day=min(28, hoy.day))` devuelve **hoy**
para cualquier día 1-28. La ficha de seguimiento que recibe el cliente decía que
su próxima actualización era el día en que la estaba leyendo.

*Dónde:* `backend/app/motors/m06_document_factory/ficha_seguimiento_context.py`,
`proxima_actualizacion`.

*Reproducción:*
```bash
python3 -c "from datetime import date; hoy=date.today(); \
  print(hoy, date.today().replace(day=min(28,hoy.day)))"   # dos fechas iguales
```

*Arreglo* (`07efe5f`): `_mes_siguiente()`, topado a 28 para que exista en
febrero. Encontrado **verificando el arreglo de §15**, no antes.

### 4 · «25 variables ficha.* y nueve proyecto.*» era falso · ARREGLADO
**Categoría A** por el mismo criterio que rige el bloque: una cifra sin medir
dentro del arreglo que trata justamente de cifras sin medir. Contadas sobre el
`.docx`: **21 y 10**. La cifra falsa estaba en tres ficheros.

*Reproducción:* extraer los `{{ ficha.* }}` de `var/templates_docx/E-001.docx`
con las etiquetas XML eliminadas (los marcadores Jinja vienen partidos entre
`<w:r>`).

*Arreglo* (`07efe5f`): corregida en los tres sitios.

---

## B · Corrompe o pierde datos en silencio

### 5 · El commit borra el contexto RLS y el `refresh` posterior revienta · ARREGLADO
**Categoría B.** `set_config(..., true)` fija la variable con alcance
**transacción**. `commit()` la termina y con ella se borra el GUC: la
transacción siguiente abre sin contexto, las policies no reconocen a nadie y la
sesión **no ve ni su propia fila** recién escrita. `db.refresh(obj)` levanta
«Could not refresh instance», FastAPI responde 500 **con la operación ya
guardada**, el usuario reintenta y duplica.

*Dónde:* no son 3 sitios, son **30 parejas `commit()` → `refresh()`** en
`backend/app`. La huella está en la base del demo: un proyecto
`DUPLICADO-CLAUDE` creado dos veces por esta vía.

*Reproducción:*
```bash
docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro \
  -c "SELECT nombre, count(*) FROM projects GROUP BY nombre HAVING count(*) > 1;"
```

*Arreglo* (`d64adca`): el inquilino se **recuerda** en `session.info` y un
listener `after_begin` lo vuelve a aplicar al empezar cada transacción. El GUC
sigue siendo transaccional a propósito: con `is_local=false` viviría lo que viva
la conexión, y las conexiones se reciclan en el pool, así que la petición
siguiente heredaría el inquilino anterior — eso ya no es un 500, es una fuga
entre inquilinos. Un test congela esa decisión.

### 6 · El resultado del simulacro de auditoría no se guarda · ARREGLADO
**Categoría B.** `execute_dry_run` hacía `flush()` y devolvía; nunca `commit()`.
Al cerrar la sesión la transacción se revertía: `audit_dry_run_results` estaba
siempre vacía, el histórico no tenía nada que comparar y la alerta de NC mayores
tampoco quedaba.

*Dónde:* `backend/app/agents/dry_run_api.py:36-39`.

*Reproducción:* ejecutar el dry-run desde `/admin/projects/{id}/audit-dry-run` y
después `SELECT count(*) FROM audit_dry_run_results;` — no sube.

*Arreglo* (`d64adca`). Ver §30: es el mismo defecto de clase que `70342a1` cerró
en tres hermanos en junio y no en éste.

### 7 · El «best-effort» del registro del INES no revertía · ARREGLADO
**Categoría B.** El `except` capturaba y seguía, prometiendo en su docstring que
«el informe se entrega igual». Falso: en PostgreSQL un statement fallido aborta
la transacción entera y SQLAlchemy la marca para rollback, así que el
`await db.commit()` de detrás revienta con `PendingRollbackError` y el endpoint
devuelve 500 — justo lo que el `except` decía estar evitando.

*Dónde:* `backend/app/motors/m27_conformity/api.py`,
`_registrar_ines_en_documents`.

*Reproducción:* sesión que falla al leer → `PendingRollbackError` en el commit
posterior. Reproducido con SQLAlchemy real antes de arreglarlo.

*Arreglo* (`07efe5f`): `await db.rollback()` dentro del `except`. Guardia nuevo
con una sesión de mentira que falla al leer. Encontrado **verificando el arreglo
de §17**, no antes.

---

## C · El resto, por daño

### 8 · Las tres pantallas que no arrancan lo que ellas mismas exigen · ARREGLADO
**Categoría C.** Hueco de interfaz, no de backend: el endpoint existe y funciona
en los tres casos, simplemente no había nada que lo llamara.

- **`/plan`** · Gantt vacío y ninguna acción para generar el plan.
- **`/dossier`** · sólo lectura, sin forma de crear el `AuditPreparationRun` que
  la propia página necesita para mostrar algo.
- **E-808**, la Autoevaluación CCN-STIC 808, **obligatoria para cerrar BÁSICA**:
  tenía plantilla en el catálogo, tenía un gate de cierre que la exige y
  **ningún productor**.

*Arreglo* (`9c02ca9`): `/plan` ya resuelto antes del bloque, congelado para que
no se caiga otra vez; `/dossier` con botón y `auditPrepApi.createRun`, y el
contrato deja de pedirle la categoría a la interfaz —invitarla a inventarla—: la
pone el backend desde el proyecto o responde 422 diciendo que falta; E-808 la
emite `m03_dda.annual_review`, que **es** la autoevaluación anual, y por la
fábrica documental.

El docstring de aquel gate afirmaba que «el generador del E-808 ya existe (M10
Audit-Sim)». Lo que existe es un DOCX de informe interno que no registra fila en
`documents` ni lleva código E-808 — que es justo lo que el gate comprueba.

### 9 · El test contaminado por orden · ARREGLADO
**Categoría C.** `test_bloque_g_metrics_publico_sin_auth` pasaba solo y fallaba
en la batería completa.

*Reproducción / bisección:*
```bash
pytest backend/tests/auth -q                                  # 90 passed
pytest backend/tests/api backend/tests/auth -q                # 2 failed
```
La causa no estaba en el test que se quejaba. El motor de base de datos se crea
al importar y su pool reutiliza conexiones; `pytest-asyncio` abre un bucle de
eventos nuevo por test y una conexión de asyncpg queda atada al bucle en que
nació. `/metrics` es de los pocos endpoints que **no** usa la sesión inyectada
por el arnés —abre la suya con `async_session()`—, así que le tocaba una
conexión heredada de un bucle muerto. Como el emisor captura el error y emite
`fulkro_llm_lectura_fallida 1` en vez de caerse (decisión correcta), el síntoma
visible era «faltan métricas», que no se parece a la causa.

*Arreglo* (`9c02ca9`): bajo `FULKRO_TESTING` el motor usa `NullPool` — no hay
nada que heredar. Y el emisor de métricas incluye ahora el **mensaje** del
error, no sólo el tipo.

### 10 · Batería · 26 fallos por falta de clave de cifrado · ARREGLADO · C1
`RuntimeError: Encryption master key unavailable` en todo lo que escribe una
columna `EncryptedText`, más `ValueError: app_secret_key too short` en m08/m16.
Se venían contando como «dependencia de entorno», que es una forma elegante de
decir que sólo pasaban en la máquina de su autor.

*Arreglo* (`9c02ca9`): `conftest.py` fija una clave maestra Fernet y un
`app_secret_key` de test — fijos, públicos, deterministas y con el nombre
diciendo que no son secretos. Con `setdefault`: si el operador exporta los
suyos, mandan.

### 11 · Batería · 11 fallos del corpus por PDF que el repo no trae · CERRADO CON MOTIVO · C1
Son los PDF de las nueve guías CCN-STIC serie 800 y la guía de gestión del
riesgo de la AEPD. **No están en el repositorio y no pueden estarlo**: son obra
de terceros con condiciones de reproducción propias — el mismo motivo por el que
`corpus_seed.sql.gz` se recortó a las cinco fuentes de libre redistribución.

*Cierre* (`9c02ca9`): marcador `requires_corpus_ccn` declarado en `pyproject`, y
el salto **dice qué falta y por qué**. El README publica cuántos quedan fuera.
Es la segunda mitad de la regla de Q3: si el entorno no puede proveer el
recurso, el test se marca y se declara.

### 12 · Batería · los 5 «errors» de pytest · ARREGLADO · C1
Un error de pytest es colección o fixture rota, que es peor que un fallo.
`backend/tests/motors/m21_diagnosis/test_iso27001_coverage.py:19` hace
`os.environ.setdefault("DATABASE_URL_SYNC", "…localhost:5433…")` y abre su propia
conexión: eran el **mismo defecto del puerto codificado en su versión fixture**.
Con la variable puesta por el entorno, coleccionan y pasan.

### 13 · Batería · los 3 «sin agrupar», atribuidos uno a uno · ARREGLADO · C3
- **m21** `test_with_notes` y cloud sync: caían por la clave de cifrado (§10).
- **m28** `drift_summary`: el test hacía `REFRESH MATERIALIZED VIEW` a pelo con
  `fulkro_app_bypassrls`, que **no es el propietario** («must be owner»), y el
  `RESET ROLE` de salida fallaba encima tapando la causa. Producción no refresca
  así: usa `fn_refresh_drift_summary()` `SECURITY DEFINER`. El test usa ahora ese
  camino.
- **m_compliance_monitor**: apuntaba a `/no/such/path` dando por hecho que
  `mkdir` fallaría; como root —que es como corre la imagen— esa ruta se crea.
  Ahora la imposibilidad es estructural: crear un directorio dentro de un fichero.
- **m_observability**: dependía de que el seed global hubiera dejado runs. Se
  fabrica el suyo.
- **legal_audit**: ver §14.

### 14 · `test_legal_audit_score_100` sólo pasa donde ya pasó antes · ARREGLADO · C1
Q3 lo arregló a medias: el directorio `progress/` no está versionado y el script
no lo creaba, así que reventaba con `FileNotFoundError` en un clon limpio. Se le
añadió el `mkdir` — correcto para un clon limpio. Pero seguía escribiendo
**dentro del árbol del repositorio**, así que heredaba el estado que el árbol
tuviera.

*Reproducción:* en esta máquina `progress/` había quedado en manos de `root` tras
una pasada dentro del contenedor, y el script, ejecutado por el usuario normal,
muere con `PermissionError: [Errno 13]`.
```bash
stat -c '%U:%G %a %n' progress          # root:root 755 progress
```
Dos síntomas, un defecto: el resultado dependía de quién hubiera pasado por ahí
antes.

*Arreglo* (`07efe5f`): `FULKRO_LEGAL_AUDIT_OUT`, y el test escribe en su propio
`tmp_path`. Sin la variable, el destino de siempre.

### 15 · Los 3 entregables de 28 que no salían · ARREGLADO (E-001) · CERRADO CON MOTIVO (E-702/E-703)
**E-001, Ficha de Seguimiento** · fallo de la plantilla, no del motor:
`HTTP 500 · Failed to render DOCX: None is undefined`. 21 variables `ficha.*` y
10 `proyecto.*` que **nadie construía**. *Arreglo* (`07efe5f`): productor que
las saca del plan, del parte de horas y de los hitos de facturación, y lo que no
consta lo dice con esas palabras en vez de inventar una cifra.

**E-702 y E-703** · `HTTP 422 · Missing required placeholders: score.score,
run.categoria_ens, run.fecha_emision`. Piden el resultado de una **ejecución** de
verificación, no datos del proyecto. *Cierre con motivo:* que no se generen sin
ella **es lo correcto** — un informe de verificación sin verificación detrás
sería un documento inventado, que es el defecto que esta campaña persigue. Lo
que sí era defecto es que el 422 listara variables sin decir de dónde salen:
ahora dice qué documento es y por dónde se lanza.

> El diagnóstico que circulaba en el README —«engancharlos al auditor interno»—
> **era incorrecto**: el auditor interno emite E-701; éstos son de M08,
> verificación técnica.

### 16 · Dos documentos firmables emitidos fuera de la fábrica documental · ARREGLADO
**Adenda E-604** (`m14_contracts/adenda_generator.py`) se renderizaba por su
cuenta con `render_docx`, subía a MinIO y anotaba en `provider_addendums`. Quien
renderiza por su cuenta se salta las cinco cosas que hace la fábrica: huella,
firma Ed25519, fila en `documents`, copia durable y `storage_path` canónico. Y
`documents` es exactamente lo que lee el generador del expediente del auditor.
Tenía plantilla en el catálogo, así que era enchufable tal cual.

**Acta de reunión E-005** (`m18_communication/minutes_service.py`) también es
firmable, pero **no tiene plantilla** —«E-005 sin plantilla» consta en tres
sitios de m09—, así que no se puede meter en la fábrica sin crearla primero. Eso
no era lo que impedía que el auditor la viera: faltaba **la fila**. Se registra
con la misma huella y la misma firma Ed25519 que el servicio ya calculaba.

*Reproducción / guardia:*
```bash
pytest backend/tests/audit_fixes/test_operaciones_normativas_un_solo_camino.py
```
La línea base está congelada: un tercer camino rompe el build.

### 17 · El informe INES no cabe en `documents` · ARREGLADO
El informe anual del art. 32 es **por organización y por año**, no por proyecto,
y `documents` exigía `project_id NOT NULL`. Registrarlo obligaba antes a decidir
a qué proyecto pertenece el informe de una organización con varios — que no es
un arreglo, es inventarse un dato de archivo.

*Reproducción:* `\d documents | grep project_id` → `not null`.

*Arreglo* (`07efe5f`): migración `ines_cabe_documents_001` · `project_id`
nullable + `client_id` + CHECK `ck_documents_ambito` (al menos uno de los dos) +
política RLS de dos ramas, la misma forma que este repositorio ya usa en
`audit_log`. **Mismo patrón que §2**: un valor legítimo que el esquema no sabía
representar.

### 18 · Los tests que necesitan base de datos no se ejecutan en CI · CERRADO CON MOTIVO
**3.371 de 6.709** tests están marcados `requires_db`. El job de CI se llama, con
todas las letras, `pytest · subconjunto sin BD sembrada`: levanta un PostgreSQL
pero no lo siembra, así que corre `-m "not requires_db"` y esos 3.371 **nunca
actúan como gate** — incluidos los de aislamiento RLS y cadena de hashes.

*Cierre con motivo:* sembrar la base en CI es trabajo de infraestructura, no de
este bloque, y la alternativa —dejar de declararlo— sería peor. Queda **dicho y
medido** en el README y aquí, que es lo que distingue una limitación conocida de
una mentira por omisión. La puerta de colección (§19) sí cubre que la suite
entera al menos *colecciona*.

### 19 · El marcador `requires_db` era ciego a quien se abre su propia conexión · ARREGLADO
`requires_db` se deriva de pedir el fixture `db`, lo que cubre 2.717 tests y
falla justo en los que se abren su **propia** conexión contra
`settings.database_url`. Ésos escapan al marcador y, por tanto, a
`-m "not requires_db"`: en una máquina sin PostgreSQL no **saltan** diciendo que
les falta la base, **revientan**.

*Dónde:* `backend/tests/conftest.py`, `pytest_collection_modifyitems`.

*Arreglo* (`07efe5f`): el hook mira también si el módulo construye un engine.
3.369 → 3.371 marcados. **Es un guardia que existía y era ciego**, no un guardia
que faltara.

### 20 · Un test que aseveraba el defecto · ARREGLADO · C2
`test_chat_stream_reset_survives_real_commit_mechanism` afirmaba **con un
assert** que tras un commit real la lectura project-scoped queda ciega («ARM A ·
ciego tras commit real»), y daba esa ceguera por contrato. La ceguera **era** el
defecto de §5. El brazo A dice ahora lo contrario.

Es la tercera categoría de Q3 —el test que asevera el defecto— y confirma su
premisa: cuando la norma está mal en el código, suele estar mal también en los
tests.

### 21 · Alembic tiene 5 heads · CERRADO CON MOTIVO
`alembic upgrade head` es ambiguo con más de un head. Medido sobre el grafo:

```
remediation_enhancement_b35_e_001 · sub_atom_5b_magerit_child_rls_001
radar_v9_perfect_f_001 · ines_cabe_documents_001 · cluster6_client_mfa_001
```

*Cierre con motivo:* eran 5 antes de este bloque y son 5 después — la migración
de §17 **consumió** un head (`no_afectada_cabe_001`) en vez de añadir uno, y
está verificado contra el commit padre. Fusionarlos es una migración de
convergencia que toca el orden de aplicación en producción: es trabajo de
despliegue (FASE J / Hetzner), no de un bloque de corrección, y hacerlo a ciegas
sin una base de producción contra la que probarlo sería exactamente la clase de
cambio que esta campaña reprocha.

### 22 · El `[MOCK]` de los agentes · CERRADO CON MOTIVO
O2 lo describía así: cuando falta la clave de API los agentes devuelven texto
`[MOCK]` fabricado y se registra como `status="success"` con tokens inventados.

*Medido hoy* (`backend/app/agents/base.py:275-299`): ya **no** es silencioso. El
diccionario lleva `mock=True`, la fila queda con `status="mock"`, `cost_usd=0` y
tokens NULL, y se eliminó el `tokens_output: 50` constante que se colaba en
`cost_usd` como si fuera una medida real.

*Cierre con motivo:* lo que queda abierto es distinto de lo que decía el
hallazgo — **hay un solo consumidor** que comprueba la bandera
(`m11_copiloto/inline_agents_api.py:298`), así que un entregable generado en modo
degradado sigue sin bloquearse en el resto de los caminos. Eso es un cambio de
producto (decidir qué hace el sistema cuando no hay clave), no una corrección, y
excede el alcance congelado. Queda declarado, con su medición.

### 23 · `sign_facturae_xades` lanza siempre · CERRADO CON MOTIVO
Incluso cuando `is_xades_available()` devuelve True, la función cae en un
`raise FacturaeSignatureNotAvailable("Implementación XAdES pendiente")`.

*Dónde:* `backend/app/motors/m15_billing/xades_signer.py:59-92`.

*Cierre con motivo:* es un stub **declarado**, no silencioso: el mensaje dice
exactamente qué falta (`TODO-FACE-XADES-CERT-FNMT-001`, certificado FNMT de
cliente real) y el caller recibe una excepción tipada. Implementarlo exige un
certificado que no existe hasta que haya cliente. No produce ninguna afirmación
falsa: falla en cerrado y lo dice.

### 24 · `npm audit` calibrado en `critical` deja pasar advisories HIGH · CERRADO CON MOTIVO
*Dónde:* `.github/workflows/security-scan.yml:7` — «npm audit · gate critical =
block». bandit sí bloquea en HIGH y el crash de `safety` sí bloquea.

*Cierre con motivo:* bajar el umbral a HIGH es una decisión de política de
riesgo sobre dependencias de terceros del frontend, con efecto inmediato sobre
la capacidad de mergear. Se declara la calibración real, que es lo que O2
reprochaba —que el gate dijera una cosa y midiera otra—.

### 25 · Nueve cadenas de modelo sueltas, y una inválida · CERRADO CON MOTIVO
```bash
git grep -ohE "claude-[a-z0-9.-]+" -- backend/app backend/scripts scripts | sort -u
```
Nueve cadenas sin registro central, unas fijadas con fecha y otras no.
`claude-sonnet` a secas **no es un identificador válido**: una llamada con esa
cadena falla en tiempo de ejecución.

*Cierre con motivo:* centralizar el registro de modelos es una refactorización
transversal de la capa de IA, no una corrección puntual, y ninguna de las nueve
produce una afirmación falsa en un documento. Queda declarado con el comando que
lo reproduce.

### 26 · «73 medidas» frente a un catálogo que declaraba 79 · ARREGLADO (verificado)
O2 lo daba por abierto. *Medido hoy:*
```bash
python3 -c "import yaml; d=yaml.safe_load(
  open('docs/catalogs/ens_measures_catalog_v1.yaml')); \
  print(len(d['medidas']), d['medidas_count'])"        # 73 73
```
El catálogo, su propio contador y lo publicado coinciden los tres. Se cierra con
la medición que lo demuestra.

> La primera versión de esta línea decía `['measures']` y **reventaba con
> `KeyError`**: la clave del fichero es `medidas`. Un comando publicado que no
> se ejecuta es el mismo defecto que este inventario persigue, así que queda
> dicho en vez de corregido en silencio.

### 27 · La evaluación de agentes no tiene tasa de aciertos real · CERRADO CON MOTIVO
Cuatro objetivos evaluados y 40 entradas, pero **ninguno tiene una tasa real**:
el gate contra el modelo necesita `ANTHROPIC_API_KEY` y no se ha ejecutado. Lo
verde mide el arnés y el cableado, no al modelo. Los umbrales de 0,80 son los que
declara cada dataset, **no una medición calibrada**.

*Cierre con motivo:* ejecutarlo cuesta llamadas reales al proveedor y no hay
clave en este entorno. Está declarado en el README en esos términos, que es la
diferencia entre una carencia conocida y una cifra inflada.

### 28 · Ningún cuestionario admite adjuntar un fichero · CERRADO CON MOTIVO
A un cliente al que se le pregunta «¿tenéis inventario de activos?» sólo puede
contestar con texto: no puede adjuntar el inventario. `onboarding_responses` no
tiene columna de fichero, mientras que evidencias, chat y mensajería sí.

*Cierre con motivo:* es una **carencia de producto, no una incorrección
normativa**: ninguna de esas preguntas afirma nada falso. Por eso quedó fuera de
la corrección normativa y sigue fuera del alcance de este bloque.

### 29 · El job de tests del CI nunca se ejecutaba · ARREGLADO (verificado)
O2: el job estaba condicionado a `workflow_dispatch` y pytest no había corrido
nunca (121 runs, ni uno por `workflow_dispatch`). *Medido hoy:*
`.github/workflows/ci.yml:124-129` documenta la activación del 2026-09-10 y el
job corre en `push` y `pull_request`. Se cierra con la medición.

### 30 · Lo que queda de los 21: el barrido arregló los casos, no la clase · ARREGLADO
`70342a1` (2026-06-14) cerró 21 bugs reales, y tres eran de clase «no hacía
commit»: simulacro pre-ENAC, acompañamiento-advance y chat cliente↔admin.

**Lo que quedaba de los 21 no era un arreglo sin hacer: era la clase.** Tres
meses después, §6 es exactamente el mismo defecto en un cuarto hermano
(`dry_run_api`) que aquel barrido no tocó, y §5 es el mismo mecanismo
(`commit()` y contexto de transacción) en su versión de lectura.

*Cierre:* §5 y §6 están arreglados, y —esto es lo que corta la clase— el arreglo
de §5 no quita `refresh` uno a uno sino que va al sitio donde no se puede
esquivar: el inquilino se recuerda y se vuelve a aplicar en cada transacción. La
trigésimo primera pareja `commit()`→`refresh()` que alguien escriba mañana ya
nace arreglada.

---

## Hallazgos nuevos

Encontrados **después** de congelar el inventario. Por la regla del bloque no se
trabajan: se declaran con su medición.

### N1 · `test_el_simulacro_se_guarda_de_verdad` falla en vez de saltar sin BD
Está marcado `requires_db`, así que con `-m "not requires_db"` queda
deseleccionado y no molesta. Pero si alguien corre el fichero suelto sin
PostgreSQL, **falla** en lugar de saltar, porque la conexión se abre en el cuerpo
del test y no en un fixture. Medición:
```bash
pytest backend/tests/audit_fixes/test_el_simulacro_se_guarda_de_verdad.py
# ConnectionRefusedError: ('127.0.0.1', 5433)
```
Es cosmético comparado con §19 —el marcador ya lo cubre donde importa— pero es la
misma familia: el motivo de no poder correr debería decirse, no reventar.

### N2 · `docker` no existe en esta distribución de WSL2
`make demo`, `make smoke` y `make recorrer-todo` no se pueden ejecutar aquí:
```bash
docker ps    # docker: command not found
pg_isready -h localhost -p 5432; pg_isready -h localhost -p 5433   # no response
```
No es un defecto del repositorio, pero **condiciona lo que este bloque pudo
medir** y por eso se declara: ver la sección de cierre del informe.

### N3 · Un `@pytest.mark.asyncio` sobre una función que no es async
`tests/motors/m_compliance_monitor/test_checks_atom_10_1.py:116` ·
`PytestWarning: The test is marked with '@pytest.mark.asyncio' but it is not an
async function`. El test pasa; la marca no hace nada. Cosmético.
