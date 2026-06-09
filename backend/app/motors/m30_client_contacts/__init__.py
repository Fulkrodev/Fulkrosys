"""Motor 30 — Client Contacts.

Catálogo de contactos por cliente (no usuarios del portal). Permite a
Marcos mantener una agenda profesional con cargos, roles, signatarios,
preferencias de comunicación y notas internas — más timeline de
interacciones cross-motor (A18 reuniones, M29 mensajes, M12 magic
links, M14 contratos).

Plan v4.2 FASE 5.5 (sub-fase 5.5.A → 5.5.G). Decisiones audit pre-impl
2026-04-29 (TODO-FASE-5.5-AUDIT):
  - H1 M12 Magic Links FK ``sent_to_contact_id`` diferido →
    ``TODO-M30-M12-INTEGRATION-001`` [BAJA].
  - H2 plan v4.2 inline DDL suficiente (sin ADR-012 doc accesible).
  - R4 RLS ``USING (true)`` + RBAC ``require_owner`` (M30 admin-only).
"""
from backend.app.motors.m30_client_contacts.models import (  # noqa: F401
    ClientContact,
    ClientContactInteraction,
)
