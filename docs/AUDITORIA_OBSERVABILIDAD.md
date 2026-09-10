# ¿Qué emite de verdad `m_observability`?

**Fecha**: 2026-09-10 · **Rama**: `main`

Un motor que se llama así lo va a abrir cualquiera que audite el repositorio,
precisamente por el nombre. Esto responde con hechos, y cada hecho lleva el
comando que lo reproduce.

---

## La respuesta corta

**No era observabilidad.** Era —y sigue siendo, además de lo nuevo— un motor de
**registro de llamadas al modelo y evaluaciones**, que es otra cosa muy
respetable pero no es lo que el nombre promete. De las dos salidas honestas
(renombrarlo por lo que hace, o añadir el mínimo real) se ha tomado la segunda,
porque el BLOQUE D acababa de dejar limpios los estados de `llm_interaction_log`
y exponerlos era casi gratis.

---

## Las cuatro preguntas, medidas

### ¿Hay métricas expuestas en algún sitio consumible?

**No había ninguna.**

```
$ grep -rn "prometheus\|opentelemetry\|start_http_server" backend/app --include=*.py | wc -l
0
$ git show HEAD:backend/app/main.py | grep -c '"/metrics"'
0
$ grep -riEn "prometheus|opentelemetry|statsd|datadog|sentry" \
    backend/requirements.txt backend/pyproject.toml | wc -l
0
```

Lo más parecido que existía son cuatro endpoints JSON bajo
`/admin/llm-observability/*` (`cost-summary`, `top-consumers`, `anomalies`,
`interactions`), protegidos con `require_owner`. Eso es **una pantalla de
administración**, no un punto de raspado: lo consume una persona con sesión
abierta, no un recolector de métricas. La diferencia importa porque de un
endpoint así no se puede sacar una alerta.

### ¿Hay trazas?

**No.** Cero apariciones de OpenTelemetry en todo el backend (comando de
arriba). No hay ni instrumentación, ni exportador, ni contexto de traza que
propagar.

### ¿Los registros son estructurados y llevan identificador de petición?

**No, y ésta era la carencia con más consecuencias prácticas.**

Se usa `loguru` con un sumidero por defecto (texto para humanos, sin
serializar). No había middleware que generara ni propagara un identificador:

```
$ grep -n "add_middleware" backend/app/main.py
430:    app.add_middleware(          # CORS
436:    app.add_middleware(          # CORS (rama alternativa)
445:app.add_middleware(BodySizeLimitMiddleware)
447:app.add_middleware(CSPMiddleware)
449:app.add_middleware(MarcosTimesheetMiddleware)
```

Las apariciones de `request_id` que sí hay en el código **son otra cosa**: el
identificador de una solicitud de derechos RGPD (`ErasureRequest`) o de una
petición de evidencia al cliente (`EvidenceRequest`). Son entidades de negocio,
no la petición HTTP:

```
$ grep -rn "request_id" backend/app --include=*.py | sed 's/:.*//' | sort | uniq -c
     35 backend/app/motors/m07_evidence/request_api.py
     17 backend/app/motors/m07_evidence/request_service.py
      9 backend/app/motors/m_compliance/rgpd_services.py
      8 backend/app/motors/m_compliance/compliance_admin_api.py
      2 backend/app/motors/m_compliance/rgpd_api.py

$ grep -n "request_id" backend/app/motors/m_compliance/rgpd_services.py | head -2
468:        request_id: UUID,
487:            {"i": str(request_id)},
```

Consecuencia concreta: ante «al cliente le falló algo a las 18:32» no había
manera de juntar las líneas de registro de esa petición y separarlas de las de
otras cinco simultáneas. Se seguía la pista a ojo, por marca de tiempo.

### ¿Entonces qué es?

Un registro de llamadas al modelo y evaluaciones. Lo que hay, medido:

| Fichero | LOC | Qué hace de verdad |
|---|---:|---|
| `eval_runner.py` | 544 | Ejecuta conjuntos dorados de evaluación |
| `llm_observability_service.py` | 427 | Agrega coste y consumo sobre `llm_interaction_log` |
| `models.py` | 259 | `ai_act_transparency_events` + `golden_eval_runs` |
| `golden_eval_runs_service.py` | 242 | Historial de ejecuciones de evaluación |
| `golden_datasets_loader.py` | 201 | Carga los conjuntos dorados |
| `transparency_service.py` | 192 | Eventos de transparencia (Reglamento de IA) |
| `api.py` | 126 | Los cuatro endpoints de administración |

Nada de eso está mal. Simplemente **no es lo que dice el nombre**, y quien abra
el motor buscando métricas y trazas no las iba a encontrar.

---

## El mínimo real que se ha añadido

Se eligió añadir en vez de renombrar por el motivo que apuntaba el encargo: D1
dejó los estados de `llm_interaction_log` limpios (`success` | `estimado` |
`mock` | `error`, catálogo cerrado por CHECK) y publicarlos cierra ese círculo.
Si el sustituto del modelo (`mock`) vuelve a colarse en producción, ahora se ve
en una gráfica en vez de descubrirse leyendo la pantalla de un cliente — que es
exactamente como se descubrió en el BLOQUE D.

**Sin dependencias nuevas.** El formato de exposición se escribe a mano
(`backend/app/motors/m_observability/metricas.py`). `prometheus_client` no está
en las dependencias y este repositorio acaba de pasar una campaña sobre
instalabilidad: añadir un paquete para generar texto plano habría sido un mal
cambio.

### 1 · `GET /metrics`

Formato de exposición Prometheus. Series emitidas:

| Métrica | Tipo | De dónde sale |
|---|---|---|
| `fulkro_llm_llamadas_total{estado}` | contador | base de datos |
| `fulkro_llm_coste_usd_total{estado}` | contador | base de datos |
| `fulkro_llm_latencia_segundos{estado}` | resumen | base de datos |
| `fulkro_llm_tokens_total{estado}` | contador | base de datos |
| `fulkro_llm_lectura_fallida` | indicador | 1 si la consulta falló |
| `fulkro_recuperacion_duracion_segundos{rama}` | histograma | memoria del proceso |
| `fulkro_recuperacion_errores_total{rama}` | contador | memoria del proceso |
| `fulkro_http_peticiones_total{metodo,ruta,codigo}` | contador | memoria del proceso |
| `fulkro_http_duracion_segundos{metodo,ruta}` | histograma | memoria del proceso |
| `fulkro_proceso_segundos_en_pie` | indicador | memoria del proceso |

**La columna de la derecha es la que hay que mirar**, y por eso está ahí. Las de
base de datos son ciertas para el sistema entero y sobreviven a un reinicio: con
dos réplicas las dos dicen lo mismo, que es lo correcto (el coste del sistema no
se duplica porque haya dos procesos). Las de memoria del proceso **son de cada
réplica**: quien las agregue tiene que sumarlas. Con dos réplicas detrás de un
balanceador —el montaje de D4— ése es el error de lectura más fácil de cometer.

Tres decisiones que conviene justificar:

- **Los cuatro estados se emiten siempre, aunque valgan cero.** Una serie que
  aparece y desaparece según haya datos rompe las alertas de quien la consume:
  `rate()` sobre una serie ausente no es cero, es *nada*.
- **Si la consulta a la base falla, no se emiten ceros**: se emite
  `fulkro_llm_lectura_fallida 1`. Una métrica que miente es peor que una que
  falta, que es la misma regla de toda esta campaña.
- **Se etiqueta con la PLANTILLA de la ruta** (`/api/v1/projects/{project_id}`),
  no con la URL concreta. Con la URL concreta, cada UUID crearía una serie nueva
  y en pocas horas habría decenas de miles: es la forma clásica de tumbar el
  sistema de métricas con el propio sistema de métricas.

**Está protegida.** El cuerpo incluye el coste acumulado y el mapa de rutas de la
API. En producción exige `Authorization: Bearer $FULKRO_METRICS_TOKEN` y, si esa
variable no está puesta, devuelve 503 en vez de servirse: negarse es más seguro
que exponerse por omisión.

### 2 · Identificador de correlación

`backend/app/motors/m_observability/correlacion.py`. Por petición:

1. Toma el `X-Request-ID` entrante o genera uno. **Se reutiliza el de fuera a
   propósito**: si no, la traza se parte justo en la frontera del sistema, que
   es donde más falta hace.
2. Lo mete en el contexto de `loguru`, así que toda línea emitida durante esa
   petición lo lleva sin que nadie tenga que acordarse de pasarlo.
3. Lo devuelve en la cabecera `X-Request-ID`, para que quien ve el error en el
   navegador pueda decir exactamente cuál mirar.
4. Emite una línea por petición con método, ruta, código y duración.

El identificador entrante **se sanea** (sólo alfanuméricos y `-_:.`, 64
caracteres): viene de fuera, y sin sanear cualquiera podría inyectar saltos de
línea y fabricar entradas falsas en el registro.

El middleware se registra **el último** porque Starlette los ejecuta en orden
inverso: así envuelve a todos los demás y el identificador está puesto antes de
que ninguno haga nada. Registrado antes, las líneas de los middlewares de arriba
saldrían sin él, que es justo cuando más falta hace.

Registro en JSON con `FULKRO_LOG_JSON=1`. **No es el valor por defecto**: una
persona mirando `docker logs` es el caso normal en este proyecto, y poner JSON
por defecto habría hecho ilegible el arranque del demo, que es lo primero que ve
quien clona el repositorio.

### 3 · Latencia de recuperación por etapa

`backend/app/corpus/retrieval.py` cronometra las etapas por separado —hoy
`embebido` y `vectorial`— y no sólo el total, porque el total no dice dónde está
el problema.

**Actualizado el 2026-09-11**: hasta esa fecha las etapas eran cuatro (`bm25`,
`vectorial_con_embebido`, `fusion` e `hidratado`), porque el buscador fusionaba
dos ramas. La fusión se retiró tras medirla (ver `docs/EVAL_RECUPERACION.md`) y
con ella se fueron dos de las series. Queda además una etiqueta menos ambigua:
`vectorial_con_embebido` mezclaba en una sola serie el embebido de la consulta
—que se lleva el 80 % del reloj— con la consulta a Postgres; ahora son dos series
separadas y se ve cuál es cuál sin tener que leerse el código.

---

## Lo que NO se ha hecho, y por qué

- **Trazas distribuidas.** Con un solo servicio y una sola base, una traza
  añadiría una dependencia grande y diría casi lo mismo que la línea por
  petición más el identificador de correlación. Cuando haya más de un servicio
  al que seguir, cambia el cálculo.
- **Métricas de negocio** (proyectos por estado, evidencias firmadas). Salen de
  la misma base y son fáciles de añadir, pero no eran la carencia: la carencia
  era que no había *ningún* punto de raspado.

---

## Cómo comprobarlo

```
make demo
curl -s http://127.0.0.1:18000/metrics | head -40
curl -si http://127.0.0.1:18000/api/v1/health | grep -i x-request-id
```
