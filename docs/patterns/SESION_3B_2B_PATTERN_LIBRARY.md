# Pattern Library Sesión 3B-2B · Cross-App Reusable Patterns

**Última actualización**: 2026-05-26 post Sesión 3B-2B.6 CERRADO
**Authoritative sources**:
- `docs/audits/VALIDATION_SESION_3B_2B_2_FINAL.md` (Path B admin polish · 9 patterns originales)
- `docs/audits/VALIDATION_SESION_3B_2B_6_PATH_C_FINAL.md` (Auditor portal · +3 patterns nuevos)
- Memoria auto persistente · `MEMORY.md` (referencia rápida cross-context)

---

## Catálogo cumulativo (12 patterns)

### Sesión 3B-2B.2 Path B · admin polish (9 patterns)

1. **sidebar ::before pseudo-element for gradient** (axe-core bg-image limitation workaround)
2. **Card solid white bg** (translucent contrast loss avoided)
3. **Token DEFAULT -700 overhaul** (Tailwind shades -500→-700 success/warning/info/danger/accent)
4. **Translucent bg matching shade** (consistency cross-components)
5. **DataTable aria-label** (WCAG 2.4.4 button-name)
6. **redirect-aware isProjectScoped** spec pattern
7. **ActionLink CTA a11y** primitive
8. **Reusable spec template** runProjectScopedProbe / runTopLevelAdminProbe + runClientPortalProbe + runAuditorPortalProbe
9. **HMR stale touch** (force frontend reload post token changes)

### Sesión 3B-2B.6 Auditor portal · NUEVOS (3 patterns)

10. **emit_auditor_event helper cross-motor** · canonical action namespace + R6 hash chain preserved + project_id/client_id explícito propagated. Extracted from `_log_portal_access` con backward-compat wrapper. Reusable cross-motor para cualquier motor que necesite emit audit_log entry tagged tenant.

    ```python
    await emit_auditor_event(
        db, ctx, AUDITOR_VIEW_DDA,
        target="dda",
        metadata={"family_filter": family, "total": len(medidas)},
    )
    ```

11. **Pure functional service layer reusable** · `compute_dda_evidence_gaps` + `generate_draft_audit_report` standalone (NO HTTP coupling · NO ORM coupling). `dataclass` return + `.to_dict()` JSON-serializable cross-context. Reusable Sesión 3B-2B.10 simulacro Pre-ENAC engine. Pattern: pure async function que toma `(db, project_id, options)` + retorna dataclass.

    ```python
    async def compute_dda_evidence_gaps(
        db: AsyncSession,
        project_id: uuid.UUID,
        *,
        options: Optional[GapDetectionOptions] = None,
    ) -> DdaEvidenceGapMatrix
    ```

12. **GRANT fulkro_app explicit migrations** · `default_acl` pattern fails para tables created by `fulkro_migrate` role · NEW tables NO auto-grant. Pattern obligatorio post-CREATE TABLE en cualquier migration nueva:

    ```python
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO fulkro_app"
    )
    ```

    **Discovery empirical**: Phase C2.2 + retroactive Phase C1 fix. Pattern formalized para todas migrations futuras.

---

## Patrones session 3B-2B.6 NO movidos a este library (internos / specific)

Los siguientes patterns son específicos del scope auditor-portal y residen en sus documentos de origen:

- **Canonical JSON signing Ed25519** (Cluster 1 dossier + Phase C4 draft report) · ver `auditor-portal-architecture.md` memoria
- **Cascade flags pattern** (`cascade_certify` + `cascade_retainer_offer`) · ver `audit-passed-state-machine.md` memoria
- **Graceful skip via response field** (`*_skipped_reason`) · ver `audit-passed-state-machine.md` memoria
- **SAVEPOINT test pattern** (Sub-atom 5.A test isolation) · ver `audit-log-rls-three-way-clause.md` memoria
- **audit_log_rls_three_way_clause** · ver memoria homónima
- **copilot_rls_three_way_clause** · ver memoria homónima
- **Pentester-portal pattern 100% mirror** · auditor portal reuses (`TokenContext` + `_validate_token_peek` + `_log_portal_access`)
- **Phase 0 micro-audit MANDATORY per phase** (OPS-052 manifestation library) · CLAUDE.md doctrine
- **RLS 2-way vs 3-way OR clause selection** · NEW table (2-way) vs existing tables con legacy NULL backfill (3-way)
- **Jinja2 dict access `["items"]` notation** (Phase C4.1 gotcha) · ver `draft-report-generation-pattern.md` memoria

---

## Cómo usar este library

1. **Antes de empezar nueva sub-sesión** · revisa los 12 patterns + memorias linked
2. **Si encuentras un pattern nuevo durante implementation** · añádelo al library + memoria persistente
3. **VALIDATION docs** mantienen evidencia empírica + commit refs · este library es índice navegable
4. **Cross-sesión references**: link `[[memoria-name]]` desde otras memorias para grafo navegable

---

## Próximas adiciones esperadas (Sesión 3B-2B.8 + 3B-2B.10)

- **Sesión 3B-2B.8** Cliente Portal Path C · esperados patterns: MFA TOTP integration · workflow cronológico cliente · gestor documental drag-drop · email instructions UX
- **Sesión 3B-2B.10** Audit Simulacro Pre-ENAC · esperados patterns: simulacro state machine `simulacro_in_progress → simulacro_passed → audit_in_progress` cascade · corrective loop iteration cap · reuse `compute_dda_evidence_gaps` + `generate_draft_audit_report` confirmados

---

**Mantener este file actualizado por sesión cerrada** · Marcos / Claude executor responsable.
