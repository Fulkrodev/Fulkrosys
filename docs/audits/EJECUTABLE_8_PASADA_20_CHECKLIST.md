# Ejecutable 8 · Pasada 20 — Checklist / guion (sesión aparte)

> Generado al cerrar la **Pasada 19** (cableado del SYSTEM_KNOWLEDGE_BASE a los
> copilotos · tests prod-fieles de comportamiento). Esta Pasada 20 es **otra
> sesión** y queda explícitamente **fuera del scope** de la 19.

## Scope de la Pasada 20 (lo que Marcos marcó como NO-tocar en la Pasada 19)

La Pasada 19 se acotó SOLO al wiring del copiloto. Lo siguiente se aplazó a la
Pasada 20 y **no se tocó** en la 19:

- [ ] **Flujo del cliente** — el recorrido completo del portal del cliente
      (más allá de lo que el copiloto *describe*; aquí se trabaja el flujo real).
- [ ] **Contratos** — generación/gestión/estado de contratos (m13/m14).
- [ ] **Firma** — e-signature (m05_signing · canvas TIER 1 + Ed25519 · ya existe
      base; revisar lo que la Pasada 20 requiera encima).
- [ ] **Pagos / facturación** — invoices / cobro (m15 billing · m23 retainer).
- [ ] **Vuln scan** — escaneo de vulnerabilidades (m08 verification · MCPs
      pentest).

## Regla de scope (heredada)

- 🔴 La Pasada 19 NO tocó nada de lo anterior. La Pasada 20 los aborda con su
      propio AUDIT-FIRST → plan → OK → construir.
- Mantener el patrón de trabajo: `cd /home/usuario/fulkro-portales &&` · sin
  radar · backup `batch2-backup-pre-rebase` intacto · `file:line` en el audit ·
  grep TEMP-NEUTER = 0 · verde con conteo · PARA tras el plan y tras cada commit.

## Estado heredado relevante (contexto para la Pasada 20)

- **Copilotos** (cerrado en 18+19): SYSTEM_KNOWLEDGE_BASE cableado (system-prompt
  estático · Opción 1 · corpus RAG normativo intacto) + comportamiento probado
  (`backend/tests/agents/test_system_knowledge_behavior_llm.py`). Si la Pasada 20
  añade flujos nuevos al portal, **actualizar** `docs/SYSTEM_KNOWLEDGE_BASE.md` +
  regenerar `backend/app/agents/system_knowledge.py` (la nav cliente se valida
  contra `frontend/components/layout/ClientSidebar.tsx`).
- **Diagnóstico previo / lead account-less** (Batch B · cerrado): plantilla 17
  preguntas + fix F-18 RLS (`precliente_rls_f18_001`, aplicada SOLO a
  `fulkro_test`) + trigger admin + email branded + frontend público
  `app/(public)/diagnostico/[token]`. Es captación de leads — **distinto** del
  flujo del cliente ya contratado que aborda la Pasada 20.
- **Firma** ya tiene base: `m05_signing` (canvas TIER 1 + Ed25519 + audit_log ·
  `pdf_signature_embed.py`). La Pasada 20 construye encima, no desde cero.

## Pendiente operativo (no de la Pasada 20, recordatorio)

- Migración `precliente_rls_f18_001` aplicada solo a `fulkro_test`. Para
  producción (FASE J Hetzner) hay que aplicarla a la DB live junto al resto.
