# ADR-004 · Una llamada al modelo que falla no puede quedar registrada como éxito

- **Fecha**: 2026-09-10
- **Estado**: aceptada, implementada y verificada contra PostgreSQL real
- **Bloque**: D · D1
- **Numeración**: ADR-003 está reservado para la escalabilidad horizontal (D4),
  que se decidió antes en el enunciado y después en el tiempo.

## Contexto

`backend/app/agents/base.py` capturaba **cualquier** excepción de la llamada al
modelo y devolvía una respuesta fabricada. Esa respuesta se registraba en
`llm_interaction_log` con `status="success"`.

Medido sobre el árbol anterior (`c8ece1c`), forzando `ConnectionError` en el
router:

```
$ git show c8ece1c:backend/app/agents/base.py > /tmp/base_antiguo.py
$ docker run --rm -v "$PWD:/app" -v /tmp:/antes -w /app -e PYTHONPATH=/app \
    fulkro/backend:test python /antes/demostrar.py

LLM call failed for agent 99 (Agente de prueba D1): proveedor caido
== invoke() NO lanzo excepcion. Devolvio:
   texto        : [MOCK-FALLBACK] Agent 99 (Agente de prueba D1). Model: sonnet-4.5...
   tokens_input : 172
   tokens_output: 50
== fila grabada en llm_interaction_log:
   status           : success
   prompt_tokens    : 172
   completion_tokens: 50
   total_tokens     : 222
   cost_usd         : 0.001266
```

Tres mentiras encadenadas en una sola fila:

1. `status="success"` para una llamada que nunca salió a la red.
2. `completion_tokens=50` — constante literal en el código, no una medida.
   `prompt_tokens=172` — palabras contadas con `.split()`, tampoco una medida.
3. `cost_usd=0.001266` — dinero calculado sobre los tokens inventados del punto 2,
   y sumado sin filtro por las siete consultas de agregación del repositorio.

El esquema no podía impedirlo: `status` era `String(16)` sin restricción y los
tres contadores eran `NOT NULL`, así que **"no hubo llamada" no tenía forma de
escribirse**. Había que inventar un número.

## Decisión

**1. El fallo se propaga.** `_call_llm` lanza `LLMCallFailed`. Antes de propagar,
`invoke()` graba una fila `status="error"` con tokens `NULL`, `cost_usd` `NULL`
y `error_message` con el tipo y el texto de la excepción. Un fallo deja rastro;
lo que no hace es hacerse pasar por otra cosa.

**2. El modo degradado se conserva, pero con nombre propio.** Sin
`ANTHROPIC_API_KEY` se sigue devolviendo una respuesta de relleno —la suite
entera depende de ello (`backend/tests/conftest.py` vacía la clave a propósito
para que ningún test salga a la red)— pero la fila queda `status="mock"`,
`cost_usd=0` y tokens `NULL`.

**3. Cuatro estados canónicos**, en `backend/app/core/ai/llm_log_status.py`:

| status     | significa                                          | ¿suma? | tokens   |
|------------|----------------------------------------------------|--------|----------|
| `success`  | el proveedor respondió y devolvió su recuento       | sí     | medidos  |
| `estimado` | hubo llamada real, el proveedor NO devolvió recuento| sí     | estimados|
| `mock`     | no hubo llamada (sin clave de API)                  | **no** | `NULL`   |
| `error`    | la llamada falló                                    | **no** | `NULL`   |

**4. Ninguna agregación suma `mock` ni `error`.** El filtro está en las siete
consultas: dos en `copilot_rate_limit.py` (el tope de gasto del copiloto) y
cinco en `m_observability/llm_observability_service.py`.

**5. La base de datos lo impone, no sólo el código.** Migración
`llm_log_status_no_finge_exito_001`, tres `CHECK`.

## Las contrapartidas, una por una

### `NULL` en los contadores, a cambio de perder el `NOT NULL`

`NULL` es "no medido"; `0` sería "medido y salió cero", que es otra cosa. Es la
distinción que faltaba y la que obligaba a inventar el 50.

El precio es real: tres columnas dejan de estar garantizadas como no nulas.
Se paga con `ck_llm_log_tokens_medidos_no_nulos`, que **mantiene la garantía
donde importa**: una fila `success` o `estimado` sigue obligada a traer los tres
contadores. El `NULL` queda reservado a las filas que no suman.

Antes de tocar nada se midió quién lee esas columnas:

```
$ command grep -rn "completion_tokens\|prompt_tokens\|total_tokens" \
    --include=*.py backend/app | command grep -v "llm_router\|pricing.py"
```

Todos los consumidores son `SUM(...)` con `COALESCE`, y `SUM` ya ignora `NULL`.
El único que leía fila a fila era `get_anomaly_alerts`, que ahora publica `None`
en vez de `0` — coherente, porque las anomalías son justamente las filas sin
medir. Ningún otro sitio lee la columna de una fila suelta.

### `estimado` sí suma, aunque no sea una medida

`agent_14_copiloto/service.py` escribe la vía de *streaming*, donde el proveedor
no devuelve recuento de tokens y el código los estima por longitud (~4
caracteres por token). Antes eso se grababa como `success`.

Se podría haber excluido de las sumas por no ser una medida. **No se hace**,
porque esa cifra alimenta el tope mensual de gasto del copiloto, y un tope tiene
que pecar de conservador: excluirla reabre la evasión del tope que el propio
comentario del código dice haber cerrado (`§4.5 · antes 0 → evasión`).

La contrapartida es que el coste publicado mezcla medidas y estimaciones. Se
paga con visibilidad, no con exclusión: la fila lleva estado propio, y
`get_anomaly_alerts` escribe literalmente `coste estimado, no medido` cuando una
de estas filas sale listada.

### El diccionario de `invoke()` devuelve `0`, la fila guarda `NULL`

Asimetría deliberada. La fila es el registro persistente y ahí `NULL` es lo
correcto. El diccionario en memoria alimenta cinco sitios que hacen aritmética
con él, dos de ellos a través de modelos pydantic que declaran `int`:

```
$ command grep -rn 'get("tokens_in\|get("tokens_out' --include=*.py backend/app \
    | command grep -v "or 0"
backend/app/api/v1/workflows_simple.py:186,187,190,191
backend/app/motors/m11_copiloto/inline_agents_api.py:231,232
backend/app/agents/api.py:583,584
backend/app/motors/m_meetings/actions.py:143,144
backend/app/motors/m04_gap/llm_prioritizer.py:401,402
```

Devolver `None` obligaría a tocar esos cinco sitios y a volver opcionales dos
modelos de respuesta que el frontend consume tipados. El `0` que se devuelve
**no es una estimación**: una llamada que no ocurrió consumió cero tokens del
proveedor. Lo que se ha eliminado es el `50` constante y el conteo por palabras.
Y para que nadie confunda un cero con una medida, el diccionario lleva ahora dos
claves explícitas: `tokens_medidos: False` y `mock: True`.

### El `downgrade` pierde información

Volver a `NOT NULL` exige rellenar lo que quedó sin medir, y se rellena con `0` —
justo la cifra inventada que esta migración existe para evitar. Está escrito en
el propio `downgrade()`: bajar de versión **pierde** la distinción entre "cero
medido" y "no medido". Es aceptable porque el `downgrade` es una salida de
emergencia, no una operación rutinaria.

## Consecuencias verificadas

```
$ APP="$(command grep -m1 '^DATABASE_URL=' .env.demo | cut -d= -f2- | tr -d '"')"
$ docker run --rm --network fulkro-demo_fulkro-demo-net \
    -e DATABASE_URL="$APP" -e FULKRO_USE_LIVE_DB=1 -e PYTHONPATH=/app \
    -v "$PWD:/app" -w /app fulkro/backend:test \
    python -m pytest backend/tests/agents/test_agent_base_no_finge_exito.py -q
7 passed in 5.11s
```

Los cuatro primeros no necesitan base de datos y por tanto corren en el job
`test` de CI, que va con `-m "not requires_db"`. Los tres últimos comprueban
sobre PostgreSQL real que el coste agregado no se mueve y que los `CHECK`
rechazan tanto una fila `mock` con coste como una `success` sin tokens.

Restricciones aplicadas, leídas de la base:

```
$ docker exec fulkro-demo-postgres-1 psql -U fulkro -d fulkro -c "\d llm_interaction_log"
"ck_llm_log_sin_coste_inventado"     CHECK (status IN ('success','estimado') OR cost_usd IS NULL OR cost_usd = 0)
"ck_llm_log_status_canonico"         CHECK (status IN ('success','estimado','mock','error'))
"ck_llm_log_tokens_medidos_no_nulos" CHECK (status NOT IN ('success','estimado')
                                            OR prompt_tokens IS NOT NULL
                                            AND completion_tokens IS NOT NULL
                                            AND total_tokens IS NOT NULL)
```

Regresión en el resto de la suite: ninguna atribuible a este cambio.

```
$ docker run ... python -m pytest backend/tests/agents backend/tests/api \
    backend/tests/motors/m_observability -q
1 failed, 557 passed, 38 skipped
```

El único fallo es
`test_golden_eval_runs_api.py::test_admin_list_runs_filter_by_agent_name`, y es
**del arnés, no del sujeto**: pide datos que sólo siembra
`scripts/build_test_db.sh` y aquí se corre contra la base del demo. Lo dice él
mismo (`0 runs en total: no hay datos y este test no puede distinguir un filtro
correcto de una base vacía`) y falla igual con el árbol anterior, comprobado con
`git stash`.

## Lo que este cambio NO arregla

- `backend/app/agents/copilot_admin_service.py` y `copilot_cliente_service.py`
  siguen escribiendo `status="success"` a mano. Es correcto: ahí los tokens
  vienen del proveedor. Pero si esas vías adquieren un modo degradado, tendrán
  que usar los mismos estados.
- El coste publicado sigue mezclando `success` y `estimado`. Separarlo en dos
  cifras en el panel de administración es trabajo de interfaz, no de este ADR.
