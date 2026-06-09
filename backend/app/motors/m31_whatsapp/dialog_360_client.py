"""360dialog HTTP REST client wrapper · MB-8 atom 8.1 Q1.B.

Lightweight httpx wrapper for 360dialog WhatsApp Business Cloud API.
mock_mode for tests · returns deterministic responses without network.

Reference: https://docs.360dialog.com/whatsapp-business-cloud-api
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx


logger = logging.getLogger(__name__)


@dataclass
class SendMessageResult:
    """Result of a send operation · provider message_id + status."""

    ok: bool
    whatsapp_message_id: Optional[str] = None
    status: str = ""
    error: Optional[str] = None
    raw_response: dict = field(default_factory=dict)


@dataclass
class WebhookEventResult:
    """Parsed webhook event from 360dialog."""

    event_type: str  # 'inbound_message' | 'delivery_status' | 'unknown'
    from_phone: Optional[str] = None
    body: Optional[str] = None
    whatsapp_message_id: Optional[str] = None
    delivery_status: Optional[str] = None  # 'sent' | 'delivered' | 'read' | 'failed'
    raw: dict = field(default_factory=dict)


class Dialog360Client:
    """Thin httpx wrapper around 360dialog WhatsApp Cloud API.

    mock_mode=True · returns deterministic placeholder responses
    without network calls (used by tests and dev when KYC pending).
    """

    def __init__(
        self,
        api_key: str = "",
        phone_number_id: str = "",
        mock_mode: bool = True,
        base_url: str = "https://waba-v2.360dialog.io",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.phone_number_id = phone_number_id
        self.mock_mode = mock_mode
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def send_text(self, to: str, body: str) -> SendMessageResult:
        """Send a plain text message to a WhatsApp E.164 number."""
        if self.mock_mode:
            return SendMessageResult(
                ok=True,
                whatsapp_message_id=f"mock-wamid-{uuid.uuid4().hex[:16]}",
                status="sent",
                raw_response={
                    "mocked": True, "to": to, "type": "text",
                },
            )

        url = f"{self.base_url}/v1/messages"
        payload = {
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        return await self._post(url, payload)

    async def send_template(
        self,
        to: str,
        template_name: str,
        lang: str = "es",
        params: Optional[list[str]] = None,
    ) -> SendMessageResult:
        """Send a pre-approved template (required for outside 24h window)."""
        if self.mock_mode:
            return SendMessageResult(
                ok=True,
                whatsapp_message_id=f"mock-tplmid-{uuid.uuid4().hex[:16]}",
                status="sent",
                raw_response={
                    "mocked": True, "template": template_name,
                    "lang": lang, "params": params,
                },
            )

        url = f"{self.base_url}/v1/messages"
        components: list[dict[str, Any]] = []
        if params:
            components.append({
                "type": "body",
                "parameters": [
                    {"type": "text", "text": p} for p in params
                ],
            })
        payload: dict[str, Any] = {
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": lang},
                "components": components,
            },
        }
        return await self._post(url, payload)

    def parse_webhook(self, payload: dict) -> WebhookEventResult:
        """Parse a webhook payload from 360dialog.

        Returns a WebhookEventResult with event_type discriminator.
        Pure function · no network · safe to unit-test.
        """
        entry = (payload.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0]
        value = changes.get("value") or {}

        # Inbound message
        messages = value.get("messages") or []
        if messages:
            msg = messages[0]
            text_body = (msg.get("text") or {}).get("body")
            return WebhookEventResult(
                event_type="inbound_message",
                from_phone=msg.get("from"),
                body=text_body,
                whatsapp_message_id=msg.get("id"),
                raw=payload,
            )

        # Delivery status update
        statuses = value.get("statuses") or []
        if statuses:
            s = statuses[0]
            return WebhookEventResult(
                event_type="delivery_status",
                whatsapp_message_id=s.get("id"),
                delivery_status=s.get("status"),
                raw=payload,
            )

        return WebhookEventResult(event_type="unknown", raw=payload)

    async def _post(self, url: str, payload: dict) -> SendMessageResult:
        headers = {
            "D360-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            logger.warning("360dialog request failed: %s", exc)
            return SendMessageResult(
                ok=False, status="network_error", error=str(exc)[:200],
            )

        if resp.status_code >= 400:
            return SendMessageResult(
                ok=False,
                status=f"http_{resp.status_code}",
                error=resp.text[:500],
            )

        try:
            data = resp.json()
        except ValueError:
            data = {"raw_text": resp.text}

        # 360dialog returns `messages: [{id: '...'}]` on success
        wamid = None
        msgs = data.get("messages") or []
        if msgs:
            wamid = msgs[0].get("id")

        return SendMessageResult(
            ok=True,
            whatsapp_message_id=wamid,
            status="sent",
            raw_response=data,
        )


_default_client: Optional[Dialog360Client] = None


def get_default_client() -> Dialog360Client:
    """Lazy singleton · reads Settings for credentials + mock_mode."""
    global _default_client
    if _default_client is None:
        from backend.app.config import get_settings
        settings = get_settings()
        mock = getattr(settings, "whatsapp_provider", "mock") != "360dialog"
        api_key = ""
        phone_id = ""
        if not mock:
            api_key_obj = getattr(settings, "dialog_360_api_key", None)
            if api_key_obj is not None:
                api_key = api_key_obj.get_secret_value()
            phone_id = getattr(settings, "dialog_360_phone_number_id", "") or ""
        _default_client = Dialog360Client(
            api_key=api_key, phone_number_id=phone_id, mock_mode=mock,
        )
    return _default_client


def reset_default_client() -> None:
    """Test helper · force recreate on next get_default_client."""
    global _default_client
    _default_client = None
