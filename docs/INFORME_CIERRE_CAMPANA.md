# Cierre de la campaña de corrección · bloques I → N → O → P

**Fecha**: 2026-09-12 · **Rama**: `main` · **Alcance**: 33 commits desde `2c1e40f`

Este informe cierra una campaña de corrección sobre el propio repositorio,
ordenada en cuatro bloques. La regla de cierre fue la misma en todos:

> Un punto se cierra cuando el código cambia y existe un test que falla en el
> commit padre y pasa en el nuevo, con las dos salidas pegadas. No se cierra
> explicando, ni documentando, ni marcando como limitación conocida. Si no se
> puede arreglar, queda ABIERTO con su medición.

Y una regla añadida a mitad, que resultó ser la más productiva:

> Un arreglo de cálculo normativo no está cerrado hasta que el documento que
> recibe el usuario cambia. Genera el entregable firmable para la misma
> categorización antes y después, y enseña el diferencial. Si el fichero es
> idéntico, no está arreglado.

---

## 1 · Resultado

| | antes (`2c1e40f`) | después |
|---|---:|---:|
| Tests que pasan | 6.367 | **6.510** |
| Tests que fallan | 45 | **44** |
| Fallos atribuibles al código | — | **0** |
| Incidencias bloqueantes del ciclo ENS | 11 | **0** |
| Entregables del expediente · proyecto BÁSICA | 1 de 28 | **25 de 28** |
| Documentos registrados en el expediente | 3 | **9** |

```bash
pytest backend/tests -q
# 44 failed, 6510 passed, 115 skipped, 5 errors in 821.19s (0:13:41)
```

Los 44 restantes están atribuidos uno a uno en el README, sección *Frentes
abiertos → Dependencias de entorno*: 25 por la clave de cifrado ausente, 16 por
un puerto codificado en el fichero de test, 3 sin agrupar. Los mismos ficheros
dan `22 failed · 195 passed · 5 errors` en los dos árboles.

---

## 2 · El patrón dominante: una regla normativa escrita N veces

De los hallazgos confirmados, el más repetido no fue un error de cálculo sino un
error de arquitectura con consecuencias de cálculo: **la misma regla del ENS
implementada en varios sitios**. Se arregla una copia, las otras se quedan atrás,
y el sistema se contradice según por dónde se le pregunte.

| regla | copias | cómo se manifestaba |
|---|---:|---|
| Regla del máximo (Anexo I) | 3 | un sistema sin valorar salía BÁSICA por una puerta y sin categoría por otra |
| Bienio del art. 31 | 5 | ya divergentes: 720 días en un sitio, 730 en otro |
| «¿Cuál es el análisis vigente?» | 8 | ninguna desempataba; el ganador lo elegía el planificador |
| Emisión de documento | 5 caminos | sólo uno registraba en `documents`, que es lo que lee el expediente |
| Cálculo de aplicabilidad | 1 escrita, 0 usada | la función buena alimentaba la pantalla; la generación usaba otra |
| Control de acceso a proyecto | 2 | las dos leían un atributo inexistente |

**El cierre no fue arreglar cada copia, sino dejar una sola y poner una guarda
que rompa la compilación si aparece otra**, en
`backend/tests/audit_fixes/test_operaciones_normativas_un_solo_camino.py`. Dos de
las instancias —la cuarta y la quinta del patrón— las encontró esa guarda al
correrla por primera vez, no la lectura del código.

Y donde la garantía podía bajar a la base de datos, bajó: el análisis vigente
dejó de ser el resultado de un `ORDER BY` y pasó a ser una columna con índice
único parcial y dos disparadores. Un resolutor al que llaman ocho sitios lo
arregla hoy; el noveno lo rompe mañana.

---

## 3 · Las nueve autocorrecciones

Errores míos, detectados y corregidos durante la propia campaña. Se listan porque
la tasa y la forma de los errores de quien revisa es un dato sobre la revisión.

| # | qué hice mal | cómo se detectó |
|---|---|---|
| 1 | `str.splitlines()` para partir el PDF del BOE: parte también por el salto de página `\x0c` y devolvía 56 de las 73 medidas | el recuento no cuadró con el contraste |
| 2 | Guarda anti-duplicación apuntando a `backend/backend/app`, que no existe: pasaba sobre cero ficheros | aserción anti-vacuidad añadida después |
| 3 | El mismo error de ruta, **una segunda vez**, en otra guarda | la misma aserción |
| 4 | Mis propios comentarios disparaban mis propias guardas (el texto explicativo contenía el patrón prohibido) | las guardas, tres veces |
| 5 | Dos rojos de CI por el mismo `F541`, el segundo sobre un fallo ya arreglado una vez | el CI · causa raíz: no tenía `ruff` local |
| 6 | Empujar sin pasar `make lint` justo después de construirlo | el propio `make lint` en el commit siguiente |
| 7 | Regla de parada de la tanda mal escrita: «si falla el primero, para» — y el primero tenía un fallo propio, así que tumbaba los otros 26 | el recorrido por navegador, que no avanzaba |
| 8 | Dar cifras de tests por directorios sin correr nunca la batería entera | la batería entera, que no coleccionaba |
| 9 | Dejar `tail` sobre la salida de la batería base y perder la lista de fallos que iba a comparar | el `comm` posterior, que salió absurdo |

---

## 4 · La lección: la capa de verificación tenía el error dentro, dos veces

La conclusión más útil de la campaña no es ninguno de los defectos del producto.
Es que **el aparato de comprobación falló del mismo modo que el código que
comprobaba**, y falló en silencio, que es lo que lo hace peligroso.

**Primera vez · guardas que no miran nada.** Dos de las guardas que escribí para
impedir la duplicación recorrían `backend/backend/app`, una ruta inexistente.
`rglob` sobre un directorio que no existe devuelve una lista vacía; el bucle no
itera; el `assert not culpables` se cumple sobre cero elementos. Verde. La guarda
publicaba una garantía que no estaba comprobando. El remedio fue añadir a cada
barrido una aserción de que **encuentra algo que medir**:

```python
ficheros = list((RAIZ / "backend" / "app").rglob("*.py"))
assert len(ficheros) > 500, (
    f"solo {len(ficheros)} ficheros barridos: la ruta esta mal y este test "
    "no esta comprobando nada"
)
```

**Segunda vez · la batería que no coleccionaba.** Un módulo importaba una
constante retirada. Un `ImportError` en la colección aborta `pytest backend/tests`
**entero**, sin ejecutar un solo test, y lo comunica con dos líneas fáciles de
pasar por alto:

```
ImportError: cannot import name 'CERTIFICATION_VALIDITY_DAYS'
Interrupted: 1 error during collection
3 warnings, 1 error in 6.46s
```

Estuvo así desde el bloque O1. No se vio porque la suite se venía corriendo por
directorios, y ninguno de esos recorridos incluye el módulo roto en un árbol que
aborte por él. El CI tampoco: su paso de conteo usa `--collect-only`, pero con
`continue-on-error` y `|| true`, de modo que se traga el error y reporta que «no
se pudo contar». El remedio es un paso que **tumba el job**, antes de ejecutar
nada, en `.github/workflows/ci.yml` → *La suite entera colecciona*.

**Y una tercera manifestación, en los tests de otros.** De los 5 fallos que
resultaron atribuibles a esta campaña, **dos eran tests que aseveraban el
defecto**:

- `test_pda_context_with_real_project` decía literalmente
  `# Categorización no creada → default BASICA`, fijando como contrato que un
  entregable firmable inventara la categoría.
- `test_e120_references_crypto_measures` exigía `mp.info.9`, un código que **no
  existe** en el Anexo II — comprobado contra las 73 medidas extraídas del PDF
  del BOE.

Un test verde sobre una regla equivocada es peor que la ausencia de test: apaga
la pregunta. La misma familia que `test_dimensions.py`, cuya cabecera anunciaba
«HTTP endpoints (GET reader · PATCH admin)» y no hacía una sola llamada HTTP —por
ese hueco pasaron meses de un 403 en producción—, y que llevó a un arnés que
marca los tests cuya cabecera promete una capa que no tocan.

**El patrón, dicho de una vez:** un mecanismo de verificación que puede pasar sin
haber medido nada es indistinguible de uno que mide y aprueba. Las tres formas
encontradas aquí —el barrido sobre cero ficheros, la suite que no colecciona, el
test que asevera el defecto— comparten esa propiedad. Por eso los remedios no son
arreglos puntuales sino aserciones sobre el propio acto de medir: *cuántos
ficheros barriste*, *cuántos tests coleccionaste*, *qué capa dices tocar*.

---

## 5 · Artefactos

| documento | qué contiene |
|---|---|
| [`README.md`](../README.md) | arquitectura, guía de los cuatro portales, métricas, frentes abiertos |
| [`docs/EVAL_RECUPERACION.md`](EVAL_RECUPERACION.md) | 49 consultas, intervalos por bootstrap, por qué se quitó la fusión |
| [`docs/PRUEBA_DE_CARGA.md`](PRUEBA_DE_CARGA.md) | rampa 1→80, dónde rompe y por qué |
| [`docs/RECORRIDO_COMPLETO.md`](RECORRIDO_COMPLETO.md) | las 167 páginas por navegador con identificadores reales |
| [`docs/adr/`](adr/) | decisiones, incluida ADR-061 reescrita para contar lo que se hizo |

Las guardas que sostienen lo corregido:

```bash
pytest backend/tests/audit_fixes/test_operaciones_normativas_un_solo_camino.py
pytest backend/tests/auth/test_getattr_no_lee_fantasmas.py
pytest backend/tests/scripts/test_tests_no_mienten_sobre_su_capa.py
pytest backend/tests/motors/m02_magerit/test_analisis_vigente_una_sola_fuente.py
pytest backend/tests/motors/m27_conformity/test_bienio_una_sola_fuente.py
```
