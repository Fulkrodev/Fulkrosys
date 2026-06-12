"""SIMULACIÓN HIPERREALISTA · Cliente ENS MEDIA (ruta certificación ENAC).

Recorre el ciclo MEDIA admin+cliente+AUDITOR, ejercitando el código real. Incluye
lo que la BÁSICA no tiene: ruta de certificación ENAC, promoción de NC (E-321/
E-322 → AuditFinding + PAC), distintivo CCN-STIC 809 + slot del certificado de la
entidad acreditada, y el PORTAL DEL AUDITOR (vías httpx · magic-link AUDITOR_PORTAL_ENAC).
EXCEPTO pentest OSCP. Vuelca a out/sim_media/ + asegura invariantes.
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text as sa_text

from backend.app.motors.m12_magic_link.purposes import MagicLinkPurpose
from backend.app.motors.m12_magic_link.schemas import MagicLinkGenerateRequest
from backend.app.motors.m12_magic_link.service import MagicLinkService
from backend.tests.conftest import _admin_setup
from backend.tests.integration.test_sim_basica import (
    _docx_text_from_path,
    _seed,
)

_OUT = Path(__file__).resolve().parents[3] / "out" / "sim_media"


def _dump(name: str, text: str) -> None:
    try:  # best-effort (CI · directorio puede no ser escribible)
        _OUT.mkdir(parents=True, exist_ok=True)
        (_OUT / name).write_text(text, encoding="utf-8")
    except OSError:
        pass


@pytest.mark.asyncio
async def test_sim_media_full_lifecycle(db, async_client, monkeypatch):
    monkeypatch.setenv("FULKRO_SKIP_WORKFLOW_GATES", "1")
    report: list[str] = ["# SIMULACIÓN MEDIA · Ayuntamiento de Villaverde del Río (ruta ENAC)\n"]

    def log(m: str) -> None:
        report.append(m)

    cid, pid, sid = await _seed(db, cat="MEDIA")
    log("## 1. Alta + categorización MEDIA\n")

    # Categorización → MEDIA
    from backend.app.motors.m01_categorization.service import CategorizationService
    res = await CategorizationService(db).compute_for_system(sid)
    categoria = res.category if hasattr(res, "category") else res.categoria
    assert str(categoria).upper().endswith("MEDIA"), categoria
    async with _admin_setup(db):
        await db.execute(sa_text(
            "UPDATE projects SET fecha_kickoff=current_date - interval '90 days', "
            "fecha_objetivo_certificacion=current_date + interval '30 days' WHERE id=:p"),
            {"p": str(pid)})
        await db.execute(sa_text(
            "INSERT INTO categorizations (id, system_id, categoria_resultante, aprobado_por, "
            "fecha_acta, created_at) VALUES (gen_random_uuid(), :s, 'MEDIA', "
            "'Comité de Seguridad', current_date, now())"), {"s": str(sid)})

    # DdA MEDIA + freeze + implantada
    from backend.app.motors.m03_dda.enums import CategoriaSistema
    from backend.app.motors.m03_dda.service import DdaService
    await DdaService(db).generate_dda(pid, CategoriaSistema("MEDIA"),
                                      responsable="Beatriz Seguridad López", enforce_gates=False)
    counts = (await db.execute(sa_text(
        "SELECT count(*) FILTER (WHERE aplicabilidad <> 'no_aplica') FROM dda_entries "
        "WHERE project_id=:p AND deleted_at IS NULL"), {"p": str(pid)})).scalar()
    log(f"## 2. DdA MEDIA · {counts} medidas aplicables (Anexo II · incluye refuerzos).\n")
    assert 60 <= int(counts) <= 73, f"MEDIA aplicables={counts}"
    await db.execute(sa_text(
        "UPDATE dda_entries SET estado_implementacion='implantada', "
        "aprobado_por='Beatriz Seguridad López', fecha_aprobacion=current_date "
        "WHERE project_id=:p AND aplicabilidad <> 'no_aplica'"), {"p": str(pid)})
    await db.flush()

    # E-040
    from backend.app.motors.m06_document_factory.informe_final_generator import (
        build_informe_final_context,
    )
    from backend.app.motors.m06_document_factory.service import DocumentFactoryService
    svc = DocumentFactoryService(db)
    await svc.load_template_metadata_from_catalog()
    e040_ctx = await build_informe_final_context(db, pid)
    e040 = await svc.generate_document(project_id=pid, template_codigo="E-040",
                                       context=e040_ctx, generate_pdf=False, sign=False,
                                       generated_by="sim")
    e040_text = _docx_text_from_path(e040["docx_path"])
    _dump("E-040_informe_final.txt", e040_text)
    assert "{{" not in e040_text
    log(f"## 3. E-040 · cumplimiento global {e040_ctx['informe']['cumplimiento_global']}%\n")

    # 4. NC de auditoría externa (E-321 + E-322) → promoción estructurada
    actor = uuid.uuid4()
    from backend.app.models.live_record import LiveRecord
    db.add(LiveRecord(project_id=pid, register_type="E-321", status="active",
                      created_by=actor, updated_by=actor, entry_data={
        "codigo_auditoria_ext": "AENOR-2026-114", "entidad_acreditada": "AENOR (ENAC 125/C-SI)",
        "fecha_inicio": "2026-05-04", "fecha_fin": "2026-05-08",
        "categoria_ens_evaluada": "MEDIA", "alcance": "Sede electrónica",
        "resultado": "conforme_con_observaciones"}))
    db.add(LiveRecord(project_id=pid, register_type="E-322", status="active",
                      created_by=actor, updated_by=actor, entry_data={
        "codigo_hallazgo": "NC-2026-01", "auditoria_codigo": "AENOR-2026-114",
        "severidad": "mayor", "medida_ens_afectada": "op.exp.8",
        "descripcion": "Retención de logs inferior a 12 meses",
        "accion_correctiva": "Ampliar la retención de logs a 12 meses",
        "responsable": "RSEG", "fecha_compromiso": "2026-06-15", "estado": "abierto"}))
    await db.flush()
    from backend.app.motors.m_live_records.nc_promotion import (
        list_structured_ncs, promote_audit_ncs,
    )
    promo = await promote_audit_ncs(db, pid)
    ncs = await list_structured_ncs(db, pid)
    log(f"## 4. NC auditoría externa → estructurada\n"
        f"Sesiones: {promo['sessions_promoted']} · NC: {promo['findings_promoted']} · "
        f"PAC violaciones: {len(promo['pac_violations'])}\n")
    assert promo["findings_promoted"] == 1
    assert ncs[0]["severidad"] == "mayor"
    assert ncs[0]["medida_afectada"] == "op.exp.8"
    _dump("NC_estructuradas.txt", str(ncs))

    # 5. Conformidad MEDIA: ruta certificación → CONFORMANT → distintivo 809 + cert externo
    from backend.app.models.conformity_lifecycle import ConformityRouteRow
    db.add(ConformityRouteRow(project_id=pid, route_type="certificacion_enac", status="CONFORMANT"))
    await db.flush()
    from backend.app.motors.m27_conformity.distintivo_persistence import (
        attach_distintivo_on_registered, attach_external_certificate, read_distintivo_bytes,
    )
    dist = await attach_distintivo_on_registered(db, pid, generated_by="sim")
    assert dist["route_state"] == "REGISTERED"
    dist_bytes, _ = await read_distintivo_bytes(db, pid)
    from docx import Document as _Docx
    dt = _Docx(io.BytesIO(dist_bytes))
    dist_full = "\n".join(p.text for p in dt.paragraphs)
    _dump("E-049_distintivo.txt", dist_full)
    # MEDIA: el distintivo NO debe sustituir al certificado de la entidad acreditada.
    assert "no sustituye" in dist_full.lower()
    assert "entidad de certificación acreditada" in dist_full
    # Slot del certificado externo (lo emite la entidad, NO Fulkro)
    cert = await attach_external_certificate(db, pid, filename="cert_aenor.pdf",
                                             content=b"%PDF-1.5 certificado AENOR ENAC",
                                             content_type="application/pdf")
    log(f"## 5. Conformidad MEDIA · distintivo 809 + certificado externo adjunto "
        f"({cert['external_cert_document_id'][:8]})\n")

    # 6. PORTAL DEL AUDITOR ENAC (magic-link · vías httpx read-only)
    ml = await MagicLinkService(db).generate_magic_link(MagicLinkGenerateRequest(
        project_id=pid, purpose=MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
        recipient_email="auditor.enac@aenor.es"), base_url="http://test")
    await db.commit()
    base = f"/api/v1/public/auditor-portal/{ml.token}"
    summary = await async_client.get(f"{base}/summary")
    assert summary.status_code == 200, summary.text
    sbody = summary.json()
    dda_view = await async_client.get(f"{base}/dda")
    assert dda_view.status_code == 200, dda_view.text
    audit_log = await async_client.get(f"{base}/audit-log")
    _dump("auditor_portal_summary.json", summary.text)
    _dump("auditor_portal_dda.json", dda_view.text[:5000])
    log("## 6. PORTAL DEL AUDITOR ENAC (MEDIA)\n"
        f"summary 200 · proyecto={sbody['project']['id'] == str(pid)} · "
        f"counts.dda_entries={sbody['counts']['dda_entries']} · dda 200 · "
        f"audit-log {audit_log.status_code}\n")
    assert sbody["project"]["id"] == str(pid)
    assert sbody["counts"]["dda_entries"] >= 60

    _dump("REPORT.md", "\n".join(report))
