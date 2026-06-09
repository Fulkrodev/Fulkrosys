"""Batch B diagnóstico previo · plantilla de email branded del magic-link.

SOLO plantilla + URL. NO hay envío automático (no hay SMTP en dev y el envío
real está bloqueado por el deber de información LSSI · Marcos envía a mano).

Marca Fulkro existente (NO se inventa): violeta #6C63FF (token --fulkro-primary-500)
+ logo light hospedado + firma canónica de ``backend.app.fulkro_identity``.

Copy en frío de captación: invitación a un diagnóstico
previo sin compromiso · NUNCA menciona precio · NUNCA revela categoría ENS.
"""
from __future__ import annotations

from backend.app.fulkro_identity import (
    FULKRO_EMAIL_SIGNATURE_HTML,
    FULKRO_EMAIL_SIGNATURE_TEXT,
    FULKRO_FOOTER_TEXT,
    FULKRO_WEB_URL,
)

# Violeta de marca UI (globals.css --fulkro-primary-500). NO el naranja del
# distintivo de conformidad (ese es Pantone 021C, otro contexto).
FULKRO_VIOLET = "#6C63FF"
_LOGO_URL = f"{FULKRO_WEB_URL}/brand/fulkro-logo-light.svg"

PRECLIENTE_EMAIL_SUBJECT = "Un diagnóstico rápido para ver si el ENS os aplica"


def build_precliente_invitation_email(
    lead_name: str | None,
    magic_link_url: str,
) -> dict:
    """Construye el email branded de invitación al diagnóstico previo.

    Devuelve {subject, html, text}. El llamador (endpoint admin) lo entrega a
    Marcos junto al magic_link_url para que lo envíe manualmente.
    """
    saludo = f"Hola {lead_name}," if lead_name else "Hola,"

    html = f"""\
<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F5F4FF;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1c1c28;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F5F4FF;padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;">
        <tr><td style="background:{FULKRO_VIOLET};padding:20px 28px;">
          <img src="{_LOGO_URL}" alt="FULKRO" height="28" style="height:28px;display:block;">
        </td></tr>
        <tr><td style="padding:28px;">
          <p style="margin:0 0 16px;font-size:16px;">{saludo}</p>
          <p style="margin:0 0 16px;font-size:15px;line-height:1.5;">
            Soy Marcos, de Fulkro. Trabajamos con empresas que se relacionan con la
            Administración pública y a veces se encuentran con el Esquema Nacional de
            Seguridad (ENS) sin tenerlo claro del todo.
          </p>
          <p style="margin:0 0 16px;font-size:15px;line-height:1.5;">
            He preparado un cuestionario breve, sin tecnicismos y sin compromiso, para
            entender vuestra situación y deciros con criterio si el ENS os aplica y por
            dónde empezaríais. Se responde en unos minutos.
          </p>
          <p style="margin:24px 0;text-align:center;">
            <a href="{magic_link_url}" style="background:{FULKRO_VIOLET};color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;padding:13px 28px;border-radius:8px;display:inline-block;">
              Responder el cuestionario
            </a>
          </p>
          <p style="margin:0 0 8px;font-size:12px;color:#6b6b76;line-height:1.5;">
            Si el botón no funciona, copia este enlace en tu navegador:<br>
            <span style="color:{FULKRO_VIOLET};word-break:break-all;">{magic_link_url}</span>
          </p>
          <hr style="border:none;border-top:1px solid #e6e4f5;margin:24px 0;">
          {FULKRO_EMAIL_SIGNATURE_HTML}
        </td></tr>
        <tr><td style="background:#F5F4FF;padding:16px 28px;text-align:center;">
          <p style="margin:0;font-size:11px;color:#9a99a6;">{FULKRO_FOOTER_TEXT}</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    text = f"""\
{saludo}

Soy Marcos, de Fulkro. Trabajamos con empresas que se relacionan con la
Administración pública y a veces se encuentran con el Esquema Nacional de
Seguridad (ENS) sin tenerlo claro del todo.

He preparado un cuestionario breve, sin tecnicismos y sin compromiso, para
entender vuestra situación y deciros con criterio si el ENS os aplica y por
dónde empezaríais. Se responde en unos minutos:

{magic_link_url}

{FULKRO_EMAIL_SIGNATURE_TEXT}

{FULKRO_FOOTER_TEXT}"""

    return {"subject": PRECLIENTE_EMAIL_SUBJECT, "html": html, "text": text}
