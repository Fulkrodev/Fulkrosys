"""Quick wins deterministas. Reglas explicitas, no LLM."""
from __future__ import annotations

QUICK_WIN_RULES: list[dict] = [
    {
        "id": "qw-roles-ens",
        "titulo": "Nombrar formalmente los roles ENS obligatorios",
        "descripcion": "Faltan roles ENS obligatorios. Sin ellos la auditoria no procede.",
        "esfuerzo": "bajo", "impacto": "critico", "horas_estimadas": 1,
        "medida_ens": "org.1",
        "condition": lambda d: d.get("stakeholder_analysis", {}).get("critical_gaps", 0) > 0,
    },
    {
        "id": "qw-contratos-art28",
        "titulo": "Formalizar contratos Art. 28 RGPD con proveedores criticos",
        "descripcion": "Contratos de encargado incompletos. NC inmediata en auditoria.",
        "esfuerzo": "medio", "impacto": "critico", "horas_estimadas": 8,
        "medida_ens": "op.ext.1",
        "condition": lambda d: d.get("maturity_scoring", {}).get("domains", {}).get("mp_info", {}).get("points", 0) < 4,
    },
    {
        "id": "qw-mfa-universal",
        "titulo": "Activar MFA universal para todos los usuarios",
        "descripcion": "MFA no esta habilitado para todos. Reduce el 80% del riesgo de compromiso.",
        "esfuerzo": "bajo", "impacto": "alto", "horas_estimadas": 2,
        "medida_ens": "op.acc.6",
        "condition": lambda d: d.get("maturity_scoring", {}).get("domains", {}).get("op_acc", {}).get("points", 0) < 3,
    },
    {
        "id": "qw-backup-formal",
        "titulo": "Formalizar estrategia de backup con pruebas de restauracion",
        "descripcion": "Backup sin proceso formal. ENS requiere copias verificadas.",
        "esfuerzo": "bajo", "impacto": "alto", "horas_estimadas": 4,
        "medida_ens": "mp.info.6",
        "condition": lambda d: d.get("maturity_scoring", {}).get("domains", {}).get("op_cont", {}).get("points", 0) < 2,
    },
    {
        "id": "qw-dpo",
        "titulo": "Designar DPO (Delegado de Proteccion de Datos)",
        "descripcion": "No hay DPO designado. Obligatorio por RGPD para ciertos tratamientos.",
        "esfuerzo": "bajo", "impacto": "alto", "horas_estimadas": 2,
        "medida_ens": "mp.info.1",
        "condition": lambda d: "dpo" in [r.get("role_key") for r in d.get("stakeholder_analysis", {}).get("missing_additional_roles", [])],
    },
    {
        "id": "qw-siem",
        "titulo": "Implantar SIEM o monitorizacion centralizada",
        "descripcion": "No hay SIEM. ENS Medio requiere monitorizacion continua.",
        "esfuerzo": "medio", "impacto": "alto", "horas_estimadas": 20,
        "medida_ens": "op.mon.1",
        "condition": lambda d: d.get("maturity_scoring", {}).get("domains", {}).get("op_mon", {}).get("points", 0) == 0,
    },
    {
        "id": "qw-mdm",
        "titulo": "Implantar gestion centralizada de endpoints (MDM/UEM)",
        "descripcion": "Endpoints no gestionados. Riesgo de dispositivos sin control.",
        "esfuerzo": "medio", "impacto": "medio", "horas_estimadas": 16,
        "medida_ens": "op.exp.2",
        "condition": lambda d: "MDM" not in str(d.get("maturity_scoring", {}).get("domains", {}).get("op_exp", {}).get("rules_matched", [])),
    },
    {
        "id": "qw-pentest",
        "titulo": "Realizar pentest externo (obligatorio ENS Medio+)",
        "descripcion": "No hay pentest reciente. ENS Medio requiere pentest anual.",
        "esfuerzo": "alto", "impacto": "alto", "horas_estimadas": 40,
        "medida_ens": "mp.s.2",
        "condition": lambda d: "pentest" not in str(d.get("maturity_scoring", {}).get("domains", {}).get("op_exp", {}).get("rules_matched", [])).lower(),
    },
]


def generate_quick_wins(diagnosis_data: dict) -> list[dict]:
    wins = []
    for rule in QUICK_WIN_RULES:
        try:
            if rule["condition"](diagnosis_data):
                wins.append({k: v for k, v in rule.items() if k != "condition"})
        except Exception:
            continue
    priority = {"critico": 0, "alto": 1, "medio": 2, "bajo": 3}
    effort = {"bajo": 0, "medio": 1, "alto": 2}
    wins.sort(key=lambda w: (priority.get(w["impacto"], 9), effort.get(w["esfuerzo"], 9)))
    return wins
