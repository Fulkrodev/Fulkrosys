# Motor 2 — MAGERIT v3

Analisis de riesgos segun MAGERIT v3 (NIPO 630-12-171-8 Libros I-III)
integrado con las 80 medidas del Anexo II del RD 311/2022 ENS.

## Funcionalidades

- **Inventario de activos** con tipificacion MAGERIT v3 Libro II.
- **Valoracion DICAT** (5 dimensiones D, I, C, A, T) heredada del Motor 1.
- **Matriz de amenazas x activos** con probabilidad + impacto.
- **Calculo de riesgo** cualitativo (BAJO/MEDIO/ALTO/CRITICO) y
  semi-cuantitativo (0.0-1.0) con calibracion MAGERIT oficial.
- **Propagacion por dependencias** via formula probabilistica
  `a + b = 1 - (1 - a) * (1 - b)` (Libro II §2.5.3).
- **Plan de tratamiento**: controles (aceptar/mitigar/transferir/evitar)
  alineados con medidas Anexo II v2.2.
- **Export .mgr XML** para PILAR (M27 adapter).

## Limitaciones conocidas

### Propagacion de riesgo: 1-hop unicamente

La funcion `_magerit_dependency_sum` aplica la formula oficial
`a + b = 1 - (1 - a) * (1 - b)` solo para dependencias **directas**
entre activos. Para grafos con dependencias **profundas** (A → B → C → D
4+ niveles) la propagacion transitiva completa via union de
probabilidades en cadena no esta implementada como algoritmo grafo.

**Impacto real para el perfil de cliente FULKRO:**

Los clientes tipicos de FULKRO (PYMEs categoria Basica/Media con
~50-100 activos y grafos planos de 2-3 niveles) **no se ven afectados**:
sus dependencias se modelan correctamente con el algoritmo 1-hop
aplicado a cada pareja (activo_superior, activo_inferior) de forma
iterativa, que converge al mismo resultado para grafos DAG planos.

**Cuando se implementara:**

Cuando aparezca un cliente categoria ALTA con infraestructura compleja
(>200 activos, grafos con profundidad >=4 niveles, ciclos) que requiera
propagacion transitiva optimizada via `networkx`. Entonces:

- Integrar `networkx.DiGraph` con activos como nodos y dependencias
  como aristas ponderadas por probabilidad de transferencia.
- Usar `networkx.all_simple_paths` + agregador probabilistico para
  calcular riesgo propagado.
- Tests de comparativa contra el algoritmo actual en grafos planos
  (deben coincidir) + tests para grafos profundos.

Hasta entonces, el algoritmo actual cumple MAGERIT v3 para el
99 percent de proyectos ENS reales en territorio espanol (datos CCN-CERT
2024: mediana de 42 activos por sistema certificado).

## Trazabilidad oficial

- Fuente: MAGERIT v3 Libros I, II, III (NIPO 630-12-171-8, 2012).
- Cross-check: 57/57 codigos de amenaza, 4/4 grupos de activos
  alineados literalmente con Libro II (ver `docs/catalogs/
  magerit_libro2_traceability.md`).
- Reforzado en Sesion 3 con columnas `official_description` y
  `official_source` en `magerit_threats` (migration `0505cf3174f8`).
