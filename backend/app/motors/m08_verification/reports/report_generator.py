"""M8 v5.1 - Generador de informes E-702/E-703/E-704 (spec §5.1).

Construye el contexto rico (findings + delta + heatmap + score + SLA +
remediation + MITRE + ENS) para un VerificationRun y delega la
renderizacion al pipeline de M6 Document Factory (docxtpl + firma Ed25519
+ PDF LibreOffice).

Uso tipico:

    generator = VerificationReportGenerator(db)
    result = await generator.generate_e702(run_id)
    result['docx_path'], result['pdf_path'], result['signature_ed25519']
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import Client, Project
from backend.app.motors.m06_document_factory.service import (
    DocumentFactoryService,
)
from backend.app.motors.m08_verification.models import (
    ExternalPentesterHandoff, VerificationFinding, VerificationRun,
)
from backend.app.motors.m08_verification.remediation.guide_generator import (
    finding_to_guide_input, generate_guide,
)
from backend.app.motors.m08_verification.remediation.sla_calculator import (
    calculate_deadline,
)
from backend.app.motors.m08_verification.reports.delta_report import (
    compute_delta, persist_delta_to_run,
)
from backend.app.motors.m08_verification.reports.heatmap_generator import (
    ENS_73_MEASURES, generate_heatmap, heatmap_summary,
)
from backend.app.motors.m08_verification.reports.score_calculator import (
    calculate_score, persist_score_to_run,
)


REPORT_CODES_BY_MODE = {
    "internal": ["E-702", "E-703"],
    "external_handoff": ["E-702", "E-703", "E-704"],
    "external_ingest_pdf": ["E-704"],
    "external_ingest_form": ["E-704"],
}


class VerificationReportGenerator:
    """Construye contexto + delega a M6 para generar DOCX+PDF firmado."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.docs = DocumentFactoryService(db)

    # ─── Context builder ─────────────────────────────────────────────

    async def build_context(
        self,
        run: VerificationRun,
        *,
        include_remediation: bool = True,
        remediation_force_offline: bool = True,
    ) -> dict[str, Any]:
        """Construye el contexto rico para renderizar E-702/E-703/E-704.

        Si ``include_remediation`` es True, invoca el guide_generator
        por cada finding con severity>=medium (por coste, quick_wins
        primero). Por defecto ``force_offline=True`` para que los tests
        y ejecuciones sin API key usen el template deterministico.
        """
        # Cliente + proyecto
        project = await self.db.get(Project, run.project_id)
        client = await self.db.get(Client, project.client_id) if project else None

        findings_all = await self._load_findings(run.id)
        findings_scope = [
            f for f in findings_all
            if f.zfp_gate5_classification in ("confirmed", "probable")
            and (f.status or "open") in ("open", "needs_review")
        ]
        findings_scope.sort(
            key=lambda f: (
                {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(
                    (f.severity or "info").lower(), 5,
                ),
                -float(f.confidence_score or 0),
            ),
        )
        findings_external = [
            f for f in findings_scope
            if any("external" in (src or "") for src in (f.tool_sources or []))
        ]
        findings_priority = [
            f for f in findings_scope
            if (f.severity or "").lower() in ("critical", "high")
        ]

        # Score + heatmap
        score = calculate_score(findings_all)
        score_dict = score.to_dict()
        score_dict["level_upper"] = score_dict["level"].upper()
        heatmap_cells = generate_heatmap(findings_all, measures=ENS_73_MEASURES)
        hm_summary = heatmap_summary(heatmap_cells)
        total_cells = hm_summary["total"] or 1
        for key in ("compliant", "partial", "non_compliant", "not_verified"):
            hm_summary[f"{key}_pct"] = round(
                100 * hm_summary.get(key, 0) / total_cells, 1,
            )

        # Delta vs run anterior (si existe previous_run_id)
        delta_payload = {
            "previous_run_date": None,
            "totals": {"new": 0, "resolved": 0, "persistent": 0, "severity_changes": 0},
            "overall_trend": "estable",
            "new": [], "resolved": [], "persistent": [], "severity_changes": [],
        }
        if run.previous_run_id:
            prev_findings = await self._load_findings(run.previous_run_id)
            delta = compute_delta(prev_findings, findings_all)
            prev_run = await self.db.get(VerificationRun, run.previous_run_id)
            delta_payload = delta.to_dict()
            delta_payload["previous_run_date"] = (
                prev_run.completed_at.date().isoformat() if prev_run and prev_run.completed_at
                else None
            )

        # Remediation guides + SLA por finding (solo los en scope)
        findings_ctx = []
        findings_external_ctx = []
        findings_priority_ctx = []
        for f in findings_scope:
            entry = self._finding_to_ctx(f)
            if include_remediation:
                entry["remediation"] = generate_guide(
                    finding_to_guide_input(f),
                    force_offline=remediation_force_offline,
                )
            else:
                entry["remediation"] = {
                    "resumen_no_tecnico": "", "riesgo_real": "",
                    "pasos": [],
                    "tiempo_estimado": "", "requiere_reinicio": False,
                    "requiere_ventana_mantenimiento": False,
                    "fuente": "skipped",
                }
            sla = calculate_deadline(f.severity, f.created_at or datetime.now(timezone.utc))
            entry["sla"] = sla.to_dict()
            findings_ctx.append(entry)
            if f in findings_external:
                findings_external_ctx.append(entry)
            if f in findings_priority:
                findings_priority_ctx.append(entry)

        # Tools usados (para la tabla metodologia)
        tools_used = run.tools_used or []
        tools_discovery = ", ".join(
            t for t in tools_used if t in ("nmap", "dns", "ad_password")
        ) or "nmap"
        tools_verification = ", ".join(
            t for t in tools_used if t in (
                "nuclei", "testssl", "zap", "lynis", "prowler", "openvas",
            )
        ) or "nuclei, testssl, zap, lynis"

        handoff = await self._load_handoff(run.id)

        cliente_ctx = {
            "razon_social": (client.nombre if client else "Cliente"),
            "nif": (client.cif if client else ""),
            "sector": (client.sector if client else ""),
            "domicilio_social": getattr(client, "domicilio_social", "") or "",
        }
        responsables_ctx = {
            "responsable_seguridad": {
                "nombre": (
                    getattr(client, "responsable_seguridad_nombre", None)
                    or "Responsable de Seguridad"
                ),
                "cargo": "Responsable de Seguridad de la Informacion",
                "email": getattr(client, "contacto_email", "") or "",
            },
        }

        fecha_emision = (
            run.completed_at.date().isoformat()
            if run.completed_at else datetime.now(timezone.utc).date().isoformat()
        )
        fecha_inicio = (
            run.phase1_started_at.date().isoformat()
            if run.phase1_started_at else "—"
        )
        duration = (
            str(run.completed_at - run.phase1_started_at).split(".")[0]
            if (run.completed_at and run.phase1_started_at) else "—"
        )

        scope_payload = run.scope_jsonb or {
            "targets": [], "web_apps": [], "exclusions": [],
        }
        run_ctx = {
            "version": "1.0",
            "fecha_emision": fecha_emision,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_emision,
            "duration": duration,
            "categoria_ens": run.category,
            "mode": run.mode,
            "authorized_by": run.authorized_by or "",
            "authorization_signed_at": (
                run.authorization_signed_at.isoformat()
                if run.authorization_signed_at else ""
            ),
            "phase1_started_at": (
                run.phase1_started_at.isoformat() if run.phase1_started_at else ""
            ),
            "completed_at": (
                run.completed_at.isoformat() if run.completed_at else ""
            ),
            "total_findings": run.total_findings or 0,
            "confirmed_findings": run.confirmed_findings or 0,
            "scope": scope_payload,
            "targets_count": len(scope_payload.get("targets") or []),
            "tools_discovery": tools_discovery,
            "tools_verification": tools_verification,
            "attack_chain": scope_payload.get("attack_chain", []),
        }

        handoff_ctx = None
        if handoff:
            handoff_ctx = {
                "total_findings_received": handoff.total_findings_received or 0,
                "pentester": {
                    "name": handoff.external_pentester_name_cached()
                    if hasattr(handoff, "external_pentester_name_cached") else "",
                    "certification": "",
                    "email": "",
                    "company": "",
                },
                "handoff_date": (
                    handoff.created_at.date().isoformat()
                    if handoff.created_at else ""
                ),
                "kickoff_scheduled_at": (
                    handoff.kickoff_scheduled_at.isoformat()
                    if handoff.kickoff_scheduled_at else ""
                ),
                "execution_start": "",
                "execution_end": "",
                "report_received_at": (
                    handoff.report_received_at.isoformat()
                    if handoff.report_received_at else ""
                ),
                "authorization_signed_at": (
                    run.authorization_signed_at.isoformat()
                    if run.authorization_signed_at else ""
                ),
                "execution_window": "L-V 09:00-18:00 CET",
            }
            # Pentester info vive en VerificationRun (por diseno v5.1)
            handoff_ctx["pentester"]["name"] = run.external_pentester_name or ""
            handoff_ctx["pentester"]["certification"] = run.external_pentester_cert or ""
            handoff_ctx["pentester"]["email"] = run.external_pentester_email or ""

        probabilidad = (
            "alta" if score.score >= 75
            else "media" if score.score >= 50
            else "baja"
        )

        return {
            "cliente": cliente_ctx,
            "responsables": responsables_ctx,
            "proyecto": {
                "version_actual": "1.0",
                "codigo_documento_base": run.category,
            },
            "run": run_ctx,
            "score": score_dict,
            "heatmap": [c.to_dict() for c in heatmap_cells],
            "heatmap_summary": hm_summary,
            "delta": delta_payload,
            "findings_confirmed": findings_ctx,
            "findings_confirmed_count": len(findings_ctx),
            "findings_external": findings_external_ctx,
            "findings_priority": findings_priority_ctx,
            "handoff": handoff_ctx or {"total_findings_received": 0, "pentester": {}},
            "conclusion": {"probabilidad_certificacion": probabilidad},
        }

    # ─── Helpers ─────────────────────────────────────────────────────

    async def _load_findings(
        self, run_id: uuid.UUID,
    ) -> list[VerificationFinding]:
        stmt = select(VerificationFinding).where(
            VerificationFinding.run_id == run_id,
            VerificationFinding.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _load_handoff(
        self, run_id: uuid.UUID,
    ) -> ExternalPentesterHandoff | None:
        stmt = select(ExternalPentesterHandoff).where(
            ExternalPentesterHandoff.run_id == run_id,
            ExternalPentesterHandoff.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    def _finding_to_ctx(self, f: VerificationFinding) -> dict:
        sev = (f.severity or "info")
        port = f.affected_port
        host_port = (
            f"{f.affected_host}:{port}" if port else (f.affected_host or "")
        )
        service_disp = f.affected_service or "—"
        if f.affected_service and f.affected_service_version:
            service_disp = f"{f.affected_service} ({f.affected_service_version})"
        ens_list = list(f.ens_measures or [])
        ens_str = ", ".join(
            f"`{m.get('measure', '')}` ({m.get('title', '')})"
            for m in ens_list if isinstance(m, dict) and m.get("measure")
        ) or "—"
        mitre_list = list(f.mitre_techniques or [])
        mitre_str = ", ".join(
            f"{t.get('technique', '')} — {t.get('tactic', '')}"
            for t in mitre_list if isinstance(t, dict)
        )
        return {
            "finding_id": str(f.id),
            "finding_hash": f.finding_hash,
            "title": f.title,
            "description": f.description,
            "severity": sev,
            "severity_upper": sev.upper(),
            "classification": f.zfp_gate5_classification,
            "confidence_score": float(f.confidence_score or 0),
            "cve_id": f.cve_id,
            "cve_id_disp": f.cve_id or "—",
            "cvss_score": float(f.cvss_score) if f.cvss_score is not None else None,
            "cvss_score_disp": (
                str(float(f.cvss_score)) if f.cvss_score is not None else "—"
            ),
            "cwe_id": f.cwe_id,
            "cwe_id_disp": f.cwe_id or "—",
            "affected_host": f.affected_host,
            "affected_port": f.affected_port,
            "host_port_disp": host_port,
            "affected_service": f.affected_service,
            "service_disp": service_disp,
            "affected_service_version": f.affected_service_version,
            "affected_url": f.affected_url,
            "affected_url_disp": f.affected_url or "—",
            "affected_os": f.affected_os,
            "tool_sources": list(f.tool_sources or []),
            "tool_sources_str": ", ".join(f.tool_sources or []) or "—",
            "ens_measures": ens_list,
            "ens_measures_str": ens_str,
            "mitre_techniques": mitre_list,
            "mitre_str": mitre_str,
            "status": f.status,
        }

    # ─── Generacion ──────────────────────────────────────────────────

    async def generate_report(
        self,
        run_id: uuid.UUID,
        codigo: str,
        *,
        generate_pdf: bool = True,
        sign: bool = True,
        remediation_force_offline: bool = True,
    ) -> dict[str, Any]:
        """Genera un informe concreto (E-702 | E-703 | E-704)."""
        run = await self.db.get(VerificationRun, run_id)
        if not run:
            raise ValueError(f"VerificationRun {run_id} no existe")
        context = await self.build_context(
            run, remediation_force_offline=remediation_force_offline,
        )
        result = await self.docs.generate_document(
            project_id=run.project_id,
            template_codigo=codigo,
            context=context,
            generate_pdf=generate_pdf,
            sign=sign,
            generated_by="m08_verification_report_generator",
            enforce_gates=False,  # E-702/3/4 no tienen gate de DdA
        )
        return result

    async def generate_all_for_run(
        self,
        run_id: uuid.UUID,
        *,
        generate_pdf: bool = True,
        sign: bool = True,
        remediation_force_offline: bool = True,
    ) -> list[dict[str, Any]]:
        """Genera todos los informes aplicables al run.mode."""
        run = await self.db.get(VerificationRun, run_id)
        if not run:
            raise ValueError(f"VerificationRun {run_id} no existe")
        codes = REPORT_CODES_BY_MODE.get(run.mode, ["E-702", "E-703"])
        out = []
        for code in codes:
            r = await self.generate_report(
                run_id, code,
                generate_pdf=generate_pdf, sign=sign,
                remediation_force_offline=remediation_force_offline,
            )
            out.append(r)
        # Persiste score + delta en el run
        findings_all = await self._load_findings(run_id)
        score = calculate_score(findings_all)
        persist_score_to_run(run, score)
        if run.previous_run_id:
            prev_findings = await self._load_findings(run.previous_run_id)
            delta = compute_delta(prev_findings, findings_all)
            persist_delta_to_run(run, delta)
        await self.db.flush()
        return out
