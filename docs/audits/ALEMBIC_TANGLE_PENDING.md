# Alembic chain tangle — diagnóstico + plan de remediación (PENDIENTE)

> Estado: **documentado, NO tocado**. Deuda real para el deploy limpio en Hetzner.
> NO se reconcilia con el sistema vivo en dev (riesgo de aplicar `sub_atom_5b` y
> otras migraciones diferidas sobre una BD en uso). Fecha diagnóstico: 2026-05-29.

## Síntoma

`alembic upgrade head` NO corre limpio sobre la BD de dev. `alembic current` y
`alembic heads` no coinciden.

## Diagnóstico empírico

- **Scripts (disco)** tienen una sola cabeza tras el merge:
  `radar_widen_sector_text_001` → `merge_heads_radar_magerit_001`.
  - `merge_heads_radar_magerit_001` es un *mergepoint* que une
    `radar_recert_001` + `sub_atom_5b_magerit_child_rls_001`.
- **BD de dev** (`alembic_version`) está en **3 filas** (3 cabezas aplicadas),
  estado PRE-merge:
  - `cluster6_client_mfa_001`
  - `radar_v9_perfect_f_001`
  - `radar_recert_001`
- Es decir:
  1. El merge `merge_heads_radar_magerit_001` **nunca se aplicó** a esta BD.
  2. `sub_atom_5b_magerit_child_rls_001` (Sub-atom 5.B · MAGERIT child RLS,
     diferido en sesiones previas) **no está aplicado**.
  3. `cluster6_client_mfa_001` y `radar_v9_perfect_f_001` constan como cabezas
     independientes en la BD que el merge no referencia.
- **`alembic_version.version_num` es `VARCHAR(32)`**. Varios revision id superan
  ese ancho (p. ej. `sub_atom_5b_magerit_child_rls_001` y
  `remediation_enhancement_b35_e_001`, 33 chars) → un upgrade que intente
  insertarlos rompería por truncación. (Deuda histórica
  `Future-1.E.radar.alembic-version-num-widen`.)

## Por qué NO se toca ahora

- Reconciliar implica aplicar/stampear migraciones diferidas (`sub_atom_5b` MAGERIT
  RLS) sobre una BD con datos vivos en dev → riesgo de cambios de esquema/políticas
  RLS no deseados con el Radar en uso.
- El fix de esquema urgente (`radar_widen_sector_text_001`, ensanche de
  `sector`/`sector_sugerido` a TEXT) se aplicó por **DDL directo** en dev,
  precisamente para no depender de `alembic upgrade` sobre este estado.

## Plan de remediación (para deploy limpio Hetzner o ventana de mantenimiento dev)

1. **Ensanchar `version_num`** antes de cualquier upgrade:
   ```sql
   ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(64);
   ```
   (Acción independiente de Alembic; segura.)
2. **Reconciliar las 3 filas de la BD vs el merge**. Opciones según el caso:
   - **Deploy limpio (BD nueva, Hetzner)**: `alembic upgrade head` de cero — con
     `version_num` ya ensanchado, aplica toda la cadena incluyendo el merge y
     `sub_atom_5b`. Es el camino recomendado.
   - **Reconciliar la BD de dev existente** (si se decide): verificar manualmente
     si el esquema de `cluster6_client_mfa_001`, `radar_v9_perfect_f_001` y
     `sub_atom_5b_magerit_child_rls_001` ya está presente físicamente; si lo está,
     `alembic stamp merge_heads_radar_magerit_001` (y luego
     `radar_widen_sector_text_001`) para alinear el puntero sin re-ejecutar DDL.
     Si NO lo está, aplicar las migraciones que falten en orden antes del stamp.
3. **Verificar**: `alembic heads` == `alembic current` == `radar_widen_sector_text_001`.

## Migración del fix de sector (ya creada)

`backend/migrations/versions/radar_widen_sector_text_001_widen_llm_sector_to_text.py`
encadena de `merge_heads_radar_magerit_001` y ensancha
`data_treatment_cache.sector_sugerido` + `tenders.sector` a TEXT. En dev el cambio
ya está aplicado por DDL; esta migración lo reproduce en un deploy limpio.
