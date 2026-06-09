"""M8 v5.1 — Generador de guias de remediacion para PYME (spec §5.2).

Usa Claude Haiku para producir un paso-a-paso en espanol, con comandos
reales y verificacion. Si no hay API key disponible (tests, entornos
offline), se devuelve una guia deterministica basada en templates por
tipo de finding (tls/cve/web/hardening/ad).

Contrato JSON de salida:

    {
      "resumen_no_tecnico": "2 lineas para el gerente no tecnico",
      "riesgo_real": "que implicaria explotar esto, en 1-2 frases",
      "pasos": [
        {
          "paso": 1,
          "titulo": "...",
          "comando": "apt update && apt upgrade -y openssl",
          "explicacion": "Actualiza OpenSSL a la version corregida...",
          "verificacion": "openssl version -a | grep '3.0.'"
        }
      ],
      "tiempo_estimado": "15 minutos",
      "requiere_reinicio": false,
      "requiere_ventana_mantenimiento": false,
      "fuente": "haiku" | "deterministic_template"
    }
"""
from __future__ import annotations

import json

from loguru import logger

from backend.app.config import get_settings


SYSTEM_PROMPT = """Eres un consultor senior de ciberseguridad que explica remediaciones a PYMEs espanolas.
Tu trabajo es generar guias de remediacion claras, en espanol peninsular, con:

1. Un RESUMEN NO TECNICO de 2 lineas que cualquier gerente no tecnico entienda.
2. RIESGO REAL en 1-2 frases concretas (no abstracciones).
3. PASOS con comandos REALES que funcionen en Debian/Ubuntu/RHEL (apt, systemctl,
   openssl, ssh, etc.). NUNCA uses placeholders como <tu_host> o {host}; usa
   los valores concretos que te damos.
4. Cada paso lleva VERIFICACION — un comando que confirme que el paso se aplico.

Responde SIEMPRE con un JSON valido y NADA MAS. Sin texto antes o despues.
Si no conoces la remediacion concreta, di que requiere investigacion manual,
pero sigue el mismo schema.

Schema obligatorio:
{
  "resumen_no_tecnico": "...",
  "riesgo_real": "...",
  "pasos": [{"paso": 1, "titulo": "...", "comando": "...", "explicacion": "...", "verificacion": "..."}],
  "tiempo_estimado": "N minutos/horas",
  "requiere_reinicio": true|false,
  "requiere_ventana_mantenimiento": true|false
}
"""


def _build_user_prompt(finding: dict) -> str:
    title = finding.get("title", "")
    description = finding.get("description", "")
    severity = finding.get("severity", "")
    host = finding.get("affected_host", "")
    port = finding.get("affected_port")
    service = finding.get("affected_service") or ""
    url = finding.get("affected_url") or ""
    cve = finding.get("cve_id") or ""
    os_info = finding.get("affected_os") or "Linux (Debian/Ubuntu)"
    version = finding.get("affected_service_version") or ""

    location_parts = []
    if host:
        location_parts.append(f"host={host}")
    if port:
        location_parts.append(f"puerto={port}")
    if service:
        location_parts.append(f"servicio={service}")
    if version:
        location_parts.append(f"version={version}")
    if url:
        location_parts.append(f"url={url}")
    if cve:
        location_parts.append(f"CVE={cve}")
    location = " | ".join(location_parts) or "no especificado"

    return f"""Genera la guia de remediacion para este hallazgo de pentest:

TITULO: {title}
SEVERIDAD: {severity}
DESCRIPCION: {description}
LOCALIZACION: {location}
SO: {os_info}

Responde solo con el JSON del schema."""


def _deterministic_template(finding: dict) -> dict:
    """Fallback offline: templates por tipo de finding."""
    title = (finding.get("title") or "").lower()
    tool = (finding.get("tool_sources") or ["unknown"])
    if isinstance(tool, list) and tool:
        tool_hint = tool[0]
    else:
        tool_hint = str(tool)
    host = finding.get("affected_host") or "HOST"
    port = finding.get("affected_port") or 443
    cve = finding.get("cve_id") or ""

    if "tls" in title or "ssl" in title or tool_hint == "testssl":
        return {
            "resumen_no_tecnico": (
                "Uno de los servicios web de la organizacion usa cifrado TLS desactualizado. "
                "Hay que actualizarlo para evitar que datos en transito queden expuestos."
            ),
            "riesgo_real": (
                f"Un atacante en la misma red podria interceptar y descifrar comunicaciones "
                f"cifradas con {host}:{port}."
            ),
            "pasos": [
                {
                    "paso": 1,
                    "titulo": "Actualizar OpenSSL y la libreria del servidor",
                    "comando": "sudo apt update && sudo apt upgrade -y openssl libssl3",
                    "explicacion": "Actualiza OpenSSL a la ultima version con correcciones de seguridad.",
                    "verificacion": "openssl version",
                },
                {
                    "paso": 2,
                    "titulo": "Deshabilitar protocolos TLS antiguos en el servidor",
                    "comando": (
                        "sudo sed -i 's/^SSLProtocol.*$/SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1/'"
                        " /etc/apache2/mods-enabled/ssl.conf"
                    ),
                    "explicacion": "Deja solo TLS 1.2 y TLS 1.3 en Apache. Para nginx, editar /etc/nginx/nginx.conf.",
                    "verificacion": f"echo | openssl s_client -connect {host}:{port} -tls1_2 2>/dev/null | grep 'Protocol'",
                },
                {
                    "paso": 3,
                    "titulo": "Reiniciar el servicio web",
                    "comando": "sudo systemctl restart apache2 || sudo systemctl restart nginx",
                    "explicacion": "Aplica la nueva configuracion TLS.",
                    "verificacion": "sudo systemctl status apache2 || sudo systemctl status nginx",
                },
            ],
            "tiempo_estimado": "30 minutos",
            "requiere_reinicio": False,
            "requiere_ventana_mantenimiento": True,
            "fuente": "deterministic_template",
        }

    if cve or "cve" in title:
        return {
            "resumen_no_tecnico": (
                f"El sistema tiene una vulnerabilidad publicamente conocida ({cve or 'CVE pendiente'}). "
                "Aplicar el parche del fabricante elimina el riesgo."
            ),
            "riesgo_real": (
                f"Existen exploits publicos para esta vulnerabilidad; cualquier atacante puede aprovecharla "
                f"contra {host}:{port}."
            ),
            "pasos": [
                {
                    "paso": 1,
                    "titulo": "Actualizar el paquete afectado",
                    "comando": "sudo apt update && sudo apt upgrade -y",
                    "explicacion": "Instala todos los parches de seguridad disponibles.",
                    "verificacion": "apt list --upgradable 2>/dev/null | grep -i security",
                },
                {
                    "paso": 2,
                    "titulo": "Reiniciar servicios si el parche lo requiere",
                    "comando": "sudo needrestart -r a",
                    "explicacion": "Reinicia los servicios que usan las librerias actualizadas.",
                    "verificacion": "needrestart -b",
                },
            ],
            "tiempo_estimado": "20 minutos",
            "requiere_reinicio": True,
            "requiere_ventana_mantenimiento": True,
            "fuente": "deterministic_template",
        }

    if tool_hint == "zap" or "xss" in title or "sql" in title or "injection" in title:
        url = finding.get("affected_url") or f"https://{host}:{port}"
        return {
            "resumen_no_tecnico": (
                "La aplicacion web tiene una vulnerabilidad en la gestion de entrada de datos. "
                "Se parchea revisando el codigo y aplicando validaciones."
            ),
            "riesgo_real": (
                f"Un atacante podria manipular respuestas o extraer datos de la base de datos via {url}."
            ),
            "pasos": [
                {
                    "paso": 1,
                    "titulo": "Identificar el parametro vulnerable",
                    "comando": f"curl -sI '{url}' | head -20",
                    "explicacion": "Revisa el endpoint reportado y localiza el parametro en el codigo fuente.",
                    "verificacion": "grep -rn 'request.args' app/ | grep -v validated",
                },
                {
                    "paso": 2,
                    "titulo": "Aplicar validacion y sanitizacion",
                    "comando": "# Editar el handler e introducir validacion con bleach, pydantic o OWASP ESAPI",
                    "explicacion": "No concatenar entradas de usuario en SQL ni HTML sin escapar.",
                    "verificacion": "pytest tests/security/",
                },
                {
                    "paso": 3,
                    "titulo": "Re-desplegar y verificar",
                    "comando": "sudo systemctl restart <nombre-servicio-app>",
                    "explicacion": "Despliega la version corregida al entorno afectado.",
                    "verificacion": f"curl -sI '{url}' | head -5",
                },
            ],
            "tiempo_estimado": "2-4 horas",
            "requiere_reinicio": False,
            "requiere_ventana_mantenimiento": False,
            "fuente": "deterministic_template",
        }

    if tool_hint == "lynis" or "hardening" in title or "config" in title:
        return {
            "resumen_no_tecnico": (
                "La configuracion del sistema no cumple con las guias de endurecimiento CCN-STIC. "
                "Se corrige aplicando parametros seguros estandar."
            ),
            "riesgo_real": (
                f"Configuracion laxa en {host} facilita movimientos laterales tras una intrusion."
            ),
            "pasos": [
                {
                    "paso": 1,
                    "titulo": "Revisar hallazgo detallado de Lynis",
                    "comando": "sudo lynis audit system --quick",
                    "explicacion": "Genera el informe completo para identificar el fichero a modificar.",
                    "verificacion": "sudo tail -50 /var/log/lynis.log",
                },
                {
                    "paso": 2,
                    "titulo": "Aplicar correccion sugerida",
                    "comando": "# Editar el fichero indicado por Lynis segun CCN-STIC 619",
                    "explicacion": "Cada control Lynis aporta su referencia a CCN-STIC. Aplicar exactamente eso.",
                    "verificacion": "sudo lynis audit system --tests " + (finding.get("tool_metadata", {}).get("control_id", "")) if isinstance(finding.get("tool_metadata"), dict) else "sudo lynis audit system",
                },
            ],
            "tiempo_estimado": "1 hora",
            "requiere_reinicio": False,
            "requiere_ventana_mantenimiento": False,
            "fuente": "deterministic_template",
        }

    # Generico
    return {
        "resumen_no_tecnico": (
            "Se ha detectado una debilidad que requiere intervencion manual del responsable tecnico."
        ),
        "riesgo_real": (
            "Sin corregir, este hallazgo puede dar al atacante una via adicional contra el sistema."
        ),
        "pasos": [
            {
                "paso": 1,
                "titulo": "Revisar el detalle tecnico y aplicar remediacion del fabricante",
                "comando": "# Consultar documentacion oficial del producto afectado",
                "explicacion": "Cada producto tiene su propia guia de remediacion oficial.",
                "verificacion": "# Ejecutar re-test de la herramienta original (nuclei / testssl / zap)",
            },
        ],
        "tiempo_estimado": "requiere investigacion",
        "requiere_reinicio": False,
        "requiere_ventana_mantenimiento": False,
        "fuente": "deterministic_template",
    }


def _validate_guide_shape(guide: dict) -> bool:
    """Verifica que el JSON tenga la estructura minima esperada."""
    required = {
        "resumen_no_tecnico", "riesgo_real", "pasos",
        "tiempo_estimado", "requiere_reinicio", "requiere_ventana_mantenimiento",
    }
    if not isinstance(guide, dict):
        return False
    if not required.issubset(guide.keys()):
        return False
    pasos = guide.get("pasos") or []
    if not isinstance(pasos, list) or not pasos:
        return False
    for p in pasos:
        if not isinstance(p, dict):
            return False
        for key in ("paso", "titulo", "comando", "explicacion", "verificacion"):
            if key not in p:
                return False
    return True


def generate_guide(
    finding: dict,
    *,
    llm_router=None,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 1500,
    force_offline: bool = False,
) -> dict:
    """Genera la guia de remediacion para un finding.

    ``finding`` es un dict con los campos del VerificationFinding (o un
    snapshot equivalente). Si Haiku responde con un JSON valido, se usa;
    en caso contrario se cae al template deterministico.
    """
    if force_offline or not get_settings().anthropic_api_key.get_secret_value():
        return _deterministic_template(finding)

    try:
        from backend.app.core.ai.llm_router import get_default_llm_router
        router = llm_router or get_default_llm_router()
        resp = router.complete(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(finding)},
            ],
            model=model,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        content = (resp.content or "").strip()
        # Limpieza: quitar fences ```json si llegan
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        guide = json.loads(content)
        if _validate_guide_shape(guide):
            guide["fuente"] = "haiku"
            return guide
        logger.warning("Haiku guide failed shape validation; fallback deterministic")
    except Exception as exc:  # pragma: no cover — red path
        logger.warning("Haiku guide generation failed: {}; fallback deterministic", exc)

    return _deterministic_template(finding)


def finding_to_guide_input(f) -> dict:
    """Convierte un VerificationFinding (SQLAlchemy) a dict para el generator."""
    return {
        "title": f.title,
        "description": f.description,
        "severity": f.severity,
        "affected_host": f.affected_host,
        "affected_port": f.affected_port,
        "affected_service": f.affected_service,
        "affected_service_version": f.affected_service_version,
        "affected_url": f.affected_url,
        "affected_os": f.affected_os,
        "cve_id": f.cve_id,
        "tool_sources": f.tool_sources,
    }
