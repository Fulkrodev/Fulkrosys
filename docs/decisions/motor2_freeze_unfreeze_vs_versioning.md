# ADR: Motor 2 Freeze/Unfreeze vs Historical Versioning

**Status:** Accepted
**Date:** 2026-04-13
**Context:** Motor 2 MAGERIT v3 Risk Engine closure

## Decision

Motor 2 analyses use a **freeze/unfreeze** pattern with JSONB snapshots
instead of a historical versioning table.

## Context

Motor 2 (MAGERIT v3 Risk Engine) produces live analyses that can be
recalculated at any time. When the pipeline runs (propagate values,
calculate intrinsic, calculate effective, generate treatment plan),
it performs DELETE + INSERT on the calculation tables. This is by
design: MAGERIT analyses are iterative, and the analyst may revise
inputs (assets, threats, safeguards) multiple times before delivery.

Two approaches were considered:

### Option A: Historical versioning (rejected)

Create a `magerit_analysis_versions` table with auto-incrementing
version numbers, each storing a full JSONB snapshot. Every recalculation
creates a new version.

- **Pro:** Full history of every calculation run.
- **Con:** Massive storage for iterative analyses (each version stores
  the complete analysis state). No real use case: the analyst only
  cares about the FINAL state they deliver to the client.
- **Con:** Complicated API: which version is "current"?

### Option B: Freeze/Unfreeze with single snapshot (accepted)

The `magerit_analysis` table has two columns:
- `result_snapshot` (JSONB): complete analysis state at freeze time
- `snapshot_frozen_at` (TIMESTAMP): when frozen (NULL = unfrozen)

When frozen:
- All pipeline modification endpoints (propagate, calculate-*,
  treatment-plan) return 409.
- The snapshot is immutable and deterministic.
- XLSX exports and PDF reports operate on the snapshot data.

When unfrozen:
- Pipeline modifications are allowed.
- Snapshot is cleared (set to NULL).
- The analyst can iterate freely.

## Rationale

1. **MAGERIT v3 is not Git.** The methodology (Libro I sec 3.4, p.15)
   describes a single analysis that evolves through phases. The client
   receives ONE final report, not a version history.

2. **Storage efficiency.** A typical analysis with 50 assets, 200
   threats, and 500 risk calculations produces a ~50KB JSONB snapshot.
   With versioning, 10 iterations = 500KB. With freeze/unfreeze,
   always ~50KB.

3. **API simplicity.** Three endpoints (freeze, unfreeze, get-snapshot)
   vs a complex version management API.

4. **Audit trail preserved.** The frozen snapshot includes a complete
   deterministic representation of all assets, dependencies, threats,
   safeguards, risk calculations, and treatment plans. This is
   sufficient for ENS audit purposes.

5. **Future extensibility.** If a client eventually needs historical
   versions (TODO-22), the frozen snapshot format is already the
   natural unit of storage. Adding a versions table later would be
   a simple extension, not a redesign.

## Consequences

- Pipeline modification endpoints check `snapshot_frozen_at` before
  allowing changes (via `_ensure_analysis_not_frozen()` helper).
- The `_build_analysis_snapshot()` function produces a deterministic
  JSONB structure with sorted arrays for reproducibility.
- Freeze requires at least one risk calculation to exist (prevents
  empty snapshots).
- Unfreeze clears both `result_snapshot` and `snapshot_frozen_at`.

## Migration

Implemented in migration `16ca047851b0`:
- Added `result_snapshot JSONB` to `magerit_analysis`
- Added `snapshot_frozen_at TIMESTAMP WITH TIME ZONE` to `magerit_analysis`
