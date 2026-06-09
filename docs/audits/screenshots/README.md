# Empirical samples · Sesión 3B-2B.6 CLUSTER 4 VALIDATION

**Fecha**: 2026-05-26 post CLUSTER 4 cierre

## Files preserved

### `empirical-draft-report-fulkro-smoke-basica.pdf`

Empirical PDF sample · Phase C4 draft audit report generator output.

- **Source project**: `FULKRO Smoke Test FASE 9.0` (categoría BASICA · same project Phase C3 heatmap validation)
- **Size**: 7988 bytes · 3 pages A4
- **Sections**: 9 (portada · alcance · resumen · hallazgos · aclaraciones · cobertura DdA-Evidencias · integridad · opinión · firma metadatos)
- **Spanish UTF-8 verified**: Categoría · Auditoría · Recomendación · Cobertura · Hallazgos · etc preserved
- **Auto-recommendation**: `NO_APROBAR` (derived per gap matrix · 11 critical_missing detected mp.com.* + op.acc.* high-req prefixes)
- **Signed Ed25519**: sha256 + signature_hex via M05 keypair reuse (Cluster 1 dossier pattern)
- **Note**: sha256 cambia entre runs (timestamps embedded en context · `generated_at` ISO instant) · sha256 self-consistent con pdf_bytes mismo run

## Screenshots pendientes (require running frontend)

Los siguientes screenshots están **DEFERRED post-piloto** (`Future-CLUSTER 3.delta.empirical-screenshots-frontend`):
- `heatmap-fulkro-smoke-basica.png` · DdA-evidence gaps heatmap UI rendered (Phase C3.3)
- `auditor-portal-sidebar-11-sections.png` · AuditorPortalChrome nav sidebar (Phase 4 base + Phase 5 + Phase C3 + Phase C4 additions)
- `admin-clarifications-inbox-sse.png` · AdminClarificationsInbox SSE realtime UI (Phase C2.3)
- `draft-report-preview-iframe.png` · DraftReportView iframe + signed download CTA (Phase C4.3)

**Rationale**: capturing frontend screenshots requires running Next.js dev server + Playwright orchestration. Backend empirical PDF sample suficiente para validar binary generation + signature flow. Frontend visual validation deferred · the polish specs (12 cumulative en `tests/polish/auditor-portal/`) cover WCAG axe-CI cross-views runtime.

---

**Mantenido vía CLUSTER 4 VALIDATION** · ver [`VALIDATION_SESION_3B_2B_6_PATH_C_FINAL.md`](../VALIDATION_SESION_3B_2B_6_PATH_C_FINAL.md) Section 5.4 + 12 patterns.
