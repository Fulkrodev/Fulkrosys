# `audit_log` Histórico — Wiring usuario

**Fecha redacción**: 2026-04-29
**Sub-bloque**: Cierre operacional audit pre-FASE 5 (Sesión 11)
**Política aplicada**: Opción B+ (preservar inmutabilidad + documentar)

## Contexto

Pre-Sesión 11 sub-fase 4.A.2.d (commit `104443f`), el sistema de triggers `audit_log` (`fn_audit_track` aplicado vía `tg_audit_<tabla>` en 12 tablas críticas) existía y registraba mutaciones correctamente. Sin embargo, **ningún endpoint del backend setea la session variable `app.current_user`** que el trigger lee mediante `current_setting('app.current_user', true)`. Resultado: los entries generados durante S1-S10 + parte de S11 tienen el campo `usuario = NULL/empty`.

Este documento captura el estado para auditor externo ENS RD 311/2022 (Anexo III §4.4 — registro de actividad debe identificar al usuario o servicio responsable).

## Ventana temporal afectada

- **Inicio**: 2026-04-22 15:18:45 UTC (primer entry registrado, tabla `projects`)
- **Fin**: 2026-04-28 ~17:55 UTC (commit `fb68d16` 4.A.3.b, antes del primer wiring funcional admin_settings)

Tras commit cierre operacional sub-bloque audit pre-FASE 5 (este commit, 2026-04-29):

- **`admin_settings`**: usuario poblado vía `service.update_section` (`set_config` explícito desde 4.A.2.d, commit `104443f`). 2 entries valid en BD al cierre.
- **`/api/v1/auth/*` endpoints** (login, logout, refresh, sessions): usuario poblado vía wiring `set_config('app.current_user', user.email, true)` en `auth/dependencies.py::get_current_user` (este commit, sub-bloque audit pre-FASE 5).
- **12 motors target (`clients`, `projects`, `contracts`, `invoices`, `evidence`, `documents`, `document_versions`, `categorizations`, `dda_entries`, `obligations`, `magerit_analysis`, `audit_findings`)**: usuario sigue NULL en mutaciones nuevas. Gap arquitectónico H14+H15 cazado durante TODO-A.3 — los motors no usan `Depends(get_current_user)`. Resolución comprometida: `TODO-MOTORS-AUTH-LANDING-001` [BLOQUEANTE deploy producción] en sub-fase dedicada Sesión 11 o 12.

## Operador conocido durante ventana

**Marcos Mata García** (ENS Owner único FULKRO durante sesiones S1-S11). Sin otros operadores con acceso al repositorio dev en BD. Identificado por:

- Único `User` con `role='owner'` en `auth_users` durante el período
- Único acceso git a la rama `sesion-11-rompecabezas`
- Único acceso WSL Ubuntu del repo dev (`/home/usuario/fulkro/`)

## Distribución empírica

Medida 2026-04-29 14:00 UTC (script `backend/scripts/_temp_audit_log_null.py`).

| Tabla | Entries NULL | Primera | Última |
|---|---:|---|---|
| `projects` | 24 | 2026-04-22 15:18:45 | 2026-04-28 11:40:18 |
| `invoices` | 15 | 2026-04-22 15:23:03 | 2026-04-22 15:23:11 |
| `clients` | 12 | 2026-04-22 15:18:45 | 2026-04-28 11:02:32 |
| `documents` | 10 | 2026-04-22 15:22:57 | 2026-04-22 15:23:08 |
| `contracts` | 6 | 2026-04-22 15:23:09 | 2026-04-22 15:23:10 |
| `evidence` | 3 | 2026-04-22 15:23:09 | 2026-04-22 15:23:09 |
| `magerit_analysis` | 1 | 2026-04-22 15:22:57 | 2026-04-22 15:22:57 |

**Total general**:
- NULL/empty: **71** entries
- Valid (admin_settings post-4.A.2.d smoke): **2** entries
- Grand total: **73** entries

**Tablas con 0 entries pre-wiring** (sin operaciones registradas durante ventana): `document_versions`, `categorizations`, `dda_entries`, `obligations`, `audit_findings`. Dichas tablas tienen `tg_audit_<tabla>` instalado pero ninguna mutación las disparó durante S1-S10 (probablemente pendientes de uso en motors aún no completados).

## Política aplicada — Opción B+

**Preservar inmutabilidad audit_log**:

- NO se modifican entries históricos NULL.
- Triggers `tg_audit_log_no_update` + `tg_audit_log_no_delete` + `tg_audit_log_hash_chain` quedan intactos (inmutabilidad ENS preservada).
- NULL existing entries documentados como "pre-wiring setup" en este archivo.

**Justificación**: la tabla `audit_log` tiene una hash chain criptográfica (BEFORE INSERT trigger) que calcula `hash_current` desde `payload + hash_prev`. Hacer UPDATE post-hoc sobre el campo `usuario` desfasaría todos los hashes posteriores y rompería la trazabilidad chain. La inmutabilidad es el activo más valioso del `audit_log` para auditor ENS — preservarla a costa de NULL semánticamente acotado es trade-off aceptable.

**Trade-off aceptado**: NULL ambiguo (¿usuario desconocido o no rastreado?) compensado por documentación explícita en este archivo + ventana temporal acotada + operador único conocido.

## Acción correctiva comprometida pre-deploy producción

`TODO-MOTORS-AUTH-LANDING-001` [BLOQUEANTE deploy producción]:

1. Cerrar gap arquitectónico motors sin auth (sub-fase 4.D dedicada Sesión 11 o 12 según decisión Marcos)
2. Aplicar Opción A/B/C de auth strategy (refactor 12 motors, middleware ASGI, o híbrido) — ver TODO para detalles
3. Habilitar set_config wiring uniforme via opción elegida
4. Tras resolución: aplicar `ALTER TABLE audit_log ALTER COLUMN usuario SET NOT NULL` (constraint formal)
5. Backfill data integrity NO se aplica — preservamos histórico NULL como pre-wiring

## Trazabilidad

- **Detección gap H14+H15**: TODO-A.3 sub-bloque (Sesión 11 post-FASE 4 cierre, 2026-04-29). Audit empírico vía `grep -r get_current_user backend/app/motors/` reveló 0 matches.
- **Lección operacional**: `LECCIÓN-OPS-003` (validar premisas arquitectónicas TODOs con grep empírico pre-implementación) — formalizada en `progress/backlog_formal.md`.
- **Reformulación TODO**: `TODO-AUDIT-USER-BACKFILL-001` → PARTIAL RESOLVED 2026-04-29 (cobertura `/auth/*` + `admin_settings/*`, gap motors deferido a TODO sucesor).
- **TODO sucesor arquitectural**: `TODO-MOTORS-AUTH-LANDING-001` (BLOQUEANTE deploy producción, esfuerzo 10-17h estimado).
- **Doc creado**: este archivo (commit cierre operacional 2026-04-29).
- **Script empírico**: `backend/scripts/_temp_audit_log_null.py` (temporal, eliminable post-commit).

## Para auditor ENS

La inmutabilidad del `audit_log` se preserva — los 71 entries NULL son inmutables, hash chain criptográfica intacta, triggers de bloqueo UPDATE/DELETE activos. La trazabilidad usuario para los entries históricos NULL queda **implícitamente identificada** mediante:

1. Ventana temporal acotada (2026-04-22 a 2026-04-28, 7 días naturales)
2. Operador único documentado (Marcos Mata García, ENS Owner)
3. Origen acotado (entries generados en repositorio dev local WSL Ubuntu, no producción)

Tras `TODO-MOTORS-AUTH-LANDING-001` RESOLVED:
- Todos los nuevos entries `audit_log` tendrán `usuario` explícito poblado
- Constraint `NOT NULL` aplicado vía migración
- Hash chain intacta, sin rotura de inmutabilidad

**Compromiso pre-deploy producción**: ningún despliegue a Hetzner se realiza hasta que `TODO-MOTORS-AUTH-LANDING-001` esté RESOLVED + suite de tests integración por motor verde + migración `NOT NULL` aplicada en BD producción inicializada con 0 entries (clean slate post-wiring).

## Referencias

- Commit detección gap H14+H15: TODO-A.3 sub-bloque (sin commit pendiente, audit-only)
- Commit Strategy A wiring `/auth/*`: cierre operacional 2026-04-29 (este commit)
- TODO sucesor arquitectural: `progress/backlog_formal.md::TODO-MOTORS-AUTH-LANDING-001`
- Lección operacional: `progress/backlog_formal.md::LECCIÓN-OPS-003`
- Schema audit_log + triggers: migración `backend/db/migrations/versions/<hash>_audit_log_*.py` (sub-bloque 4.A.2.d, commit `104443f`)
