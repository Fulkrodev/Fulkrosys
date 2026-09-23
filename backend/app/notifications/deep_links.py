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
- Cada ruta tiene que existir como página en ``frontend/app`` (lo comprueba
  ``backend/tests/test_enlaces_de_interfaz_existen.py``). No hay páginas de
  detalle por tarea, evidencia o auditoría: el enlace va a la lista donde
  vive el elemento y el id viaja en la query, como ya hacía ``chat_thread``.
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
        # /client-portal/tasks/{id} no existe: las tareas son una lista.
        return self._build(
            "/client-portal/tasks", {"task": _coerce_id(task_id)},
        )

    def chat_thread(self, thread_id: uuid.UUID | str) -> str:
        return self._build(
            "/client-portal/chat",
            {"thread": _coerce_id(thread_id)},
        )

    def evidence(self, evidence_id: uuid.UUID | str) -> str:
        # La página es /client-portal/evidencias (en español) y no tiene
        # detalle por id; /client-portal/evidences/{id} daba «no encontrado».
        return self._build(
            "/client-portal/evidencias", {"evidence": _coerce_id(evidence_id)},
        )

    def phase(self, phase_name: str) -> str:
        return self._build("/client-portal/workflow", {"phase": phase_name})

    def audit(self, audit_id: uuid.UUID | str) -> str:
        # No hay /client-portal/audits: el cliente sigue su auditoría en
        # /client-portal/certificacion (acompañamiento de la certificación).
        return self._build(
            "/client-portal/certificacion", {"audit": _coerce_id(audit_id)},
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
        # /account/notifications solo redirige aquí; se enlaza el destino.
        return self._build("/client-portal/settings/notifications")

    def login(self) -> str:
        return self._build("/client-portal/login")

    def magic_link(self, magic_token: str) -> str:
        # /auth/magic/{token} no existe. Es la misma URL que construye M12
        # (MagicLinkService.generate_magic_link): /ml/consume?token=...
        return self._build("/ml/consume", {"token": magic_token})

    # ──────────── Admin (Marcos) ────────────

    def task_admin(
        self,
        project_id: uuid.UUID | str,
        task_id: uuid.UUID | str,
    ) -> str:
        # No hay página de tarea admin; las tareas del proyecto se ven en su
        # pestaña Workflow (vista cronológica).
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}/workflow",
            {"task": _coerce_id(task_id)},
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
        # La pestaña Evidencias no tiene detalle por id.
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}/evidence",
            {"evidence": _coerce_id(evidence_id)},
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
        # La pestaña es /audit (singular) y no tiene detalle por id.
        return self._build(
            f"/admin/projects/{_coerce_id(project_id)}/audit",
            {"audit": _coerce_id(audit_id)},
        )

    def project_admin(self, project_id: uuid.UUID | str) -> str:
        return self._build(f"/admin/projects/{_coerce_id(project_id)}")

    def client_admin(self, client_id: uuid.UUID | str) -> str:
        return self._build(f"/admin/clients/{_coerce_id(client_id)}")

    def client_user_admin(
        self,
        client_id: uuid.UUID | str,
        client_user_id: uuid.UUID | str,
        project_id: uuid.UUID | str | None = None,
    ) -> str:
        # /admin/clients/{id}/users/{id} no existe (R23: los usuarios del
        # portal cuelgan del proyecto). Con proyecto se va a su pestaña
        # Usuarios; sin él, al enrutador /admin/clients/{id}, que resuelve el
        # proyecto del cliente.
        user = _coerce_id(client_user_id)
        if project_id is not None:
            return self._build(
                f"/admin/projects/{_coerce_id(project_id)}/users",
                {"user": user},
            )
        return self._build(
            f"/admin/clients/{_coerce_id(client_id)}", {"user": user},
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
        # /admin no tiene página; el panel es /admin/dashboard.
        return self._build("/admin/dashboard")

    def inbox_admin(self) -> str:
        return self._build("/admin/inbox")

    def notifications_admin(self) -> str:
        return self._build("/admin/notifications")

    def admin_login(self) -> str:
        return self._build("/login")


__all__ = ["DeepLinkGenerator"]
