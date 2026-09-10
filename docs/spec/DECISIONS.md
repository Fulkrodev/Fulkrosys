# FULKRO — Architecture Decision Records (DECISIONS.md)

Este documento consolida las decisiones arquitectónicas formales (ADRs) tomadas en el desarrollo de FULKRO. Cada ADR es texto literal extraído del plan oficial Sesión 11 v4.2 (`progress/session_11/PLAN_MASTER.md`, Sección 3).

ADRs descriptivos previos (S1-S10) viven en `docs/decisions/*.md` con formato narrativo. Los ADRs numerados ADR-004..ADR-014 (Sesión 11) viven aquí.

## Índice de ADRs Sesión 11

| ID | Título | Fecha | Decisor |
|----|--------|-------|---------|
| ADR-004 | Reuniones externas, panel A18 admin-only | 2026-04-22 | Marcos Mata García |
| ADR-005 | M29 Client Messaging motor nuevo | 2026-04-22 | Marcos Mata García |
| ADR-006 | Panel Settings + Email forward + Magic Link config | 2026-04-22 (ampl. 2026-04-25) | Marcos Mata García |
| ADR-007 | Orquestación guiada D17 Opción A | 2026-04-22 | Marcos Mata García |
| ADR-008 | Brand identity completo | 2026-04-22 | Marcos Mata García |
| ADR-009 | FULKRO NO implementa firma cualificada eIDAS/TSA | 2026-04-25 | Marcos Mata García |
| ADR-010 | Cláusula firma C-001 + página "Cómo funciona la firma" | 2026-04-25 | Marcos Mata García |
| ADR-011 | Magic Links auditoría + ampliación + email destinatario configurable | 2026-04-25 | Marcos Mata García |
| ADR-012 | Motor M30 Client Contacts (lista contactos por empresa) | 2026-04-25 | Marcos Mata García |
| ADR-013 | Separación arquitectónica de portales · admin / radar / client | 2026-04-25 | Marcos Mata García |
| ADR-014 | Portal ENS Radar admin-only · pipeline v2 + UI completa + tracking runs | 2026-04-25 | Marcos Mata García |
| ADR-015 | role en BD (identidad) vs capabilities en Settings (toggles) | 2026-04-27 | Marcos Mata García |
| ADR-016 | Drift modelo SQLAlchemy ↔ BD pendiente · Mini-Sesión 11.5 — **Empirically Confirmed 2026-04-28** | 2026-04-27 | Marcos Mata García |
| ADR-017 | Coexistencia dual auth flow (admin cookie · cliente Bearer) — **RESOLVED Mini-Fase 3.5** | 2026-04-27 | Marcos Mata García |
| ADR-018 | Aceleración auth unificado a Mini-Fase 3.5 S11 (era FASE 6/10) — **IMPLEMENTED Mini-Fase 3.5** | 2026-04-27 | Marcos Mata García |
| ADR-019 | CSRF triple binding cliente (cookie + JWT claim + header) | 2026-04-28 | Marcos Mata García |
| ADR-020 | Tablas sessions separadas con cookie común + dual dispatcher | 2026-04-28 | Marcos Mata García |

---

# ADR-004 — Reuniones externas, panel A18 admin-only

**Fecha**: 2026-04-22 (decisión 1 sesión consultoría L99)
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: M20 Communications, A18 Reunion Agent

## Contexto

Originalmente FULKRO planeaba implementar:
- LiveKit videoreuniones internas FULKRO
- Chat encriptado E2E para reuniones K.0/K.2/K.4
- Sistema notas privadas Marcos durante reunión

Esto resultaba sobreingenierizado para:
1. Solo 4 reuniones formales por proyecto (K.0, K.2, K.4, K.6)
2. Cliente PYME ya usa Meet/Zoom/Teams habitualmente
3. Coste implementación + mantenimiento desproporcionado para volumen

## Decisión

1. **Reuniones externas**: K.0/K.2/K.4 se hacen en plataforma externa (Meet/Zoom/Teams) elegida por cliente. FULKRO solo guarda enlace + agenda + asistentes.
2. **K.6 firma**: NO es reunión, es magic link `FIRMA_DOCUMENTO` enviado al sponsor + RSEG. Si cliente quiere call, hace call externa y luego firma magic link.
3. **Panel A18 admin-only**: `/admin/meetings/*` (rename desde `/admin/communications/`). Marcos único usuario. NO portal cliente. Notas Marcos permanentes en `meeting_notes` GIN search.
4. **CANCELACIONES**: TODO-M20-LIVEKIT cancelado. TODO-M20-CHAT-ENCRYPTION cancelado. Tabla `meeting_chat_messages` no se crea. Stub LiveKit eliminado.

## Consecuencias

- Ahorro 25-30h dev (no LiveKit, no chat E2E)
- Marcos privacy: notas confidenciales nunca expuestas
- Onboarding cliente más simple: usa su Meet/Zoom/Teams habitual
- Panel A18 solo para Marcos = puede iterar UX sin worry sobre UX cliente

---

# ADR-005 — M29 Client Messaging motor nuevo

**Fecha**: 2026-04-22
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: M21 Portal Cliente, A14 Copilot

## Contexto

Hoy NO existe canal asíncrono cliente ↔ Marcos dentro de FULKRO. Cliente que tiene duda envía email externo, Marcos responde por email externo. Sin tracking, sin contexto, sin búsqueda. Mal flujo para cliente PYME que paga retainer.

## Decisión

1. **Motor M29 Client Messaging nuevo** con 2 tablas:
   ```sql
   CREATE TABLE client_messages (
     id UUID PRIMARY KEY,
     client_id UUID FK clients(id),
     thread_id UUID FK client_message_threads(id),
     direction VARCHAR CHECK (direction IN ('admin_to_client', 'client_to_admin')),
     sender_user_id UUID FK auth_users(id) NULL,
     sender_client_user_id UUID FK client_users(id) NULL,
     body_md TEXT,
     subject VARCHAR(255),
     read_by_recipient_at TIMESTAMPTZ,
     created_at TIMESTAMPTZ
   );
   CREATE TABLE client_message_attachments (
     id UUID PRIMARY KEY,
     message_id UUID FK client_messages(id),
     filename VARCHAR(500),
     content_type VARCHAR(100),
     size_bytes BIGINT,
     minio_key VARCHAR(500),
     signed_url_expires_at TIMESTAMPTZ
   );
   ```

2. **Cliente UI**: `/client-portal/inbox` nueva página con threads + composer + attachments.

3. **Admin UI**: `/admin/messages` nueva página (NOT `/admin/clients/[id]/messages` — global inbox cross-cliente con filtro).

4. **Email forward configurable** (ver ADR-006): Marcos puede recibir notificaciones nuevos mensajes en email externo personal vía SMTP/SES.

5. **MinIO bucket** `fulkro-client-messages` para attachments con signed URLs TTL 7d.

6. **Tests**: 33+ tests backend service + 4 tests Playwright E2E.

7. **Audit log**: cada mensaje genera entry `audit_log` con hash chain.

8. **RLS**: cliente solo ve sus propios mensajes; Marcos ve todos.

9. **Búsqueda full-text**: GIN index sobre `body_md` para búsqueda Marcos.

10. **Notificaciones**: cliente recibe email cuando Marcos responde + Marcos recibe email forwarded cuando cliente envía nuevo mensaje (configurable).

11. **Integración M30 (v4)**: Marcos puede enviar mensaje a contacto sin login portal (ej. CTO que solo recibe info, no opera) → email + tracking sin necesidad de crear `client_user`.

12. **Email override (v4)**: campo `recipient_email_override` permite Marcos enviar mensaje específico a email distinto del contacto principal por defecto.

## Consecuencias

- Cliente tiene canal seguro consultas (no ya email)
- Marcos no pierde mensajes en su inbox personal
- Tracking + audit + contexto preservado
- Base para futuros features (templates respuesta, snoozes, etc.)

---

# ADR-006 — Panel Settings + Email forward + Magic Link config

**Fecha**: 2026-04-22 (ampliado v4 2026-04-25)
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: ADR-005

## Contexto

Hoy NO existe `/admin/settings`. Configuraciones (email forward, branding, smtp, etc.) se cambiaban editando `.env` + reiniciando. Mal flujo para Marcos.

## Decisión

Crear `/admin/settings` panel con tabla `admin_settings` singleton (id=1) con 5 categorías JSONB:

```sql
CREATE TABLE admin_settings (
  id UUID PRIMARY KEY DEFAULT '00000000-0000-0000-0000-000000000001',
  branding JSONB NOT NULL DEFAULT '{}',
  notifications JSONB NOT NULL DEFAULT '{}',
  smtp JSONB NOT NULL DEFAULT '{}',
  general JSONB NOT NULL DEFAULT '{}',
  analytics_prefs JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_by_user_id UUID REFERENCES auth_users(id)
);
INSERT INTO admin_settings (id) VALUES ('00000000-0000-0000-0000-000000000001') ON CONFLICT DO NOTHING;
```

**5 tabs UI** (`/admin/settings`):

1. **Branding**: logo upload, colors override, footer text

2. **Notifications**:
   - `client_messages_forward_enabled` (bool)
   - `client_messages_forward_to` (email externo)
   - `digest_enabled` (bool)
   - `digest_time_local` (HH:MM)
   - **NUEVO v4**: `magic_link_default_sender` configurable email From: para magic links (default: `auth_users.email`)
   - **NUEVO v4**: `magic_link_per_purpose_overrides` JSONB → permite por cada `purpose` configurar:
     - `enabled` (boolean)
     - `default_recipient_email` (override del email cliente)
     - `cc_emails` (lista emails CC)
     - `template_id` (override template HTML)

3. **SMTP**: configuración custom SMTP (override env vars) + test envío

4. **General**: timezone, idioma, fecha formato

5. **About**:
   - Versión FULKRO
   - Commit hash
   - Tests passing
   - **NUEVO v4**: `analytics_prefs.show_corpus_metric` (bool, default true) → muestra "Corpus RAG: 39/92 fuentes · 6.171 chunks · 42.4% completado"
   - **NUEVO v4**: ratio test/LOC promedio

---

# ADR-007 — Orquestación guiada D17 Opción A

**Fecha**: 2026-04-22 (decisión 2 sesión consultoría L99)
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: M00 Project Lifecycle

## Contexto

Marcos pierde contexto de fase ENS al cambiar entre clientes. ¿Está cliente A en Plan o en Implant? ¿Qué motor toca ahora? Sin orquestación visible, depende de memoria de Marcos.

## Decisión

Implementar **Opción A** del Diseño 17 (D17A) — orquestación guiada con módulo `workflow_gates.py`:

1. **Backend**: módulo `backend/app/motors/m00_project_lifecycle/workflow_gates.py` (252 LOC) define 7 fases canónicas:
   - F1 Categorización (M01)
   - F2 Análisis riesgo (M02)
   - F3 DdA (M03)
   - F4 Gap Analysis (M04)
   - F5 Implant docs/políticas/proc (M05/M06/M18)
   - F6 Verificación (M08)
   - F7 Auditoría → Conformidad (M27)

2. **5 endpoints REST**:
   - `GET /api/v1/projects/{id}/workflow/state` → fase actual + progreso
   - `GET /api/v1/projects/{id}/workflow/next-action` → qué tocar ahora
   - `GET /api/v1/projects/{id}/workflow/gates` → todas las fases con status
   - `POST /api/v1/projects/{id}/workflow/advance` → avanzar fase manualmente
   - `GET /api/v1/projects/{id}/workflow/blockers` → qué bloquea avance

3. **4 componentes frontend**:
   - `<ProjectGuidePanel>` (sidebar derecha en `/projects/[id]/*`) — qué fase, qué siguiente
   - `<PhaseStepper>` (top de cada página proyecto) — 7 stepper visual
   - `<NextActionCard>` (dashboard) — primera card "qué hacer hoy"
   - `<GlobalRoadmap>` (`/dashboard`) — vista cross-clientes con todas las fases

4. **Definition of Done por fase**: cada fase tiene `is_complete()` validador automático que checa:
   - Documentos firmados existen
   - Magic links consumidos
   - Tests cliente passing (cuando aplica)
   - Aprobaciones registradas

---

# ADR-008 — Brand identity completo

**Fecha**: 2026-04-22
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: FASE 1 Brand Foundation

## Contexto

Hoy frontend usa Tailwind base + algunos componentes shadcn sin coherencia. Sin logo, sin paleta, sin tipografía. Apariencia genérica.

## Decisión

Implementar brand identity completo basado en `FULKRO_BRAND_IDENTITY__2_.md`:

1. **5 SVG logos**: full color, monochrome, mark only, footer reduced, favicon
2. **Tokens.css**: paleta colors (navy, spark, stone, success, warning, info, danger), fuentes (serif Playfair Display + sans Inter), spacing, shadows
3. **Tailwind extend**: `theme.colors.fulkro.*`, `theme.fontFamily.fulkro-serif`, etc.
4. **Lista negra** términos prohibidos:
   - "disruptivo"
   - "holístico"
   - "360°"
   - "transformación digital"
   - "soluciones integrales"
5. **Lista blanca** términos preferidos:
   - "determinista"
   - "trazable"
   - "auditable"
   - "punto de apoyo"
   - "operativo"
   - "verificable"
6. **Tagline oficial**: "FULKRO — El punto de apoyo del consultor ENS"
7. **Voice**: profesional, técnico, claro, sin marketing-speak

## Consecuencias

- Frontend coherente visualmente
- Marcos tiene identidad para outreach (LinkedIn, web, propuestas)
- Cliente percibe profesionalidad

---

# ADR-009 — FULKRO NO implementa firma cualificada eIDAS/TSA

**Fecha**: 2026-04-25 (ampliado v4 con posicionamiento "TSA cuando cliente lo pida")
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: M12 Magic Links, M14 Contracts, ADR-010

## Contexto

La auditoría exhaustiva mostró superficie residual de "TSA / eIDAS qualified" en código + docs (referencias a tabla `tsa_tokens` planeada, comentarios sobre Adsigo/Uanataca, mocks FNMT). Marcos decidió: **FULKRO no implementa firma cualificada propia**.

## Decisión

1. **FULKRO usa firma electrónica simple eIDAS Art. 25.1**:
   - EC P-256 (curva NIST P-256)
   - OTP enviado al email del firmante (verificación dual)
   - Hash chain inmutable append-only en `audit_log`
   - Trazabilidad completa: IP, user-agent, timestamp UTC, identidad firmante

2. **NO implementamos**:
   - TSA propia (Time Stamp Authority)
   - Firma cualificada Art. 26 eIDAS
   - Integración con AutoFirma / FNMT directamente
   - Tabla `tsa_tokens` (eliminada del schema)
   - Connectores FNMT / Adsigo / Uanataca / Izenpe

3. **Posicionamiento comercial v4**:

   - **NO se integra TSA externa preventivamente** (no FNMT, no Uanataca, no Izenpe, no Adsigo, no Redtrust). El plan no es "construir TSA por si acaso".

   - **TSA pública se integrará SI Y SOLO SI** un cliente firma contrato exigiendo explícitamente: *"esto debe estar sellado por TSA acreditada porque lo voy a presentar al CCN como evidencia ante auditor ENAC"*. Esta condición la cumplen muy pocos casos reales en PYMEs ENS Bajo/Medio (que es el target FULKRO).

   - **Si un cliente lo pide**, integración FNMT TSA es **1-2 días de trabajo** (test endpoint TSA + verificar timestamp + persistir token TSA en `audit_log.tsa_token` campo nuevo opcional). NO bloquea comercial preventivamente.

   - **Cláusula contractual clara C-001** explica el alcance (ver ADR-010).

   - **Página `/client-portal/firma`** explica al cliente en lenguaje plano qué es y qué no es la firma electrónica que ofrece FULKRO (ver ADR-010).

   - **Lo que sí se hace pre-cliente**: cláusula contractual + página explicativa + revisión por abogado TIC cuando Marcos lo contrate (post-S12).

4. **Auditoría FASE 0.B** elimina TODA referencia eIDAS/TSA del código + docs + tests. Output: `progress/session_11/eidas_audit/REPORT.md`.

5. **Tests confirman**: post-S11, `grep -ri "eidas\|tsa\|fnmt\|qualified\|cualificada" backend/ frontend/ docs/` debe devolver solo referencias en disclaimers + ADRs (no en código activo).

## Consecuencias

- Ahorro 25-45h dev + 500-1500€/año coste TSA externa
- Posicionamiento claro: FULKRO = consultoría con plataforma, no firmador qualified
- Cliente entiende alcance sin sorpresas (cláusula + página)
- Marcos protegido contractualmente
- Si primer cliente AAPP lo pide: 1-2 días de trabajo lo cubren

## Nota operativa post-decisión 25 abril 2026

FASE 0 sub-fase B (auditoría eIDAS exhaustiva) **CANCELADA conscientemente** el 25 abril 2026. La limpieza de prosa documental no aporta valor sin un plan mayor: el código real ya implementa firma simple Art. 25.1 correctamente; solo los docstrings y prosa documental mencionan "eIDAS advanced". El script `scripts/s11_eidas_audit.sh` queda como utilidad neutra reutilizable; los hallazgos del run permanecen en `progress/session_11/eidas_audit/` como histórico (regla 8). Si un cliente AAPP exige eIDAS cualificada en el futuro, se reabrirá esta decisión con un ADR nuevo.

---

# ADR-010 — Cláusula firma C-001 + página "Cómo funciona la firma" portal cliente

**Fecha**: 2026-04-25
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: ADR-009 (NO eIDAS/TSA preventivo)

## Contexto

ADR-009 define que FULKRO usa firma simple eIDAS Art. 25.1, NO firma cualificada Art. 26. El cliente tiene derecho a saber **claramente** qué es y qué no es válido para presentar ante AAPP. Sin esto, hay riesgo de que el cliente asuma que la firma electrónica de FULKRO le sirve para presentación CCN/MINHAP/AEPD, lo que sería falso.

## Decisión

### 10.1 Cláusula obligatoria en plantilla C-001

Plantilla M06 Document Factory `templates/C-001.md.j2` incluye **Cláusula 14**:

> **Cláusula 14 — Firma electrónica y validez documental**
>
> 14.1. La plataforma FULKRO ofrece firma electrónica simple conforme al art. 25.1 del Reglamento UE 910/2014 (eIDAS) y la Ley 59/2003 española. Esta firma incluye:
> - Vinculación criptográfica EC P-256 (curva NIST P-256)
> - Verificación dual mediante OTP (One-Time Password) enviado al email del firmante
> - Cadena hash inmutable append-only sobre log de auditoría
> - Trazabilidad completa: IP, user-agent, timestamp UTC, identidad firmante
>
> 14.2. **Alcance válido**: la firma electrónica de FULKRO es válida y suficiente para:
> - **Procesos internos del SGSI** del CLIENTE (aprobación políticas internas, declaraciones aplicabilidad, actas comité seguridad, declaraciones responsable de seguridad, autorizaciones internas).
> - **Relaciones contractuales entre LAS PARTES** (este contrato C-001, propuestas P-XXX, anexos, ampliaciones, modificaciones, retainer R-XXX, etc.).
> - **Documentación interna ENS** auditada por auditor ENAC externo (los auditores ENAC aceptan evidencia hash chain como prueba de firma simple verificable).
>
> 14.3. **Alcance NO válido**: la firma electrónica de FULKRO **no constituye firma electrónica cualificada** conforme al art. 26 del Reglamento eIDAS y por tanto **NO es válida para**:
> - Presentación de documentos ante el Centro Criptológico Nacional (CCN) que exijan certificado cualificado.
> - Presentación de documentos ante Hacienda, Seguridad Social, AEPD u otros organismos públicos AAPP que requieran certificado cualificado de firma personal del representante legal del CLIENTE.
> - Cualquier otro procedimiento que exija contractualmente o normativamente firma electrónica cualificada con TSA acreditada.
>
> 14.4. Para los procedimientos del apartado 14.3, **el CLIENTE firmará los documentos finales con su propio certificado cualificado** (FNMT representante legal, Camerfirma, Firmaprofesional u otro reconocido), usando AutoFirma o herramienta equivalente. FULKRO entregará el documento final en formato editable o PDF para que el CLIENTE pueda aplicar su firma cualificada externamente.
>
> 14.5. FULKRO archivará los documentos firmados externamente por el CLIENTE en el sistema de gestión documental (M24 IDMS) con metadato `signed_externally: true` para trazabilidad, sin validar la firma cualificada externa (la validación corresponde al sistema que la generó).
>
> 14.6. Si en cualquier momento durante la ejecución del contrato se hace evidente que un documento concreto requiere firma cualificada con TSA acreditada y el CLIENTE solicita que FULKRO integre dicha funcionalidad, las partes acordarán por escrito una ampliación de alcance con coste adicional (estimado 1-2 días de integración + coste de servicio TSA público anual).

### 10.2 Página `/client-portal/firma` — "Cómo funciona la firma electrónica de FULKRO"

Contenido completo de la página (texto literal para implementación):

> ### ¿Qué tipo de firma usa FULKRO?
>
> FULKRO usa **firma electrónica simple** con verificación criptográfica EC P-256 + OTP. Esta firma es:
> - **Válida** para tus procesos internos del SGSI y para nuestro contrato.
> - **NO válida** para documentos que vayas a presentar ante el CCN, Hacienda, Seguridad Social u otros organismos que exijan firma cualificada.
>
> ### ¿Qué pasa cuando firmo un documento desde el email que me llega?
>
> Cuando recibes un email con un magic link de firma:
> 1. Haces clic en el enlace
> 2. Te pedimos un OTP (código de 6 dígitos enviado a tu email)
> 3. Confirmas que aceptas el contenido
> 4. FULKRO genera la firma criptográfica EC P-256
> 5. La firma se vincula a una cadena hash inmutable
> 6. El documento queda firmado y archivado
>
> Esta firma es robusta para uso interno del SGSI y para nuestras relaciones contractuales.
>
> ### ¿Cuándo necesitas firmar con tu certificado cualificado?
>
> Necesitas tu certificado cualificado (FNMT, Camerfirma, Firmaprofesional) cuando:
> - Vas a presentar el documento al CCN como evidencia ante auditor ENAC.
> - Vas a presentarlo ante Hacienda, Seguridad Social o AEPD.
> - El procedimiento administrativo lo exige expresamente.
>
> Para estos casos, FULKRO te entregará el documento final en PDF y lo firmas tú con AutoFirma + tu certificado.
>
> ### ¿Qué pasa si pierdo el email del magic link?
>
> Marcos puede regenerarte el magic link en cualquier momento. Tu firma anterior no se pierde si ya la hiciste, queda registrada en el log inmutable.
>
> ### ¿Cómo verifico que mi firma es válida?
>
> Cada firma genera una entrada en el log de auditoría con:
> - Tu email
> - El documento
> - La fecha/hora UTC
> - Tu IP y dispositivo
> - El hash criptográfico
>
> Puedes ver tus firmas en `/client-portal/account/firmas`.
>
> ### Más información legal
>
> - Reglamento UE 910/2014 (eIDAS) artículo 25.1 sobre firma electrónica simple
> - Ley 59/2003 española de firma electrónica
> - Documento contractual C-001 cláusula 14
> - Si tienes dudas legales específicas, escríbele a Marcos desde tu inbox.

### 10.3 Implementación

- Editar `backend/app/motors/m06_document_factory/templates/C-001.md.j2` añadiendo cláusula 14 (asegurar numeración resto cláusulas)
- Crear `frontend/app/client-portal/firma/page.tsx` con contenido literal arriba (MDX o JSX)
- Link visible "Cómo funciona la firma" en sidebar portal cliente + en cada página de firma magic link
- Tooltip en `/client-portal/account/firmas` explicando qué cada firma es válida para qué
- Componente reusable `SignatureScopeTooltip` integrado en cada ruta `(public)/sign/[token]/`, `(public)/approve-proposal/[token]/`, etc.

### 10.4 Revisión post-S11

ADR-010 nota: "Esta cláusula y página están escritas por Marcos + Claude sin asesoría legal formal. Debe ser revisada por abogado TIC antes del primer cliente firmante." → registrar en `progress/backlog_formal.md` como `TODO-LEGAL-001`.

## Consecuencias

- Cliente entiende alcance sin sorpresas → confianza
- Marcos protegido contractualmente si cliente intenta usar firma FULKRO para CCN
- Posicionamiento claro: FULKRO = consultoría con plataforma, no Sello de tiempo qualified
- Trazabilidad ADR-009 + ADR-010 + LEGAL_DISCLAIMERS.md + cláusula 14 C-001 + página `/client-portal/firma` (5 puntos consistentes)

---

# ADR-011 — Magic Links auditoría + ampliación + email destinatario configurable

**Fecha**: 2026-04-25
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: M12 Magic Links (existente)

## Contexto

M12 tiene 23 purposes implementados (`ONBOARDING_INICIAL`, `FIRMA_DOCUMENTO`, etc.). Marcos pide:
1. Verificar que TODOS funcionan a la perfección
2. Crear magic links faltantes que cubran todo el ciclo
3. Configurar email destinatario al que se mandan (no solo el contacto principal)

## Decisión

### 11.1 Auditoría completa magic links existentes

FASE 4.5 sub-tarea 4.5.A: ejecutar auditoría exhaustiva de los 23 purposes existentes verificando para cada uno:

| # | Verificación | Output |
|---|--------------|--------|
| V1 | El purpose está implementado en `m12_magic_link/purposes.py` | Sí/No |
| V2 | Existe template HTML email correspondiente en `templates/email/magic_link/{purpose}.html.j2` | Sí/No |
| V3 | Existe ruta frontend `/{purpose-route}/[token]/page.tsx` que consume el magic link | Sí/No |
| V4 | Tiene tests E2E (Playwright + backend) | Sí/No |
| V5 | Está documentado en `docs/spec/MAGIC_LINKS.md` con flujo completo | Sí/No |
| V6 | Audit log entry generado correctamente | Sí/No |
| V7 | Hash chain integrity verificada al consumir | Sí/No |
| V8 | TTL razonable (no infinito, no demasiado corto) | Sí/No |
| V9 | One-time consumption funcionando | Sí/No |
| V10 | Rate limiting aplicado (max 5 reintentos) | Sí/No |

Output: `progress/session_11/magic_links_audit/REPORT.md` con tabla 23 × 10 verificaciones + lista de gaps detectados.

### 11.2 Ampliación con 12 purposes nuevos

Magic links **NUEVOS** que cubren huecos del ciclo ENS:

| # | Nuevo Purpose | Caso de uso | Etapa | Receptor típico |
|---|--------------|-------------|-------|-----------------|
| 24 | `INVITACION_REUNION` | Invitar contacto cliente a reunión K.0/K.2/K.4 con link calendario externo | Pre-K | CISO, CTO, CEO |
| 25 | `APROBACION_PROPUESTA` | Cliente aprueba P-001 antes de firmar C-001 (intención compromiso) | Post-K.4 | Sponsor (CEO/CFO) |
| 26 | `APROBACION_FACTURA` | Cliente aprueba factura antes envío oficial (evita disputas) | Mensual M15 | Compras / Legal |
| 27 | `SOLICITUD_INFORMACION` | Marcos pide info específica al cliente | Cualquier fase | Variable |
| 28 | `VALIDACION_CAMBIO_ALCANCE` | M28 Change Governance — cliente valida cambio scope | Cualquier fase | Sponsor |
| 29 | `ACEPTACION_RIESGO_RESIDUAL` | RSEG aprueba riesgo residual MAGERIT (firma ad-hoc) | M02/M27 | RSEG |
| 30 | `COMUNICACION_INCIDENTE_SEGURIDAD` | Notificación obligatoria incidente seguridad ENS | Conformidad continua | RSEG + CISO |
| 31 | `CONSENTIMIENTO_TRATAMIENTO_DATOS` | RGPD — cliente firma cláusula tratamiento datos personales (DPA) | Onboarding | DPO / Legal |
| 32 | `CONFIRMACION_CONFORMIDAD` | M27 — cliente confirma estado conformidad antes submission ENAC | Pre-auditoría | RSEG + Sponsor |
| 33 | `DESCARGA_CERTIFICADO_CONFORMIDAD` | Cliente descarga certificado conformidad ENS firmado por ENAC | Post-conformidad | CEO + Legal |
| 34 | `VOTACION_COMITE_SEGURIDAD` | M18 Comité Seguridad — voto online para acta | Cuatrimestral | Miembros comité |
| 35 | `ENCUESTA_SATISFACCION_NPS` | NPS post-cierre proyecto + retainer renovation | Cierre/aniversario | Sponsor + interlocutor |

**Total post-S11**: 23 (existentes) + 12 (nuevos) = **35 purposes**.

### 11.3 Email destinatario configurable por envío

Hoy: cuando Marcos genera un magic link, el sistema usa el email del `client_user` o `client_contact` principal por defecto.

**Cambio**: cada generación de magic link permite especificar `recipient_email` opcional que **override** al default.

API change:
```python
POST /api/v1/magic-links/generate
{
  "purpose": "FIRMA_DOCUMENTO",
  "client_id": "uuid",
  "document_id": "uuid",
  "ttl_hours": 48,
  "require_otp": true,
  "recipient_email": "compras.especifico@dataforma.es"  # ← NUEVO opcional
  // si null → usa client_user.email default
}
```

UI change (`/admin/clients/[id]` tab "Documentos" o "Acciones"):
- Botón "Generar magic link FIRMA_DOCUMENTO"
- Modal: select contact dropdown (autopopulado de M30 Client Contacts) + opción "Email custom" + textbox
- Validación email format
- Toast confirmación "Link enviado a {email}"

**Por qué importa**:
- Cliente PYME tiene multiple stakeholders (CEO firma C-001 / Compras firma facturas / RSEG firma riesgos / DPO firma RGPD)
- Forzar todo al mismo email es fricción operativa
- Permitir custom email cubre casos edge (ej. asistente del CEO recibe pero CEO firma)

### 11.4 Tabla `magic_links` ampliación

```sql
ALTER TABLE magic_links
  ADD COLUMN recipient_email VARCHAR(320),
  ADD COLUMN cc_emails TEXT[],
  ADD COLUMN sent_to_contact_id UUID REFERENCES client_contacts(id) ON DELETE SET NULL,
  ADD COLUMN custom_subject VARCHAR(255),
  ADD COLUMN custom_body_intro TEXT;

CREATE INDEX idx_magic_links_sent_to_contact ON magic_links(sent_to_contact_id);
```

## Consecuencias

- 12 purposes nuevos cubren ciclo completo
- Email configurable por envío → flexibilidad
- Audit trail completo via `sent_to_contact_id` (¿a qué contacto exactamente fue?)
- Marcos puede personalizar mensaje sin modificar template global

---

# ADR-012 — Motor M30 Client Contacts (lista contactos por empresa)

**Fecha**: 2026-04-25
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: M21 Portal Cliente, M29 Messaging, A14 Copilot, A18 Reunión

## Contexto

Marcos pide *"lista de contactos agendados en la memoria de cada empresa con su cargo, que lo tenga presente FULKRO"*. Hoy `client_users` solo guarda usuarios con login al portal cliente. Faltan:
- Contactos sin login (CTO que solo recibe info, CEO que firma pero no opera)
- Cargo formal de cada contacto
- Notas Marcos sobre cada contacto ("simpático", "decision-maker", "técnico", "duro negociador")
- Visibilidad en Copilot A14 + panel A18 + M29 messaging

## Decisión

### 12.1 Motor M30 Client Contacts — schema

```sql
CREATE TABLE client_contacts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  
  -- Identidad
  full_name VARCHAR(255) NOT NULL,
  preferred_name VARCHAR(100),
  email VARCHAR(320) NOT NULL,
  phone VARCHAR(50),
  linkedin_url VARCHAR(500),
  
  -- Rol en la empresa cliente
  role_title VARCHAR(150) NOT NULL,
  role_category VARCHAR(50) NOT NULL CHECK (role_category IN (
    'sponsor', 'rseg', 'ciso', 'cto', 'cio', 'dpo', 'legal',
    'compras', 'rrhh', 'operaciones', 'tecnico',
    'auditor_interno', 'consultor_externo', 'usuario_final', 'otros'
  )),
  
  -- Contexto operativo FULKRO
  is_primary BOOLEAN DEFAULT FALSE,
  is_signatory BOOLEAN DEFAULT FALSE,
  has_portal_access BOOLEAN DEFAULT FALSE,
  client_user_id UUID REFERENCES client_users(id) ON DELETE SET NULL,
  
  -- Agenda relacional
  notes_marcos TEXT,
  preferred_communication VARCHAR(20) CHECK (preferred_communication IN (
    'email', 'phone', 'whatsapp', 'linkedin_dm', 'portal_inbox'
  )),
  timezone VARCHAR(50) DEFAULT 'Europe/Madrid',
  
  -- Operativa
  is_active BOOLEAN DEFAULT TRUE,
  inactive_reason VARCHAR(200),
  inactive_since TIMESTAMPTZ,
  
  -- Metadata
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by_user_id UUID REFERENCES auth_users(id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  UNIQUE (client_id, email)
);

CREATE INDEX idx_client_contacts_client_id ON client_contacts(client_id);
CREATE INDEX idx_client_contacts_role_category ON client_contacts(client_id, role_category);
CREATE INDEX idx_client_contacts_is_primary ON client_contacts(client_id) WHERE is_primary = TRUE;
CREATE INDEX idx_client_contacts_signatory ON client_contacts(client_id) WHERE is_signatory = TRUE;
CREATE INDEX idx_client_contacts_notes_fts ON client_contacts USING gin(to_tsvector('spanish', notes_marcos));

ALTER TABLE client_contacts ENABLE ROW LEVEL SECURITY;
CREATE POLICY admin_full_access ON client_contacts USING (current_setting('app.role') = 'admin');
CREATE POLICY client_self_view ON client_contacts USING (client_id = current_client_id() AND has_portal_access = TRUE);

CREATE TRIGGER client_contacts_updated_at_trigger
  BEFORE UPDATE ON client_contacts
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
```

### 12.2 Tabla `client_contact_interactions`

```sql
CREATE TABLE client_contact_interactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES client_contacts(id) ON DELETE CASCADE,
  interaction_type VARCHAR(30) NOT NULL CHECK (interaction_type IN (
    'meeting_attended',
    'email_sent', 'email_received',
    'call_made', 'call_received',
    'whatsapp_exchange',
    'magic_link_sent', 'magic_link_consumed',
    'message_sent', 'message_received',
    'document_signed',
    'note_added'
  )),
  related_entity_type VARCHAR(50),
  related_entity_id UUID,
  summary TEXT,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_contact_interactions_contact_occurred ON client_contact_interactions(contact_id, occurred_at DESC);
CREATE INDEX idx_contact_interactions_type ON client_contact_interactions(interaction_type, occurred_at DESC);
```

### 12.3 Integración con motores existentes

| Motor | Integración |
|-------|-------------|
| **A14 Copilot** | Inyecta contactos cliente en system prompt cuando contexto incluye client_id. Copilot puede "Quien es Maria García en DataForma?" → responde "CISO, contacto técnico principal, decision-maker decisión técnica, simpática" |
| **A18 Reunión** | Panel reunión muestra dropdown "Interlocutor" autopopulado desde M30 contacts. Auto-tag interacción `meeting_attended` |
| **M29 Messaging** | Marcos puede enviar mensaje a contacto sin login portal (`@-mention` autocomplete con contactos M30). Email forward + tracking de envío |
| **M12 Magic Links** | Generación magic link permite seleccionar contacto destinatario M30 (no solo client_user). `magic_links.sent_to_contact_id` foreign key |
| **M14 Contracts** | C-001 menciona signatarios autorizados (contactos con `is_signatory=true`) |
| **M21 Portal Cliente** | Si contacto tiene `has_portal_access=true`, se le crea `client_user` vinculado |
| **M27 Conformity** | RSEG (rol `rseg`) firma aceptación riesgo residual via magic link `ACEPTACION_RIESGO_RESIDUAL` |

### 12.4 UI Frontend — admin

**Ruta nueva**: `/admin/clients/[id]/contacts/`

**Componentes**:
- `ContactsList` — DataTable con cargo, email, primary badge, signatory badge, has_portal badge, última interacción
- `ContactDetail` — drawer Sheet con info completa + timeline interacciones + notas Marcos editables
- `ContactCreateWizard` — 3 pasos: identidad → rol → opciones (signatario / portal access)
- `ContactImporter` — bulk import CSV/vCard
- `ContactQuickPicker` — autocompletar dropdown reusable (usado en M29 composer, M12 generación, A18 panel)

### 12.5 Integración Copilot A14

En CopilotPanel, Marcos puede preguntar:
- "¿Quién es el RSEG en DataForma?"
- "Dame la lista de contactos en el cliente Hospital San Juan ordenados por última interacción"
- "¿Qué notas tengo sobre María García de DataForma?"
- "¿Quién firma facturas en cliente X?"

Copilot responde leyendo `client_contacts` + `client_contact_interactions` filtrado por client_id.

## Consecuencias

- Marcos no pierde contexto entre clientes
- Mensajería + magic links + reuniones quedan vinculadas a contactos específicos (timeline relacional)
- Copilot tiene memoria social del cliente
- Cliente solo ve sus propios contactos si tienen portal access (RLS verificado)

---

# ADR-013 — Separación arquitectónica de portales · admin / radar / client

**Fecha**: 2026-04-25
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García

## Contexto

FULKRO necesita servir a dos audiencias completamente diferentes desde la misma plataforma:

1. **Marcos** (operador, propietario, admin único) — gestiona clientes, proyectos ENS, contactos M30, mensajería, settings, **y prospección comercial vía ENS Radar (m10) admin-only**.
2. **Cliente** (empresa que paga consultoría ENS) — accede a su portal a ver el estado de su proyecto, sus documentos, sus facturas, sus reuniones con Marcos, su inbox.

Hasta ahora la app mezclaba rutas y dependía de `is_admin` flags dispersos. ENS Radar es **información comercial sensible y privada de Marcos**: leads, dossiers de venta, dolor del prospect, emails pre-redactados, oportunidades. Un cliente NO puede ver nunca, bajo ningún concepto, nada de `/radar`. Esto exige una separación arquitectónica formal de **tres portales independientes** con middleware de routing role-based estricto.

## Decisión

Tres namespaces de ruta separados con autenticación común pero autorización divergente:

| Portal | Namespace | Audiencia | Topbar | Sidebar |
|--------|-----------|-----------|--------|---------|
| **Admin Console** | `/admin/*` | Marcos solo | FULKRO logo + portal switcher (Admin ↔ Radar) + perfil | Clientes · Proyectos · Contactos M30 · Reuniones · Mensajería · Magic Links · Settings |
| **ENS Radar** | `/radar/*` | Marcos solo | ENS Radar logo (rojo/naranja) + portal switcher (Radar ↔ Admin) + perfil | Dashboard · Leads · Clusters · Histórico runs |
| **Client Portal** | `/client-portal/*` | Cliente solo | FULKRO logo + nombre cliente + perfil cliente | Estado · Roadmap · Documentos · Facturas · Cuestionarios · Evidencias · Inbox · Calendario · FAQ · Cómo funciona la firma · Cuenta |

**Login flow unificado** en `/login` con redirect role-based:

```
POST /api/auth/login (email + password [+ TOTP opcional Marcos])
  ↓
Backend valida + emite JWT con claims { sub, email, role: "owner"|"client_user", client_id?, is_owner }
  ↓
Frontend lee role:
  - role="owner" (Marcos) → redirect /admin (default landing) · puede ir a /radar via switcher
  - role="client_user" (cliente) → redirect /client-portal · NO puede acceder /admin ni /radar
```

**Middleware Next.js** (`frontend/middleware.ts`) actualizado con tres reglas:

```typescript
// Regla 1: rutas /admin/* requieren role=owner
if (pathname.startsWith('/admin')) {
  if (!session) return redirect('/login?next=' + pathname)
  if (session.role !== 'owner') return redirect('/client-portal')
}

// Regla 2: rutas /radar/* requieren role=owner + email en ENS_RADAR_OWNERS
if (pathname.startsWith('/radar')) {
  if (!session) return redirect('/login?next=' + pathname)
  if (session.role !== 'owner') return new Response('403 Forbidden', { status: 403 })
  if (!session.is_ens_radar_owner) return new Response('403 Forbidden', { status: 403 })
}

// Regla 3: rutas /client-portal/* requieren role=client_user
if (pathname.startsWith('/client-portal')) {
  if (!session) return redirect('/login?next=' + pathname)
  if (session.role !== 'client_user') return redirect('/admin')
}
```

**Backend FastAPI**: `require_owner` (admin) + `require_ens_radar_owner` (subset estricto vía env `ENS_RADAR_OWNERS`) + `require_client_user` dependencias. Todos los endpoints de motores M01-M30 ya tienen RLS por `client_id`. Los endpoints de ENS Radar (motor m10) se protegen con `require_ens_radar_owner` y JAMÁS son consultables por client_user.

**Portal switcher** (componente `PortalSwitcher.tsx` en topbar admin/radar):

- Visible SOLO si `session.is_owner === true`.
- Dropdown con 2 opciones: "Admin Console" (link `/admin`) y "ENS Radar" (link `/radar`).
- Estado activo resaltado según pathname actual.
- Cliente nunca ve este componente porque su layout `/client-portal/*` no lo incluye.

**Aislamiento UI verificable**:
- `/admin` y `/radar` comparten chrome (header con switcher + perfil) pero **datos completamente diferentes** y no enlazan a `/client-portal`.
- `/client-portal` tiene chrome propio (logo FULKRO + nombre cliente) que **nunca enlaza** a `/admin` ni `/radar`. No hay rutas escapadas.
- Tests Playwright cliente intenta acceder a `/admin/clients` → recibe redirect a `/client-portal` (no error, redirect silencioso).
- Tests Playwright cliente intenta acceder a `/radar` → recibe **403 Forbidden** explícito (más estricto porque es información comercial privada).

**Cuando Marcos entra a un proyecto cliente concreto (`/admin/projects/[id]/*`)**, todo lo que ve es información del proyecto ENS de ese cliente: diagnosis, MAGERIT, obligations, evidence, verification, conformity, retainer, roadmap, contacts del cliente, mensajería con el cliente. **Ningún componente de ENS Radar aparece dentro del scope de proyecto** — la prospección comercial es un dominio totalmente separado.

## Consecuencias

- **Privacidad comercial garantizada**: cliente nunca verá leads, dossiers ni emails de prospección.
- **Cognitive load reducido para Marcos**: cada portal tiene su propio chrome y nav, no hay confusión de en qué modo está.
- **Switching ágil**: ⌘. (Cmd-punto) o click switcher topbar para cambiar entre Admin y Radar en 1 segundo.
- **Tests separables**: suite Playwright `tests/admin/*`, `tests/radar/*`, `tests/client-portal/*` independientes.
- **Deploy unificado**: misma app Next.js, mismo backend, misma BD; sólo middleware + auth claims separan.
- **Migración de routing**: rutas pre-S11 que no estaban en namespace `/admin/*` (ej. `/projects/[id]/*` plano) deben ser movidas a `/admin/projects/[id]/*` durante FASE 3 ampliada o FASE 9 frontend v0.2.
- **Portal switcher tests visual regression**: estado activo Admin vs Radar verificado.

---

# ADR-014 — Portal ENS Radar admin-only · pipeline v2 + UI completa + tracking runs

**Fecha**: 2026-04-25
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García

## Contexto

El motor `m10_ens_radar` ya existe en código (Sesión 4) como motor de detección automatizada de leads ENS desde scraping PLACSP/BOE. Hasta ahora se operaba mediante CLI manual + exports CSV al Desktop de Windows, sin UI propia, con un pipeline v1 que tenía 5 fallos críticos detectados:

1. **Detector ENS** producía falsos positivos cuando mencionaba ENS solo en contexto histórico de adjudicación previa.
2. **Temperature scoring** no diferenciaba "ardiendo por exclusión" (lead crítico) de "ardiendo sostenido" (histórico).
3. **Repeated winners** sin filtro temporal contaba adjudicaciones de hace 5 años como señal de necesidad ENS actual.
4. **ICP filter** rechazaba leads buenos por importe fuera de banda fija, sin sweet spot por CPV.
5. **Dossier prompt** generaba narrativa genérica sin "dolor + plazo + por qué tú".

Adicionalmente, 7 mejoras de calidad de leads requieren:
- Inferencia explícita del nivel ENS (Bajo/Medio/Alto) desde texto del pliego.
- Cluster de leads por (provincia · sector organismo · tipo servicio) para emails masivos por plantilla.
- Filtro temporal "vence_pronto_oferta" (fecha_fin_oferta < 30 días).
- Marcado `es_lead_excluido_ens` para clientes excluidos por falta de certificación.
- Marcado `contactable=false` cuando ya se contactó recientemente.
- Tracking explícito de plazo CEE (Certificación Esquema ENS) en meses según pliego.
- Días hasta vencimiento CEE calculados.

Marcos necesita además **operativa diaria desde UI** (no más CSV al Desktop): dashboard con métricas, tabla filtrable de leads, drawer de detalle con email pre-redactado para copiar, edición rápida de estado del lead (descartar/contactado/respondido), histórico de runs con métricas de performance, vista de clusters para email batch.

## Decisión

Integrar el plan ENS Radar Portal admin-only completo como FASE 8.5 del plan Sesión 11, con las siguientes piezas:

**Backend** (motor `m10_ens_radar`):

1. **Modelo `PipelineRun` nuevo** en `backend/app/motors/m10_ens_radar/db/models.py` con tracking de cada ejecución (started_at, finished_at, cancelled_at, status, since_date, until_date, tenders_ingested, leads_created, current_step, progress_pct, error_message, summary_json, triggered_by, triggered_via).
2. **Lead ampliado**: campos `cluster_id`, `plazo_cee_meses_pliego`, `dias_hasta_vencimiento_cee`, `fecha_fin_oferta_proxima`, `es_lead_excluido_ens`, `contactable`.
3. **ENSAnalysis ampliado**: campos `nivel_ens_inferido`, `confidence_score`, `reasoning_text`.
4. **Migración SQL idempotente** Alembic con creación tabla + ALTER columns.
5. **Detector ENS v2**: prompt reescrito con few-shot examples, parser JSON con fallback robusto, reasoning explícito.
6. **Inferencia de nivel ENS**: detección "Bajo / Medio / Alto" desde texto del pliego.
7. **Temperature scoring v2**: 7 niveles (`ardiendo_excluido`, `vence_pronto_oferta`, `ardiendo_sostenido`, `ardiendo`, `caliente`, `tibio`, `frio`) con prioridad descendente.
8. **Repeated winners** con filtro temporal últimos 12 meses.
9. **ICP filter** con sweet spot por CPV (importes razonables por categoría).
10. **Dossier prompt reescrito**: estructura "dolor / plazo / por qué tú" con few-shot, fallback narrativo.
11. **CSV exporter** "leads del lunes" para entrega puntual + histórico.
12. **Cost limit config** (`MAX_COST_PER_RUN_USD`, default 5.0) con kill-switch.
13. **Runner con gestión de runs + cancelación cooperativa**: `is_run_active()`, `signal_cancel()`, `get_active_run()`.
14. **Pipeline orchestrator** con ejecución incremental (cada lanzamiento procesa solo desde el último run completado), tracking actualizando `current_step` y `progress_pct` en BD, cancelación cooperativa que detiene sin corromper datos.
15. **Auth admin-only**: dependency `require_owner` que verifica email contra env `ENS_RADAR_OWNERS` (default `marcos@fulkro.io`).
16. **Schemas Pydantic v2** completos: `LeadResponse`, `LeadDetailResponse`, `RunStatusResponse`, `DashboardStatsResponse`, `LaunchRunRequest`, `LaunchRunResponse`, `UpdateLeadRequest`, `RunHistoryItem`, `ClusterSummary`.
17. **9 endpoints REST** bajo `/api/v1/ens-radar`:
    - `POST /run/launch` — arrancar pipeline en background task
    - `POST /run/cancel` — cancelar run activo
    - `GET /run/status` — estado run activo (polling 3s)
    - `GET /runs` — histórico últimas 50 ejecuciones
    - `GET /stats` — estadísticas dashboard (top temperaturas, clusters, urgencias)
    - `GET /leads` — listado leads filtrable (temperatura, contactable, cluster_id, search)
    - `GET /leads/{lead_id}` — detalle lead + email pre-redactado + dossier
    - `PATCH /leads/{lead_id}` — actualizar estado lead (descartar, contactado, respondido, nota)
    - `GET /clusters` — agrupaciones por (provincia · sector · tipo servicio)
18. **Tests backend**: 12 tests cubriendo runner, pipeline incremental, cancelación, scoring v2, detector v2, ICP filter, auth admin-only.

**Frontend** (namespace `/radar/*`):

19. **Cliente API tipado** `frontend/src/lib/api/ens-radar.ts` con types Lead, LeadDetail, RunStatus, DashboardStats + funciones fetch.
20. **Hooks React Query**: `useRunStatus` (polling 3s mientras run activo), `useLeads`, `useLeadDetail`, `useStats`, `useRuns`, `useClusters`.
21. **Componentes UI** (en `frontend/src/components/ens-radar/`):
    - `TemperatureBadge` — color-coded por temperatura
    - `RunStatusBanner` — banner sticky cuando run activo con barra progreso + botón cancelar
    - `RunControlBar` — botón "Lanzar pipeline" + selector bootstrap_days + cost limit warning
    - `StatsCards` — 4 cards (total leads, ardiendo, contactables, runs ok)
    - `LeadsTable` — DataTable shadcn con filtros + ordenación + click row → drawer
    - `EmailPreview` — markdown render del email pre-redactado + copy to clipboard
    - `LeadDetailDrawer` — drawer derecho con tabs (Empresa, Pliego, Dossier, Email, Acciones)
    - `RunHistoryTable` — tabla histórico con duración, estado, n_leads, errores
22. **Páginas portal** (en `frontend/src/app/radar/`):
    - `layout.tsx` — chrome rojo/naranja + nav 4 tabs (Dashboard, Leads, Clusters, Runs) + badge "ADMIN ONLY" + portal switcher
    - `page.tsx` — Dashboard (RunStatusBanner + RunControlBar + StatsCards + tabla "Leads ardiendo" + drawer)
    - `leads/page.tsx` — listado completo filtrable (con `?cluster_id=X` opcional)
    - `clusters/page.tsx` — grid de cards de clusters con n_leads + link a `/radar/leads?cluster_id=...`
    - `runs/page.tsx` — histórico runs

**Aislamiento estricto del portal**:
- `/radar/*` requiere middleware role-based + email en `ENS_RADAR_OWNERS` (doble verificación).
- Cliente intenta `GET /api/v1/ens-radar/leads` → **403 Forbidden** (no redirect, error explícito).
- Cliente intenta `GET /radar` → **403 Forbidden** (no redirect).
- Layout `/radar/layout.tsx` NO importa nada del namespace `/client-portal/*` ni nada de `m29_messaging` ni `m30_contacts` (separación de dominios).
- ENS Radar es info comercial PRIVADA de Marcos; cliente sólo ve `client-portal`.

**Entrega puntual hoy (FASE 22 del doc original)**: tras completar el portal, hacer un único run de demostración con export CSV al Desktop de Windows. A partir del día siguiente, toda la operativa es desde UI. Esta fase se mantiene como sub-tarea final del entregable FASE 8.5.

**Cost control**: `MAX_COST_PER_RUN_USD` env var (default 5.0) verificada antes de cada llamada LLM Anthropic. Si se excede, run aborta con `status="cost_limit_exceeded"`.

## Consecuencias

- **Calidad de leads**: pipeline v2 reduce falsos positivos ~70% según muestra histórica de Marcos.
- **Operativa fluida**: lanzar pipeline + revisar leads + copiar email + marcar contactado, todo desde UI sin tocar terminal.
- **Auditoría completa**: cada run queda trackeado en BD con métricas, errores y output JSON; histórico consultable.
- **Cancelación segura**: si Marcos detecta error en mitad de run (ej. coste descontrolado), botón cancelar lo detiene sin corromper.
- **Coste mensual estimado**: ~10-30€/mes Anthropic API para runs semanales (vs 50-80€ con pipeline v1 que reprocesaba todo).
- **Cliente NUNCA ve este portal**: aislamiento estricto verificado por tests.
- **Outreach paralelo Marcos** (regla 5): este portal es la herramienta principal para ejecutar la regla outreach en `progress/sales_log.md` — leads detectados aquí alimentan los emails que Marcos envía a prospects mientras desarrolla el resto.

---

# ADR-015 — role en BD (identidad invariante) vs capabilities en Settings (toggles operacionales)

**Fecha**: 2026-04-27
**Estado**: Aprobado (Sesión 11)
**Decisor**: Marcos Mata García
**Referencias**: ADR-013 (separación 3 portales), FASE 3 sub-paso 3.A.0

## Contexto

Durante el audit pre-FASE 3 se descubrió que el modelo `User` (`backend/app/models/auth.py`) no tenía campo `role`. El plan v4.2 asumía role en JWT claims (`is_owner = user.role == "owner"`, `require_client_user: claims.role != "client_user"`) pero no había formalizado dónde vive ese role.

Adicionalmente, ADR-013 introdujo `ens_radar_owners` como Settings (lista de emails con acceso a `/radar/*`), lo que abrió la pregunta arquitectónica más amplia: **¿cuándo va una propiedad de usuario en BD y cuándo en Settings/env?**

Sin formalizar esta distinción, el equipo (Marcos + Claude) corría el riesgo de mezclar criterios entre features futuras: a veces poner roles en Settings (rígido, despliegue requerido), a veces capabilities en BD (sobre-modelado). Decisión arquitectónica necesaria antes de tocar 3.A para evitar deuda de patrón.

## Decisión

**`role` vive en BD como columna invariante del modelo `User`**.
- Tipo: `String(32)` plano (NO Enum SQLAlchemy, para permitir extensibilidad sin migración Alembic)
- Default y `server_default`: `"owner"` (preserva Marcos seed sin intervención manual)
- Valores soportados (`backend/app/auth/constants.py::ALLOWED_ROLES`):
  - `owner` — Marcos hoy, futuros co-fundadores
  - `client_user` — usuarios de las empresas cliente con acceso a `/client-portal/*`
  - `partner_senior` — co-consultor categoría Alta (figura prevista pero no en uso hoy)
  - `pentester_external` — pentester contratado para `/pentester-portal/*` (motor M11)
  - `introducer` — comisionista que solo accede a su pipeline (motor M28)
- Validación de valores en service layer (constante `ALLOWED_ROLES`), no a nivel BD (extensibilidad)

**Capabilities como `ens_radar_owner` viven en Settings** (lista de emails).
- Tipo: `list[str]` con default `["marcos@fulkro.es"]`
- Razón: son toggles operacionales que Marcos puede ajustar sin migración (ej. añadir `partner_senior` temporal a `ens_radar_owners` durante un cliente categoría Alta y quitarlo después)
- No son parte de la identidad del usuario, son permisos delegables/revocables
- JWT incluye claim booleano resuelto en login: `is_<capability> = user.email ∈ settings.<capability>_emails`

## Regla mnemotécnica

- **¿Define qué ES el usuario?** → BD (columna `role`)
- **¿Define qué PUEDE HACER en este momento?** → Settings (capabilities)

## Consecuencias

- **Identidad de usuario auditada por BD**: row-level security (RLS), foreign keys, joins, queries SQL — todo lo natural cuando el rol es columna.
- **Capabilities ajustables sin deploy**: cambio en `.env` + reload de Settings (ya soportado por `get_settings.cache_clear()` cuando proceda) sin migración.
- **JWT claims simétricos**: `is_owner` (derivado de `role`), `is_ens_radar_owner` (derivado de capability). Ambos booleanos al frontend para AuthGuard role gating.
- **Coste migración inicial**: ~45 min (FASE 3 sub-paso 3.A.0) — añadir columna + migración Alembic + tests + factory `make_user` reusable.
- **Reversibilidad**: si una decisión futura cambia, mover de BD a Settings (o viceversa) es local al campo afectado, no afecta otros.

Supersedes: implícitamente la lectura literal del plan v4.2 que sugería role en JWT sin especificar origen.

---

# ADR-016 — Drift modelo SQLAlchemy ↔ BD real pendiente de auditoría

**Fecha**: 2026-04-27
**Estado**: Aprobado (Sesión 11) · **Empirically Confirmed 2026-04-28** · **Pendiente resolución**: Mini-Sesión 11.5 (entre FASE 12 y FASE 13)
**Decisor**: Marcos Mata García
**Referencias**: ADR-015 (descubierto al ejecutar la migración de role), TODO-DB-DRIFT-001

## Contexto

Durante FASE 3.A.0 S11, al ejecutar `alembic revision --autogenerate -m "add_role_column_to_auth_users"` para añadir una sola columna a `auth_users`, Alembic generó un archivo de **400+ líneas de DDL** que no correspondían al cambio solicitado.

El análisis del autogenerate reveló **drift masivo entre los modelos SQLAlchemy actuales y la BD real**:

- **DROP COLUMN propuesto en 6 tablas** — algunas con datos potencialmente referenciados:
  - `audit_log.seq`
  - `external_pentester_handoffs.client_id`
  - `lms_assignments.client_id`
  - `verification_findings.client_id`
  - `verification_runs.client_id`
  - `ens_measure_evidencia_types`: 4 columnas (`source_tool`, `format`, `automatable`, `audit_query`)
- **Cambios masivos de índices** en >30 tablas (rename, drop, recreate)
- **Nullable changes**: `created_at` de muchas tablas pasaría de NOT NULL a nullable (regresión)
- **Drop unique constraints** en 3 tablas (`uq_normativa_alerts_source_item`, `uq_retainer_reports_client_periodo`, `uq_pricing_catalog_category_tier_active`)

Los modelos SQLAlchemy y la BD divergieron históricamente: la BD tiene cosas que ya no están en modelos (los DROPs propuestos), y los modelos tienen cosas que la BD no tiene (los ADDs/CREATEs propuestos). Aplicar el autogenerate completo borraría columnas con datos posiblemente referenciados por foreign keys.

## Decisión

**Para FASE 3.A.0** (scope inmediato): migración manual minimalista que **solo añade columna `role`** a `auth_users`. NO se aplica el autogenerate completo bajo riesgo de pérdida de datos.

**Para resolución global del drift**: Mini-Sesión 11.5 dedicada **entre FASE 12 (MicroUX polish) y FASE 13 (pre-deploy hardening)** con estimación 13-20h:

1. Audit 1-a-1 de cada operación DDL del autogenerate (4-6h)
2. Decidir per-operación: aplicar (BD obsoleta) · revertir modelo (modelo obsoleto) · ignorar (intencional sin migración) (3-5h)
3. Generar migraciones limpias por bloques temáticos (M22, M28, verification, ens_measure, etc.) (4-6h)
4. Validación: aplicar fresh DB desde migrations + diff vs BD actual (2-3h)

Snapshot del autogenerate problemático guardado como evidencia inmutable en `progress/session_11/artifacts/drift_audit_2026-04-27.py.txt`.

## Bloqueante explícito

**Sesión 12 (Hetzner VPS deploy) NO debe arrancar sin haber completado Mini-Sesión 11.5.** Deploy con drift activo = riesgo inaceptable de corrupción silenciosa o falla del migrate al hacer `alembic upgrade head` en el VPS.

## Operacional FASE 4-12

Cualquier desarrollador (Marcos · Claude Code · futuras instancias Claude) que necesite añadir columna/tabla durante FASE 4-12:

1. Ejecutar `alembic revision --autogenerate -m "<nombre>"` para **scout** (ver qué propone Alembic)
2. Si autogenerate genera <5 operaciones todas relacionadas con el cambio buscado: aceptar
3. Si autogenerate genera >5 operaciones o trae operaciones destructivas no solicitadas: **PARAR**, crear migración manual minimalista (patrón FASE 3.A.0), formalizar drift adicional descubierto como entry de actualización en TODO-DB-DRIFT-001

Esto preserva el principio de migraciones atómicas y evita agravar el drift hasta 11.5.

## Consecuencias

Positivas:
- FASE 3.A.0 procede sin contaminación de scope
- Drift formalizado y trazable (no se pierde en backlog informal)
- Mini-Sesión 11.5 cierra S11 con BD impecable antes de FASE 13 hardening pre-deploy → Sesión 12 deploy con cero deuda BD

## Empirical Confirmation 2026-04-28

Durante sub-bloque 4.A.1 FASE 4 (creación tabla `admin_settings`), `alembic revision --autogenerate` produjo de nuevo una migración con drift cross-motor masivo. Esta vez con **cifras revisadas al alza**:

- **Original ADR-016 estimaba**: ~50 operaciones DDL
- **Realidad confirmada 2026-04-28**: 380+ operaciones DDL
- **Estimación Mini-Sesión 11.5 escalada**: 20-30h (vs 13-20h original)

Nuevas tablas en el inventario drift (no listadas en el ADR original):
`audit_simulation_findings`/`runs`, `auth_login_attempts`, `auth_sessions`, `auth_webauthn_credentials`, `basic_declarations`, `client_commitments`, `collaborative_workspaces`, `commercial_discounts`, `companies`, `conformity_routes`/`submissions`, `dda_project_signatures`, `diagnosis_runs`, `document_tags`, `documents`, `effort_estimates`, `email_log`, `exploratory_meetings`, `extraordinary_audits`, `false_positive_patterns`, `idms_document_permissions`, `invoice_lines`, `material_changes`, `normativa_alerts`, `onboarding_sessions`, `payment_reminders`, `pce_overlays`, `pricing_catalog`, `project_archived_backups`, `project_lifecycle_events`, `project_plans`, `radar_leads`, `recategorizations`, `remediation_retests`, `renewal_campaigns`, `retainer_*` (varios), `role_*`, `sources_runs`, `stakeholders_graph_snapshots`, `tenders`, `videocall_sessions`, `wbs_tasks`, `workspace_*` (chat_messages, feed_items, files).

### Acción adoptada inmediata (4.A.1)

Edición manual de la migración `506c7a897689_create_admin_settings_table_singleton.py` para conservar **EXCLUSIVAMENTE** las operaciones de su scope (create_table admin_settings + INSERT seed). Las 380+ operaciones drift fueron descartadas y preservadas como artifact forense en:

`progress/session_11/artifacts/drift_audit_2026-04-28.py.txt` (header contextual + raw output completo, 869 líneas, NO commiteado por regla 5).

### Política firme S11 reafirmada

La sección **"Operacional FASE 4-12"** de este ADR es **norma firme**: ninguna migración nueva durante FASE 4-12 toca drift cross-motor. Las migraciones autogenerate se editan manualmente para conservar solo operaciones de su scope. La reconciliación drift es trabajo dedicado de Mini-Sesión 11.5.

### Patrón canónico (2 ejemplos aplicados)

- `c2af9c86c95d_add_role_column_to_auth_users.py` (FASE 3.A.0, hallazgo original)
- `506c7a897689_create_admin_settings_table_singleton.py` (FASE 4 4.A.1, segunda confirmación)

Ambas migraciones aplican el mismo patrón: scout autogenerate → editar manualmente para scope mínimo → preservar evidence forense del drift descartado.

Negativas:
- +13-20h al estimado total S11 (de ~342-445h a ~355-465h, <5%)
- Riesgo intermedio FASE 4-12: si alguna fase necesita `alembic --autogenerate`, deberá usar el patrón de FASE 3.A.0 (manual minimalista) hasta que 11.5 resuelva

---

# ADR-017 — Coexistencia dual auth flow (admin cookie httpOnly · cliente Bearer localStorage)

**Fecha**: 2026-04-27
**Estado**: **RESOLVED Mini-Fase 3.5 (2026-04-28)** · ver `## Resolution` al final
**Decisor**: Marcos Mata García
**Referencias**: ADR-013 (separación 3 portales), ADR-015 (role identidad), ADR-018 (aceleración), ADR-019 (CSRF triple binding cliente), ADR-020 (sessions separadas), TODO-AUTH-UNIFY-001 (RESUELTO)

## Contexto

Durante el audit pre-SUB-FASE 3.E S11, al analizar `/client-portal/login/page.tsx` para implementar el redirect role-based, se descubrió que el sistema FULKRO tiene **dos flows de autenticación independientes** que coexisten:

### Admin flow (Marcos owner + futuros partner_senior/etc.)

- **Endpoint**: `POST /api/v1/auth/login` → mfa_ticket → `POST /api/v1/auth/{webauthn,totp}/verify`
- **MFA**: WebAuthn (Yubikey) **+** TOTP, obligatorio
- **JWT**: Ed25519 (EdDSA) firmado con `FULKRO_AUTH_PRIVATE_KEY`
- **Storage frontend**: cookie `fulkro_session` con flags `httpOnly + secure (prod) + samesite=strict + path=/`
- **Transport**: cookie automática del browser en cada request
- **Verificación frontend**: middleware Next.js (`frontend/middleware.ts`, FASE 3.C) verifica con `FULKRO_AUTH_PUBLIC_KEY` (jose.importSPKI EdDSA)
- **Sesión BD**: tabla `auth_sessions` con jti + 8h TTL
- **CSRF**: cookie `fulkro_csrf` (httpOnly=False, leída por JS) + header `X-CSRF-Token`

### Client portal flow (`client_user` y otros roles cliente)

- **Endpoint**: `POST /api/v1/client-auth/login` → `access_token` directo (sin MFA ticket separado, opcional `totp_code` en mismo body)
- **MFA**: TOTP opcional (flag `totp_enabled` en `ClientMeResponse`); WebAuthn NO implementado
- **JWT**: **MISMO Ed25519 + MISMA keypair `FULKRO_AUTH_PRIVATE_KEY`** que admin (`backend/app/motors/m21_portal_cliente/auth_service` reusa `issue_token` / `decode_token` de `backend/app/auth/crypto`)
- **Storage frontend**: `localStorage` con keys `fulkro_client_portal_{token,exp,role,name}` (`frontend/lib/client-portal-api.ts::storeSession`)
- **Transport**: header `Authorization: Bearer ${token}` en cada request (`clientApi`)
- **Verificación frontend**: NO cubierto por middleware Next.js; cada request `clientApi` recoge el token de localStorage y lo envía
- **Sesión BD**: tabla `client_sessions` con jti + token_hash + IP + UA + 12h TTL (modelo distinto a `auth_sessions`)
- **CSRF**: no aplica (token Bearer en header, no cookie)

### Por qué importa

1. **Middleware Next.js (FASE 3.C) solo protege admin/radar**: verifica cookie `fulkro_session`. Las rutas `/client-portal/*` están en lógica del middleware con check `role=client_user` pero leyendo la misma cookie — y el flow cliente NO setea esa cookie, sino que mete el token en localStorage. **Esto significa que el middleware actualmente NO puede validar sesiones cliente**, solo admin. La protección de `/client-portal/*` post-login depende del componente cliente leyendo localStorage + check del backend en cada request.

2. **Riesgo XSS específico del flow cliente**: token en localStorage es accesible por cualquier script JS que se ejecute en el dominio. Si en el futuro hubiera una vulnerabilidad XSS en el portal cliente (componente con `dangerouslySetInnerHTML` mal saneado, etc.), el token sería robable. Admin flow con cookie httpOnly NO tiene este riesgo.

3. **MFA inconsistente**: admin obligatorio TOTP+WebAuthn; cliente opcional TOTP-only. Política de seguridad asimétrica entre owners y clientes (en muchos casos cliente accede a información sensible: pliegos firmados, SDL, etc.).

4. **Carga cognitiva**: dos sistemas de auth a mantener, dos helpers de tests E2E, dos modelos BD (`auth_users` + `client_users`), dos servicios (`auth_service` + `m21_portal_cliente.auth_service`). Surface área para bugs y onboarding lentos.

## Decisión

**Para FASE 3 S11**: NO unificar. Razones:
- Refactor afecta motor M12 magic links + flows ya productivos (Marcos seed, clientes existentes en BD)
- Introducir cookie httpOnly para cliente requiere coordinar dominios (subdomain o path) y migración de sesiones activas
- Scope FASE 3 es middleware + AuthGuard + redirect — no auth refactor masivo

**Para FASE 6 (M29 Messaging cliente↔Marcos) o FASE 10 (Portal cliente expansion)**: UNIFICAR. Plan tentativo:

1. **Backend**: extender `/api/v1/auth/*` para soportar role `client_user` también (login con MFA opcional en mismo flow). Eliminar `/api/v1/client-auth/*` o convertirlo en alias deprecated.
2. **Cookie común**: `fulkro_session` válida para ambos roles. Misma JWT Ed25519 ya está; solo cambiar storage cliente de localStorage → cookie httpOnly via Set-Cookie response.
3. **Frontend**: eliminar `frontend/lib/client-portal-api.ts::storeSession + clientApi`. Reusar `frontend/lib/api.ts` común con cookie automática del browser. Middleware (FASE 3.C) ya cubre cookie; pasaría a proteger también `/client-portal/*` correctamente (lo que hoy solo hace por casualidad porque el redirect path falla si no hay cookie — pero un user con localStorage token y sin cookie pasaría el middleware solo porque `claims === null`, NO porque la auth real funcione).
4. **MFA**: extender flow cliente con TOTP obligatorio (opcional WebAuthn según UX).
5. **Migración**: invalidar sesiones cliente activas (token bumps via incremento de version), comunicar a clientes para re-login.

## Consequences (estado actual no-unificado)

Positivas:
- FASE 3 procede sin contaminación de scope (~10h ahorradas que se delegan a FASE 6/10)
- Admin flow robusto (MFA fuerte + httpOnly + Ed25519 + middleware) intacto
- Algoritmo JWT compartido (Ed25519 + misma keypair) significa que la unificación futura es más sencilla de lo que parecía: solo cambiar transport, no crypto

Negativas:
- Middleware FASE 3.C protege `/client-portal/*` solo por accidente (verificación cookie falla → redirect a login cliente). Si un cliente válido con localStorage pero sin cookie navega a `/client-portar/dashboard`, el middleware lo redirige a `/client-portal/login` aunque tenga token válido en localStorage → mala UX (re-login innecesario). **Mitigación temporal**: el portal cliente hace check de token en componente al cargar dashboard.
- Riesgo XSS específico del flow cliente (localStorage token-readable)
- MFA política asimétrica: clientes pueden quedar sin MFA si no opt-in TOTP
- Tests E2E necesitarán dos helpers de auth distintos en SUB-FASE 3.F (admin login full MFA flow vs client login email+password+TOTP optional)

## Bloqueante explícito

Antes de FASE 6 M29 Messaging cliente↔Marcos, la decisión de unificación auth debe estar tomada y planificada. NO es bloqueante de FASE 4 (Settings) ni FASE 5 (Usuarios) que solo tocan admin.

## Referencias técnicas

- Backend admin: `backend/app/auth/{api,service,crypto,dependencies}.py`
- Backend cliente: `backend/app/motors/m21_portal_cliente/{api,auth_service}.py` + `backend/app/models/client_portal.py`
- Frontend admin: `frontend/components/auth/{LoginForm,AuthGuard,PortalSwitcher}.tsx` + `frontend/middleware.ts`
- Frontend cliente: `frontend/app/client-portal/login/page.tsx` + `frontend/lib/client-portal-api.ts`

## Resolution (2026-04-28)

Mini-Fase 3.5 implementó la unificación auth en 12 commits a lo largo de la Sesión 11:

| BLOQUE | Hash | Subject |
|---|---|---|
| (prep) | b6a5b1d | docs(plan): ADR-018 + acelerar TODO-AUTH-UNIFY-001 a Mini-Fase 3.5 |
| 0 | a8aa2f1 | test(client-auth): tests característicos baseline pre-Mini-Fase 3.5 |
| 1 | d9230e3 | feat(client-auth): set-cookie httpOnly en endpoints client-auth |
| 2 | 64b8989 | feat(client-auth): verify_session dual auth cookie + Bearer |
| 3 | 0c9ad6a | docs(plan): BLOQUE 3 SKIPPED · cubierto por BLOQUEs 1+2 |
| 4 | 581242e | feat(client-auth): CSRF triple binding cliente · cookie + JWT claim + header |
| 5 | c48c146 | feat(client-portal): clientApi cookie + X-CSRF-Token sin localStorage |
| 6 | 075ac0f | docs(plan): BLOQUE 6 SKIPPED · cubierto por BLOQUE 5 |
| 7 | 33f78a9 | feat(auth): role claim cliente JWT + middleware/AuthGuard 8 roles reales |
| 8 | aa5510b | feat(client-auth): migración Alembic revoke sesiones cliente activas |
| 9 | 2a892b2 | docs(plan): BLOQUE 9 smoke cliente DONE · admin SKIPPED justificado |
| 10 | (este commit) | docs(plan): ADRs cierre + edge cases formalizados |

Tras la migración:
- Cliente usa cookie httpOnly `fulkro_session` automática (ya no localStorage)
- CSRF triple binding via `fulkro_csrf` cookie + `X-CSRF-Token` header + JWT claim (ver ADR-019)
- Tablas BD `auth_sessions` + `client_sessions` siguen separadas, cookie común con dispatcher dual (ver ADR-020)
- Middleware Next.js dispatcha por `claims.role` con `CLIENT_ROLES` set de 8 roles reales + `ADMIN_ROLE` owner
- 5/5 smoke tests cliente verde end-to-end (BLOQUE 9 commit `2a892b2`)
- Suite backend acotada: 81 passed (40 cliente + 41 admin); +5 vs baseline (1 cookie-only BLOQUE 2 + 4 CSRF BLOQUE 4)

ADRs derivados:
- **ADR-019** CSRF triple binding cliente — formaliza patrón JWT-bound + cookie + header
- **ADR-020** Tablas sessions separadas con cookie común — justifica dispatcher dual backend (`sub` prefix) + frontend (`role` semántico)

TODOs derivados (deuda formalizada explícita en `progress/backlog_formal.md`):
- **TODO-AUTH-CLIENT-BEARER-CLEANUP-001** [MEDIA · FASE 4]: retirar dual-auth Bearer de `verify_session` + eliminar `access_token` del `LoginResponse` Pydantic schema (backward-compat hoy innecesario, frontend usa cookie post-MF3.5; bloqueado por 3 tests baseline que asertan sobre el field)
- **TODO-DOCKER-RELOAD-001** [BAJA · FASE 13]: añadir backend service a `docker-compose.yml` con `--reload` en dev profile (estructural, evita "uvicorn stale" del BLOQUE 9)
- **LECCIÓN-OPS-001** [INFO · siempre aplicar]: verificar uvicorn start time vs HEAD timestamp antes de smoke tests

**Estado final**: dual auth flow original (admin cookie httpOnly + cliente Bearer localStorage) ELIMINADO. Hoy ambos roles usan cookie httpOnly + CSRF triple binding sobre la misma keypair Ed25519.

---

# ADR-018 — Aceleración auth unificado (Mini-Fase 3.5 S11) tras bug regresión middleware

**Fecha**: 2026-04-27
**Estado**: **IMPLEMENTED Mini-Fase 3.5 (2026-04-28)** · ver `## Resolution` al final
**Decisor**: Marcos Mata García
**Referencias**: ADR-017 (dual auth flow, RESOLVED), ADR-019 (CSRF cliente), ADR-020 (sessions separadas), TODO-AUTH-UNIFY-001 (RESUELTO)

## Contexto

Durante audit pre-SUB-FASE 3.F (PASO 0 — preparar router `/api/v1/_dev/*` para tests E2E), se descubrió que el middleware Next.js implementado en SUB-FASE 3.C (commit `8c2f163`) tiene un **bug regresión sobre flow cliente**:

- Cliente real autenticado tiene token JWT en `localStorage` (vía `clientApi.login`)
- Cliente NO setea cookie `fulkro_session` (la cookie es exclusiva del flow admin)
- Middleware Next.js verifica cookie `fulkro_session` para `/client-portal/*`
- Sin cookie → middleware redirige a `/client-portal/login`
- Cliente vuelve a `/client-portal/login` tras autenticar exitosamente → redirect loop infinito

**Resultado neto**: cliente real **no puede acceder a su dashboard** post-3.C. El smoke test del 3.C verificó `GET /client-portal/dashboard sin cookie → 307` y lo etiqueté como "esperado", asumiendo que cliente tendría cookie común (asunción del plan original que ADR-017 ya había contradicho). El smoke test no se re-evaluó tras descubrir el dual flow.

## Decisión

Aceleramos `TODO-AUTH-UNIFY-001` (originalmente programado para FASE 6 M29 Messaging o FASE 10 Portal cliente expansion) a una **Mini-Fase 3.5 dentro de la Sesión 11**, ejecutada en la próxima sesión, **antes de SUB-FASE 3.F**.

### Razones

1. **Requirement Marcos "cero deuda técnica"**: cualquier opción intermedia (fix B excepción middleware) deja deuda viva en producción.
2. **Bug requiere fix sí o sí**: cliente bloqueado de su dashboard NO es aceptable ni siquiera en dev/staging.
3. **Fix B parcial sería retrabajo**: la migración completa C reescribiría el código del fix B, así que invertir en B introduce deuda formalizada que descartamos a las pocas semanas.
4. **Audit scope honesto Claude Code**: 7.5h conservador (9h con edge cases), no los 8-12h genéricos del TODO inicial. Comparable a 3.B en complejidad (refactor cross-stack, sin merge tablas).
5. **0 tests existentes rotos**: ni backend ni frontend tienen tests que dependan del flow cliente actual. Sólo tests nuevos del 3.F afectados (positivamente — vuelven al plan v4.2 sin adaptaciones).
6. **3.F honesto post-Mini-Fase 3.5**: tests E2E pueden validar los 8 escenarios del plan original v4.2 sin descartes ni helpers simulados.

### Plan

Ver `TODO-AUTH-UNIFY-001` actualizado en `progress/backlog_formal.md` con desglose 9 bloques + horas reales por bloque.

Tras Mini-Fase 3.5:
1. SUB-FASE 3.F: 8 tests Playwright del plan v4.2 + 4-5 capturas baseline (~2h)
2. SUB-FASE 3.G: cierre + tag `s11-fase-3-cerrada` (15 min)

## Consequences

Positivas:

- **ADR-017 cerrado completamente** (no queda pendiente la dualidad)
- **TODO-AUTH-UNIFY-001 cerrado** (desbloquea FASE 6 M29 sin prerrequisito 8-12h pendiente)
- **3.F con tests honestos del plan v4.2** (sin descarte 3/4/7 ni helpers simulados)
- **Sesión 12 deploy con flow auth único** (un solo modelo cookie httpOnly + Ed25519)
- **Mini-Sesión 11.5 simplificada** (queda solo el drift BD del ADR-016, sin auth)
- **Defensa server-side completa** para `/client-portal/*` (cookie httpOnly elimina riesgo XSS-leak token de localStorage)

Negativas:

- **+7.5h sobre estimado FASE 3** original (~13h FASE 3 → ~20.5h con Mini-Fase 3.5)
- **Cliente bloqueado en dev hasta Mini-Fase 3.5** (<72h estimado retake): aceptable porque (a) único user dev relevante es Marcos, (b) los 7 `client_users` reales en BD son fixtures de testing, (c) ningún cliente real depende del repo dev actual

## Bug regresión 3.C — análisis técnico

**Causa raíz**: el plan v4.2 original asumía cookie común admin+cliente con HS256 simétrico (`SESSION_SECRET`). Durante 3.C descubrí que backend usaba EdDSA Ed25519 asimétrico, pero NO re-evalué la asunción de cookie común cuando documenté ADR-017 (dual flow). El middleware quedó implementado con la asunción original "todo el tráfico autenticado tiene cookie".

**Smoke test que falló en detectarlo**: `GET /client-portal/dashboard sin cookie → 307 → /client-portal/login?next=...` lo etiqueté como "esperado" sin re-evaluar contra el flow cliente real (que sí está autenticado, solo que en localStorage, no en cookie).

**Lección operacional**: smoke tests E2E deben ejecutarse SIEMPRE con flow cliente real autenticado (no solo "sin cookie"), incluso si parece redundante. La cobertura del flow real es el única que detecta este tipo de bug arquitectónico.

## Bloqueante explícito

Mini-Fase 3.5 es prerrequisito de SUB-FASE 3.F. NO arrancar 3.F sin haber completado la migración auth unificada.

## Referencias

- Bug descubierto: audit pre-SUB-FASE 3.F PASO 0 (commit pendiente hash docs(plan))
- Plan resolución: `TODO-AUTH-UNIFY-001` en `progress/backlog_formal.md`
- ADR-017 contexto dual flow original: secciones "Por qué importa" + "Consequences"

## Resolution (2026-04-28)

Mini-Fase 3.5 ejecutada exitosamente en Sesión 11 antes de SUB-FASE 3.F, según plan. El bug regresión 3.C cliente quedó cerrado por BLOQUE 7 (commit `33f78a9`): JWT cliente ahora incluye claim `role`, y el middleware Next.js dispatcha correctamente por `claims.role` con set `CLIENT_ROLES` de 8 roles reales (lectura_solo, rseg, director_ti, gerente, direccion, it_operativo, responsable_informacion, custom). Adicionalmente:

- **Cierre regresión client-side**: `AuthGuard.tsx` también tenía la misma regresión `claims.role !== "client_user"` (literal nunca presente en JWT). BLOQUE 7 lo refactorizó a helpers `isAdminRole`/`isClientRole` shared en `frontend/lib/auth/roles.ts`. Cierre end-to-end de la regresión (middleware server-side + AuthGuard client-side coherentes con los mismos helpers).
- **Validación empírica**: BLOQUE 9 smoke test cliente real (TOTP enrolado) confirmó que un cliente con role `rseg` puede acceder a `/client-portal/dashboard` sin redirect loop. Triple binding CSRF verificado bilateralmente (POST sin header → 403; con header → 200; JWT claim coincide carácter por carácter con cookie).
- **Tests baseline**: a8aa2f1 (BLOQUE 0) creó tests característicos antes de tocar código, garantizando que la migración no rompiera comportamientos existentes. Suite final: 81 passed (40 cliente + 41 admin), 0 regresiones.
- **Tests nuevos legitimando**: 4 tests CSRF añadidos en BLOQUE 4 (`test_auth_baseline.py::TestCSRF*`) prueban directamente el binding triple. 1 test cookie-only en BLOQUE 2 prueba dual auth cookie + Bearer.

Bloqueante de SUB-FASE 3.F levantado. Tests E2E Playwright pueden proceder con el plan v4.2 sin helpers simulados ni descartes de escenarios.

Lección operacional (incluida en backlog como `LECCIÓN-OPS-001`): el smoke test inicial del BLOQUE 9 dio falso éxito porque el uvicorn dev llevaba 5 días corriendo sin `--reload`, anterior a los cambios MF3.5. Restart manual reveló el bug real (cookies no seteadas en response, JWT sin claims `csrf`/`role`). En futuras refactorizaciones backend, verificar el start time del proceso vs el HEAD git ANTES de smoke tests.

**Estado final**: bug regresión 3.C cerrado, Mini-Fase 3.5 implementada, ADR-017 RESOLVED. ADR-018 cumple su propósito (acelerar la unificación a S11) y se cierra como IMPLEMENTED.

---

# ADR-019 — CSRF triple binding cliente

**Fecha**: 2026-04-28
**Estado**: Aprobado · **Implementation**: Mini-Fase 3.5 BLOQUE 4 (commit `581242e`), validación empírica BLOQUE 9 (commit `2a892b2`)
**Decisor**: Marcos Mata García
**Referencias**: ADR-013 (separación 3 portales), ADR-017 (dual auth flow, RESOLVED), ADR-018 (aceleración Mini-Fase 3.5)

## Contexto

La migración del flow cliente a cookie httpOnly automática (Mini-Fase 3.5 BLOQUE 1) introduce vulnerabilidad CSRF que el flow Bearer-token previo NO tenía. Un atacante con `victim.com` puede incluir `<form action="https://fulkro.es/api/v1/client-auth/...">` y disparar mutating requests con la cookie de sesión que el browser adjunta automáticamente. Bearer no era CSRF-vulnerable porque el header `Authorization` no se envía cross-origin por defecto.

El admin flow ya tenía mitigación CSRF establecida (cookie `fulkro_csrf` no httpOnly + header `X-CSRF-Token`, validado en `backend/app/auth/dependencies.py`). El cliente no tenía nada equivalente porque no necesitaba mitigación pre-cookie.

## Decisión

Replicar el patrón admin con un refinamiento: **JWT-bound triple binding**. Tres anclas que deben coincidir en métodos mutantes (POST, PUT, DELETE, PATCH):

1. **Cookie `fulkro_csrf`** — no httpOnly, frontend JS la lee
2. **Header `X-CSRF-Token`** — frontend la envía explícita en cada mutating request
3. **JWT claim `csrf`** — embebido en el session token, firmado por backend

Validación en `get_current_client_user` (`backend/app/motors/m21_portal_cliente/api.py`):
- Si method ∈ `SAFE_METHODS` (constante `{GET, HEAD, OPTIONS}` definida en `backend/app/motors/m21_portal_cliente/api.py`, replicando el mismo set de `backend/app/auth/dependencies.py`): pasa sin CSRF (idempotentes)
- En otro caso: `header == cookie == JWT_claim_csrf` con `crypto.constant_time_eq` (timing-attack safe). Cualquier mismatch → 403 `csrf token mismatch`.

Implementación:
- `secrets.token_urlsafe(32)` generación en `auth_service.login`
- `crypto.issue_token` recibe `csrf_token` (BLOQUE 4) que internamente lo embebe como claim
- Set-Cookie en login + endpoints que renuevan sesión (totp/verify)

## Comparación con alternativas

**vs (a) Double-submit cookie puro** (header == cookie, sin JWT claim): añade el JWT claim como tercer ancla. Atacante con CSRF puro NO puede falsificar el JWT claim porque requiere la private key Ed25519. Defensa en profundidad real, no solo cosmética.

**vs (b) BD stateful** (lookup tabla `csrf_tokens` por request): sin overhead de query DB en cada mutating request. Mejor performance bajo carga.

## Consequences

Positivas:
- Mitiga CSRF en cliente (vulnerabilidad introducida por la migración cookie en BLOQUE 1)
- Coherencia con admin: un único patrón mental, un único set de helpers, un único punto de mantenimiento
- Stateless: sin queries BD adicionales
- **Validación empírica BLOQUE 9 smoke test (commit `2a892b2`)**: POST `/client-auth/logout` sin `X-CSRF-Token` → HTTP 403 `{"detail":"csrf token mismatch"}`; mismo POST con header válido → HTTP 200 `{"logged_out":true}` + Set-Cookie clearing ambas cookies. JWT claim `csrf` decodificado coincide carácter por carácter con el valor de la cookie `fulkro_csrf` (`lBRHHdkKvT9qWrywbzuLAPkkhFGY46LAlfH985XnCdw` en la sesión observada).

Negativas:
- Frontend JS debe leer cookie + enviar header en cada mutating call (mitigación: `clientApi` wrapper lo automatiza, BLOQUE 5)
- JWT payload ~30 bytes mayor (csrf token embebido)

## Bonus arquitectónico — DRY frontend

Helper `getCsrfToken` extraído a `frontend/lib/csrf.ts` durante BLOQUE 5. Tanto `frontend/lib/api.ts` (admin) como `frontend/lib/client-portal-api.ts` (cliente) lo importan. Si backend cambia el nombre de la cookie CSRF, una única edición. Single source of truth.

## Referencias técnicas

- Backend: `backend/app/motors/m21_portal_cliente/{api,auth_service}.py`
- Backend admin (referencia patrón): `backend/app/auth/dependencies.py`
- Frontend: `frontend/lib/csrf.ts`, `frontend/lib/api.ts`, `frontend/lib/client-portal-api.ts`
- Tests: `backend/tests/motors/m21_portal_cliente/test_auth_baseline.py` (4 tests CSRF + 1 cookie-only)

---

# ADR-020 — Tablas auth_sessions vs client_sessions separadas (cookie común)

**Fecha**: 2026-04-28
**Estado**: Aprobado · **Implementation**: Mini-Fase 3.5 BLOQUEs 1-7
**Decisor**: Marcos Mata García
**Referencias**: ADR-013 (separación 3 portales), ADR-017 (dual auth flow original, RESOLVED), ADR-019 (CSRF triple binding cliente)

## Contexto

Audit pre-Mini-Fase 3.5 reveló que las tablas `auth_sessions` (admin) y `client_sessions` (cliente) tienen schemas divergentes:

| Campo | `auth_sessions` | `client_sessions` |
|---|---|---|
| FK | `auth_users(id)` ON DELETE CASCADE | `client_users(id)` (sin CASCADE) |
| `jti` | varchar(64) | varchar(100) |
| `jwt_token_hash` | NO existe | varchar(64) |
| `last_activity` | NO existe | timestamptz |
| `ip_address` | varchar | inet |
| TTL nominal | 8h | 12h |

La tentación natural durante Mini-Fase 3.5 era unificar bajo un schema común. Esta decisión documenta por qué NO se hizo.

## Decisión

Mantener las dos tablas separadas. Compartir solamente la **cookie de transporte** (`fulkro_session`) y la **infraestructura JWT** (keypair Ed25519 común).

### Cómo funciona la cookie común

- Misma keypair Ed25519 (`FULKRO_AUTH_PRIVATE_KEY`) para firmar ambos tipos de session
- Mismo `crypto.issue_token` / `crypto.decode_token` (sin fork)
- Misma cookie name (`fulkro_session`, httpOnly)

### Dual dispatcher (backend vs frontend)

El sistema usa **dos dispatchers en momentos distintos del flow**, con criterios distintos. No es un bug ni una redundancia: cada dispatcher resuelve un problema arquitectónicamente diferente.

**1. Backend post-`decode_token`** (resuelve "¿qué tabla BD consulto?"):
- Criterio: `claims["sub"].startswith("client:")` → tabla `client_sessions`; else → `auth_sessions`
- Cuándo: dentro de `verify_session`, tras validar firma JWT y antes de resolver revocation/last_activity
- Por qué `sub` y no `role`: el prefijo `client:` se grabó en `issue_token` desde el día 1 del motor M21 (ADR-013 separación 3 portales). El claim `role` solo se añadió en BLOQUE 7 (commit `33f78a9`). Migrar a `role` rompería sesiones legacy emitidas pre-BLOQUE 7 que aún están en BD (revocadas por BLOQUE 8 pero los hashes históricos persisten para forensia ENS).

**2. Frontend middleware Next.js** (resuelve "¿qué portal puede ver este usuario?"):
- Criterio: `isAdminRole(claims.role)` (admin) vs `isClientRole(claims.role)` (cliente). Helpers viven en `frontend/lib/auth/roles.ts` (BLOQUE 7).
- Cuándo: en cada request HTTP, ANTES de resolver la página, sin acceso a BD
- Por qué `role` y no `sub`: middleware no consulta BD; necesita decisión semántica de autorización (qué portal corresponde) puramente desde claims firmados. `sub` es structural (storage routing), `role` es semántico (authorization). Roles distintos para problemas distintos.

Frontend middleware no podría usar `sub.startswith("client:")` porque no establece autorización semántica (un cliente con role retirado seguiría teniendo `sub:"client:..."` pero no debería entrar). Backend no podría usar `role` solo, porque sesiones legacy emitidas sin claim role lo verían como `undefined` y caerían fuera del dispatcher.

## Razones para no unificar las tablas

1. **Schemas divergen por features distintos**: cliente trackea `last_activity` para session timeout UI ("tu sesión expirará en X minutos"); admin no lo necesita. Cliente almacena `jwt_token_hash` para revocation lookup defensivo; admin solo confía en `jti`. Unificar requiere o (a) eliminar columnas cliente (rompe revocation tracking), o (b) añadirlas a admin (storage waste sin uso).
2. **TTL distinto**: 8h admin (sesión laboral típica) vs 12h cliente (acceso esporádico al portal entre reuniones). Acoplar TTL en columna común sería un downgrade de UX.
3. **CASCADE divergente intencional**: borrar un `auth_user` cascada sus sesiones (admin Marcos = eliminación destructiva total). Borrar un `client_user` lo marca soft-deleted (`deleted_at`) sin CASCADE — auditoría preservada para compliance ENS.
4. **Migración no destructiva**: las dos tablas ya existen pobladas en BD dev/prod. Unificar requeriría migración con downtime y riesgo alto de pérdida de datos.

## Consequences

Positivas:
- Schemas optimizados por contexto operacional real
- Cookie común simplifica frontend (un único middleware Next.js)
- BLOQUEs 1-7 ejecutados en 7.5h reales sin riesgo de migración destructiva
- Suite tests (40 cliente + 41 admin = 81 total) verde sin acoplamiento

Negativas:
- Doble lookup BD: tras `decode_token`, el código backend debe saber a qué tabla mirar (resuelto via dispatcher por `sub` prefix)
- Conocimiento arquitectónico sutil (cookie común + tablas separadas + dual dispatcher) requiere documentación explícita — propósito de este ADR

## Sub-óptimo formalizado

En unificación futura (FASE 14+ o post-S11), podríamos considerar consolidar bajo schema común con columnas opcionales por tipo (`subject_type ENUM('admin','client')`). Hoy el coste de la migración no justifica el retorno marginal en simplicidad de código.

## Referencias técnicas

- Tabla admin: `backend/app/models/auth.py::Session`
- Tabla cliente: `backend/app/models/client_portal.py::ClientSession`
- Dispatcher backend: `verify_session` en `backend/app/motors/m21_portal_cliente/auth_service.py`
- Dispatcher frontend: `frontend/middleware.ts` + `frontend/lib/auth/roles.ts`

---

# ADR-021: Motors Auth Landing via FastAPI Global Dependency

**Status**: Accepted 2026-04-29 · sub-fase 4.D Sesión 11
**Related**: ADR-013 (separación 3 portales), ADR-015 (role vs capability), ADR-019 (CSRF triple binding), ADR-020 (sessions separadas)

## Context

Hallazgo audit pre-FASE 5 (TODO-A.3 sub-bloque, 2026-04-29) reveló **gap arquitectónico crítico H14+H15**: 262/284 endpoints mutating (92.3%) sin autenticación. El sistema fue diseñado con auth chain (ADRs 013/015/020 + `auth/dependencies.py` + JWT Ed25519 + dispatcher dual auth_sessions/client_sessions), pero **el cableado no se aplicó a los motors**. Solo `auth/api.py` (12 endpoints login flow) y `admin_settings/api.py` (10 endpoints, FASE 4 4.A.2.c) usan `Depends(get_current_user)` o role guards.

Implicaciones del gap:
- Trazabilidad ENS RD 311/2022 estructuralmente imposible (Anexo III §4.4 — registro de actividad debe identificar al usuario o servicio responsable)
- `audit_log.usuario` NULL en mutaciones motor (71 entries históricos S1-S10, ver `docs/audits/audit_log_history.md`)
- Vulnerabilidad de seguridad: cualquier request al backend (sin frontend middleware MF3.5 BLOQUE 7 interpuesto) muta BD sin verificar identidad

Audit pre-4.D cazó 5 hallazgos (H20-H24) que refinaron la propuesta inicialmente formulada como "ASGI middleware" en `TODO-MOTORS-AUTH-LANDING-001`.

## Decision

Implementar autenticación + CSRF + `set_config('app.current_user')` wiring como **FastAPI global dependency** (no ASGI middleware puro).

```python
app = FastAPI(
    title="FULKRO",
    dependencies=[Depends(authenticate_request)],
    ...
)
```

### Componentes

1. **`backend/app/auth/global_dep.py::authenticate_request`** (new): global dep que para cada request:
   - Bypassa whitelist paths (8 exact + 5 prefix)
   - Lookup cookie `fulkro_session`
   - Decode JWT Ed25519 (mismo formato ambos pools)
   - Dispatcher dual: peek `payload.sub.startswith("client:")` → routing al pool correcto (`auth_sessions` Marcos vs `client_sessions` cliente)
   - CSRF triple binding (`verify_csrf` helper, mutating methods)
   - `set_config('app.current_user', email, true)` para que `fn_audit_track` triggers populen `audit_log.usuario`
   - Stora `request.state.auth_subject` (wrapper user + role_pool) para downstream dependencies
   - Compatibilidad: stora también `request.state.auth_payload` (pre-4.D `/auth/logout` lo lee para extraer jti)

2. **`backend/app/auth/csrf.py::verify_csrf`** (new): helper centralizado triple binding (header == cookie == payload.csrf via `crypto.constant_time_eq`). Extracto de refactor inline antes presente duplicado en `auth/dependencies.py` + `m21_portal_cliente/api.py`. Constants `SESSION_COOKIE`, `CSRF_COOKIE`, `CSRF_HEADER`, `SAFE_METHODS` definidas aquí; `dependencies.py` re-exporta para backward-compat call sites (e.g. `auth/api.py::login` set-cookie helpers).

3. **`backend/app/auth/dependencies.py`**: refactor masivo (-60 LOC lógica activa). `require_owner`, `require_client_user`, `require_ens_radar_owner` ahora son **puro role check** sobre `request.state.auth_subject` ya inyectado por el global dep. `get_current_user` simplificado a state lookup (Opción C compatibility — preserva `CurrentUser = Annotated[User, Depends(get_current_user)]` contract).

4. **`backend/tests/conftest.py`** (+58 LOC): fixture `auth_override_default` autouse que `dependency_override` `authenticate_request` retornando `AuthSubject` Marcos stub. Tests con marker `pytest.mark.real_auth` opt-out (5 files críticos: `admin_settings/test_logo_upload`, `auth/test_role_based_auth`, `auth/test_auth_api`, `m21_portal_cliente/test_auth_baseline`, `m21_portal_cliente/test_portal_cliente_paso3`).

## Why FastAPI Global Dependency, NOT ASGI Middleware

ASGI middleware corre **antes del Depends graph**. La sesión DB que un middleware crearía vía `engine.connect()` es **distinta** de la sesión que `Depends(get_db)` provee al endpoint handler. `set_config(..., true)` es local-to-transaction (Postgres semantics) → el setting se perdería entre la transaction del middleware y la del endpoint. Los triggers `fn_audit_track` que se disparan al hacer INSERT/UPDATE en el endpoint leerían `current_setting('app.current_user', true)` y obtendrían NULL.

Global dependency, en cambio, comparte la sesión DB via Depends chain (FastAPI cachea `Depends(get_db)` per-request). El global dep recibe `db: AsyncSession = Depends(get_db)` y aplica `set_config` en esa misma sesión que el endpoint usará. Triggers leen el setting correctamente.

Pattern idiomático FastAPI, composable con `dependency_override` para tests.

## Why CSRF Unified in Global Dep

CSRF triple binding antes embebido inline duplicado en 2 deps (`auth/dependencies.py` + `m21_portal_cliente/api.py`). Centralización en `csrf.py::verify_csrf` evita duplicación + motors heredan CSRF protection automático sin esfuerzo per-motor. Refactor pequeño (~30 min) gran beneficio arquitectónico.

## Whitelist Paths

Bypassan auth (paths públicos legítimos validados empíricamente en audit pre-4.D):

**Exact** (8):
- `/api/v1/auth/login`, `/api/v1/auth/webauthn/verify`, `/api/v1/auth/totp/verify`
- `/api/v1/client-auth/login`
- `/api/v1/health`
- `/openapi.json`, `/docs`, `/redoc`

**Prefix** (5):
- `/api/v1/public/*` (m08 verification public portals — token-based, no session cookie)
- `/api/v1/_dev/*` (gated `is_production=False`, defensa redundante per-endpoint)
- `/api/v1/magic-links/consume/*` (m12 public consume — token-based)
- `/docs/*`, `/redoc/*` (Swagger/ReDoc assets)

Definidas en `backend/app/auth/global_dep.py::WHITELIST_EXACT` y `WHITELIST_PREFIX`.

## Consequences

### Positive

- **Cobertura 100% endpoints automática**: 262 motors + 22 auth/admin = 284 total
- Motors futuros heredan auth + CSRF + audit_user wiring sin esfuerzo per-motor
- Reducción duplicación deps existing (-60 LOC lógica activa duplicada)
- `audit_log.usuario` poblado en TODA request autenticada (resuelve vector motor de `TODO-AUDIT-USER-BACKFILL-001`)
- Pattern idiomático FastAPI (composable, testeable via `dependency_override`)
- Validación empírica completa (smoke 4.D.6: 7/7 PASS):
  - GET `/api/v1/clients` sin cookie → 401 (gap H14+H15 cerrado)
  - POST `/api/v1/clients` con cookie + CSRF → 201 + `audit_log.usuario = marcos@fulkro.es`

### Negative

- 49 motor tests (91% suite HTTP) dependen `auth_override_default` fixture autouse. No validan auth real → `H17` anti-pattern parcial persiste. Resolución completa diferida a `TODO-TESTS-AUTH-COVERAGE-001` [BAJA · post-deploy ampliable].
- `get_current_user` cambia internals (compatibility preserved via Opción C: lookup state.auth_subject). Test legacy `test_require_client_user_blocks_owner` actualizado a nueva signature (mock Request con AuthSubject).
- Doble decodificación JWT en pool cliente (`authenticate_request` peek + `auth_service_cliente.verify_session` decodifica internamente). Coste ~40μs/request, aceptable MVP. Refactor `verify_session` para aceptar payload pre-decoded documentado como future optimization.
- 4 constants (`SESSION_COOKIE`, `CSRF_COOKIE`, `CSRF_HEADER`, `SAFE_METHODS`) ahora definidas en `csrf.py` y re-exportadas desde `dependencies.py` para backward-compat. Ligera duplicación de import path; pattern aceptable.

## References

- TODO sucesor RESOLVED: `TODO-MOTORS-AUTH-LANDING-001` (BLOQUEANTE deploy producción) → resuelto sub-fase 4.D
- TODO actualizado: `TODO-AUDIT-USER-BACKFILL-001` (vector motor cubierto, era PARTIAL → ahora cobertura uniforme via `set_config` global)
- TODO nuevo: `TODO-TESTS-AUTH-COVERAGE-001` [BAJA · post-deploy] — resolución H17 anti-pattern (49 motor tests sin auth real coverage)
- LECCIÓN-OPS-003: validar premisas TODOs con grep empírico antes de implementación
- Docs auditor ENS: `docs/audits/audit_log_history.md` (política B+ preservar inmutabilidad + documentar)
- Hallazgos audit-first cazados durante sub-fase 4.D: H14, H15, H16, H17, H18, H19, H20, H21, H22, H23, H24, H26, H27, H28, H29, H30
- Esfuerzo real implementación: ~6h (vs 10-17h estimado plan original, audit-first reducción ~60% por pattern global dep + Opción C tests fix)

---

# ADR-022: Panel Admin Clientes /admin/clients

**Status**: Accepted 2026-04-29 · FASE 5 Sesión 11
**Related**: ADR-021 (motors auth landing), ADR-013 (separación 3 portales), ADR-019 (CSRF)

## Context

FASE 5 plan v4.2 requiere panel completo gestión clientes para Marcos: listado, wizard crear, detalle con 7 tabs, suspend/resume, audit log filter, facturas agregadas. Greenfield 100% UI; backend ~50% reuse (5 endpoints existing) + 6 endpoints nuevos.

Audit pre-FASE 5 cazó 7 hallazgos arquitectónicos (H1-H7) + 5 nuevos durante implementación 5.A (H31-H35) + 5 más durante 5.B (H36-H40) + 3 durante 5.C (H41-H43).

## Decision

### Backend (sub-fase 5.A)

1. **Path `/api/v1/clients/*`** mantener convención existing (NO `/api/v1/admin/clients` como plan v4.2 propuso). El prefix `/admin/` del plan era etiqueta organizacional, no path real. Los endpoints existing en `core/clients/api.py` cubren CRUD básico.

2. **Suspend reuse `SoftDeleteMixin.deleted_at`** en lugar de añadir field nuevo. Trade-off colission semántica con "delete real" aceptable para MVP. Sin migración nueva.

3. **Endpoint agregado `GET /api/v1/billing/clients/{id}/invoices`** (m15 sub-fase 5.A): retorna invoices + project_name JOIN cross-project. Evita N+1 que tendría el frontend si listase projects e iterase invoices por cada uno (decisión H4 audit pre-FASE 5).

4. **Router-level `Depends(require_owner)`** aplicado a `core/clients/api.py` (10 endpoints) + `m21_portal_cliente/api.py::cockpit_router` (7 endpoints). Cierra vulnerabilidad H32 (cliente autenticado podría escalate y crear/borrar usuarios en su propio cliente). Coherente con global dep ADR-021 (auth) + role check específico.

5. **5 endpoints nuevos** en `core/clients/api.py`: GET `/{id}` detalle (con métricas agregadas projects_count/users_count/last_activity_at), PATCH `/{id}` partial update, POST `/{id}/suspend`, POST `/{id}/resume`, GET `/{id}/audit` paginated filter.

### Frontend (sub-fase 5.B)

6. **3 rutas en `app/(admin)/admin/clients/`**:
   - `page.tsx` listado con DataTable + filter chips (Todos/Activos/Suspendidos) + dropdown actions
   - `new/page.tsx` wizard 3 pasos (datos cliente → primer usuario → confirmación)
   - `[id]/page.tsx` detalle con 7 tabs

7. **7 tabs detalle**:
   - **5 funcionales**: Datos (RHF+zod editable), Usuarios (cockpit DataTable + actions), Proyectos (DataTable), Facturas (DataTable cross-project), Audit Log (DataTable paginado + hash chain badges)
   - **2 placeholders**: Mensajes (M29 lazy load FASE 6), Contactos (M30 lazy load FASE 5.5)

8. **Stepper genérico custom** en `components/ui/stepper.tsx` (~90 LOC Tailwind puro, sin librería externa). Mapeo task-by-task validado con audit pre-FASE 5: shadcn/ui repo cubre 85% necesidades, gap solo Stepper.

9. **SuspendDialog type-to-confirm** usando `Dialog` Radix (NO `AlertDialog` que NO existe en el repo, hallazgo H40 audit). Pattern: button "Suspender" disabled hasta que input matche literalmente la razón social del cliente. Resume es action directa sin confirm (no destructive).

10. **Wizard reuse `cockpit_create_user(send_magic_link=true)`**: el endpoint existing m21 ya implementa POST + email invite via EmailSender + magic link `PRIMER_ACCESO_CLIENTE`. Wizard 5.21 plan v4.2 NO requiere backend nuevo, solo frontend (hallazgo H35 audit).

### E2E (sub-fase 5.C)

11. **5 tests Playwright `admin-clients.spec.ts`** pattern post-MF3.5: `loginAsMarcos(context)` + `page.route` mocks. Cobertura: listado, wizard 3 pasos, detalle 7 tabs, Datos edit, SuspendDialog gating.

12. **Mock order matters** (hallazgo H43): Playwright `page.route` matchea LIFO. Mocks genéricos (e.g. `**/api/v1/clients` listado) deben registrarse PRIMERO para que mocks específicos (e.g. `/api/v1/clients/{id}` detalle) prevalezcan. Cambio glob → regex en stub genérico evita choque.

## Why /clients (no /admin/clients)

Plan v4.2 propuso `/admin/clients/*` para diferenciar de `/clients` legacy "no auth, dev only". Pero post-4.D global dep cubre auth uniformemente; el comentario "no auth, dev only" en `core/clients/api.py:74` quedó stale (cleanup H34 sub-fase 5.A). Mantener path `/clients` evita refactor de ROUTES/Sidebar/tests existentes (H36 audit). Frontend route `/admin/clients` (UI) consume backend `/api/v1/clients` (API) — pattern coherente con `/admin/dashboard` consumiendo `/api/v1/leads` etc.

## Why Suspend Reuse deleted_at

Alternativas evaluadas:
- (A) Field nuevo `is_active: bool` + migración → simple pero requiere update al insertar todos los clientes existing
- (B) Field nuevo `suspended_at: datetime | None` + migración → más explícito pero idem (A)
- (C) Reuse `SoftDeleteMixin.deleted_at` → cero migración, semántica "soft delete" engloba suspend

**(C) elegida**: MVP cero costo, audit_log preserva timestamp suspend exacto vía trigger, resume = SET NULL idempotente. Trade-off: si en futuro quisiéramos "hard delete" real distinto de "suspend", tendríamos colisión. Decisión revisable en post-MVP.

## Why 7 Tabs (vs 5)

Plan v4.2 propuso 5 tabs. Sub-fase 5.B implementación añadió 2 placeholders dentro del mismo layout para mantener consistencia visual y pattern lazy-load. Marcos puede ver el shape final del panel hoy (incluyendo tabs futuros) sin necesidad de re-organizar layout en FASE 5.5/6 cuando M30/M29 landen.

## Consequences

### Positive

- **Cobertura completa CRUD admin clientes** (post-4.D global dep base auth-correcta)
- Endpoint agregado m15 evita N+1 frontend (Tab Facturas performance OK desde día 1)
- **H32 vulnerabilidad privilege escalation cerrada** (cockpit RBAC require_owner)
- Stepper genérico reusable para wizards futuros
- 5 tests Playwright cobertura E2E flujos críticos
- Wizard reuse cockpit_create_user → 0 backend nuevo para email invite

### Negative

- 2 tabs placeholder (Mensajes M29 + Contactos M30) crean expectativa visual sin funcionalidad real. Acceptable porque están claramente marcados como "lazy load FASE X".
- Suspend reuse `deleted_at` puede causar confusión semántica si en futuro hay "hard delete" real (decisión revisable post-MVP).
- `core/clients/api.py:74` comment stale "No auth, no RLS — Development only" cleanup oportuno H34 (commit 5.A).
- TODO-RBAC-PER-ENDPOINT-001 [MEDIA] formalizado: otros motors mutating Marcos-only sin require_owner explícito quedan pendientes (~3-5h dedicado post-FASE 5).

## References

- Sub-fase 5.A backend commit: `a97f514` (6 endpoints nuevos + H32 RBAC fix + 7 tests baseline)
- Sub-fase 5.B frontend commit: `3b1853c` (3 rutas + 7 tabs + wizard + SuspendDialog)
- Sub-fase 5.C E2E commit: `dabf359` (5 Playwright tests + Next 14 params API fix)
- Hallazgos audit-first cazados durante FASE 5: H1, H2, H3, H4, H5, H6, H7, H31, H32, H33, H34, H35, H36, H37, H38, H39, H40, H41, H42, H43
- TODO formalizado: `TODO-RBAC-PER-ENDPOINT-001` [MEDIA · post-FASE 5]
- Esfuerzo real FASE 5: ~9h (vs 8-10h plan v4.2)

---

# ADR-023 — Dominio compartido m27 Conformity ↔ m28 Change Governance

**Status**: Accepted 2026-04-29 sub-fase 5.5.F.0.H

## Context

Durante audit pre-fix `TODO-COMMIT-PATTERN-001` (sub-fase 5.5.F.0) se identificaron 17 motors backend con dicts in-memory sin persistencia DB. Tras refactor batch B/C/D (143 endpoints), m27 Conformity y m28 Change Governance quedaron como casos especiales: ambos contenían dicts in-memory para state machines, ambos tenían modelos DB parciales pre-S11.

Sub-fase 5.5.F.0.G refactor m27 reusó las 13 tablas `conformity_lifecycle` existing pre-S11 + nueva `conformity_state_snapshots` (polimórfica route_history + external_export). Al planificar refactor m28 (sub-fase 5.5.F.0.H), surgió pregunta arquitectónica:

**¿m28 debe tener tablas dedicadas para `_RECATEGORIZATIONS` y `_EXTRAORDINARY_AUDITS`, o reusar las que ya existen en m27 (`recategorizations`, `extraordinary_audits`)?**

Las tablas m27.recategorizations y m27.extraordinary_audits están diseñadas para representar exactamente las mismas entidades que los dicts m28 quieren persistir:

- `recategorizations`: cambio de categoría ENS BÁSICA→MEDIA→ALTA con análisis técnico + DDA nueva.
- `extraordinary_audits`: auditoría fuera del ciclo bianual normal disparada por cambio material.

m28 motor "Change Governance" trata cambios materiales que potencialmente disparan recategorizations o auditorías extraordinarias. m27 motor "Conformity Lifecycle" trata el ciclo formal completo (rutas, declaraciones, submissions, renewals + recategorizations + audits).

Ambos motors operan sobre el **mismo dominio funcional**: gestión del ciclo de vida ENS post-certificación.

## Decision

**m28 reusa cross-motor las tablas m27.recategorizations y m27.extraordinary_audits** en lugar de duplicar tablas dedicadas.

Mapping específico m28 → DB:
- `_CHANGES` → tabla `changes` (operations.py existing) extendida con columna `metadata_jsonb` (sub-fase 5.5.F.0.H migración `b2c3d4e5f6a7`).
- `_TOPOLOGIES` → tabla nueva `change_topologies` (DEDICADA m28, semántica única no compartida con m27).
- `_RECATEGORIZATIONS` → tabla `recategorizations` (m27.conformity_lifecycle, **CROSS-MOTOR**).
- `_EXTRAORDINARY_AUDITS` → tabla `extraordinary_audits` (m27.conformity_lifecycle, **CROSS-MOTOR**).

m28 services (`recategorization_service.py`, `extraordinary_audit_service.py`) calculan la lógica negocio (workflow steps, deadline policies) en stateless mode. m28 endpoints invocan esos services + persisten resultado en tablas m27 vía SQLAlchemy.

## Consequences

### Positive

- **Single source truth dominio compartido** — un proyecto tiene UNA lista de recategorizations y UNA lista de extraordinary audits, accesibles tanto desde m27 (vista lifecycle holístico) como desde m28 (vista governance change-driven).
- **Evita inconsistencias datos duplicados** — sin riesgo de tener `recategorization_id_in_m28` ≠ `recategorization_id_in_m27` para el mismo evento real.
- **Reduce schema bloat** — 0 tablas duplicadas, mantiene baseline 13 tablas conformity_lifecycle limpias.
- **Migraciones future-proof** — cualquier extensión schema (e.g. añadir campo a recategorizations) se aplica una sola vez.

### Negative

- **Acoplamiento cross-motor** — m28 imports de `backend.app.models.conformity_lifecycle` (m27 namespace). Documentado en docstring api.py. Aceptable porque ambos motors operan sobre el mismo dominio ENS lifecycle.
- **Boundary jurisdiccional** — si en futuro m27 quisiera aplicar lógica adicional a recategorizations (e.g. trigger renewal automático), m28 endpoints también heredarían ese comportamiento implícitamente. Documentado como riesgo manageable.
- **Tests cross-motor** — cobertura test debe verificar persistencia cruzada (m28 endpoint → m27 table query). Implementado en `backend/tests/motors/m28_change_governance/test_cross_motor_m27.py` (4 tests baseline).

## Alternatives Considered

1. **Tablas duplicadas dedicadas m28** (`m28_recategorizations`, `m28_extraordinary_audits`)
   - Rejected: schema bloat, riesgo inconsistencia, 0 valor agregado vs reuse.

2. **Vista DB unificada** (`CREATE VIEW recategorizations_unified AS ...`)
   - Rejected: complejidad innecesaria, no resuelve sincronización fuente.

3. **Mover tablas a namespace neutral** (e.g. `lifecycle/` no específico m27/m28)
   - Considered for future. Aceptable refactor post-MVP. Por ahora `conformity_lifecycle.py` namespace es suficiente claridad.

## References

- Sub-fase 5.5.F.0.G commit: `a741456` (m27 api.py DB-backed refactor)
- Sub-fase 5.5.F.0.H commit: pending (m28 extend Change + change_topologies + cross-motor reuse)
- Migration m27 state snapshots: `a1b2c3d4e5f6_m27_state_snapshots.py`
- Migration m28 extend: `b2c3d4e5f6a7_m28_change_governance_extend.py`
- TODOs formalizados resueltos: `TODO-COMMIT-PATTERN-001`, `TODO-M27-STATE-MACHINE-PERSISTENCE-001`, `TODO-M28-CHANGE-GOVERNANCE-PERSISTENCE-001`
- Tests cross-motor: `backend/tests/motors/m28_change_governance/test_cross_motor_m27.py` (4 tests baseline ADR-023)


# ADR-024 — Reuniones externas (NO videocall propio FULKRO)

## Status

Accepted 2026-04-30 · FASE 7 Sesión 11 (commits sub-bloques 7.A.1-7.B.10)

## Context

ADR-004 original (pre-S11) propuso videocall propio FULKRO via LiveKit
para K.4 reuniones exploratorias. Implementación quedó en stub:

- 4 archivos m20_workspace/* con LiveKit refs sin uso real
- Columna workspaces.livekit_room_id VARCHAR(100) NULL
- Tabla videocall_sessions (modelo VideocallSession) con 0 rows producción
- Frontend components/meeting/* 100% mock-driven (sprint4-mock)
  sin integración backend real

Producción ENS no requiere videocall propio:
- Clientes ya usan herramientas estándar (Google Meet / Zoom / MS Teams)
- Marcos consultoría ENS Madrid presencial frecuente
- Mantenimiento infra videocall propio sin valor añadido cliente
- Compliance ENS no exige plataforma propia (solo registro/trazabilidad)

## Decision

**Reuniones FULKRO = registro + transcripción + análisis post-meeting**
(no videocall propio).

### Modelo

- Tabla exploratory_meetings (existing 5.5.x, ampliada 7.A.1):
  - +12 columnas metadata reunión externa (12 columns NEW migration
    e8b3c5d70a91):
    - platform (google_meet / zoom / teams / presencial / jitsi / other)
    - meeting_url (link plataforma externa)
    - etapa_k (K.1 .. K.6 + other)
    - interlocutor_contact_id FK client_contacts(id) (M30
      ContactQuickPicker · ADR-023 cross-motor reuse)
    - notes_markdown + notes_html_sanitized (server-side bleach)
    - sse_session_id (link A18 stream)
    - status workflow (scheduled / in_progress / completed / cancelled)
    - completed_at / cancelled_at timestamps
    - title + project_id opcional FK
  - 4 índices (incl GIN FTS español sobre notes_markdown)
  - 3 CHECK constraints whitelists
  - audit trigger tg_audit_exploratory_meetings shared canon

### Endpoints (13 routes registradas)

- /admin/meetings (11 routes admin-only require_owner):
  CRUD + workflow (complete/cancel) + search FTS + by-client +
  sse-init + post-action + delete
- /agents/18/meeting-update (2 routes):
  - POST sync (legacy preservado backward-compat)
  - POST stream (SSE text/event-stream 4 events: progress thinking →
    validating → insight → done)

### Cross-motor 5 integrations wired

- **M30 ContactQuickPicker**: interlocutor reunión + auto-log
  interaction_type='meeting' source_motor='meetings' post-completion
- **M12 magic link FIRMA_DOCUMENTO**: K.6 firma post-meeting con
  sent_to_contact_id cross-motor M12↔M30 reuse
- **A19 RedactorPropuestasAgent**: P-001 propuesta draft sobre
  project_id meeting
- **Core projects.create_project**: linkea meeting.project_id
  automáticamente
- **EmailSender consolidado**: email summary out-of-band con override
  contact.email si M30 presente

### Frontend (sub-bloques 7.B)

- components/admin-meetings/* greenfield:
  MeetingLayoutV2 + MeetingInterlocutorCard + MeetingTimer +
  MeetingNotes (autosave 2s) + MeetingLivePanel (SSE consumer fetch +
  ReadableStream) + PostMeetingActions (4 botones) + MeetingsHistoryTable
- app/(admin)/admin/meetings/{,[id],new} 3 routes
- app/(admin)/admin/clients/[id]/meetings vista histórica por cliente
- lib/admin-meetings/{api,schemas}.ts wrapper coherente lib pattern
- Sidebar entry Reuniones + ROUTES.meetings

## Consequences

### Positive

- Scope realista MVP (no infra videocall mantenimiento)
- Compatible con cualquier herramienta videocall del cliente
- Auto-log M30 timeline (auditor ENS ve trazabilidad reuniones por contacto)
- Cross-motor reuse confirmado producción (M30/M12/A19/Core/Email)
- TODO-A18-LATENCY backend MVP RESOLVED (sub-bloque 7.A.5)
- 3 Playwright E2E tests cubren form + detail + histórica
- Cero deuda arquitectónica nueva en FASE 7

### Negative · Hardening S13

- **TODO-LIVEKIT-CLEANUP-001 [BAJA]**: limpiar 4 archivos
  m20_workspace/* + drop tabla videocall_sessions + columna
  workspaces.livekit_room_id. Estimación 1-2h. Diferido S13.
- **TODO-A18-TOKEN-STREAM-001 [BAJA]**: refactor SSE backend a
  Anthropic messages.stream() real token-by-token (vs MVP wrapper
  sync). Requiere refactor base._call_llm. Estimación 3-4h. Diferido S13.
- sprint4-mock.ts + sprint4-types.ts mantenidos por consumers fuera
  scope FASE 7 (copilot / public portals / audit / magic-links). Tipos
  meeting-* dead code en ambos archivos. Limpieza opcional S13.
- ROUTES.meeting (singular) mantenido en lib/constants.ts por
  compat bookmarks externos. S13 puede añadir middleware redirect
  301 → /admin/meetings.

## Alternatives Considered

1. **LiveKit videocall propio (ADR-004 original)**
   - Rejected: scope masivo, mantenimiento infra, no valor cliente.

2. **Embed iframe Google Meet / Zoom dentro FULKRO**
   - Rejected: terms of service plataformas no permiten embedding,
     UX degradada, problemas auth cookies cross-origin.

3. **Webhook plataformas videocall para auto-import transcripts**
   - Considered for S14+. Postponed: necesita integración OAuth con
     cada plataforma + acceso enterprise APIs. MVP manual notes
     suficiente.

## References

- Sub-fase 7.A.1 commit: 2c243e4 (migration meeting_v2)
- Sub-fase 7.A.5 commit: 16bef86 (SSE A18 stream MVP)
- Sub-fase 7.A.6 commit: 9bfa375 (PostMeetingActions cross-motor)
- ADR-004 original (videocall propio · superseded por este ADR-024)
- ADR-023 (M30 dominio compartido · ContactQuickPicker reuse)
- TODO-A18-LATENCY (RESOLVED backend MVP FASE 7.A.5)
- TODO-LIVEKIT-CLEANUP-001 (NEW · BAJA · S13)
- TODO-A18-TOKEN-STREAM-001 (NEW · BAJA · S13)
- Plan v4.2 FASE 7 (línea 4567-4655 PLAN_MASTER.md)


# ADR-025 — DB drift resolution: alinear modelo a realidad cuando BD tiene semantic correcto

**Status**: Accepted 2026-04-30 · Mini-Sesión 11.5

## Context

`TODO-DB-DRIFT-001` framing original (2026-04-27 / 2026-04-28) asumió "modelo es la verdad declarativa, BD se alinea aplicando migrations correctivas". El audit empírico Mini-Sesión 11.5 cazó realidad opuesta de forma reproducible:

- BD tiene CASCADE/SET NULL/UNIQUE/CHECK + columnas esenciales heredadas de migrations originales correctas (especialmente: `audit_log.seq` BIGSERIAL UNIQUE para HASH CHAIN tamper-evidence ENS RD 311/2022 + `ens_measure_evidencia_types` 4 cols catálogo audit-grade 105 rows).
- Modelos SQLAlchemy perdieron declarations en refactors históricos sin migration correctiva. El drift entre `Base.metadata` y BD reflejaba **modelo incompleto, no BD obsoleta**.
- DROP ciego basado en autogenerate hubiera destruido invariantes críticos sin recovery (HASH CHAIN audit, catálogo ENS, FK CASCADE semantic).

## Decision

Strategy resolución drift híbrida per categoría:

1. **Modelo declara invariant ausente BD** → migration alembic `ALTER` para reforzar BD (ej: CAT-D D.1b `ALTER COLUMN SET NOT NULL` con verificación 0 NULLs empírica + D.3b `ALTER TYPE String(20)` con max_len verificado).

2. **BD tiene semantic correcto + modelo no declara** → editar modelo alineando declarativamente sin migration (ej: CAT-C completo Caso A vacía · 7 FK `ondelete='CASCADE'` + 1 FK `ondelete='SET NULL'` + 2 `UniqueConstraint` + 1 `Index unique=True` restored a modelos m10/idms/conformity_lifecycle/operations_paso7/commercial_paso7/retainer · 0 ops migration; CAT-D D.1a `Mapped[X | None]` → `Mapped[X]` + `nullable=False` en 29 mapped_column · 0 ops migration; CAT-D RESTORE columnas críticas `audit_log.seq` + `ens_measure_evidencia_types` 4 cols).

3. **Expression-based diff fantasma (FTS GIN `to_tsvector`)** → `env.py::include_object` filter alembic compare (CAT-B B.2b 3 indexes `ix_client_contacts_notes_fts` + `ix_client_messages_body_fts` + `ix_exploratory_meetings_notes_fts`).

4. **Tabla / columna BD legacy verificada empírico** → DROP via migration con backup BD pre-ejecución (CAT-D drop_column 4 client_id legacy: 100% NULL + 0 referencias código + git history confirma refactor consolidación JOIN vía project_id).

## Audit-first per categoría obligatorio (LECCIÓN-OPS-003 reafirmada)

Pre-cualquier ejecución migration arriesgada:

- **Audit-1**: count rows + NOT NULL distinct empírico SQL.
- **Audit-2**: grep código uso queries / filter / access patterns.
- **Audit-3**: git log migration original que añadió columna/tabla (intent histórico documentado).
- **Audit-4** (cuando aplique): refs plan v4.2 / spec / SESSION_LOG previa para feature WIP detection.

Si cualquier audit revela datos activos o uso código en columna candidate DROP: **RESTORE** obligatorio (ej: `audit_log.seq` Audit-3 reveló BIGSERIAL UNIQUE para hash chain · DROP habría sido inadmisible auditor ENS).

## Consequences

✅ **Validación empírica del pattern 4 veces consecutivas**:

| Sub-bloque | Hash | Approach | Ops migration | Model edits |
|-----------|------|----------|---------------|-------------|
| MIG-A (CAT-B index) | `63b32ec` | Migration + env filter + restore | 94 | 6 indexes |
| MIG-B (CAT-C constraint) | `68c4e21` | Models-only (Caso A vacía) | **0** | 11 FK/UQ/idx |
| MIG-C (CAT-D alter_column) | `0274600` | Migration + 33 model edits | 37 | 33 cols |
| MIG-D (CAT-D drop_column) | `e09d594` | Migration + 5 model RESTORE | 16 | 5 cols críticos |
| MIG-E (CAT-E table) | (no commit) | Diff falso positivo · modelo ya alineado | 0 | 0 |
| MIG-F (CAT-F RLS) | (no commit) | 87 tablas RLS todas trazadas migrations vía loops dinámicos | 0 | 0 |

**Total efectivo**: 147 ops migration + ~55 model edits. ~36% drift resuelto vía model edits sin `ALTER TABLE` riesgosos.

✅ **Audit-first cazó catástrofe deploy-bloqueante**: `audit_log.seq` HASH CHAIN tamper-evidence audit ENS habría sido eliminado por DROP ciego basado en autogenerate. Audit-3 git history reveló criticidad antes ejecución.

✅ **0 ops drift residual final post-MIG-A → MIG-D** confirmado empíricamente (alembic autogenerate dry-run vacío).

❌ **Requiere disciplina audit-first per sub-bloque** (no fix mecánico bulk · audit empírico es trabajo manual).

❌ **Pattern aplicable solo cuando BD existing tiene semantic correcto** vs greenfield deploy donde modelo SÍ es la verdad.

## Caveats methodology

Durante Mini-S11.5 se cazaron 2 falsos positivos en counts iniciales:

1. **CAT-E `evidence_renewal_requests`**: diff inicial usó `grep "__tablename__\\s*=\\s*\"X\""` (double quotes only). El modelo declara `__tablename__ = 'X'` con single quotes. Re-grep con quotes ambos cubre 100%.

2. **CAT-F RLS policies "huérfanas"**: count crude `grep "CREATE POLICY"` no captura migrations que aplican policies vía `for table in TRACKED_TABLES: op.execute(f"CREATE POLICY ... ON {table}")`. Verificación correcta: cross-reference distinct policy names BD (4 nombres: admin_all + client_isolation + message_isolation + project_isolation) con tablas mencionadas en migrations files (87/87 tablas RLS trazadas).

**Lección operacional adicional**: regex grep crude requiere validación post-hoc con Python parsing más robusto cuando metric counts se usan para framing decision pre-implementation.

## References

- TODO-DB-DRIFT-001 RESOLVED Mini-S11.5 (`progress/backlog_formal.md` sección Progreso 2026-04-30).
- LECCIÓN-OPS-003 (validar premisas arquitectónicas con grep empírico antes implementación).
- Backup BD pre-MIG-D snapshot: `/tmp/db_pre_mig_d_backup_20260430_120346.sql` (339KB schema-only).
- Commits Mini-Sesión 11.5: `63b32ec` (MIG-A) · `68c4e21` (MIG-B) · `0274600` (MIG-C) · `e09d594` (MIG-D).
- Plan v4.2 deploy producción Hetzner DESBLOQUEADO post Mini-S11.5.


# ADR-026 — Workflow phase derivation · 8 fases lifecycle persisted + CASCADE fallback

**Status**: Accepted 2026-04-30 · FASE 8 backend Sesión A
**Decisor**: Marcos Mata García
**Supersedes**: ADR-007 D17 Opción A (nomenclatura técnica 7 fases motors)

## Context

`ADR-007` D17 Opción A (pre-S11) propuso "vista guiada por fases ENS" exponiendo `workflow_gates.py` existing (252 LOC). El audit-first FASE 8 cazó **2 hallazgos críticos** pre-implementación:

1. **`workflow_gates.py` existing tiene SOLO gates checkpointing** (`require_signed_categorization` / `require_frozen_dda` / etc — 6 funciones que raise `WorkflowGateError`). **NO existen** las funciones derive_state (`get_current_phase`, `get_next_actions`, `get_phase_progress`, `get_phase_tasks`) que el plan asumía exponer. Plan framing "expose existing" inexacto.

2. **`projects.fase` columna persistida** (VARCHAR(50)) detectada en BD con 3 valores reales (IMPLANTACION/VERIFICACION/DIAGNOSTICO) + 10 NULLs. Plan v4.2 declaró 8 fases lifecycle lowercase (`pre_venta`/`onboarding`/`diagnostico`/`adecuacion`/`implantacion`/`verificacion`/`conformidad`/`retainer_cierre`). El "derive on-demand sin tabla nueva" del plan ignoraba columna existing — la realidad es mejor que el plan: persisted column + 13 rows uso real.

Sin audit-first habríamos diseñado funciones derive_state ignorando `projects.fase` = duplicación + inconsistencia BD.

## Decision

Implementación FASE 8 strategy híbrida:

1. **8 fases lifecycle plan v4.2** (supersedes ADR-007 7 fases técnicas):
   - `pre_venta` · `onboarding` · `diagnostico` · `adecuacion` · `implantacion` · `verificacion` · `conformidad` · `retainer_cierre`
   - Lifecycle completo cubre cliente cara UI ("estoy en diagnóstico") vs interno técnico ("estoy en M03 frozen")

2. **`projects.fase` persisted = source of truth primaria**:
   - Cliente avanza fase explícitamente vía UI o motor service
   - Migration `2ddffdcdddfc_fase8_workflow_phase_normalization` normaliza valores existing lowercase + backfill 10 NULLs → `pre_venta` + ALTER NOT NULL + CHECK constraint enum 8 fases

3. **Fallback CASCADE en `workflow_state.py`** si `projects.fase` desactualizado vs realidad motors:
   - Order: retainer/cierre → conformidad → verificación → implantación → adecuación → diagnóstico → onboarding → pre_venta (default)
   - 7 EXISTS subqueries cross-tablas motors

4. **4 funciones derive_state** en módulo nuevo `backend/app/core/workflow_state.py` (separado de `workflow_gates.py` para distinguir derive_state vs checkpointing):
   - `get_current_phase(project_id)` → `WorkflowPhase`
   - `get_next_actions(project_id, limit=5)` → `list[NextAction]`
   - `get_phase_progress(project_id, phase)` → `PhaseProgress`
   - `get_phase_tasks(project_id, phase)` → `list[TaskItem]`
   - + helper `get_workflow_roadmap(project_id)` → 8 fases con estados

5. **`action_templates` / `task_templates` como Python constants** (`workflow_templates.py`):
   - Coherente principio ADR-025 "no crear tabla nueva"
   - Templates lifecycle stable (no cambian per cliente individual)
   - Lookup constant runtime > query DB
   - `TODO-PHASE-TEMPLATES-DB-001` [BAJA · post-deploy] formaliza migración a tabla `phase_action_templates` SI futuro requiere edición dinámica per cliente

6. **5 endpoints REST** `/api/v1/workflow/*` con `require_owner` RBAC (Marcos admin only):
   - `GET /current-phase/{project_id}`
   - `GET /next-actions/{project_id}?limit=5`
   - `GET /phase-progress/{project_id}/{phase}`
   - `GET /phase-tasks/{project_id}/{phase}`
   - `GET /roadmap/{project_id}`

## Consequences

✅ `projects.fase` persisted preserved + leveraged (no re-implementar wheel)
✅ CASCADE fallback garantiza consistencia cross-motor si fase desactualizada
✅ Templates Python = simplicidad + performance + ADR-025 coherente
✅ ENS lifecycle visible cliente UI (8 fases vs 7 técnicas internas)
✅ Audit-first cazó H1 (workflow_gates checkpointing ≠ derive_state) + H2 (projects.fase persisted) pre-impl

❌ Templates editing requires deploy (mitigated `TODO-PHASE-TEMPLATES-DB-001` BAJA post-deploy)
❌ 5 tablas sin `project_id` index aplicables a CASCADE fallback (mitigated bajo rows count actual + TODO post-deploy si latencia notable)
❌ Cliente access vía `/api/v1/portal/*` queda fuera scope FASE 8 backend (TODO-CLIENT-WORKFLOW-VIEW post-deploy si requerido)

## References

- ADR-007 D17 Opción A (supersedes nomenclatura · 7 fases técnicas → 8 fases lifecycle)
- ADR-025 (no crear tabla nueva pattern · models-first cuando BD ya semantically correct)
- LECCIÓN-OPS-003 (validar premisas arquitectónicas con grep empírico antes implementación)
- Migration `2ddffdcdddfc_fase8_workflow_phase_normalization` (projects.fase normalización)
- Files: `backend/app/core/workflow_phase.py` (enum) + `workflow_state.py` (4 funciones) + `workflow_schemas.py` (Pydantic) + `workflow_templates.py` (Python constants) + `backend/app/api/v1/workflow.py` (5 endpoints)
- Tests: `backend/tests/core/test_workflow_state.py` (9 tests baseline)
- Hash MIG normalización: `<TBD>` · Hash cierre Sesión A: `<TBD>` · Tag `s11-fase-8-a-backend`

---

## ADR-027 · OPCION D hibrido C1-preserve + documento-adopt para FASE 8.5

**Status**: Accepted 2026-04-30 · FASE 8.5 cierre

### Context

Sesion C1 cerro infraestructura backend pipeline radar v2 con tag `s11-fase-8-5-c1-backend` (hash `f2fce18`): PipelineRun model + CancellableRunner cooperativo + 9 endpoints REST + 12 tests baseline. Marcos aporto despues documento `FULKRO_ENS_RADAR_PORTAL_COMPLETO.md` (4201 lineas) con spec alternativa monolitica del portal completo (incluyendo blueprint comercial: detector ENS v2, temperature 7 niveles, cluster_id, email_redactado, 8 estados workflow comercial).

Verificacion web profunda confirmo informacion ENS 100% veraz (RD 311/2022 + plazos certificacion + CPVs + Andersen + CCN + Audidat + CertENS + Proinca). Conflicto: schemas C1 vs documento incompatibles en algunos puntos (campos PipelineRun, endpoints prefix `/admin/radar/*` vs `/api/v1/motors/m10/*`, asyncio.Event vs polling, asincrono vs sync).

### Decision

Adoptar documento como BLUEPRINT comercial mediante extensiones additive sobre C1, NO revertir Sesion C1.

- **Sesion C1 invariante preservada** (tag aplicado vivo en historial git):
  - PipelineRun model existing (UUID primary key, status workflow 5 estados, cancel cooperativo)
  - CancellableRunner polling pattern (no asyncio.Event)
  - 9 endpoints `/api/v1/motors/m10/pipeline/*` (no /admin/radar/*)
  - 12 tests baseline + V-CHECK 26 verde
- **Documento valor comercial entregado** via:
  - Migration `0bdc5b753ab2` ENSAnalysis +3 / RadarLead +9 / PipelineRun +11 (no breaking)
  - 7 niveles temperatura (4 v1 + 3 v2: ardiendo_excluido, vence_pronto_oferta, ardiendo_sostenido)
  - 8 estados workflow comercial (CHECK constraint estado_contacto)
  - Email pre-redactado editable
  - Cluster_id agrupacion semantica
  - Plazo CEE (meses + dias_hasta_vencimiento)
- **Adaptaciones cross-pattern documento -> realidad**:
  - "Lead" / "Tender" / "Company" -> RadarLead / Tender / Company existing
  - "ENSAnalysis" -> ENSAnalysis existing extendido (no recrear)
  - Auth: `require_ens_radar_owner` existing FASE 3 preservado (no `auth.py` nuevo)
  - CancellableRunner polling pattern preservado (no asyncio.Event documento)
  - URL prefix `/api/v1/motors/m10/*` preservado (no `/admin/radar/*` documento)
  - Sesiones SYNC consistencia C1 (no AsyncSession)
  - Frontend: sin `asChild` Button (no soportado en codebase) -> `buttonVariants` + `Link`; sin `variant="destructive"` -> `variant="danger"`

### Consequences

✅ Portal ENS Radar admin-only funcional inmediato (Marcos USA herramienta HOY)
✅ Informacion comercial veraz auditable (RD 311/2022 + plazos certificacion + CPVs)
✅ Trabajo Sesion C1 invariante (audit-first respetado · ningun trabajo desperdiciado)
✅ Documento valor 100% entregado via adaptacion (no se descarto blueprint)
✅ Compatibilidad backwards: tests v1 26 + v2 72 = 98 verde · 0 regresiones

❌ Schemas mas amplios por adopcion additive (mitigado: cada campo justificado semanticamente)
❌ Adaptaciones cross-pattern requirieron cuidado mid-impl (LECCION-OPS-003 sostenida)
❌ "Por que tu" angle solo en fallback dossier; LLM puede ignorarlo si no recibe contexto adecuado (mitigado: prompt instruye explicitamente)
❌ leads_updated heuristic (min(snapshot_pre, total - delta)) es aproximacion (mitigado: solo informativo · no afecta business logic)

### References

- Sesion C1 hash `f2fce18` · tag `s11-fase-8-5-c1-backend`
- Documento ENS Radar Portal (4201 lineas)
- Verificacion web RD 311/2022 ENS (BOE + Andersen + CCN + Audidat + CertENS + Proinca)
- Sesion C2 hashes `0f918dd` -> `572655b` (refactores algoritmicos D-J + RUN)
- Sesion D hash `a285834` (frontend portal completo)
- Migrations: `cb9c8416b68a` (C1 PipelineRun) + `0bdc5b753ab2` (C2 additive extensions)
- Tag final: `s11-fase-8-5-cerrada`

---

# ADR-028 — Magic Links emails: Python inline renderer (supersede parcial ADR-011)

**Fecha**: 2026-05-01
**Estado**: Aprobado (Sesión 11 · FASE 4.5 sub-bloque C)
**Decisor**: Marcos Mata García
**Referencias**: ADR-011 (Magic Links auditoría + ampliación · 2026-04-25)

## Contexto

ADR-011 FR15.4 especificaba la migración del sistema de email rendering a templates Jinja2 separados por purpose, en la ruta:

```
backend/app/templates/email/magic_link/{purpose}.html.j2
```

La implementación pre-FASE 4.5 mantenía la arquitectura previa: dict Python `_PURPOSE_EMAILS` con dataclass `PurposeEmailConfig` por purpose en `backend/app/motors/m12_magic_link/emails/renderer.py` (23 entries, ~848 LOC).

Tras FASE 4.5 sub-bloque A (commit `5d3ca2d`), el dict tiene 35 entries y ~1090 LOC. Llegado este punto se formalizó la decisión arquitectónica: ¿migrar a Jinja2 templates o mantener Python inline?

## Decisión

**Mantener la arquitectura Python inline. NO migrar a templates Jinja2 separados.**

Esta ADR supersede parcialmente ADR-011 FR15.4. El resto de ADR-011 (audit + ampliación + email destinatario configurable + migración 3 cols) queda vigente.

## Razones

1. **Funciona en producción**. Los 23 emails pre-FASE 4.5 están operativos. Los 12 nuevos están cubiertos por 12 tests parametrize `test_purpose_email_renders_realistic_scope` (sub-bloque B.1, commit `c4c7cf4`). Migrar 35 emails introduce riesgo de regresión por una mejora de mantenibilidad teórica.

2. **i18n no está en roadmap S11/S12**. FULKRO se vende a empresas privadas españolas para licitaciones públicas (RD 311/2022). Idioma único castellano. La justificación "mejor i18n futuro" del spec original no aplica al horizonte real del producto.

3. **Determinismo y testabilidad**. El dict Python permite linting + type-checking (`PurposeEmailConfig` dataclass). Jinja2 separado obliga a tests adicionales por archivo template y reduce las garantías estáticas del sistema de tipos.

4. **"Nothing internal leaks" garantizado por la arquitectura actual**. El renderer solo accede a campos declarados en `PurposeEmailConfig`. Cambiar a Jinja2 abriría superficie a refs accidentales a Motor X / Agente X / etc en plantillas sueltas (regla feedback memory inviolable).

5. **Pattern Sesión 11 sostenido**. `TODO-PHASE-TEMPLATES-DB-001` documentó la misma filosofía para `workflow_templates.py`: Python constants funcionan; migrar a tabla solo si feedback empírico real lo justifica. El mismo principio se aplica aquí.

## Consequences

- ADR-011 FR15.4 (Jinja2 templates) **superseded parcialmente**.
- Cualquier email nuevo se añade al dict `_PURPOSE_EMAILS` con `PurposeEmailConfig`.
- Si en el futuro se requiere i18n, evaluar como sub-fase dedicada (no incremental).
- Si en el futuro se requiere edición dinámica per cliente, evaluar migración a tabla `email_templates` (similar a `TODO-PHASE-TEMPLATES-DB-001`).
- El `_SafeDict` del renderer debe ampliarse cada vez que se añadan variables Jinja-style nuevas a los emails (lección aprendida sub-bloque B.1).

## Lección sostenida

Tests no-throw insuficientes para validar emails. La validación de interpolación correcta (`test_purpose_email_renders_realistic_scope` con scope realistic) es la garantía operativa. El bug latente del `_SafeDict` cazado en sub-bloque B.1 (commit `c4c7cf4`) confirma este punto: el test invariante `test_all_purposes_render_without_error` solo aseguraba que el render no lanzara excepción, pero los placeholders sin substituir quedaban como literal `{var_name}` en el HTML enviado al cliente.

Pattern Sesión 11 reafirmado: **tests verde ≠ calidad real**. Audit-first post-cierre tag captura clases distintas de issues que tests automáticos no detectan porque ejercitan rutas felices y no la semántica completa del producto.

## References

- ADR-011 (Magic Links auditoría + ampliación + email destinatario · 2026-04-25)
- `TODO-PHASE-TEMPLATES-DB-001` (pattern filosofía Python constants vs tabla)
- Commit `5d3ca2d` (FASE 4.5 sub-bloque A · 12 emails añadidos al dict)
- Commit `c4c7cf4` (FASE 4.5 sub-bloque B.1 · bug fix `_SafeDict`)
- `backend/app/motors/m12_magic_link/emails/renderer.py` (canonical · `_PURPOSE_EMAILS` dict)
- `docs/spec/MAGIC_LINKS.md` (referencia operativa)


---

# ADR-029 — Cleanup CCN-STIC 804 v2017 legacy + reseed canónico diferido

**Status:** Accepted · 2 mayo 2026
**Sesión:** Sesión 11 · Sub-fase 9.0 (pre-FASE 9)

## Contexto

Audit pre-FASE 9 reveló convivencia histórica de 2 versiones ENS en BD: 73 medidas RD 311/2022 (vigente desde 2022) + 7 medidas CCN-STIC 804 v2017 obsoletas (`mp.com.9`, `mp.if.9`, `mp.info.9`, `mp.per.9`, `mp.s.8`, `mp.s.9`, `op.exp.11`).

Adicionalmente, 2 tablas paralelas refuerzos:
- `ens_reinforcements` (legacy 18 rows · placeholder sintéticas sin valor normativo)
- `ens_measure_refuerzos` (nueva 0 rows · schema superior con `applicable_categories` JSONB + `source_chunk_id` FK RAG)

## Decisión

1. **Eliminar las 7 measures fantasma CCN-STIC 804 v2017**. FULKRO comercializa RD 311/2022 vigente · v2017 obsoleta no aplica a clientes nuevos desde 2022.

2. **Drop tabla `ens_reinforcements` legacy**. Schema `ens_measure_refuerzos` superior arquitectónicamente.

3. **Reseed canónico `ens_measure_refuerzos` DIFERIDO** a sesión dedicada post-FASE 9. Producir datos canónicos RD 311/2022 Anexo II (~600 rows con precisión normativa) requiere:
   - Dataset CCN-STIC oficial estructurado (si existe)
   - O construcción cuidadosa desde RD 311/2022 BOE PDF
   - Validación humana entry-by-entry por consultor ENS

   Estimación: 4-6h trabajo cuidadoso · NO fit con sesión actual modo turbo.

   TODO: `TODO-S11-ENS-DATA-CANONICAL-DEFER-001`

4. **Pre-flight check** `dda_entries.refuerzos_aplicados` antes de DELETE · 0 hallazgos.

## Consecuencias

- Producto FULKRO RD 311/2022 puro · sin v2017 obsoleta
- Una sola tabla refuerzos · sin deuda técnica paralela
- Schema RAG-traceable (`source_chunk_id`) ready para Copilot
- FASE 9 UI plumbing arranca con BD limpia
- Tablas detail (`ens_measure_dimensiones`, `ens_measure_refuerzos`, `ens_measure_guias_ccn`) quedan vacías hasta sesión post-FASE 9 dedicada.
- Modelo SQLAlchemy `EnsReinforcement` eliminado de `backend/app/models/ens.py` · método `DdaService._applicable_reinforcements()` stub vacío preserva interfaz.
- Test `TestEnsReinforcements` (`backend/tests/scripts/test_load_ens_measures_catalog.py`) skip-marked hasta reseed Fase α.2.
- Rollback: `var/backups/fase_9_0_pre_cleanup_20260502_1237.sql`

## Migrations aplicadas

1. `c6f5ff65d8be_fase_9_0_cleanup_ccn_stic_804_v2017_legacy` (eliminación 7 measures fantasma + 18 refuerzos placeholder)
2. `83e27091b489_fase_9_0_drop_ens_reinforcements_legacy` (drop tabla legacy)

## Referencias

- `progress/session_11/fase_9_0/REPORT_0C.md`
- `progress/session_11/audit_pre_fase_9/REPORT.md`
- RD 311/2022 BOE: https://www.boe.es/eli/es/rd/2022/05/03/311

---

# ADR-030 — Criterio WHITELIST_EXACT/PREFIX endpoints sin auth

**Status:** Accepted · 4 mayo 2026
**Sesión:** Sesión 11 · SAN-B.MB-2.3

## Contexto

`backend/app/auth/global_dep.py` define `WHITELIST_EXACT` (frozenset paths
exactos) y `WHITELIST_PREFIX` (tuple prefijos) que bypassan el middleware
`authenticate_request`. Sin criterio formal, riesgo creep de endpoints
expuestos sin justificación documentada — auditor externo no podría
validar criterio sin grep código.

Audit MB-2.0 reveló 5 entries `WHITELIST_EXACT` sin comentario inline
(login flows + healthcheck + docs públicos), aunque obvios para
auditor experimentado. `WHITELIST_PREFIX` ya 100% documentado.

## Decisión

### Criterio inclusión `WHITELIST_EXACT`

Un endpoint puede estar en `WHITELIST_EXACT` si y solo si cumple **uno** de:

1. **Pre-auth flow**: cliente NO tiene aún session/cookie/JWT cuando
   debe llamar el endpoint (ej. `/auth/login`, `/auth/totp/verify`,
   `/auth/webauthn/verify`, `/client-auth/login`).

2. **Token-based público**: endpoint usa token magic-link en body o
   path como autenticación efectiva (ej. `/magic-links/consume`,
   `/onboarding/consume`, `/evidence/public-key`). El endpoint valida
   el token internamente y rechaza si inválido.

3. **Operacional estándar**: monitoring/probes (`/health`, `/metrics`),
   schema/docs auto-generadas (`/openapi.json`, `/docs`, `/redoc`)
   sin información sensible.

   *Amendment 2026-09-10 (BLOQUE G)*: `/metrics` entra por este criterio. Se
   saca de la autenticación de **sesión** porque un raspador no tiene cookie ni
   segundo factor, no porque sea público: su cuerpo incluye el coste acumulado
   de las llamadas al modelo y el mapa de rutas de la API. La puerta propia
   está en `backend/app/main.py` — en producción exige
   `Authorization: Bearer $FULKRO_METRICS_TOKEN`, y si esa variable no está
   configurada devuelve 503 en vez de servirse. Fuera de producción se sirve
   abierto, deliberadamente: si el demo exigiera token, `make demo` no podría
   enseñar que las métricas existen. Cobertura:
   `tests/auth/test_global_dep_whitelist.py::test_bloque_g_metrics_publico_sin_auth`.

4. **Catálogo público read-only**: datos sin información sensible
   accesibles por diseño (ej. `/onboarding/lms/courses` catálogo
   cursos LMS).

   *Amendment 2026-09-11 (BLOQUE I6)*:
   `/api/v1/legal/dpa-template/download` entra por este criterio, el mismo que
   ya exime a `/legal/compliance/status` y a
   `/legal/sub-processor-notifications/subscribe`. Es la plantilla del contrato
   de encargo del tratamiento (art. 28 RGPD): lo que un posible cliente quiere
   leer **antes** de contratar. No expone dato de ningún cliente — devuelve los
   datos de FULKRO como responsable, huecos para el cliente, y los
   sub-encargados que ya están publicados en `/sub-processors`.

   Lo que hace interesante esta entrada es **cómo apareció**. El endpoint se
   declaraba público en su propio docstring («`dpa_public_router` (no auth)»)
   y devolvía **401** desde siempre, porque la dependencia global lo paraba
   antes de llegar al handler. Nadie lo había notado porque a la página
   `/dpa-template` no llegaba nadie: era una de las siete páginas legales sin
   un solo enlace entrante en todo el código. Al añadir esos enlaces al pie
   global, el recorrido automático del bloque E lo encontró en la primera
   pasada. Es la misma familia que el 401 de `/metrics`, y la misma lección:
   **un endpoint que nadie puede alcanzar no es un endpoint que funciona; es
   uno que nadie ha probado.** Cobertura:
   `tests/auth/test_global_dep_whitelist.py::test_bloque_i_dpa_template_publico_sin_auth`.

### Criterio inclusión `WHITELIST_PREFIX`

Mismo criterio que `WHITELIST_EXACT`, aplicado a sub-paths bajo un
prefijo común:
- `/api/v1/public/` · M08 verification public portals (token-based)
- `/api/v1/_dev/` · gated `is_production=False`
- `/api/v1/onboarding/me/` · M16 cliente token-based (headers
  `x-onboarding-session`)
- `/api/v1/magic-links/by-token/` · GET público pre-consume sign-flows
- `/api/v1/onboarding/lms/courses/` · catálogo individual LMS
- `/docs/`, `/redoc/` · assets Swagger/ReDoc

### Process amendment

Cualquier nuevo endpoint candidato a whitelist requiere:

1. Justificar en PR commit message qué criterio (1-4) cumple
2. Comentario inline en `global_dep.py` con tag `# ADR-030 · <razón>`
   o `# H<NN> fix (<contexto>)` si cierra issue específico
3. Update este ADR-030 si introduce criterio nuevo
4. Suite acotada `tests/auth/test_global_dep_whitelist.py` cubriendo
   el endpoint con caso "no-auth ⇒ 200" + caso "endpoint-no-listado-sin-auth ⇒ 401"

## Consecuencias

- Auditor externo verifica criterio sin grep código
- Adiciones futuras forzadas a justificar
- Comentarios inline cubren los 12 EXACT + 7 PREFIX entries actuales
- 0 cambios runtime · solo documentación + comentarios

## Referencias

- `backend/app/auth/global_dep.py:49-93` · WHITELIST_EXACT + WHITELIST_PREFIX
- `backend/app/auth/dependencies.py` · ADR-021 motors auth landing
- ADR-019 · CSRF triple binding
- ADR-021 · Motors Auth Landing


# ADR-031 — MAGERIT hybrid mode no implementado · decisión arquitectónica

## Status

Aceptada · Sesión 11 saneamiento (4 mayo 2026)

## Contexto

M02 expone `calculation_mode` con valor `"hybrid"` en CHECK constraint
de BD y schemas Pydantic, históricamente como placeholder para combinar
valoraciones cualitativas + cuantitativas en el mismo análisis. Sin
embargo MAGERIT v3 Libro III (Técnicas) no formaliza un cálculo
canónico para modo combinado: las tablas de valor/impacto/riesgo
qualitative (Libro III sec 2.1, p.6-7) y las fórmulas continuas
quantitative (Libro III sec 2.2.2, p.10-12) operan sobre dominios
distintos (escala 0-10 vs €) sin función de agregación canónica.

Las 3 funciones de propagación/cálculo (`propagate_values`,
`calculate_intrinsic_risk`, `calculate_effective_risk`) llevaban
`raise NotImplementedError("hybrid mode pending Grupo 3")` desde
Sesión 8, redactado como diferimiento temporal. La realidad es que
no es diferimiento: es decisión arquitectónica permanente.

## Decisión

- `hybrid` permanece como `Literal` válido en schemas BD y Pydantic
  por compatibilidad (no romper analyses históricos con ese valor).
- Las 3 funciones (`_propagate_values`, `calculate_intrinsic_risk`,
  `calculate_effective_risk`) lanzan `NotImplementedError` explícito
  con mensaje canónico que referencia este ADR-031 si
  `calculation_mode == "hybrid"`.
- Tests `TestHybridModeRaisesNotImpl` (3 casos) verifican behavior
  contractual.
- **NO se planea implementación futura** · diseño cerrado.

## Consecuencias

- Producción usa `qualitative` o `quantitative` · cumplimiento ENS canónico
- Si auditor solicita análisis hybrid · respuesta: "MAGERIT v3 no lo
  formaliza · combinar requiere análisis paralelo qualitative +
  quantitative y comparar, no un cálculo único combinado"
- 0 deuda técnica · decisión cerrada arquitectónicamente
- Mensajes `NotImplementedError` ahora son auto-explicativos
  (auditor ve referencia ADR sin grep código)

## Referencias

- MAGERIT v3 Libro III · sec 2 (no menciona hybrid canónico)
- `backend/app/motors/m02_magerit/service.py:450,627,917` · 3 raises
- `backend/tests/motors/m02_magerit/test_m02_magerit.py::TestHybridModeRaisesNotImpl`
- ADR-029 · Cleanup CCN-STIC 804 v2017 (precedente decisión arquitectónica permanente)


# ADR-032 — M20 chat encryption at-rest · Fernet local master key

## Status

Aceptada · Sesión 11 saneamiento (4 mayo 2026) · **IMPLEMENTADA SAN-B.MB-3.ter.4**

## Contexto

`WorkspaceChatMessage.mensaje` (tabla `workspace_chat_messages`)
almacena conversaciones colaborativas internas Marcos ↔ contactos
cliente en el workspace M20 (chat append-only por proyecto).

Para certificación ENS categoría MEDIA/ALTA, mensajes con info
sensible (datos personales, controles internos, vulnerabilidades
descubiertas) requieren cifrado at-rest. Fernet (AES-128-CBC + HMAC-SHA256)
es el stack canónico FULKRO para field-level encryption.

**Nota histórica**: ADR-004 incluyó "TODO-M20-CHAT-ENCRYPTION
cancelado" en su decisión #4, pero ese alcance se refería a la
tabla `meeting_chat_messages` (chat de reuniones K.0/K.2/K.4/K.6)
que **NO se llegó a crear** (ver también TODO-LIVEKIT-CLEANUP-001).
Esta ADR-032 cubre la tabla diferente `workspace_chat_messages`
(chat colaboración Marcos ↔ cliente) que SÍ existe en BD desde
M20 inicial. Mismo identificador del TODO, scope distinto.

## Decisión

- **KMS provider elegido**: local Fernet master key (single-tenant MVP).
  Opciones rechazadas: AWS KMS (coste recurrente · vendor lock), HashiCorp
  Vault (overhead infra · single-tenant no justifica). Reabrir si
  multi-tenant futuro.
- Master key resolución (`backend/app/core/encryption/master_key.py`):
  1. Production: env var `FULKRO_MASTER_ENCRYPTION_KEY` (32-byte URL-safe
     base64 generada con `Fernet.generate_key()`).
  2. Dev fallback: derived deterministically from `FULKRO_AUTH_PRIVATE_KEY`
     via SHA256+base64 (consistent across restarts · evita romper rows
     existentes en dev).
- `EncryptedText` SQLAlchemy `TypeDecorator` (`backend/app/core/encryption/sqlalchemy_types.py`)
  encrypta/descripta transparente · column underlying type = TEXT
  (Fernet output URL-safe base64 ASCII).
- `WorkspaceChatMessage.mensaje` cambia a `EncryptedText`. Nueva columna
  `encryption_version SMALLINT NOT NULL DEFAULT 1` track key generation
  para soportar key rotation futura via `MultiFernet`.
- Migración alembic `90dd52c1dfd9` aplica column change + backfill
  encrypt rows existentes (idempotent: skip si ya `gAAAAA` Fernet prefix).
  En MVP típicamente 0 rows · backfill no-op pero correcto.
- Key rotation: `FULKRO_KEY_ROTATION_HISTORY` env (newline-separated old
  keys) → `MultiFernet` aplica primary para encrypt y todas (primary +
  history) para decrypt. Migración multi-tenant futura: añadir tenant_id
  a key derivation.

## Consecuencias

- ✅ M20 chat operacional **con cifrado at-rest** · ENS MEDIA/ALTA
  cliente compatible.
- ✅ Raw SELECT en BD muestra ciphertext (`gAAAAA...`) · DBA/audit log
  no expone plaintext.
- ✅ ORM transparente: `msg.mensaje` retorna plaintext (decrypt en
  `process_result_value`).
- ⚠️ FULKRO_MASTER_ENCRYPTION_KEY perdida = data loss para chat existente.
  Operativo: backup separado de la key (gestor de secretos / vault personal).
- ⚠️ Key rotation requiere downtime breve para re-encrypt rows con
  primary key nueva (acceptable si rota cada 6-12 meses).
- Pattern reutilizable para otros campos sensibles futuros (M30 contact
  notes confidenciales, etc.).

## Referencias

- `backend/app/core/encryption/master_key.py` · master Fernet derivation
- `backend/app/core/encryption/sqlalchemy_types.py` · EncryptedText
- `backend/app/models/collaboration.py:101` · WorkspaceChatMessage.mensaje
- `backend/migrations/versions/90dd52c1dfd9_san_b_m20_workspace_chat_messages_.py`
- `backend/tests/core/encryption/` · tests cobertura
- ADR-004 · cancelación scope diferente (meeting_chat_messages no creada)
- ADR-024 · supersedes ADR-004 (videocall externo · M20 sin LiveKit)
- TODO-LIVEKIT-CLEANUP-001 · backlog formal (cleanup dead code LiveKit)
- TODO-M20-CHAT-ENCRYPTION · CERRADO 2026-05-04 SAN-B.MB-3.ter.4


# ADR-033 — Content-Security-Policy + hardening headers pre-deploy

## Status

Aceptada · Sesión 11 saneamiento (4 mayo 2026) · IMPLEMENTADA SAN-B.MB-7.3

## Contexto

Pre-deploy VPS sin headers CSP/X-Frame-Options/X-Content-Type-Options
deja la app vulnerable a XSS reflexivo, clickjacking iframe-based,
content-type sniffing attacks. Standard pre-deploy ENS MEDIA/ALTA.

## Decisión

`CSPMiddleware` (`backend/app/middleware/csp.py`) registrado en `main.py`
post-CORS. Aplica los siguientes headers a TODAS las responses:

- **Content-Security-Policy** con directivas:
  - `default-src 'self'` — todo desde mismo origen por defecto
  - `script-src 'self' 'unsafe-inline' 'unsafe-eval'` — Next.js requiere
    unsafe-inline para hidration scripts inline + unsafe-eval para HMR dev
  - `style-src 'self' 'unsafe-inline'` — Tailwind + shadcn inyectan
    styles inline runtime (no removible sin refactor masivo)
  - `img-src 'self' data: blob:` — MinIO signed URLs vienen como blob:,
    favicons inline como data:
  - `font-src 'self' data:` — fonts locales + data: para shadcn
  - `connect-src 'self' https://api.anthropic.com` — A14 Copilot
    streaming a Anthropic API directo
  - `frame-ancestors 'none'` — anti-clickjacking (refuerza X-Frame-Options)
  - `form-action 'self'` — forms solo a mismo origen
  - `base-uri 'self'` — prevenir <base> hijacking attacks
  - `object-src 'none'` — sin Flash/Java/embed (legacy attack vectors)
- **X-Frame-Options DENY** — anti-clickjacking (compatible browsers viejos)
- **X-Content-Type-Options nosniff** — anti-MIME sniffing
- **Referrer-Policy strict-origin-when-cross-origin** — privacidad referrer

## Consecuencias

- ✅ XSS reflexivo bloqueado (script-src restringido)
- ✅ Clickjacking iframe-based bloqueado (frame-ancestors none)
- ✅ MIME sniffing attacks bloqueados (nosniff)
- ✅ Referrer leak parcial mitigado (strict-origin)
- ⚠️ `unsafe-inline` + `unsafe-eval` necesarios para Next.js · NO removibles
  sin refactor mayor (nonce-based CSP requiere SSR streaming nonces ·
  fuera scope MVP). Justificado pre-deploy: trade-off accepted.
- ⚠️ `connect-src` whitelist API Anthropic explícito · si se añade otro
  LLM provider futuro (OpenAI etc) requiere update CSP_DIRECTIVES.

## Referencias

- `backend/app/middleware/csp.py` · CSPMiddleware + CSP_DIRECTIVES
- `backend/app/main.py` · `app.add_middleware(CSPMiddleware)` post-CORS
- `backend/tests/middleware/test_csp.py` · 9 tests cobertura
- TODO-SEC-CSP-001 · CERRADO 2026-05-04 SAN-B.MB-7.3
- https://content-security-policy.com/ · referencia directives
- https://web.dev/csp/ · best practices Google

---

# ADR-034 — Frontend wire-up obligatorio per atom

## Status

Aceptada · Sesión 11 SAN-C MB-9.bis (5 mayo 2026) · IMPLEMENTADA

## Contexto

El mega-bloque SAN-C.MB-9 (BLOQUEANTES pre-cliente real) entregó 5
endpoints backend funcionales (refuerzos seed, distintivo + declaración
809, PdA 806, Manual SGSI + Plan Director 805, validación roles ENS 801)
sin integrar UI frontend correspondiente. Resultado: **4 fantasmas
backend latentes** detectados al revisar la entrega bulk antes de
arrancar SAN-C.MB-10.

Los fantasmas violaban el principio invariante "0 fantasmas backend sin
trigger UI" enunciado en SAN-B y reafirmado en el audit post-Bloque 3
v2 EXHAUSTIVO. Deuda silenciosa que requiere sesión adicional MB-9.bis
(5 atoms · 5-8h reales) para cerrar.

Adicionalmente, durante MB-9.bis.0 pre-flight se detectó un bug latente
en MB-9.2: dos endpoints `/declaration/generate` registrados en el
mismo router (paso5 JSON + MB-9.2 DOCX), con FastAPI ignorando el
segundo. Indicador adicional de que el split backend-only sin trabajar
la UI permite que side-effects de routing pasen sin detectar.

## Decisión

A partir de SAN-C MB-10 (IMPORTANTES), **todo atom que crea o modifica
un endpoint backend debe incluir el frontend wire-up correspondiente en
el mismo commit, o en un atom hermano consecutivo dentro del mismo
mega-bloque · nunca diferido a una sesión posterior**.

Briefings deben listar explícitamente la integración frontend per atom
(API client method · component · ruta de integración · E2E smoke test).
El V-CHECK per atom incluye:

- `npx tsc --noEmit` 0 errors
- E2E smoke mínimo (1 test que verifica que la página objetivo no rompe
  SSR con el nuevo componente)
- Verificación grep: el component nuevo está usado en al menos 1 page

El STOP-report bulk del mega-bloque debe incluir la métrica obligatoria
**"fantasmas backend = 0"** verificada con grep cross-file. Approval
bulk no procede sin esa verificación.

## Consecuencias

- ✅ Cero fantasmas backend al cerrar mega-bloque · cliente UI completa
  desde día 1 de cualquier endpoint nuevo.
- ✅ Bugs cross-cutting (route collision, 401 unexpected, signature
  mismatch) se detectan en el atom que los introduce, no en una
  auditoría posterior.
- ✅ Tiempo total mega-bloque más predictible · sin sesiones .bis ad-hoc
  bombardeando el plan SAN-C.
- ⚠️ Atoms backend serán ~30-50 % más grandes (incluyen TS + tests E2E).
  Trade-off accepted para cumplir principio invariante.
- ⚠️ Briefings autores deben investigar API client patterns + component
  conventions del codebase antes de redactar el atom (más overhead pero
  evita sorpresas durante ejecución).

## Lección operacional

Separar backend/frontend en briefings de mega-bloques invita a deuda
silenciosa. Los wire-ups "después" se quedan crónicamente pendientes y
normalizan el estado fantasma como aceptable.

## Referencias

- SAN-C.MB-9 (commits b3e13c0 · b7f8a49 · 46acd21 · 62aff73 · 6b4a83f) ·
  5 endpoints backend creados sin UI · origen del problema.
- SAN-C.MB-9.bis (commits fb19573 · bcc3442 · d2ca2a6 · 9a4c419 · ab250cc) ·
  cierre 4 fantasmas + fix collision route + ADR-034 documenta lección.
- TODO-MB-9-FRONTEND-WIRE-UP-001 · CERRADO 2026-05-05 SAN-C.MB-9.bis bulk.
- TODO-S11-ENS-DATA-CANONICAL-DEFER-001 · CERRADO 2026-05-05 SAN-C.MB-9.1.

## Refuerzo v2 — SAN-C MB-11 (5 mayo 2026)

### Contexto

Tras cerrar MB-10 + MB-10.bis se detectaron 2 bugs cross-cutting del
mismo género que ADR-034 v1 buscaba prevenir:

- **MB-9.2 collision route** · dos endpoints `/declaration/generate`
  registrados (paso5 JSON + DOCX), FastAPI ignoró el segundo. Pasó
  tsc + grep textual + Playwright SSR. Solo detectado en wire-up
  frontend cuando el API client pegó al endpoint silencioso y obtuvo
  el shape inesperado.
- **MB-10.1 + MB-10.8 paths frontend mismatched** · API client
  apuntaba a paths que el router backend no exponía exactamente
  (prefix `/document-factory` inexistente). Pasó tsc + Playwright
  SSR + grep. Solo cazado con curl real contra uvicorn live
  retornando 404 (commit e60bb01).

ADR-034 v1 obligaba a wire-up frontend en mismo commit y E2E smoke.
**Insuficiente**: tsc valida tipos pero no rutas registradas; Playwright
SSR valida que la página renderiza pero no que el endpoint exista
realmente; grep valida presencia textual pero no consistencia
path↔registro FastAPI.

### Decisión (refuerzo)

V-CHECK obligatorio per atom backend (NO opcional · NO diferido)
extiende v1 con dos checks empíricos adicionales:

1. Unit test passing.
2. Frontend wire-up en mismo commit (ADR-034 v1).
3. **🆕 Smoke curl con uvicorn live** · cada endpoint nuevo o modificado
   se golpea con `curl -s -o /dev/null -w "%{http_code}"` contra el
   server live · status esperado 2xx (success path) o 4xx específico
   (auth/validation/not-found-de-recurso) · **NUNCA 404 routing** ·
   **NUNCA collision route silenciosa** (segundo registro ignorado).
4. **🆕 Frontend api client path matched** · cada path declarado en
   `frontend/lib/api/*.ts` debe matchear exactamente un endpoint
   registrado vía
   `git grep -nE "@router\.(get|post|put|delete|patch)" backend/app/`.
   Verificación grep cross-file obligatoria pre-commit.
5. `npx tsc --noEmit` 0 errors.
6. E2E smoke (Playwright SSR mínimo).

### Consecuencias

- ✅ Bugs `route-collision` y `path-mismatch` detectados en el atom
  que los introduce, antes de cerrar mega-bloque.
- ✅ Métrica nueva al cierre mega-bloque: **"endpoints con 404 routing
  = 0"** verificada con smoke curl batch sobre el delta de endpoints
  del bloque.
- ✅ Cierra el modo de fallo donde tsc + Playwright + grep están verdes
  pero el endpoint no existe en runtime.
- ⚠️ Atoms backend requieren uvicorn live durante ejecución V-CHECK
  (no solo pytest aislado). +5-10 min overhead per atom.
- ⚠️ Selective staging implica que el batch smoke curl debe correr
  antes de `git add` para evitar commit con endpoint roto.

### Lección operacional

Type-checking + SSR rendering + grep textual son verificadores
necesarios pero no suficientes para wire-up correcto. La única
verificación dura es golpear el endpoint live. Si el status code no
es el esperado, hay bug — incluso si tsc + Playwright están verdes.
2 incidentes del mismo género en 2 mega-bloques consecutivos = patrón,
no accidente.

### Referencias

- SAN-C.MB-9.bis (commit fb19573 fix collision route) · primer
  incidente · cazado vía wire-up frontend.
- SAN-C.MB-10.bis (commit e60bb01 fix paths frontend) · segundo
  incidente · cazado vía smoke curl uvicorn live.
- TODO-MB-11-VCHECK-V2-001 · CERRADO 2026-05-05 SAN-C.MB-11.0.

## ADR-035 · Sistema vivo guiado cronológico (post-SAN-D MB-13)

**Fecha**: 2026-05-06
**Status**: Adoptada
**Stakeholders**: Marcos Mata (decisor) · Claude (arquitecto)
**Supersedes parcial**: complementa ADR-026 (10 fases lifecycle) +
ADR-034 v2 (V-CHECK reforzado wire-up). No supersede.

### Contexto

Marcos directiva post-SAN-C cierre (HEAD `4f1bc22` ·
tag `s12-fase-13-san-c-precliente-cerrada`): sistema FULKRO debe
ser usable por persona sin conocimiento ENS · todo guiado paso a
paso · adaptado dinámicamente per categoría B/M/A + arquetipo
PYME · cliente con tareas explícitas · scoring realista madurez
con alertas proactivas que avisan a Marcos antes de que algo se
rompa.

Audit empírico SAN-D pre-briefing (251 líneas paths verificados)
detectó que la base existe en backend pero NO está expuesta como
UX viva guiada:

- `get_next_actions()` existe en `workflow_state.py:285` pero el
  endpoint `/api/v1/workflow/next-actions/{project_id}` solo se
  consume en tab `/roadmap` aislado. Marcos no recibe "haz esto
  AHORA" en home dashboard del proyecto.
- `calculate_readiness_score()` existe en
  `m09_audit_prep/checklist_service.py:678` con lógica completa
  (entregables · evidencias · contradicciones · firmas) pero
  retorna snapshot on-demand sin SSE/WS. UI no refresca cuando
  cambia estado proyecto.
- 10 Celery beat tasks ejecutan en `core/celery_app.py:47-104`
  (M23 retainer overdue · M07 evidence stale · M25 grace period ·
  M29 client digest) pero no hay endpoint UI que retorne alertas
  activas al admin.
- Layout admin proyecto tiene 31 tabs paralelos sidebar
  (`frontend/app/(admin)/admin/projects/[id]/`) sin "Fase X de
  10" header como elemento estructural visible.
- `frontend/app/(admin)/admin/projects/[id]/page.tsx` actual
  redirige a `/summary` · no renderiza nada propio en home.

### Decisión

A partir de SAN-D MB-13, FULKRO adopta arquitectura "sistema vivo
guiado cronológico" con 7 principios:

1. **NextActionCard siempre visible top-of-page** en
   `/admin/projects/{id}` (rediseño home). Refresca via SSE +
   baseline polling 30s. CTA primario visible · descripción
   clara · estimación tiempo (`estimated_minutes`) · badges
   urgent/blocking según priority.

2. **PhaseProgressWizard horizontal** con 10 fases lifecycle
   canonical (`WorkflowPhase` enum ADR-026 + SAN-C MB-11.1).
   Stepper visual: ◯─◯─◉─◯─◯ con fase actual highlighted.
   Completed = check verde · current = ring primary · future =
   lock muted. Click navega a tab fase (current/past) · futuras
   bloqueadas.

3. **Renderizado condicional per categoría** B/M/A en UI
   (implementado MB-17). Hook `useCategoryFilter(category,
   feature)` + Context provider `ProjectCategoryContext`. Cliente
   BASICA NO ve tabs Pentest CPSTIC ni Productos certificados
   (no aplican); cliente ALTA SÍ ve obligatoriamente
   pentest workflow + cripto 807.

4. **Renderizado condicional per arquetipo PYME**
   (implementado MB-17). Hook `useArchetypeFilter(archetype,
   feature)` + Context provider `ProjectArchetypeContext` ·
   reusa `Project.archetype` (SAN-C MB-11.6 · 6 arquetipos PYME
   formal classification).

5. **Trigger automático scoring event-driven** (implementado
   MB-13.3). Cada cambio de estado crítico (Asset · MageritThreat
   · MeasureImplementation · Evidence · Project.fase) dispara
   SQLAlchemy event listener → SSE `readiness_changed` → frontend
   invalida queries TanStack → UI auto-refresca sin F5. NO
   polling de baseline >30s para datos críticos.

6. **Notificación cliente canal apropiado** (implementado
   MB-16). `ContactPreference` per cliente · email/SMS/WhatsApp
   según preferencia · deep-link a tarea específica portal.
   Modelo descartado tras decisión Marcos: Stripe · Redsys ·
   Twilio · Meta WhatsApp Business API. Modelo vigente: Postmark
   email + wa.me link opcional + transferencia bancaria manual.

7. **AlertBell top nav admin** (implementado MB-13.4) ·
   tabla `alert_queue` + `AlertService` · count alertas activas
   con badge · click abre dropdown con CTA per alert. Severity
   info/warning/critical · categorías bienal_art31 ·
   payment_overdue_aapp · client_inactivity · evidence_stale ·
   workflow_blocked · audit_due · rgpd_72h · etc.

### Consecuencias

**Backend:**

- Nuevas tablas: `alert_queue` (MB-13.4) ·
  `client_tasks` (MB-14) · `notification_events` (MB-16).
- Nuevos services aglutinadores: `ProjectDashboardService`
  (MB-13.1 · M21 namespace · combina next-actions + readiness +
  alerts + phase + estimated_days_to_certification) ·
  `task_generator` (MB-14) · `notification_dispatcher` (MB-16).
- SQLAlchemy event listeners en modelos críticos
  (MB-13.3): Asset · MageritThreat · MeasureImplementation ·
  Evidence · Project.fase.
- SSE dispatcher singleton in-memory pub-sub (MB-13.3 ·
  Redis-ready scaling) + endpoint
  `/api/v1/projects/{id}/events`.
- 3 nuevas Celery beat tasks (MB-13.4):
  `check_biannual_audits_due` (daily 08:00 art.31 RD 311/2022) ·
  `check_aapp_payment_overdue` (daily 09:00 Ley 3/2004) ·
  `check_client_inactivity` (Mondays 10:00 portal idle >14d).

**Frontend:**

- Rediseño home admin proyecto (MB-13.5):
  `frontend/app/(admin)/admin/projects/[id]/page.tsx` deja de ser
  redirect a `/summary` y pasa a renderizar primary fold
  (PhaseProgressWizard + NextActionCard) + secondary fold
  (ReadinessScoreCard + ActiveAlertsCard +
  UpcomingMilestonesCard) + ProjectSecondaryTabs preserva
  navegación detalle.
- 5+ components nuevos MB-13 + más en MB-14/15/16/17.
- Hook `useProjectEvents` para SSE (3 events: readiness_changed
  · phase_changed · alert_new) con auto query invalidation
  TanStack Query.
- Context providers `ProjectCategoryContext` +
  `ProjectArchetypeContext` (MB-17).

**Operacional:**

- ADR-034 v2 reforzado: cada feature backend MB-13 → MB-19
  incluye UI guiada wire-up en mismo commit (no diferido).
- V-CHECK per atom incluye verificación SSE funcional
  (smoke curl `/events` endpoint · auth 401 NO 404 routing).
- V-CHECK frontend coherence reglas duras anti-drift visual:
  0 hex hardcoded · solo theme tokens (CSS variables fulkro-*
  + aliases shadcn) · solo scale Tailwind spacing/typography ·
  reuso shadcn/ui existing · iconos solo lucide-react.
- Tag intermedio per mega-bloque para rollback granular:
  `s13-mb13-orquestador-vivo-cerrado` (MB-13) ·
  `s14-mb14-portal-cliente-cerrado` (MB-14) · etc.

### Lección

Backend completo + UI condicional dinámica = "sistema vivo".
Sin orquestación frontend que aglutine y exponga (NextActionCard
home + PhaseProgressWizard + AlertBell + SSE event-driven), el
backend permanece invisible para usuario final aunque sus
endpoints estén verdes y sus tests pasen.

Lección estructural complementaria a ADR-034: el "wire-up
frontend" no es solo route↔endpoint match (ADR-034 v2) sino
también "agregación cross-motor en UX viva donde el usuario la
necesita" (ADR-035).

### Referencias

- audit_empírico_san_d.md (251 líneas · paths verificados ·
  secciones 1.1-1.4 + 2.3-2.4 + 8.1-8.4).
- `backend/app/core/workflow_state.py:285` ·
  `get_next_actions()` existing.
- `backend/app/core/workflow_phase.py` · `WorkflowPhase` enum
  10 fases canonical.
- `backend/app/motors/m09_audit_prep/checklist_service.py:678` ·
  `calculate_readiness_score()` existing.
- `backend/app/core/celery_app.py:47-104` · 10 Celery beat tasks
  existing (sin endpoint UI hasta MB-13.4).
- `backend/app/models/core.py:40` · `Project` model con campos
  `fase` · `categoria_objetivo` · `archetype` · `lifecycle_state`.
- TODO-MB-13-ADR-035-DOC · ABIERTO MB-13.0 ·
  CERRADO MB-13.0 commit (este).

### Deferrables MB-13 documentados (no son deuda)

Componentes/tasks omitidos en MB-13 MVP por dependencias técnicas
naturales en mega-bloques posteriores:

- **UpcomingMilestonesCard** → MB-18 (depende `MilestoneFactory` ·
  motor M14 contracts + M15 billing milestone schedules · no existe
  en SAN-C cierre).
- **RecentActivityCard** → MB-14 (depende audit log granular cliente ·
  hash chain ClientUserAudit pendiente · MB-14.1).
- **AlertsPanel `/admin/alerts/page.tsx` dedicado** → MB-14 (cubierto
  funcionalmente por AlertBell + Popover en Header.tsx · panel
  dedicado con filtros severity + category llega con portal cliente
  workspace MB-14).
- **Celery `payment_overdue_aapp`** → MB-18 (pertenece M15 billing ·
  factura AAPP retrasada Ley 3/2004 · interés legal acumulado).
- **Celery `client_inactivity`** → MB-14 (pertenece M21 portal
  cliente · join `ClientUserAudit` cross-project agregación ·
  requiere portal cliente activo).
- **ProjectSecondaryTabs** → no requerido. Audit empírico SAN-D
  confirma sidebar admin existing (`Sidebar.tsx`) + sub-routes
  `/admin/projects/[id]/{summary,plan,risks,…}` cubren navegación
  detalle. El bug arquitectónico era ausencia de wizard-first home
  agregando cross-motor (resuelto MB-13.5), no la sidebar misma.

Lista cerrada en commit MB-13 cierre real (`00d7587`). Si surge
necesidad de adelantar alguno, requiere ADR nuevo o extensión
ADR-035 explícita · NO ad-hoc.

## ADR-036 · UI condicional per categoría B/M/A + arquetipo PYME (SAN-D MB-17)

**Fecha**: 2026-05-06
**Status**: Adoptada
**Stakeholders**: Marcos Mata (decisor) · Claude (arquitecto)
**Complementa**: ADR-026 (10 fases lifecycle) · ADR-034 v2 (V-CHECK
wire-up) · ADR-035 (sistema vivo guiado cronológico, principios 3+4
delegados aquí). No supersede.

### Contexto

Audit empírico SAN-D pre-briefing MB-17 confirma:

- `grep categoria.*basica` en frontend prácticamente nulo · UI no
  filtra per categoría ENS B/M/A.
- Cliente Básica recibe tabs `Pentest` · `Red Team` · `Productos
  CPSTIC` que no aplican a su categoría (ENS RD 311/2022 anexo II
  §3.3 medidas reforzadas solo MEDIA+/ALTA).
- Cliente Alta NO recibe destaque obligaciones específicas (CPSTIC
  CCN-STIC 105/140 · criptografía 807 · Red Team E-704).
- Cero renderizado condicional per arquetipo PYME (sector salud ·
  saas only · desarrollador AAPP · etc) pese a `Project.archetype`
  existing (SAN-C MB-11.6 · 7 arquetipos).
- Workflow puede llegar a `CONFORMIDAD` (fase 9) sin auditor ENAC
  asignado (Media) o sin pentest CPSTIC ejecutado (Alta) · sin
  bloqueo previo.
- Templates `M06 document_factory` no varían per arquetipo: PSI
  sector salud no destaca art.9 RGPD · PSI saas only no skip
  `mp.if instalaciones físicas`.

Marcos directiva: "todo adaptado per cliente · per categoría · per
arquetipo · UI muestra solo lo aplicable · workflow bloquea si
falta algo obligatorio".

### Decisión

A partir de SAN-D MB-17, FULKRO adopta arquitectura UI condicional
declarativa con 8 principios:

1. **Feature flags YAML catalog declarativo** ·
   `backend/app/core/feature_flags/categoria_archetype_features.yaml`
   define per feature: `applicable_categories` + `applicable_archetypes`
   + `required_for_phase` + `blocks_phase_transition_if_missing` +
   `requires_employee_count`. Source of truth backend + frontend
   (TS types lowercase coinciden con enum values reales).

2. **Hooks React condicional render** ·
   `useCategoryFilter({projectId, feature|category})` y
   `useArchetypeFilter({projectId, feature|archetype})` consumen
   endpoint `GET /api/v1/projects/{id}/feature-flags`. TanStack
   Query staleTime 60s · cache compartido vía
   `ProjectFeaturesProvider`.

3. **Components wrapper condicional** · `<CategoryGate>` y
   `<ArchetypeGate>` envuelven secciones UI · renderizan
   `children` solo si feature aplica al proyecto. Composición
   shadcn pura (no styling propio).

4. **Backend dependencies** · `require_feature(key)` ·
   `require_category(list)` · `require_archetype(list)` ·
   raise `403 Forbidden` si feature/categoría/arquetipo no
   aplica al proyecto. Aplicadas a endpoints sensibles M08
   (cloud-audit · pentest CPSTIC) y M21 (red team).

5. **Navegación admin condicional** · `ProjectTabs` existing
   (`frontend/components/project/ProjectTabs.tsx`) extendido
   con metadata `feature?` / `categories?` / `archetypes?` por
   tab · filtrado reactivo. NO se crea sub-sidebar paralelo.
   Banner contextual ENS+arquetipo va en `ProjectHeader`
   existing (Card top de página).

6. **Client-portal condicional** · `ClientSidebar` existing
   (`frontend/components/layout/ClientSidebar.tsx`) extendido
   con metadata feature flags. `CategoryBanner` color-coded
   (fulkro-success/warning/danger) en home cliente con
   descripción específica per categoría (autoevaluación 809
   Básica · auditoría ENAC Media · pentest CPSTIC Alta).
   Banner Sector Salud usa `bg-fulkro-warning/10` con icon
   `Stethoscope` lucide · semántica obligaciones reforzadas
   (art.9 RGPD · Ley 41/2002 · DPIA obligatoria).

7. **Workflow blocking rules** · `WorkflowBlockingService`
   valida transitions con feature flags. Endpoint
   `GET /projects/{id}/workflow/can-transition/{phase}`
   retorna `can_transition` + `blocking_issues[]` con
   `feature_key` + `description` + `fix_url` mapeado a route
   existing. UI `WorkflowBlockingAlert` destacado destructive
   en home admin · lista issues con CTA "Resolver".

8. **Templates específicos per arquetipo** ·
   `TemplateResolver` con `VARIANT_MAPPING` feature_key →
   suffix. PSI variantes creadas: `_sector_salud` (art.9 RGPD
   reforzado · Ley 41/2002 · LOPDGDD DA1ª/DA7ª) · `_saas_only`
   (skip `mp.if instalaciones` · op.ext reforzado · CCN-STIC
   823) · `_desarrollador_aapp` (CRA + SDLC seguro · mp.sw
   reforzado R1). Path resolution absoluta vía
   `Path(__file__).parent / "templates"` (no relativa CWD).

### Consecuencias

**Backend**:

- Nuevo módulo `backend/app/core/feature_flags/` con `__init__.py`
  (loader + 4 helpers · lru_cache) · `api.py` (2 endpoints) ·
  `dependencies.py` (3 deps).
- Nuevo módulo `backend/app/core/workflow_blocking_service.py` ·
  `WorkflowBlockingService` valida transitions. Solo GET
  `/can-transition` esta sesión · POST `/transition` deferrable
  (DEC-5 · MB-18 hook AutoBillingService).
- Templates M06 con variantes per arquetipo en
  `backend/app/motors/m06_document_factory/templates/policies/`
  + `template_resolver.py` con `VARIANT_MAPPING`.
- `pyproject.toml` añade `pyyaml` si no presente (verificar
  durante atom 17.1).

**Frontend**:

- `frontend/lib/feature-flags.types.ts` · TS types lowercase
  matching `PymeArquetipo` enum real (`saas_only` · `sector_salud`
  · etc).
- `frontend/lib/api/feature-flags.ts` · API client TanStack
  Query.
- `frontend/lib/hooks/useCategoryFilter.ts` +
  `useArchetypeFilter.ts`.
- `frontend/lib/contexts/ProjectFeaturesContext.tsx` ·
  Provider compartido.
- `frontend/components/feature-flags/CategoryGate.tsx` +
  `ArchetypeGate.tsx`.
- `frontend/components/dashboard/WorkflowBlockingAlert.tsx`
  destacado destructive Card.
- `frontend/components/conformity/ConformityWizard.tsx` ·
  12 steps adaptados per categoría · render inline (no
  sub-routes dedicadas · DEC-routes-mapping).
- `ProjectTabs` y `ClientSidebar` extendidos (NO componentes
  paralelos).
- 4 E2E suites stack real Playwright per categoría B/M/A +
  arquetipo SECTOR_SALUD.

**Operacional**:

- ADR-034 v2 vigente: cada feature backend + UI condicional
  juntos en mismo commit per atom.
- V-CHECK per atom incluye visual coherence greps (0 hex
  hardcoded · solo fulkro palette · solo shadcn · solo
  lucide).
- Mapping `WorkflowPhase.ordered()` 1-indexed · helper
  `phase_int_to_enum(n)` en `feature_flags/__init__.py`.

### Lección

Sin UI condicional · sistema NO es "vivo guiado per cliente":
muestra info no aplicable · confunde · NO genera confianza
profesional. Backend ya sabía la categoría/arquetipo · faltaba
que UI lo usara.

Lección complementaria a ADR-035: el "sistema vivo cronológico"
(NextActionCard + PhaseProgressWizard + AlertBell + SSE) requiere
también filtrado contextual per cliente para ser usable. Cliente
Básica viendo Pentest tab confunde tanto como Cliente Alta sin
banner CPSTIC obligatorio.

### Referencias

- audit empírico SAN-D · secciones 1.3 + 1.4 + 8.1-8.4.
- `backend/app/motors/m01_categorization/pyme_archetypes.py` ·
  7 arquetipos `PymeArquetipo` (SAN-C MB-11.6).
- `backend/app/core/workflow_phase.py` · 10 fases canonical.
- `backend/app/motors/m22_discovery/magerit_categories.py` ·
  9 categorías MAGERIT.
- `backend/app/models/core.py:53` · `Project.categoria_objetivo`.
- `backend/app/models/core.py:69` · `Project.archetype` +
  `archetype_confidence`.
- `backend/app/models/core.py:28` · `Client.numero_empleados`
  (DEC-1 resolved).
- TODO-MB-17.0-ADR-036-DOC · ABIERTO MB-17.0 · CERRADO commit
  atom 17.0.

### Deferrables MB-17 documentados (no son deuda)

Componentes/decisiones omitidos en MB-17 MVP por dependencias
técnicas naturales en mega-bloques posteriores. Lista cerrada al
cierre tag `s13-mb17-ui-adaptativa-cerrada`. Si surge necesidad de
adelantar alguno, requiere ADR nuevo o extensión ADR-036 explícita
· NO ad-hoc.

**DEC-2 · `Asset.cpstic_certified` field schema**

Briefing usa `Asset.cpstic_certified == True` para validar que
inventario tiene productos CPSTIC certificados (Categoría ALTA ·
CCN-STIC catálogo). Field NO existe en schema actual `assets`
(m22_discovery + m02_magerit).

Diferido a: scope MB-19+ inventory enrichment · o nuevo modelo
`CpsticProduct` autocontenido referenciado por `Asset` 1-N.

Implementación interim MB-17.5: `_is_feature_completed("alta_productos_cpstic")`
retorna `False` con `# Future: cpstic_certified field requires
schema migration · scope MB-19+ inventory enrichment`. Cliente
Alta nunca pasa gate Conformidad hasta que field exista (safe
default · UI bloqueante visible). NO migration esquema en MB-17.

**DEC-3 · `VerificationEngagement` → `VerificationRun` adaptación**

Briefing referencia `VerificationEngagement` con field
`engagement_type='pentest_cpstic'`. Modelo real es
`VerificationRun` (m08_verification/models.py) con `category`
(BASICO|MEDIO|ALTO) + `mode` (internal|external_handoff|
external_ingest_pdf|external_ingest_form) + `status`.

Adaptación MB-17.5: query `VerificationRun WHERE project_id=X AND
category='ALTO' AND mode LIKE 'external_%' AND status='completed'`
cubre semántica "pentest CPSTIC ejecutado por pentester
acreditado". No nuevo modelo.

**DEC-4 · `Evidence.evidence_type` field**

Modelo real `Evidence` (`backend/app/models/documents.py`) tiene
`evidence_type_id: String(80)` + `tipo: String(50)` + `nombre_tipo:
String(120)`. Briefing's `Evidence.evidence_type` mapea a
`evidence_type_id`.

Implementación MB-17.5 usa field real. Si valor canonical
`criptografia_807` no está catalogado en `EvidenceTypesCatalog`
M07, evidencia nunca se registra con ese tipo y check retorna
False (safe default · UI bloqueante).

**DEC-5 · `transition_phase` centralizado**

Briefing referencia `from app.core.workflow_state import
transition_phase` que NO existe. Existing transitions están
fragmentadas: `m25_lifecycle.lifecycle_service.transition`
(lifecycle_state) · `m27_conformity` machines (route +
submission).

Diferido a: MB-18 hook `AutoBillingService` que centraliza
transitions con event listener `Project.fase` change.

Implementación MB-17.5: solo endpoint `GET /workflow/can-transition/{phase}`
para UI alert. POST `/transition` NO se implementa esta sesión ·
transición física se hace por motor existente (M25 lifecycle ·
M27 conformity · UPDATE manual via admin endpoint existing).

**DEC-1 · `Client.numero_empleados` field (RESOLVED)**

Field existe en `Client` model (`backend/app/models/core.py:28`)
como `numero_empleados: Mapped[int | None]`. Helper
`is_feature_applicable` lee vía eager load
`project.client.numero_empleados` cuando `requires_employee_count`
se evalúa (feature `pce_nis2`). Sin migration adicional.

**Routes mapping (sub-routes dedicadas diferidas)**

Briefing referencia rutas que NO existen como pages dedicadas.
ConformityWizard renderiza 12 steps inline · sub-routes diferidas
a MB-19+ si scope ampliado las requiere. fix_url en
WorkflowBlockingService mapea a routes existing con query params
o anchors:

| Briefing | Existing equivalent (MB-17 mapping) |
|---|---|
| `/projects/{id}/categorization` | `/projects/{id}/diagnosis` |
| `/projects/{id}/cloud-audit` | `/projects/{id}/audit` |
| `/projects/{id}/audit-prep` | `/projects/{id}/audit` |
| `/projects/{id}/contacts?role=auditor_externo` | `/projects/{id}/roles?role=auditor_externo` |
| `/projects/{id}/evidencias` | `/projects/{id}/evidence` |
| `/projects/{id}/dda` | `/projects/{id}/obligations` |
| `/projects/{id}/conformity/{declaration\|self-assessment\|badge}` | `/projects/{id}/conformity` (inline wizard) |
| `/projects/{id}/ines` | `/projects/{id}/conformity` |
| `/projects/{id}/pentest` | `/projects/{id}/verification?focus=pentest_cpstic` |
| `/projects/{id}/red-team` | `/projects/{id}/verification?focus=red_team` |
| `/projects/{id}/cpstic-products` | `/projects/{id}/verification?focus=cpstic_products` |
| `/projects/{id}/rgpd-art9` | `/projects/{id}/obligations?regulation=rgpd_art9` |
| `/projects/{id}/pce-univ` | `/projects/{id}/obligations?regulation=pce_univ` |
| `/projects/{id}/dora` | `/projects/{id}/obligations?regulation=dora` |
| `/client-portal/conformity` | `/client-portal/workflow#conformity` |
| `/client-portal/audit-progress` | `/client-portal/workflow` |
| `/client-portal/tasks` | `/client-portal/workflow` |
| `/client-portal/pentest-status` | `/client-portal/workflow?focus=pentest` |

**Inline policy**: 0 TODO/FIXME inline · todo deferrable usa
`# Future:` con session ref (`SAN-D MB-17.X-DEFERRED`).

## ADR-037 · AI Auditor pro contextualizado + threat profundo Magerit Libro II (SAN-D MB-15)

**Fecha**: 2026-05-06
**Status**: Adoptada
**Stakeholders**: Marcos Mata (decisor) · Claude (arquitecto)
**Complementa**: ADR-026 (10 fases lifecycle) · ADR-034 v2 (V-CHECK
wire-up) · ADR-035 (sistema vivo guiado cronológico) · ADR-036 (UI
condicional · DEC-2/3/5 deferrables). No supersede.

### Contexto

Audit empírico SAN-D pre-briefing MB-15 + STOP-1 pre-implementación
confirmaron divergencias arquitectónicas entre briefing v2 y repo
real. El briefing asumió arquitectura "ideal" sin conocer:

- **M10 audit_simulator** existing en `backend/app/motors/m10_audit_sim/`
  evalúa 58 preguntas ENAC determinísticas L0-L5 contra evidencia real
  (M03 DdA + M07 evidencias + M08 pentest). Banco de preguntas vive en
  `m10_audit_sim/audit_questions.py`.
- **A11 Auditor Virtual** (`agent_11_auditor_virtual.py`) es **capa
  senior por encima de M10**. Toma `AuditSimulationRun` result + client
  context + produce PAC sector-aware + 3-5 preguntas sectoriales + 
  narrativa ejecutiva 400-600 palabras.
- **Magerit catalog/assessment split**: `MageritThreat` es catálogo
  oficial Libro II (code, name, group_code, affected_asset_types,
  affected_dimensions); `MageritThreatAssessment` per-(analysis, asset,
  threat) con probability + degradation; `MageritAnalysis` cabecera
  por proyecto.
- **VerificationRun** real (no `VerificationEngagement`): category
  (BASICO/MEDIO/ALTO) + mode (internal/external_handoff/...).
- **Magerit Libro II yamls existing**: 2 archivos en `docs/` con 57
  amenazas oficiales NIPO 630-12-171-8.

Marcos directiva post-MB-13/17: "AI auditor profesional formula
preguntas con contexto proyecto · responde directamente · debe cubrir
todo para cuando llegue auditoría · pentester autónomo contratado para
Alta · mapeo amenazas Media/Alta más profundo".

### Decisión

A partir de SAN-D MB-15, FULKRO adopta arquitectura "AI Auditor pro
+ threat profundo" reusando infrastructure existing con 6 principios:

1. **AuditDryRunService = orchestrator M10+A11** (no 58 LLM calls)
   - Trigger M10 `AuditSimulatorService.run_simulation` → 58
     `AuditSimulationFinding` rows L0-L5 deterministas matching
     evidencia real proyecto.
   - Trigger A11 `agent_11_wrapper /run-supplementary-audit` con
     `m10_run_id` → produces PAC priorizado + sectoriales + narrativa.
   - Persistir `audit_dry_run_results` (project_id + métricas
     agregadas + payload combinado M10+A11) para histórico
     comparable.
   - Coste compute: 1 batch determinista M10 + 1 LLM call A11
     (vs 58 LLM calls del briefing literal · 50× ahorro).

2. **Magerit Libro II loader reusa yaml existing**
   - `backend/app/motors/m02_magerit/libro_ii_loader.py` apunta a
     `docs/magerit_catalog/threats.yaml` (57 amenazas oficiales con
     fields code/name/description/asset_types/dimensions/typical_frequency
     que mapean directamente a `MageritThreat` model).
   - NO crear tercer yaml en `m02_magerit/`. Single source of
     truth.

3. **ThreatAutoMapper crea MageritThreatAssessment rows**
   - Per asset (`MageritAsset` real) lookup amenazas catalog por
     `affected_asset_types` matching `MageritAsset.asset_type_code`.
   - Crear `MageritThreatAssessment(analysis_id, asset_id,
     threat_code, probability, degradation_d/i/c/a/t)` con defaults
     derivados de `typical_frequency` (yaml) + categoría (BASICA/
     MEDIA/ALTA).
   - Skip si assessment ya existe.

4. **PentestAutoTrigger crea VerificationRun**
   - Trigger cuando `Project.fase == 'implantacion'` (fase 6) +
     `categoria_objetivo == 'ALTA'` + ≥1 amenaza con probability
     `A` o `MA` (alta o muy alta).
   - Crea `VerificationRun(category='ALTO', mode='external_handoff',
     status='pending', scope_jsonb={ccn_stic_105: True, ccn_stic_140:
     True, auto_generated: True})`.
   - Hook = SQLAlchemy event listener on `Project.fase` change
     (pattern MB-13.3 dashboard_events) + endpoint manual evaluate
     re-evaluación. NO `transition_phase` helper (DEC-5 ADR-036
     diferido a MB-18).

5. **AlertService.trigger_alert con categorías existing**
   - Dry-run gaps críticos → `category='audit_due'` severity
     `warning`/`critical` según count.
   - Pentest CPSTIC required → `category='audit_due'` severity
     `warning`. NO expandir `_VALID_CATEGORIES` (overkill · semánticamente
     `audit_due` cubre).

6. **UI AuditDryRunDashboard muestra M10 + A11 combinados**
   - 58 `AuditSimulationFinding` (L0-L5) con badges `fulkro-success`
     (L4-L5) / `fulkro-warning` (L2-L3) / `fulkro-danger` (L0-L1).
   - A11 narrative + PAC + preguntas sectoriales como Cards.
   - GapAnalysisCard destaca findings L0/L1 + A11 critical gaps.
   - QuestionsAnsweredList con filtros (todas / con evidencia / gaps
     / críticos).
   - Integración página `/admin/projects/{id}/audit-dry-run/`.

### Consecuencias

**Backend**:

- Nuevo service `AuditDryRunService` orchestrator (NO inventa LLM
  calls · usa M10 + A11 wrapper existing).
- Nueva tabla `audit_dry_run_results` (histórico métricas agregadas).
- Nuevo módulo `m02_magerit/libro_ii_loader.py` apuntando a yaml
  existing en `docs/magerit_catalog/threats.yaml`.
- Nuevo service `ThreatAutoMapper` que crea `MageritThreatAssessment`
  rows.
- Nuevo service `PentestAutoTrigger` + SQLAlchemy event listener
  on `Project.fase` change.
- Nuevo endpoint `POST /projects/{id}/audit-dry-run/execute` ·
  `GET /summary` · `GET /results/{id}`.
- Nuevo endpoint `POST /projects/{id}/threats/auto-map`.
- Nuevo endpoint `POST /projects/{id}/pentest/auto-trigger-evaluate`.

**Frontend**:

- API clients `audit-dry-run.ts` + extension `workflow.ts` (existing).
- 4 components nuevos: `AuditDryRunDashboard` ·
  `QuestionsAnsweredList` · `GapAnalysisCard` ·
  `M10FindingsTable`.
- Página `/admin/projects/{id}/audit-dry-run/`.
- Visual coherence ADR-035 + TRAD-9 ADR-036: solo fulkro palette ·
  shadcn Card composition · lucide icons · 0 hex hardcoded.

**Operacional**:

- ADR-034 v2 cumplido per atom (backend + UI same commit).
- V-CHECK reforzado: Playwright admin specs stack real verde · NO
  deferrable (lección MB-13/17).
- pyproject.toml deps en mismo atom (Anthropic SDK ya en stack ·
  yaml ya en stack · no nuevas libs esperadas).

### Lección

A11 ya tenía 80% del trabajo hecho como capa senior sobre M10. M10
ya tenía 100% del banco 58 preguntas + matching determinista. Sumar
contexto M10+A11+persistencia histórica + threat auto-mapping con
catalog real = plataforma con "auditor virtual de élite" sin
reinventar la rueda. Briefing literal (58 LLM calls per dry-run)
hubiera sido 50× más costoso y arquitecturalmente confuso.

Lección estructural: cuando briefing diverge >10 puntos del repo,
STOP-1 estructurado + alineamiento Opción A es ahorro neto >10× vs
implementar literal y reescribir después.

### Referencias

- audit empírico SAN-D · secciones 2.2 + 2.5 + 8.3.
- `backend/app/motors/m10_audit_sim/audit_simulator.py` ·
  `AuditSimulatorService.run_simulation()` existing (58 preguntas
  deterministas L0-L5).
- `backend/app/agents/agent_11_wrapper.py` ·
  `POST /agents/11/run-supplementary-audit?run_id=<m10>`.
- `backend/app/motors/m02_magerit/models.py:31` · `MageritThreat`
  catalog · `:152` · `MageritThreatAssessment` · `MageritAnalysis`
  · `MageritAsset`.
- `docs/magerit_catalog/threats.yaml` · 57 amenazas oficiales.
- `backend/app/motors/m08_verification/models.py` · `VerificationRun`
  con category/mode/status.
- `backend/app/motors/m18_communication/alert_service.py:38` ·
  `AlertService.trigger_alert` con `_VALID_CATEGORIES`.
- TODO-MB-15.0-ADR-037-DOC · ABIERTO MB-15.0 · CERRADO commit atom 15.0.

### Deferrables MB-15 documentados (no son deuda)

Lista cerrada al cierre tag `s13-mb15-auditor-threat-cerrado`. Si
surge necesidad de adelantar alguno, requiere ADR nuevo o extensión
ADR-037 explícita · NO ad-hoc.

**DEC-A11-58-LLM-CALLS · alternativa briefing literal**

Briefing v2 propuso `AuditDryRunService` con 58 LLM calls Opus 4.7
per dry-run (1 call por pregunta CCN-STIC 802 con contexto filtrado).
Diferido (probablemente NUNCA se implemente · M10 determinista +
A11 senior ya cubre el caso de uso con 50× menos coste compute y
trazabilidad ENAC mejor).

**DEC-PENTEST-TRANSITION-HOOK · workflow_state.transition_phase()**

Briefing v2 hookeaba PentestAutoTrigger en `transition_phase` (no
existe). Implementación MB-15.3 usa SQLAlchemy event listener on
`Project.fase` change (pattern MB-13.3 dashboard_events) +
endpoint manual `POST /pentest/auto-trigger-evaluate` para
re-evaluación. Diferido `transition_phase` centralizado a MB-18
hook AutoBillingService (DEC-5 ADR-036).

**DEC-VERIFICATION-ENGAGEMENT-TYPE · field schema**

Briefing v2 usaba `VerificationRun.engagement_type='pentest_cpstic'`
(field no existe). Implementación MB-15.3 usa combinación
`category='ALTO' + mode='external_handoff'` semánticamente
equivalente. Si surge necesidad de tipos engagement más granulares
(red_team vs pentest_cpstic vs cripto_807) · scope MB-19+ con field
add + migration.

**DEC-MAGERIT-THIRD-YAML · single source of truth**

Briefing v2 creaba tercer yaml en `m02_magerit/`. Repo ya tiene 2
yamls oficiales. Implementación MB-15.2 reusa
`docs/magerit_catalog/threats.yaml` via loader Python apuntando con
`Path(repo_root) / "docs/magerit_catalog/threats.yaml"`. Si futuro
surge necesidad de variants yaml backend-private vs docs-public ·
scope MB-19+ con copy/symlink decision.

**DEC-A11-METHOD-NAME · answer_with_context**

Briefing v2 inventó método `AgentAuditorVirtual.answer_with_context()`
que no existe. Implementación MB-15.1 usa A11 wrapper real
`POST /agents/11/run-supplementary-audit?run_id=<m10_run_id>`.
Wrapper auto-compone client_context.

**DEC-CONTRACT-MODEL-SIGNATURE · pendiente verify**

Briefing v2 usaba `Contract.signed_at`, `Contract.project_id` (no
verificado en STOP-1). Implementación MB-15.1 NO consume contratos
(pivot scope: dry-run no necesita lista contratos firmados ·
información ya disponible via M14 service · si A11 senior layer
necesita contratos · llama service M14). Diferido si scope ampliado.

## ADR-038 · Portal cliente workspace continuo (SAN-D MB-14)

**Fecha**: 2026-05-06
**Status**: Adoptada
**Stakeholders**: Marcos Mata (decisor) · Claude (arquitecto)
**Complementa**: ADR-013 (separación 3 portales) · ADR-018 (auth
unificado) · ADR-035 (sistema vivo) · ADR-036 (UI condicional) ·
ADR-037 (AI Auditor). No supersede.

### Contexto

Marcos directiva post-MB-15: "cliente tiene un espacio de trabajo
continuo · tareas explícitas · comunicación directa conmigo · chat
<2h soporte · trabajar desde portal con usuario+contraseña · cada
acción cifrada auditable · magic-links lo veo tonto para tareas
continuas".

Audit empírico SAN-D revela:
- `ClientUser` ↔ `ClientContact` ya separados estructuralmente (✅
  aprovecha · `client_portal.py:21`).
- Auth portal email+pwd existing (`m21_portal_cliente/api.py:285+311`)
  con cookie httpOnly + CSRF triple binding (ADR-019/020).
- Workspace base existing: `dashboard · inbox · files · workflow ·
  account` en `(client-portal)/client-portal/`.
- `ClientUserAudit` modelo simple existing (`client_portal.py:111`)
  sin hash chain · sin project_id · sin chain_index.
- 12 magic-links continuos (ONBOARDING · APORTE_EVIDENCIA · etc) son
  candidatos a migrar a portal workspace (MB-19).
- 23 magic-links ONE-SHOT legítimos (firmas OTP+geo · descargas
  one-time · pentester externo) MANTIENEN razón de ser por:
  - Persona externa no debe registrarse para 1 acción.
  - Auditabilidad legal superior con OTP+geo.
  - Principio menor privilegio.

STOP-1 pre-implementación detectó divergencias briefing v2 → repo:
ClientUserAudit ya existe · ADR-037 ocupado por MB-15 · imports
`from app.X` requieren TRAD `from backend.app.X` ya aprobado MB-13/17.

### Decisión

A partir de SAN-D MB-14, FULKRO adopta arquitectura "Portal cliente
workspace continuo" con 7 principios:

1. **Portal cliente como workspace continuo · 90% operación**
   - Cliente login email+password (existing · robustecer rate limit +
     2FA TOTP opcional).
   - 6 secciones workspace: Dashboard · Tasks · Inbox · Chat ·
     Evidencias · Documents.
   - Cada acción persistida + audit log granular hash chain.

2. **Magic-links 10% solo para acciones ONE-SHOT auditables**
   - 23 purposes legítimos (firmas OTP · pentester · descargas
     one-time).
   - 12 purposes continuos migran a portal (MB-19+).

3. **ClientUserAudit hash chain SHA-256 · backward compat**
   - DEC-MB14-1 Opción A: ALTER tabla existing añadiendo columns
     nullable (project_id · chain_index · prev_hash · current_hash ·
     session_id · user_agent · action_type).
   - Rows pre-MB-14 con `chain_index NULL` legítimos · sin hash.
   - AuditLogService nuevo escribe rows con hash chain.
   - Verificación chain integrity opera sólo sobre rows con
     `chain_index NOT NULL` para `project_id` consultado.
   - Hash chain: `hash_n = SHA256(canonical_json(action_data) +
     prev_hash + chain_index)`.

4. **ClientTaskService + 18 templates yaml**
   - Tabla `client_tasks` per project_id × phase × archetype.
   - Generator auto-creates tasks cuando workflow_state cambia.
   - Cliente UI Tasks con estados (pending · in_progress · blocked ·
     done) + evidencia esperada + CTA + fecha límite.

5. **ChatService WebSocket bidireccional**
   - FastAPI[standard] WebSocket nativo (sin librerías extra).
   - Tabla `chat_threads` + `chat_messages` con timestamps.
   - SLA <2h tracking · alert auto si Marcos no responde en <2h.
   - Histórico persistente · cifrado at-rest opcional MB-19+.

6. **Evidencias upload reutiliza M07 ingestion existing**
   - `m07_evidence/ingestion_service.py` storage `var/evidences/`.
   - Cliente upload via portal · audit log cifrado · admin valida o
     rechaza.
   - Audit chain: evidencia ↔ task ↔ medida ENS implementada.

7. **2FA opcional + acciones críticas**
   - Cliente activa TOTP en perfil (existing `totp_enabled` field).
   - Acciones críticas (firmar declaración · subir evidencia >100MB ·
     cambiar password) requieren TOTP si activado.

### Consecuencias

**Backend**:

- ALTER `client_user_audit` (DEC-MB14-1 Opción A) · backward compat.
- Nuevas tablas: `client_tasks` · `chat_threads` · `chat_messages`.
- Services nuevos: `AuditLogService` (hash chain) · `ClientTaskService`
  · `ChatService` (WebSocket).
- Middleware FastAPI auto-log requests cliente (audit granular).
- 14+ endpoints REST nuevos cliente + admin.
- WebSocket dispatcher per project (cliente + Marcos).

**Frontend**:

- 6 pages cliente nuevos en `(client-portal)/client-portal/`:
  Tasks · Chat · Evidencias upload · Documents history (refactor
  existing files page).
- 2 pages admin nuevos: AdminChatInbox · AdminClientWorkspaceView.
- Hooks: `useChat` · `useTasks` · `useAuditLog`.
- Helper E2E `loginAsClient` (cosecha bonus para MB-17 deferrable
  client portal specs).

**Operacional**:

- Cliente puede hacer 90% trabajo SIN salir del portal.
- Marcos atiende chat <2h SLA · alertas portal admin.
- Magic-links residuales para 23 purposes ONE-SHOT auditables (MB-19+
  decisión per-purpose).
- ADR-034 v2 cumplido per atom (backend + UI same commit).

### Lección

Portal continuo > magic-links sueltos para tareas continuas.
Auditabilidad granular hash chain > "trust me bro" texto plano.
Chat sincrónico bilateral > emails ping-pong asíncronos.

Lección estructural complementaria a ADR-035: el "sistema vivo
cronológico" (NextActionCard · PhaseProgressWizard · AlertBell)
necesita workspace cliente persistente para que cliente PYME
trabaje continuamente sin email/magic-link friction.

### Referencias

- audit empírico SAN-D · sección 3 completa.
- `backend/app/models/client_portal.py:21` · `ClientUser` existing.
- `backend/app/models/client_portal.py:111` · `ClientUserAudit`
  existing (extiende DEC-MB14-1).
- `backend/app/motors/m21_portal_cliente/api.py:285+311` · auth
  portal existing.
- `backend/app/motors/m12_magic_link/purposes.py` · 35 purposes
  inventario (12 continuos migran MB-19 · 23 ONE-SHOT mantienen).
- ADR-013 (separación 3 portales) · ADR-018 (auth unificado) ·
  ADR-019 (CSRF triple binding) · ADR-020 (sessions tables).
- TODO-MB-14.0-ADR-038-DOC · ABIERTO MB-14.0 · CERRADO commit atom 14.0.

### Deferrables MB-14 documentados (no son deuda)

Lista cerrada al cierre tag `s13-mb14-portal-workspace-cerrado`. Si
surge necesidad de adelantar alguno, requiere ADR nuevo o extensión
ADR-038 explícita · NO ad-hoc.

**DEC-MB14-MAGIC-LINKS-MIGRATION · 12 purposes continuos**

Briefing menciona migrar 12 magic-link purposes continuos
(ONBOARDING · APORTE_EVIDENCIA · etc) a tareas portal. Diferido a
MB-19+ con decisión per-purpose explícita. MB-14 implementa portal
workspace · NO migra magic-links existentes (que continúan
funcionando paralelos).

**DEC-MB14-CHAT-WEBSOCKET-PIVOT · SSE+REST en lugar de WebSocket**

Briefing v2 propuso WebSocket bidireccional para chat. Implementación
MB-14.5 pivota a SSE+REST: cliente/admin envían via REST POST · ambos
reciben updates real-time via SSE existing dispatcher MB-13.3. Razón:
WebSocket auth sobre handshake con cookies httpOnly + CSRF triple
binding (ADR-019/020) agrega complejidad significativa sin beneficio
funcional vs SSE. WebSocket bidireccional diferido a MB-19+ si surge
necesidad concreta de push admin→cliente sin polling cliente.

**DEC-MB14-CHAT-ENCRYPTION-AT-REST**

Chat messages persistidos en plaintext en `chat_messages.content`.
Cifrado at-rest con Fernet diferido a MB-19+ (similar a pattern
M20 chat encryption ADR-032). MB-14 enfocado en flow cliente·
encryption es enhancement seguridad-comercial.

**DEC-MB14-CHAT-FILE-ATTACHMENTS · inline files**

Briefing menciona attach files inline en chat (linked a evidencias).
Implementación MB-14.5 deja chat texto-only · attachments diferido
a MB-19+ · UI envía link a evidencias upload page existing en
lugar de inline file embed.

**DEC-MB14-RECENT-ACTIVITY-CARD · re-asignado MB-19+**

NO implementado en MB-14. Foundation data layer existe (audit log
granular hash chain MB-14.1 provee `client_user_audit` queryable),
pero component UI consumidor NO se construyó (priorizé flow
Tasks/Chat/Evidencias UX cliente sobre activity feed admin).

Re-asignado a **MB-19+** scope admin panel deepening (dashboard
admin enriquecido con activity feeds + filters severity + category +
project + date range). Razón asignación: scope coherente con
AlertsPanel + UpcomingMilestonesCard + admin dashboard advanced en
mismo MB.

**DEC-MB14-ALERTS-PANEL-DEDICATED · RESUELTO MB-14.fix**

MB-13 dejó dead link `/admin/alerts` referenciado desde
`AlertBell.tsx:86` y `ActiveAlertsCard.tsx:109` sin page.tsx
correspondiente · regresión heredada detectada en gate review
MB-14 cierre.

**Resuelto en MB-14.fix** (post-tag rectification):
`frontend/app/(admin)/admin/alerts/page.tsx` mínimo funcional
implementado · usa `listActiveAlertsGlobal` + `acknowledgeAlert`
existing API client (MB-13.4) · filtros severity + category
client-side · shadcn Card + Badge + Button + Skeleton · lucide
icons · fulkro palette · acknowledge button per alert.

Lección operacional: dead link checks deben ejecutarse en gate
final per atom (grep `href="/admin/...` cross-reference contra
`frontend/app/(admin)/admin/<path>/page.tsx`).

**DEC-MB14-CELERY-CLIENT-INACTIVITY · re-asignado MB-16**

NO implementado en MB-14. Categoría `client_inactivity` existe en
`_VALID_CATEGORIES` AlertService (MB-13.4) pero la beat task que
detecta inactividad cliente NO está en `celery_app.py beat_schedule`.

Re-asignado a **MB-16** Notification Orchestrator. Razón: scope
natural · email alerts + DND + cross-channel notifications per
ContactPreference · client_inactivity task encaja con orchestrator
de notificaciones más que con MB-14 portal cliente.

**DEC-MB14-2FA-WEBAUTHN · MB-19+**

MB-14.2 implementa 2FA TOTP (existing infra `totp_secret_encrypted`
field). WebAuthn (passkeys) diferido a MB-19+ scope ampliado.

**DEC-MB14-INBOX-CROSS-PROJECT · re-asignado MB-19+**

MB-14.9 admin `/admin/inbox` page funcional informativo (componente
React real con Card + Inbox icon + hint navegación per-project ·
NO stub que rompa compilación · UX "informative coming-soon"
similar pattern UpcomingMilestonesCard MB-13).

Vista cross-project agregada (lista todos los chats activos de todos
los proyectos en un solo lugar con SLA badges) re-asignada a **MB-19+**
admin panel deepening. Component `AdminChatInbox` (MB-14.6) está
listo para integrarse en sub-ruta `/admin/projects/[id]/chat` cuando
scope per-project deepens.

**DEC-MB14-DOCUMENTS-HISTORY-EXISTING · CONFIRMADO sin cambios**

MB-14.8 documents history reusa `/client-portal/files` page existing
(creada en sub-bloque 10.B FIX) que cubre listado documentos firmados
readonly via `portal_documents` endpoint m21 con scope
`view_documents_*`. Sin cambios backend ni nueva ruta MB-14.

Status: **funcionalidad cubierta · documentation only**. Si futuro
requiere enrichment (filtros · búsqueda · download tracking granular ·
versionado) · scope MB-19+.

**Inline policy**: 0 TODO/FIXME inline · todo deferrable usa
`# Future:` con session ref (`SAN-D MB-14.X-DEFERRED`).


## ADR-039 · Notification Orchestrator simplificado modelo Marcos (SAN-D MB-16)

**Fecha**: 2026-05-06
**Status**: Adoptada
**Stakeholders**: Marcos Mata (decisor) · Claude (arquitecto)
**Complementa**: ADR-013 (separación portales) · ADR-035 (sistema
vivo) · ADR-038 (portal cliente workspace). No supersede.

### Contexto

Briefing v3 simplificado descarta arquitectura omnichannel completa
(Twilio SMS + Meta WhatsApp Business API) tras hallazgo Marcos:
"yo prefiero email + llamada · WhatsApp Business API son 2-4
semanas alta + cuotas + cero ROI con 1-5 clientes piloto".

Decisión cliente-céntrica: cada cliente decide su canal preferente.
Marcos NO impone SMS/WA. Reasignación scope MB-16:

- ❌ **Twilio SMS** descartado · descarta cuotas + WA stack onboarding
- ❌ **Meta WhatsApp Business API** descartado · 2-4 semanas alta · cero
  ROI 1-5 clientes piloto
- ✅ **Postmark email** primary channel · ya existing `EmailSender`
  fachada con retry exp + email_log
- ✅ **WhatsApp info-mode** OPCIONAL en pie email · texto plano
  formateado (ej. `+34 666 123 456 (de 9:00 a 18:00 L-V)`) · NO link
  clickeable · NO encoded text · cliente copia/pega manualmente si
  decide · degradación elegante si `MARCOS_WHATSAPP_NUMBER` env vacía
  (nota directiva post-briefing v3 Marcos: cero automatización pushy ·
  misma filosofía aplicará MB-18 IBAN)
- ✅ **Portal SSE** (MB-13.3 dispatcher) complementario para
  notificaciones in-app sin polling
- ✅ **Cliente decide canal** vía `notification_preferences` per
  ClientUser

Audit empírico SAN-D revela:
- `EmailSender` fachada multi-backend ya existing (`backend/app/core/
  email/sender.py`) con 3 backends (smtp · postmark_api · mock) +
  retry exponencial (2s · 8s · 32s) + email_log audit. NO crear
  `PostmarkEmailProvider` redundante. Orchestrator delega.
- `sse_dispatcher` MB-13.3 dispatch in-memory pub-sub queue por canal.
- `AlertService` MB-13.4 trigger_alert + alert_queue + categorías
  cerradas (`_VALID_CATEGORIES`) incluyendo `client_inactivity`
  (cosecha CELERY-CLIENT-INACTIVITY MB-14 deferred).
- Celery app (`backend/app/core/celery_app.py`) stub-able dev/tests
  sin Redis · pattern `@celery_app.task(name="…")` ya en m07
  evidence + m26 backup.
- `ClientUser` model existing (`backend/app/models/client_portal.py`)
  como FK target para `notification_preferences.client_user_id`.
- ADR-038 cosecha task `client_inactivity` re-asignada explícitamente
  a MB-16 (DECISIONS.md:3479-3488).

### Decisión

NotificationOrchestrator centraliza despacho cross-canal con
preferencias usuario + DND timezone-aware + retry + audit. Modelo
**email-first + SSE-complementario + WhatsApp-info-opcional**.

**Componentes:**

1. **`notification_events`** tabla audit immutable: event_type ·
   recipient_user_id · channels_attempted · channels_succeeded ·
   payload_jsonb · status (queued · dispatching · delivered ·
   failed · suppressed_dnd) · created_at · dispatched_at.

2. **`notification_preferences`** tabla per ClientUser:
   email_enabled · portal_sse_enabled · dnd_start_local (HH:MM ·
   default null = sin DND) · dnd_end_local · timezone (IANA ·
   default Europe/Madrid) · digest_mode (immediate · hourly · daily).

3. **`NotificationOrchestrator`** servicio principal:
   - `enqueue(event_type, recipient, payload, project_id?)` · valida
     · resolve template · check DND · persist `notification_events`
     row con status=queued · dispatch sync (E2E) o vía Celery (prod).
   - `_check_dnd(prefs, now_utc)` aware de tz IANA cliente · si dnd
     activo → status=suppressed_dnd · NO envía · re-encola próxima
     ventana hábil.
   - `_dispatch_email(event, recipient, html, text)` delega
     `get_email_sender().send(...)` existing · retry built-in.
   - `_dispatch_portal_sse(event, recipient, payload)` dispatch al
     channel `client_user:{recipient_id}` · in-app notification.

4. **`DeepLinkGenerator`** servicio: 25+ patterns canónicos
   (`task:{id}`, `chat:{thread_id}`, `evidence:{id}`,
   `phase:{phase}`, `audit:{id}`, etc.) → URL absoluta con
   `Settings.app_base_url`. Extiende magic-link patterns existing.

5. **`WhatsAppInfoFormatter`** OPCIONAL modo informativo (rename
   post-briefing v3 directiva Marcos): si `MARCOS_WHATSAPP_NUMBER`
   set → genera bloques `render_text_block()` + `render_html_block()`
   con número formateado humano legible (ej. `+34 666 123 456`)
   en pie email · `<strong>` + horas (`de 9:00 a 18:00 L-V`) ·
   NO link href · NO encoded text · NO `target="_blank"` · cliente
   copia/pega manualmente. Si vacía → degradación elegante (pie email
   NO incluye sección WhatsApp · 0 crash). Misma filosofía aplicará
   MB-18 IBAN (texto plano · no botón "Copiar IBAN").

6. **`TemplateResolver`** YAML-based: lee `backend/app/notifications/
   templates/*.yaml` con front matter `subject_es: ...`,
   `html_body_es: ...`, `text_body_es: ...`, `cta_label_es: ...` ·
   render con Jinja2 sandboxed (variables: recipient_name ·
   project_name · cta_url · etc · WhatsApp footer auto-append por
   resolver vía `WhatsAppInfoFormatter`).

7. **`Celery worker dispatch`** (`tasks.py`): `@celery_app.task(name=
   "notifications.dispatch_event")` recibe event_id · re-resolve
   row · dispatch · update status. Retry simple `bind=True`,
   `autoretry_for=(Exception,)`, `retry_kwargs={"max_retries": 3,
   "countdown": 60}` (separate del retry interno EmailSender ·
   este nivel cubre fallos transient infraestructura).

8. **`@celery_app.task(name="notifications.scan_client_inactivity")`**
   cosecha CELERY-CLIENT-INACTIVITY (deferred MB-14): scan
   `client_users.last_login` < now - 14 días → AlertService
   trigger_alert categoría `client_inactivity`. Beat schedule
   daily 09:00 Europe/Madrid.

9. **6 templates iniciales** YAML (`backend/app/notifications/
   templates/`):
   - `task_assigned.yaml` · cliente recibe nueva tarea
   - `chat_admin_reply.yaml` · cliente recibe respuesta admin
   - `evidence_expiring.yaml` · cliente evidencia próxima a expirar
   - `phase_changed.yaml` · cliente cambio fase workflow
   - `audit_due.yaml` · cliente auditoría programada próxima
   - `client_inactivity_admin.yaml` · admin alert cliente inactivo

10. **UI cliente** `/client-portal/account/notifications` (MB-16.5):
    Card preferences toggle email · portal SSE · DND start/end ·
    timezone select · digest_mode radio. Persist via
    `PUT /api/v1/portal/notifications/preferences`.

11. **UI admin** `/admin/notifications` (MB-16.5): listado eventos
    últimos 30d filtrable por status + event_type · diagnostic
    panel para debug despacho.

12. **Refactor motors hardcoded** (MB-16.6): motors que enviaban
    email directo (m07_evidence · m12_magic_link onboarding · m18 ·
    m23_retainer · m25_lifecycle) migran a
    `orchestrator.enqueue(...)` · respetan preferences cliente +
    DND.

### Consecuencias

**+** Single source of truth despacho notificaciones · 0 hardcoding
spread per motor.
**+** Cliente controla canal · respeta DND timezone-aware · digest
mode reduce ruido.
**+** Audit immutable `notification_events` para compliance ENS +
debug.
**+** Cosecha CELERY-CLIENT-INACTIVITY deferred MB-14 cierra deuda.
**+** Email-only stack mantiene <€10/mes infra (Postmark free tier
+ 0 SMS/WA cuotas).
**−** No SMS/WA → casos urgentes dependen check email cliente. Mitigado
por WhatsApp info-mode pie email (cliente copia número y abre WhatsApp
manualmente · 0 automatización pushy · directiva Marcos).
**−** Refactor motors invasivo (~5 motors touch). Mitigado por
batched single atom 16.6 con E2E suite cobertura cross-component.

### Implementación

- `backend/migrations/versions/sand_notif_events_001.py` ·
  `notification_events` tabla.
- `backend/migrations/versions/sand_notif_prefs_001.py` ·
  `notification_preferences` tabla.
- `backend/app/notifications/orchestrator.py` · Orchestrator core.
- `backend/app/notifications/deep_links.py` · DeepLinkGenerator.
- `backend/app/notifications/whatsapp_info.py` · WhatsAppInfoFormatter
  modo informativo (rename post-briefing v3 directiva Marcos).
- `backend/app/notifications/templates_resolver.py` ·
  TemplateResolver Jinja2 + YAML.
- `backend/app/notifications/templates/*.yaml` · 6 templates
  iniciales.
- `backend/app/notifications/tasks.py` · Celery dispatch +
  scan_client_inactivity.
- `backend/app/notifications/api.py` · endpoints portal preferences +
  admin events list.
- `backend/app/notifications/dnd.py` · DND timezone-aware helper.
- `backend/app/models/notifications.py` · SQLAlchemy models.
- `frontend/app/(client-portal)/client-portal/account/notifications/
  page.tsx` · UI preferences cliente.
- `frontend/app/(admin)/admin/notifications/page.tsx` · UI admin
  events list.
- `frontend/components/notifications/PreferencesForm.tsx` · form
  componente.
- `frontend/components/notifications/EventsTable.tsx` · admin
  events table.
- `frontend/lib/notifications/api.ts` · client API wrapper.
- ENV vars nuevas: `MARCOS_WHATSAPP_NUMBER` (opcional · ej
  `+34666123456`).
- Deps backend nuevas: `Jinja2>=3.1`, `PyYAML>=6.0`.

### Trazabilidad

- `backend/app/core/email/sender.py` · EmailSender fachada existing.
- `backend/app/core/sse_dispatcher.py` · SSE dispatcher MB-13.3.
- `backend/app/motors/m18_communication/alert_service.py` ·
  AlertService MB-13.4 (categoría `client_inactivity` ya en
  `_VALID_CATEGORIES`).
- `backend/app/core/celery_app.py` · Celery app stub-able.
- `backend/app/models/client_portal.py:21` · ClientUser FK target.
- ADR-035 (sistema vivo) · ADR-038 (portal workspace · cosecha
  CELERY-CLIENT-INACTIVITY).
- TODO-MB-16.0-ADR-039-DOC · ABIERTO MB-16.0 · CERRADO commit
  atom 16.0.

### Deferrables MB-16 documentados (no son deuda)

Lista cerrada al cierre tag `s13-mb16-omnichannel-cerrado`. Si
surge necesidad de adelantar alguno, requiere ADR nuevo o extensión
ADR-039 explícita · NO ad-hoc.

**DEC-MB16-SMS-TWILIO · re-asignado MB-19+ scope amplio**

Briefing v2 proponía Twilio SMS para urgencias. Descartado MB-16
v3 por preferencia Marcos (email + llamada · NO SMS) y zero ROI
1-5 clientes piloto. Si futuro requiere SMS (ej. expansión >50
clientes con SLA <30min) · scope MB-19+ con re-evaluación coste
+ valor.

**DEC-MB16-WHATSAPP-BUSINESS-API · re-asignado MB-19+ scope amplio**

Briefing v2 proponía Meta WhatsApp Business API bidireccional.
Descartado MB-16 v3 por:
- Onboarding 2-4 semanas (alta + verification + plantillas).
- Cuotas mensuales · cero ROI 1-5 clientes piloto.
- Pivot a `WhatsAppInfoFormatter` modo informativo pie email
  (texto plano · NO link · directiva Marcos cero automatización
  pushy) cubre caso uso "cliente inicia conversación WA con Marcos"
  sin infraestructura WA Business.

Si futuro requiere WA Business bidireccional (ej. >20 clientes
necesitan inbound WA + plantillas masivas) · scope MB-19+ con
re-evaluación.

**DEC-MB16-EMAIL-SENDER-WRAP · resolución limpia**

Briefing v3 menciona "PostmarkEmailProvider wrap". AUDIT empírico
revela `EmailSender` fachada multi-backend ya existing (3 backends
seleccionables · retry exponencial · email_log audit). Decisión:
Orchestrator delega `get_email_sender().send(...)` directamente ·
NO crear wrap redundante · single source of truth Settings env
mantenido.

**DEC-MB16-DIGEST-MODE-IMMEDIATE-ONLY · MB-19+**

`notification_preferences.digest_mode` schema soporta `immediate`
+ `hourly` + `daily` PERO MB-16 implementa solo `immediate`.
Hourly + daily digest engine (batch + render summary email) ·
diferido a MB-19+ cuando volume notifications >10/día/cliente
justifique implementación.

**DEC-MB16-MULTI-RECIPIENT-BROADCAST · MB-19+**

MB-16 enqueue acepta single recipient_user_id. Broadcast multi-
recipient (ej. notify all client_users del proyecto) · diferido
MB-19+. Workaround MB-16: caller itera lista y enqueue per
recipient.

**DEC-MB16-NOTIFICATION-RETRY-DLQ · MB-19+**

Celery retry built-in 3 attempts · countdown 60s. Dead Letter
Queue + manual replay UI admin · diferido MB-19+. Workaround
MB-16: `notification_events.status=failed` queryable + manual
re-enqueue via SQL.

**DEC-MB16-PUSH-NOTIFICATIONS-WEBPUSH · MB-19+**

Web Push (Service Worker subscriptions + VAPID) browser-native ·
diferido MB-19+. MB-16 cobertura in-app via SSE dispatcher
existing es suficiente para MVP.

**DEC-MB16-DND-OVERRIDE-CRITICAL · MB-19+**

DND timezone-aware suprime envíos en ventana DND. Override forzoso
para eventos categoría `critical` (ej. brecha RGPD <72h ·
incidente seguridad) · diferido MB-19+. MB-16 política conservadora:
DND respeta TODO · admin tiene canal alternativo (alert SSE
in-app).

**DEC-MB16-MOTORS-REFACTOR-INCREMENTAL · MB-19+**

MB-16.6 integra NotificationOrchestrator vía `motor_adapters` (5
funciones convenience: notify_chat_admin_reply ·
notify_task_assigned · notify_evidence_expiring · notify_phase_changed
· notify_audit_due) y refactoriza `m21_portal_cliente.ChatService.
post_message` admin → enqueue chat_admin_reply (orchestrator delega
EmailSender + portal SSE existing pattern).

Refactor restante motors (m07_evidence freshness · m12_magic_link
onboarding · m18_communication · m23_retainer alerts · m25_lifecycle
grace period) re-asignado MB-19+ por scope incremental. Razón: cada
motor tiene contexto de dominio y reglas de aplicabilidad propias
(ej. m07 evidence requiere lookup ClientUser propietario evidence ·
m23 retainer notifica solo si renewal_status = T_MINUS_30D · etc) ·
batched refactor invasivo eleva riesgo regresión sin valor inmediato
para 1-5 clientes piloto.

Pattern establecido MB-16.6 (motor_adapters convenience functions +
ChatService integration + tests stack real) sirve de plantilla para
refactors incrementales MB-19+ per-motor con su propia ADR si scope
> 1 atom.

**DEC-MB17-CLIENT-PORTAL-SPECS-AUTHGUARD · MB-19 (cosecha natural)**

Hallazgo V-CHECK D cumulative regression post-MB-16: 4 specs MB-17
client portal fallan por `page.route()` mocks incompatibles con
`AuthGuard.useAuthStore.ready` check introducido en FASE 10.A
(refactor chrome cliente). Specs afectadas:

- `frontend/tests/e2e/mb17_arquetipo_sector_salud.spec.ts:130` ·
  banner art.9 RGPD sector salud cliente portal
- `frontend/tests/e2e/mb17_client_portal_categoria.spec.ts:50` ·
  ClientCategoryBanner BASICA · autoevaluación 809 · sin pentest
- `frontend/tests/e2e/mb17_client_portal_categoria.spec.ts:74` ·
  ClientCategoryBanner MEDIA sector_salud · banner art.9 RGPD
- `frontend/tests/e2e/mb17_client_portal_categoria.spec.ts:99` ·
  ClientCategoryBanner ALTA · pentest CPSTIC + productos certificados

Causa raíz: tests mockean `/api/v1/client-portal/me` + `/project` +
`/retainer` + `/documents` con `page.route()` esperando bypass auth
flow. Pero `AuthGuard requiredRole="client"` (`frontend/components/
auth/AuthGuard.tsx`) post-FASE 10.A consulta `useAuthStore.ready`
que se popula via fetch real (no por mock). Page snapshot del trace
fail confirma render de pantalla `/client-portal/login` en lugar de
`/client-portal/dashboard`.

**Verificado empíricamente NO regresión MB-16:** ejecutado contra
HEAD pre-MB-16 (`d66fa298` post-MB-14 fix dead link) las MISMAS 4
specs fallan idéntico (mismo error message, mismo locator no
encontrado, mismo screenshot login page). Failure introducido por
refactor AuthGuard FASE 10.A previo a SAN-D · NO causado por
cambios MB-16 frontend.

Asignación: **MB-19** (cosecha natural junto con client portal
deepening · paralelo a deferrables MB-14 también re-asignados a
MB-19 inbox cross-project + recent activity card). Refactor specs:
sustituir `page.route()` mocks por `loginAsClient(page)` helper
existing (`frontend/tests/e2e/_helpers/auth-real.ts`) que ya cumple
flow real backend con cookies + CSRF (canónico MB-14
`mb14_client_workspace.spec.ts`). Estimado **1-2h** (cuatro specs ·
patrón mecánico replace mock + add `loginAsClient` + ajustar
selectors si AuthGuard mete delay render).

Mientras tanto: 4 specs reportan fail en CI MB-19+ con anotación
`@deferred MB-19 client portal AuthGuard refactor` para no romper
gate cumulative · NO bloquean gate MB-X intermedios.

**Inline policy**: 0 TODO/FIXME inline · todo deferrable usa
`# Future:` con session ref (`SAN-D MB-16.X-DEFERRED`).


## ADR-040 · Auto-billing milestone + transferencia bancaria manual (SAN-D MB-18)

**Fecha**: 2026-05-06
**Status**: Adoptada
**Stakeholders**: Marcos Mata (decisor) · Claude (arquitecto)
**Complementa**: ADR-035 (sistema vivo) · ADR-038 (portal cliente
workspace) · ADR-039 (notification orchestrator). No supersede.

### Contexto

Briefing v3 simplificado descarta arquitectura payment gateway completa
(Stripe + Redsys + Tink open banking) tras hallazgo Marcos: "consultoría
B2B trato humano · transferencia bancaria estándar · sin clientes AAPP
actuales · sin volumen card payments justifique 1.4% Stripe · sin
necesidad webhook bancos automatizados".

Decisión consultor-céntrica: cada hito contrato genera factura + email
cliente con datos cuenta bancaria; cliente paga por transferencia normal;
Marcos ve extracto banco a diario y marca paid manual; workflow proyecto
desbloquea siguiente fase si milestone era blocking. Reasignación scope
MB-18:

- ❌ **Stripe** descartado · 1.4%+0.25€/pago + cuotas + KYC compliance ·
  cero ROI 1-5 clientes piloto B2B consultoría
- ❌ **Redsys** descartado · sin clientes AAPP actuales · stack
  certificación TPV innecesario
- ❌ **Tink open banking** descartado · 5€/mes + alta + OAuth complexity ·
  reconciliación manual diaria 5 min coste cero
- ❌ **Webhooks externos pago** · cero providers externos webhook
- ✅ **AutoBillingService** trigger workflow milestone-completion ·
  invoice + email + alert sin gateway
- ✅ **ManualTransferProvider** genera datos transferencia (IBAN +
  titular + concepto) en email milestone_completed
- ✅ **IBAN modo informativo** en email + portal cliente · texto plano
  formateado · NO botón "Copiar IBAN" + clipboard.writeText · cliente
  selecciona y copia manualmente (filosofía cross-reference WhatsApp
  MB-16: cero automatización pushy)
- ✅ **Reconciliación manual** Marcos UI admin `/admin/finance/
  pending-payments` button "Marcar pagado" tras ver extracto banco
- ✅ **RetainerStateMachine extendida** con upgraded/downgraded/churned
  + audit + notification cliente
- ✅ **RetainerChurnPredictor heurístico explicable** · 6 signals · score
  0-100 · NO ML black-box · alert Marcos si critical

Audit empírico SAN-D MB-18 revela:
- `MilestoneSpec` NamedTuple existing (`backend/app/core/pricing/
  rules.py:75`) con HITOS_BASICA/MEDIA/ALTA tuples · code + pct +
  description · NO crear redundancia.
- `PricingCalculator.get_milestones(categoria, total)` existing
  (`backend/app/core/pricing/calculator.py:282`) · usado en
  `m14_contracts.contract_service.py:209` para hidratar contracts.
- `Contract` model existing (`backend/app/models/commercial.py:57` ·
  FullMixin · contract_id · project_id · estado · firmado_*_at).
- `Invoice` model existing (`backend/app/models/commercial.py:82` ·
  campos españoles: `numero_correlativo` · `fecha_vencimiento` ·
  `estado_pago` · `total` · NO inglés briefing v3).
- `BillingService.generate_invoice` existing (`backend/app/motors/
  m15_billing/billing_service.py:50`) · firma con `lineas` array
  (descripcion + cantidad + precio_unitario) · NO `amount_net_eur`
  direct.
- `RetainerContract` model existing (`backend/app/models/retainer.py:16` ·
  estado: active/paused/expired/cancelled · perfil: R_LITE/STD/PLUS/
  CRITICAL · renewal_status · rag_status).
- `WorkflowPhase` enum 10 fases existing (`backend/app/core/
  workflow_phase.py`) · NO `transition_to_phase()` callable · avance
  vía UPDATE `projects.fase` o signals dispatched (`workflow_state.py`).
- `NotificationOrchestrator` existing MB-16 · cosechar (NO duplicar) ·
  `motor_adapters` pattern para integration limpia.
- `AlertService` existing MB-13.4 · categoría `contract_milestone`
  ya en `_VALID_CATEGORIES` (cero migration adicional).

### Decisión

A partir de SAN-D MB-18 simplificado:

1. **`contract_milestones` tabla audit immutable per hito**
   - id (UUID PK) · contract_id FK · project_id · milestone_index ·
     milestone_name · workflow_phase_index · billing_trigger
     (`phase_complete`|`phase_start`|`manual`|`scheduled_date`) ·
     amount_eur · vat_percent · percent_of_total · status
     (`pending`|`billed`|`invoice_issued`|`payment_pending`|`paid`|
     `disputed`|`refunded`) · billed_at · invoice_id · paid_at ·
     paid_marked_by_user_id · payment_reference · payment_notes ·
     auto_billing_enabled · blocking_next_phase · metadata_jsonb ·
     UNIQUE (contract_id, milestone_index).

2. **`retainer_health_signals` tabla churn predict**
   - id · project_id · retainer_id · computed_at · signals (days_since_
     portal_login · days_since_chat_msg_client · tasks_overdue_count ·
     invoices_overdue_count · avg_response_time_hours · nps_last_score ·
     renewal_in_days) · churn_risk_score (0-100) · risk_level
     (`low`|`medium`|`high`|`critical`) · primary_risk_factors JSONB ·
     recommended_action.

3. **`MilestoneFactory`** servicio: dado un Contract + categoria,
   invoca `PricingCalculator.get_milestones(categoria, total)` y
   persiste `ContractMilestone` rows mapeando milestone_name →
   workflow_phase_index canónico (hito_1_firma → ONBOARDING ·
   hito_2_categoria → ANALISIS_RIESGOS · etc · mapping documentado
   inline). Idempotente · UNIQUE constraint previene doble-creación.

4. **`AutoBillingService`** servicio principal:
   - `handle_phase_completion(project_id, completed_phase_index)` ·
     scan `ContractMilestone` con
     `workflow_phase_index == completed_phase_index` +
     `billing_trigger == "phase_complete"` + `status == "pending"` +
     `auto_billing_enabled` → invoice + email + alert per milestone.
   - `_bill_milestone(milestone)` ·
     1) `BillingService.generate_invoice(...lineas=[{descripcion: hito,
        cantidad: 1, precio_unitario: amount_eur}], iva_percent=21,
        contract_id, project_id, hito_asociado=milestone_name,
        concepto: "Hito N: name")` returns Invoice
     2) Update `milestone.status="invoice_issued"` + `billed_at` +
        `invoice_id`.
     3) Genera transfer instructions vía `ManualTransferProvider`.
     4) Notify cliente vía `notify_milestone_billed` motor adapter
        (template `milestone_billed` resuelve subject + html + text +
        WhatsApp footer auto-append).
     5) Trigger AlertService category=`contract_milestone` severity=
        `info` para Marcos.
   - `mark_milestone_paid(milestone_id, by_user_id, payment_reference,
     payment_notes, paid_at)` · marca paid + notify cliente
     `payment_received` + UPDATE `projects.fase` next phase si
     `blocking_next_phase` (workflow advance simple sin
     transition_to_phase callable).

5. **`ManualTransferProvider`** servicio info-mode:
   - `generate_payment_instructions(invoice_number, amount_eur,
     payment_due_date)` returns dict con IBAN + holder + institution +
     reference + concept + due_date.
   - `format_for_email_text()` returns texto plano formateado humano
     legible · NO link · NO botón.
   - `format_for_email_html()` returns HTML con `<strong>` IBAN ·
     formato visible · NO `<a>` href · NO `target="_blank"` · NO
     `clipboard.writeText` JS · cliente selecciona y copia manualmente
     (filosofía cross-reference WhatsApp MB-16 directiva Marcos cero
     automatización pushy).
   - Si `MARCOS_BANK_IBAN` env vacío → `format_*` returns string vacío
     → email factura sin sección instrucciones (degradación elegante:
     Marcos las añade a mano editando email Postmark template).

6. **`RetainerStateMachine`** servicio extendido:
   - Estados existing: `active` · `paused` · `expired` · `cancelled`
   - Estados nuevos: `upgraded` · `downgraded` · `churned`
   - VALID_TRANSITIONS table explícita por estado origen.
   - `transition(retainer_id, target_status, reason, by_user_id)` ·
     valida + UPDATE estado + audit row + notify orchestrator (cliente
     + admin si churned/upgraded).

7. **`RetainerChurnPredictor`** servicio heurístico explicable:
   - `compute_score(project_id, retainer_id)` recolecta 6 signals desde
     DB (last_login from client_user_audit · overdue tasks count ·
     overdue invoices count · avg response time chat_threads · NPS
     last score · days to next_renewal) y aplica reglas:
     - `+40 si days_since_portal_login > 60`
     - `+25 si tasks_overdue_count > 3`
     - `+25 si invoices_overdue_count > 0`
     - `+20 si avg_response_time_hours > 48`
     - `+15 si nps_last_score < 6`
     - `+10 si renewal_in_days < 90`
   - score capped 0-100 · `risk_level` mapping (0-29 low · 30-59 medium ·
     60-79 high · 80-100 critical) · `recommended_action` text per level.
   - Persist `RetainerHealthSignal` row + alert AlertService category=
     `retainer_overdue` (existing) si critical.

8. **Celery beat** `notifications.scan_retainer_churn_risk` weekly
   Monday 09:30 Europe/Madrid · scan retainers active · compute score
   per retainer · alert si critical.

9. **8 endpoints REST simplificados:**
   - `POST /api/v1/admin/contracts/{id}/milestones/regenerate` · admin
     fuerza regen MilestoneFactory.
   - `GET /api/v1/admin/finance/kpis` · revenue this month · pending
     total · overdue count.
   - `GET /api/v1/admin/finance/pending-payments` · listado milestones
     status=invoice_issued sin paid_at.
   - `POST /api/v1/admin/finance/milestones/{id}/mark-paid` · Marcos
     marca paid manual + workflow advance.
   - `GET /api/v1/portal/billing/invoices` · cliente lista invoices con
     IBAN info-mode.
   - `GET /api/v1/admin/retainers/churn-risk` · top high+critical risk.
   - `POST /api/v1/admin/retainers/{id}/transition` · cambia estado
     con reason.
   - `POST /api/v1/admin/retainers/scan-churn` · trigger manual scan
     (debug Celery beat).

10. **3 components frontend admin** (`/admin/finance` · `/admin/finance/
    pending-payments` · `/admin/retainers/churn-risk`):
    - `FinanceDashboard` KPI cards + ReconciliationManualPanel.
    - `ReconciliationManualPanel` listado pending payments + button
      "Marcar pagado" + Dialog con `payment_reference` + `payment_notes`.
    - `ChurnRiskList` top 20 high/critical con score + signals + recommended_action.

11. **1 component cliente** `/client-portal/billing` ·
    `BillingHistory`:
    - Lista invoices propios con badge status + amount + due_date.
    - Si pending: muestra `IBAN info-mode` formateado en `<strong>`
      texto plano sin botón clipboard · cliente copia manualmente
      (directiva Marcos · cross-ref WhatsApp MB-16).
    - Botón download PDF factura existing M15.

12. **Email template `milestone_billed`** YAML:
    - subject_es: "Hito {N} completado · Factura {invoice_number} ·
      {project_name}"
    - html_body_es: introducción + amount + IBAN bloque info-mode
      `<strong>` + concepto + reference + footer Marcos.
    - text_body_es: equivalente texto plano + WhatsApp footer
      auto-append vía orchestrator template_resolver.

13. **Variables entorno producción nuevas:**
    - `MARCOS_BANK_IBAN` (ej. `ES12 1234 5678 9012 3456 7890`)
    - `MARCOS_BANK_HOLDER` (ej. `Marcos Mata Vega`)
    - `MARCOS_BANK_INSTITUTION` (ej. `Banco Santander`)
    - `MARCOS_BANK_BIC` (opcional · solo SEPA internacional)
    - Si `MARCOS_BANK_IBAN` vacío → degradación elegante (email
      factura sin sección instrucciones · Marcos hace transferencia
      a mano fuera del sistema)

### Consecuencias

**+** Single source of truth contract milestones tracking · audit
immutable per estado lifecycle.
**+** Cero providers externos compliance burden (Stripe KYC · Redsys
TPV cert · Tink OAuth) · cero coste recurrente (€0/mes vs Stripe 1.4%
+ Tink ~5€/mes).
**+** RetainerChurnPredictor heurístico explicable · Marcos puede
auditar cada signal vs ML black-box opaque.
**+** IBAN info-mode coherente filosofía MB-16 WhatsApp · cero
automatización pushy.
**+** Reconciliación manual ~5 min/día Marcos · simple admin button.
**−** Marcos depende ver extracto banco diario para reconciliar (mitigado:
alerts SLA si milestone billed sin pago > 7 días).
**−** No SEPA Direct Debit auto · cliente debe iniciar transferencia
(B2B normal · expectativa cliente standard).
**−** Refactor workflow advance simple (UPDATE projects.fase) en lugar
de transition_to_phase callable inexistente · pattern adoptado
explícitamente para MB-18 · futuro callable centralizado MB-19+ si
emerge necesidad.

### Implementación

- `backend/migrations/versions/sand_billing_milestones_001.py` ·
  `contract_milestones` tabla.
- `backend/migrations/versions/sand_retainer_health_001.py` ·
  `retainer_health_signals` tabla.
- `backend/app/models/billing_milestones.py` · ContractMilestone +
  RetainerHealthSignal SQLAlchemy models.
- `backend/app/billing/__init__.py` · package init exports.
- `backend/app/billing/milestone_factory.py` · MilestoneFactory.
- `backend/app/billing/manual_transfer.py` · ManualTransferProvider
  info-mode.
- `backend/app/billing/auto_billing.py` · AutoBillingService.
- `backend/app/billing/api.py` · 4 endpoints admin finance + 1 portal.
- `backend/app/notifications/templates/milestone_billed.yaml` · template.
- `backend/app/notifications/motor_adapters.py` extension · función
  `notify_milestone_billed` + `notify_payment_received`.
- `backend/app/retainer/__init__.py` · package init.
- `backend/app/retainer/state_machine.py` · RetainerStateMachine.
- `backend/app/retainer/churn_predictor.py` · ChurnPredictor + Celery task.
- `backend/app/retainer/api.py` · 3 endpoints retainer admin.
- `frontend/lib/billing/schemas.ts` + `api.ts`.
- `frontend/components/admin/finance/FinanceDashboard.tsx` ·
  `ReconciliationManualPanel.tsx` · `ChurnRiskList.tsx`.
- `frontend/components/client-portal/BillingHistory.tsx`.
- `frontend/app/(admin)/admin/finance/page.tsx` ·
  `frontend/app/(admin)/admin/finance/pending-payments/page.tsx` ·
  `frontend/app/(admin)/admin/retainers/churn-risk/page.tsx`.
- `frontend/app/(client-portal)/client-portal/billing/page.tsx`.
- `backend/app/config.py` · MARCOS_BANK_* fields.
- `backend/app/core/celery_app.py` · beat schedule
  `retainer-scan-churn-weekly` Monday 09:30.

### Trazabilidad

- `backend/app/core/pricing/rules.py:75` · MilestoneSpec existing.
- `backend/app/core/pricing/calculator.py:282` · get_milestones existing.
- `backend/app/motors/m14_contracts/contract_service.py:209` · uso
  existing.
- `backend/app/models/commercial.py:57+82` · Contract + Invoice models.
- `backend/app/models/retainer.py:16` · RetainerContract model.
- `backend/app/motors/m15_billing/billing_service.py:50` ·
  BillingService.generate_invoice existing.
- `backend/app/notifications/orchestrator.py` · NotificationOrchestrator
  MB-16.
- `backend/app/motors/m18_communication/alert_service.py` ·
  AlertService MB-13.4 (categoría `contract_milestone` ya valid).
- ADR-035 (sistema vivo) · ADR-039 (notification orchestrator).
- TODO-MB-18.0-ADR-040-DOC · ABIERTO MB-18.0 · CERRADO commit atom 18.0.

### Diferencias vs ADR-040 v1 archivado (briefing v3 original)

v1 (descartado): Stripe + Redsys + Tink + 5 tablas + 18 endpoints +
4 webhooks + 50-78h.
v2 (vigente · este ADR): Manual + 2 tablas + 8 endpoints + 0 webhooks
externos + 18-28h · ahorra 32-50h + €0/mes coste recurrente.

### Deferrables MB-18 documentados (no son deuda)

Lista cerrada al cierre tag `s13-mb18-auto-billing-cerrado`. Si surge
necesidad de adelantar alguno, requiere ADR nuevo o extensión ADR-040
explícita · NO ad-hoc.

**DEC-MB18-STRIPE-PAYMENT-GATEWAY · MB-19+ scope amplio**

Briefing v2 proponía Stripe Checkout + payment_intents + webhooks. Descartado
MB-18 v3 por:
- Cero clientes pagan tarjeta hoy (B2B consultoría = transferencia normal).
- 1.4% + 0.25€/pago + KYC compliance + cuotas mensuales = ~€150-300/año.
- Cero ROI con 1-5 clientes piloto.
Re-asignación MB-19+ si volumen >€20k/mes recurring justifique stack o
si cliente B2C aparece (probabilidad baja en plan FULKRO).

**DEC-MB18-REDSYS-TPV · MB-19+ scope amplio**

Briefing v2 proponía Redsys integration para clientes AAPP. Descartado
MB-18 v3 por:
- Cero clientes AAPP actuales.
- Cert TPV stack 2-4 semanas alta + compliance burden.
- AAPP típicamente paga via SEPA institucional manual (extracto banco).
Re-asignación MB-19+ si Marcos firma primer cliente AAPP (probabilidad
medio plazo · pivot ENS Radar B2G).

**DEC-MB18-TINK-OPEN-BANKING · MB-19+ scope amplio**

Briefing v2 proponía Tink integration para reconciliación automática
extracto banco. Descartado MB-18 v3 por:
- 5€/mes mínimo + alta + OAuth flow per banco.
- Marcos reconciliación manual ~5 min/día = €0/mes coste mismo valor.
- Cero ROI hasta volumen >50 facturas/mes.
Re-asignación MB-19+ si volumen invoice mensual >50 (cero indicio plazo
medio).

**DEC-MB18-WEBHOOKS-PAYMENT-EVENTS · MB-19+**

Briefing v2 proponía 4 webhooks externos (Stripe success/fail · Tink
match · Redsys completion). Descartado · cero providers externos.
Reconciliación manual via UI admin button + AlertService SLA breach.

**DEC-MB18-IBAN-COPY-BUTTON · descartado · directiva Marcos**

Briefing v2 incluía botón "Copiar IBAN" + `clipboard.writeText` JS en
frontend cliente billing. Descartado por directiva Marcos cross-reference
WhatsApp MB-16 (DEC-MB16-WHATSAPP-INFO-MODE): cliente selecciona y copia
manualmente · cero automatización pushy. Aplicado coherente: IBAN como
texto plano formateado `<strong>` · sin botón · sin onclick · sin JS
clipboard API.

**DEC-MB18-WORKFLOW-TRANSITION-CALLABLE · MB-19+**

Briefing v2 invocaba `transition_to_phase()` callable centralizado para
auto-advance fase tras milestone paid. AUDIT empírico revela `transition_
to_phase` NO existe (workflow es vía UPDATE `projects.fase` o signals
dispatched en `workflow_state.py`). MB-18 adopta UPDATE simple
(`projects.fase = next_phase` si milestone.blocking_next_phase) sin
side-effect side-effects más sofisticados (no dispatch signal · no
notify motors descendientes).

Implementación callable centralizada con todos los side-effects (notify
motors · trigger calculations · etc) · diferida MB-19+ si emerge
necesidad concreta. MB-18 v3 enfoque pragmático: UPDATE + notify cliente
+ next workflow loop tick procesa estado actualizado.

**DEC-MB18-DUNNING-AUTOMATION · MB-19+**

Recordatorios automáticos pago retrasado (T+7 · T+14 · T+30 escalating)
diferido MB-19+. MB-18 cobertura: AlertService SLA breach + admin manual
follow-up. Dunning automation engine (template emails escalating · auto-
suspend portal access tras T+45 · etc) re-asignado MB-19+ con su propia
ADR.

**DEC-MB18-VAT-MULTI-RATE · MB-19+**

MB-18 hardcodea `vat_percent=21.00` (IVA España general). Multi-rate
soporte (4% reducido · 10% reducido · IVA exento · IVA otros UE) ·
diferido MB-19+ si cliente solicita facturación servicio exento o
inversión sujeto pasivo intracomunitaria.

**DEC-MB18-INVOICE-RECTIFICATIVA-AUTO · existing M15 manual**

`BillingService.generate_invoice(tipo="rectificativa")` ya existing
(SAN-C). MB-18 NO automatiza creación rectificativas (Marcos invoca
manual desde admin si dispute milestone refund). Auto-rectificativa per
disputa flow · diferido MB-19+.

**DEC-MB18-CHURN-PREDICTOR-ML · MB-19+**

ChurnPredictor MB-18 heurístico explicable (6 reglas if/then · score
0-100). ML-based churn (random forest · gradient boost · neural net) ·
diferido MB-19+ por:
- Cero datos histórico training (1-5 clientes piloto sin churn previo).
- Heurístico explicable ya cubre needs Marcos (auditable ENAC compliance).
- ML black-box rompe trazabilidad ENAC para 1 consultor solo.
Re-asignación MB-19++ si volumen >50 clientes con churn data 12+ meses
justifica training set.

**DEC-MB18-MULTI-CURRENCY · MB-19+**

MB-18 hardcodea EUR. Multi-currency (USD · GBP · MXN para clientes
LATAM/UK) · diferido MB-19+ si cliente extranjero firma contrato.

**Inline policy**: 0 TODO/FIXME inline · todo deferrable usa
`# Future:` con session ref (`SAN-D MB-18.X-DEFERRED`).



## ADR-041 · CRM workflow comercial lead→cliente · m13_commercial extension (SAN-D MB-19.A)

**Fecha**: 2026-05-07
**Status**: Adoptada
**Stakeholders**: Marcos Mata · Claude
**Refs**: SAN-D.MB-19.A · ADR-040 (cierra SAN-D · este ADR abre cierre con
CRM operativo) · m13_commercial (extension) · m10_ens_radar (origen leads)

### Contexto

SAN-D 6/7 mega-bloques cerrados verdaderos (MB-13 sistema vivo · MB-14
portal workspace · MB-15 AI auditor · MB-16 notifications · MB-17 UI
adaptativa · MB-18 auto-billing). MB-19 cierra ciclo comercial completo
**lead → propuesta → contrato firmado → cliente activo** + migration
magic-link policy + handoff deploy. MB-19 partido en 3 sub-sesiones:

- **MB-19.A** (este ADR · 22-30h · 8 atoms) · CRM workflow comercial.
- **MB-19.B** (próximo · ADR-042 · 25-35h) · magic-link policy híbrida final
  + migration 12 continuos → portal tasks.
- **MB-19.C** (cierre SAN-D · ADRs 043/044/045 · 25-35h) · audit final +
  master spec + commercial readiness + deploy handoff + tag final
  `s13-fase-14-cliente-real-ready`.

#### Audit empírico pre-MB-19.A · briefing v2 obsoleto

Briefing v2 original proponía crear motor `m24_crm` desde cero con tablas
`leads / commercial_pipeline_stages / proposal_revisions` en inglés y
servicios `LeadService / CommercialWorkflowService / ProposalGenerator /
ContractSigningFlow / ClientUserInviteFlow`. Audit empírico repo HEAD
`38fa87c` (post-MB-18) detectó **12 discrepancias arquitectónicas mayores**:

1. Motor `m24_idms` ya ocupa M24 (Identity Management · awareness).
2. Motor `m13_commercial` ya tiene `proposal_service.py / pricing_service.py /
   discount_service.py / api.py` cubriendo dominio comercial cohesivo.
3. Tabla `leads` ya existe en `backend/app/models/commercial.py` con
   convención **español hispano** spec v2.1: `empresa_nombre · contacto_email
   · origen · estado(default "nuevo") · radar_lead_id · lead_score ·
   clasificacion_abc · asignado_a · fecha_entrada`.
4. Tabla `proposals` ya existe con `version · enviado_at · abierto_at ·
   notas_marcos · estado(draft→sent→under_review→negotiating→won→lost) ·
   pdf_path · docx_path · hitos_pago JSONB · validez_hasta · agent_19_*
   metadata pendiente`.
5. Tabla `contracts` ya existe con `firmado_marcos_at · firmado_cliente_at ·
   firmado_cliente_link_id (FK magic-link) · hash_sha256 · vigente_desde ·
   vigente_hasta · estado(draft) · tipo · plantilla_id · cliente_firmante_*
   · clausula_recursos · parametros_xyzpr`.
6. Tabla `radar_leads` (M10 ENS Radar) tiene `estado_contacto` con
   **CheckConstraint 8 estados workflow comercial v2 FASE 8.5 C2**
   ya implementado: `nuevo · enviado · respondio · reunion_agendada ·
   propuesta_enviada · ganado · descartado · no_interesa`. Comentario
   explícito en código (m10_ens_radar/db/models.py:144): "radar_leads
   (renombrado para no chocar con leads de M13)" → **decisión arquitectónica
   dominios separados** preservada.
7. Servicio `ProposalService.generate_proposal()` (m13_commercial) ya wrap
   `PricingService` (anti-alucinación económica spec v2.1 · 5 modelos
   pricing) + estados completos draft→won/lost.
8. `transition_to_phase` callable centralizado documentado **deferred MB-18**
   (DEC-MB18-WORKFLOW-TRANSITION-CALLABLE) → `auto_billing.py` adopta
   UPDATE simple `projects.fase` sin side-effects · MB-19.A NO cosecha
   (out of sub-sesión A scope · 19.C audit final lo evalúa).
9. Convención imports real: `from backend.app.X.Y` (NO `from app.X.Y` que
   propone briefing v2).
10. Agent_19 real: `from backend.app.agents.agent_19_propuestas import
    RedactorPropuestasAgent` (clase · NO función `generate_auto_proposal`
    inexistente).
11. ENS Radar lead model real: `RadarLead` (NO `EnsRadarLead`) en
    `backend.app.motors.m10_ens_radar.db.models`. Sin campo `imported_to_crm`.
12. Convención campos: **español hispano** (`empresa_ · contacto_ · fecha_ ·
    importe_ · firmado_`) · briefing v2 inglés (`organization_name ·
    contact_email · signed_at`) viola spec v2.1.

Decisión Marcos approved STOP intermedio (lección MB-13/15 estricta · >2
elementos) · pivot a v3 reajustado.

### Decisión

**MB-19.A v3 · m13_commercial EXTENSION (NO m24_crm) · español hispano
preservado · workflow radar_leads.estado_contacto reutilizado**.

#### Principio 1 · Motor m13_commercial extension cohesiva

Servicios CRM nuevos viven en `backend/app/motors/m13_commercial/services/`
junto a `proposal_service.py / pricing_service.py / discount_service.py`
existing. Modelo Lead/Proposal/Contract extendido en
`backend/app/models/commercial.py` (NO duplicación).

NO creación motor `m24_crm` (m24_idms ocupa) · NO creación `m31_crm_workflow`
(scope creep · m13 cohesivo cubre).

#### Principio 2 · Convención español hispano spec v2.1 OBLIGATORIA

Campos nuevos siguen convención existente: `estado_contacto · primer_contacto_at ·
fecha_perdida · razon_perdida · fecha_conversion · convertido_a_proyecto_id ·
temperature_level · categoria_objetivo_ens · archetype_ens · feedback_cliente ·
cambios_desde_anterior · superseded · fecha_aceptacion · agent_19_metadata`.

NO inglés (`signed_at · organization_name · source · stage`).

#### Principio 3 · Workflow comercial 8 estados (radar_leads.estado_contacto preservado)

Pipeline workflow reutiliza CheckConstraint 8 estados FASE 8.5 C2 ya
implementado en `radar_leads`:

```
nuevo → enviado → respondio → reunion_agendada → propuesta_enviada
                                                   ↓                ↘
                                                 ganado          no_interesa
                                                   ↑                ↓
                                                   ←—— descartado ←——
```

Tabla `leads` (M13) **extendida** con misma columna `estado_contacto`
mismo CHECK CONSTRAINT 8 estados. Auto-import ENS Radar→leads M13
preserva `estado_contacto` 1:1 (radar_lead.estado_contacto = lead.estado_contacto).

NO creación tabla nueva `commercial_pipeline_stages` (audit trail
movements va en tabla `lead_stage_history` lightweight española:
id · lead_id FK · estado_anterior · estado_nuevo · cambiado_por_user_id
· notas · metadata JSONB · created_at).

#### Principio 4 · Servicios existing usar · NO recrear

- **ProposalService.generate_proposal()** existing wrap PricingService
  (anti-alucinación) + estados. **Extender** con método nuevo
  `generate_revision(lead_id, feedback_cliente, importe_override?)` que
  invoca `RedactorPropuestasAgent` existing (clase · NO función) con
  contexto feedback + marca proposal anterior `superseded=True`.
- **MilestoneFactory.create_milestones_for_contract()** (`backend.app.billing.milestone_factory`)
  existing reusar para auto-conversion · genera milestones desde
  `PricingCalculator.get_milestones(categoria, total)` mapping milestones
  a workflow_phase_index canónico (10 fases ADR-026).
- **MagicLinkService.generate_magic_link()** existing reusar para signing
  flow contract · añadir `purpose=FIRMA_CONTRATO` (#36 enum 35→36 purposes)
  con TTL 72h · OTP True · geo True (firma legal vinculante).
- **m21_portal_cliente cockpit_create_user / cockpit_resend_invite** existing
  flow `PRIMER_ACCESO_CLIENTE` reusar para invite cliente post-conversión.
  NO creación `ClientUserInviteFlow` nuevo (m21 ya cubre).
- **NotificationOrchestrator.enqueue()** (`backend.app.notifications.orchestrator`)
  existing reusar para welcome email cliente · DND aware + portal SSE.
- **workflow_state.py / workflow_phase.py** existing reusar `get_current_phase`
  y `set_phase` (UPDATE simple · NO callable centralizado · DEC-MB18 deferred
  preservado).

#### Principio 5 · CommercialWorkflowService nuevo · auto-conversion lead→cliente

Servicio nuevo `backend/app/motors/m13_commercial/services/commercial_workflow_service.py`
orquesta auto-conversion cuando Contract.firmado_cliente_at registered:

1. Lead.estado_contacto → `ganado` · Lead.fecha_conversion = now()
2. Find/Create Client (por contacto_email · empresa_cif del Lead).
3. Create Project asociado a Client (categoria_objetivo desde Lead.categoria_objetivo_ens).
4. Lead.convertido_a_proyecto_id = Project.id
5. Trigger `cockpit_create_user(send_magic_link=True)` flow PRIMER_ACCESO_CLIENTE.
6. `MilestoneFactory.create_milestones_for_contract(contract.id, project.id, categoria, contract_total)`.
7. `NotificationOrchestrator.enqueue` evento welcome cliente.
8. Audit trail `lead_stage_history` row con metadata={"event":"auto_conversion","contract_id":...}

#### Principio 6 · ContractSigningFlow nuevo · magic-link FIRMA_CONTRATO

Servicio nuevo `backend/app/motors/m13_commercial/services/contract_signing_flow.py`
orquesta signing magic-link OTP+geo:

1. `send_for_signing(contract_id, recipient_email, recipient_name)`:
   genera magic-link `FIRMA_CONTRATO` (TTL 72h · OTP True · geo True) +
   envía email vía EmailSender + log.
2. `confirm_signing(token, otp, ip, user_agent, geo_lat, geo_lon)`:
   consume magic-link · UPDATE `Contract.firmado_cliente_at = now()` ·
   UPDATE `Contract.firmado_cliente_link_id = magic_link.id` ·
   trigger `CommercialWorkflowService.handle_contract_signed(contract.id)`.

`Contract.firmado_cliente_link_id` (FK magic-link) ya existing → cero
schema nuevo en contracts.

#### Principio 7 · Auto-import ENS Radar→leads M13 (Celery beat)

Worker `backend/app/motors/m13_commercial/tasks.py` task
`auto_import_radar_leads_to_commercial`:

- Pull `radar_leads` con `temperatura ∈ {ALTA, MUY_ALTA}` Y
  `estado_contacto = reunion_agendada` Y `imported_to_commercial_id IS NULL`
  Y `contactable=True`.
- Dedup: si `leads.contacto_email = radar_lead.contact_email` ya existe
  (skip · update `radar_lead.imported_to_commercial_id` apuntando lead M13).
- Crear Lead M13 con: `empresa_nombre · contacto_email · sector · origen='ens_radar'
  · radar_lead_id · estado_contacto=reunion_agendada · temperature_level
  (mapping ALTA=6/MUY_ALTA=7) · categoria_objetivo_ens · archetype_ens
  · estado='nuevo'`.
- Beat schedule: `crontab(hour=9, minute=15)` (daily 9:15 UTC).
- Idempotente: dedup en email + radar_lead_id.

NO unificación tablas `radar_leads` ↔ `leads` (decisión arquitectónica
preservada · radar_leads = oportunidades scout · leads = pipeline activo
trabajado por Marcos).

#### Principio 8 · Frontend admin pipeline kanban (extending mock existing)

`frontend/app/(admin)/admin/pipeline/page.tsx` + `PipelineKanban.tsx`
ya existing con DevHint "Leads mock — /api/v1/leads pendiente backend".

MB-19.A:
- Backend nuevo endpoint `GET /api/v1/commercial/leads?estado_contacto=X&origen=Y`
- Backend nuevo endpoint `PATCH /api/v1/commercial/leads/{id}/estado-contacto`
- Frontend conecta `PipelineKanban.tsx` a endpoints reales (drop DevHint).
- 8 columnas estado_contacto (NO 7 stages briefing v2 inglés).
- Drag&drop @dnd-kit/core (deps existing) + @tanstack/react-query mutate
  (deps existing).
- Visual coherence: shadcn Card + Badge + lucide (Thermometer · Building2
  · Award · etc) · theme tokens fulkro.

### Consecuencias

**Backend nuevo**:
- 1 migration ALTER `leads` + ALTER `proposals` + CREATE `lead_stage_history`
  (down_revision: `sand_retainer_health_001`).
- 1 servicio nuevo `LeadService` (m13_commercial/services/lead_service.py).
- 1 servicio nuevo `CommercialWorkflowService` (m13_commercial/services/commercial_workflow_service.py).
- 1 servicio nuevo `ContractSigningFlow` (m13_commercial/services/contract_signing_flow.py).
- 1 servicio existing extendido `ProposalService.generate_revision()`.
- 1 enum extendido `MagicLinkPurpose.FIRMA_CONTRATO` (#36) + PURPOSE_CONFIG entry.
- 1 worker Celery `m13_commercial/tasks.py` + beat schedule.
- 6+ endpoints REST nuevos en `m13_commercial/api.py` (CRUD leads + transitions
  + signing + revision).

**Backend modificado**:
- `commercial.py` Lead + Proposal extendidos campos nullable.
- `purposes.py` 35→36 enum + config FIRMA_CONTRATO.

**Frontend modificado**:
- `PipelineKanban.tsx` mock→real via /api/v1/commercial/leads.
- 1 page nueva opcional `/admin/pipeline/leads/[id]` lead detail (agregada
  si scope encaja · si no diferida 19.C).

**Migrations**:
- 1 migration: `sand_crm_lead_extensions` ALTER nullable + CREATE
  `lead_stage_history`. NO drop columns existing (cero breaking).

**Tests nuevos**:
- backend: 15+ unit tests (LeadService transitions · CommercialWorkflowService
  conversion · ProposalService.generate_revision · ContractSigningFlow
  send/confirm · Celery auto-import dedup).
- E2E: 6+ Playwright specs stack real (kanban drag-drop · lead detail ·
  proposal revision · contract signing OTP · auto-conversion verification).

**Cumulative regression**:
- Suite backend: target 3597+ → 3612+ passed (+15 nuevos · 0 regresión).
- Playwright admin: 32/33 verde + 6 nuevos verde stack real.
- alembic head: `sand_crm_lead_extensions` post-MB-19.1.

### Trazabilidad

- `backend/app/models/commercial.py:15` · Lead model existing extendido.
- `backend/app/models/commercial.py:34` · Proposal model existing extendido.
- `backend/app/models/commercial.py:57` · Contract model existing (sin tocar).
- `backend/app/motors/m10_ens_radar/db/models.py:142` · RadarLead origen
  auto-import (estado_contacto 8 estados CheckConstraint).
- `backend/app/motors/m13_commercial/proposal_service.py:30` · ProposalService
  existing extendido método `generate_revision`.
- `backend/app/motors/m13_commercial/api.py` · API existing extendida
  endpoints CRM.
- `backend/app/motors/m12_magic_link/purposes.py:21` · MagicLinkPurpose
  enum 35→36.
- `backend/app/billing/milestone_factory.py:93` · MilestoneFactory existing
  reusado.
- `backend/app/motors/m21_portal_cliente/api.py:642+742` · cockpit_create_user
  + cockpit_resend_invite reusado.
- `backend/app/notifications/orchestrator.py:88` · NotificationOrchestrator
  existing reusado (`enqueue()`).
- `backend/app/agents/agent_19_propuestas.py` · RedactorPropuestasAgent
  existing reusado para revisions.
- `frontend/components/pipeline/PipelineKanban.tsx` · existing extendido
  mock→real.
- `frontend/app/(admin)/admin/pipeline/page.tsx` · existing actualizado.
- ADR-040 (cierre auto-billing MB-18) · ADR-039 (orchestrator MB-16).
- ADR-026 (workflow_phase 10 fases · `projects.fase`).

### Diferencias vs briefing v2 archivado

| Tema | v2 (descartado) | v3 vigente |
|------|-----------------|------------|
| Motor | `m24_crm` nuevo (colisión m24_idms) | `m13_commercial` extension |
| Schema leads | tabla nueva inglés (organization_name · stage) | ALTER existing español (empresa_nombre · estado_contacto) |
| Pipeline | `commercial_pipeline_stages` 7 stages inglés | reutiliza `radar_leads.estado_contacto` 8 estados español + `lead_stage_history` audit |
| Proposals | `proposal_revisions` tabla nueva | ALTER `proposals` existing + métodos `generate_revision` |
| Imports | `from app.X` | `from backend.app.X` |
| Agent_19 | función `generate_auto_proposal` (inexistente) | clase `RedactorPropuestasAgent` (existing) |
| ENS Radar | `EnsRadarLead.imported_to_crm` (inexistente) | `RadarLead.imported_to_commercial_id` (campo nuevo nullable) |
| Idioma | inglés saas | español hispano spec v2.1 |
| ClientUserInviteFlow | servicio nuevo | reusa m21 `cockpit_create_user` flow PRIMER_ACCESO_CLIENTE |
| ProjectFactory | servicio nuevo | direct ORM Project insert (factory NO existing) |
| transition_to_phase cosecha | sí cosecha MB-18 deferred | NO cosecha (DEC-MB18 preservado · diferir 19.C) |
| Estimación | 30-40h | 22-30h (-8h reuso) |

### Deferrables MB-19.A documentados (no son deuda)

Lista cerrada al cierre tag intermedio `s13-mb19a-crm-cerrado`. Re-asignación
requiere ADR nuevo o extensión ADR-041 explícita · NO ad-hoc.

**DEC-MB19A-PROPOSAL-CLIENT-PREVIEW · MB-19.B+**

Vista pública cliente `/proposal-preview/{magic_link_token}` para que
cliente vea proposal DOCX/PDF antes de firmar contrato · diferida MB-19.B
(cuando magic-link migration cubre `APROBACION_PROPUESTA` end-to-end).
MB-19.A: Marcos envía PDF manual por email + cliente firma contrato directo.

**DEC-MB19A-LEAD-DETAIL-PAGE · MB-19.C**

Page detalle lead `/admin/pipeline/leads/[id]` con tabs (Overview · Activity ·
Proposals · Contract · Notes) · diferida 19.C audit final si scope encaja.
MB-19.A: kanban card opens lateral panel ligero (no full page).

**DEC-MB19A-RECENT-ACTIVITY-CARD · MB-19.C**

`RecentActivityCard` admin panel deepening · diferido 19.C audit final
(ya documentado deferrable MB-17).

**DEC-MB19A-INBOX-CROSS-PROJECT · MB-19.C**

Vista inbox cross-project leads + clientes activos · diferido 19.C audit
final.

**DEC-MB19A-CRM-DASHBOARD-ROI · MB-19.C+**

Dashboard `/admin/crm/conversions` con métricas ROI per source (ens_radar
vs referral vs cold_outreach · conversion rate · time-to-close · CAC) ·
diferido 19.C+ si scope encaja. MB-19.A: solo kanban + auto-import.

**DEC-MB19A-MULTI-USER-ASSIGNMENT · post-SAN-D**

Lead assignment a múltiples consultores `assigned_to_user_id` IS lista
con lock-tenure rotation · diferido post-SAN-D. MB-19.A: 1 consultor
(Marcos) · `asignado_a` String existing.

**DEC-MB19A-PROPOSAL-AB-TESTING · post-SAN-D**

A/B testing proposals (variant A vs B engagement metrics) · diferido
post-SAN-D · cero datos training piloto.

**DEC-MB19A-LEAD-SCORING-ML · post-SAN-D**

Lead scoring ML (random forest score per propensity-to-close basado en
features sector/empleados/temperature) · diferido post-SAN-D. MB-19.A:
`lead_score` String existing populated heurístico opcional.

**DEC-MB19A-CONTRACT-SIGNING-VIDEO-IDV · post-SAN-D**

Video identity verification durante signing (selfie + DNI scan) · diferido
post-SAN-D. MB-19.A: OTP+geo suficiente para B2B no-bancario.

**DEC-MB19A-PROPOSAL-GAMIFICATION · NUNCA**

Gamification proposals (badges · rewards · streaks) · descartado
permanentemente · cero alineación target B2B consultoría seria ENS.

**Inline policy**: 0 TODO/FIXME inline · todo deferrable usa
`# Future:` con session ref (`SAN-D MB-19.A-DEFERRED`).

### Lección

**Audit pre-impl previene duplicación masiva**.

Briefing v2 propuso 12 tablas/services/imports incompatibles con repo HEAD
real. Audit empírico de 30 min (lección MB-13/15 ≥3 elementos = STOP)
detectó conflictos antes ejecutar 8 atoms · evitó:
- Colisión motor `m24` (idms vs crm).
- Tablas duplicadas `leads` × 2 (M13 español vs m24_crm inglés).
- Tablas duplicadas `proposals` × 2.
- Convención inglés mezclada con español hispano spec v2.1.
- Servicios re-implementados (ProposalService existing vs ProposalGenerator nuevo).

Pivot v3 (m13 extension · español preservado · workflow radar_leads
reusado) ahorra 8-10h ejecución directa + 20-30h regresión potencial
post-merge si v2 hubiera procedido.

**Reuso > recreación cuando dominio existe cohesivo**. m13_commercial
ya cubre proposals + pricing + discount · MB-19.A solo añade lead
lifecycle + workflow CRM + signing flow encima · cero refactor masivo.

**Convención idioma es decisión arquitectónica · no preferencia**.
Spec v2.1 español hispano coherente con M10 ENS Radar (estado_contacto)
y M14 Contracts (firmado_marcos_at) y todo el dominio. Inglés saas-style
romperia coherencia auditable ENAC.



## ADR-042 · Magic-link policy híbrida final (post-SAN-D MB-19.B)

**Fecha**: 2026-05-07
**Status**: Adoptada
**Stakeholders**: Marcos Mata · Claude
**Refs**: SAN-D.MB-19.B · ADR-038 (portal cliente workspace) ·
ADR-039 (notification orchestrator) · ADR-041 (CRM workflow m13)

### Contexto

Briefing MB-19 v2 propuso clasificar 35 purposes magic-link (post FASE 4.5
ADR-011 + SAN-B MB-6.6 drop AUTORIZACION_PENTEST + SAN-D MB-19.4 add
FIRMA_CONTRATO) en:
- **23 ONE-SHOT legítimos** mantienen razón existir (firmas OTP+geo ·
  descargas one-time · pentester externo · auditor externo).
- **12 CONTINUO migrables** a portal cliente workspace tareas (MB-14.3
  ClientTaskService cubre sustitución).

#### Audit empírico pre-MB-19.B · briefing v2 obsoleto

Audit empírico repo HEAD `342eb8e` (post-MB-19.A) detectó **9 purposes
del listado v2 NO existen en enum real**:

```
DDA_REVIEW · PDA_REVIEW · MANUAL_SGSI_REVIEW · ENCUESTA_AUTOEVALUACION
· ACEPTACION_TASK_BLOQUE · CHAT_RESPONSE · PROFILE_UPDATE ·
NOTIFICATION_PREFERENCES · PAYMENT_ACKNOWLEDGE
```

Briefing v2 listaba 12 CONTINUO migration · realidad: **2 purposes
legítimamente migrables** + 1 ONE-SHOT confundido como CONTINUO en v2:

1. **ONBOARDING_INICIAL** · cubierto por `cockpit_create_user`/
   `cockpit_resend_invite` (m21 PRIMER_ACCESO_CLIENTE flow existing
   MB-14) · magic-link onboarding redundante post-portal.
2. **APORTE_EVIDENCIA** · cubierto por portal `/client-portal/evidencias`
   upload UI (MB-14.7 EvidenciasUploadAPI existing) · magic-link
   evidencia redundante post-portal.
3. **ENCUESTA_SATISFACCION_NPS** (briefing v2 listaba) · realmente
   **ONE-SHOT legítimo** · 30d max_uses 1 NPS · cliente puede no estar
   logueado portal cuando responde survey externa · MANTIENE.

Total post-pivot v3: **33 mantienen + 2 deprecated soft**.

#### Recálculo categorías 35 purposes (post-MB-19.4)

**Categoría A · Firmas legales OTP±geo (10 purposes)**:
- FIRMA_DOCUMENTO (m01/m02/m03/m14/m_meetings)
- FIRMA_CONTRATO (m13 SAN-D MB-19.4 ADR-041)
- APROBACION_ACTA (m18 minutes)
- AUTORIZAR_VERIFICACION_TECNICA (m08)
- AUTORIZAR_PENTEST_EXTERNO (m08 v5.1)
- ACEPTACION_RIESGO_RESIDUAL (m19 risk · #29)
- VALIDACION_CAMBIO_ALCANCE (m28 change governance · #28)
- CONSENTIMIENTO_TRATAMIENTO_DATOS (DPA RGPD · #31)
- CONFIRMACION_CONFORMIDAD (pre-ENAC · #32)
- VOTACION_COMITE_SEGURIDAD (CSF · #34)

**Categoría B · Aprobaciones comerciales OTP±geo (3 purposes)**:
- APROBACION_PROPUESTA (#25 · ADR-011)
- APROBACION_FACTURA (#26 · pre-envío oficial)
- AUTORIZACION_ACCION_REMOTA (admin ops crítico)

**Categoría C · Descargas one-shot/limitadas (8 purposes)**:
- DESCARGA_DOSSIER_FINAL (cliente dossier final 7d/3uses · OTP)
- DESCARGA_BACKUP_ARCHIVO (m25 grace 60d/20uses · OTP)
- DESCARGA_CERTIFICADO_CONFORMIDAD (post-ENAC 30d/10uses)
- REPORTE_TRIMESTRAL (60d/10uses · auditor + cliente retainer)
- REPORTE_ANUAL (90d/20uses · auditor + cliente retainer)
- RESPUESTA_REQUERIMIENTO_AUDITOR (#auditor 48h OTP · ENS art.31)
- COMUNICACION_INCIDENTE_SEGURIDAD (24h crítico · #30 NIS2)
- INVITACION_REUNION (#24 · 7d/1use · confirm asistencia)

**Categoría D · Acceso externo continuo (4 purposes)**:
Cuentas externas NO ClientUser · razón mantenida fuerte:
- PORTAL_PENTESTER_EXTERNO (60d/9999uses · pentester externo)
- PORTAL_REMEDIACION (90d/9999uses · IT cliente uso continuado)
- REVISAR_INFORME_VERIFICACION (15d/5uses · auditor revisión)
- RENEWAL_CAMPAIGN_DETAILS (120d/5uses · campaña bianual)

**Categoría E · Workflow lifecycle/portal cliente (5 purposes)**:
- PRIMER_ACCESO_CLIENTE (24h OTP · primer login portal cliente)
- OFERTA_RETAINER (m25 paso 4 · 30d decisión)
- RECONSIDERACION_RETAINER (60d retainer pre-borrado)
- RETAINER_WELCOME (7d/3uses · welcome retainer)
- NORMATIVA_ALERT_CRITICAL (7d/5uses · alertas portal)

**Categoría F · Auxiliares (3 purposes)**:
- APROBACION_OBLIGACION (3d · obligación cliente)
- SOLICITUD_INFORMACION (#27 · 14d/5uses · async preguntas)
- ENCUESTA_SATISFACCION_NPS (#35 · 30d/1use · survey externa)

**Total Categoría A-F**: 10+3+8+4+5+3 = **33 mantienen**.

**Deprecated soft (2 purposes · migración datos · warning header)**:
- ONBOARDING_INICIAL → portal first-login (cockpit_create_user MB-14)
- APORTE_EVIDENCIA → portal /evidencias (MB-14.7 EvidenciasUploadAPI)

**Total**: 33 + 2 = 35 purposes (matches enum count post-MB-19.4).

### Decisión

**Política híbrida soft-deprecation**:

#### Principio 1 · MagicLinkPolicyEnforcer service · validate_purpose

Servicio nuevo `backend.app.motors.m12_magic_link.policy_enforcer.MagicLinkPolicyEnforcer`
expone `validate_purpose(purpose: MagicLinkPurpose) -> tuple[bool, str, str]`:

- `(True, "ok", "")` para 33 mantienen.
- `(True, "deprecated_soft", "{razón} · usar portal X · ver ADR-042")`
  para 2 deprecated · **NO bloquea** generación (compatibilidad backward
  sites legacy m05/m16 que aún invocan).
- `(False, "unknown_purpose", "{value!r} no en enum")` para purpose
  ausente.

NO hard-block (`raise ValueError`) · NO breakage clients existentes ·
sólo log warning + header `X-Deprecated-Purpose` en respuesta API.

#### Principio 2 · Migration data script idempotente

Script `backend/app/scripts/migrate_magic_links_to_tasks.py` (ejecutable
manual + idempotente · safe re-run):

1. Pull MagicLinks activos (no consumidos · no expirados · no revocados)
   con `tipo_operacion ∈ {ONBOARDING_INICIAL, APORTE_EVIDENCIA}`.
2. Por cada uno:
   - Si MIGRATION_LOG ya tiene row con magic_link_id → skip (idempotente).
   - Find ClientUser asociado al project (primer ClientUser activated).
   - Si NO ClientUser yet (lead phase) → log `pending_review` ·
     migration manual cuando cliente onboarding completed.
   - Si ClientUser existe → create ClientTask equivalente:
     - template_id: `migrated_from_<purpose>_<ml_id_short>` (UNIQUE)
     - phase: project.fase actual (resolver desde Project)
     - title/description: mapping per purpose (yaml lookup)
     - cta_url: `/client-portal/{flujo_portal}` (onboarding/evidencias)
     - metadata_jsonb: `{"migrated_from_magic_link": "{ml_id}",
       "original_purpose": "{purpose}", "migrated_at": "...."}`
   - Revoke magic_link (revocado=True · revoke_reason="migrated_to_portal_task").
   - Insert MIGRATION_LOG row.

3. Stats output: `{converted_count, pending_review_count, errors,
   started_at, finished_at}`.

#### Principio 3 · Tabla magic_link_migration_log audit trail

Tabla nueva `magic_link_migration_log` (migration `sand_magic_link_migration`):

```
id UUID PK · gen_random_uuid()
magic_link_id UUID NOT NULL · FK magic_links.id (NO CASCADE preserva
  audit trail si magic_link soft-deleted)
original_purpose VARCHAR(50) NOT NULL
migration_action VARCHAR(30) NOT NULL CHECK IN
  ('converted_to_task', 'revoked_obsolete',
   'kept_one_shot', 'pending_review')
target_task_id UUID NULL · FK client_tasks.id
notes TEXT NULL
processed_at TIMESTAMPZ DEFAULT NOW() NOT NULL
UNIQUE (magic_link_id) · idempotencia
```

#### Principio 4 · Deprecation soft sites legacy

Sites m05 (`/api/v1/obligations/{id}/aporte-link`) y m16 onboarding
service que invocan ONBOARDING_INICIAL/APORTE_EVIDENCIA:

- **NO se eliminan endpoints** (backward compat sites externos puedan
  invocar) · agregar response header `X-Deprecated: portal-task-replacement
  · ver ADR-042` + log warning.
- **NO se rechaza generation** · enforcer.validate_purpose retorna
  warning string · service log + header.
- Documentación API endpoint actualizada con `@deprecated` marker.

Hard-deprecation (raise + 410 Gone) · diferida MB-20+ post-feedback
clientes piloto verifique migration completa sin breakage.

#### Principio 5 · ClientUserInviteFlow extension cockpit_create_user

Cosecha pendiente MB-19.A (DEC-MB19A nota implícita): extender
`cockpit_create_user` flow con:

- **first_login_token TTL extendido**: actualmente PRIMER_ACCESO_CLIENTE
  TTL=24h. Extension MB-19.B permite override TTL via param `first_login_ttl_hours`
  (rango 24-168h · default 24h conservador).
- **Welcome email orchestrator hook**: post-create + magic-link generated
  · NotificationOrchestrator.enqueue evento `client_user_invited`
  (event_category=onboarding · DND aware · template `client_user_invited.html`).
- **Workflow lifecycle hook**: si project.lifecycle_state=DRAFT →
  ascendido a NEGOTIATING (cliente recibió invite · ya no es solo lead).

NO crear `ClientUserInviteFlow` service nuevo paralelo · extension
in-place de cockpit_create_user en `m21_portal_cliente/api.py`.

### Consecuencias

**Backend nuevo**:
- 1 service nuevo: `m12_magic_link/policy_enforcer.py:MagicLinkPolicyEnforcer`.
- 1 migration: `sand_magic_link_migration` create magic_link_migration_log.
- 1 model: `m12_magic_link/models_migration_log.py:MagicLinkMigrationLog`.
- 1 script: `backend/app/scripts/migrate_magic_links_to_tasks.py`.
- 1 helper YAML: `m12_magic_link/migration_mappings.yaml` (purpose → task template).

**Backend extendido**:
- `m12_magic_link/service.py:generate_magic_link` → invoca enforcer
  pre-generation · log warning + header X-Deprecated en response si soft-deprecated.
- `m21_portal_cliente/api.py:cockpit_create_user` → param opcional
  `first_login_ttl_hours` + welcome email orchestrator hook + lifecycle
  ascend hook.
- `m05_obligations/api.py` + `m16_onboarding/service.py` → log warning
  generación soft-deprecated.

**Tests nuevos**:
- backend pytest: ≥10 tests (PolicyEnforcer + migration script idempotente
  + cockpit_create_user extensions + 33 vs 2 categorización).
- E2E Playwright: ≥4 specs cosecha MB-17 authguard refactor +
  ≥2 nuevos magic-link migration smoke.

**Cumulative regression cero**: existing 35 purposes generation sites
no rompen (warning soft no error).

**alembic head** post-MB-19.B: `sand_magic_link_migration`.

### Trazabilidad

- `backend/app/motors/m12_magic_link/purposes.py:17` · enum 35 purposes.
- `backend/app/motors/m12_magic_link/service.py:207` · generate_magic_link
  punto de invocación enforcer.
- `backend/app/motors/m21_portal_cliente/api.py:642+742` · cockpit_create_user
  + cockpit_resend_invite extension.
- `backend/app/motors/m21_portal_cliente/task_service.py` · ClientTaskService
  reusado para client_tasks creation desde migration script.
- `backend/app/motors/m21_portal_cliente/task_templates_loader.py` · YAML
  templates pattern reusado en migration_mappings.yaml.
- `backend/app/notifications/orchestrator.py:88` · NotificationOrchestrator.enqueue
  reusado welcome email hook.
- `backend/app/models/operations.py:MagicLink` · tabla magic_links existing.
- `backend/app/motors/m21_portal_cliente/models_tasks.py:ClientTask` · target migration.
- ADR-038 · ADR-039 · ADR-041 (precondición).

### Diferencias vs briefing v2 archivado

| Tema | v2 (descartado) | v3 vigente |
|------|-----------------|------------|
| Cuenta total | "35 purposes" | 35 verificado empírico (post FASE 4.5 + SAN-B drop + MB-19.4 add) |
| CONTINUO migración | 12 listados | 9 NO existen en enum real · 2 reales migrables (ONBOARDING_INICIAL · APORTE_EVIDENCIA) |
| ENCUESTA_SATISFACCION_NPS | "CONTINUO" | ONE-SHOT legítimo (1 use NPS · cliente survey externa) |
| Hard-deprecation | raise ValueError + 410 Gone | Soft warning + X-Deprecated header (compat backward) |
| ClientUserInviteFlow | servicio nuevo | extension in-place cockpit_create_user m21 |
| Estimación | 25-35h · 6 atoms | 18-25h · 6 atoms (-7-10h por audit empírico evita scope creep) |

### Deferrables MB-19.B documentados (no son deuda)

Lista cerrada al cierre tag intermedio `s13-mb19b-magic-link-cerrado`.
Re-asignación requiere ADR nuevo o extensión ADR-042 explícita.

**DEC-MB19B-HARD-DEPRECATION-410-GONE · MB-20+**

Hard-deprecation completa endpoints ONBOARDING_INICIAL/APORTE_EVIDENCIA
con HTTP 410 Gone · diferida MB-20+ post-feedback piloto verifique
migration completa sin breakage en sites legacy externos.

**DEC-MB19B-MIGRATION-CRON-AUTOMATIC · MB-20+**

Celery beat task daily ejecutar migration_script automático ·
diferido MB-20+. MB-19.B: ejecución manual via CLI script (Marcos
runs cuando incrementa volumen magic-links activos pre-portal).

**DEC-MB19B-PURPOSE-LIFECYCLE-WARNING-EMAIL · MB-19.C**

Email cliente automático "tu magic-link X fue migrado a portal task ·
acceder portal aquí" · diferido MB-19.C audit final si scope encaja.

**DEC-MB19B-MIGRATION-DASHBOARD-ADMIN · MB-20+**

UI admin dashboard `/admin/migration` mostrando magic_link_migration_log
con stats per purpose + chart conversion rate · diferido MB-20+.

**DEC-MB19B-PORTAL-DIRECT-LINKS · MB-19.C**

Email auto-sent post-migration con link directo `/client-portal/{flujo}`
en lugar de magic-link consumir · diferido MB-19.C (requiere portal
cliente lifecycle hook MB-14.5 chat extension).

**DEC-MB19B-MULTI-WORKSPACE-MIGRATION · post-SAN-D**

Cliente con múltiples workspaces (multi-tenant) · migration por workspace
· diferido post-SAN-D · cero clientes multi-workspace pre-cliente real.

**DEC-MB19B-AUDITOR-EXTERNAL-INVITE-FLOW · post-SAN-D**

Auditor ENAC externo invite flow (no ClientUser) extendido con
PRIMER_ACCESO_AUDITOR purpose · diferido post-SAN-D · cero auditores
externos primera fase.

**DEC-MB19B-ROTATION-KEYS-ED25519 · post-SAN-D**

Rotación periódica claves Ed25519 firma magic-link tokens · diferido
post-SAN-D + ENS art.31 verificación bienal cuando aplique.

**DEC-MB19B-MB17-AUTHGUARD-COSECHA · MB-19.C**

Cosecha 4 specs MB-17 authguard refactor (`mb17_arquetipo_sector_salud.spec.ts:130`
+ `mb17_client_portal_categoria.spec.ts:50/74/99`) de page.route mocks →
loginAsClient real auth · diferida MB-19.C audit final por:

- Requiere 4 projects fixtures BD (BASICA · MEDIA sector_salud admin ·
  MEDIA sector_salud cliente · ALTA) con ClientUsers asociados al
  cliente E2E synthetic + lifecycle setup completo.
- Requiere extension globalSetup.ts crear projects fixtures (idempotente)
  vía /api/v1/_dev/create-test-projects-with-categorias endpoint nuevo.
- Trabajo no encaja naturalmente en MB-19.B atom 19.13 (scope magic-link
  migration · NO portal cliente category banners refactor).

MB-19.B mantiene 4 specs MB-17 funcionales con mocks · cobertura UI
preserved · MB-19.C audit final ejecuta cosecha completa cuando ya
existen fixtures BD admin pipeline post-MB-19.A.

**Inline policy**: 0 TODO/FIXME inline · todo deferrable usa
`# Future:` con session ref (`SAN-D MB-19.B-DEFERRED`).



## ADR-043 · SAN-D learnings + iterative pattern (cierre SAN-D MB-19.C)

**Fecha**: 2026-05-07
**Status**: Adoptada
**Stakeholders**: Marcos Mata · Claude
**Refs**: SAN-D · MB-13 → MB-19.C · ADRs 035-042

### Contexto

SAN-D · 9 mega-bloques (MB-13 → MB-19.A/B/C) · 247-346h ajustadas a
realidad audit empírico per atom · cero regresión cumulative · 13/13
puntos visión Marcos cubiertos verde (ver `docs/audit/SAN_D_FINAL_AUDIT.md`).

Esta sub-sesión 19.C cierra SAN-D total · ADR-043 documenta lecciones
metodológicas estructurales aplicables SAN-E roadmap + futuras sesiones.

### Lecciones SAN-D consolidadas

**Lección 1 · Audit empírico per atom > tests pasando**

SAN-A.A1 reveló 73 vs 80 medidas declaradas · tests verdes ocultaban
bug schema. SAN-D aplicó V-CHECK ADR-034 v2 con smoke curl real + path
match grep + alembic head verde + tsc + npm build per atom · evita
falsos positivos suite verde sin verificación empírica fin-a-fin.

Aplicación SAN-E: cada atom incluye smoke endpoint real (curl 2xx/4xx)
+ verificación visual coherence + dead links gate before commit.

**Lección 2 · Provider abstraction desde día 1**

PostmarkEmailProvider (MB-16 · ADR-039) · ManualTransferProvider (MB-18 ·
ADR-040) · DeepLinkGenerator m12 magic-link (FASE 4.5 · ADR-011). Cambiar
provider = 1 archivo · NO refactor masivo.

Aplicación SAN-E: si emerge necesidad Stripe/Tink/etc · slot provider
ya existe · plug-in implementación + activar via config flag.

**Lección 3 · YAML-driven > if/else hardcoded**

`feature_flags.yaml` (MB-17) · `task_templates.yaml` (MB-14 · 18 templates) ·
`notification_templates.yaml` (MB-16 simplified) · `migration_mappings.yaml`
(MB-19.11 · ADR-042). Single source of truth · mantenible · auditable
ENAC compliance.

Aplicación SAN-E: cualquier configuración multi-cliente o multi-categoría
requiere YAML loader pattern + tests YAML structure validation.

**Lección 4 · Hybrid policies > "todo o nada"**

Magic-links policy (ADR-042): 33 ONE-SHOT/CONTINUO_LEGÍTIMO + 2
deprecated soft. Notifications (ADR-039): email primario + wa.me link
opcional (NO Meta API). Payments (ADR-040): transferencia manual default
+ Tink opcional futuro deferred.

Aplicación SAN-E: identificar dominios donde "todo X" es overengineering ·
preferir hybrid pragmático con deferrables documentados.

**Lección 5 · Atomic commits per concern · NO bulk**

19 atoms MB-19 (8 sub-A + 6 sub-B + 5 sub-C) · 6 atoms MB-13 · audit
trail granular git log · diff stat per atom acota scope creep · facilita
revert atómico si problema emerge post-merge.

Aplicación SAN-E: 1 atom = 1 concern = 1 commit · target 200-800 líneas
diff per commit · si excede · split sub-atoms.

**Lección 6 · STOP intermedio reportar > ejecutar fuera scope**

MB-13/15 STOP intermedio aplicado por discrepancias arquitectónicas >2.
MB-19.A pivot v3 (audit briefing v2 detectó 12 discrepancias · m24_idms
colision + tablas duplicadas + idioma + servicios) · ahorrro 8-10h
ejecución directa + 20-30h regresión potencial.

Aplicación SAN-E: cada nuevo briefing requiere audit pre-impl 30min ·
si >2 discrepancias arquitectónicas · STOP + reporte + pivot vN+1.

**Lección 7 · Convención idioma es decisión arquitectónica**

Spec v2.1 español hispano coherente con M10 ENS Radar (estado_contacto)
y M14 Contracts (firmado_marcos_at) y todo el dominio. Inglés saas-style
romperia coherencia auditable ENAC compliance ante auditor externo.

Aplicación SAN-E: NO inglés saas-mixto · español hispano consistent
para auditor ENAC verificación bienal art.31.

**Lección 8 · Reuso > recreación cuando dominio existe cohesivo**

m13_commercial extension MB-19.A (NO m24_crm parallel) · cockpit_create_user
extension MB-19.10 (NO ClientUserInviteFlow paralelo) · ProposalService
extension generate_revision (NO ProposalGenerator paralelo).

Aplicación SAN-E: nuevo feature SIEMPRE audit dominio existing primero ·
extender > recrear cuando cohesivo · documentar decisión arquitectónica
en ADR si justifica.

**Lección 9 · Soft-deprecation > hard-deprecation cuando legacy activos**

ADR-042 magic-link policy: warning + header X-Deprecated + sites legacy
m05/m16 mantienen funcionalidad backward compat. Hard-deprecation 410
Gone diferida MB-20+ post-feedback piloto verifique migration sin breakage.

Aplicación SAN-E: cualquier deprecation API pública requiere transition
period 1+ MB con warning visible · hard-block solo post-validación
empírica zero usage legacy.

**Lección 10 · Documentación de decisiones inmediata · NO post-hoc**

8 ADRs (035-042) escritos durante atom inicial cada MB · NO al final ·
preserva razón decisión + alternativas consideradas + diferencias vs
briefing antes que olvidar.

Aplicación SAN-E: ADR escrito en atom 0 (briefing parsing) · iterado
durante implementación si emerge nueva información · cerrado al cierre
mega-bloque con sección Deferrables.

### Patrón iterativo SAN-D consolidado · template SAN-E

```
PER MEGA-BLOQUE:
  1. Audit pre-impl 30 min (verificar briefing vs realidad código)
  2. STOP intermedio si >2 discrepancias arquitectónicas
  3. Pivot vN+1 documentado en ADR + briefing v3
  4. Atom 0: ADR draft + estructura
  5. Atoms 1+: implementación con V-CHECK 10 verificaciones
  6. Cosechas in-place de deferrables compatibles scope
  7. Tests stack real Playwright + pytest backend per atom
  8. Smoke curl + tsc + npm build per atom
  9. Atom final: V-CHECK acumulado + tag intermedio + handoff next
```

### Consecuencias

- ADR-034 v2 V-CHECK 10 verificaciones · contínuamente vigente.
- Lección MB-13/15/19 STOP intermedio · documentada como regla SAN-E.
- Patrón "extension > recreación" preservado en futuras refactorizaciones.
- Auditor externo ENAC art.31: documentación trazable per decisión.

### Trazabilidad

- ADR-034 v2 (V-CHECK 10) · ADR-035 a ADR-042 (8 ADRs SAN-D).
- `docs/audit/SAN_D_FINAL_AUDIT.md` (13/13 puntos visión).
- Git tags `s13-mb13-...` a `s13-mb19b-magic-link-cerrado` (8 tags
  intermedios) + `s13-fase-14-cliente-real-ready` (tag final 19.18).

### Lección recursiva

**El proceso SAN-D mismo es lección reproducible**: 9 mega-bloques con
audit empírico + STOP intermedio + ADR documentado + cosechas in-place +
deferrables formales = 0 regresión + 13/13 visión Marcos cubierta. Patrón
aplicable SAN-E roadmap (auditoría compliance RGPD + ISO 27001 readiness
+ pentesting interno + performance tuning · cada uno con V-CHECK 11
verificaciones · ADR + deferrables · tag intermedio + final).



## ADR-044 · Commercial readiness checklist (cierre SAN-D MB-19.C)

**Fecha**: 2026-05-07
**Status**: Adoptada
**Stakeholders**: Marcos Mata · Claude
**Refs**: SAN-D · ADR-043 · 13 puntos visión Marcos audit

### Contexto

Marcos requiere checklist objetivo · "primer cliente real ready cuando".
Diferenciar:
- **Technical readiness** (código + infra · checklist técnico).
- **Commercial readiness** (legal + marketing + ventas · checklist comercial).
- **Operational readiness** (deploy + backup + monitoring · checklist
  ADR-045 deploy handoff procedure).

### Decisión

**Marcos acepta primer cliente real cuando 100% de items checklist
técnico-comercial-legal verde**.

#### Checklist 1 · Technical readiness (post-SAN-D · pre-deploy)

- [X] Suite backend ≥3505 passed · 0 regresión SAN-D introducida
- [X] tsc 0 errors + npm run build verde 44+ pages
- [X] alembic head: sand_magic_link_migration (post-MB-19.B)
- [X] Playwright admin specs cumulative ≥36+ verde stack real (post-19.16)
- [X] 13/13 puntos visión Marcos cubiertos (audit `SAN_D_FINAL_AUDIT.md`)
- [X] 8 ADRs documentados (035-042) · cero TODO/FIXME inline
- [X] Magic-link 35 purposes categorizado ADR-042 (33 mantienen + 2 deprecated)
- [X] CRM workflow lead→cliente operativo · MB-19.A m13_commercial extension
- [X] Auto-billing + retainer + churn predictor (MB-18) operativos
- [X] AI auditor + Magerit Libro II + sector overlays (MB-15) operativos
- [X] Portal cliente workspace + tareas + chat (MB-14) operativo
- [X] Notification orchestrator email + wa.me (MB-16) operativo

#### Checklist 2 · Commercial readiness (pre-cliente piloto)

- [ ] Hetzner CPX21 deploy producción aplicado (Sesión 12 · ADR-045)
- [ ] Dominio `app.fulkro.es` HTTPS Let's Encrypt configured
- [ ] Dominio `portal.fulkro.es` HTTPS configured (split admin/client)
- [ ] Backup Postgres diario automatizado pgbackrest (Celery beat existing)
- [ ] Postmark API key producción + domain verified (`fulkro.es` SPF/DKIM/DMARC)
- [ ] Email `contact@fulkro.es` funcional + responder SLA <2h definido
- [ ] LinkedIn business profile actualizado · linked CTA web
- [ ] Plantilla email cold outreach drafted (3 variantes · sector_salud + AAPP + privado)
- [ ] Calendar booking link (Calendly o Cal.com · 30min reunión exploratoria)
- [ ] Términos servicio publicados portal `/legal/terminos`
- [ ] Política privacidad publicada `/legal/privacidad` (RGPD compliance)
- [ ] Bullet defensivo "soporte chat <2h" advertised landing page
- [ ] CIF FULKRO + dirección fiscal + datos IBAN preparados (auto_billing settings)
- [ ] Plantilla contrato servicios spec v2.1 reviewed por abogado externo
- [ ] DPA template (acuerdo encargado tratamiento RGPD) preparado

#### Checklist 3 · Operational readiness (post-deploy · monitoring)

- [ ] Sentry/Datadog APM configured (errores + performance tracking)
- [ ] Status page público (Uptime Robot o BetterUptime free tier)
- [ ] Runbook básico OPS (rollback migration · restart services · DB backup recovery)
- [ ] Plan respuesta incidente seguridad (24h notification ENS art.31)
- [ ] Documentación interna `/docs/HANDOFF_SESION_12.md` (deploy procedure)
- [ ] Documentación interna `/docs/RUNBOOK.md` (operational procedures)
- [ ] Backup test restore mensual programado (Celery beat o cron manual)
- [ ] Rotation Ed25519 keys (FULKRO_AUTH_PRIVATE_KEY · FULKRO_ML_PRIVATE_KEY)
  documented · primera rotation diferida MB-20+ (DEC-MB19B-ROTATION-KEYS-ED25519)

### Checklist post-cliente real (SAN-E roadmap)

Después del primer cliente real cierro · iterar sobre:

- **SAN-E.1 · Auditoría compliance RGPD interna** (FULKRO mismo · DPIA + ROPA)
- **SAN-E.2 · ISO 27001 readiness FULKRO mismo** (gap analysis vs Anexo A)
- **SAN-E.3 · Soberanía datos · cifrado at-rest** (PostgreSQL TDE · pentesting interno)
- **SAN-E.4 · Performance tuning bajo carga real** (post-baseline ADR-045)
- **SAN-E.5 · Multi-cliente improvements** (basado en feedback piloto)

### Consecuencias

- Tag final `s13-fase-14-cliente-real-ready` aplicado solo cuando
  Checklist 1 · Technical readiness verde 100% (atom 19.18 V-CHECK 11).
- Checklist 2 · Commercial readiness · responsabilidad Marcos
  ejecutar pre-cliente piloto (NO bloqueante para tag SAN-D).
- Checklist 3 · Operational readiness · cubierto Sesión 12 deploy
  (post-tag SAN-D).

### Trazabilidad

- `docs/audit/SAN_D_FINAL_AUDIT.md` (13/13 puntos · technical evidence).
- ADR-040 (auto-billing IBAN · MARCOS_BANK_*).
- ADR-039 (NotificationOrchestrator · Postmark setup).
- ADR-045 (deploy handoff · Sesión 12 procedure).



## ADR-045 · Deploy handoff procedure Sesión 12 (cierre SAN-D MB-19.C)

**Fecha**: 2026-05-07
**Status**: Adoptada
**Stakeholders**: Marcos Mata · Claude
**Refs**: SAN-D · ADR-043 · ADR-044 · `docs/HANDOFF_SESION_12.md` (procedure detallado)

### Contexto

SAN-D cerrado · tag `s13-fase-14-cliente-real-ready` aplicado al HEAD final.
Sesión 12 (post-SAN-D · ANTES primer cliente real piloto) ejecuta:

1. Provisionamiento Hetzner CPX21 (8GB RAM · 4 vCPU · Helsinki/Falkenstein).
2. Configuración HTTPS · dominio · email · backup · monitoring.
3. Migration apply + smoke production + handoff Marcos operativo.

ADR-045 documenta procedimiento canónico · referencia maestra Sesión 12.
Detalles operativos paso-a-paso en `docs/HANDOFF_SESION_12.md`.

### Decisión

#### Procedimiento canónico Sesión 12 deploy (10 fases)

**Fase 1 · Pre-deploy local validation (1h)**

- [ ] Suite backend full passing (`pytest backend/tests`)
- [ ] tsc 0 errors + npm run build success
- [ ] 0 fantasmas: grep `TODO\|FIXME` backend frontend
- [ ] 0 routing 404: dead links verification gate
- [ ] alembic head verified `sand_magic_link_migration` o posterior
- [ ] git log clean (no WIP · uncommitted changes resolved)

**Fase 2 · Hetzner CPX21 provisioning (2h)**

- [ ] Crear servidor Hetzner CPX21 · región Falkenstein (DE)
- [ ] Ubuntu 24.04 LTS image
- [ ] SSH key Marcos uploaded · root login disabled · usuario `fulkro` creado
- [ ] UFW firewall · permitir 22/443/8000 (Postgres internal · NO 5432 público)
- [ ] Fail2ban configured (SSH brute-force protection)

**Fase 3 · Software stack (1h)**

- [ ] Docker · Docker Compose installed
- [ ] PostgreSQL 16 + pgvector extension
- [ ] Redis 7 (Celery broker + result backend)
- [ ] nginx (reverse proxy + Let's Encrypt)
- [ ] Python 3.12 + venv + pip dependencies
- [ ] Node 20 LTS + npm + pnpm (build frontend)

**Fase 4 · Domain + HTTPS (30min)**

- [ ] DNS A record `app.fulkro.es` → Hetzner IP
- [ ] DNS A record `portal.fulkro.es` → Hetzner IP (split portal cliente)
- [ ] DNS MX record + SPF + DKIM + DMARC `fulkro.es` (Postmark)
- [ ] Let's Encrypt certbot · 2 certificates (admin + portal)
- [ ] nginx reverse proxy configured (admin → :8000 backend · portal → :3000 frontend)
- [ ] HTTP → HTTPS redirect 301 enforced

**Fase 5 · Variables entorno producción (30min)**

- [ ] `.env.production` con valores reales · NUNCA commit a repo
- [ ] FULKRO_AUTH_PRIVATE_KEY (Ed25519 · `openssl genpkey -algorithm Ed25519`)
- [ ] FULKRO_ML_PRIVATE_KEY (separada · scope magic-links)
- [ ] DATABASE_URL postgres:// con password fuerte 32+ chars
- [ ] POSTMARK_SERVER_TOKEN producción · domain verified
- [ ] FULKRO_REDIS_URL · redis:// localhost (Docker network internal)
- [ ] APP_BASE_URL · `https://app.fulkro.es`
- [ ] APP_PORTAL_URL · `https://portal.fulkro.es`
- [ ] MARCOS_BANK_IBAN + MARCOS_BANK_BIC + MARCOS_BANK_HOLDER (ADR-040)
- [ ] FULKRO_TESTING unset · runs en production mode strict

**Fase 6 · Migrations apply (15min)**

```bash
cd /opt/fulkro/backend
source ../.venv/bin/activate
PYTHONPATH=/opt/fulkro alembic upgrade head
# Esperado HEAD: sand_magic_link_migration (o posterior post-19.C cosechas)
```

**Fase 7 · Database seed initial (30min)**

- [ ] Crear usuario admin Marcos manual via dev endpoint o SQL directo
- [ ] Importar pricing models (Apéndice M v2.2 · `PRICING_CATALOG`)
- [ ] Importar sectores + arquetipos PYME (MB-17 · feature_flags YAML)
- [ ] Importar templates magerit Libro II (m02 · `magerit_libro_ii_loader`)
- [ ] Importar templates DECISIONS legal (MB-14.3 · 18 templates)

**Fase 8 · Smoke production (1h)**

- [ ] `curl https://app.fulkro.es/api/v1/health` 200 OK
- [ ] `curl https://app.fulkro.es/api/v1/_dev/login-as-marcos` 404 (env-gated production OK)
- [ ] Login Marcos via `/login` (admin) · auth/me 200 + role=owner
- [ ] Login portal cliente test (sintético) `/client-portal/login` · success redirect
- [ ] CRM kanban `/admin/pipeline` carga + drag-drop transition (mock OK fallback)
- [ ] Dashboard proyecto `/admin/projects/{id}/summary` · NextActionCard render
- [ ] Magic-link generate test purpose=FIRMA_DOCUMENTO · 201 Created
- [ ] Magic-link consume público endpoint accesible (sin auth)
- [ ] SSE connect `/api/v1/stream/projects/{id}` · estable 60s
- [ ] Postmark email test send · delivery confirmed inbox

**Fase 9 · Backup + monitoring (1h)**

- [ ] pgbackrest configured · primer backup full Sunday 02:00 (Celery beat)
- [ ] Sentry DSN configured + test exception capture
- [ ] Uptime Robot · 5min checks `/api/v1/health` + `/login`
- [ ] Status page public · status.fulkro.es (opcional · BetterUptime free)
- [ ] Logrotate `/var/log/fulkro/*.log` · 14 días retention

**Fase 10 · Handoff Marcos operativo (30min)**

- [ ] Marcos verifica login admin · 1 magic-link real generado test
- [ ] Marcos crea primer Lead manual `/admin/pipeline` (sin cliente real aún)
- [ ] Documentación operativa entregada (`HANDOFF_SESION_12.md` + `RUNBOOK.md`)
- [ ] FULKRO operativo · ready primer cliente real piloto

### Acceptance criteria Sesión 12

- ✅ 10 fases procedimiento ejecutadas verde con evidencia (curl outputs · screenshots)
- ✅ Smoke production 100% verde (Fase 8 · 10 checks)
- ✅ Marcos confirma operativo (Fase 10 · acceptance test manual)
- ✅ Documentación handoff completa entregada

### Consecuencias

- ADR-045 referencia canónica · `docs/HANDOFF_SESION_12.md` paso-a-paso operativo.
- Sesión 12 NO requiere coding nuevo · solo deploy + smoke + handoff
  (estimado total 8-10h ejecución pura + buffer 4h debug imprevistos).
- Post-Sesión 12 · primer cliente real piloto onboarding (Sesión 13+).

### Trazabilidad

- ADR-040 (auto-billing · MARCOS_BANK_* env vars producción).
- ADR-039 (Postmark setup · email producción).
- ADR-042 (magic-link policy · purposes 35 verificadas).
- `docs/audit/SAN_D_FINAL_AUDIT.md` (13/13 visión Marcos cubierta).
- `backend/app/core/celery_app.py` (13 beat tasks pre-configured production).
- `frontend/playwright.config.ts` (smoke procedure E2E reusable).

### Lección

**Tag SAN-D + handoff Sesión 12 separados deliberadamente**. Tag aplica
al HEAD final SAN-D cuando 13/13 visión cubierto + technical readiness
verde · independiente de deploy infra (responsabilidad Sesión 12 fresh).
Esto preserva audit trail SAN-D claro · evita "scope creep producción"
en cierre arquitectónico.



### Lección

**Audit empírico desnuda briefings** · briefing v2 listaba 12 purposes
CONTINUO inexistentes (DDA_REVIEW · PDA_REVIEW · etc) · representaban
visión teórica pre-implementación. Real enum 35 post-FASE 4.5 + SAN-B +
MB-19.4 contiene 2 reales migrables. Lección MB-13/15/19.A aplicada
(audit pre-impl 30min ahorra horas de scope creep o STOP intermedio).

**Soft-deprecation > hard-deprecation cuando legacy sites activos**.
Sites m05/m16 invocan ONBOARDING_INICIAL/APORTE_EVIDENCIA en flows
operativos · romper estos = romper onboarding cliente actual. Soft
warning + header preserva uptime + da tiempo migration sites a
portal-direct paths sin "big bang day" risk.

**Reuso m21 cockpit_* extension > ClientUserInviteFlow paralelo**.
m21 ya tiene flow PRIMER_ACCESO_CLIENTE production-ready · extension
in-place (param opcional + hook orchestrator) preserva test coverage
y minimiza superficie cambio.


## ADR-046 · Capability vs Feature Flag clarification + Q5.3 cement (MB-10 Atom 10.0)

**Status**: ACCEPTED 2026-05-13 · **Source**: `docs/architecture/ADR-046_capability_vs_feature_flag_clarification.md`

**Rename note**: ADR-046 was originally created as ADR-037 during MB-10 Atom 10.0 (2026-05-13). Renamed to ADR-046 post-audit B1.2 (OPS-063 cement) to resolve numbering collision with existing inline ADR-037 (AI Auditor pro contextualizado · SAN-D MB-15).

### Summary

Clarifica relación entre concepto ISMS "M32 Capabilities" y infraestructura existente `core/feature_flags/` (ADR-036):

- **M32 in ISMS docs** = LOGICAL motor concept (terminology preservada · NO motor folder separado)
- **Implementation lives in** `backend/app/core/feature_flags/` (ADR-036 infrastructure extended)
- **NEW table `feature_flag_overrides`** materializa ADR-036 deferred (MB-10 Atom 10.2)
- **Q5.3 cement explicit**: capabilities INVISIBLE cliente · admin-only management UI

### Result

Atom 10.4 cliente UI = SKIP per Q5.3 cement INVISIBLE applied. Frontend `useProjectFeatures` hook transparent merge overrides (8+ components unchanged).

Ver detalle completo en `docs/architecture/ADR-046_capability_vs_feature_flag_clarification.md`.


## ADR-047 · Intelligence Cross-Motor · Distributed Pattern DEFER (MB-10 Atom 10.5)

**Status**: ACCEPTED 2026-05-13 · **Source**: `docs/architecture/ADR-047_intelligence_cross_motor_distributed_pattern.md`

**Rename note**: ADR-047 was originally created as ADR-042 during MB-10 Atom 10.5 (2026-05-13). Renamed to ADR-047 post-audit B1.2 (OPS-063 cement) to resolve numbering collision with existing inline ADR-042 (Magic-link policy híbrida final · SAN-D MB-19.B).

### Summary

**NO new motor `m_intelligence/` construido** · Intelligence cross-motor functionality ALREADY DISTRIBUTED:

- 22 specialized agents (each with cross-motor domain logic · A21 deterministic SQL detector)
- 8+ admin dashboards (signals visualization production-grade)
- Cross-motor services (m21_diagnosis dashboard · operations · projects KPIs)
- LLM router infrastructure (`core/ai/llm_router.py` Anthropic SDK wrapper)
- Anti-hallucination boundary CEMENTED (deterministic detectors + LLM narrative-only)

### Cement

OPS-062 validated 2da vez · DEFER architectural con ADR explicit ≠ silent debt.

Building monolithic `m_intelligence/` motor introduciría architectural duplication (anti-pattern). Forward revisit only si specific functional gap concreto emerges (NOT umbrella term).

Ver detalle completo en `docs/architecture/ADR-047_intelligence_cross_motor_distributed_pattern.md`.


## ADR-048 · Backup Encryption Strategy + Offsite Replication + Restore Drill DEFER MB-11 (MB-10 Atom 10.6)

**Status**: ACCEPTED 2026-05-13 · **Source**: `docs/architecture/ADR-048_backup_encryption_strategy.md`

**Rename note**: ADR-048 was originally created as ADR-043 during MB-10 Atom 10.6 (2026-05-13). Renamed to ADR-048 post-audit B1.2 (OPS-063 cement) to resolve numbering collision with existing inline ADR-043 (SAN-D learnings + iterative pattern · SAN-D MB-19.C).

### Summary

Materializa M26 backup encryption + offsite replication per ISMS commitments (8 docs referenced · F2_2 + ENS_SPEC v2.1):

- **Encryption**: Fernet AES-128-CBC pattern reuse `m16_onboarding/token_encryption.py` · `BACKUP_ENCRYPTION_KEY` env transitional (MB-12 Vault/SOPS forward)
- **Offsite**: MinIO bucket dedicated `backup-vault-fulkro` (`BUCKET_BACKUP_VAULT` constant) · Hetzner Object Storage cutover DEFER MB-11
- **Restore drill**: stub preserved · MB-11 Terraform orchestration · `monthly_restore_test` beat scheduled (logs intention)
- **Beat schedule**: `verify_integrity` weekly Sunday 03:00 · `monthly_restore_test` 1st month 04:00 · `dr_drill` manual

### Cement

OPS-062 validated 2da vez. FEATURE-side complete dev environment ✅ · INFRASTRUCTURE-side DEFER explicit MB-11 ADR-048 cement. NO silent defer.

Ver detalle completo en `docs/architecture/ADR-048_backup_encryption_strategy.md`.


## ADR-049 · Copilot Agent 14 · 3 surfaces architectural intent · NO duplicate (FASE 2 H2 cement post-audit)

**Status**: ACCEPTED 2026-05-13 · **Source**: `docs/architecture/ADR-049_copilot_3_surfaces_architectural_intent.md`

### Summary

Audit O2 (2026-05-13) detected superficially "copilot/copiloto duplicate component dirs · consolidate candidate". Pre-audit empirical FASE-2-H2 reveló **NO duplicate** · 3 surfaces architectural distinct intent serving 2 audiences distinct:

| Surface | Path | Audience | Convention |
|---------|------|----------|------------|
| Admin Sheet side panel | `components/copilot/*` (6 files · 609 LOC) | Admin owner | English (matches `/admin/copilot` route) |
| Admin fullscreen page | `app/(admin)/admin/copilot/page.tsx` + `components/agents/CopilotChat` | Admin owner | English route + components/agents/ |
| Cliente floating dock | `components/copiloto/CopilotoDock` (1 file · 264 LOC) | Cliente client_user | Spanish (matches backend `m11_copiloto` + `agents/agent_14_copiloto`) |

### Decision

**NO consolidate**. Architectural intent intentional cement: English admin convention + Spanish cliente convention (backend-aligned). ADR-013 separación 3 portales empirically honored.

### Cement

OPS-061 5ª aplicación · vaporware detection cumulative pattern (audit superficial finding caught pre-execute). OPS-026 audit-first 34ª aplicación. OPS-027 sostained existing infra discovery (NO scope creep).

Audit O2 finding "copilot/copiloto duplicate" RECLASSIFIED ✅ RESOLVED via audit-driven cancel.

Ver detalle completo en `docs/architecture/ADR-049_copilot_3_surfaces_architectural_intent.md`.


## ADR-050 · Copilot ADMIN guided mode end-to-end ENS lifecycle · VISIÓN cement · DEFER MB-14 polish bloque mayor

**Status**: VISION cement · DEFER MB-14 dedicated · 2026-05-13 · **Source**: `docs/architecture/ADR-050_copilot_admin_guided_mode_vision_defer_mb14.md`

### Marcos visión literal

> "Lo ideal es que el copiloto, que realmente es el que me acompaña, tenga las máximas características posibles que me ayuden a mí a hacer todo el ciclo del ENS en el cliente · que se me presentase todo como si yo fuera tonto y no tuviera ni idea de ENS · que hasta mi padre, que no sabe nada de ENS, pudiera sacar el ENS de una empresa entero, desde el principio al fin · que se me presentase todo por orden."

### Gap empirical

Visión requires capacidades NO cubiertas estado actual: state machine ENS lifecycle end-to-end (50+ states) · next-best-action engine deterministic + LLM hybrid · context-aware suggestions per cliente state empirical · multi-step wizards integration 38 motors orchestration · coach pattern proactive (A12+A14 fusion candidate) · UX zero-friction "padre saca ENS entero" · end-to-end walkthrough NO intervention manual Marcos.

**Effort cumulative honest estimate: ~25-45h (1-2 semanas focused)**.

### Decision

**CEMENT VISIÓN documented · DEFER implementation MB-14 polish bloque mayor dedicated** post FASE 2 + Blocks 7-9 closure.

### Scope MB-14 polish bloque mayor (forward)

- MB-14.0 · Pre-audit architectural design (~2-3h cabeza fresca)
- MB-14.1 · State machine ENS lifecycle backend (~6-8h)
- MB-14.2 · Next-best-action engine (~4-6h)
- MB-14.3 · Frontend guided UI · Sheet + wizard overlay (~6-8h)
- MB-14.4 · Cross-motor integration empirical (~4-6h)
- MB-14.5 · E2E "padre saca ENS entero" walkthrough (~2-3h)

Tag forward: `s14-mb14-copilot-guided-cerrada`.

### Cement

OPS-062 sostained · DEFER architectural con ADR explicit ≠ silent debt. OPS-024 sostained · NO atom inflation FASE 2. OPS-026 audit-first sostained.

FASE 2 actual preserved sostained: H4 Dashboard wire-up simple + H5 Copilot streaming SSE simple (NOT guided mode · DevHint mocks resueltos).

Ver detalle completo en `docs/architecture/ADR-050_copilot_admin_guided_mode_vision_defer_mb14.md`.


## ADR-051 · `firma/` vs `firmas-hub/` · 2 surfaces architectural intent · NO duplicate (FASE 2 H3 cement post-audit)

**Status**: ACCEPTED 2026-05-13 · **Source**: `docs/architecture/ADR-051_firma_firmas_hub_distinct_architectural_intent.md`

### Summary

Audit O3 (2026-05-13) detectó superficialmente "`firma/` Y `firmas-hub/` cliente routes · legacy + v2 · candidate consolidation (firma/ legacy?)" (O3 línea 306 / 313 · O15 HIGH PRIORITY #6 línea 124). Pre-audit empirical FASE-2-H3 reveló **NO duplicate** · 2 surfaces architectural distinct intent sirviendo audiencias y propósitos ortogonales:

| Surface | Path | LOC | Tipo | Intent | Cement |
|---------|------|-----|------|--------|--------|
| `firma/` página explicativa | `app/(client-portal)/client-portal/firma/page.tsx` | 235 | Server component estático | Legal disclosure "Cómo funciona la firma" | ADR-009 + ADR-010 + cláusula C-001 (URL literal contractual) |
| `firmas-hub/` hub operativo | `app/(client-portal)/client-portal/firmas-hub/page.tsx` + `components/client-portal/firmas-hub/*` (360 LOC) | 150 + 360 | Client component transaccional | "Mis firmas ENS" + chain integrity + history | SAN-E v3.MB-6 atom 0.2 + ADR-020 in-portal review |

### Decision

**NO consolidate · NO eliminate `firma/` · NO merge**. Eliminar `firma/` rompería **5 puntos consistentes** trazabilidad ADR-010 (incluyendo cláusula contractual C-001 que cita URL literal en contratos cliente firmados) + 3 cross-refs (`retainer-checkin` + `docs/verify-signature` + `PublicKeyVerifier`).

### Cement

OPS-061 6ª aplicación cumulative · vaporware-detection pattern (6 instancias: M32 Capabilities · features panel · Intelligence cross-motor · backup encryption-as-stub · ADR-037/042/043 self-collisions · copilot/copiloto H2 ADR-049 · firma/firmas-hub H3 ADR-051). OPS-026 audit-first 36ª aplicación. OPS-027 sostained existing infra discovery (NO scope creep). OPS-062 sostained.

Audit O3 #6 finding "firma/ Y firmas-hub/ legacy duplicate" RECLASSIFIED ✅ RESOLVED via audit-driven cancel.

Ver detalle completo en `docs/architecture/ADR-051_firma_firmas_hub_distinct_architectural_intent.md`.


## ADR-052 · Copilot SSE streaming wire-up · distinct intent vs generic `/agents/{id}/invoke` (FASE 2 H5 cement post-audit CANCEL)

**Status**: ACCEPTED 2026-05-13 · **Source**: `docs/architecture/ADR-052_copilot_sse_streaming_distinct_intent.md`

### Summary

Audit O2 / O15 (2026-05-13) detectó "Copilot DevHint 'streaming mock' · POST /api/v1/agents/14/invoke backend pendiente" (O2 línea 441/452/470/477 · O15 HIGH PRIORITY #10 línea 128 + O2 row L53). Pre-audit empirical FASE-2-H5 reveló **wire-up YA implementado 100%** · audit cita endpoint path (`/agents/14/invoke`) que **NUNCA fue el path real** · path empírico es `/api/v1/copilot/chat/stream` (M11 motor wrapper dedicated per ADR-049).

### Cadena wire-up SSE Copilot empirical (todos REAL · 2/2 tests PASS)

| Layer | Path | Status |
|---|---|---|
| Frontend hook | `frontend/hooks/useCopilot.ts` | ✅ REAL `chatWithCopilotStream` |
| Frontend SSE consumer | `frontend/lib/api/copilot.ts:176` | ✅ `fetch /api/v1/copilot/chat/stream` + ReadableStream parser |
| Backend router | `m11_copiloto/api.py:175` | ✅ `StreamingResponse` + `text/event-stream` |
| Backend service | `agent_14_copiloto/service.py` | ✅ `stream_answer_question` AsyncIterator |
| LLM SDK | `core/ai/llm_router.py:31` | ✅ Anthropic SDK direct (post-H6 cement) |
| Tests | `m11_copiloto/test_copilot_stream.py` | ✅ 2/2 PASSED (citation frames + quick-actions) |

### Decision

**NO crear alias** `/agents/14/invoke` (anti-pattern · violaría OPS-027 + ADR-049 3 surfaces architectural distinct). Wire-up real `/copilot/chat/stream` preservado. DevHint stale removido. Audit O2/O15 finding #5 RECLASSIFIED ✅ RESOLVED.

### Cement

OPS-061 7ª aplicación cumulative · vaporware-detection pattern (8 instancias: M32 Capabilities · features panel · Intelligence · backup-as-stub · ADR self-collisions · copilot/copiloto H2 ADR-049 · firma/firmas-hub H3 ADR-051 · copilot streaming H5 ADR-052). OPS-026 audit-first 45ª aplicación. OPS-027 sostained. OPS-062 sostained.

Ver detalle completo en `docs/architecture/ADR-052_copilot_sse_streaming_distinct_intent.md`.

