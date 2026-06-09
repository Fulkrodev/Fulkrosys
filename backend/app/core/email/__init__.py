"""FULKRO core email sender — Paso 7 + TODO-EMAIL-SENDER-CONSOLIDATION-001.

Transversal a M12 magic links, M23 retainer, M25 lifecycle, M27
conformity y Agente 15 vigilancia. Permite 3 backends seleccionables
por ``Settings.email_backend``:

- ``smtp`` — SMTP estandar via ``SmtpConfig`` resuelto por
  ``admin_settings.email_config.get_smtp_config(db)`` (AdminSettings
  override + Settings env fallback, sub-fase 4.A.3.b).
- ``postmark_api`` — Postmark REST API. Token vía ``Settings.postmark_api_token``.
- ``mock`` — NO envia, solo loguea en email_log. Ideal para tests y
  dev local sin credenciales.

Single source of truth: ``Settings`` env. Los ``os.environ.get(...)``
directos previos (``FULKRO_EMAIL_BACKEND``, ``FULKRO_EMAIL_FROM``,
``FULKRO_EMAIL_FROM_NAME``, ``FULKRO_POSTMARK_API_TOKEN``) fueron
eliminados en TODO-EMAIL-SENDER-CONSOLIDATION-001 (Sesión 11).

Todos los envios se registran en ``email_log`` (Paso 7 migration
f4b8e7c3a915) para auditoria + debugging + compliance.
"""
from backend.app.core.email.sender import (  # noqa: F401
    EmailResult,
    EmailSender,
    EmailSendError,
    get_email_sender,
    reset_email_sender,
)
