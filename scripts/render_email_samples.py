"""Render sample HTML previews of every compliance email template.

Outputs two width variants per template under:

    /mnt/c/Users/Usuario/Desktop/Fulkro compliance/08-Self_Monitoring_Reports/email_samples/

- ``{name}_email.html``   → 600px, the real width Postmark / Gmail / Outlook
  / Apple Mail use. Looks "mobile-ish" in a desktop browser because email
  clients enforce this max-width.
- ``{name}_preview.html`` → 840px, comfortable for desktop browser
  inspection. NOT representative of real email rendering width — useful
  only to evaluate brand consistency, typography, color hierarchy.

Run from the project root with ``.venv`` active:

    PYTHONPATH=/home/usuario/fulkro python scripts/render_email_samples.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.app.motors.m_compliance.email_design.mjml_compiler import (
    render_email,
)


OUTPUT_DIR = Path(
    "/mnt/c/Users/Usuario/Desktop/Fulkro compliance/"
    "08-Self_Monitoring_Reports/email_samples"
)

EMAIL_WIDTH = "600px"      # Postmark / Gmail / Outlook real width
PREVIEW_WIDTH = "840px"    # comfortable desktop browser inspection


_PREVIEW_BANNER_HEAD = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>FULKRO email preview · {name}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: #e5e7eb;
      font-family: -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
    }}
    .preview-banner {{
      background: #fbbf24;
      color: #1a1a1a;
      padding: 14px 24px;
      text-align: center;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.02em;
    }}
    .preview-banner small {{
      display: block;
      margin-top: 4px;
      opacity: 0.75;
      font-weight: 400;
      font-size: 12px;
    }}
    .preview-shell {{ padding: 32px 16px; }}
    /* Override MJML max-width on email tables for comfortable
       browser inspection (real email clients ignore these). */
    .preview-shell > div > div[style*="max-width:600px"],
    .preview-shell > div > div[style*="max-width:840px"] {{
      max-width: 1100px !important;
      width: 100% !important;
    }}
    .preview-shell > div > div[style*="max-width:600px"] table,
    .preview-shell > div > div[style*="max-width:840px"] table {{
      width: 100% !important;
    }}
  </style>
</head>
<body>
  <div class="preview-banner">
    📧 PREVIEW MODE · Browser inspection wide (max 1100&nbsp;px)
    <small>NOT real email render · Gmail / Outlook / Apple Mail use 600&nbsp;px container industry standard</small>
  </div>
  <div class="preview-shell">
"""

_PREVIEW_BANNER_TAIL = """  </div>
</body>
</html>
"""


def _wrap_preview(name: str, mjml_html: str) -> str:
    return _PREVIEW_BANNER_HEAD.format(name=name) + mjml_html + _PREVIEW_BANNER_TAIL


@dataclass
class _Breach:
    breach_code: str = "BREACH_2026_001"
    detected_at: datetime = datetime(2026, 5, 12, 10, 0, tzinfo=timezone.utc)
    severity: str = "high"
    description: str = (
        "Detección de acceso no autorizado a una copia de seguridad antigua "
        "de la base de datos. El bucket de almacenamiento tenía configurada "
        "una política de permisos demasiado permisiva durante 4 horas."
    )
    data_categories_affected: list = None
    data_subjects_count: int = 42
    root_cause: str = (
        "Cambio manual en la configuración del bucket MinIO sin pasar por la "
        "revisión 4 ojos. La detección llegó por la auditoría de cambios."
    )
    containment_actions: str = (
        "1. Credenciales del bucket revocadas inmediatamente.\n"
        "2. Política de permisos restaurada a la línea base.\n"
        "3. Rotación de claves de acceso."
    )
    remediation_actions: str = (
        "Implementación de revisión obligatoria 4 ojos para cambios de "
        "política en buckets de evidencias. Auditoría externa de "
        "configuración cloud prevista para la próxima semana."
    )


@dataclass
class _Request:
    id: str = "00000000-0000-0000-0000-000000000001"
    requested_at: datetime = datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc)
    processed_at: datetime = datetime(2026, 5, 12, 10, 0, tzinfo=timezone.utc)
    processed_by: str = "marcosmata@fulkro.es"
    rejection_reason: str = (
        "Datos retenidos por obligación legal: RD 311/2022 art. 24.1 — "
        "retención de evidencias ENS durante 7 años + Art. 30.4 RGPD. El "
        "registro de auditoría asociado se mantiene anonimizado al "
        "vencer la obligación."
    )


_SAMPLES: dict[str, tuple[str, dict]] = {
    "compliance_alert_HIGH": (
        "compliance_alert.mjml",
        dict(
            severity_label="HIGH",
            severity_level="high",
            status_label="RED",
            period_label="alerta inmediata",
            check_count=2,
            alerts=[
                {
                    "check_name": "ssl_cert_expiry",
                    "status": "RED",
                    "status_level": "red",
                    "message": "Certificado expira en 5 días",
                },
                {
                    "check_name": "backups_integrity",
                    "status": "YELLOW",
                    "status_level": "yellow",
                    "message": "Última copia tiene 56h de antigüedad",
                },
            ],
            admin_url="https://fulkro.es/admin/compliance/monitor",
            report_url="https://fulkro.es/reports/sample.md",
        ),
    ),
    "compliance_alert_MEDIUM_DIGEST": (
        "compliance_alert.mjml",
        dict(
            severity_label="DIGEST",
            severity_level="medium",
            status_label="YELLOW/MEDIUM",
            period_label="digest weekly",
            check_count=3,
            alerts=[
                {
                    "check_name": "audit_logs_continuity",
                    "status": "YELLOW",
                    "status_level": "yellow",
                    "message": "Audit log gap de 36h",
                },
                {
                    "check_name": "rls_coverage_percentage",
                    "status": "YELLOW",
                    "status_level": "yellow",
                    "message": "RLS coverage 84% (objetivo ≥ 90%)",
                },
                {
                    "check_name": "isms_docs_review_due",
                    "status": "YELLOW",
                    "status_level": "yellow",
                    "message": "2 ISMS docs próximos a revisión anual",
                },
            ],
            admin_url="https://fulkro.es/admin/compliance/monitor",
            report_url=None,
        ),
    ),
    "aepd_breach_notification": (
        "aepd_breach_notification.mjml",
        dict(
            breach=_Breach(
                data_categories_affected=[
                    "Identificativos (nombre, apellidos)",
                    "Contacto profesional (email, teléfono)",
                    "Datos técnicos del sistema cliente (IPs, hostnames)",
                ],
            ),
            now=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
        ),
    ),
    "client_breach_notification": (
        "client_breach_notification.mjml",
        dict(
            breach=_Breach(
                severity="medium",
                data_categories_affected=[
                    "Tu email de acceso al portal",
                    "Tu nombre completo",
                ],
            ),
            cliente_email="empleado.ejemplo@empresa-cliente.com",
            now=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
        ),
    ),
    "erasure_completed": (
        "erasure_completed.mjml",
        dict(request=_Request()),
    ),
    "erasure_rejected": (
        "erasure_rejected.mjml",
        dict(request=_Request()),
    ),
}


_README = """# FULKRO Email Samples · Visual Inspection Guide

Cada plantilla compliance se renderiza en **2 anchos** para que puedas
inspeccionarla con criterio adecuado:

| Sufijo | Ancho | Cuándo es relevante |
|---|---|---|
| `_email.html` | **600 px** | Render real Postmark / Gmail / Outlook / Apple Mail. Email clients fuerzan este max-width, así que parece "móvil" en browser desktop · es lo correcto. |
| `_preview.html` | **840 px** | Inspección visual cómoda en browser desktop. NO representa el render real de email — sirve para juzgar tipografía, jerarquía cromática y consistencia de marca. |

## Cómo evaluar la calidad

1. **Para juzgar diseño + brand** → abre `_preview.html` (840 px).
2. **Para verificar fidelidad email** → abre `_email.html` (600 px) o copia
   el archivo a tu correo y envíatelo a ti mismo desde mock backend.

## Logos aplicados

Todos los templates usan el logo `fulkro-logo-mono-white.svg` (white over
slate-900 header) inline como base64 — no hay imágenes externas: los
clientes de email bloquean URLs externas, por lo que SVG inline es la
forma email-safe de incluir el logo.

Helper context-aware disponible en `FulkroLogos.for_background(bg_hex)`:
selecciona el variant de mejor contraste (mono-white sobre fondos
oscuros, black sobre fondos claros).

## Templates incluidos (6)

| Template | Audiencia | Severity | Cuándo se envía |
|---|---|---|---|
| `compliance_alert_HIGH` | Admin (Marcos) | HIGH (rojo) | Self-Monitoring detecta alerta crítica inmediata |
| `compliance_alert_MEDIUM_DIGEST` | Admin (Marcos) | MEDIUM (amber) | Digest semanal de avisos no críticos |
| `aepd_breach_notification` | AEPD oficial | High | Art. 33 RGPD 72h |
| `client_breach_notification` | Cliente | Medium | Art. 34 RGPD (afectado por brecha) |
| `erasure_completed` | Cliente | Success | Art. 17 RGPD ejecutado (tombstone anonymize) |
| `erasure_rejected` | Cliente | Warning | Art. 17.3 RGPD denegado (retención legal) |

## Cambios round 2 (vs versión anterior)

- ✅ Logo FULKRO SVG inline base64 (eliminado placeholder texto)
- ✅ 2 variants per template (600px email + 840px preview)
- ✅ SEVERITY_MEDIUM: `#ea580c` → `#c2410c` (WCAG AA contrast 6.5:1)
"""


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rendered = 0
    for name, (template, base_ctx) in _SAMPLES.items():
        for suffix, width in (("email", EMAIL_WIDTH), ("preview", PREVIEW_WIDTH)):
            html = render_email(template, {**base_ctx, "body_width": width})
            if suffix == "preview":
                html = _wrap_preview(name, html)
            path = OUTPUT_DIR / f"{name}_{suffix}.html"
            path.write_text(html, encoding="utf-8")
            print(f"  wrote {path.name} ({len(html):,} bytes · width={width})")
            rendered += 1

    (OUTPUT_DIR / "README.md").write_text(_README, encoding="utf-8")
    print(f"  wrote README.md (visual inspection guide)")
    print(f"\n✓ {rendered} samples + README rendered to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
