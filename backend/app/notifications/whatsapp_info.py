"""WhatsAppInfoFormatter modo informativo (MB-16.3 ADR-039 fix).

Directiva Marcos post-briefing v3: WhatsApp aparece en pie email
como TEXTO PLANO con espacios legibles · NO link clickeable wa.me ·
NO encoded text. Cliente copia el número y lo introduce en su
WhatsApp manualmente si decide. Cero automatización pushy.

Misma filosofía aplicará a MB-18 IBAN (próximo MB · solo texto · no
botón "Copiar IBAN").

API:
    formatter = WhatsAppInfoFormatter()
    info = formatter.format()
    if info is not None:
        # info.number = "+34 666 123 456"
        # info.hours = "de 9:00 a 18:00 L-V"
        ...

Si ``Settings.marcos_whatsapp_number`` está vacío → ``format()``
retorna ``None`` · pie email NO incluye sección WhatsApp
(degradación elegante).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from backend.app.config import get_settings


_DIGITS_RE = re.compile(r"\D+")


@dataclass(frozen=True)
class WhatsAppInfo:
    number: str
    hours: str


def _format_phone_humano(raw: str) -> str:
    """Formatea ``+34666123456`` o ``34666123456`` a ``+34 666 123 456``.

    - Si tiene 11 dígitos asumimos prefijo país 1-3 dígitos · separa
      grupos remanentes en bloques de 3.
    - Si no encaja patrón conocido devuelve raw normalizado con espacios
      cada 3 dígitos manteniendo el ``+`` inicial si presente.

    Política conservadora: si fallo parsing devuelve raw stripped.
    """
    s = raw.strip()
    if not s:
        return s
    has_plus = s.startswith("+")
    digits = _DIGITS_RE.sub("", s)
    if not digits:
        return s

    if has_plus and len(digits) in (11, 12):
        prefix_len = 2 if len(digits) == 11 else 3
        prefix = digits[:prefix_len]
        rest = digits[prefix_len:]
        chunks = [rest[i:i + 3] for i in range(0, len(rest), 3)]
        return f"+{prefix} " + " ".join(chunks)

    if has_plus:
        return f"+{digits}"
    return digits


class WhatsAppInfoFormatter:
    """Formatea info contacto WhatsApp para pie email · modo informativo.

    NO genera URLs · NO encoded text · NO link href · NO ``target="_blank"``.
    Solo texto formateado para que cliente copie/pegue manualmente
    en su WhatsApp si decide usarlo.
    """

    def format(self) -> WhatsAppInfo | None:
        """Devuelve ``WhatsAppInfo`` o ``None`` si no configurado.

        ``None`` indica degradación elegante · pie email NO debe
        incluir sección WhatsApp.
        """
        settings = get_settings()
        raw = (settings.marcos_whatsapp_number or "").strip()
        if not raw:
            return None
        return WhatsAppInfo(
            number=_format_phone_humano(raw),
            hours=settings.marcos_whatsapp_hours,
        )

    def render_text_block(self) -> str:
        """Bloque texto plano para pie email plain-text.

        Formato:
            ---
            📞 ¿Prefieres WhatsApp? +34 666 123 456 (de 9:00 a 18:00 L-V)

        Retorna ``""`` si no configurado (caller concatena sin riesgo).
        """
        info = self.format()
        if info is None:
            return ""
        return (
            "\n---\n"
            f"📞 ¿Prefieres WhatsApp? {info.number} ({info.hours})\n"
        )

    def render_html_block(self) -> str:
        """Bloque HTML para pie email · NO link · solo strong + spans.

        Formato:
            <hr><p style="color:#666;font-size:14px;">
            📞 ¿Prefieres WhatsApp? <strong>+34 666 123 456</strong>
            <span style="color:#999;">(de 9:00 a 18:00 L-V)</span>
            </p>

        Retorna ``""`` si no configurado.
        """
        info = self.format()
        if info is None:
            return ""
        return (
            "<hr>"
            "<p style=\"color:#666;font-size:14px;\">"
            "📞 ¿Prefieres WhatsApp? "
            f"<strong>{info.number}</strong> "
            f"<span style=\"color:#999;\">({info.hours})</span>"
            "</p>"
        )


__all__ = ["WhatsAppInfoFormatter", "WhatsAppInfo"]
