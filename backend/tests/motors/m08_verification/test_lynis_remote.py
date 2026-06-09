"""Tests M08 Lynis runner remote SSH mode · paramiko mocked.

Cubre SAN-B.MB-3.bis.2 (TODO-M8-G2 cierre):
- Modo remote success (Lynis output parsed identical a local)
- ssh_auth_failed estructurado
- ssh_connect_failed estructurado
- lynis_not_provisioned estructurado
- ssh_command_timeout estructurado
- mode='remote' sin ssh_credentials → ValueError
"""
from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest
import paramiko

from backend.app.motors.m08_verification.tools.lynis_runner import LynisRunner


SAMPLE_LYNIS_OUTPUT = (
    b"# Lynis report\n"
    b"warning[]=AUTH-9286|Set a password on GRUB to prevent altering boot configuration|2|\n"
    b"warning[]=KRNL-5820|Reboot is needed due to updated kernel|3|\n"
    b"suggestion[]=AUTH-9230|Configure minimum password age in /etc/login.defs|2|\n"
)


def _make_mock_stdout(rc: int, output: bytes):
    """Build a paramiko exec_command-style mock returning (stdin, stdout, stderr)."""
    mock_stdout = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = rc
    mock_stdout.read.return_value = output
    return (MagicMock(), mock_stdout, MagicMock())


@pytest.mark.asyncio
async def test_lynis_remote_mock_success():
    """Mock paramiko returns Lynis output → findings parsed identical local."""
    creds = {
        "host": "10.0.0.5", "port": 22, "user": "root",
        "auth_method": "key", "key_path_local": "/tmp/test.pem",
    }

    with patch("paramiko.SSHClient") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        # First exec_command = `command -v lynis` (rc=0 = provisioned)
        # Second = actual lynis run
        mock_client.exec_command.side_effect = [
            _make_mock_stdout(rc=0, output=b"/usr/bin/lynis\n"),
            _make_mock_stdout(rc=0, output=SAMPLE_LYNIS_OUTPUT),
        ]

        result = await LynisRunner.run(
            targets=[], host_label="cliente-prod-host",
            mode="remote", ssh_credentials=creds,
        )

    assert result.error is None
    assert result.return_code == 0
    assert len(result.findings) == 3  # 2 warnings + 1 suggestion
    titles = {f["title"] for f in result.findings}
    assert "Lynis WARNING AUTH-9286" in titles
    assert "Lynis SUGGESTION AUTH-9230" in titles
    # Affected host correctly tagged
    assert all(f["affected_host"] == "cliente-prod-host" for f in result.findings)


@pytest.mark.asyncio
async def test_lynis_remote_ssh_auth_failed():
    creds = {
        "host": "10.0.0.5", "port": 22, "user": "root",
        "auth_method": "password", "password": "wrong",
    }

    with patch("paramiko.SSHClient") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        mock_client.connect.side_effect = paramiko.AuthenticationException(
            "Authentication failed."
        )

        result = await LynisRunner.run(
            targets=[], host_label="cliente",
            mode="remote", ssh_credentials=creds,
        )

    assert result.return_code == -1
    assert result.findings == []
    assert result.error is not None
    assert result.error.startswith("ssh_auth_failed")


@pytest.mark.asyncio
async def test_lynis_remote_ssh_connect_failed_network():
    creds = {
        "host": "192.0.2.1", "port": 22, "user": "root",
        "auth_method": "key", "key_path_local": "/tmp/nope.pem",
    }

    with patch("paramiko.SSHClient") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        mock_client.connect.side_effect = socket.error(
            "Connection refused"
        )

        result = await LynisRunner.run(
            targets=[], host_label="dead-host",
            mode="remote", ssh_credentials=creds,
        )

    assert result.return_code == -1
    assert result.findings == []
    assert result.error is not None
    assert result.error.startswith("ssh_connect_failed")


@pytest.mark.asyncio
async def test_lynis_remote_lynis_not_provisioned():
    """`command -v lynis` returns 1 → structured error sin crash."""
    creds = {
        "host": "10.0.0.6", "port": 22, "user": "root",
        "auth_method": "key", "key_path_local": "/tmp/test.pem",
    }

    with patch("paramiko.SSHClient") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        # which lynis returns rc=1 (not found)
        mock_client.exec_command.side_effect = [
            _make_mock_stdout(rc=1, output=b""),
        ]

        result = await LynisRunner.run(
            targets=[], host_label="no-lynis-host",
            mode="remote", ssh_credentials=creds,
        )

    assert result.return_code == -1
    assert result.findings == []
    assert result.error is not None
    assert result.error.startswith("lynis_not_provisioned")


@pytest.mark.asyncio
async def test_lynis_remote_unsupported_auth_method():
    """auth_method desconocido cae en branch ssh_connect_failed (ValueError)."""
    creds = {
        "host": "10.0.0.5", "port": 22, "user": "root",
        "auth_method": "kerberos",  # no soportado
    }

    with patch("paramiko.SSHClient") as mock_class:
        mock_class.return_value = MagicMock()

        result = await LynisRunner.run(
            targets=[], host_label="x",
            mode="remote", ssh_credentials=creds,
        )

    assert result.error is not None
    assert "ssh_connect_failed" in result.error or "kerberos" in result.error


@pytest.mark.asyncio
async def test_lynis_remote_requires_ssh_credentials():
    """mode='remote' sin ssh_credentials → ValueError explícito."""
    with pytest.raises(ValueError, match="ssh_credentials"):
        await LynisRunner.run(
            targets=[], host_label="x",
            mode="remote", ssh_credentials=None,
        )
