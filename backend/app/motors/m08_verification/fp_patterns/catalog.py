"""M8 v5.1 — Base de False-Positive patterns conocidos.

100+ patrones iniciales para los scanners reales de la pipeline. La
spec v5.1 §3.3 anticipa ~500 patrones tras varios engagements; estos
100 cubren los FPs mas comunes en proyectos ENS Basica y Media.

Cada patron declarado aqui se sincroniza a la tabla
``false_positive_patterns`` la primera vez que arranca el motor
(seed idempotente). Marcos puede anadir mas marcando findings como
'false_positive' en el portal — la tabla los persiste y el catalogo
local sirve solo de bootstrap.

Estructura de cada patron:
    {
      "tool": "nuclei" | "openvas" | "zap" | "lynis" | "testssl" | "nmap",
      "pattern": str (substring match contra titulo del finding),
      "condition_jsonb": dict | None (condiciones adicionales contra
          tool_metadata o severity),
      "reason": str (explicacion para el auditor),
    }
"""
from __future__ import annotations

from typing import Any


FALSE_POSITIVE_PATTERNS: list[dict[str, Any]] = [
    # ════════════════════════════════════════════════════════════════
    # NUCLEI — 25 patrones FP comunes
    # ════════════════════════════════════════════════════════════════
    {
        "tool": "nuclei",
        "pattern": "wordpress-detect",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Deteccion de tecnologia, no vulnerabilidad explotable",
    },
    {
        "tool": "nuclei",
        "pattern": "tech-detect",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Templates 'tech-detect' identifican stack, no fallos",
    },
    {
        "tool": "nuclei",
        "pattern": "favicon-detect",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Fingerprinting de favicon — no es vulnerabilidad",
    },
    {
        "tool": "nuclei",
        "pattern": "robots-txt",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Lectura de robots.txt no es hallazgo per se",
    },
    {
        "tool": "nuclei",
        "pattern": "sitemap-detect",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Sitemap publico es estandar SEO, no vulnerabilidad",
    },
    {
        "tool": "nuclei",
        "pattern": "wp-login",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Existencia de wp-login es esperada en WordPress publico",
    },
    {
        "tool": "nuclei",
        "pattern": "options-method",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "OPTIONS habilitado no es vuln en sitios publicos",
    },
    {
        "tool": "nuclei",
        "pattern": "default-page",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Pagina default detectada — no implica acceso elevado",
    },
    {
        "tool": "nuclei",
        "pattern": "metatag-cms",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Metatag generator es deteccion, no vulnerabilidad",
    },
    {
        "tool": "nuclei",
        "pattern": "ssl-issuer",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Issuer de certificado: telemetria, no debilidad",
    },
    {
        "tool": "nuclei",
        "pattern": "ssl-dns-names",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Lista de SANs en cert es publica por diseno",
    },
    {
        "tool": "nuclei",
        "pattern": "weak-cipher-suites",
        "condition_jsonb": {"port_in": [25, 587]},
        "reason": "STARTTLS SMTP: ciphers debiles aceptados por compat con remitentes legacy",
    },
    {
        "tool": "nuclei",
        "pattern": "http-missing-security-headers",
        "condition_jsonb": {"path_contains": ["/static/", "/assets/", "/css/"]},
        "reason": "Falta de cabeceras en assets estaticos no es explotable",
    },
    {
        "tool": "nuclei",
        "pattern": "x-content-type-options",
        "condition_jsonb": {"content_type_contains": "text/css"},
        "reason": "X-Content-Type-Options no aplica a CSS servido como text/css",
    },
    {
        "tool": "nuclei",
        "pattern": "cookie-without-secure",
        "condition_jsonb": {"environment": "dev"},
        "reason": "En entornos dev sin TLS la cookie sin Secure es esperada",
    },
    {
        "tool": "nuclei",
        "pattern": "exposed-svn",
        "condition_jsonb": {"path_pattern": "/.svn/empty"},
        "reason": "Carpeta .svn vacia por convencion de despliegue",
    },
    {
        "tool": "nuclei",
        "pattern": "git-config",
        "condition_jsonb": {"http_status": 403},
        "reason": "Servidor responde 403 al intentar leer .git/config (correcto)",
    },
    {
        "tool": "nuclei",
        "pattern": "swagger-api",
        "condition_jsonb": {"environment": "dev"},
        "reason": "Swagger UI accesible en dev; en prod debe restringirse",
    },
    {
        "tool": "nuclei",
        "pattern": "graphql-detect",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Endpoint GraphQL detectado: no implica introspection abierto",
    },
    {
        "tool": "nuclei",
        "pattern": "jenkins-login",
        "condition_jsonb": {"http_status": 200},
        "reason": "Pagina login Jenkins accesible es esperada con auth",
    },
    {
        "tool": "nuclei",
        "pattern": "phpmyadmin-detect",
        "condition_jsonb": {"environment": "dev"},
        "reason": "phpMyAdmin solo accesible internamente en dev",
    },
    {
        "tool": "nuclei",
        "pattern": "kibana-detect",
        "condition_jsonb": {"http_status": 401},
        "reason": "Kibana detectado pero requiere autenticacion (401 esperado)",
    },
    {
        "tool": "nuclei",
        "pattern": "elastic-search",
        "condition_jsonb": {"http_status": 401},
        "reason": "Elastic con auth: 401 esperado",
    },
    {
        "tool": "nuclei",
        "pattern": "header-disclosure",
        "condition_jsonb": {"header_name": "Server"},
        "reason": "Cabecera Server informativa no constituye CVE",
    },
    {
        "tool": "nuclei",
        "pattern": "powered-by-disclosure",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "X-Powered-By informativo (mejor practica ocultarlo, no vuln)",
    },

    # ════════════════════════════════════════════════════════════════
    # OPENVAS — 25 patrones FP
    # ════════════════════════════════════════════════════════════════
    {
        "tool": "openvas",
        "pattern": "SSH Weak MAC Algorithms",
        "condition_jsonb": {"ssh_version_gte": "8.9"},
        "reason": "OpenSSH 8.9+ negocia MAC seguros por defecto; reporte heredado",
    },
    {
        "tool": "openvas",
        "pattern": "TCP timestamps",
        "condition_jsonb": {"severity_lte": "low"},
        "reason": "TCP timestamps informativo, no explotable en contexto ENS",
    },
    {
        "tool": "openvas",
        "pattern": "ICMP Timestamp Reply",
        "condition_jsonb": {"severity_lte": "low"},
        "reason": "ICMP timestamp es informativo y a menudo necesario para diagnostico",
    },
    {
        "tool": "openvas",
        "pattern": "Traceroute Detection",
        "condition_jsonb": {"severity_lte": "low"},
        "reason": "Respuesta a traceroute no es vulnerabilidad",
    },
    {
        "tool": "openvas",
        "pattern": "OS Detection",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Fingerprinting OS no es vulnerabilidad",
    },
    {
        "tool": "openvas",
        "pattern": "SSH Server Type and Version Information",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Banner SSH visible es estandar; ocultarlo no anade seguridad real",
    },
    {
        "tool": "openvas",
        "pattern": "HTTP Server Type and Version",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Banner HTTP informativo",
    },
    {
        "tool": "openvas",
        "pattern": "DCE/RPC and MSRPC Services Enumeration",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Enumeracion RPC sin acceso explotable",
    },
    {
        "tool": "openvas",
        "pattern": "SSL/TLS: Certificate Signed Using A Weak Signature Algorithm",
        "condition_jsonb": {"signature_algo_contains": "sha1"},
        "reason": "SHA-1 deprecado pero residual en certs internos legacy; vencimiento programado",
    },
    {
        "tool": "openvas",
        "pattern": "SSL/TLS: Diffie-Hellman Key Exchange Insufficient DH Group Strength",
        "condition_jsonb": {"dh_bits_gte": 2048},
        "reason": "DH >=2048 bits es aceptable en NIST SP 800-131A actual",
    },
    {
        "tool": "openvas",
        "pattern": "SMTP Open Relay Detection",
        "condition_jsonb": {"port_in": [25], "smtp_auth_required": True},
        "reason": "Servidor SMTP requiere auth; falso positivo del test de relay",
    },
    {
        "tool": "openvas",
        "pattern": "Apache HTTP Server <= 2.4.x Status Page",
        "condition_jsonb": {"http_status": 403},
        "reason": "/server-status responde 403; mod_status restringido correctamente",
    },
    {
        "tool": "openvas",
        "pattern": "PHP Information Disclosure",
        "condition_jsonb": {"path_contains": ["/info.php", "/phpinfo.php"], "http_status": 404},
        "reason": "phpinfo() devuelve 404 (no expuesto)",
    },
    {
        "tool": "openvas",
        "pattern": "Cleartext Transmission of Sensitive Information",
        "condition_jsonb": {"path_contains": ["/health", "/status"]},
        "reason": "Healthchecks no transmiten informacion sensible",
    },
    {
        "tool": "openvas",
        "pattern": "Anonymous FTP Login Reporting",
        "condition_jsonb": {"path_contains": ["/pub/"]},
        "reason": "FTP anonimo intencional para repositorio publico",
    },
    {
        "tool": "openvas",
        "pattern": "Microsoft Windows SMB Service NULL Session Authentication",
        "condition_jsonb": {"smb_signing_required": True},
        "reason": "SMB signing forzado mitiga sesiones nulas",
    },
    {
        "tool": "openvas",
        "pattern": "Conficker Detection",
        "condition_jsonb": {"os_contains": "linux"},
        "reason": "Conficker es malware Windows; FP sobre host Linux",
    },
    {
        "tool": "openvas",
        "pattern": "DCE Services Enumeration Reporting",
        "condition_jsonb": {"severity_eq": "low"},
        "reason": "Enumeracion DCE sin acceso explotable",
    },
    {
        "tool": "openvas",
        "pattern": "Web Application Default Credentials",
        "condition_jsonb": {"login_succeeded": False},
        "reason": "Probaron creds default y NO funcionaron — finding informativo",
    },
    {
        "tool": "openvas",
        "pattern": "SNMP Default Community String",
        "condition_jsonb": {"snmp_response": False},
        "reason": "Servidor no responde a community public/private (correcto)",
    },
    {
        "tool": "openvas",
        "pattern": "MySQL/MariaDB Version Disclosure",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Banner MySQL informativo, no exploit",
    },
    {
        "tool": "openvas",
        "pattern": "Postgres Version Disclosure",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Banner PostgreSQL informativo",
    },
    {
        "tool": "openvas",
        "pattern": "VMware ESXi Version Detection",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Deteccion ESXi sin CVE asociada",
    },
    {
        "tool": "openvas",
        "pattern": "Kerberos username enumeration",
        "condition_jsonb": {"ad_minimum_2019": True},
        "reason": "AD 2019+ mitigado contra enumeracion AS-REP",
    },
    {
        "tool": "openvas",
        "pattern": "Telnet Server Type and Version",
        "condition_jsonb": {"port_in": [23], "internal_lab_only": True},
        "reason": "Telnet en lab interno aislado del resto",
    },

    # ════════════════════════════════════════════════════════════════
    # ZAP — 25 patrones FP
    # ════════════════════════════════════════════════════════════════
    {
        "tool": "zap",
        "pattern": "X-Content-Type-Options Header Missing",
        "condition_jsonb": {"content_type_contains": "text/css"},
        "reason": "X-Content-Type-Options no aplica a CSS",
    },
    {
        "tool": "zap",
        "pattern": "X-Content-Type-Options Header Missing",
        "condition_jsonb": {"content_type_contains": "image/"},
        "reason": "No aplica a imagenes",
    },
    {
        "tool": "zap",
        "pattern": "X-Frame-Options Header Not Set",
        "condition_jsonb": {"path_contains": ["/embed/", "/oembed/"]},
        "reason": "Endpoints disenados para embedding (oembed)",
    },
    {
        "tool": "zap",
        "pattern": "X-Frame-Options Header Not Set",
        "condition_jsonb": {"csp_frame_ancestors_present": True},
        "reason": "CSP frame-ancestors sustituye X-Frame-Options",
    },
    {
        "tool": "zap",
        "pattern": "Strict-Transport-Security Header Not Set",
        "condition_jsonb": {"http_or_intranet": True},
        "reason": "HSTS no aplica en HTTP plano (intranet sin TLS)",
    },
    {
        "tool": "zap",
        "pattern": "Cookie No HttpOnly Flag",
        "condition_jsonb": {"cookie_name_contains": ["XSRF-TOKEN", "csrftoken"]},
        "reason": "Tokens CSRF deben ser leibles por JavaScript por diseno",
    },
    {
        "tool": "zap",
        "pattern": "Cookie Without Secure Flag",
        "condition_jsonb": {"environment": "dev"},
        "reason": "Dev sin TLS",
    },
    {
        "tool": "zap",
        "pattern": "Cross-Domain JavaScript Source File Inclusion",
        "condition_jsonb": {"source_domain_in_whitelist": True},
        "reason": "Dominio externo en allowlist (CDN propio)",
    },
    {
        "tool": "zap",
        "pattern": "Information Disclosure - Suspicious Comments",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Comentarios HTML 'TODO/FIXME' sin info sensible",
    },
    {
        "tool": "zap",
        "pattern": "Information Disclosure - Sensitive Information in URL",
        "condition_jsonb": {"path_contains": ["/api/v1/", "/docs/"]},
        "reason": "Versionado en URL es estandar REST",
    },
    {
        "tool": "zap",
        "pattern": "Application Error Disclosure",
        "condition_jsonb": {"environment": "dev"},
        "reason": "Stacktraces visibles solo en dev (Django DEBUG=True)",
    },
    {
        "tool": "zap",
        "pattern": "Reverse Tabnabbing",
        "condition_jsonb": {"target_attr": "_blank", "rel_attr_contains": "noopener"},
        "reason": "Mitigacion correcta con rel=noopener noreferrer",
    },
    {
        "tool": "zap",
        "pattern": "Session ID in URL Rewrite",
        "condition_jsonb": {"path_contains": ["/oauth/", "/saml/"]},
        "reason": "Tokens en URL son parte del flujo OAuth/SAML estandar",
    },
    {
        "tool": "zap",
        "pattern": "Server Leaks Version Information via 'Server' HTTP Response Header Field",
        "condition_jsonb": {"severity_lte": "low"},
        "reason": "Banner Server informativo, mitigacion menor",
    },
    {
        "tool": "zap",
        "pattern": "Web Browser XSS Protection Not Enabled",
        "condition_jsonb": {"csp_present": True},
        "reason": "Cabecera X-XSS-Protection deprecada; CSP la sustituye",
    },
    {
        "tool": "zap",
        "pattern": "Anti-CSRF Tokens Check",
        "condition_jsonb": {"http_method_eq": "GET"},
        "reason": "GET no requiere CSRF token",
    },
    {
        "tool": "zap",
        "pattern": "Modern Web Application",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Detecta SPA — informativo, no vuln",
    },
    {
        "tool": "zap",
        "pattern": "Charset Mismatch",
        "condition_jsonb": {"content_type_contains": "json"},
        "reason": "JSON sin charset declarado pero parseable como UTF-8",
    },
    {
        "tool": "zap",
        "pattern": "Loosely Scoped Cookie",
        "condition_jsonb": {"cookie_domain_eq_host": True},
        "reason": "Cookie limitada al host actual (no a todo el dominio)",
    },
    {
        "tool": "zap",
        "pattern": "Storable and Cacheable Content",
        "condition_jsonb": {"content_type_contains": ["image/", "text/css", "application/javascript"]},
        "reason": "Cacheabilidad esperada de assets estaticos",
    },
    {
        "tool": "zap",
        "pattern": "Re-examine Cache-control Directives",
        "condition_jsonb": {"path_contains": ["/static/", "/assets/"]},
        "reason": "Static assets con cache largo es buena practica",
    },
    {
        "tool": "zap",
        "pattern": "Format String Error",
        "condition_jsonb": {"severity_lte": "low"},
        "reason": "Falso positivo en plantillas Jinja2 que reflejan input intencionalmente",
    },
    {
        "tool": "zap",
        "pattern": "GET for POST",
        "condition_jsonb": {"endpoint_idempotent": True},
        "reason": "Endpoint idempotente: GET o POST equivalentes por diseno",
    },
    {
        "tool": "zap",
        "pattern": "User Controllable HTML Element Attribute",
        "condition_jsonb": {"attribute_in": ["data-id", "data-uuid"]},
        "reason": "Atributos data-* sanitizados; no vector XSS",
    },
    {
        "tool": "zap",
        "pattern": "Big Redirect Detected",
        "condition_jsonb": {"path_contains": ["/oauth/", "/saml/"]},
        "reason": "Redirects largos son normales en flujos OAuth/SAML con state",
    },

    # ════════════════════════════════════════════════════════════════
    # LYNIS — 22 patrones FP
    # ════════════════════════════════════════════════════════════════
    {
        "tool": "lynis",
        "pattern": "PKGS-7350",
        "condition_jsonb": None,
        "reason": "'No tool found to ...': falsa alerta cuando se usan otros tools",
    },
    {
        "tool": "lynis",
        "pattern": "PKGS-7392",
        "condition_jsonb": {"distro_in": ["ubuntu_22.04", "ubuntu_24.04"]},
        "reason": "Vulnerabilidades de paquetes con upstream patcheado en Ubuntu LTS",
    },
    {
        "tool": "lynis",
        "pattern": "BANN-7126",
        "condition_jsonb": None,
        "reason": "Banner /etc/issue: opcional segun politica corporativa",
    },
    {
        "tool": "lynis",
        "pattern": "BANN-7130",
        "condition_jsonb": None,
        "reason": "Banner /etc/issue.net: opcional",
    },
    {
        "tool": "lynis",
        "pattern": "AUTH-9282",
        "condition_jsonb": {"min_len_actual_gte": 10},
        "reason": "PASS_MIN_LEN >=10 ya cumple ENS; warning legacy",
    },
    {
        "tool": "lynis",
        "pattern": "AUTH-9286",
        "condition_jsonb": None,
        "reason": "Hash sha512 ya configurado en /etc/login.defs",
    },
    {
        "tool": "lynis",
        "pattern": "FILE-6310",
        "condition_jsonb": None,
        "reason": "Particion /tmp como tmpfs en lugar de mount: alternativa valida",
    },
    {
        "tool": "lynis",
        "pattern": "FILE-7524",
        "condition_jsonb": {"world_writable_allowlist": True},
        "reason": "Ficheros world-writable autorizados (sockets dev)",
    },
    {
        "tool": "lynis",
        "pattern": "USB-1000",
        "condition_jsonb": None,
        "reason": "USBGuard no necesario en servidores headless",
    },
    {
        "tool": "lynis",
        "pattern": "STRG-1840",
        "condition_jsonb": None,
        "reason": "Wireless desactivado por defecto en servidores",
    },
    {
        "tool": "lynis",
        "pattern": "STRG-1846",
        "condition_jsonb": None,
        "reason": "Bluetooth desactivado",
    },
    {
        "tool": "lynis",
        "pattern": "BOOT-5122",
        "condition_jsonb": None,
        "reason": "GRUB password no aplica en servidores con acceso fisico restringido",
    },
    {
        "tool": "lynis",
        "pattern": "KRNL-5820",
        "condition_jsonb": None,
        "reason": "core dumps deshabilitados via systemd, no via sysctl",
    },
    {
        "tool": "lynis",
        "pattern": "AUTH-9230",
        "condition_jsonb": None,
        "reason": "PAM ldap configurado por chef/ansible (no detectado por Lynis)",
    },
    {
        "tool": "lynis",
        "pattern": "FINT-4350",
        "condition_jsonb": None,
        "reason": "AIDE/Tripwire reemplazado por OSSEC/Wazuh",
    },
    {
        "tool": "lynis",
        "pattern": "MAIL-8818",
        "condition_jsonb": None,
        "reason": "MTA local desactivado intencionalmente (logs externos)",
    },
    {
        "tool": "lynis",
        "pattern": "SSH-7440",
        "condition_jsonb": {"protocol_eq": 2},
        "reason": "SSH protocolo 2 ya forzado",
    },
    {
        "tool": "lynis",
        "pattern": "SSH-7408",
        "condition_jsonb": {"port_eq": 22, "fail2ban_active": True},
        "reason": "Puerto 22 estandar; fail2ban mitiga brute force",
    },
    {
        "tool": "lynis",
        "pattern": "SCHD-7702",
        "condition_jsonb": None,
        "reason": "atd no usado; cron es suficiente",
    },
    {
        "tool": "lynis",
        "pattern": "TIME-3104",
        "condition_jsonb": None,
        "reason": "ntpd o chrony ya configurado pero Lynis no detecta",
    },
    {
        "tool": "lynis",
        "pattern": "PRNT-2308",
        "condition_jsonb": None,
        "reason": "CUPS deshabilitado en servidores sin impresion",
    },
    {
        "tool": "lynis",
        "pattern": "INSE-8001",
        "condition_jsonb": None,
        "reason": "Servicio inetd no instalado (correcto, no warning)",
    },

    # ════════════════════════════════════════════════════════════════
    # TESTSSL.SH — 12 patrones FP
    # ════════════════════════════════════════════════════════════════
    {
        "tool": "testssl",
        "pattern": "secure_renego",
        "condition_jsonb": {"severity_lte": "low"},
        "reason": "Servidor moderno: secure renegotiation soportado",
    },
    {
        "tool": "testssl",
        "pattern": "client_auth",
        "condition_jsonb": {"severity_lte": "info"},
        "reason": "Mutual TLS no requerido para web publica",
    },
    {
        "tool": "testssl",
        "pattern": "TLS_extensions",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "Lista de extensiones TLS es informativa",
    },
    {
        "tool": "testssl",
        "pattern": "session_resumption",
        "condition_jsonb": {"severity_lte": "low"},
        "reason": "Resumption habilitado mejora UX, no es debilidad",
    },
    {
        "tool": "testssl",
        "pattern": "OCSP_stapling",
        "condition_jsonb": None,
        "reason": "OCSP stapling es plus, no fallo critico si falta",
    },
    {
        "tool": "testssl",
        "pattern": "DH_groups",
        "condition_jsonb": {"dh_bits_gte": 2048},
        "reason": "DH group >= 2048 bits aceptable",
    },
    {
        "tool": "testssl",
        "pattern": "FREAK",
        "condition_jsonb": {"openssl_version_gte": "1.1.0"},
        "reason": "OpenSSL >= 1.1.0 mitiga FREAK",
    },
    {
        "tool": "testssl",
        "pattern": "LOGJAM",
        "condition_jsonb": {"openssl_version_gte": "1.1.0"},
        "reason": "OpenSSL >= 1.1.0 mitiga LOGJAM",
    },
    {
        "tool": "testssl",
        "pattern": "CRIME",
        "condition_jsonb": {"compression_disabled": True},
        "reason": "Compression TLS deshabilitada — CRIME no aplica",
    },
    {
        "tool": "testssl",
        "pattern": "LUCKY13",
        "condition_jsonb": {"cbc_mac_disabled": True},
        "reason": "CBC ciphers deshabilitados — LUCKY13 no explotable",
    },
    {
        "tool": "testssl",
        "pattern": "TLSv1_3",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "TLS 1.3 soportado: deteccion informativa positiva",
    },
    {
        "tool": "testssl",
        "pattern": "fallback_SCSV",
        "condition_jsonb": {"severity_eq": "info"},
        "reason": "TLS_FALLBACK_SCSV soportado correctamente",
    },

    # ════════════════════════════════════════════════════════════════
    # NMAP — 10 patrones FP
    # ════════════════════════════════════════════════════════════════
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 80/tcp",
        "condition_jsonb": {"target_role": "web_public"},
        "reason": "Puerto 80 abierto en web publica es esperado (redirect a 443)",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 443/tcp",
        "condition_jsonb": {"target_role": "web_public"},
        "reason": "Puerto 443 abierto en web publica es la operacion normal",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 22/tcp",
        "condition_jsonb": {"jump_host": True, "fail2ban_active": True},
        "reason": "SSH en bastion con fail2ban; vector controlado",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 25/tcp",
        "condition_jsonb": {"target_role": "smtp_relay", "smtp_auth_required": True},
        "reason": "Servidor SMTP relay autenticado",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 53/tcp",
        "condition_jsonb": {"target_role": "dns_server"},
        "reason": "DNS server: 53/tcp esperado para zone transfers controlados",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 3306/tcp",
        "condition_jsonb": {"firewall_restricts_to_app_subnet": True},
        "reason": "MySQL accesible solo desde app subnet via firewall",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 5432/tcp",
        "condition_jsonb": {"firewall_restricts_to_app_subnet": True},
        "reason": "PostgreSQL accesible solo desde app subnet",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 6379/tcp",
        "condition_jsonb": {"redis_requirepass": True},
        "reason": "Redis con requirepass habilitado",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 9200/tcp",
        "condition_jsonb": {"elastic_basic_auth": True},
        "reason": "Elasticsearch con auth basico",
    },
    {
        "tool": "nmap",
        "pattern": "Puerto abierto 8080/tcp",
        "condition_jsonb": {"target_role": "internal_app"},
        "reason": "Apps internas tipicamente en 8080",
    },
]


def get_patterns_for_tool(tool: str) -> list[dict[str, Any]]:
    """Devuelve los patrones FP para una herramienta concreta."""
    return [p for p in FALSE_POSITIVE_PATTERNS if p["tool"] == tool]


def total_patterns() -> int:
    return len(FALSE_POSITIVE_PATTERNS)


def patterns_by_tool_count() -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in FALSE_POSITIVE_PATTERNS:
        counts[p["tool"]] = counts.get(p["tool"], 0) + 1
    return counts
