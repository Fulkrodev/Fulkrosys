# FULKRO Architecture Decision Records

> **La puerta de entrada al catálogo completo es [`docs/adr/README.md`](../adr/README.md).**
> Los ADR viven repartidos en tres sitios por razones históricas; ese índice los
> lista los sesenta con su ubicación, marca los que están duplicados y señala
> tres números citados en el código que **no están escritos en ninguna parte**.
> Este README describe sólo el directorio `docs/architecture/` (ADR-046 a
> ADR-055). *(Añadido 2026-09-11 · BLOQUE I7.)*

Catálogo de Architecture Decision Records (ADRs) del proyecto FULKRO ENS.

## Historical split context

Los ADRs históricos **ADR-001 a ADR-045** viven consolidados en
[`docs/spec/DECISIONS.md`](../spec/DECISIONS.md) por razones de historia
(formato monolítico Sesiones 1-11 · pre-MB-19 cement). Decisión de NO migrar
preventivamente: cada ADR antiguo se mueve a archivo separado SOLO si requiere
modificación significativa post-creación · evita churn masivo.

A partir de **ADR-046** (incluido) los ADRs viven en archivos separados aquí:
`docs/architecture/ADR-XXX_{slug}.md` (e.g.
[`ADR-053_cloud_first_architecture.md`](./ADR-053_cloud_first_architecture.md)).

Razón del switch desde ADR-046: ADRs creciendo en complejidad · monolithic
DECISIONS.md aumentando size + dificultando cross-reference + diff noise en
commits. Archivos separados permiten ownership claro per decisión + linkable
URL desde commits/issues/CLAUDE.md.

## Going forward (convention ADR-046+)

- **NUEVOS ADRs (≥046)** → archivo separado en este directorio · naming
  `ADR-XXX_{slug-kebab-case}.md`
- **NUNCA migrar ADRs antiguos preventivamente** · solo si requieren modificación
  significativa post-creación
- **Numbering secuencial · NO saltar números** · si skip ocurre por error
  documentar en este README sección "Numbering anomalies"
- **Cross-references**: usar slug en lugar de número cuando posible (e.g.
  `ADR-053 cloud-first-architecture` mejor que `ADR-053` solo · ayuda lectura)
- **Header obligatorio** per ADR-046+:
  - `# ADR-XXX · <título descriptivo>`
  - `**Status**: Proposed | Accepted | Deprecated | Superseded · YYYY-MM-DD`
  - `**Cement**: <lección operativa | sub-atom | cross-ref>`
  - Secciones: Context · Decision · Consequences · Compatibility · References

## Numbering anomalies registry

Las anomalías vivas están documentadas en [`docs/adr/README.md`](../adr/README.md),
que es el índice único: ADR-001..003 citados y nunca escritos, y ADR-046..052
duplicados entre este directorio y `DECISIONS.md`. La numeración colisionada de
`docs/adr/` se resolvió el 2026-09-11 renumerando aquella serie a ADR-056..060.

Documentar aquí cualquier skip de numbering ADR detectado · evita confusión
histórica futura.

(Vacío actualmente · numbering ADR-001..053 secuencial continuo en momento de
creación de este README, 2026-05-21 · sub-atom 1.D.X.VERIFY commit 3).

## ADRs publicados aquí (≥046)

| ADR | Status | Title | Date |
|---|---|---|---|
| [ADR-046](./ADR-046_capability_vs_feature_flag_clarification.md) | Accepted | Capability vs feature flag clarification | — |
| [ADR-047](./ADR-047_intelligence_cross_motor_distributed_pattern.md) | Accepted | Intelligence cross-motor distributed pattern | — |
| [ADR-048](./ADR-048_backup_encryption_strategy.md) | Accepted | Backup encryption strategy | — |
| [ADR-049](./ADR-049_copilot_3_surfaces_architectural_intent.md) | Accepted | Copilot 3 surfaces architectural intent | — |
| [ADR-050](./ADR-050_copilot_admin_guided_mode_vision_defer_mb14.md) | Accepted | Copilot admin guided mode vision (defer MB-14) | — |
| [ADR-051](./ADR-051_firma_firmas_hub_distinct_architectural_intent.md) | Accepted | Firma vs firmas-hub distinct intent | — |
| [ADR-052](./ADR-052_copilot_sse_streaming_distinct_intent.md) | Accepted | Copilot SSE streaming distinct intent | 2026-05-13 |
| [ADR-053](./ADR-053_cloud_first_architecture.md) | Accepted | Cloud-First Architecture · unified m_cloud_connectors | 2026-05-21 |

ADRs históricos (001-045) referenciados directamente en
[`docs/spec/DECISIONS.md`](../spec/DECISIONS.md).

## Cross-reference con CLAUDE.md

- Lecciones operativas formalizadas: ver [CLAUDE.md sección Lecciones operativas](../../CLAUDE.md#lecciones-operativas)
- Patterns arquitecturales reusables: ver [CLAUDE.md sección Patterns arquitecturales reusables](../../CLAUDE.md#patterns-arquitecturales-reusables)
- ADR-053 cement OPS-045 29ª aplicación (audit-first cloud-first MVP)
