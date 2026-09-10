# Histórico de workflows retirados

Este directorio guarda workflows de GitHub Actions que **ya no se ejecutan**. Están aquí
como historia (por qué existieron, por qué se retiraron y qué se aprendió de ellos), no
como plantilla a copiar. Al vivir fuera de `.github/workflows/`, GitHub no los carga.

---

## `deploy.yml.retirado` — CD por SSH a Hetzner

**Retirado el 2026-09-10.** Fichero original: `.github/workflows/deploy.yml`
(119 líneas, sin modificar; se conserva tal cual estaba en `main`).

### Por qué se retira en vez de parchearse

Desplegaba por SSH contra un servidor Hetzner que se dio de baja el **2026-09-09**.
El destino ya no existe, así que no hay nada que arreglar: cualquier parche sería
mantenimiento de un despliegue sin máquina al otro lado. Cuando vuelva a haber
infraestructura, el CD se reescribe contra ella, y este fichero sirve de referencia
de qué hacía (`git pull --ff-only` + `docker compose build` + `up -d` + espera a
`healthy` real, sin `sleep` ciego) y de qué NO repetir.

Antes de moverlo se comprobó que **ningún otro workflow lo invoca**:

```
$ command grep -rn "workflow_call" .github/
    # (sin resultados)
$ command grep -rn "deploy.yml" .github/ scripts/ Makefile
    # (sin resultados)
```

`workflow_call` no aparece en ningún workflow del repo, así que moverlo no rompe
ninguna cadena de llamadas: sólo deja de dispararse en cada push a `main`.

### Los dos defectos que hay que llevarse de aquí

**1. El gate de migraciones era *fail-open*: si Alembic reventaba, el gate pasaba
(líneas 69-73).** Es el defecto grave, más que el host caído, porque es un patrón
que se repite:

```yaml
# deploy.yml.retirado:69-73
heads="$(python -m alembic heads 2>&1 || true)"
echo "$heads"
n="$(echo "$heads" | grep -c '(head)' || true)"
if [ "${n:-0}" -ge 2 ]; then echo "::error::Multiple Alembic heads (${n}) · prod-breaker"; exit 1; fi
echo "Alembic heads = ${n:-desconocido}"
```

El `2>&1 || true` de la línea 69 mete el mensaje de error *dentro* de la variable y
anula el código de salida. Si Alembic no arranca (import roto, migración con error de
sintaxis, base inalcanzable), el texto capturado no contiene `(head)`, el contador de
la línea 71 vale `0`, la condición de la línea 72 es falsa y el bloque termina en
`exit 0`. El gate sólo detectaba el caso «multi-head»; nunca el caso «Alembic no
arranca», que es el peor de los dos justo antes de tocar producción.

Reproducido el 2026-09-10 sustituyendo el comando por uno que revienta:

```
$ heads="$(alembic_que_revienta 2>&1 || true)"; n="$(echo "$heads" | grep -c '(head)' || true)"
$ if [ "${n:-0}" -ge 2 ]; then exit 1; fi; echo "Alembic heads = ${n:-desconocido}"
heads=[Traceback (most recent call last): ImportError: no module named alembic]
Alembic heads = 0
EXIT=0
```

Fallo de la herramienta convertido en verde. Si se reescribe el CD, la forma correcta
es dejar que el fallo del comando tumbe el paso (sin `|| true`) y añadir la condición
simétrica: fallar también si el contador es `0`, porque «cero heads» tampoco es un
estado válido.

**2. El «verde si faltan secrets» era un `exit 0` explícito (líneas 85-88).**

```yaml
# deploy.yml.retirado:85-88
if [ -z "$HOST" ] || [ -z "$KEY" ]; then
  echo "::notice::Secrets HETZNER_* aún no configurados — deploy OMITIDO (no es un fallo)."
  exit 0
fi
```

La intención era razonable (no molestar mientras no hubiera secretos configurados),
pero el efecto es que el workflow podía salir verde **sin haber desplegado nada**, y
desde fuera un tick verde de un workflow llamado «Deploy» se lee como «desplegado».
Además, en el estado en que se retira los tres secretos **sí** estaban puestos, así que
ni siquiera entraba por esta rama: intentaba la conexión SSH contra un host que ya no
responde. Un `skip` debe usar `if:` a nivel de job (que GitHub pinta como *skipped*,
no como *success*), nunca un `exit 0` dentro del `run`.

### Qué queda cubierto sin este workflow

Los dos jobs de verificación que traía (`gate`: ruff + `compileall`; `migrations`:
`compileall migrations` + recuento de heads) no se pierden como cobertura: `ci.yml`
ejecuta ruff en cada push y, desde 2026-09-10, ejecuta además tests reales. El
recuento de heads de Alembic **no** tiene hoy sustituto en CI; queda como hueco
declarado, no como algo tapado.
