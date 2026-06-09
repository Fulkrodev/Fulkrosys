# FULKRO Self-Compliance · Norma Plugins

Cada normativa regulatoria que verifica FULKRO sobre sí misma vive aquí
como un plugin independiente. Esta carpeta implementa el patrón
Open/Closed Principle:

> **Para agregar una norma nueva: crea un fichero. Nunca modifiques el
> motor.** El motor descubre el plugin al arrancar y lo registra
> automáticamente.

## Estructura

```
normas/
├── README.md          (este documento)
├── __init__.py        (auto-discovery · NO editar)
├── base.py            (NormaModule abstract base · NO editar)
├── registry.py        (singleton · NO editar)
├── rgpd_ue_2016_679.py
├── lopdgdd_3_2018.py
├── lssi_ce_34_2002.py
├── aepd_cookies_2020.py
├── nis2_ue_2022_2555.py
├── iso_27001_2022.py
└── ens_rd_311_2022.py
```

## Cómo añadir una nueva norma (ejemplo: DORA)

### 1 · Identifica los datos regulatorios

| Campo | Ejemplo DORA |
|---|---|
| `norma_key` | `DORA_UE_2022_2554` (snake case + año) |
| `norma_name` | `DORA · Digital Operational Resilience Act` |
| `regulatory_basis_url` | `https://eur-lex.europa.eu/eli/reg/2022/2554/oj` |
| `applies_to` | `["FULKRO_PLATFORM_IF_FINANCIAL_SECTOR"]` |
| `frequency` | `weekly` / `monthly` / `quarterly` |
| `priority` | `critical` / `high` / `medium` / `low` |
| `checks_owned` | nombres exactos de `m_compliance_monitor/checks.py` |
| `check_weights` | dict `name → peso` · debe sumar `1.0` |

### 2 · Mapea checks técnicos

Mira el registro de checks en `backend/app/motors/m_compliance_monitor/
checks.py`. **Si necesitas un check que no existe**, créalo primero:

1. Añade una función `async def check_dora_xyz(db) -> CheckResult` en
   `checks.py`.
2. Registra su `CheckSpec` en `CHECK_REGISTRY` con `regulatory_basis`
   apuntando al artículo DORA correspondiente.
3. Sólo entonces inclúyelo en tu `checks_owned`.

### 3 · Crea el fichero plugin

```python
# backend/app/motors/m_compliance_monitor/normas/dora_ue_2022_2554.py
from datetime import datetime

from backend.app.motors.m_compliance_monitor.normas.base import (
    CheckOutcome,
    NormaModule,
)
from backend.app.motors.m_compliance_monitor.normas.registry import NormaRegistry


class DORAModule(NormaModule):
    norma_key = "DORA_UE_2022_2554"
    norma_name = "DORA · Digital Operational Resilience Act"
    regulatory_basis_url = "https://eur-lex.europa.eu/eli/reg/2022/2554/oj"
    applies_to = ["FULKRO_PLATFORM_IF_FINANCIAL_SECTOR"]
    frequency = "quarterly"
    priority = "high"
    checks_owned = ["check_dora_xyz", "check_dora_abc"]
    check_weights = {"check_dora_xyz": 0.6, "check_dora_abc": 0.4}

    def generate_report_md(self, outcomes, period_start, period_end):
        score = self.calculate_score(outcomes)
        # ... build markdown report ...
        return f"# Reporte DORA · score {score:.1f}%\n..."


NormaRegistry.register(DORAModule())
```

### 4 · Reinicia y comprueba

- El motor importa el fichero automáticamente (`__init__.py` recorre `*.py`).
- Celery beat añade la entrada de cron correspondiente a la frecuencia.
- El admin UI (`/admin/compliance/norma-reports`) lista la norma nueva.
- El Trust Center público (`/api/v1/legal/compliance/status`) expone el
  score en `compliance_scores_per_norma`.

### 5 · Test obligatorio

Añade tu plugin a los tests de `test_norma_plugins.py`:

```python
def test_dora_module_basic():
    dora = NormaRegistry.get("DORA_UE_2022_2554")
    assert dora is not None
    assert dora.frequency == "quarterly"
    assert sum(dora.check_weights.values()) == pytest.approx(1.0)
```

El test `test_every_plugin_weights_sum_to_one` ya valida tu plugin
automáticamente; la asercion local sólo añade granularidad.

## Versionado de normas

Si el regulador publica una versión nueva incompatible (ej. NIS2 → NIS3):

- **Cambio menor compatible**: actualiza `checks_owned`, `check_weights`
  o `regulatory_basis_url` en el plugin existente. La historia en
  `fulkro_compliance_norma_reports` se preserva (queries por
  `norma_key` + `period_end`).
- **Cambio mayor incompatible**: crea un plugin nuevo con `norma_key`
  versionada (`NIS3_UE_2025_XXXX`). El plugin viejo queda como histórico
  hasta que decidas retirarlo.

## Cross-cutting checks

Un check puede ser propiedad de varias normas a la vez. Por ejemplo
`ssl_cert_expiry` pertenece a NIS2, ISO 27001 y ENS. El registro
expone `NormaRegistry.get_by_check_owned("ssl_cert_expiry")` para
descubrir qué normas se ven afectadas si ese check falla.

## Separación FULKRO self-compliance vs cliente compliance

| Ámbito | Motor | Carpeta de plugins |
|---|---|---|
| **FULKRO sobre sí misma** | `m_compliance_monitor` | **esta** (`normas/`) |
| **Compliance de los clientes** | `m22_multinorma` (futuro) | refactor futuro con el mismo patrón |

El motor `m22_multinorma` existente todavía no usa este patrón de
plugins; cuando se refactorice (post MB-9), reusará exactamente esta
arquitectura cambiando solo el ámbito (`applies_to` apuntará a entidades
cliente concretas en lugar de `FULKRO_PLATFORM`).
