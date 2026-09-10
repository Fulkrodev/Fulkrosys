# Informe · Instalabilidad (C0) y CI/CD (C1)

- **Fecha:** 10 de septiembre de 2026
- **Punto de partida:** `2fe3462`, que era lo publicado en `main`
- **Al cerrar:** 21 commits después

Regla que gobierna este documento: **cada afirmación lleva pegado el comando que la produce**. Lo
que no se pudo medir se dice, y se dice por qué. Las cifras que no cuadraron con lo que se creía
—incluidas las propias— están corregidas en el sitio, no borradas.

---

## 1. El antes y el después, medido con el mismo método

Ambas columnas salen del mismo guion, en el mismo tipo de máquina: un contenedor **Ubuntu 24.04
con su propio demonio Docker**, sin acceso al checkout local, clonando desde GitHub. El arnés está
en el repositorio (`scripts/maquina_limpia_up.sh` + `scripts/traza_instalacion_limpia.sh`) y la
traza completa en [`docs/INSTALL_TRACE.md`](INSTALL_TRACE.md).

| | Antes · siguiendo el README publicado | Después · siguiendo `INSTALL.md` |
|---|---:|---:|
| **Pasos manuales no documentados** | **3** | **0** |
| **Fallos** | **7** | **0** |
| ¿Queda una aplicación navegable? | **No** | **Sí, con datos en los tres portales** |
| Tiempo hasta ese resultado | 229 s | **199 s** |
| `make demo` en frío | no existía | **187 s** |

El detalle que más dice: **la columna de «antes» tardaba más y terminaba sin aplicación**.

Los siete fallos de partida, cada uno con su traza en `INSTALL_TRACE.md`: `python3.12 -m venv`
falla sin `python3.12-venv`; `pip install -e backend[dev]` no compila porque `mjml-python` arrastra
`pycairo`; `cp .env.example .env` deja **las cuatro** variables obligatorias sin definir;
`build_test_db.sh` busca un contenedor que solo existe si el clon se llama `fulkro`; la recolección
de `pytest` aborta con `6383 tests collected, 7 errors` y salida 2; el backend aborta **aunque se
arranque como el README dice**; y no hay Node.

### Partir la imagen se nota donde importa

| Commit | `make demo` en frío | Imágenes |
|---|---:|---:|
| `8972895` | 384 s | 10,58 GB |
| `39c156e` | **187 s** | **5,45 GB** |

---

## 2. Qué se ha cerrado, con su comando

| | Comando que lo demuestra | Resultado |
|---|---|---|
| Un solo comando instala | `make demo && make smoke` en contenedor limpio | **verde**, 199 s |
| El smoke detecta base vacía | vaciar catálogos y `make smoke` | **exit 2**, 7 comprobaciones en fallo |
| Dependencias declaradas | `pytest --collect-only` en venv limpio | de **exit 2 / 7 errores** a **exit 0 / 6.470** |
| `.env.example` completo | `pytest backend/tests/test_env_example_completeness.py` | 6 pasan; borrando `DATABASE_URL` **falla** |
| Rutas absolutas | `command grep -rIo "/home/usuario" --exclude-dir=.git . \| wc -l` | de **62** a **29** |
| `--force` rota las tres claves | sha256 antes/después en ficheros de juguete | AUTH **sí** rota |
| Postgres del demo sin AGE | `docker compose -f docker-compose.demo.yml config` + arranque | 4 extensiones, sin `pgaudit` |
| Imagen sin instrumental | `docker images` | **7,92 GB → 2,79 GB** (−64,8 %) |
| El CD muerto, retirado | `ls .github/workflows/` | `deploy.yml` no está |
| Los tests corren en CI | job `pytest` en cada push | `3153 passed, 23 skipped, 3294 deselected` |
| `mypy` puede fallar | job sin `continue-on-error` | verde sobre 160 ficheros |
| `safety` no se traga un crash | 4 escenarios reproducidos | parser viejo exit 0 ×4, nuevo exit 1 ×4 |
| `npm audit` con lista acotada | 6 escenarios reproducidos | crítico nuevo, caducado y roto **bloquean** |
| Imagen publicada en GHCR | workflow `Publicar imagen` | `ghcr.io/fulkrodev/fulkrosys/backend` |
| Alembic no se equivoca de base | `alembic current` sin la variable | **exit 1** con mensaje accionable |

### Cuántos tests corre el CI, y sobre cuántos

```
3153 passed, 23 skipped, 3294 deselected, 21 warnings in 82.27s
```

**3.153 de 6.470: el 48,7 %.** Antes eran **0 de 6.464**, y no por accidente: los jobs `test` y
`playwright` estaban condicionados a `workflow_dispatch`. Medido paginando el historial entero, no
la primera página: de 362 ejecuciones, **las 121 de CI son de evento `push`, cero
`workflow_dispatch`**. Nunca se habían ejecutado.

Los 3.294 apartados son los `requires_db`, que necesitan una base sembrada. El propio job publica
la proporción en su resumen, contándola en cada ejecución.

---

## 3. Los ADR escritos

- [`ADR-001`](adr/ADR-001-postgres-demo-sin-age.md) · **El Postgres del demo no compila Apache AGE.**
  Cero usos en las 268 migraciones y cero en `backend/app`; el único consumidor es un script de
  seed que ya se saltaba por defecto. Compilarlo costaba 57,1 s de los 63,95 s del build.
  Contrapartida: se pierde el grafo de conocimiento, que hoy no lee nadie, y resucitarlo exigiría
  volver a la imagen propia.

- [`ADR-002`](adr/ADR-002-imagen-backend-sin-instrumental-pentest.md) · **La imagen del backend se
  parte en dos.** 7,92 GB → 2,79 GB. Contrapartida: dos variantes que mantener, y quien quiera
  lanzar un pentest tiene que levantar el perfil `scanner`.

---

## 4. Lo que sigue abierto en la máquina de un tercero

Prefiero esta lista, cierta, a un «listo» que se rompe cuando alguien lo prueba.

1. **Dos ejecuciones remotas de código sin autenticar, sin arreglar.** Next.js 14.2.33 arrastra
   `GHSA-p293-qw3h-jr36` (servidores Windows) y `GHSA-2xp9-vwfh-vxw4` (API de imágenes con AVIF).
   Se arreglan en **Next ≥ 15.5.24**, un salto mayor que toca el App Router entero. Están acotadas
   por escrito en `.github/npm-audit-allowlist.json` **con fecha de caducidad: 31/12/2026**, y a
   partir de ahí el gate bloquea. No es un arreglo: es una deuda con fecha.

2. **No hay protección de rama.** `gh api repos/Fulkrodev/Fulkrosys/branches/main -q .protected`
   sigue devolviendo `false`, así que todos los gates anteriores se pueden saltar. Es configuración
   de GitHub y hay que hacerla a mano; los pasos exactos, con los nombres literales de los checks,
   están en [`docs/CI.md`](CI.md).

3. **896 de 1.056 ficheros siguen sin pasar por `mypy`.** El gate cubre 160 (15,2 %). De golpe eran
   515 errores en 212 ficheros. La lista solo puede crecer.

4. **3.294 tests no corren en CI.** Son los `requires_db`. Falta sembrar la base en el runner.

5. **La evaluación de agentes cubre 1 de 13.** Hay un arnés completo y un solo conjunto de datos,
   con 10 ejemplos. Y el runner por línea de comandos del arnés **no evalúa nada**: sin clave
   devolvía tasa de acierto 1.0 con cero entradas evaluadas y salida 0, un verde vacío perfecto. El
   gate nuevo exige un mínimo de entradas evaluadas, pero los datos para evaluar siguen sin existir.

6. **El modelo de embeddings no viene precargado.** La primera consulta del copiloto al corpus lo
   descarga de HuggingFace (unos 2 GB). Sin red, esa función falla; el resto de la aplicación va.

7. **La imagen no es reproducible bit a bit.** `pip install uv` no fija versión, así que
   reconstruir sin cambio funcional produce capas distintas.

8. **`httpx` choca de nombre.** En la imagen de la aplicación `command -v httpx` responde que sí,
   pero es el script de Python del paquete PyPI, no el escáner de Go. No rompe nada hoy, pero es un
   falso positivo esperando a quien audite por nombre.

9. **Quedan 29 apariciones de la ruta personal del autor, ninguna ejecutable**, medidas
   **excluyendo este documento**:

   ```bash
   $ command grep -rIo "/home/usuario" --exclude-dir=.git --exclude=INFORME_C0_C1.md . | wc -l
   29
   ```

   Se reparten así: 19 en el informe fechado `docs/audit/AUDITORIA_2026-09.md`, cuyas citas
   textuales falsificaría reescribir; 4 en el README, que documenta el problema; y 1 en un tracker
   histórico bajo `out/`.

   La exclusión no es una trampa: es el único modo de que el número sea estable. Al redactar este
   punto la cifra saltó de 29 a 31 y luego a 30, **porque el documento que reporta el número lo
   modifica cada vez que lo nombra**. Es exactamente el fallo que autoinvalidó la cifra del README
   dentro del commit que la publicó. La lección, que vale para cualquier conteo publicado en prosa
   en este repositorio: o lleva su exclusión escrita, o lo genera un test, o tiene una vida media
   de un commit.

10. **`AgentBase._call_llm` sigue fabricando respuestas en silencio.** Hallazgo previo, sigue
    abierto: cuando falta la clave o falla la llamada, devuelve texto inventado y lo asienta en el
    libro mayor con `status="success"`. Fuera del alcance de esta campaña, pero es el más grave que
    queda vivo.

11. **El bloque C2 (nube) no se ha tocado**, por instrucción expresa.

---

## 5. Errores propios cometidos y corregidos

Se listan porque cada uno produjo una cifra falsa, y porque la lección se repitió:
**cuando el arnés de verificación falla, la primera pregunta es si falló el arnés o el sujeto.**
Las seis veces fue el arnés.

1. **Overlay anidado.** La compilación de AGE fallaba con `failed to convert whiteout file`. Era el
   arnés, no el repositorio. Darlo por bueno habría acusado al proyecto de algo que no hace.
2. **`| tail` enmascarando códigos de salida.** Dos pasos apuntados como correctos cuando el
   binario ni existía. Volvió a pasar una segunda vez con `alembic`.
3. **Clonar en un directorio elegido a mano**, lo que **ocultaba** el bug del nombre de contenedor.
4. **Un `grep` que no encontraba nada** y me hizo dar por bueno un test que no probaba nada.
5. **Una contraseña inventada** en vez de la que genera el demo, atribuida al sujeto.
6. **Cambiar la población medida** al reescribir un test: pasé de contar operaciones a contar
   caminos, con el umbral puesto en operaciones. Son 8 caminos y 10 operaciones.

Y un falso positivo que estuvo a punto de entrar en este informe: dije que la suite no se podía
ejecutar «porque falta `dotenv`». `python-dotenv>=1.0.1` está declarada en
`backend/pyproject.toml:27`. Lo que faltaba era mi entorno, no la dependencia.

---

## 6. Cifras del README que no eran ciertas, y su corrección

| Afirmación | Realidad medida |
|---|---|
| «34 rutas absolutas en 26 ficheros» | Se autoinvalidó **dentro del commit que la publicó** |
| «Ocho de cada diez endpoints exigen ser el administrador» | Conclusión **correcta**, comando **no**: son 845 rutas, no 249 |
| «32 identificadores, 13 activos» | **31 y 12**, parseando con AST en vez de contar literales |
| «13 activos frente a 12 clases: cuadra» | **12 activos y 13 clases**: dos errores que se compensaban |
| «1.201 rutas» con su comando | Valor correcto, **comando caducado**: hoy devuelve 0 |
| «La evaluación cubre uno de doce» | **Uno de trece** |

El caso del reparto de autorización merece detalle, porque la corrección ingenua también habría
sido falsa. El `grep` contaba ocurrencias de un literal; 132 de las 249 están a nivel de
`APIRouter` y cada una protege **todos** los endpoints que cuelgan de ese router. Es decir, el
`grep` **se quedaba corto**. Medido contra la aplicación en ejecución con
`scripts/medir_autorizacion.py`, recorriendo el árbol de dependencias de forma recursiva: **845**
rutas con `require_owner`. Y de las 1.106 con puerta de población, **849 exigen ser el
administrador: el 76,8 %**. La frase se sostiene; el comando que la acompañaba, no.
