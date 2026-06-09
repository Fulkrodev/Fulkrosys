"""Motor 29 — Client Messaging.

Mensajería bidireccional cliente ↔ Marcos con captura adjuntos, email
forward, notifications. Integrado con M30 Contacts (composer admin
permite seleccionar contacto destinatario).

Arquitectura (plan v4.2 sección 6):
  - 2 tablas: ``client_messages`` + ``client_message_attachments``
  - RLS: ``client_isolation`` (cliente pool ve solo sus mensajes;
    admin bypassa via ``SET LOCAL ROLE fulkro_app_bypassrls``).
  - Email forward: EmailSender consolidado + override ``contact.email``
    si ``to_contact_id`` presente.
  - Attachments: MinIO bucket ``fulkro-client-messages`` + signed URLs
    TTL 7d + MIME whitelist + 10 MB size limit.
  - Celery tasks: cleanup attachments TTL expirado + digest diario.
  - Auto-log interaction M30 al enviar/responder mensaje a contacto.

Sub-fase 6.A backend (FASE 6 SESIÓN A).

Ver:
  - ADR-005 mensajería cliente
  - FR6 plan v4.2
  - Plan v4.2 sección 6 (línea 4388-4565)
"""
