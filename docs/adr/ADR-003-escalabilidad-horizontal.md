# ADR-003 · ¿Es escalable en horizontal? Medido con dos réplicas

- **Fecha**: 2026-09-10
- **Estado**: aceptada · con una limitación conocida y escrita
- **Bloque**: D · D4
- **Cómo repetirlo**: `python3 scripts/medir_escalabilidad.py` (inventario, no
  necesita la aplicación levantada) y `bash scripts/probar_dos_replicas.sh`
  (la prueba de verdad, con el demo en pie).

## La pregunta

*«¿Es escalable? Contéstalo con medidas, no con adjetivos.»* Cuatro
comprobaciones y una prueba. Esto es el resultado, salga lo que salga.

---

## La prueba que lo zanja

Dos réplicas del backend detrás de nginx con reparto por turnos
(`docker-compose.escalabilidad.yml` + `infra/docker/nginx-escalabilidad.conf`).
No es una simulación: son dos procesos `uvicorn` distintos, en dos contenedores
distintos, y nginx alterna entre ellos petición a petición.

```
$ bash scripts/probar_dos_replicas.sh

0 · levantar la pila con dos replicas
  OK  dos replicas del backend en pie y sanas   fulkro-demo-backend-1 fulkro-demo-backend-2
1 · ¿nginx reparte de verdad?
  OK  el reparto alcanza a las dos replicas     5 172.25.0.5:8000   7 172.25.0.7:8000
2 · las claves de firma, ¿son las mismas en las dos replicas?
  OK  clave ed25519_signing_private.pem identica en A y B    sha256 6afcedd944c7edf4…
  OK  clave m05_signing_dev.ed25519.pem identica en A y B    sha256 8da73ea95e94fb67…
  OK  clave m6_signing_dev.ed25519.pem identica en A y B     sha256 8df34530aee1be22…
  OK  FULKRO_AUTH_PRIVATE_KEY identica en A y B              sha256 ac3a93b065a79e5b…
  OK  FULKRO_ML_PRIVATE_KEY identica en A y B                sha256 a3aa538504559ac6…
3 · la sesion abierta en una replica, ¿vale en la otra?
  OK  entrar contra la replica A                mfa_ticket emitido
  OK  cookie de sesion emitida por A            fulkro_session
  OK  esa MISMA cookie vale en la replica B     HTTP 200 · demo@fulkro.es
  OK  8 peticiones repartidas con la misma sesion   todas 200
4 · un enlace de portal emitido por A, ¿funciona en B?
  OK  A emite un enlace de portal firmado       Ed25519 · OTP 721707
  OK  B sirve el portal del enlace emitido por A    HTTP 200 (resumen)
5 · un evento en tiempo real, ¿llega a los suscriptores de las DOS replicas?
  OK  se provoca un evento real (m17.plan.updated)   PATCH de una tarea · HTTP 200
  OK  el evento llega a las DOS conexiones           hay difusion entre replicas

 Resultado: 15 correctas, 0 fallidas
```

**La primera vez esto no salió así.** El apartado 5 dio
`solo a 1 de 2`, y ese fallo es la razón de que exista el arreglo que se
describe abajo. El «arregla lo mínimo para que pase y vuelve a medir» del
encargo se cumplió: **1 de 2 → 2 de 2**.

---

## Las cuatro comprobaciones

### 1 · Escrituras a disco fuera de `/tmp`

```
$ python3 scripts/medir_escalabilidad.py
     15  sin clasificar
     12  /tmp (efímero · no cuenta)
      5  disco del contenedor · var/keys      <-- CLAVES
      2  disco del contenedor · var/evidences
      1  disco del contenedor · var/ (otros)
     35  TOTAL sitios de llamada

   Subidas a almacenamiento de objetos (MinIO/S3): 22 sitios
```

**La etiqueta dice lo que el comando mide**: son **sitios de llamada** en el
código, no escrituras ejecutadas.

Lo que importa: **MinIO existe y se usa** (22 sitios de subida, con un cliente
propio en `backend/app/core/storage/minio_client.py`), **pero no es el único
camino**. Coexisten dos:

| qué | dónde acaba | ¿vale con varias réplicas? |
|---|---|---|
| documentos, actas, adendas, informes | MinIO (22 sitios) | **sí** |
| ficheros de evidencia (`ingestion_service.py:197`) | `var/evidences/` del contenedor | sólo si `var/` es un volumen compartido |
| cuarentena del antivirus | `var/quarantine/` del contenedor | igual |
| claves de firma M05/M06/M07 | `var/keys/` del contenedor | igual, y es lo más grave |
| volcados de depuración de 10 agentes | `/tmp` con ruta fija | irrelevante (efímero) |

En el compose del demo, `/app/var` es un **volumen con nombre**
(`fulkro-demo_vardata`), y por eso las dos réplicas comparten claves y ficheros:

```
$ docker inspect fulkro-demo-backend-1 --format '{{range .Mounts}}{{.Type}} {{.Destination}}{{println}}{{end}}'
volume /app/var
```

**Eso funciona porque las dos réplicas están en la MISMA máquina.** En dos
máquinas, un volumen local no se comparte, y entonces:

- las evidencias subidas a una réplica no existen para la otra,
- y cada réplica genera sus propias claves de firma.

### 2 · Las tres claves Ed25519 — y las otras tres

La pregunta del encargo dice «las tres claves». **Son seis**, y se comportan de
dos maneras distintas. Ésta es la parte que más importa de todo el ADR.

| clave | para qué | de dónde sale | ¿aborta el arranque si falta? |
|---|---|---|---|
| `FULKRO_AUTH_PRIVATE_KEY` | cookie de sesión | **entorno** | **sí** |
| `FULKRO_ML_PRIVATE_KEY` | enlaces mágicos y portales | **entorno** | **sí** |
| `FULKRO_BACKUP_SIGNING_KEY` | firma de backups (M26) | **entorno** | **sí** |
| `FULKRO_M05_SIGNING_PRIVATE_KEY` | firma de documentos | entorno **o disco** | **no** |
| `FULKRO_M06_SIGNING_PRIVATE_KEY` | document factory | entorno **o disco** | **no** |
| `FULKRO_M07_SIGNING_PRIVATE_KEY` | firma de evidencias | entorno **o disco** | **no** |

Medido en el demo:

```
$ docker exec fulkro-demo-backend-1 sh -lc 'echo ${FULKRO_M05_SIGNING_PRIVATE_KEY:-AUSENTE}'
AUSENTE
$ docker exec fulkro-demo-backend-1 ls -la /app/var/keys
-rw------- 1 fulkro fulkro 119 ... ed25519_signing_private.pem
-rw------- 1 fulkro fulkro 119 ... m05_signing_dev.ed25519.pem
-rw------- 1 fulkro fulkro 119 ... m6_signing_dev.ed25519.pem
```

**La respuesta a «¿qué pasa exactamente si no están en el entorno?»:**

- **Las tres primeras**: el arranque **aborta**
  (`startup_checks.py:_REQUIRED_ENV_VARS` → `verify_critical_env()`). Como el
  arranque no llega a servir nada, no puede haber dos réplicas firmando
  distinto. **La preocupación del encargo —«dos réplicas firman distinto y eso
  rompe los portales por token»— NO se materializa**: el enlace de portal se
  firma con `FULKRO_ML_PRIVATE_KEY`, que viene del entorno, es la misma en todas
  las réplicas, y el arranque se niega a empezar sin ella. Verificado en el
  apartado 4 de la prueba: **el enlace que emite A lo sirve B**.
- **Las tres de firma de documentos y evidencias**: NO abortan. Cada proceso
  **se genera la suya en disco** si no la encuentra. Con `var/` compartido, la
  primera réplica que arranca la crea y las demás la reutilizan. Sin `var/`
  compartido, **cada réplica firma con una clave distinta** y lo firmado en una
  no se verifica en la otra. El propio código lo dice
  (`startup_checks.py:62-68`): *«cada `docker recreate` rotaba la clave e
  invalidaba la verificación de toda firma previa»*.

### 3 · Sesiones: ni Redis ni memoria del proceso

```
mecanismo: cookie firmada Ed25519 (JWT), sin estado en el servidor
cookie: fulkro_session
guardada_en_redis: False
guardada_en_memoria_del_proceso: False
```

La sesión **no ata a ninguna réplica**: la valida cualquiera que tenga la misma
`FULKRO_AUTH_PRIVATE_KEY`. Es la razón por la que el apartado 3 de la prueba
sale verde sin haber tocado nada: ocho peticiones repartidas por turnos entre
dos procesos, todas 200.

### 4 · Estado en la memoria del proceso

12 estructuras mutables a nivel de módulo. Cinco importan de verdad:

| dónde | qué | qué se rompe con N réplicas |
|---|---|---|
| `core/sse_dispatcher.py` | suscriptores + buffer de repetición | **era el fallo**; ver abajo |
| `m09_audit_prep/public_api.py:62` | `_failed_attempts` (bloqueo por intentos fallidos del portal de auditor) | el atacante dispone de **N veces** los intentos |
| `m08_verification/public_api.py:65` | `_RATE_STATE` (límite de peticiones) | el límite pasa a ser **N × el configurado** |
| `m25_lifecycle/public_api.py:60` | `_RATE_STATE` | igual |
| `m11_copiloto/inline_agents_api.py:105` | `_suggestion_cache` (30 min) | sólo desperdicia: N veces la misma llamada al modelo |

Los tres primeros son de seguridad, no de rendimiento: **un límite en memoria de
proceso se multiplica por el número de réplicas**. No estaba escrito en ninguna
parte. Ahora lo está.

---

## Lo que se arregló, y por qué eso y no más

`SseDispatcher` era un pub/sub en memoria: diccionario de colas y `deque` de
repetición, sin intermediario. La primera medición lo confirmó en ejecución, que
es distinto de deducirlo leyendo:

```
5 · un evento en tiempo real, ¿llega a los suscriptores de las DOS replicas?
  FALLO  el evento llega a las DOS conexiones   solo a 1 de 2
```

**Arreglo mínimo**: publicar en Redis lo que se despacha, y entregar en local lo
que llegue de otras réplicas. Redis **ya estaba en la pila** (Celery lo usa), así
que no se añade ninguna pieza nueva. `dispatch()` se parte en dos —
`entregar_local()` y `publicar_en_bus()` — y un puente por proceso escucha
`fulkro:sse:*`. Cada mensaje lleva el identificador del proceso que lo publicó,
para no entregar dos veces lo propio.

**Sin `REDIS_URL` no hay puente y el comportamiento es exactamente el de antes.**
Eso importa: el modo de una réplica, que es el que usa el demo y el que usará el
primer cliente, no depende de nada nuevo.

### Contrapartidas, una por una

**Entrega «como mucho una vez».** Si Redis se cae, o una réplica está arrancando
cuando se publica, el evento se pierde y nadie lo reintenta. Se acepta porque el
SSE de esta aplicación es una **señal para refrescar**, no un canal de datos: la
interfaz vuelve a pedir el estado por HTTP. Un evento perdido cuesta que una
pantalla tarde en actualizarse hasta la siguiente acción; no cuesta un dato.
Si algún día se despacha por SSE algo que no se pueda volver a pedir, esta
decisión hay que revisarla.

**El buffer de repetición sigue siendo de proceso.** El `deque(maxlen=100)` por
canal, que sirve para el `Last-Event-ID` del navegador, **no se comparte**. Si el
navegador reconecta y cae en otra réplica, el hueco no se rellena. Se acepta por
lo mismo: la interfaz refresca por HTTP al reconectar. Compartirlo exigiría un
`Stream` de Redis, no un `publish`, y eso ya no es «lo mínimo».

**Un salto de red por evento.** Medido no está: no se ha comparado la latencia
antes y después, porque con un solo suscriptor la diferencia queda por debajo del
ruido. **No medido**, y se dice así.

**Redis pasa a ser una dependencia del tiempo real multi-réplica.** No del
arranque —el puente degrada con un aviso en el log— pero sí de la función. Con
Redis caído y dos réplicas, se vuelve al comportamiento anterior: cada réplica
avisa sólo a los suyos, en silencio salvo por ese aviso.

---

## Veredicto

**Con esta configuración, sí escala en horizontal**, y está medido: dos réplicas
reales detrás de un reparto por turnos, 15 comprobaciones, 0 fallidas.

**Con estas cinco condiciones**, que no son opcionales:

1. Las seis claves Ed25519 **inyectadas por entorno**, las seis, iguales en
   todas las réplicas. Hoy tres se generan en disco si faltan, y eso sólo
   funciona porque comparten volumen.
2. `var/` en un almacenamiento **compartido de verdad** entre réplicas, o las
   evidencias migradas a MinIO. Hoy dos réplicas en la misma máquina comparten
   un volumen local; dos máquinas no comparten nada.
3. **Redis disponible**, o no hay tiempo real entre réplicas.
4. Los límites de intentos y de peticiones **movidos fuera del proceso** antes de
   apoyarse en ellos como control de seguridad con más de una réplica.
5. La base de datos sigue siendo **una**. Esto escala la capa de aplicación, no
   la de datos, y ese techo no se ha medido.

**Lo que NO se ha medido, y por tanto no se afirma**: rendimiento, latencia,
cuántas réplicas aguanta la base, comportamiento con réplicas en máquinas
distintas, y el propio techo de PostgreSQL. Aquí sólo se ha medido
**corrección** con dos réplicas: que nada se rompa al repartir.

Con esas condiciones sobre la mesa, la palabra «escalable» puede escribirse.
Sin ellas, no.
