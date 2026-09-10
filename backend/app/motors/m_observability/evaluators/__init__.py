"""Per-agent golden dataset evaluators · sub-atom 1.E.1.B.3.D Path C-light.

Cada evaluator agent-specific se registra automáticamente al importar el
módulo (`register_evaluator` side-effect). Para activar evaluators desde
runtime · importar este package (e.g. desde tests o eval_runner CLI con
flag explicit).

BLOQUE D · D2 (2026-09-10): además del evaluador, cada módulo registra su
constructor de salida sintética (`register_synthetic_output`), que es lo que
el gate del arnés usa para comprobar la auto-consistencia entre dataset y
evaluador sin tener que conocer el esquema de ningún agente. Ver el bloque
"Registro de salidas sintéticas" en `eval_runner.py`.

Restricción que hay que respetar al añadir un evaluador nuevo: el job
`evals-arnes` de CI importa este paquete con **sólo pydantic y pyyaml**
instalados, así que ningún evaluador puede importar `backend.app.agents.*`
ni nada que arrastre SQLAlchemy. Los catálogos que un evaluador necesite se
copian en su módulo y se protegen contra deriva desde
`backend/tests/motors/m_observability/test_evaluadores_agentes.py`.
"""
from backend.app.motors.m_observability.evaluators import (  # noqa: F401
    agent_06_contratos_evaluator,
    agent_18_reunion_evaluator,
    agent_27_clasificador_evaluator,
    deliverable_text_auditor_evaluator,
)
