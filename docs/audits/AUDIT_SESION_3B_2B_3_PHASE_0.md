# Sesión 3B-2B.3 · Phase 0 Empirical Inventory Audit

**Status**: 🟡 STOP-AND-REPORT · architect approve required antes Phase 1 execute
**Doctrine**: OPS-052 Phase 0 mandatory · empirical filesystem verification ANTES propagate implementation chain
**Date**: 2026-05-25

---

## Empirical reality vs prior framing

| Metric | Prior framing (Sesión 3B-2B.2 cierre) | Real empirical |
|--------|----------------------------------------|----------------|
| Total admin pages | not stated explicit (cliente piloto path only) | **83 page.tsx** files under `frontend/app/(admin)/admin/` |
| Verified PASS in CI green | "22 admin pages green" | **22 routes** in `test:polish:green` script (verified) |
| Honest empirical coverage | (framed as cliente piloto path complete) | **22/83 = 26.5%** absolute admin coverage |

**Honesty path**: prior "22 green" framing was correct for cliente piloto MEDIA path · NOT for full admin coverage. Sesión 3B-2B.3 expands HONEST to broader scope.

---

## Inventory complete · 83 routes categorized

### Bucket A · ALREADY VERIFIED PASS in `test:polish:green` (22 routes)

PROBE (5):
1. `/admin/dashboard`
2. `/admin/projects` (selector)
3. `/admin/projects/[id]/roadmap`
4. `/admin/projects/[id]/summary`
5. `/admin/projects/[id]/dda`

P1 (13):
6. `/admin/projects/[id]/archetype`
7. `/admin/projects/[id]/risks`
8. `/admin/projects/[id]/dossier`
9. `/admin/projects/[id]/magerit`
10. `/admin/projects/[id]/plan`
11. `/admin/projects/[id]/contratos`
12. `/admin/projects/[id]/cloud-connectors`
13. `/admin/projects/[id]/conformity`
14. `/admin/projects/[id]/evidence`
15. `/admin/projects/[id]/users`
16. `/admin/projects/[id]/personalizacion`
17. `/admin/projects/[id]/retainer`
18. `/admin/projects/[id]/equipo`

P2 (4 · subset of P2 in CI green):
19. `/admin/compliance` (landing)
20. `/admin/compliance/monitor`
21. `/admin/compliance/norma-reports`
22. `/admin/compliance/projects` (canonical)

---

### Bucket B · P2 STAGED (specs exist · NOT in CI green) — 3 routes

These already have spec files (P2/05, P2/06, P2/07) but were deferred to `Future-1.E.admin-polish-p2-iterate-remaining` per CLAUDE.md Sesión 3B-2B.2 closure. Verify + add to CI is trivial.

23. `/admin/clients` (P2/05 spec exists)
24. `/admin/retainers` (P2/06 spec exists)
25. `/admin/clients/[id]` (P2/07 spec exists)

**ETA empírico**: ~30 min · run specs + add to CI green if PASS · 0 new spec creation needed.

---

### Bucket C · P2 daily-use Marcos workflow (HIGH visibility cliente piloto path) — ~35 routes

Top-level admin (16 routes · cross-cliente):
26. `/admin/clients/new` · create cliente form
27. `/admin/clients/[id]/branding` · cliente branding admin
28. `/admin/clients/[id]/meetings` · per-cliente meetings
29. `/admin/projects/new` · create project form
30. `/admin/pipeline` · pre-sales pipeline list
31. `/admin/pipeline/leads/[id]` · lead drill-down
32. `/admin/finance` · billing/revenue aggregator
33. `/admin/retainers/churn-risk` · churn drill-down
34. `/admin/meetings` · cross-cliente calendar
35. `/admin/meetings/new` · create meeting
36. `/admin/meetings/[id]` · meeting detail
37. `/admin/messages` · admin messaging
38. `/admin/inbox` · admin inbox
39. `/admin/notifications` · notification center
40. `/admin/alerts` · alerts feed
41. `/admin/workflow-command-center` · WCC cross-cliente

Top-level admin (Bucket C continued — 7 routes):
42. `/admin/workflow-command-center/projects/[id]` · WCC per-project
43. `/admin/operations` · ops dashboard
44. `/admin/timesheet` · time tracking
45. `/admin/system-health` · FULKRO self-monitoring
46. `/admin/llm-observability` · LLM cost monitor
47. `/admin/magic-links` · auth magic links list
48. `/admin/settings` · admin settings

Project-scoped daily-use (12 routes):
49. `/admin/projects/[id]/documents` · M24 IDMS daily
50. `/admin/projects/[id]/changes` · M28 governance
51. `/admin/projects/[id]/discrepancies` · A21 quality control
52. `/admin/projects/[id]/planes-accion` · cross-motor action plans
53. `/admin/projects/[id]/discovery` · cloud discovery
54. `/admin/projects/[id]/diagnosis` · cloud diagnosis
55. `/admin/projects/[id]/dimensiones` · M01 dimensiones
56. `/admin/projects/[id]/communication` · cliente comms
57. `/admin/projects/[id]/mcps` · pentest MCPs (1.D.E)
58. `/admin/projects/[id]/providers` · supply chain (1.D.I)
59. `/admin/projects/[id]/onboarding` · cliente onboarding
60. `/admin/projects/[id]/workspace` · daily entry

**ETA empírico**: ~5-8h · pattern reuse (template-driven · 5-12 LOC per spec) · expected 0-1 NEW patterns (Tailwind overhaul + sidebar ::before + Card solid white already fixed cross-app).

---

### Bucket D · P3 secundarias (edge / niche / lifecycle) — 20 routes

Project-scoped lifecycle/edge (15 routes):
61. `/admin/projects/[id]/aepd` · RGPD adyacencia (post-piloto T2)
62. `/admin/projects/[id]/audit` · ENS audit prep
63. `/admin/projects/[id]/audit-dry-run` · ENS audit prep
64. `/admin/projects/[id]/awareness` · LMS workflow
65. `/admin/projects/[id]/backup-policy` · M26 backup
66. `/admin/projects/[id]/bia` · BIA workflow
67. `/admin/projects/[id]/billing/aapp` · AAPP billing niche
68. `/admin/projects/[id]/exit` · exit lifecycle
69. `/admin/projects/[id]/feature-flags` · admin internal
70. `/admin/projects/[id]/financial` · per-project financial
71. `/admin/projects/[id]/implementation` · implementation workflow
72. `/admin/projects/[id]/obligations` · ENS obligations engine
73. `/admin/projects/[id]/renewal` · renewal cycle
74. `/admin/projects/[id]/roles` · ENS roles assign (covered transitively via equipo)
75. `/admin/projects/[id]/verification` · post-action verify
76. `/admin/projects/[id]/transparency` · governance compliance
77. `/admin/projects/[id]/equipo/areas` · sub-route equipo

Top-level edge (3 routes):
78. `/admin/whatsapp` · whatsapp ops
79. `/admin/llm-observability/golden-eval` · B.3.D evaluator
80. `/admin/magerit-analyses/[id]/import` · MAGERIT import flow

**ETA empírico**: ~3-5h · template-driven specs (~3-5 LOC each) · verify OR honest Future-X defer per page.

---

### Bucket E · TRIVIAL REDIRECT / SCOPE-OUT — 3 routes

81. `/admin/projects/[id]/page.tsx` · 9 LOC `redirect()` to `/summary` · **TRANSITIVELY COVERED** via Bucket A summary spec
82. `/admin/cross-project-compliance/page.tsx` · 48 LOC legacy redirect to `/admin/compliance/projects` · **SCOPE-OUT** (legacy backward-compat layer · canonical in CI green Bucket A)
83. `/admin/copilot/page.tsx` · 22 LOC standalone wrapper · **SCOPE-OUT** (refactored into CopilotoAdminSidebar 1.D.B.2 · standalone preserved for backward compat only · low visibility)

**No spec creation needed** · 0 risk.

---

## Realistic ETA per bucket cumulative

| Bucket | Routes | ETA empírico | Pattern reuse |
|--------|--------|--------------|---------------|
| B · P2 staged → CI green | 3 | ~30 min | 100% (specs exist) |
| C · P2 daily-use polish | 35 | ~5-8h | ~95% (template + Tailwind overhaul fixed) |
| D · P3 secundarias triage | 20 | ~3-5h | ~90% (template-driven thin specs) |
| E · trivial scope-out | 3 | 0h | N/A |
| **Cumulative Sesión 3B-2B.3** | **61 new + 22 existing = 83 total** | **~8-13h cumulative** | **OPS-045 audit-first sostained** |

**Coverage target post-3B-2B.3**: 22 (current) + 3 (B) + 35 (C) + 20 (D) = **80/83 = 96% verified empirical** · 3/83 trivial scope-out documented.

---

## Honesty guards · OPS-049 + OPS-052 sostained

1. **Honest baseline**: 22/83 = 26.5% absolute admin coverage current (NOT 76% framing).
2. **No artificial scope**: 83 is REAL `find page.tsx` count · NOT memory-cited "81".
3. **Pattern reuse expected**: Tailwind DEFAULT shades -700 + sidebar ::before + Card solid white + DataTable aria-label + token translucent matching shade · ALL fixed cross-app Sesión 3B-2B.2 · 0-1 NEW patterns max anticipated.
4. **STOP-AND-REPORT per phase**: if NEW pattern emerges mid-Phase, halt + report honest.
5. **Per page PASS evidence**: 12/12 criteria empirical required.
6. **Future-X explicit deferral**: any page failing PASS gets explicit `Future-1.E.admin-polish.{bucket}.{page}` captured · NO silent debt.

---

## Recommended scope Phase 1+2+3

### Phase 1 · Bucket B (~30 min) + Bucket C batches (~5-8h)

Auto-chain batches per coherent concern grouping:

**Batch B (1 commit)** · Move 3 staged P2 specs into `test:polish:green` post empirical PASS verify.

**Batch C.1 · Clients ops** (~30-45 min · 3 specs) · `/admin/clients/new` · `/admin/clients/[id]/branding` · `/admin/clients/[id]/meetings`

**Batch C.2 · Projects ops** (~15-30 min · 1 spec) · `/admin/projects/new`

**Batch C.3 · Pre-sales pipeline** (~30-45 min · 2 specs) · `/admin/pipeline` · `/admin/pipeline/leads/[id]`

**Batch C.4 · Finance + retainers** (~30-45 min · 2 specs) · `/admin/finance` · `/admin/retainers/churn-risk`

**Batch C.5 · Meetings** (~45-60 min · 3 specs) · `/admin/meetings` · `/admin/meetings/new` · `/admin/meetings/[id]`

**Batch C.6 · Messaging/inbox/alerts** (~45-60 min · 4 specs) · `/admin/messages` · `/admin/inbox` · `/admin/notifications` · `/admin/alerts`

**Batch C.7 · WCC + ops** (~45-60 min · 4 specs) · `/admin/workflow-command-center` · `/admin/workflow-command-center/projects/[id]` · `/admin/operations` · `/admin/timesheet`

**Batch C.8 · Self-monitoring + observability** (~30-45 min · 3 specs) · `/admin/system-health` · `/admin/llm-observability` · `/admin/magic-links`

**Batch C.9 · Settings** (~15 min · 1 spec) · `/admin/settings`

**Batch C.10 · Project workflow daily** (~90-120 min · 8 specs) · documents · changes · discrepancies · planes-accion · discovery · diagnosis · dimensiones · communication

**Batch C.11 · Project supply chain + onboarding + workspace** (~45-60 min · 4 specs) · mcps · providers · onboarding · workspace

### Phase 2 · Bucket D batches (~3-5h)

**Batch D.1 · Project lifecycle** (~60-90 min · 7 specs) · aepd · audit · audit-dry-run · awareness · bia · implementation · obligations

**Batch D.2 · Project edge** (~45-60 min · 5 specs) · backup-policy · billing/aapp · feature-flags · financial · transparency

**Batch D.3 · Project ENS roles + lifecycle close** (~45-60 min · 5 specs) · roles · renewal · exit · verification · equipo/areas

**Batch D.4 · Top-level edge** (~30-45 min · 3 specs) · whatsapp · llm-observability/golden-eval · magerit-analyses/[id]/import

### Phase 3 · CI + VALIDATION (~1h)

- Update `test:polish:green` to include all verified specs (~80 specs)
- VALIDATION_SESION_3B_2B_3_FINAL.md per-batch evidence + honest coverage math
- Future-X buckets if any failing pages survive after pattern reuse attempts

---

## Decision required architect

**Question**: ¿Proceder con scope Phase 1+2+3 cumulative ~8-13h empírico (~96% admin coverage target)?

Alternative scopes:
- **Reduced**: Phase 1 only (Bucket B+C ~35-40 routes verified · ~5.5-8.5h · 70% coverage)
- **Maximal**: All buckets (B+C+D · 80% target ~8-13h · 96% coverage)
- **Custom**: architect specifies different priority ordering

Recommended: **Maximal** per architect directive "honest expansion + reuse pattern library + Tailwind overhaul already done · 0 app-fixes expected per Phase A.2 evidence".
