"""DeepLinkGenerator · 25+ patterns canónicos rutas frontend (MB-16.3 ADR-039).

Genera URLs absolutas con prefijo ``Settings.app_base_url`` para enlaces
embebidos en notificaciones email + portal SSE. Centraliza los patrones
de rutas para que cambios en routing frontend solo requieran update
aquí (single source of truth).

Convenciones:
- Patterns ``*_admin`` apuntan a ``/admin/...`` (Marcos).
- Patterns sin sufijo apuntan a ``/client-portal/...`` (cliente).
- Path params posicionales · query params via ``query_kv``.
- IDs UUID validados via ``str(UUID)`` para prevenir injection.
"""
from __future__ import annotations

import urllib.parse
import uuid
from dataclasses import dataclass
from typing import Mapping

from backend.app.config import get_settings


def _coerce_id(value: uuid.UUID | str) -> str:
    if isinstance(value, uuid.UUID):
        return str(value)
    uuid.UUID(value)
    return value


@dataclass(frozen=True)
class DeepLinkGenerator:
    """Resuelve patrones canónicos a URLs absolutas frontend.

    Inicialización opcional con ``base_url`` (override de
    ``Settings.app_base_url`` para tests sintéticos).
    """

    base_url: str | None = None

    @property
    def root(self) -> str:
        return (self.base_url or get_settings().app_base_url).rstrip("/")

    def _build(self, path: str, query: Mapping[str, str] | None = None) -> str:
        if not path.startswith("/"):
            path = "/" + path
        if query:
            qs = urllib.parse.urlencode(query)
            return f"{self.root}{path}?{qs}"
        return f"{self.root}{path}"

    # ──────────── Cliente portal ────────────

    def task(self, task_id: uuid.UUID | str) -> str:
        return self._build(f"/client-portal/tasks/{_coerce_id(task_id)}")

    def chat_thread(self, thread_id: uuid.UUID | str) -> str:
        return self._build(
            "/client-portal/chat",
            {"thread": _coerce_id(thread_id)},
        )

    def evidence(self, evidence_id: uuid.UUID | str) -> str:
        return self._build(
            f"/client-portal/evidences/{_coerce_id(evidence_id)}"
        )

    def phase(self, phase_name: str) -> str:
        return self._build("/client-portal/workflow", {"phase": phase_name})

    def audit(self, audit_id: uuid.UUID | str) -> str:
        return self._build(
            f"/client-portal/audits/{_coerce_id(audit_id)}"
        )

    def dashboard(self) -> str:
        return self._build("/client-portal/dashboard")

    def inbox(self) -> str:
        return self._build("/client-portal/inbox")

    def files(self) -> str:
        return self._build("/client-portal/files")

    def account(self) -> str:
        return self._build("/client-portal/account")

    def notifications(self) -> str:
        return self._build("/client-portal/account/notifications")

    def login(self) -> str:
        return self._build("/client-portal/login")

    def magic_link(self, magic_token: str) -> str:
        return self._build(f"/auth/magic/{magic_token}")

    # ──────────── Admin (Marcos) ────────────

    def task_admin(
        self,
        project_id: uuid.UUID | str,
        task_id: uuid.UUID | str,
    ) -> str:
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}"
            f"/tasks/{_coerce_id(task_id)}"
        )

    def chat_thread_admin(
        self,
        project_id: uuid.UUID | str,
        thread_id: uuid.UUID | str,
    ) -> str:
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}/chat",
            {"thread": _coerce_id(thread_id)},
        )

    def evidence_admin(
        self,
        project_id: uuid.UUID | str,
        evidence_id: uuid.UUID | str,
    ) -> str:
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}"
            f"/evidence/{_coerce_id(evidence_id)}"
        )

    def phase_admin(
        self, project_id: uuid.UUID | str, phase_name: str,
    ) -> str:
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}",
            {"phase": phase_name},
        )

    def audit_admin(
        self,
        project_id: uuid.UUID | str,
        audit_id: uuid.UUID | str,
    ) -> str:
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}"
            f"/audits/{_coerce_id(audit_id)}"
        )

    def project_admin(self, project_id: uuid.UUID | str) -> str:
        return self._build(f"/admin/projects/{_coerce_id(project_id)}")

    def client_admin(self, client_id: uuid.UUID | str) -> str:
        return self._build(f"/admin/clients/{_coerce_id(client_id)}")

    def client_user_admin(
        self,
        client_id: uuid.UUID | str,
        client_user_id: uuid.UUID | str,
    ) -> str:
        return self._build(
            f"/admin/clients/{_coerce_id(client_id)}"
            f"/users/{_coerce_id(client_user_id)}"
        )

    def alert_admin(self, alert_id: uuid.UUID | str) -> str:
        return self._build(
            "/admin/alerts", {"id": _coerce_id(alert_id)}
        )

    def meeting_admin(self, meeting_id: uuid.UUID | str) -> str:
        return self._build(f"/admin/meetings/{_coerce_id(meeting_id)}")

    def retainer_admin(self, project_id: uuid.UUID | str) -> str:
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}/retainer"
        )

    def dashboard_admin(self) -> str:
        return self._build("/admin")

    def inbox_admin(self) -> str:
        return self._build("/admin/inbox")

    def notifications_admin(self) -> str:
        return self._build("/admin/notifications")

    def admin_login(self) -> str:
        return self._build("/login")


__all__ = ["DeepLinkGenerator"]
