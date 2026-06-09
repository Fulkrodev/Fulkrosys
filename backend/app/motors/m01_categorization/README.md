# Motor 1 · Categorization Engine

Categorización de sistemas ENS según Anexo I del RD 311/2022 (BÁSICA / MEDIA / ALTA) usando la regla del máximo sobre las 5 dimensiones DICAT. Determinístico puro · NO LLM · trazabilidad oficial completa.

## Funcionalidades

- **Inventario de sistemas + servicios + tipos de información** con valoración DICAT por cada uno.
- **Cálculo de categoría sistema** vía regla del máximo: la categoría es la mayor dimensión sobre todos los activos en scope.
- **Categorías**: `BASICA` (todas dimensiones BAJO) · `MEDIA` (alguna MEDIO) · `ALTA` (alguna ALTO).
- **Acta E.012** generation cliente-facing post-firma del owner cliente.
- **Histórico de categorizaciones** versionado · `CategorizationHistoryItem` + `CategorizationVersionDetail`.
- **Arquetipos PYME** preconfigurados (`pyme_archetypes.py` + `archetype_api.py`) para acelerar inventario inicial.
- **Integración firma E.012** vía M12 magic-link (`signature_integration.py`).

## Stats empírico

| Métrica | Valor |
|---|:---:|
| LOC | 2.125 |
| Files | 7 |
| Status | production-grade |
| Tests | `backend/tests/motors/m01_categorization/` |
| API prefix | `/api/v1/categorization/*` |
| RBAC | Cat A · Marcos-only (`require_owner`) |

## Key files

- `api.py` · 12+ endpoints HTTP (sistemas · servicios · tipos info · categorización · acta · firma)
- `service.py` · `CategorizationService` + `compute_category` (algoritmo máximo)
- `schemas.py` · Pydantic in/out (≈14 schemas)
- `archetype_api.py` · endpoints arquetipos PYME
- `pyme_archetypes.py` · catálogo arquetipos preconfigurados
- `signature_integration.py` · wire-up M12 magic-link para firma E.012

## DB tables

N/A motor-specific · usa modelos core (`Project` · `System` · `Service` · `InformationType` · `Categorization`) definidos en `backend/app/models/core.py`.

## Cross-motor integration

- **Inbound**: ninguno directo (motor de entrada del flow ENS · alimenta M02 MAGERIT downstream)
- **Outbound**: M12 magic-link (firma E.012)
- **LLM agents**: ninguno (motor determinístico)

## ADRs referenced

- ADR-034 · cement categorización determinística

## Cement OPS

Motor de entrada del flow ENS pre-MAGERIT. Determinístico estricto: la regla del máximo no admite excepciones LLM. Trazabilidad oficial CCN-STIC 803 alineada literal.
