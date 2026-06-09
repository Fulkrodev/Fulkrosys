"""CopilotPersonaService · sub-atom 1.D.B.0.1 v3.10 base infra LLM swap-in.

Wraps AgentBase pattern existing (`backend/app/agents/base.py`) con persona-aware
system prompt rendering · context building per role (cliente | admin) · ready
para swap-in 1.D.B.1 (cliente LLM real) + 1.D.B.2 (admin LLM real).

OPS-045 14ª aplicación consecutiva: AgentBase ya provee 95% LLM infra
(router + cache + log + parse + citation extraction). Este service añade
solo persona-aware prompt rendering · context loaders por rol.

Sostiene R1 inviolable: NO decisiones normativas automatizadas (A21 determinista
cubre). Copilotos LLM = chat conversacional · explicar · ayudar · sugerir.

Sostiene R29 (cliente sin presión coercitiva) + R30 (admin asume cero ENS) ·
boundaries enforced via YAML personas + tests boundary verify.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agents.copilot_personas_loader import (
    CopilotPersona,
    PersonaRole,
    build_system_prompt,
    get_persona,
    lookup_screen_reference,
)


class CopilotPersonaService:
    """Service base copilot persona-aware · ready swap-in 1.D.B.1+.2."""

    def __init__(self, role: PersonaRole):
        self.role: PersonaRole = role
        self.persona: CopilotPersona = get_persona(role)

    # ════════════════════════════════════════════════════════════════
    # Context builders per role
    # ════════════════════════════════════════════════════════════════

    async def build_client_context(
        self,
        db: AsyncSession,
        project_id: uuid.UUID | None,
        step_template_id: str | None = None,
        step_title: str | None = None,
        fase_actual: str | None = None,
    ) -> dict[str, Any]:
        """Construye context cliente · solo SU proyecto · NO admin metadata.

        Sostiene R30 inverso (NO admin metadata exposure) · cliente recibe
        solo info útil su workflow personal.
        """
        if self.role != "cliente":
            raise ValueError(
                "build_client_context only valid for role=cliente",
            )

        client_company = "(empresa cliente)"
        project_category = "(categoría ENS)"
        project_context = "(contexto proyecto no disponible)"

        if project_id is not None:
            try:
                result = await db.execute(
                    sa_text(
                        "SELECT p.nombre, p.categoria_objetivo, p.fase, "
                        "c.nombre as client_name "
                        "FROM projects p "
                        "LEFT JOIN clients c ON p.client_id = c.id "
                        "WHERE p.id = :pid",
                    ),
                    {"pid": str(project_id)},
                )
                row = result.fetchone()
                if row:
                    project_name = row[0] or "(sin nombre)"
                    project_category = row[1] or "(sin categoría)"
                    fase = row[2] or "(sin fase)"
                    client_company = row[3] or project_name
                    project_context = (
                        f"Proyecto: {project_name} · Fase: {fase} · "
                        f"Categoría ENS: {project_category}"
                    )
            except Exception:
                # Best-effort · context limited si query falla
                pass

        current_step_context = "(sin step activo)"
        if step_title:
            current_step_context = step_title
        elif step_template_id:
            current_step_context = f"Step template: {step_template_id}"
        if fase_actual and current_step_context != "(sin step activo)":
            current_step_context = f"{current_step_context} · Fase: {fase_actual}"

        return {
            "client_company": client_company,
            "project_category": project_category,
            "project_context": project_context,
            "current_step_context": current_step_context,
        }

    async def build_admin_context(
        self,
        db: AsyncSession,
        active_project_id: uuid.UUID | None = None,
        active_project_name: str | None = None,
        active_step_title: str | None = None,
        active_fase: str | None = None,
        current_screen: str | None = None,
        active_motor: str | None = None,
    ) -> dict[str, Any]:
        """Construye context admin · portfolio + cliente activo opcional.

        Si Marcos viendo cliente específico (active_project_id provisto) ·
        include detalle ese cliente. Portfolio context resumen multi-cliente.

        1.D.F.0.D · si current_screen provisto · lookup screen_references_catalog
        para inyectar `current_screen_context` + `current_screen_actions` ·
        permite copiloto referenciar botones específicos UI.
        """
        if self.role != "admin":
            raise ValueError(
                "build_admin_context only valid for role=admin",
            )

        portfolio_context = await self._build_portfolio_summary(db)

        active_client_context = "(sin cliente activo focus)"
        details: list[str] = []
        if active_project_name:
            details.append(f"Cliente: {active_project_name}")
        if active_fase:
            details.append(f"Fase: {active_fase}")
        if active_step_title:
            details.append(f"Step actual: {active_step_title}")

        if details:
            active_client_context = " · ".join(details)
        elif active_project_id is not None:
            # Fallback · fetch project name desde DB cuando NO se pasó name
            try:
                result = await db.execute(
                    sa_text(
                        "SELECT nombre, fase FROM projects WHERE id = :pid",
                    ),
                    {"pid": str(active_project_id)},
                )
                row = result.fetchone()
                if row:
                    active_client_context = (
                        f"Cliente: {row[0] or '(sin nombre)'} · "
                        f"Fase: {row[1] or '(sin fase)'}"
                    )
            except Exception:
                pass

        # 1.D.F.0.D · screen-aware context lookup
        screen_ref = lookup_screen_reference(self.persona, current_screen)
        if screen_ref is not None:
            motor_label = active_motor or screen_ref.motor
            current_screen_context = (
                f"{screen_ref.screen_name} (motor {motor_label}) · "
                f"{screen_ref.context_hints}"
            )
            bullets = "\n".join(f"  - {a}" for a in screen_ref.actions)
            current_screen_actions = (
                f"Botones disponibles en pantalla activa:\n{bullets}"
            )
        else:
            current_screen_context = "(sin pantalla activa identificada)"
            current_screen_actions = (
                "(sin acciones específicas · da guidance conceptual general)"
            )

        return {
            "portfolio_context": portfolio_context,
            "active_client_context": active_client_context,
            "current_screen_context": current_screen_context,
            "current_screen_actions": current_screen_actions,
        }

    async def _build_portfolio_summary(self, db: AsyncSession) -> str:
        """Resumen portfolio multi-cliente · counts per fase · best-effort."""
        try:
            result = await db.execute(
                sa_text(
                    # #7.3 guard: proyectos LIGEROS (lead en embudo · DRAFT +
                    # pre_venta) NO cuentan como clientes activos.
                    "SELECT COUNT(*) FROM projects "
                    "WHERE deleted_at IS NULL AND estado != 'cerrado' "
                    "AND NOT (lifecycle_state = 'DRAFT' AND fase = 'pre_venta')",
                ),
            )
            active_count = result.scalar() or 0
            return f"Portfolio activo: {active_count} cliente(s)"
        except Exception:
            return "(portfolio resumen no disponible)"

    # ════════════════════════════════════════════════════════════════
    # System prompt rendering
    # ════════════════════════════════════════════════════════════════

    def render_system_prompt(self, context: dict[str, Any]) -> str:
        """Render system prompt con persona + context provisto."""
        return build_system_prompt(self.persona, context)

    # ════════════════════════════════════════════════════════════════
    # Persona metadata accessors (para tests + UI exposure si necesario)
    # ════════════════════════════════════════════════════════════════

    @property
    def model(self) -> str:
        return self.persona.model_recommended

    @property
    def temperature(self) -> float:
        return self.persona.temperature

    @property
    def max_tokens(self) -> int:
        return self.persona.max_tokens

    @property
    def enable_prompt_caching(self) -> bool:
        return self.persona.enable_prompt_caching

    @property
    def citations_required(self) -> bool:
        return self.persona.citations_required
