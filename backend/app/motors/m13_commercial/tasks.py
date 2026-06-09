"""m13_commercial Celery tasks · CRM pipeline workers.

SAN-D MB-19.6 · ADR-041.

Módulo de tareas Celery del motor comercial M13. Importado por
``backend.app.core.celery_app`` (``include=[...]``).

Ejecución:
    celery -A backend.app.core.celery_app worker -l info
    celery -A backend.app.core.celery_app beat -l info

Refs:
- backend/app/motors/m13_commercial/services/lead_service.py:LeadService
- ADR-041 (CRM workflow comercial m13 extension)
"""
from __future__ import annotations

import logging


logger = logging.getLogger(__name__)
