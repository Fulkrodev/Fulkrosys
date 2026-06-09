"""Tests Paso 7 (parcial): Agente 15 + EmailSender + PRIMER_ACCESO_CLIENTE.

7.3-7.11 diferidos al siguiente turno.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, text as sa_text

from backend.app.core.email import (
    EmailSender,
    get_email_sender,
    reset_email_sender,
)
from backend.app.core.email.sender import VALID_BACKENDS
from backend.app.models.operations_paso7 import EmailLog
from backend.app.motors.m12_magic_link.purposes import (
    MagicLinkPurpose, get_config,
)
from backend.app.motors.m23_retainer.agent_15_vigilancia import (
    Agente15Vigilancia,
    FeedItem,
    classify_relevance_heuristic,
    parse_rss_items,
)


# ══════════════════════════════════════════════════════════════════════
# 7.1 Agente 15 Vigilancia
# ══════════════════════════════════════════════════════════════════════


class TestAgente15RSSParsing:
    def test_parse_rss_item_minimo(self):
        xml = b"""<?xml version='1.0'?>
<rss version='2.0'><channel>
  <item>
    <title>Nueva vulnerabilidad critica</title>
    <description>Detalle</description>
    <pubDate>Wed, 22 Apr 2026 10:00:00 +0000</pubDate>
    <guid>ccn-vuln-2026-01</guid>
  </item>
</channel></rss>"""
        items = parse_rss_items(xml, "ccn_cert")
        assert len(items) == 1
        assert items[0].title == "Nueva vulnerabilidad critica"
        assert items[0].source_item_id == "ccn-vuln-2026-01"

    def test_parse_rss_handles_invalid_xml(self):
        assert parse_rss_items(b"not xml", "ccn_cert") == []

    def test_parse_rss_handles_empty_channel(self):
        xml = b"<rss><channel></channel></rss>"
        assert parse_rss_items(xml, "ccn_cert") == []


class TestAgente15Classifier:
    def test_relevant_ens_keyword(self):
        item = FeedItem(
            source="boe", source_item_id="b1",
            title="Real Decreto modifica el Esquema Nacional de Seguridad",
            description="", source_url=None, published_at=None,
        )
        v = classify_relevance_heuristic(item)
        assert v["relevant"] is True
        assert v["severity"] in ("medium", "high", "critical")

    def test_relevant_privacy_keyword(self):
        item = FeedItem(
            source="aepd", source_item_id="a1",
            title="Nueva sancion AEPD", description="RGPD art. 33",
            source_url=None, published_at=None,
        )
        v = classify_relevance_heuristic(item)
        assert v["relevant"] is True

    def test_critical_vulnerability(self):
        item = FeedItem(
            source="ccn_cert", source_item_id="c1",
            title="Vulnerabilidad critica detectada",
            description="zero-day exploit publico", source_url=None,
            published_at=None,
        )
        v = classify_relevance_heuristic(item)
        assert v["severity"] == "critical"

    def test_irrelevant_generic(self):
        item = FeedItem(
            source="boe", source_item_id="b2",
            title="Nombramientos ministeriales",
            description="Actualizacion de cargos", source_url=None,
            published_at=None,
        )
        v = classify_relevance_heuristic(item)
        assert v["relevant"] is False


class TestAgente15RunDailyCheck:
    @pytest.mark.asyncio
    async def test_run_creates_alerts_from_override(self, db):
        agent = Agente15Vigilancia()
        override = [
            FeedItem(
                source="ccn_cert", source_item_id=f"t1-{uuid.uuid4().hex[:8]}",
                title="Vulnerabilidad critica zero-day en ENS",
                description="CCN-CERT emite boletin sobre RD 311/2022",
                source_url="https://ccn-cert.cni.es/test1",
                published_at=datetime.now(timezone.utc),
            ),
            FeedItem(
                source="boe", source_item_id=f"t2-{uuid.uuid4().hex[:8]}",
                title="Actualizacion tecnica de ciberseguridad publica",
                description="Afecta al Esquema Nacional de Seguridad",
                source_url="https://boe.es/test",
                published_at=datetime.now(timezone.utc),
            ),
            FeedItem(
                source="enisa", source_item_id=f"t3-{uuid.uuid4().hex[:8]}",
                title="Nombramientos varios",
                description="Ajustes administrativos",
                source_url=None, published_at=None,
            ),
        ]
        result = await agent.run_daily_check(
            db, raw_items_override=override,
        )
        assert result["fetched_count"] == 3
        assert result["new_count"] == 2  # 2 relevantes, 1 descartado
        assert result["skipped_irrelevant"] == 1

    @pytest.mark.asyncio
    async def test_run_dedups_second_pass(self, db):
        agent = Agente15Vigilancia()
        same_id = f"dedup-{uuid.uuid4().hex[:8]}"
        item = FeedItem(
            source="ccn_cert", source_item_id=same_id,
            title="Vulnerabilidad critica",
            description="zero-day ENS",
            source_url=None, published_at=None,
        )
        r1 = await agent.run_daily_check(db, raw_items_override=[item])
        r2 = await agent.run_daily_check(db, raw_items_override=[item])
        assert r1["new_count"] == 1
        assert r2["new_count"] == 0
        assert r2["skipped_existing"] == 1


class TestAgente15Digest:
    @pytest.mark.asyncio
    async def test_digest_groups_by_severity(self, db):
        agent = Agente15Vigilancia()
        # Poblar 3 alerts con distintas severities
        override = [
            FeedItem(
                source="ccn_cert", source_item_id=f"dig-{i}-{uuid.uuid4().hex[:8]}",
                title=t, description=d, source_url=None,
                published_at=datetime.now(timezone.utc),
            )
            for i, (t, d) in enumerate([
                ("Vulnerabilidad critica zero-day en ENS", "exploit"),
                ("Nueva guia CCN-STIC 803", "Esquema Nacional de Seguridad"),
                ("Nota AEPD sobre RGPD", "proteccion datos"),
            ])
        ]
        await agent.run_daily_check(db, raw_items_override=override)

        since = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        digest = await agent.generate_daily_digest(db, since=since)
        assert digest["total"] >= 3
        assert "critical" in digest["by_severity"]
        assert "<h3" in digest["html"]


# ══════════════════════════════════════════════════════════════════════
# 7.2 EmailSender
# ══════════════════════════════════════════════════════════════════════


class TestEmailSender:
    def test_backends_list(self):
        assert set(VALID_BACKENDS) == {"smtp", "postmark_api", "mock"}

    def test_default_backend_is_mock(self, patched_settings):
        # TODO-EMAIL-SENDER-CONSOLIDATION-001 RESOLVED: backend selector
        # ahora desde Settings.email_backend (no os.environ legacy).
        patched_settings(email_backend="mock")
        reset_email_sender()
        sender = get_email_sender()
        assert sender.backend == "mock"

    def test_explicit_backend_selection(self):
        sender = EmailSender(backend="mock")
        assert sender.backend == "mock"

    def test_invalid_backend_falls_back_to_mock(self):
        sender = EmailSender(backend="invalid-xx")
        assert sender.backend == "mock"

    @pytest.mark.asyncio
    async def test_mock_send_logs_success(self, db):
        sender = EmailSender(backend="mock")
        r = await sender.send(
            db, to="test@example.com", subject="Test",
            html_body="<p>Hello</p>",
            template_used="test_template",
        )
        assert r.ok is True
        assert r.backend_used == "mock"
        assert r.message_id is not None
        assert r.email_log_id is not None

        # Verificar persistencia en email_log
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            row = (await db.execute(
                select(EmailLog).where(EmailLog.id == r.email_log_id)
            )).scalar_one()
            assert row.recipient == "test@example.com"
            assert row.delivery_status == "sent"
            assert row.backend_used == "mock"
        finally:
            await db.execute(sa_text("RESET ROLE"))

    @pytest.mark.asyncio
    async def test_postmark_without_token_fails_gracefully(
        self, db, patched_settings,
    ):
        # TODO-EMAIL-SENDER-CONSOLIDATION-001 RESOLVED: postmark token
        # ahora desde Settings.postmark_api_token (SecretStr).
        patched_settings(postmark_api_token="")
        sender = EmailSender(backend="postmark_api")
        r = await sender.send(
            db, to="test@example.com", subject="X",
            html_body="<p>x</p>", retry=False,
        )
        assert r.ok is False
        assert "postmark_api_token" in (r.error or "").lower()
        # email_log entry marked failed
        await db.execute(sa_text("SET LOCAL ROLE fulkro_app_bypassrls"))
        try:
            row = (await db.execute(
                select(EmailLog).where(EmailLog.id == r.email_log_id)
            )).scalar_one()
            assert row.delivery_status == "failed"
        finally:
            await db.execute(sa_text("RESET ROLE"))


# ══════════════════════════════════════════════════════════════════════
# 7.5 Magic link purposes nuevos
# ══════════════════════════════════════════════════════════════════════


class TestMagicLinkPurposesPaso7:
    def test_purposes_registered(self):
        # Paso 7 final cerro con 23 purposes. ADR-011 (Sesion 11 FASE 4.5)
        # amplio el catalogo a 35 purposes. SAN-B.MB-6.6 (Sesion 11
        # saneamiento) eliminó AUTORIZACION_PENTEST legacy (superseded
        # por AUTORIZAR_PENTEST_EXTERNO M8 v5.1) · count 34.
        # SAN-D MB-19.4 (ADR-041): FIRMA_CONTRATO añadido (#36) · count 35.
        # Ejecutable 8 Pasada 16: AUDITOR_PORTAL_ENAC añadido Sesión 3B-2B.6 (auditor portal ·
        # CLAUDE.md + memoria auditor-portal-architecture.md) · count 36. (test desactualizado · fuente citada)
        # Batch A diagnóstico previo: DIAGNOSTICO_PRECLIENTE añadido (#38) · count 37.
        assert len(list(MagicLinkPurpose)) == 37

    def test_primer_acceso_cliente_ttl_24h_otp(self):
        cfg = get_config(MagicLinkPurpose.PRIMER_ACCESO_CLIENTE)
        assert cfg["ttl_hours"] == 24
        assert cfg["requires_otp"] is True
        assert cfg["max_uses"] == 1

    def test_normativa_alert_ttl_7d(self):
        cfg = get_config(MagicLinkPurpose.NORMATIVA_ALERT_CRITICAL)
        assert cfg["ttl_hours"] == 7 * 24

    def test_retainer_welcome_ttl_7d(self):
        cfg = get_config(MagicLinkPurpose.RETAINER_WELCOME)
        assert cfg["ttl_hours"] == 7 * 24


# ══════════════════════════════════════════════════════════════════════
# Compatibilidad audit renderer paso 5.5 (100/100 mantenido)
# ══════════════════════════════════════════════════════════════════════


class TestRendererCompatibility:
    def test_all_purposes_have_email_template(self):
        from backend.app.motors.m12_magic_link.emails.renderer import (
            _PURPOSE_EMAILS,
        )
        # Ejecutable 8 Pasada 16: purposes que NO requieren template email (fuente citada):
        # - 4 REVOCADOS ADR-020 v3 (cliente firma/aprueba IN-PORTAL · policy_enforcer
        #   hard-reject · migración a7c5b9e2d1f8 · comentario renderer.py:194-201).
        # - AUDITOR_PORTAL_ENAC: entrega OUT-OF-BAND (admin comparte el link al auditor
        #   ENAC externo · NO email automático · solo validación de token en m09 public_api).
        no_email_template = {
            MagicLinkPurpose.APROBACION_FACTURA,
            MagicLinkPurpose.VALIDACION_CAMBIO_ALCANCE,
            MagicLinkPurpose.ACEPTACION_RIESGO_RESIDUAL,
            MagicLinkPurpose.CONSENTIMIENTO_TRATAMIENTO_DATOS,
            MagicLinkPurpose.AUDITOR_PORTAL_ENAC,
            # Batch A diagnóstico previo: template de email pendiente Batch B
            # (envío real al lead vía outreach M20). Exento de momento.
            MagicLinkPurpose.DIAGNOSTICO_PRECLIENTE,
        }
        missing = [
            p.value for p in MagicLinkPurpose
            if p not in _PURPOSE_EMAILS and p not in no_email_template
        ]
        assert missing == [], f"Purposes sin template: {missing}"
