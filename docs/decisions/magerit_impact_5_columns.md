# ADR: Tabla de impacto extendida de 3 a 5 columnas de degradacion

## Status
Accepted — 2026-04-13

## Context
MAGERIT v3 Libro III sec 2.1 p.6 define la tabla de impacto cualitativa con
3 columnas de degradacion: 1%, 10%, 100%. Esto corresponde a una escala de
3 niveles de degradacion.

Sin embargo, el modelo FULKRO usa una escala de 5 niveles en todas las
dimensiones (MB, B, M, A, MA) para consistencia interna. La tabla de riesgo
5x5 (Libro III p.7) ya usa 5 niveles para probabilidad e impacto. Tener la
tabla de impacto con solo 3 columnas de degradacion crea una asimetria:
la degradacion tiene menos granularidad que las demas dimensiones.

## Decision
Extender la tabla de impacto de 3 columnas (1%, 10%, 100%) a 5 columnas
(MB, B, M, A, MA) por interpolacion. Las 3 columnas oficiales se mantienen
como anclas:

| | MB (nuevo) | B (nuevo) | M (~10%) | A (nuevo) | MA (~100%) |
|---|---|---|---|---|---|
| **MA** | M | A | A | MA | MA |
| **A** | B | M | M | A | A |
| **M** | MB | B | B | M | M |
| **B** | MB | MB | MB | B | B |
| **MB** | MB | MB | MB | MB | MB |

Tabla oficial de 3 columnas del Libro III p.6 (anclas en negrita):

| | **1% (~MB)** | **10% (~M)** | **100% (~MA)** |
|---|---|---|---|
| **MA** | M | A | MA |
| **A** | B | M | A |
| **M** | MB | B | M |
| **B** | MB | MB | B |
| **MB** | MB | MB | MB |

Las columnas B y A son interpolaciones consistentes: cada celda queda
entre las anclas oficiales sin excederlas.

## Consequences

**Positivas:**
- Consistencia con escala 5-niveles en todo el modelo MAGERIT
- Permite degradaciones intermedias (6-20% = B, 51-90% = A) que la tabla
  oficial de 3 columnas no distingue
- Tests comparativos con caso Jaymon validan coherencia

**Negativas:**
- 10 celdas interpoladas que no estan en la tabla oficial
  (documentadas explicitamente en docstring de _lookup_impact_qualitative)
- Exportacion a PILAR debe usar solo las 3 columnas oficiales

**Convencion FULKRO:** marcada explicitamente en service.py con comentario
"Extended to 5 degradation levels for consistency with the 5-level scale."

## Alternatives considered

1. Mantener 3 columnas y mapear MB/B/M/A/MA a solo 3 buckets: rechazada
   por perdida de granularidad en escenarios reales con degradaciones del
   30-40% (todas caerian en el bucket "10%").

2. Usar interpolacion lineal numerica: rechazada por perder la propiedad
   de lookup table pura (que es lo que MAGERIT prescribe).

## References
- MAGERIT v3 Libro III, sec 2.1 p.6 (tabla de impacto oficial)
- Implementacion: backend/app/motors/m02_magerit/service.py
  funcion _lookup_impact_qualitative()
- Tests: test_lookup_impact_qualitative() en test_m02_magerit.py
