"""Endpoint público de contacto del landing (fulkro.es/contacto).

SIN autenticación. Lo consume el formulario estático de `landing/contacto.html`
(servido por Caddy en fulkro.es; Caddy proxya esta ruta a app:8000). Envía el
lead por email a CONTACT_EMAIL (por defecto marcosmata@fulkro.es) usando el
EmailSender + SMTP propios (datos en el servidor UE · RGPD-clean · NO terceros).

Anti-spam: honeypot `website` (un bot lo rellena → se descarta en silencio) +
límites de longitud de Pydantic.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.email.sender import get_email_sender
from backend.app.database import get_db

router = APIRouter(prefix="/public", tags=["Public — Contacto landing"])

CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "marcosmata@fulkro.es")


class ContactForm(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=160)
    empresa: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    cargo: str = Field("", max_length=160)
    telefono: str = Field("", max_length=60)
    nivel: str = Field("", max_length=40)
    mensaje: str = Field("", max_length=5000)
    # Honeypot · debe llegar vacío. Los bots lo rellenan.
    website: str = Field("", max_length=200)


class ContactResponse(BaseModel):
    ok: bool


def _esc(s: str) -> str:
    """Escape mínimo para incrustar texto del usuario en el HTML del email."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@router.post("/contact", response_model=ContactResponse)
async def submit_contact(
    form: ContactForm,
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Recibe el formulario del landing y lo envía por email a CONTACT_EMAIL.

    Devuelve siempre ``ok: true`` (también si el honeypot está relleno, para no
    dar pistas al bot). El fallo de envío se registra en email_log (delivery
    _status='failed') sin romper la respuesta al visitante.
    """
    # Honeypot · descarta silenciosamente sin enviar.
    if form.website.strip():
        return ContactResponse(ok=True)

    cargo = form.cargo.strip() or "—"
    telefono = form.telefono.strip() or "—"
    nivel = form.nivel.strip() or "(no indicado)"
    mensaje = form.mensaje.strip() or "(sin mensaje)"

    subject = f"[Web FULKRO] {form.nombre} · {form.empresa}"
    html_body = (
        "<h2>Nuevo contacto desde fulkro.es</h2>"
        f"<p><b>Nombre:</b> {_esc(form.nombre)}<br>"
        f"<b>Empresa:</b> {_esc(form.empresa)}<br>"
        f"<b>Cargo:</b> {_esc(cargo)}<br>"
        f"<b>Email:</b> <a href=\"mailto:{_esc(form.email)}\">{_esc(form.email)}</a><br>"
        f"<b>Teléfono:</b> {_esc(telefono)}<br>"
        f"<b>Nivel ENS:</b> {_esc(nivel)}</p>"
        f"<p><b>Mensaje:</b><br>{_esc(mensaje).replace(chr(10), '<br>')}</p>"
        "<hr><p style=\"color:#888;font-size:12px\">Formulario de contacto · "
        "landing fulkro.es</p>"
    )
    text_body = (
        "Nuevo contacto desde fulkro.es\n\n"
        f"Nombre: {form.nombre}\n"
        f"Empresa: {form.empresa}\n"
        f"Cargo: {cargo}\n"
        f"Email: {form.email}\n"
        f"Telefono: {telefono}\n"
        f"Nivel ENS: {nivel}\n\n"
        f"Mensaje:\n{mensaje}\n"
    )

    sender = get_email_sender()
    await sender.send(
        db,
        to=CONTACT_EMAIL,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        template_used="landing_contacto",
        metadata={"source": "landing_contacto", "from_email": form.email},
    )
    await db.commit()
    return ContactResponse(ok=True)
