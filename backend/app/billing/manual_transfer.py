"""ManualTransferProvider · info-mode (MB-18.2 ADR-040).

Genera datos transferencia bancaria para email cliente + portal
billing. Texto plano formateado humano legible · NO link clickeable ·
NO `clipboard.writeText` JS · NO botón "Copiar IBAN" · cliente
selecciona y copia manualmente.

Cross-reference WhatsApp MB-16 directiva Marcos: cero automatización
pushy · transferencia bancaria estándar B2B consultoría.

Si ``Settings.marcos_bank_iban`` vacío → ``format_*`` retornan string
vacío → email factura sin sección instrucciones (degradación elegante:
Marcos añade datos a mano editando email Postmark template antes envío).
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from decimal import Decimal

from backend.app.config import get_settings


_DIGITS_RE = re.compile(r"\D+")


@dataclass(frozen=True)
class BankInstructions:
    iban: str
    holder: str
    institution: str
    bic: str | None
    amount_eur: str
    reference: str
    concept: str
    payment_due_date: str | None


def _format_iban_humano(raw: str) -> str:
    """Formatea IBAN en bloques de 4 caracteres (estilo banca europea).

    ``ES12123456789012345678901234`` → ``ES12 1234 5678 9012 3456 7890 1234``.

    Si el formato no encaja (ej. menor a 8 chars), devuelve raw stripped.
    """
    s = (raw or "").strip().replace(" ", "").upper()
    if not s or len(s) < 8:
        return s
    return " ".join(s[i:i + 4] for i in range(0, len(s), 4))


class ManualTransferProvider:
    """Provider info-mode datos transferencia bancaria.

    NO genera URLs · NO encoded text · NO clipboard JS. Solo formato
    texto plano + HTML con `<strong>` para email + portal cliente.
    """

    def build_instructions(
        self,
        *,
        invoice_number: str,
        amount_eur: Decimal,
        payment_due_date: str | None = None,
        concept_override: str | None = None,
    ) -> BankInstructions | None:
        """Devuelve instrucciones · None si IBAN no configurado."""
        settings = get_settings()
        iban = (settings.marcos_bank_iban or "").strip()
        if not iban:
            return None
        return BankInstructions(
            iban=_format_iban_humano(iban),
            holder=settings.marcos_bank_holder or "Marcos Mata",
            institution=settings.marcos_bank_institution or "",
            bic=(settings.marcos_bank_bic or "").strip() or None,
            amount_eur=f"{amount_eur:.2f}",
            reference=invoice_number,
            concept=concept_override or f"Factura {invoice_number}",
            payment_due_date=payment_due_date,
        )

    def render_text_block(
        self,
        *,
        invoice_number: str,
        amount_eur: Decimal,
        payment_due_date: str | None = None,
        concept_override: str | None = None,
    ) -> str:
        """Bloque texto plano para email body.

        Retorna ``""`` si no configurado (caller concatena sin riesgo).
        Cliente selecciona y copia el IBAN manualmente · NO botón.
        """
        info = self.build_instructions(
            invoice_number=invoice_number,
            amount_eur=amount_eur,
            payment_due_date=payment_due_date,
            concept_override=concept_override,
        )
        if info is None:
            return ""
        lines = [
            "📋 INSTRUCCIONES PARA LA TRANSFERENCIA",
            "",
            f"💶 Importe: {info.amount_eur} EUR",
            f"🏦 Banco: {info.institution}" if info.institution else None,
            f"📋 IBAN: {info.iban}",
            f"👤 Titular: {info.holder}",
            f"🔖 Concepto: {info.concept}",
        ]
        if info.bic:
            lines.append(f"🌐 BIC: {info.bic}")
        if info.payment_due_date:
            lines.append(f"📅 Fecha límite: {info.payment_due_date}")
        lines.append("")
        lines.append(
            f"Por favor incluye la referencia '{info.reference}' "
            "en el concepto de la transferencia."
        )
        return "\n".join(line for line in lines if line is not None)

    def render_html_block(
        self,
        *,
        invoice_number: str,
        amount_eur: Decimal,
        payment_due_date: str | None = None,
        concept_override: str | None = None,
    ) -> str:
        """Bloque HTML para email body.

        Formato: `<div>` con `<p><strong>` per campo · NO link · NO
        botón · NO `clipboard.writeText` JS · NO `target="_blank"`.
        Cliente selecciona y copia manualmente.
        """
        info = self.build_instructions(
            invoice_number=invoice_number,
            amount_eur=amount_eur,
            payment_due_date=payment_due_date,
            concept_override=concept_override,
        )
        if info is None:
            return ""
        rows = [
            f"<p style=\"margin:4px 0;\">💶 Importe: <strong>{info.amount_eur} EUR</strong></p>",
        ]
        if info.institution:
            rows.append(
                f"<p style=\"margin:4px 0;\">🏦 Banco: <strong>{html.escape(info.institution)}</strong></p>"
            )
        rows.append(
            f"<p style=\"margin:4px 0;\">📋 IBAN: <strong>{html.escape(info.iban)}</strong></p>"
        )
        rows.append(
            f"<p style=\"margin:4px 0;\">👤 Titular: <strong>{html.escape(info.holder)}</strong></p>"
        )
        rows.append(
            f"<p style=\"margin:4px 0;\">🔖 Concepto: <strong>{html.escape(info.concept)}</strong></p>"
        )
        if info.bic:
            rows.append(
                f"<p style=\"margin:4px 0;\">🌐 BIC: <strong>{html.escape(info.bic)}</strong></p>"
            )
        if info.payment_due_date:
            rows.append(
                f"<p style=\"margin:4px 0;\">📅 Fecha límite: <strong>{info.payment_due_date}</strong></p>"
            )
        instructions_html = (
            f"<p style=\"margin-top:12px;color:#555;font-size:14px;\">"
            f"Por favor incluye la referencia "
            f"<strong>{html.escape(info.reference)}</strong> en el concepto de "
            f"la transferencia.</p>"
        )
        return (
            "<div style=\"background:#f9fafb;border:1px solid #e5e7eb;"
            "border-radius:8px;padding:16px;margin:16px 0;\">"
            "<h4 style=\"margin:0 0 8px 0;color:#1f2937;\">"
            "📋 Instrucciones para la transferencia</h4>"
            + "".join(rows)
            + instructions_html
            + "</div>"
        )


__all__ = ["ManualTransferProvider", "BankInstructions"]
