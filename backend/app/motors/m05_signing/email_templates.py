"""Email templates step-up OTP · M05 signing · SAN-E v3.MB-5.2.bis.

Pattern alineado con m12_magic_link/emails/renderer.py: Jinja2 inline
strings · render returns ``(subject, html, text)`` tuple · NO file
templates externos.

Caller pattern:

    subject, html, text = render_step_up_otp_email(
        otp_code="123456",
        signable_type="dda",
        user_name="Marcos",
        expires_in_minutes=5,
        request_ip="192.168.1.1",
    )
    await email_sender.send(db, to=user.email, subject=subject,
                             html_body=html, text_body=text,
                             template_used="m05_signing/step_up_otp")
"""
from __future__ import annotations

from datetime import UTC, datetime

import jinja2

from backend.app.motors.m05_signing.signable_types import SIGNABLE_TYPE_LABELS


SIGNABLE_LABELS_ES: dict[str, str] = {
    "dda": "Declaración de Aplicabilidad ENS · 73 medidas",
    "magerit_validation": "Validación inventario activos MAGERIT",
    "pentest_authorization": "Autorización ventana pentesting",
    "conformidad_ens": "Conformidad ENS final · firma distintivo",
    "acta_comite": "Acta Comité de Seguridad",
    "retainer_offer": "Oferta retainer post-certificación",
    "policy_approval": "Aprobación política / procedimiento",
    "incident_close": "Cierre incidente seguridad",
    "dpc_anual": "DPC Anual · revisión obligatoria ENS",
    "renewal": "Renovación bianual ENS",
    "acta_nombramiento_roles": "Acta de Nombramiento de Roles ENS",
    "plan_adecuacion": "Plan de Adecuación al ENS",
    "documento_alcance": "Documento de Alcance del SGSI",
    "document_generic": "Documento",
}


def get_signable_label(signable_type: str) -> str:
    """Etiqueta humana del tipo firmable para el email de step-up OTP.

    Las variantes email-friendly de ``SIGNABLE_LABELS_ES`` (más cortas) ganan
    donde existen; para los 4 tipos no cubiertos aquí (declaracion_conformidad_basica,
    retainer_quarterly_signoff, acta_decision_direccion, contrato_comercial) se
    recurre al mapa canónico ``SIGNABLE_TYPE_LABELS`` en vez de mostrar el genérico
    "Documento" (audit-roundup-W3 §4.1/341). Solo cae al genérico si el tipo no
    existe en ningún mapa.
    """
    return (
        SIGNABLE_LABELS_ES.get(signable_type)
        or SIGNABLE_TYPE_LABELS.get(signable_type, "Documento")
    )


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Código de seguridad FULKRO</title>
</head>
<body style="font-family: -apple-system, system-ui, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1a1a1a;">
  <h2 style="color: #2D3253;">Código de seguridad</h2>
  <p>Hola {{ user_name }},</p>
  <p>Para firmar el documento <strong>{{ signable_label }}</strong> en FULKRO, introduce este código:</p>

  <div style="font-size: 36px; font-weight: bold; letter-spacing: 12px; padding: 24px; background: #f5f5f5; text-align: center; margin: 24px 0; border-radius: 8px; font-family: monospace;">
    {{ otp_code }}
  </div>

  <p><strong>El código expira en {{ expires_in_minutes }} minutos.</strong></p>

  <p>Si no fuiste tú quien solicitó esta firma:</p>
  <ul>
    <li>Ignora este email</li>
    <li>NO compartas el código con nadie</li>
    <li>Avisa a Marcos: marcos@fulkro.com</li>
  </ul>

  <p style="color: #888; font-size: 12px; margin-top: 24px;">
    Este código es válido para una sola firma · NO se repite · es trazable en el audit log del proyecto.
  </p>

  <hr style="border: none; border-top: 1px solid #e5e5e5; margin: 24px 0;">

  <p style="color: #888; font-size: 11px;">
    FULKRO · Cumplimiento ENS · Madrid<br>
    Documento firmable: {{ signable_type }}<br>
    Solicitud: {{ requested_at }}<br>
    {% if request_ip %}IP solicitud: {{ request_ip }}{% endif %}
  </p>
</body>
</html>
"""


_TEXT_TEMPLATE = """\
Código de seguridad FULKRO

Hola {user_name},

Para firmar el documento "{signable_label}" en FULKRO, introduce este código:

    {otp_code}

El código expira en {expires_in_minutes} minutos.

Si no fuiste tú quien solicitó esta firma:
- Ignora este email
- NO compartas el código con nadie
- Avisa a Marcos: marcos@fulkro.com

Este código es válido para una sola firma · NO se repite · es trazable
en el audit log del proyecto.

---
FULKRO · Cumplimiento ENS · Madrid
Documento firmable: {signable_type}
Solicitud: {requested_at}
"""


def render_step_up_otp_email(
    *,
    otp_code: str,
    signable_type: str,
    user_name: str,
    expires_in_minutes: int = 5,
    request_ip: str | None = None,
) -> tuple[str, str, str]:
    """Render step-up OTP email · returns ``(subject, html, text)``.

    Args:
        otp_code: 6-digit plain OTP code.
        signable_type: M05 signable_type (mapeado a label ES).
        user_name: nombre destinatario para personalización.
        expires_in_minutes: TTL del code · default 5.
        request_ip: IP solicitud (audit · opcional).
    """
    subject = "Tu codigo de seguridad para firmar - FULKRO"
    label = get_signable_label(signable_type)
    requested_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    env = jinja2.Environment(
        autoescape=True, undefined=jinja2.StrictUndefined,
    )
    html = env.from_string(_HTML_TEMPLATE).render(
        user_name=user_name,
        signable_label=label,
        signable_type=signable_type,
        otp_code=otp_code,
        expires_in_minutes=expires_in_minutes,
        requested_at=requested_at,
        request_ip=request_ip or "",
    )

    text = _TEXT_TEMPLATE.format(
        user_name=user_name,
        signable_label=label,
        signable_type=signable_type,
        otp_code=otp_code,
        expires_in_minutes=expires_in_minutes,
        requested_at=requested_at,
    )
    return subject, html, text


def mask_email(email: str) -> str:
    """Mask email para audit log + response · 'j***@example.com'."""
    parts = email.split("@")
    if len(parts) != 2 or not parts[0]:
        return "***"
    local = parts[0]
    return f"{local[0]}***@{parts[1]}"
