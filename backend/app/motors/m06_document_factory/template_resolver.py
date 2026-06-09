"""Template variant resolver per arquetipo PYME (ADR-036 SAN-D MB-17.6).

``TemplateResolver.resolve_template(template_id, categoria, archetype)``
busca el archivo template más específico al arquetipo del proyecto y
fallback al canonical baseline si no existe variant.

Ejemplo (sector_salud)::

    resolver.resolve_template(
        "E100_politica_de_seguridad_de_la_informacion",
        categoria="MEDIA",
        archetype="sector_salud",
    )
    # → templates/policies/E100_politica_de_seguridad_de_la_informacion_sector_salud.md

VARIANT_MAPPING traduce ``feature_key`` (catalog) → suffix archivo.
Lowercase enum values per ``PymeArquetipo`` real.

Path resolution absoluta vía ``Path(__file__).parent`` (TRAD-10
ADR-036 · evita relative path bug si CWD difiere).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from backend.app.core.feature_flags import is_feature_applicable


class TemplateResolver:
    """Resuelve template específico per arquetipo del proyecto."""

    TEMPLATES_ROOT = Path(__file__).parent / "templates"

    # feature_key (catalog) → suffix archivo · lowercase enum values
    VARIANT_MAPPING: dict[str, str] = {
        "art9_rgpd_data": "_sector_salud",
        "skip_mp_if_instalaciones": "_saas_only",
        "cra_sdlc_seguro": "_desarrollador_aapp",
        "dora_dual_compliance": "_proveedor_financiero",
        "ztna_mfa_obligatorio": "_teletrabajo_total",
        "pce_universidades": "_universidades",
    }

    def resolve_template(
        self,
        template_id: str,
        categoria: str,
        archetype: Optional[str] = None,
        subdir: str = "policies",
    ) -> Path:
        """Retorna path template · prefiere variant arquetipo si existe.

        Si no hay variant aplicable o no existe el archivo, retorna
        path canonical baseline ``{template_id}.md`` aunque también no
        exista (caller verifica existence si necesita).
        """
        if archetype:
            for feature_key, suffix in self.VARIANT_MAPPING.items():
                if not is_feature_applicable(feature_key, categoria, archetype):
                    continue
                variant_path = (
                    self.TEMPLATES_ROOT / subdir / f"{template_id}{suffix}.md"
                )
                if variant_path.exists():
                    return variant_path

        return self._canonical_path(template_id, subdir)

    def _canonical_path(self, template_id: str, subdir: str) -> Path:
        return self.TEMPLATES_ROOT / subdir / f"{template_id}.md"
