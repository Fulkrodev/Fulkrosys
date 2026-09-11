# ADR-061 · El eje de dimensiones: una dimensión no afectada no se adscribe a ningún nivel

**Fecha**: 2026-09-11 · **Estado**: aceptado · **Ámbito**: motor de categorización (m01) y DdA (m03)

**Este ADR se escribe DESPUÉS del código, y cuenta lo que se hizo.** No sustituye
al arreglo: lo documenta. El arreglo está en el commit `c300514` (N1) y se apoya
en la verificación del `92e8f2d` (N0).

**Origen de los números**: `backend/tests/fixtures/anexo2_boe_verificado.json`,
extraído del PDF consolidado del BOE por
[`backend/scripts/extraer_anexo2_boe.py`](../../backend/scripts/extraer_anexo2_boe.py).
sha256 del PDF: `07a74608dce3a146890f444c73ef8f2ee04f49c101114e2e2642941e53a92211`.

---

## El problema, con su línea

`m01_categorization/service.py` arrancaba las cinco dimensiones de seguridad en
`BAJO`:

```python
max_per_dim = {"D": "BAJO", "I": "BAJO", "C": "BAJO", "A": "BAJO", "T": "BAJO"}
```

Y `grep -i no_afectada backend/app` devolvía **cero**. El concepto no existía.

La consecuencia no es cosmética. Una dimensión que ningún tipo de información y
ningún servicio valoraba terminaba en BAJO, y BAJO **arrastra medidas**. El
Anexo I, punto 3, dice lo contrario, literalmente:

> «Cada dimensión de seguridad afectada se adscribirá a uno de los siguientes
> niveles de seguridad: BAJO, MEDIO o ALTO. **Si una dimensión de seguridad no
> se ve afectada, no se adscribirá a ningún nivel.**»

## Por qué no se vio antes

Porque el catálogo del Anexo II que el sistema usaba como fuente única **no
guardaba el eje**. Guardaba, por cada medida, si aplica en BÁSICA / MEDIA / ALTA,
y eso es correcto —N0 lo contrastó contra el PDF del BOE y el diferencial salió
vacío: 73 de 73 códigos, 0 discrepancias de aplicabilidad—. Lo que no guardaba
es la **tercera columna** de la tabla: si la medida se exige por la *categoría*
del sistema o por el *nivel de una o varias dimensiones*.

Sin esa columna no se puede distinguir «esta medida entra porque el sistema es
MEDIA» de «esta medida entra porque la trazabilidad está en BAJO». Y sin esa
distinción, marcar una dimensión como no afectada no cambia nada, porque nadie
sabe qué medidas colgaban de ella.

El BOE sí la trae: **45 medidas por categoría y 28 por dimensión**.

## Qué se decidió

**1. `NO_AFECTADA` es un estado del enumerado, con `numeric = 0`.** No es un
nivel: es la ausencia de adscripción. Vale 0 para que la regla del máximo del
Anexo I la ignore sola, sin condicionales repartidos.

**2. Es el valor de partida, no `BAJO`.** Y la categorización obliga a decidir
las cinco explícitamente: `valida_niveles` no tiene valor por defecto, porque el
valor por defecto *era* el defecto. Si faltan dimensiones, falla.

**3. El eje vive en el catálogo, generado desde el fixture del BOE.**
`EJE_Y_DIMENSIONES` en `anexo2_rd311_2022.py`, con las iniciales en el orden del
BOE (`CITA`, `IA`, `TA`) por fidelidad, comparadas como conjunto porque el orden
no significa nada. No se escribe a mano: un test lo vuelve a contrastar contra el
fixture, así que cualquier edición manual que se desvíe falla.

**4. La aplicabilidad es una función pura.** `m01_categorization/aplicabilidad.py`:
entra categoría y nivel de cada dimensión, sale el conjunto de medidas aplicables
y, por cada una, el motivo. Sin base de datos y sin efectos, para que se pueda
probar con un test dorado y razonar sobre ella sin levantar nada.

**5. La DdA lee el catálogo verificado, no la columna vieja.**

## La decisión que se apartó del enunciado, y por qué

El encargo decía: *«Recablea la DdA para que lea `ens_measure_dimensiones` (272
filas, correcta) en vez de `dimensiones_aplicables`»*. Se recableó, pero **no a
esa tabla**, y conviene que conste el motivo.

`ens_measure_dimensiones` resuelve «Todas» como las cinco dimensiones. Eso hace
que a `org.1` —que el Anexo II exige **por categoría**— le atribuya
D+I+C+A+T. Como dato es cierto; en la DdA es engañoso: se lee como «exigida por
cinco dimensiones» algo que la norma exige por la categoría del sistema. El
catálogo del Anexo II sí distingue las dos cosas, y además está contrastado
contra el PDF.

De paso, N0 dejó probado que esa tabla **es correcta**: sus 272 filas son
exactamente `45 × 5 + 47` (45 medidas por categoría × 5 dimensiones, más los 47
pares medida-dimensión de las 28 indexadas por dimensión). Se verificó contra la
norma sin levantar la base de datos.

La columna vieja, `ens_measures.dimensiones_aplicables`, se quedó **sin un solo
lector** del atributo ORM, y hay un test que recorre `app/` y `scripts/` y falla
si alguien vuelve.

## Lo que esto cambia, medido

```
A · BÁSICA · T=BAJO         -> 52 medidas
B · BÁSICA · T=NO_AFECTADA  -> 51 medidas

diferencia:
  - op.exp.8 · Registro de la actividad · exigida por el nivel BAJO de trazabilidad [T]
```

Una sola medida, y está bien que sea una sola: `op.acc.1/2/4/5/6` siguen dentro
con la trazabilidad no afectada porque les basta **una** dimensión afectada, y la
autenticidad sigue en BAJO. Que el número no se desplome es parte de la
comprobación.

Contraste independiente del test dorado: ALTA con todo en ALTO da 73 medidas;
quitando disponibilidad da 63, y las 10 que salen son exactamente las 10 que el
Anexo II indexa **sólo** por D.

## Lo que NO se ha hecho, y por tanto no se afirma

- **No se ha migrado ninguna categorización existente.** El cambio afecta a
  cálculos nuevos. Una categorización guardada antes del cambio conserva sus
  cinco dimensiones en BAJO, y nadie la ha revisado. Si se quiere corregir el
  histórico, es otro trabajo y hay que decidir si se re-categoriza o se anota.
- **No se ha borrado la columna `dimensiones_aplicables`.** Se ha quedado sin
  lectores, que es lo que se pedía y lo que un test congela, pero sigue en el
  esquema. Borrarla es una migración con su propio riesgo.
- **No se ha tocado el eje de los refuerzos.** `EJE_Y_DIMENSIONES` describe la
  medida base. Si un refuerzo concreto declarase dimensiones distintas de las de
  su medida (el seeder menciona `mp.info.3 R1` como caso raro), este modelo no lo
  captura. No se ha medido cuántos casos hay.

## Referencias

- RD 311/2022, Anexo I punto 3 (adscripción a niveles) y punto 1 (re-evaluación anual)
- RD 311/2022, Anexo II puntos 4 y 5 (tabla de medidas y convenciones)
- [ADR-060 · El número de workers no lo limita la CPU](ADR-060-el-modelo-en-el-proceso-limita-los-workers.md) — mismo criterio: la cifra del título, medida
- `backend/tests/fixtures/aplicabilidad_oro.json` — test dorado congelado, 6 casos
