"""Tests for CCN-STIC scraper · MB-7.bis atom 7.bis.2."""
import pytest
from sqlalchemy import text

from backend.app.motors.m23_retainer.ccn_stic_scraper import (
    parse_index_html,
    scrape_and_persist,
)
from backend.tests.conftest import _admin_setup


pytestmark = pytest.mark.asyncio


_SAMPLE_INDEX = b"""<html><body>
  <a href="/series-ccn-stic/800-esquema-nacional">CCN-STIC 800</a>
  <a href="/series-ccn-stic/810-pruebas">CCN-STIC 810</a>
  <a href="https://www.ccn-cert.cni.es/series-ccn-stic/870">CCN-STIC 870</a>
  <a href="/series-ccn-stic/800-esquema-nacional">duplicate</a>
  <a href="/otra-cosa">should be ignored</a>
</body></html>"""


def test_parse_index_html_extracts_unique_guides():
    guides = parse_index_html(_SAMPLE_INDEX)
    assert len(guides) == 3  # duplicate filtered
    slugs = {g.source_item_id.split("-")[0] for g in guides}
    assert "800" in slugs
    assert "810" in slugs
    assert "870" in slugs


def test_parse_index_html_skips_non_matching_anchors():
    guides = parse_index_html(_SAMPLE_INDEX)
    for g in guides:
        assert "series-ccn-stic" in g.url


def test_parse_index_html_empty_returns_empty_list():
    assert parse_index_html(b"<html></html>") == []


async def test_scrape_and_persist_inserts_new_alerts(db):
    fetched = []

    def fake_fetch(url):
        fetched.append(url)
        return _SAMPLE_INDEX, {}

    def fake_head(url):
        return {"last-modified": "Mon, 11 May 2026 10:00:00 GMT"}

    async with _admin_setup(db):
        pass  # nothing to seed

    result = await scrape_and_persist(
        db, fetch_html=fake_fetch, head_url=fake_head, rate_limit=0,
    )
    assert result["indexed"] == 3
    assert result["new"] == 3
    assert result["skipped"] == 0
    assert fetched == ["https://www.ccn-cert.cni.es/series-ccn-stic.html"]

    rows = (await db.execute(text(
        "SELECT count(*) FROM normativa_alerts WHERE source = 'ccn_stic'"
    ))).first()
    assert int(rows[0]) >= 3


async def test_scrape_and_persist_skips_existing(db):
    """Second run skips already-persisted item_ids."""
    fake_fetch = lambda u: (_SAMPLE_INDEX, {})
    fake_head = lambda u: {}

    r1 = await scrape_and_persist(db, fetch_html=fake_fetch, head_url=fake_head, rate_limit=0)
    assert r1["new"] == 3

    r2 = await scrape_and_persist(db, fetch_html=fake_fetch, head_url=fake_head, rate_limit=0)
    assert r2["new"] == 0
    assert r2["skipped"] == 3


async def test_scrape_and_persist_handles_fetch_failure(db):
    fake_fetch = lambda u: (None, {})
    fake_head = lambda u: {}

    result = await scrape_and_persist(db, fetch_html=fake_fetch, head_url=fake_head, rate_limit=0)
    assert result["errors"] == 1
    assert result["new"] == 0
