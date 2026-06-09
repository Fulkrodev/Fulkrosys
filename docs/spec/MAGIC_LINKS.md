# Magic Links · Referencia Operativa FULKRO

**Versión**: 1.0 · FASE 4.5 cerrada · 2026-05-01
**Spec base**: ADR-011 + ADR-028
**Motor**: M12 Magic Link

## Resumen

35 purposes operativos para enlaces de un solo uso (magic links) firmados con OTP opcional, scope JSON, geo restriction opcional, y audit trail integrado en `client_interactions`.

Single source of truth de los valores TTL / max_uses / requires_otp / requires_geo: `backend/app/motors/m12_magic_link/purposes.py::PURPOSE_CONFIG`. Esta tabla es un volcado de ese dict (regenerar si el código cambia).

## Tabla maestra · 35 purposes

| #  | Purpose                              | TTL    | Max  | OTP | Geo | UI Route            | Estado |
|----|--------------------------------------|--------|------|-----|-----|---------------------|--------|
| 1  | `onboarding_inicial`                 | 168h   | 1    | no  | no  | scaffold            | legacy |
| 2  | `firma_documento`                    | 72h    | 1    | sí  | no  | sign/[token]        | legacy |
| 3  | `aporte_evidencia`                   | 168h   | 3    | no  | no  | upload/[token]      | legacy |
| 4  | `aprobacion_acta`                    | 72h    | 1    | sí  | no  | sign/[token]        | legacy |
| 5  | `respuesta_requerimiento_auditor`    | 48h    | 1    | sí  | no  | survey/[token]      | legacy |
| 6  | `autorizacion_pentest`               | 24h    | 1    | sí  | sí  | scaffold            | DEPREC |
| 7  | `autorizacion_accion_remota`         | 24h    | 1    | sí  | sí  | scaffold            | legacy |
| 8  | `aprobacion_obligacion`              | 72h    | 1    | no  | no  | scaffold            | legacy |
| 9  | `descarga_dossier_final`             | 168h   | 3    | sí  | no  | scaffold            | legacy |
| 10 | `autorizar_verificacion_tecnica`     | 48h    | 1    | sí  | no  | verify-auth/[token] | M8     |
| 11 | `autorizar_pentest_externo`          | 72h    | 1    | sí  | no  | scaffold            | M8     |
| 12 | `portal_remediacion`                 | 2160h  | 9999 | no  | no  | remediation/[token] | M8     |
| 13 | `portal_pentester_externo`           | 1440h  | 9999 | sí  | no  | pentester-portal/.. | M8     |
| 14 | `revisar_informe_verificacion`       | 360h   | 5    | sí  | no  | survey/[token]      | M8     |
| 15 | `oferta_retainer`                    | 720h   | 1    | no  | no  | scaffold            | M25    |
| 16 | `descarga_backup_archivo`            | 1440h  | 20   | sí  | no  | scaffold            | M25    |
| 17 | `reconsideracion_retainer`           | 1440h  | 1    | no  | no  | scaffold            | M25    |
| 18 | `primer_acceso_cliente`              | 24h    | 1    | sí  | no  | scaffold            | M21    |
| 19 | `normativa_alert_critical`           | 168h   | 5    | no  | no  | scaffold            | A15    |
| 20 | `retainer_welcome`                   | 168h   | 3    | no  | no  | scaffold            | M21    |
| 21 | `reporte_trimestral`                 | 1440h  | 10   | no  | no  | scaffold            | M23    |
| 22 | `reporte_anual`                      | 2160h  | 20   | no  | no  | scaffold            | M23    |
| 23 | `renewal_campaign_details`           | 2880h  | 5    | no  | no  | scaffold            | M27    |
| 24 | `invitacion_reunion`                 | 168h   | 1    | no  | no  | meeting/[token]     | F4.5   |
| 25 | `aprobacion_propuesta`               | 168h   | 3    | sí  | sí  | sign/[token]        | F4.5   |
| 26 | `aprobacion_factura`                 | 168h   | 3    | sí  | sí  | sign/[token]        | F4.5   |
| 27 | `solicitud_informacion`              | 336h   | 5    | no  | no  | survey/[token]      | F4.5   |
| 28 | `validacion_cambio_alcance`          | 168h   | 3    | sí  | sí  | sign/[token]        | F4.5   |
| 29 | `aceptacion_riesgo_residual`         | 168h   | 3    | sí  | sí  | sign/[token]        | F4.5   |
| 30 | `comunicacion_incidente_seguridad`   | 24h    | 5    | sí  | sí  | incident/[token]    | F4.5   |
| 31 | `consentimiento_tratamiento_datos`   | 336h   | 3    | sí  | sí  | sign/[token]        | F4.5   |
| 32 | `confirmacion_conformidad`           | 168h   | 3    | sí  | sí  | sign/[token]        | F4.5   |
| 33 | `descarga_certificado_conformidad`   | 720h   | 10   | no  | no  | download/[token]    | F4.5   |
| 34 | `votacion_comite_seguridad`          | 168h   | 1    | sí  | no  | vote/[token]        | F4.5   |
| 35 | `encuesta_satisfaccion_nps`          | 720h   | 1    | no  | no  | nps/[token]         | F4.5   |

**Estado**:
- `legacy` = pre-FASE 7 (originales 9 + 3 sin scaffold dedicado)
- `DEPREC` = deprecated, eliminar en S12 cleanup (ver `TODO-FASE-4-5-DEDUP-001`)
- `M8`, `M21`, `M23`, `M25`, `M27`, `A15` = motor/agente que añadió el purpose (Sesión 7-8)
- `F4.5` = añadidos en FASE 4.5 sub-bloque A (commit `5d3ca2d`)

## Arquitectura

### Backend (Motor 12)

- Carpeta: `backend/app/motors/m12_magic_link/`
- Tabla principal: `magic_links` (21 columnas + Mixin)
- Tabla audit: `client_interactions` (FK `magic_link_id`)
- Email rendering: dict Python `_PURPOSE_EMAILS` en `emails/renderer.py` · ver ADR-028 (decisión Python inline · supersede parcial ADR-011 FR15.4)

#### Endpoints REST (6)

| Método | Path                                    | Auth   | Uso                                          |
|--------|-----------------------------------------|--------|----------------------------------------------|
| POST   | `/api/v1/magic-links/generate`          | admin  | Crear nuevo magic link                       |
| POST   | `/api/v1/magic-links/consume`           | público | Consumir link con `token` + `otp`            |
| POST   | `/api/v1/magic-links/{id}/revoke`       | admin  | Revocar link activo (idempotente)            |
| GET    | `/api/v1/magic-links/{id}/status`       | admin  | Estado interno para dashboard                |
| GET    | `/api/v1/magic-links/by-token/{token}`  | público | Subset estricto público para UI sign-flow    |
| GET    | `/api/v1/magic-links`                   | admin  | List filtered (project / purpose / active)   |

#### Columnas BD relevantes

```
project_id                FK projects (RLS por owner)
tipo_operacion            VARCHAR(50) · purpose backend
scope                     JSONB · contexto específico del link
token_hash                hash SHA-256 del token (nunca plaintext)
otp_hash                  hash del OTP (nullable · si requires_otp)
expira_at                 TIMESTAMP TZ
max_usos / usos           INT
revocado / revoked_at     bool + timestamp soft revoke
otp_failures              rate limit (>=3 → bloqueo)
recipient_email           email destinatario principal
allowed_countries         JSONB · ISO codes (geo restriction)
sent_to_contact_id        FK client_contacts.id (M30 integration)
cc_emails                 TEXT[] · CC del envío email
custom_subject            VARCHAR(255) · override subject default
custom_body_intro         TEXT · prepend body (no replace)
```

### Frontend

- **Types** (`frontend/lib/magic-link-types.ts`):
  - `MagicLinkBackendPurpose` (string union de los 35 valores)
  - `MAGIC_LINK_BACKEND_LABELS` (action_label exact match con backend)
  - `MAGIC_LINK_BACKEND_CATEGORIES` (6 categorías UI dropdown)
  - `MAGIC_LINK_OTP_REQUIRED` (Set para derive client-side)
  - `isMagicLinkActive` helper
- **Routing** (`frontend/lib/magic-link-routing.ts`):
  - `backendPurposeToUIRoute(purpose)` · función pura · 12 UIRoute literal type
- **API** (`frontend/lib/api/magic-links.ts`):
  - 5 wrappers: `list`, `generate`, `getByToken`, `consume`, `revoke`
- **Hooks React Query** (`frontend/hooks/magic-link/index.ts`):
  - `useMagicLinkList`, `useMagicLinkStatus`, `useGenerateMagicLink`, `useMagicLinkConsume`, `useRevokeMagicLink`
- **Admin UI**:
  - `/admin/magic-links/page.tsx` (Tabs Generar / Histórico)
  - `MagicLinkGenerator` (RHF + Zod + 35 purposes categorized + accordion overrides)
  - `MagicLinkHistoryTable` (TanStack Table v8 + filtros + revoke)
- **Public sign-flows** (multiplex `sign/[token]`):
  - `SignFlowDisclaimer` + `BaseSignFlow` + `LegacyDocumentSignFlow`
  - 6 flows nuevos: `ApprovePropuestaFlow`, `ApproveFacturaFlow`, `ValidateScopeChangeFlow`, `AcceptResidualRiskFlow`, `SignDPAFlow`, `ConfirmConformidadFlow`
- **Public scaffolds** (FASE 9):
  - `TokenScaffold` shared
  - 5 page.tsx: `/meeting/[token]`, `/incident/[token]`, `/download/[token]`, `/vote/[token]`, `/nps/[token]`
- **Public legacy** (mocks pendientes cleanup FASE 9 · `TODO-FASE-9-MAGIC-LINK-MOCKS-CLEANUP-001`):
  - `/upload/[token]`, `/survey/[token]`
  - `(portal)/remediation/[token]`, `(portal)/verify-auth/[token]`, `(portal)/pentester-portal/[token]`

## Categorización UI

Los 35 purposes se agrupan en 6 categorías para el dropdown del `MagicLinkGenerator`:

1. **Onboarding y acceso** (3): `onboarding_inicial`, `primer_acceso_cliente`, `retainer_welcome`
2. **Firma documental** (8): `firma_documento`, `aprobacion_acta`, `aprobacion_propuesta`, `aprobacion_factura`, `validacion_cambio_alcance`, `aceptacion_riesgo_residual`, `consentimiento_tratamiento_datos`, `confirmacion_conformidad`
3. **Evidencias y verificación** (7): `aporte_evidencia`, `autorizar_verificacion_tecnica`, `autorizar_pentest_externo`, `portal_remediacion`, `portal_pentester_externo`, `revisar_informe_verificacion`, `respuesta_requerimiento_auditor`
4. **Comunicación y reporting** (7): `solicitud_informacion`, `invitacion_reunion`, `reporte_trimestral`, `reporte_anual`, `comunicacion_incidente_seguridad`, `normativa_alert_critical`, `votacion_comite_seguridad`
5. **Cierre y descargas** (7): `descarga_dossier_final`, `descarga_backup_archivo`, `descarga_certificado_conformidad`, `encuesta_satisfaccion_nps`, `oferta_retainer`, `reconsideracion_retainer`, `renewal_campaign_details`
6. **Deprecated** (3): `autorizacion_pentest`, `autorizacion_accion_remota`, `aprobacion_obligacion` (filtradas del select del generator · gestionadas solo por código existing)

## Ciclo operativo

1. **Generate**: admin desde `/admin/magic-links` o motor programático invoca `MagicLinkService.generate_magic_link(req)`. Se persiste row + email opcional enviado vía `email_sender.send` con renderer `_PURPOSE_EMAILS[purpose]`. Se devuelve `token` plaintext **una sola vez** + `otp` (si `requires_otp`).

2. **Consume**: cliente abre link público `https://app.fulkro.es/{ui_route}/{token}`. Frontend fetcha `GET /magic-links/by-token/{token}` (subset público) → render flow específico → `POST /magic-links/consume` con `otp` si `requires_otp`.

3. **Audit**: cada `consume` crea fila en `client_interactions` con `accion` + `ip` + `user_agent` + `geolocalizacion` + `payload`. Si el link tenía `sent_to_contact_id`, también se loggea `interaction_type='magic_link'` en el timeline del contacto M30.

4. **Revoke**: admin puede revocar manualmente desde `/admin/magic-links` (botón en tabla histórico) o vía `POST /magic-links/{id}/revoke`. Marca `revocado=true` + `revoked_at`. Futuras `consume` devuelven 403 con detail uniforme.

## Override email (3 niveles)

1. **Por magic link** (columnas BD añadidas en sub-bloque A · migration `f658961972a2`):
   - `cc_emails: TEXT[]` · destinatarios CC
   - `custom_subject: VARCHAR(255)` · sustituye subject default
   - `custom_body_intro: TEXT` · prepend al body antes del párrafo contextual

2. **Por purpose globalmente** (settings admin):
   - `magic_link_per_purpose_overrides: JSONB` (objeto libre · ver `NotificationsTab` en `/admin/settings`)
   - Permite ajustar custom_sender / custom_subject / custom_body_intro por purpose

3. **Por sistema globalmente** (settings admin):
   - `magic_link_default_sender: VARCHAR` · email From: por defecto (default `auth_users.email` del owner)

UI admin: accordion "Personalización avanzada" en `MagicLinkGenerator` para overrides por link individual.

## Privacidad endpoint público `/by-token/{token}`

Subset estricto devuelto al cliente para evitar enumeration (mantiene token + datos sensibles fuera de la response):

```
tipo_operacion              · purpose backend
scope                       · contexto del link (ya conocido por el cliente)
expira_at, max_usos, usos
revocado
recipient_email_hint        · "jor***@dataforma.es" · NO email completo
```

NO se exponen: `id` interno, `project_id`, `recipient_email` completo, `cc_emails`, `custom_subject`, `custom_body_intro`, `sent_to_contact_id`, `allowed_countries`, `token_hash`, `otp_hash`. Helper `_mask_email` en `service.py`.

## Deuda y backlog FASE 9

3 entries trazadas en `progress/backlog_formal.md`:

- **TODO-FASE-9-MAGIC-LINK-FRONTEND-ROUTES-001** [ALTA] · implementar 5 scaffold flows reales (meeting / incident / download / vote / nps).
- **TODO-FASE-9-MAGIC-LINK-MOCKS-CLEANUP-001** [ALTA] · eliminar `useMagicLink` legacy (sprint4-mock) · migrar consumidores a `useMagicLinkStatus` + `useMagicLinkConsume` reales.
- **TODO-FASE-9-MAGIC-LINK-CONTACTPICKER-001** [MEDIA] · integrar `ContactQuickPicker` (M30) en `MagicLinkGenerator`.

S12 cleanup:
- **TODO-FASE-4-5-DEDUP-001** · eliminar `AUTORIZACION_PENTEST` superseded por `AUTORIZAR_PENTEST_EXTERNO` (verificar 0 magic links activos en BD antes de DROP).

## Referencias

- ADR-011 (Magic Links auditoría + ampliación · 2026-04-25)
- ADR-028 (Python inline emails · supersede parcial ADR-011 FR15.4 · 2026-05-01)
- `progress/session_11/magic_links_audit/REPORT.md` · audit estado FASE 4.5
- `backend/app/motors/m12_magic_link/purposes.py` · canonical TTL/max/OTP/geo + action_label
- `backend/app/motors/m12_magic_link/emails/renderer.py` · `_PURPOSE_EMAILS` dict (35 entries)
- `frontend/lib/magic-link-types.ts` · typing frontend (35 purposes)
- `frontend/lib/magic-link-routing.ts` · `backendPurposeToUIRoute` función pura
