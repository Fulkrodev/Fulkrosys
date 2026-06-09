# Floor de riesgo: propiedad emergente de la tabla MAGERIT v3

## Resumen ejecutivo

FULKRO implementa fielmente la tabla de impacto cualitativa del Libro III
p.6 de MAGERIT v3. Una propiedad emergente de esta tabla es que los activos
de valor MUY ALTO (MA) tienen un **suelo de riesgo implicito**: incluso con
salvaguardas de eficacia maxima (100%), el riesgo residual nunca desciende
por debajo del nivel B.

Esto NO es un bug ni un parametro configurable: es una caracteristica de la
tabla oficial que refleja la realidad operativa de que un activo critico
nunca es "completamente seguro". Herramientas que reducen riesgo
aritmeticamente (producto lineal) pueden llegar a riesgo cero, lo cual
contradice este principio y puede inducir falsa seguridad.

## Mecanismo tecnico

La tabla de impacto del Libro III p.6 define:

    _lookup_impact_qualitative("MA", "MB") = "M"

Es decir: un activo de valor MA con degradacion reducida a MB (por
salvaguarda perfecta) SIGUE teniendo impacto M (no MB).

Combinado con la tabla de riesgo del Libro III p.7:

    _lookup_risk_matrix("M", "MB") = "B"

El riesgo minimo alcanzable es B, no MB. El floor es una propiedad
matematica de las tablas lookup, no un parametro artificial.

## Valores de floor por nivel de activo

| Valor del activo | Floor de riesgo (con salvaguarda perfecta) |
|---|---|
| MA | **B** (impacto M con degradacion MB) |
| A | **MB** (impacto B con degradacion MB) |
| M | **MB** (impacto MB con degradacion MB) |
| B | **MB** |
| MB | **MB** |

Solo los activos MA tienen un floor no-trivial (B en vez de MB).

## Validacion

Test: `test_effective_qualitative_perfect_efficacy` en Bloque E del Motor 2.

Escenario: activo valor 10 (MA), amenaza probabilidad MA, degradacion 100%,
salvaguarda eficacia 100% tipo "both".

Resultado: riesgo efectivo = **B** (no MB).

Este test fue disenado especificamente para validar el floor tras el
hallazgo durante el desarrollo del Motor 2.

## Implicacion para auditoria ENS

Cuando un auditor ENAC revisa un informe de riesgos y ve que un activo
critico (MA) tiene riesgo residual B a pesar de salvaguardas excelentes,
esto es **coherente con la experiencia del auditor**: ningun sistema es
100% seguro. Si el informe dijera MB (o "riesgo cero"), el auditor
dudaria de la metodologia.

FULKRO produce analisis que pasan auditoria sin necesidad de ajustes
manuales porque el modelo respeta esta propiedad emergente de MAGERIT.

## Diferenciacion frente a implementaciones naive

Herramientas que usan `riesgo = intrinseco * (1 - eficacia)` como producto
lineal producen riesgo cercano a 0 con eficacias altas. Esto:
- Falla en auditoria ENAC por "demasiado optimista"
- Obliga al consultor a ajustar manualmente los resultados
- No refleja la tabla oficial de MAGERIT v3

FULKRO evita estos problemas por diseno, no por parametros arbitrarios.

## Referencias
- MAGERIT v3 Libro III sec 2.1 p.6 (tabla de impacto)
- MAGERIT v3 Libro III sec 2.1 p.7 (tabla de riesgo)
- Implementacion: backend/app/motors/m02_magerit/service.py
  funciones _lookup_impact_qualitative() y _lookup_risk_matrix()
- Test: test_effective_qualitative_perfect_efficacy en test_m02_magerit.py
- Caso comparativo: progress/jaymon_comparative_analysis.md
