"""Motor 26 — Backup & Disaster Recovery.

Built in weeks 4-6 per §9.13. MUST be operational before
ingesting any real client data.

Components:
- service.py: Core backup/restore/DR service layer
- tasks.py: Celery tasks for scheduled backup operations
- api.py: FastAPI endpoints for the Operations dashboard
"""
from backend.app.motors.m26_backup.service import BackupService  # noqa: F401
