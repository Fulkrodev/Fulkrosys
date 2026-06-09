"""Tests DeepLinkGenerator (MB-16.3 ADR-039)."""
from __future__ import annotations

import uuid

import pytest

from backend.app.notifications import DeepLinkGenerator


BASE = "https://fulkro.es"


@pytest.fixture
def gen():
    return DeepLinkGenerator(base_url=BASE)


def test_task_client(gen):
    tid = uuid.uuid4()
    url = gen.task(tid)
    assert url == f"{BASE}/client-portal/tasks/{tid}"


def test_task_admin(gen):
    pid = uuid.uuid4()
    tid = uuid.uuid4()
    url = gen.task_admin(pid, tid)
    assert url == f"{BASE}/admin/projects/{pid}/tasks/{tid}"


def test_chat_thread_client(gen):
    thread = uuid.uuid4()
    url = gen.chat_thread(thread)
    assert url == f"{BASE}/client-portal/chat?thread={thread}"


def test_chat_thread_admin(gen):
    pid = uuid.uuid4()
    thread = uuid.uuid4()
    url = gen.chat_thread_admin(pid, thread)
    assert url == f"{BASE}/admin/projects/{pid}/chat?thread={thread}"


def test_evidence_client(gen):
    eid = uuid.uuid4()
    url = gen.evidence(eid)
    assert url == f"{BASE}/client-portal/evidences/{eid}"


def test_evidence_admin(gen):
    pid = uuid.uuid4()
    eid = uuid.uuid4()
    url = gen.evidence_admin(pid, eid)
    assert url == f"{BASE}/admin/projects/{pid}/evidence/{eid}"


def test_phase_client(gen):
    url = gen.phase("operacion")
    assert url == f"{BASE}/client-portal/workflow?phase=operacion"


def test_phase_admin(gen):
    pid = uuid.uuid4()
    url = gen.phase_admin(pid, "auditoria")
    assert url == f"{BASE}/admin/projects/{pid}?phase=auditoria"


def test_audit_client(gen):
    aid = uuid.uuid4()
    url = gen.audit(aid)
    assert url == f"{BASE}/client-portal/audits/{aid}"


def test_audit_admin(gen):
    pid = uuid.uuid4()
    aid = uuid.uuid4()
    url = gen.audit_admin(pid, aid)
    assert url == f"{BASE}/admin/projects/{pid}/audits/{aid}"


def test_dashboard_client(gen):
    assert gen.dashboard() == f"{BASE}/client-portal/dashboard"


def test_dashboard_admin(gen):
    assert gen.dashboard_admin() == f"{BASE}/admin"


def test_inbox_routes(gen):
    assert gen.inbox() == f"{BASE}/client-portal/inbox"
    assert gen.inbox_admin() == f"{BASE}/admin/inbox"


def test_files(gen):
    assert gen.files() == f"{BASE}/client-portal/files"


def test_account_notifications(gen):
    assert gen.account() == f"{BASE}/client-portal/account"
    assert gen.notifications() == (
        f"{BASE}/client-portal/account/notifications"
    )
    assert gen.notifications_admin() == f"{BASE}/admin/notifications"


def test_login_routes(gen):
    assert gen.login() == f"{BASE}/client-portal/login"
    assert gen.admin_login() == f"{BASE}/login"


def test_magic_link(gen):
    url = gen.magic_link("abc123token")
    assert url == f"{BASE}/auth/magic/abc123token"


def test_project_admin(gen):
    pid = uuid.uuid4()
    assert gen.project_admin(pid) == f"{BASE}/admin/projects/{pid}"


def test_client_admin(gen):
    cid = uuid.uuid4()
    assert gen.client_admin(cid) == f"{BASE}/admin/clients/{cid}"


def test_client_user_admin(gen):
    cid = uuid.uuid4()
    uid = uuid.uuid4()
    assert gen.client_user_admin(cid, uid) == (
        f"{BASE}/admin/clients/{cid}/users/{uid}"
    )


def test_alert_admin(gen):
    aid = uuid.uuid4()
    assert gen.alert_admin(aid) == f"{BASE}/admin/alerts?id={aid}"


def test_meeting_admin(gen):
    mid = uuid.uuid4()
    assert gen.meeting_admin(mid) == f"{BASE}/admin/meetings/{mid}"


def test_retainer_admin(gen):
    pid = uuid.uuid4()
    assert gen.retainer_admin(pid) == (
        f"{BASE}/admin/projects/{pid}/retainer"
    )


def test_uuid_string_accepted(gen):
    tid = str(uuid.uuid4())
    url = gen.task(tid)
    assert tid in url


def test_invalid_uuid_string_raises(gen):
    with pytest.raises(ValueError):
        gen.task("not-a-uuid")


def test_base_url_strips_trailing_slash():
    g = DeepLinkGenerator(base_url="https://fulkro.es/")
    assert g.dashboard().startswith("https://fulkro.es/client-portal")


def test_base_url_falls_back_to_settings(monkeypatch):
    g = DeepLinkGenerator()
    url = g.dashboard()
    assert url.endswith("/client-portal/dashboard")
