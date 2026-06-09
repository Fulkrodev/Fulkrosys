"""Unit tests for MarcosTimesheetMiddleware path matching · MB-7.bis closure."""
import pytest

from backend.app.middleware.marcos_timesheet_middleware import (
    _is_marcos,
    _match_tracked,
)


def test_match_tracked_projects_path():
    kind, ctx_id = _match_tracked(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/dashboard"
    )
    assert kind == "project_id"
    assert ctx_id == "00000000-0000-0000-0000-000000000001"


def test_match_tracked_retainer_plural_alias():
    kind, ctx_id = _match_tracked(
        "/api/v1/admin/retainers/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/edit"
    )
    assert kind == "retainer_id"
    assert ctx_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def test_match_tracked_retainer_singular_legacy():
    kind, ctx_id = _match_tracked(
        "/api/v1/admin/retainer/00000000-0000-0000-0000-000000000099/list"
    )
    assert kind == "retainer_id"
    assert ctx_id == "00000000-0000-0000-0000-000000000099"


def test_match_tracked_whatsapp_thread():
    kind, ctx_id = _match_tracked(
        "/api/v1/admin/whatsapp/threads/12345678-1234-1234-1234-123456789012/send"
    )
    assert kind == "thread_id"
    assert ctx_id == "12345678-1234-1234-1234-123456789012"


def test_match_tracked_unrelated_path_returns_none():
    kind, ctx_id = _match_tracked("/api/v1/health")
    assert kind is None
    assert ctx_id is None


def test_match_tracked_short_id_skipped():
    """Path with non-UUID id is skipped (avoid false positives)."""
    kind, ctx_id = _match_tracked("/api/v1/projects/short-id/foo")
    assert kind is None


def test_is_marcos_exact_email():
    assert _is_marcos("marcos@fulkro.es", ["marcos@fulkro.es"]) is True


def test_is_marcos_case_insensitive():
    assert _is_marcos("Marcos@FULKRO.es", ["marcos@fulkro.es"]) is True


def test_is_marcos_other_user_false():
    assert _is_marcos("user@cliente.com", ["marcos@fulkro.es"]) is False


def test_is_marcos_none_email_false():
    assert _is_marcos(None, ["marcos@fulkro.es"]) is False
