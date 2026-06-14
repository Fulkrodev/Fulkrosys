"""Biblioteca de playbooks de host VERIFICADOS · m_remediation (ADR-055).

Plantillas DETERMINISTAS e idempotentes que el agente on-prem ejecuta sobre los
sistemas del cliente. NO son código generado por LLM: son specs revisadas y
firmadas (allowlist en agent_protocol.PLAYBOOK_ALLOWLIST). El LLM (impl_selector)
solo SELECCIONA y PARAMETRIZA estas plantillas según el inventario del cliente;
NUNCA escribe los pasos que se ejecutan (doctrina anti-injection · R1).

Cada playbook declara:
  - os_families      : SO soportados (el selector elige por inventario)
  - ansible_steps    : pasos idempotentes como datos (módulo Ansible + args ·
                       el agente los ejecuta vía ansible-runner; NUNCA shell libre)
  - check_assertion  : clave booleana que `verify` comprueba tras aplicar
  - params_schema    : parámetros que el selector debe rellenar (con defaults)
  - reversible       : si hay rollback determinista
  - dry_run_summary  : descripción del plan para previsualizar antes de aplicar

Cobertura técnica ENS por playbook (ver impl_catalog para el mapeo medida→plantilla).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HostPlaybookSpec:
    playbook_id: str
    title_es: str
    os_families: tuple[str, ...]
    check_assertion: str
    ansible_steps: tuple[dict[str, Any], ...]
    rollback_steps: tuple[dict[str, Any], ...]
    params_schema: dict[str, Any]
    reversible: bool
    dry_run_summary: str


# Catálogo de playbooks de host (debe ser subconjunto de PLAYBOOK_ALLOWLIST).
HOST_PLAYBOOKS: dict[str, HostPlaybookSpec] = {
    "harden_sshd_root_login": HostPlaybookSpec(
        playbook_id="harden_sshd_root_login",
        title_es="Deshabilitar login root por SSH",
        os_families=("linux",),
        check_assertion="permit_root_login_no",
        ansible_steps=(
            {"module": "ansible.builtin.lineinfile", "args": {
                "path": "/etc/ssh/sshd_config", "regexp": "^#?PermitRootLogin",
                "line": "PermitRootLogin no", "backup": True}},
            {"module": "ansible.builtin.service", "args": {
                "name": "sshd", "state": "reloaded"}},
        ),
        rollback_steps=(
            {"module": "ansible.builtin.copy", "args": {
                "src": "{{ backup_path }}", "dest": "/etc/ssh/sshd_config",
                "remote_src": True}},
            {"module": "ansible.builtin.service", "args": {
                "name": "sshd", "state": "reloaded"}},
        ),
        params_schema={},
        reversible=True,
        dry_run_summary=(
            "Pone PermitRootLogin no en sshd_config (con backup) y recarga sshd."
        ),
    ),
    "enable_host_firewall_rule": HostPlaybookSpec(
        playbook_id="enable_host_firewall_rule",
        title_es="Cerrar puerto expuesto (firewall)",
        os_families=("linux",),
        check_assertion="port_closed",
        ansible_steps=(
            {"module": "community.general.ufw", "args": {
                "rule": "deny", "port": "{{ port }}", "proto": "{{ proto }}"}},
        ),
        rollback_steps=(
            {"module": "community.general.ufw", "args": {
                "rule": "allow", "port": "{{ port }}", "proto": "{{ proto }}"}},
        ),
        params_schema={"port": {"type": "string", "required": True},
                       "proto": {"type": "string", "default": "tcp"}},
        reversible=True,
        dry_run_summary="Aplica regla ufw deny al puerto indicado.",
    ),
    "apply_package_security_update": HostPlaybookSpec(
        playbook_id="apply_package_security_update",
        title_es="Aplicar parche de seguridad de paquete",
        os_families=("linux",),
        check_assertion="package_patched",
        ansible_steps=(
            {"module": "ansible.builtin.package", "args": {
                "name": "{{ package }}", "state": "latest"}},
        ),
        rollback_steps=(
            {"module": "ansible.builtin.package", "args": {
                "name": "{{ package }}={{ previous_version }}", "state": "present"}},
        ),
        params_schema={"package": {"type": "string", "required": True}},
        reversible=True,
        dry_run_summary="Actualiza el paquete a la última versión (con copia de versión previa).",
    ),
    "configure_host_backup": HostPlaybookSpec(
        playbook_id="configure_host_backup",
        title_es="Configurar copias de seguridad automáticas",
        os_families=("linux", "windows"),
        check_assertion="backup_configured",
        ansible_steps=(
            {"module": "ansible.builtin.package", "args": {
                "name": "restic", "state": "present"}},
            {"module": "ansible.builtin.cron", "args": {
                "name": "fulkro-backup", "minute": "0", "hour": "{{ hour }}",
                "job": "restic -r {{ repo }} backup {{ paths }} "
                       "&& restic -r {{ repo }} check"}},
        ),
        rollback_steps=(
            {"module": "ansible.builtin.cron", "args": {
                "name": "fulkro-backup", "state": "absent"}},
        ),
        params_schema={
            "repo": {"type": "string", "required": True,
                     "desc": "Destino del repositorio de copias"},
            "paths": {"type": "string", "required": True,
                      "desc": "Rutas a respaldar (separadas por espacio)"},
            "hour": {"type": "string", "default": "3"},
        },
        reversible=True,
        dry_run_summary=(
            "Instala restic y programa una copia diaria con verificación de "
            "restaurabilidad (restic check). No borra datos existentes."
        ),
    ),
    "configure_log_forwarding": HostPlaybookSpec(
        playbook_id="configure_log_forwarding",
        title_es="Activar registro y envío de logs (SIEM)",
        os_families=("linux", "windows"),
        check_assertion="log_forwarding_active",
        ansible_steps=(
            {"module": "ansible.builtin.package", "args": {
                "name": "rsyslog", "state": "present"}},
            {"module": "ansible.builtin.copy", "args": {
                "dest": "/etc/rsyslog.d/60-fulkro-siem.conf",
                "content": "*.* @@{{ siem_host }}:{{ siem_port }}\n",
                "backup": True}},
            {"module": "ansible.builtin.service", "args": {
                "name": "rsyslog", "state": "restarted"}},
        ),
        rollback_steps=(
            {"module": "ansible.builtin.file", "args": {
                "path": "/etc/rsyslog.d/60-fulkro-siem.conf", "state": "absent"}},
            {"module": "ansible.builtin.service", "args": {
                "name": "rsyslog", "state": "restarted"}},
        ),
        params_schema={
            "siem_host": {"type": "string", "required": True},
            "siem_port": {"type": "string", "default": "6514"},
        },
        reversible=True,
        dry_run_summary=(
            "Configura rsyslog para enviar la actividad al SIEM por TCP (TLS). "
            "No modifica logs locales existentes."
        ),
    ),
    "enable_host_firewall_baseline": HostPlaybookSpec(
        playbook_id="enable_host_firewall_baseline",
        title_es="Aplicar línea base de firewall (deny-by-default)",
        os_families=("linux",),
        check_assertion="firewall_baseline_active",
        ansible_steps=(
            {"module": "community.general.ufw", "args": {
                "direction": "incoming", "policy": "deny"}},
            {"module": "community.general.ufw", "args": {
                "rule": "allow", "port": "{{ allow_ports }}", "proto": "tcp"}},
            {"module": "community.general.ufw", "args": {"state": "enabled"}},
        ),
        rollback_steps=(
            {"module": "community.general.ufw", "args": {"state": "disabled"}},
        ),
        params_schema={
            "allow_ports": {"type": "string", "default": "22,443",
                            "desc": "Puertos a permitir (revisados con el cliente)"},
        },
        reversible=True,
        dry_run_summary=(
            "Deny-by-default en entrante + permite solo los puertos acordados. "
            "GUARDED: se previsualiza y aprueba para no cortar servicios en uso."
        ),
    ),
    "enroll_endpoint_edr": HostPlaybookSpec(
        playbook_id="enroll_endpoint_edr",
        title_es="Desplegar antimalware/EDR",
        os_families=("linux", "windows"),
        check_assertion="edr_enrolled",
        ansible_steps=(
            {"module": "ansible.builtin.package", "args": {
                "name": "{{ edr_package }}", "state": "present"}},
            {"module": "ansible.builtin.command", "args": {
                "cmd": "{{ edr_enroll_cmd }}"}},
        ),
        rollback_steps=(
            {"module": "ansible.builtin.package", "args": {
                "name": "{{ edr_package }}", "state": "absent"}},
        ),
        params_schema={
            "edr_package": {"type": "string", "required": True,
                            "desc": "Paquete del EDR del cliente (p.ej. wazuh-agent)"},
            "edr_enroll_cmd": {"type": "string", "required": True,
                               "desc": "Comando de enrolamiento provisto por el cliente"},
        },
        reversible=True,
        dry_run_summary=(
            "Instala y enrola el agente EDR del cliente. GUARDED: requiere los "
            "datos de enrolamiento del cliente."
        ),
    ),
}


def get_host_playbook(playbook_id: str) -> HostPlaybookSpec | None:
    return HOST_PLAYBOOKS.get(playbook_id)


def host_playbooks_for_os(os_family: str) -> list[HostPlaybookSpec]:
    return [p for p in HOST_PLAYBOOKS.values() if os_family in p.os_families]
