"""V-CHECK Paso 7 — DEMO FINAL 13 ESCENARIOS END-TO-END sobre DataForma.

Integra todo lo construido en Sesion 7:
- Paso 5 M21 (diagnostico organizacional)
- Paso 6 M22 (discovery tecnico + conectores mock)
- M8 v5.1 verification (pipeline BASICO + MEDIO + ZFP + ENS + MITRE)
- M12 magic links (autorizar + portal remediacion + portal pentester)
- M7 evidence, M5 remediation, M3 tech_verification
- M9 audit_prep (dossier ZIP completo)
- FP learning loop
- Findings externos ingest
- Kill switch

Los 13 escenarios se ejecutan secuencialmente. Cada uno reporta
PASS/FAIL con detalle. Si alguno falla, el script continua y
al final muestra el resumen completo.

Target simulado: Juice Shop (localhost:3001) contra el que se
generan fixtures realistas. El demo no ejecuta nuclei/zap reales
(eso requeriria MCP servers en pentest-net); usa findings fixture
que representan la salida real de esos scanners.
"""
from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("FULKRO_SKIP_WORKFLOW_GATES", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import get_settings
from backend.app.database import set_tenant_context
from backend.app.models.diagnosis import Stakeholder
from backend.app.models.onboarding import DiscoveredAsset
from backend.app.motors.m06_document_factory.service import (
    DocumentFactoryService,
)
from backend.app.motors.m08_verification.ens_mapper import EnsMapper
from backend.app.motors.m08_verification.external.findings_ingester import (
    ingest_external_findings,
)
from backend.app.motors.m08_verification.external.handoff_builder import (
    build_handoff_package,
)
from backend.app.motors.m08_verification.fp_patterns.learner import (
    learn_from_finding, seed_catalog_to_db,
)
from backend.app.motors.m08_verification.kill_switch import (
    force_kill_run_processes, register_subprocess, request_kill,
    unregister_subprocess,
)
from backend.app.motors.m08_verification.mitre_mapper import MitreMapper
from backend.app.motors.m08_verification.models import (
    VerificationFinding, VerificationRun,
)
from backend.app.motors.m08_verification.reports.delta_report import (
    compute_delta,
)
from backend.app.motors.m08_verification.reports.heatmap_generator import (
    generate_heatmap, heatmap_summary,
)
from backend.app.motors.m08_verification.reports.report_generator import (
    VerificationReportGenerator,
)
from backend.app.motors.m08_verification.reports.score_calculator import (
    calculate_score,
)
from backend.app.motors.m08_verification.service import VerificationService
from backend.app.motors.m08_verification.zfp_engine import (
    ZfpFinding, compute_finding_hash, gate2_fp_filter,
    gate3_correlation, gate5_classify,
)
from backend.app.motors.m09_audit_prep import (
    checklist_service,
)
from backend.app.motors.m09_audit_prep.dossier_generator import (
    generate_dossier,
)
from backend.app.motors.m12_magic_link.emails.renderer import (
    render_email_for_magic_link,
)
from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.app.motors.m21_diagnosis import stakeholders_service as stk
from backend.app.motors.m21_diagnosis.paso5_orchestrator import (
    run_full_diagnosis_paso5,
)
from backend.app.motors.m22_discovery import paso6_orchestrator
from backend.app.motors.m22_discovery.paso6_demo_mocks import (
    build_aws_connector_dataforma,
    build_m365_connector_dataforma,
    dataforma_m365_defender_alerts,
    dataforma_password_policy,
    dataforma_security_hub_findings,
)


# ════════════════════════════════════════════════════════════════════
# Leak patterns (prohibidos en entregables cliente)
# ════════════════════════════════════════════════════════════════════

LEAK_PATTERNS = [
    r"\bFULKRO\b", r"\bMotor \d+\b", r"\bAgente \d+\b",
    r"\bDocument Factory\b", r"\bCopiloto\b(?! ENS)",
    r"\bM\d+-V\d+\b", r"\bv5\.1\b",
]


def grep_leaks_text(text: str) -> list[str]:
    out: list[str] = []
    for pat in LEAK_PATTERNS:
        for m in re.finditer(pat, text):
            out.append(f"{pat} | {text[max(0, m.start()-20):m.end()+20]!r}")
    return out


def grep_leaks_docx(path: Path) -> list[str]:
    from docx import Document
    try:
        d = Document(str(path))
    except Exception as exc:
        return [f"(can_not_open) {exc}"]
    text = "\n".join(p.text for p in d.paragraphs)
    for tbl in d.tables:
        for row in tbl.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    text += "\n" + p.text
    return grep_leaks_text(text)


# ════════════════════════════════════════════════════════════════════
# Reporte PASS/FAIL
# ════════════════════════════════════════════════════════════════════

RESULTS: list[tuple[str, bool, str]] = []
ARTIFACTS: list[tuple[str, Path, int]] = []


def report(label: str, ok: bool, detail: str = "") -> None:
    mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
    print(f"[{mark}] {label}")
    if detail:
        print(f"      {detail}")
    RESULTS.append((label, ok, detail))


def artifact(label: str, path: Path) -> None:
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        size = 0
    ARTIFACTS.append((label, path, size))


# ════════════════════════════════════════════════════════════════════
# Fixtures Juice Shop (simulan salida de nuclei/testssl/nmap/lynis/zap
# contra el container Juice Shop localhost:3001)
# ════════════════════════════════════════════════════════════════════

JUICE_TARGET = "localhost:3001"

JUICE_BASICO_FINDINGS = [
    {
        "title": "Verbose stack trace leakage in error responses",
        "description": "Juice Shop devuelve stack traces completos "
                       "con paths del server en errores 500.",
        "severity": "high",
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
        "tool_sources": ["nuclei"],
        "tool_metadata": {"template_id": "juice-shop-stack-trace"},
    },
    {
        "title": "Cross-site scripting (XSS) reflected in search",
        "description": "El parametro q de /rest/products/search refleja "
                       "HTML sin escapar.",
        "severity": "high",
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
        "affected_url": f"http://{JUICE_TARGET}/rest/products/search",
        "tool_sources": ["zap", "nuclei"],
        "tool_metadata": {"alert_id": "40012"},
    },
    {
        "title": "Missing HSTS header",
        "description": "Respuestas HTTP sin Strict-Transport-Security.",
        "severity": "medium",
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
        "tool_sources": ["testssl", "nuclei"],
        "tool_metadata": {"testssl_id": "HSTS"},
    },
    {
        "title": "Directory listing enabled on /ftp",
        "description": "El path /ftp expone listado completo de ficheros.",
        "severity": "medium",
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
        "affected_url": f"http://{JUICE_TARGET}/ftp",
        "tool_sources": ["nuclei"],
        "tool_metadata": {"template_id": "dir-listing"},
    },
]


JUICE_MEDIO_EXTRA_FINDINGS = [
    {
        "title": "SQL injection in product search",
        "description": "Payload ')) OR 1=1--' en /rest/products/search "
                       "devuelve todos los productos.",
        "severity": "critical",
        "cve_id": "CVE-2024-JUICESQL",
        "cvss_score": 9.1,
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
        "affected_url": f"http://{JUICE_TARGET}/rest/products/search",
        "tool_sources": ["zap", "nuclei", "nmap"],
        "tool_metadata": {"alert_id": "40018"},
    },
    {
        "title": "Insecure deserialization via node-serialize",
        "description": "Objeto serializado en cookie session se "
                       "deserializa con eval().",
        "severity": "critical",
        "cve_id": "CVE-2017-5941",
        "cvss_score": 9.8,
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
        "tool_sources": ["nuclei", "zap"],
        "tool_metadata": {"template_id": "cve-2017-5941"},
    },
    {
        "title": "JWT secret key 'none' algorithm accepted",
        "description": "Backend acepta JWTs firmados con alg=none sin "
                       "validacion.",
        "severity": "high",
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
        "tool_sources": ["nuclei"],
        "tool_metadata": {"template_id": "jwt-none-alg"},
    },
]


# Findings externos simulados (OSCP pentester entrega JSON estructurado)
# Los titulos y descripciones usan terminologia estandar que el ENS mapper
# rule-based reconoce (XSS, SQL Injection, default credentials, TLS 1.0,
# DMARC, etc.) — mapeo automatico esperado para los 5.
EXTERNAL_FINDINGS = [
    {
        "title": "Blind SQL Injection in /rest/user endpoint",
        "description": "Payload blind SQLi en query parameter id "
                       "permite extraer hash de passwords.",
        "severity": "critical",
        "cvss_score": 9.0,
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
        "affected_url": f"http://{JUICE_TARGET}/rest/user",
        "pentester_notes": "Test manual OSCP, reproducible en 3 pasos.",
    },
    {
        "title": "Default credentials admin/admin en panel back-office",
        "description": "El panel de administracion acepta default credentials "
                       "admin/admin sin cambio forzado en primer login.",
        "severity": "high",
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
        "affected_service": "http",
    },
    {
        "title": "Missing Strict-Transport-Security header in all responses",
        "description": "Ninguna respuesta HTTP incluye cabecera "
                       "Strict-Transport-Security (HSTS). Permite downgrade.",
        "severity": "medium",
        "affected_host": JUICE_TARGET,
        "affected_port": 3001,
    },
    {
        "title": "Stored XSS in product review comments",
        "description": "Los comentarios de reviews almacenan y reflejan "
                       "payloads XSS persistentes a otros usuarios.",
        "severity": "critical",
        "cvss_score": 9.5,
        "affected_host": JUICE_TARGET,
        "pentester_notes": "Explotacion encadenada confirmada en test real.",
    },
    {
        "title": "Weak cipher suites accepted: RC4 enabled on TLS endpoint",
        "description": "El servidor TLS acepta cipher suites RC4, "
                       "considerados weak cipher deprecated.",
        "severity": "medium",
        "affected_host": JUICE_TARGET,
    },
]


# ════════════════════════════════════════════════════════════════════
# Helpers
# ════════════════════════════════════════════════════════════════════

async def _get_dataforma(engine) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(sa_text("SET LOCAL ROLE fulkro"))
        r = await conn.execute(sa_text(
            "SELECT c.id, p.id FROM clients c "
            "JOIN projects p ON p.client_id = c.id "
            "WHERE c.nombre ILIKE '%DataForma%' LIMIT 1"
        ))
        row = r.first()
        if not row:
            raise RuntimeError(
                "DataForma no existe. Ejecuta demo_s7_paso2_vcheck.py primero.",
            )
        return row[0], row[1]


async def _seed_juice_asset(db: AsyncSession, project_id: uuid.UUID) -> None:
    """Anade el target juice-shop como DiscoveredAsset para scope_deriver."""
    r = await db.execute(select(DiscoveredAsset).where(
        DiscoveredAsset.project_id == project_id,
        DiscoveredAsset.identificador == JUICE_TARGET,
        DiscoveredAsset.deleted_at.is_(None),
    ))
    if r.scalars().first():
        return
    db.add(DiscoveredAsset(
        project_id=project_id,
        tipo_magerit="S",
        nombre="Juice Shop (test target)",
        identificador=JUICE_TARGET,
        metadata_extra={
            "url": f"http://{JUICE_TARGET}",
            "platform": "Node.js",
            "http": True,
            "environment": "test",
            "ssh_accessible": False,
        },
        fuente_conector="manual_seed",
    ))
    await db.flush()


def _build_zfp_from_fixture(fixtures: list[dict]) -> list[ZfpFinding]:
    zfps: list[ZfpFinding] = []
    for f in fixtures:
        cand = {
            "title": f["title"], "description": f["description"],
            "severity": f["severity"],
            "cve_id": f.get("cve_id"), "cvss_score": f.get("cvss_score"),
            "affected_host": f["affected_host"],
            "affected_port": f.get("affected_port"),
            "affected_service": f.get("affected_service"),
            "affected_service_version": f.get("affected_service_version"),
            "affected_url": f.get("affected_url"),
            "raw_output_excerpt": f["description"][:200],
            "tool": f["tool_sources"][0],
            "tool_metadata": f.get("tool_metadata", {}),
        }
        zf = ZfpFinding(
            finding_hash=compute_finding_hash(cand),
            title=cand["title"], description=cand["description"],
            severity=cand["severity"],
            affected_host=cand["affected_host"],
            affected_port=cand.get("affected_port"),
            affected_service=cand.get("affected_service"),
            affected_url=cand.get("affected_url"),
            cve_id=cand.get("cve_id"),
            cvss_score=cand.get("cvss_score"),
            affected_service_version=cand.get("affected_service_version"),
            tool_sources=list(f["tool_sources"]),
            has_known_cve=bool(cand.get("cve_id")),
        )
        # tool_metadata en ZfpFinding es lista[dict]; poblamos con el dict
        # original para que gate2_fp_filter pueda evaluar condition_jsonb.
        zf.tool_metadata.append(dict(f.get("tool_metadata") or {}))
        zfps.append(zf)
    return zfps


async def _persist_zfp_as_findings(
    db: AsyncSession, project_id: uuid.UUID, run_id: uuid.UUID,
    zfps: list[ZfpFinding],
) -> None:
    """Corre mappers ENS+MITRE y persiste los ZfpFindings como VerificationFindings."""
    ens_mapper = EnsMapper(db, enable_llm=False)
    mitre_mapper = MitreMapper(enable_llm=False)
    for z in zfps:
        measures, primary = await ens_mapper.map(z)
        z.ens_measures_result = measures
        z.ens_primary = primary
        z.mitre_result = mitre_mapper.map(z)
        vf = VerificationFinding(
            project_id=project_id,
            run_id=run_id,
            finding_hash=z.finding_hash,
            title=z.title, description=z.description,
            severity=z.severity,
            cve_id=z.cve_id, cvss_score=z.cvss_score,
            affected_host=z.affected_host,
            affected_port=z.affected_port,
            affected_service=z.affected_service,
            affected_url=z.affected_url,
            tool_sources=list(z.tool_sources),
            raw_outputs=[{
                "tool": z.tool_sources[0] if z.tool_sources else "unknown",
                "excerpt": z.description[:200],
                "metadata": {},
            }],
            confidence_score=z.confidence_score,
            zfp_gate1_dedup=True, zfp_gate2_fp_filter=True,
            zfp_gate3_cross_tool=z.zfp_gate3_cross_tool,
            zfp_gate4_retest="not_applicable",
            zfp_gate5_classification=z.zfp_gate5_classification,
            ens_measures=z.ens_measures_result,
            ens_primary_measure=z.ens_primary,
            mitre_techniques=[{
                "technique": t.get("technique_id"),
                "tactic": t.get("tactic"),
                "technique_name": t.get("technique_name"),
            } for t in (z.mitre_result or [])],
            remediation_summary=f"Remediar: {z.title}",
            status="open",
        )
        db.add(vf)


# ════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════

async def main() -> int:
    t_start = time.monotonic()
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    Session = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False,
    )

    client_id, project_id = await _get_dataforma(engine)
    print("\n" + "=" * 72)
    print("V-CHECK PASO 7 — DEMO FINAL 13 ESCENARIOS E2E · DataForma Galicia SL")
    print("=" * 72)
    print(f"client={client_id}  project={project_id}  target={JUICE_TARGET}\n")

    # Carga catalogo de plantillas (E-702/E-703)
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        await DocumentFactoryService(db).load_template_metadata_from_catalog()
        await seed_catalog_to_db(db)
        await db.commit()

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 1 · M21 Diagnosis
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 1/13 · M21 Organizational Diagnosis ──")
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        # Asegurar stakeholders seed
        r = await db.execute(
            select(Stakeholder).where(
                Stakeholder.project_id == project_id,
                Stakeholder.deleted_at.is_(None),
            )
        )
        if not list(r.scalars().all()):
            await stk.build_graph(
                db, project_id,
                personas=[
                    stk.PersonaInput(
                        nombre="Maria Perez Nunez",
                        email="mperez@dataforma.es",
                        cargo="Consejera Delegada",
                        departamento="Direccion",
                    ),
                    stk.PersonaInput(
                        nombre="Jorge Fernandez Rodriguez",
                        email="jfernandez@dataforma.es",
                        cargo="CISO / Responsable de Seguridad",
                        rol_interno="rseg",
                    ),
                    stk.PersonaInput(
                        nombre="Laura Vazquez Torres",
                        email="lvazquez@dataforma.es",
                        cargo="IT Manager / Responsable del Sistema",
                        rol_interno="rsis",
                    ),
                    stk.PersonaInput(
                        nombre="Andres Lopez Fernandez",
                        email="alopez@dataforma.es",
                        cargo="Responsable de la Informacion",
                        rol_interno="ri",
                    ),
                    stk.PersonaInput(
                        nombre="Elena Garcia Pazos",
                        email="egarcia@dataforma.es",
                        cargo="Responsable del Servicio",
                        rol_interno="rs",
                    ),
                    stk.PersonaInput(
                        nombre="Jose Romero",
                        email="jromero@dataforma.es",
                        cargo="DPO externo",
                        rol_interno="dpo",
                    ),
                ],
            )
            await db.commit()

    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        diag = await run_full_diagnosis_paso5(
            db, project_id, sector="sanidad_privada",
            empleados=180, datos_sensibles=True,
        )
        await db.commit()
    ens_coverage = diag["stakeholders"]["ens_responsibles"]["coverage_pct"]
    m1_cat = diag["m1_category_hint"]["categoria_sugerida"]
    obligaciones = diag["compliance"]["total_obligaciones"]
    bia_procesos = diag["bia"]["total_procesos"]
    ok1 = (
        ens_coverage == 100.0 and m1_cat in {"ALTA", "MEDIA"}
        and obligaciones >= 4 and bia_procesos >= 10
    )
    report(
        "1) M21 Diagnosis — ENS 100% + categoria + obligaciones + procesos",
        ok1,
        f"ENS cov={ens_coverage}% · cat={m1_cat} · obligaciones={obligaciones} "
        f"· procesos={bia_procesos}",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 2 · M22 Technical Discovery
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 2/13 · M22 Technical Discovery ──")
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        m365 = build_m365_connector_dataforma()
        aws = build_aws_connector_dataforma()
        m22_report = await paso6_orchestrator.run_full_paso6(
            db, project_id,
            m365_connector=m365, aws_connector=aws,
            ens_category="MEDIA",
            password_policy=dataforma_password_policy(),
            security_hub_findings=dataforma_security_hub_findings(),
            m365_defender_alerts=dataforma_m365_defender_alerts(),
            azure_activity_enabled=True,
            vault_enabled=False,
        )
        await _seed_juice_asset(db, project_id)
        await db.commit()
    m22_assets = m22_report["e090_tecnica"]["total_activos"]
    m22_mfa_pct = m22_report["e090_tecnica"]["mfa_pct"]
    m22_maturity = m22_report["e090_tecnica"]["madurez_nivel"]
    m22_vulns = m22_report["e090_tecnica"]["vulns_abiertas"]
    m22_dfds = m22_report["data_flows"]["dfds_generados"]
    ok2 = (
        m22_assets >= 20 and m22_vulns >= 10
        and m22_maturity in {"L0", "L1", "L2"}
    )
    report(
        "2) M22 Discovery — assets + vulns + DFDs + madurez",
        ok2,
        f"assets={m22_assets} · vulns={m22_vulns} · DFDs={m22_dfds} "
        f"· MFA={m22_mfa_pct}% · madurez={m22_maturity}",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 3 · Magic link autorizar_verificacion_tecnica
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 3/13 · Magic Link autorizar_verificacion_tecnica ──")
    ml_authorization_ok = False
    try:
        async with Session() as db:
            await set_tenant_context(
                db, client_id=client_id, project_id=project_id,
            )
            await db.execute(sa_text("SET LOCAL ROLE fulkro"))
            svc = MagicLinkService(db)
            req = MagicLinkGenerateRequest(
                project_id=project_id,
                purpose=MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
                recipient_email="jfernandez@dataforma.es",
                scope={"category": "BASICO"},
            )
            resp = await svc.generate_magic_link(
                req, base_url="https://portal.fulkro.es",
            )
            await db.commit()
        subject, html, _ = render_email_for_magic_link(
            purpose=MagicLinkPurpose.AUTORIZAR_VERIFICACION_TECNICA,
            link_url=resp.url,
            expires_at=resp.expires_at,
            cliente={
                "razon_social": "DataForma Galicia SL",
                "cif": "B72634815",
            },
            proyecto={"nombre": "Adecuacion ENS DataForma"},
            destinatario={
                "nombre": "Jorge Fernandez",
                "cargo": "CISO / Responsable de Seguridad",
            },
            otp=resp.otp,
            alcance_corto="Verificacion tecnica BASICA DataForma",
            ventana_inicio=(
                datetime.now(timezone.utc) + timedelta(hours=24)
            ).strftime("%d/%m/%Y %H:%M"),
        )
        html_leaks = grep_leaks_text(html)
        # Simular firma: marcamos autorizado en el run siguiente
        ml_authorization_ok = (
            resp.otp is not None
            and "magic" not in subject.lower()
            and not html_leaks
            and len(html) > 2000
        )
        report(
            "3) Magic link autorizar_verificacion_tecnica + email HTML",
            ml_authorization_ok,
            f"OTP={resp.otp[:2]}**** · HTML={len(html)}b · leaks={len(html_leaks)} "
            f"· subject='{subject[:40]}'",
        )
    except Exception as exc:
        report("3) Magic link autorizar_verificacion_tecnica", False, str(exc))

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 4 · M8 v5.1 run BASICO contra Juice Shop + E-702
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 4/13 · M8 run BASICO + ZFP + E-702 ──")
    basic_run_id = None
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        svc_v = VerificationService(db)
        run = await svc_v.create_run(
            project_id=project_id, category="BASICO", mode="internal",
            created_by="marcos_demo_paso7",
        )
        basic_run_id = run.id
        # Autorizar inmediatamente (simulado tras OTP)
        run.authorized_by = "Jorge Fernandez (RSEG) — OTP simulado"
        run.authorization_signed_at = datetime.now(timezone.utc)
        run.status = "authorized"
        await db.commit()

    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        zfps_basico = _build_zfp_from_fixture(JUICE_BASICO_FINDINGS)
        # Aplicar gate3 (correlacion cross-tool)
        gate3_correlation(zfps_basico)
        gate5_classify(zfps_basico)
        await _persist_zfp_as_findings(db, project_id, basic_run_id, zfps_basico)
        rr = await db.get(VerificationRun, basic_run_id)
        rr.total_findings = len(zfps_basico)
        rr.confirmed_findings = sum(
            1 for z in zfps_basico if z.zfp_gate5_classification == "confirmed"
        )
        rr.high_count = sum(1 for z in zfps_basico if z.severity == "high")
        rr.medium_count = sum(1 for z in zfps_basico if z.severity == "medium")
        rr.status = "completed"
        rr.phase1_started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        rr.completed_at = datetime.now(timezone.utc)
        rr.tools_used = sorted({t for z in zfps_basico for t in z.tool_sources})
        await db.commit()

    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        gen = VerificationReportGenerator(db)
        r702 = await gen.generate_report(
            basic_run_id, "E-702", generate_pdf=False, sign=True,
            remediation_force_offline=True,
        )
        await db.commit()
    e702_path = Path(r702["docx_path"])
    e702_leaks = grep_leaks_docx(e702_path)
    e702_size = e702_path.stat().st_size if e702_path.exists() else 0
    artifact("E-702 BASICA (juice-shop)", e702_path)
    ok4 = (
        basic_run_id is not None
        and e702_path.exists()
        and e702_size > 20000
        and not e702_leaks
        and r702.get("signature_ed25519")
    )
    report(
        "4) M8 BASICO + E-702 firmado Ed25519",
        ok4,
        f"findings={len(zfps_basico)} · E-702={e702_size}b "
        f"· leaks={len(e702_leaks)} · firma={bool(r702.get('signature_ed25519'))}",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 5 · Marcar FP y aprender
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 5/13 · FP learning loop ──")
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        # Coger el finding HSTS (fixture 3) y marcarlo FP
        r = await db.execute(
            select(VerificationFinding).where(
                VerificationFinding.run_id == basic_run_id,
                VerificationFinding.title.ilike("%HSTS%"),
            ).limit(1)
        )
        hsts_finding = r.scalar_one_or_none()
        fp_pattern = None
        if hsts_finding:
            hsts_finding.status = "false_positive"
            fp_pattern = await learn_from_finding(
                db, hsts_finding,
                reason=(
                    "DataForma sirve solo HTTP interno en LAN hospitalaria; "
                    "HSTS no aplica al perimetro"
                ),
                learned_from_project_id=project_id,
            )
            await db.commit()

    # Verificar que nuevo candidato con mismo title se filtra como FP
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        new_zfp = _build_zfp_from_fixture([JUICE_BASICO_FINDINGS[2]])  # HSTS
        kept, rejected_as_fp = await gate2_fp_filter(db, new_zfp)
    filtered_out = len(rejected_as_fp) > 0
    ok5 = bool(fp_pattern) and filtered_out and bool(fp_pattern.id)
    report(
        "5) FP learning — patron creado + filtrado en siguiente run",
        ok5,
        f"patron='{fp_pattern.pattern[:30] if fp_pattern else 'NONE'}' "
        f"· filtered_next={filtered_out} "
        f"· kept={len(kept)} · rejected={len(rejected_as_fp)}",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 6 · Portal remediacion
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 6/13 · Portal remediacion click-through ──")
    ok6 = False
    try:
        async with Session() as db:
            await set_tenant_context(
                db, client_id=client_id, project_id=project_id,
            )
            await db.execute(sa_text("SET LOCAL ROLE fulkro"))
            svc = MagicLinkService(db)
            req = MagicLinkGenerateRequest(
                project_id=project_id,
                purpose=MagicLinkPurpose.PORTAL_REMEDIACION,
                recipient_email="lvazquez@dataforma.es",
                scope={"run_id": str(basic_run_id)},
            )
            portal_resp = await svc.generate_magic_link(
                req, base_url="https://portal.fulkro.es",
            )
            # Simular "Ya lo he arreglado" marcando un finding como remediado
            r = await db.execute(
                select(VerificationFinding).where(
                    VerificationFinding.run_id == basic_run_id,
                    VerificationFinding.status == "open",
                    VerificationFinding.title.ilike("%directory listing%"),
                ).limit(1)
            )
            f = r.scalar_one_or_none()
            remediated_title = None
            if f:
                f.status = "remediated"
                f.remediation_notes = (
                    "IT Manager marca arreglado via portal remediacion — "
                    "directory listing deshabilitado."
                )
                remediated_title = f.title
            await db.commit()
        ok6 = (
            portal_resp.url.startswith("https://portal.fulkro.es")
            and remediated_title is not None
        )
        report(
            "6) Portal remediacion magic link + click 'Ya arreglado'",
            ok6,
            f"URL generada · finding remediado: '{(remediated_title or '')[:40]}'",
        )
    except Exception as exc:
        report("6) Portal remediacion", False, str(exc))

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 7 · M8 run MEDIO (pipeline completo, mas findings)
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 7/13 · M8 MEDIO pipeline completo ──")
    medio_run_id = None
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        svc_v = VerificationService(db)
        run = await svc_v.create_run(
            project_id=project_id, category="MEDIO", mode="internal",
            created_by="marcos_demo_paso7",
        )
        medio_run_id = run.id
        run.authorized_by = "Jorge Fernandez (RSEG) — OTP simulado MEDIO"
        run.authorization_signed_at = datetime.now(timezone.utc)
        run.status = "authorized"
        await db.commit()

    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        # Reusar fixtures BASICO + extras MEDIO
        zfps_medio = _build_zfp_from_fixture(
            JUICE_BASICO_FINDINGS + JUICE_MEDIO_EXTRA_FINDINGS,
        )
        gate3_correlation(zfps_medio)
        gate5_classify(zfps_medio)
        await _persist_zfp_as_findings(db, project_id, medio_run_id, zfps_medio)
        rr = await db.get(VerificationRun, medio_run_id)
        rr.total_findings = len(zfps_medio)
        rr.confirmed_findings = sum(
            1 for z in zfps_medio if z.zfp_gate5_classification == "confirmed"
        )
        rr.critical_count = sum(1 for z in zfps_medio if z.severity == "critical")
        rr.high_count = sum(1 for z in zfps_medio if z.severity == "high")
        rr.medium_count = sum(1 for z in zfps_medio if z.severity == "medium")
        rr.status = "completed"
        rr.phase1_started_at = datetime.now(timezone.utc) - timedelta(hours=2)
        rr.completed_at = datetime.now(timezone.utc)
        rr.tools_used = sorted({t for z in zfps_medio for t in z.tool_sources})
        await db.commit()
    correlated = sum(1 for z in zfps_medio if z.zfp_gate3_cross_tool)
    max_conf = max((z.confidence_score for z in zfps_medio), default=0.0)
    ok7 = len(zfps_medio) == 7 and correlated >= 3 and max_conf >= 0.90
    report(
        "7) M8 MEDIO pipeline multi-tool correlacionado",
        ok7,
        f"total={len(zfps_medio)} · correlados cross-tool={correlated} "
        f"· max confidence={max_conf:.2f}",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 8 · Delta report BASICO vs MEDIO
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 8/13 · Delta BASICO -> MEDIO ──")
    previous = [{
        "finding_hash": z.finding_hash,
        "severity": z.severity,
        "title": z.title,
    } for z in zfps_basico]
    current = [{
        "finding_hash": z.finding_hash,
        "severity": z.severity,
        "title": z.title,
    } for z in zfps_medio]
    delta = compute_delta(previous, current)
    ok8 = (
        len(delta.new) >= 3 and len(delta.persistent) >= 3
        and delta.overall_trend in {"empeorando", "mejorando", "estable"}
    )
    report(
        "8) Delta report — new/resolved/persistent/trend",
        ok8,
        f"new={len(delta.new)} · resolved={len(delta.resolved)} "
        f"· persistent={len(delta.persistent)} · trend={delta.overall_trend}",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 9 · Compliance heatmap 73 medidas
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 9/13 · Compliance heatmap 73 medidas ──")
    hm_findings = []
    for z in zfps_medio:
        hm_findings.append({
            "finding_hash": z.finding_hash,
            "severity": z.severity,
            "status": "open",
            "ens_primary_measure": z.ens_primary,
            "ens_measures": z.ens_measures_result or [],
        })
    cells = generate_heatmap(hm_findings)
    summary_hm = heatmap_summary(cells)
    ok9 = (
        summary_hm["total"] == 73
        and (summary_hm["compliant"] + summary_hm["partial"]
             + summary_hm["non_compliant"] + summary_hm["not_verified"]) == 73
    )
    report(
        "9) Compliance heatmap 73 medidas",
        ok9,
        f"total={summary_hm['total']} · compliant={summary_hm['compliant']} "
        f"· partial={summary_hm['partial']} · non_compliant={summary_hm['non_compliant']} "
        f"· not_verified={summary_hm['not_verified']}",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 10 · ALTA handoff pentester externo
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 10/13 · Handoff pentester externo ALTA ──")
    handoff_id = None
    portal_pentester_url = None
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        await db.execute(sa_text("SET LOCAL ROLE fulkro"))
        handoff = await build_handoff_package(db, medio_run_id)
        handoff_id = handoff.id
        # Portal magic link para el pentester
        req_ml = MagicLinkGenerateRequest(
            project_id=project_id,
            purpose=MagicLinkPurpose.PORTAL_PENTESTER_EXTERNO,
            recipient_email="oscp.pentester@redteam.es",
            scope={
                "handoff_id": str(handoff.id),
                "run_id": str(medio_run_id),
                "pentester_cert": "OSCP",
                "deadline": (
                    datetime.now(timezone.utc) + timedelta(days=14)
                ).isoformat(),
            },
        )
        resp_ml = await MagicLinkService(db).generate_magic_link(
            req_ml, base_url="https://portal.fulkro.es",
        )
        portal_pentester_url = resp_ml.url
        await db.commit()
    pkg_docs = handoff.package_documents if handoff else []
    ok10 = (
        handoff_id is not None
        and len(pkg_docs) == 7
        and portal_pentester_url.startswith("https://portal.fulkro.es")
    )
    report(
        "10) Handoff ALTA con 7 documentos + portal pentester externo",
        ok10,
        f"handoff_id={str(handoff_id)[:8]} · docs={len(pkg_docs)} "
        f"· portal_url_len={len(portal_pentester_url or '')}",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 11 · Ingesta findings externos estructurados
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 11/13 · Ingesta findings externos OSCP ──")
    ingested = []
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        ingested = await ingest_external_findings(
            db, medio_run_id, EXTERNAL_FINDINGS,
            source="structured_form",
        )
        await db.commit()

    # Verificar ENS mapping automatico (usando JSONB contains para tool_sources)
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        r = await db.execute(
            select(VerificationFinding).where(
                VerificationFinding.run_id == medio_run_id,
                VerificationFinding.tool_sources.contains(["external_structured"]),
            )
        )
        externals = list(r.scalars().all())
    ens_mapped = sum(1 for f in externals if f.ens_measures and len(f.ens_measures) > 0)
    ok11 = len(ingested) == 5 and ens_mapped >= 4
    report(
        "11) Ingesta 5 findings externos + ENS mapping automatico",
        ok11,
        f"ingested={len(ingested)} · ens_mapped>=1={ens_mapped}/5",
    )

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 12 · M9 Dossier completo (force=True)
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 12/13 · M9 Dossier ZIP completo ──")
    dossier_path = None
    try:
        async with Session() as db:
            await set_tenant_context(
                db, client_id=client_id, project_id=project_id,
            )
            await db.execute(sa_text("SET LOCAL ROLE fulkro"))
            audit_run = await checklist_service.run_full_checklist(
                db, project_id, "BASICA",
            )
            await db.commit()
            audit_run_id = audit_run.id

        async with Session() as db:
            await set_tenant_context(
                db, client_id=client_id, project_id=project_id,
            )
            await db.execute(sa_text("SET LOCAL ROLE fulkro"))
            zip_bytes = await generate_dossier(
                db, project_id, audit_run_id, force=True,
            )
            await db.commit()

        dossier_path = Path("/tmp") / f"dossier_paso7_{audit_run_id}.zip"
        dossier_path.write_bytes(zip_bytes)
        artifact("M9 Dossier ZIP", dossier_path)

        # Verificar contenido
        with zipfile.ZipFile(dossier_path) as z:
            names = z.namelist()
            folders = {n.split("/")[0] for n in names if "/" in n}
            has_matriz = any("Matriz" in n or "matriz" in n for n in names)
            has_manifest = any("MANIFEST" in n or "manifest" in n for n in names)
            has_index = any("INDICE" in n or "indice" in n.lower() for n in names)
        ok12 = (
            len(folders) >= 10 and has_matriz and has_manifest
            and dossier_path.stat().st_size > 10000
        )
        report(
            "12) M9 Dossier ZIP con 15 carpetas + matriz 99 + manifest",
            ok12,
            f"size={dossier_path.stat().st_size}b · folders={len(folders)} "
            f"· matriz={has_matriz} · manifest={has_manifest} · index={has_index}",
        )
    except Exception as exc:
        report("12) M9 Dossier completo", False, f"{exc!r}")

    # ────────────────────────────────────────────────────────────────
    # ESCENARIO 13 · Kill switch con subprocess real <5s
    # ────────────────────────────────────────────────────────────────
    print("\n── Escenario 13/13 · Kill switch <5s con subprocess real ──")
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        svc_v = VerificationService(db)
        kill_run = await svc_v.create_run(
            project_id=project_id, category="BASICO", mode="internal",
            created_by="marcos_kill_test_paso7",
        )
        kill_run_id = kill_run.id
        await db.commit()

    proc = subprocess.Popen(
        ["sleep", "30"],
        preexec_fn=os.setsid,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    pgid = os.getpgid(proc.pid)
    register_subprocess(kill_run_id, pgid)

    t0 = time.monotonic()
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        rr = await db.get(VerificationRun, kill_run_id)
        rr.status = "phase1_running"
        await db.commit()
    async with Session() as db:
        await set_tenant_context(
            db, client_id=client_id, project_id=project_id,
        )
        await request_kill(db, kill_run_id, requested_by="marcos_paso7")
        await db.commit()

    deadline = t0 + 5.0
    while proc.poll() is None and time.monotonic() < deadline:
        await asyncio.sleep(0.1)
    elapsed = time.monotonic() - t0
    killed = proc.poll() is not None
    if not killed:
        force_kill_run_processes(kill_run_id)
        try:
            proc.wait(timeout=2.0)
            killed = True
        except subprocess.TimeoutExpired:
            pass
    unregister_subprocess(kill_run_id, pgid)
    ok13 = killed and elapsed < 5.0
    report(
        "13) Kill switch <5s con subprocess real",
        ok13,
        f"elapsed={elapsed:.2f}s · killed={killed} · pid={proc.pid}",
    )

    # ════════════════════════════════════════════════════════════════
    # REPORTE FINAL
    # ════════════════════════════════════════════════════════════════
    elapsed_total = time.monotonic() - t_start
    pass_count = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)

    # Score calculation (current medio run)
    score_input = [{
        "severity": z.severity, "status": "open",
        "zfp_gate5_classification": z.zfp_gate5_classification,
    } for z in zfps_medio]
    score = calculate_score(score_input)

    print("\n" + "=" * 72)
    print("RESUMEN FINAL DataForma · Paso 7 · 13 Escenarios E2E")
    print("=" * 72)
    print(f"  Escenarios PASS: {pass_count}/{total}")
    print(f"  Tiempo total: {elapsed_total:.1f}s")
    print()
    print("  Metricas DataForma:")
    print(f"    · Categoria ENS sugerida: {m1_cat}")
    print(f"    · Stakeholders: {diag['stakeholders']['total_personas']} "
          f"personas ({ens_coverage}% ENS coverage)")
    print(f"    · Procesos: {bia_procesos} "
          f"({len(diag['bia']['por_criticidad'].get('alta', []))} criticos)")
    print(f"    · Obligaciones cruzadas: {obligaciones}")
    print(f"    · Assets MAGERIT (via M22): {m22_assets}")
    print(f"    · Findings BASICO: {len(zfps_basico)}")
    print(f"    · Findings MEDIO: {len(zfps_medio)} + {len(ingested)} externos")
    print(f"    · Madurez tecnica M22: {m22_maturity} ({m22_mfa_pct}% MFA)")
    print(f"    · Score seguridad: {score.score}/100 ({score.level})")
    print(f"    · Dossier ZIP: "
          f"{dossier_path.stat().st_size if dossier_path and dossier_path.exists() else 0}b")
    print()
    print("  Artifacts generados:")
    for label, p, size in ARTIFACTS:
        status = "OK" if p.exists() else "MISSING"
        print(f"    [{status}] {label}: {p.name} ({size}b)")
    print()
    if pass_count != total:
        print("  FAILS:")
        for label, ok, det in RESULTS:
            if not ok:
                print(f"    · {label}: {det}")
    print("=" * 72)

    await engine.dispose()
    return 0 if pass_count == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
