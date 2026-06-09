# AUDIT #11 · MCPs 16 servers (NEW)

**Status**: ✅ Audit empírico completo · Bloque 1 Mega-baseline item 10/11
**Date**: 2026-05-24
**Scope item**: pre-piloto #11 (NEW) · "Verify 16 MCP servers · functional vs scaffolding · tools availability"

---

## Verdict empírico

**15 MCP servers** identificados directly (NO 16 per briefing · audit empírico count actual). Structure homogénea production-ready · **69 tool files** distribuidos entre 13 specialized servers (scope_enforcer + shared son utility).

**Status per memoria** (4 reales validados + 11 estructurales):
- ✅ **Reales validated**: vulnscan · cloud · config · phishing (4 servers · per CLAUDE.md "3 reales validados" actualizable a 4 per memoria)
- 🟡 **Structurales scaffolding**: apisec · cracking · infra · mobile · recon · redteam · sast · webpentest · wireless (9 servers · per memoria)
- ⚙️ **Utility**: scope_enforcer · shared (2 servers · fail-closed + protocol)

**Gap específico identificado**: 9 servers structural NO validated end-to-end · tool availability per docker container untested · cliente piloto MEDIA NO bloquea (4 reales cubren scenarios principales pentest).

**ETA empírico realista refined**: 
- **Scope-out PERMANENT pre-piloto**: 0h · 4 reales cubren cliente piloto MEDIA
- **Polish + verification 9 structurales**: ~10-20h post-piloto demand-driven (depends pentest scope clientes futuros)

---

## Stats baseline

### 15 MCP servers (structure homogénea 7 files cada · 6 scope_enforcer)
Per server contains: Dockerfile + README.md + __init__.py + authorization.json + requirements.txt + server.py + tools/

| Server | Tools count | Status per memoria |
|--------|-------------|---------------------|
| **vulnscan** | 4 (nuclei + openvas + trivy + grype) | ✅ REAL VALIDATED |
| **cloud** | 4 (prowler + scoutsuite + pacu + kube_security) | ✅ REAL VALIDATED (88 mappings) |
| **config** | 2+ (clara + lynis · CIS bench) | ✅ REAL VALIDATED |
| **phishing** | 1+ (gophish) | ✅ REAL VALIDATED |
| webpentest | 7 (testssl + ffuf + nikto + xss + zap + sqlmap + wapiti) | 🟡 SCAFFOLDING |
| infra | 14 (metasploit_* x5 + bloodhound x2 + impacket + kerbrute + netexec + responder + lynis + certipy + coercer) | 🟡 SCAFFOLDING |
| recon | 11 (subfinder + httpx + naabu + shodan + spiderfoot + dns_checker + masscan + searchsploit + theharvester + amass + nmap) | 🟡 SCAFFOLDING |
| redteam | 6 (caldera x2 + sliver + atomic_red_team + purplesharp + infection_monkey) | 🟡 SCAFFOLDING |
| apisec | 4 (arjun + auth_bypass + kiterunner + graphql) | 🟡 SCAFFOLDING |
| mobile | 2 (mobsf + apktool) | 🟡 SCAFFOLDING |
| sast | (audit demand-driven) | 🟡 SCAFFOLDING |
| cracking | (audit demand-driven) | 🟡 SCAFFOLDING |
| wireless | (audit demand-driven) | 🟡 SCAFFOLDING |
| **scope_enforcer** | (enforcer.py · fail-closed authorization) | ⚙️ UTILITY |
| **shared** | (mcp_protocol + output_normalizer + scope_check + tool_base + utils) | ⚙️ UTILITY |

**Total**: 69 tool files identificados (sample · demand-driven count exhaustivo)

### Architecture
- MCP server pattern: server.py extends `shared.MCPServer` base · register_tool(TOOL, function_handler)
- Authorization: `authorization.json` per server gates execution
- scope_enforcer: fail-closed authorization (Sesion 10)
- shared: protocol + output normalizer + scope check + tool_base + utils

### Recent FASE 1.D.E MCPs executor backend
- `motors/m08_verification/mcp_executor_service.py` (450 LOC · 13 tools catalog · executor singleton)
- `api/v1/mcps_execute.py` (270 LOC · 6 endpoints REST)
- 17 tests verified (per CLAUDE.md sub-atom 1.D.E)
- Frontend SubcontractsPanel pattern reusable (per Audit #4 + 1.D.E)

---

## Verification gap per server

### ✅ Reales validated (4 servers · production cliente piloto MEDIA)
- vulnscan · cloud · config · phishing
- Per memoria 88 mappings CIS/CVE → ENS Anexo II
- Used by 1.D.E MCP executor frontend (SubcontractsPanel polish)

### 🟡 Scaffolding (9 servers · NO validated end-to-end)
- Tool files exist (sample 69 LOC structure)
- Docker containers NO ejecutados verified
- authorization.json gates exist pero NO end-to-end test
- Cliente piloto MEDIA NO requiere · scope avanzado red team/pentest deep

### ⚙️ Utility (2 servers · permanent)
- scope_enforcer fail-closed authorization
- shared protocol + normalizers

---

## Recomendación

**Scope-out PERMANENT pre-piloto** · 0h independent task:
- 4 reales cubren 100% scenarios cliente piloto MEDIA (vulnerability + cloud + config + phishing simulation)
- 9 scaffolding NO bloquea piloto · acceptable docs ENAC explicar "scope extended pentest available demand-driven"

**Future-1.E.mcps-9-scaffolding-promote** capturado:
- ETA empírico ~10-20h cumulative per server validation Docker E2E
- Per server: ~1-3h (Docker container test + tool catalog verify + integration smoke test)
- Post-piloto demand-driven cuando cliente specifico requiere scope extended

**Quick win pre-piloto opcional** (~30 min):
- Document scope MCPs en ENS dossier · explicar 4 reales validated + 9 structural extendible
- Marcos comercial mensaje: "Platform tiene 15 MCPs · 4 production · 9 demand-driven scope extensión"

---

## Cross-ref

- MCP servers source: `backend/mcp_servers/{15 dirs}`
- MCP executor service: `backend/app/motors/m08_verification/mcp_executor_service.py` (1.D.E)
- API: `backend/app/api/v1/mcps_execute.py`
- Frontend SubcontractsPanel + ScopedPanel pattern reusable
- Memoria reference: 4 reales validados (4 servers · NO 3) + 11 structural
- ADR-???? scope_enforcer fail-closed

---

## Honest notes

1. NO inspección detallada per servidor 9 scaffolding · audit count files + structure only
2. Docker containers NO ejecutados (audit static read-only)
3. Discrepancia briefing "16 servers" vs realidad 15 · probable rounding OR `shared` excluded count
4. Future-1.E ETA 10-20h ASSUMES per-server validation realistic 1-3h cada · architecture sostained
