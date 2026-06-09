# Architecture Decision Records — FULKRO

## Template

### ADR-NNN: Title

**Status:** Proposed | Accepted | Deprecated | Superseded
**Date:** YYYY-MM-DD
**Context:** What is the issue that is motivating this decision?
**Decision:** What is the change that we are proposing and/or doing?
**Consequences:** What becomes easier or more difficult to do because of this change?

---

## ADR-001: WSL2 development environment

**Status:** Accepted
**Date:** 2026-04-11
**Context:** Marcos develops on Windows 11. The platform targets Hetzner CCX33 (Debian 12). Motor 26 (pgBackRest, backup/DR) requires native Linux tooling.
**Decision:** Develop in WSL2 (Ubuntu) at ~/fulkro. All server-side tooling runs natively on Linux from day 1.
**Consequences:** No path translation issues. Docker, pgBackRest, Terraform, Ansible all work natively. Windows only used for IDE access via VS Code Remote WSL.

---

## ADR-002: Single PostgreSQL instance with extensions over separate services

**Status:** Accepted
**Date:** 2026-04-11
**Context:** The platform needs relational data, vector search (RAG), graph queries (knowledge graph), and audit logging. Could use separate databases (Neo4j, Qdrant, etc.) or a single PostgreSQL with extensions.
**Decision:** Single PostgreSQL 16 with pgvector (embeddings), Apache AGE (graph), pgAudit (audit), pgBackRest (backup). Per v2.1 Parte 4.1.
**Consequences:** Simpler ops (one DB to backup/restore/monitor), ACID across all data types, lower cost. Trade-off: AGE Cypher is less mature than Neo4j, pgvector less optimized than dedicated vector DBs. Acceptable for our scale (< 1M vectors).

---

## ADR-003: Dev auth with session fallback until Yubikey available

**Status:** Accepted
**Date:** 2026-04-11
**Context:** WebAuthn with Yubikey is the production auth method per v2.1. Marcos has not yet purchased the Yubikeys.
**Decision:** Implement WebAuthn stub + simple session-based dev auth (configurable via APP_ENV). TODO markers in code for Yubikey integration. Dev auth disabled when APP_ENV=production.
**Consequences:** Development can proceed immediately. Clear migration path when Yubikeys arrive.
