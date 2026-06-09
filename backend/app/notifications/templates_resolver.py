"""TemplateResolver YAML + Jinja2 sandboxed (MB-16.3 ADR-039).

Carga templates desde ``backend/app/notifications/templates/<name>.yaml``
con estructura:

    subject_es: "Plantilla asunto · {{ project_name }}"
    html_body_es: |
        <p>Hola {{ recipient_name }} ...</p>
    text_body_es: |
        Hola {{ recipient_name }} ...
    cta_label_es: "Abrir tarea"

API:

    resolver = TemplateResolver()
    rendered = resolver.render(
        "task_assigned",
        context={
            "recipient_name": "Ana",
            "project_name": "Proyecto X",
            "cta_url": "https://fulkro.es/...",
        },
    )
    rendered.subject  # str
    rendered.html_body  # str (con whatsapp pie auto-appended)
    rendered.text_body  # str (con whatsapp pie auto-appended)

Sandbox Jinja2:
- ``ImmutableSandboxedEnvironment`` previene escapes peligrosos.
- ``StrictUndefined`` falla si template referencia variable no
  presente en context (catch dev errors temprano).
- ``autoescape`` activo para HTML body solo (text_body raw).
- WhatsApp footer auto-append vía ``WhatsAppInfoFormatter``.
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import StrictUndefined
from jinja2.sandbox import ImmutableSandboxedEnvironment

from backend.app.notifications.whatsapp_info import WhatsAppInfoFormatter


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


class TemplateError(Exception):
    """Error genérico template resolver."""


@dataclass(frozen=True)
class RenderedTemplate:
    subject: str
    html_body: str
    text_body: str
    cta_label: str | None = None


@functools.lru_cache(maxsize=64)
def _load_template_raw(name: str, templates_dir: str) -> dict:
    path = Path(templates_dir) / f"{name}.yaml"
    if not path.exists():
        raise TemplateError(f"Template not found: {name} at {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise TemplateError(
            f"Template {name} must be a YAML mapping at top level"
        )
    return data


def clear_template_cache() -> None:
    """Drop the in-process template cache · útil para tests + hot reload."""
    _load_template_raw.cache_clear()


class TemplateResolver:
    """Resuelve templates YAML a HTML/text renderizados con Jinja2 sandbox.

    El sandbox previene templates maliciosos (callable execution,
    attribute access privado). Variables faltantes raise StrictUndefined
    para detectar bugs dev temprano.

    ``render()`` añade WhatsApp footer automaticamente al final del
    cuerpo (HTML + text). Si ``MARCOS_WHATSAPP_NUMBER`` vacío → no
    se añade nada (degradación elegante).
    """

    def __init__(
        self,
        *,
        templates_dir: Path | None = None,
        whatsapp_formatter: WhatsAppInfoFormatter | None = None,
    ):
        self._templates_dir = templates_dir or TEMPLATES_DIR
        self._whatsapp = whatsapp_formatter or WhatsAppInfoFormatter()
        self._html_env = ImmutableSandboxedEnvironment(
            autoescape=True,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._text_env = ImmutableSandboxedEnvironment(
            autoescape=False,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, name: str, context: dict) -> RenderedTemplate:
        raw = _load_template_raw(name, str(self._templates_dir))
        subject = self._render_string(
            raw.get("subject_es", ""), context, html=False,
        )
        html_body = self._render_string(
            raw.get("html_body_es", ""), context, html=True,
        )
        text_body = self._render_string(
            raw.get("text_body_es", ""), context, html=False,
        )
        cta_label = raw.get("cta_label_es")
        if cta_label:
            cta_label = self._render_string(cta_label, context, html=False)

        whatsapp_html = self._whatsapp.render_html_block()
        whatsapp_text = self._whatsapp.render_text_block()
        if whatsapp_html:
            html_body = html_body.rstrip() + "\n" + whatsapp_html + "\n"
        if whatsapp_text:
            text_body = text_body.rstrip() + whatsapp_text

        return RenderedTemplate(
            subject=subject.strip(),
            html_body=html_body,
            text_body=text_body,
            cta_label=cta_label,
        )

    def _render_string(self, source: str, context: dict, *, html: bool) -> str:
        if not source:
            return ""
        env = self._html_env if html else self._text_env
        template = env.from_string(source)
        return template.render(**context)


__all__ = [
    "TemplateResolver",
    "RenderedTemplate",
    "TemplateError",
    "TEMPLATES_DIR",
    "clear_template_cache",
]
