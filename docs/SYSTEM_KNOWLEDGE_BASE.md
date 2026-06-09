# SYSTEM_KNOWLEDGE_BASE — Fulkro (auto-conocimiento de plataforma para copilotos)

> **Propósito**: fuente-única veraz del sistema para que los copilotos respondan
> preguntas de **uso de la plataforma** (no normativa ENS — eso lo cubre el corpus
> RAG: RD 311/2022 + CCN-STIC). De aquí se deriva la constante compacta
> `backend/app/agents/system_knowledge.py` inyectada en los system-prompts.
>
> **Atribución en respuestas**: lo que el copiloto afirme desde este documento se
> cita como `[Fulkro Plataforma]`. Las afirmaciones normativas SIEMPRE conservan
> sus citas ENS obligatorias (R2: RD 311/2022, CCN-STIC, Anexo II).
>
> **Generación (Pasada 18)**: estructura derivada del **código real** verificado
> contra el repo:
> - Navegación cliente: `frontend/components/layout/ClientSidebar.tsx`
>   (`CLIENT_NAV_SECTIONS`).
> - Fases canónicas: `backend/app/core/workflow_phase.py` (`WorkflowPhase`, 10).
> - Identidad: `backend/app/fulkro_identity.py`.
>
> Las secciones de **copy cliente-facing** (cómo se describe Fulkro y el portal al
> cliente) van marcadas **⚠ REVISIÓN CONSULTOR** — son el mensaje de producto de
> Marcos y NO son definitivas hasta su pasada (mismo criterio que la plantilla
> E-155).

---

## 1. Qué es Fulkro · ⚠ REVISIÓN CONSULTOR

> Borrador derivado de `backend/app/fulkro_identity.py` + CLAUDE.md. Marcos revisa
> el framing exacto antes de que el copiloto lo diga a clientes.

Fulkro es una **plataforma de implantación del ENS** (Esquema Nacional de
Seguridad · RD 311/2022) operada por la consultora Fulkro (Marcos Mata,
consultor autónomo en Madrid). Acompaña a una empresa privada que licita a la
Administración Pública a lo largo de todo el ciclo: del diagnóstico inicial a la
certificación/conformidad ENS y su mantenimiento posterior.

Contacto Fulkro (canónico · `fulkro_identity.py`): los datos exactos (teléfono,
web, email) viven en ese módulo y se inyectan vía `FULKRO_COPILOT_PRIMARY_CONTEXT`
— el copiloto NO debe inventarlos.

**Categorías ENS** (RD 311/2022 Art. 40 + Anexo I): BÁSICA, MEDIA, ALTA. La
exigencia de auditoría externa por entidad acreditada aplica a MEDIA y ALTA;
BÁSICA admite autoevaluación/declaración de conformidad. *(Afirmación normativa:
el copiloto la respalda con cita ENS, no con [Fulkro Plataforma].)*

---

## 2. El portal del cliente · navegación real · ⚠ REVISIÓN CONSULTOR

> Backbone factual (**verificado**): `frontend/components/layout/ClientSidebar.tsx`
> (`CLIENT_NAV_SECTIONS`). El **copy descriptivo** de cada sección lo revisa Marcos.

Filosofía **cliente-mínimo** (transversal · ver §4): el cliente HACE lo
indispensable (aportar info, subir documentos, firmar, ver tareas) y **Marcos
opera todo lo demás desde el panel admin**. Etiquetas cliente-friendly (R29 ·
sin jerga admin; R30-inverso · sin internals).

**Navegación del portal (secciones y entradas reales):**

| Sección | Entrada (label real) | Ruta | Qué hace el cliente |
|---|---|---|---|
| (principal) | Inicio | `/client-portal/` | Vista general + su siguiente paso. |
| (principal) | Cumplimiento | `/client-portal/cumplimiento` | Estado de cumplimiento de su proyecto. |
| (principal) | Mis tareas | `/client-portal/tasks` | Catálogo de lo que TÚ haces. |
| (principal) | Firmas pendientes | `/client-portal/firmas-hub` | Firmar documentos (firma Ed25519). |
| (principal) | Subir documentos | `/client-portal/files` | Aportar documentos/evidencias. |
| (principal) | Mejoras propuestas | `/client-portal/remediaciones` | Ver/aceptar remediaciones recomendadas. |
| (principal) | Mi plan ENS | `/client-portal/plan` | Ver el plan de adecuación (solo lectura). |
| Mi empresa | Onboarding | `/client-portal/onboarding` | Puesta en marcha · info de la empresa. |
| Mi empresa | Conexiones cloud | `/client-portal/cloud-connections` | Conectar servicios cloud (OAuth solo lectura). |
| Mi empresa | Facturación | `/client-portal/billing` | Facturas del proyecto. |
| Comunicación | Chat con Marcos | `/client-portal/chat` | Conversar con el consultor. |
| Comunicación | Mensajes | `/client-portal/inbox` | Bandeja de notificaciones/mensajes. |
| Comunicación | WhatsApp | `/client-portal/whatsapp` | Opt-in de avisos por WhatsApp. |
| Mi cuenta | Mi cuenta | `/client-portal/account` | Datos de su cuenta. |

**Páginas SIN entrada en el menú** (el cliente llega vía una tarea concreta que
Marcos le asigna, no navegando): `/evidencias`, `/policies`, `/dda`, `/magerit`,
`/conformidad`, `/dpc-anual`, `/actas`, `/incidents`, `/retainer-checkin`,
`/pentest-authorization`, `/workflow`. *(Por eso, si un cliente pregunta "¿dónde
aporto la evidencia X?", la respuesta típica es "Subir documentos" o la tarea
concreta que se le ha asignado.)*

---

## 3. El ciclo ENS del proyecto · fases canónicas

> Backbone factual (**verificado**): `backend/app/core/workflow_phase.py`
> (`WorkflowPhase`, 10 fases · source of truth). La **descripción cliente-facing**
> va en ⚠ REVISIÓN CONSULTOR.

10 fases canónicas en orden: `pre_venta` → `onboarding` → `diagnostico` →
`analisis_riesgos` → `adecuacion` → `implantacion` → `dda_final` →
`verificacion` → `conformidad` → `retainer_cierre`.

**⚠ REVISIÓN CONSULTOR** — explicación cliente-facing (borrador):
- **Onboarding**: alta del proyecto, datos de la empresa, primeras conexiones.
- **Diagnóstico / Análisis de riesgos**: categorización del sistema y valoración
  de riesgos (MAGERIT).
- **Adecuación / Implantación**: el equipo de Fulkro implanta las medidas; el
  cliente aporta evidencias y aprueba lo necesario.
- **DdA final / Verificación**: Declaración de Aplicabilidad y preparación de
  auditoría.
- **Conformidad**: auditoría/certificación (MEDIA/ALTA) o declaración (BÁSICA).
- **Retainer / cierre**: mantenimiento posterior a la certificación.

---

## 4. Qué hace y qué NO hace el cliente (cliente-mínimo) · ⚠ REVISIÓN CONSULTOR

> Doctrina del repo (R29 cliente-friendly + R30-inverso: el cliente no ve
> internals ni jerga admin · `ClientSidebar.tsx` cabecera). Framing exacto: Marcos.

- **SÍ hace**: aportar información de su empresa, subir documentos/evidencias,
  firmar, ver y atender sus tareas, ver su plan y su estado de cumplimiento,
  aceptar mejoras propuestas, conectar su cloud en modo solo-lectura, comunicarse
  con Marcos. Cuando aplica: autorizar acciones técnicas (p. ej. pentest).
- **NO hace**: redactar políticas/procedimientos ENS, operar la plataforma,
  ejecutar el análisis técnico, decidir la normativa. De la implantación técnica
  se encarga el equipo de Fulkro (Marcos opera desde el panel admin).
- **Tono**: "sin prisa por tu parte"; nunca presión coercitiva; sin jerga ENS
  sin explicar.

---

## 5. Cómo el copiloto debe usar este conocimiento

- Preguntas de **uso de plataforma** ("¿cómo subo una evidencia?", "¿qué hago en
  esta fase?", "¿dónde firmo?") → responder desde este documento, citando
  `[Fulkro Plataforma]`.
- Preguntas **normativas ENS** ("¿es obligatorio el pentest en MEDIA?") → seguir
  el camino normal (corpus RAG con citas RD 311/2022 / CCN-STIC · R2). Este
  documento NO sustituye al corpus normativo.
- Si algo no está ni aquí ni en el corpus → no inventar; derivar a Marcos (Chat /
  Mensajes) o decir que no consta.
- **Cliente-mínimo**: a un cliente nunca se le explican internals ni se le pide
  operar el ENS técnico.

---

## 6. Mantenimiento

Este documento es **documentación-de-lo-que-existe**, no una promesa. Cuando
cambien la navegación (`ClientSidebar.tsx`), las fases (`workflow_phase.py`) o la
identidad (`fulkro_identity.py`), actualizar aquí y regenerar la constante
compacta `backend/app/agents/system_knowledge.py`. Las secciones
⚠ REVISIÓN CONSULTOR requieren pasada de Marcos antes de exponerse como copy
definitivo al cliente.
