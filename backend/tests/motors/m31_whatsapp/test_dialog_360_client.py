"""Tests for Dialog360Client mock + webhook parsing · atom 8.1."""
import pytest

from backend.app.motors.m31_whatsapp.dialog_360_client import Dialog360Client


pytestmark = pytest.mark.asyncio


async def test_send_text_mock_returns_ok():
    client = Dialog360Client(mock_mode=True)
    result = await client.send_text(to="+34666123456", body="hola")
    assert result.ok is True
    assert result.whatsapp_message_id is not None
    assert result.whatsapp_message_id.startswith("mock-wamid-")
    assert result.status == "sent"


async def test_send_template_mock_returns_ok():
    client = Dialog360Client(mock_mode=True)
    result = await client.send_template(
        to="+34666123456", template_name="incident_critical_resolved",
        params=["Test", "https://example.com"],
    )
    assert result.ok is True
    assert result.whatsapp_message_id.startswith("mock-tplmid-")


def test_parse_webhook_inbound_message():
    client = Dialog360Client(mock_mode=True)
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "34666111222",
                        "id": "wamid.ABCD",
                        "text": {"body": "Hola Marcos"},
                    }],
                },
            }],
        }],
    }
    event = client.parse_webhook(payload)
    assert event.event_type == "inbound_message"
    assert event.from_phone == "34666111222"
    assert event.body == "Hola Marcos"
    assert event.whatsapp_message_id == "wamid.ABCD"


def test_parse_webhook_delivery_status():
    client = Dialog360Client(mock_mode=True)
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{
                        "id": "wamid.XYZ",
                        "status": "delivered",
                    }],
                },
            }],
        }],
    }
    event = client.parse_webhook(payload)
    assert event.event_type == "delivery_status"
    assert event.whatsapp_message_id == "wamid.XYZ"
    assert event.delivery_status == "delivered"


def test_parse_webhook_unknown_returns_unknown_type():
    client = Dialog360Client(mock_mode=True)
    event = client.parse_webhook({"foo": "bar"})
    assert event.event_type == "unknown"
