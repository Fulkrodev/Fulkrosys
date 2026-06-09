/**
 * Portal Workflow schemas TypeScript (sub-bloque 8.B.2 FASE 8 · ADR-026).
 *
 * Subset de admin-workflow/schemas.ts para el cliente. Reusa enums + types
 * con re-export para evitar duplicación.
 */

export {
  WORKFLOW_PHASES,
  PHASE_LABELS,
  type WorkflowPhase,
  type PhaseStatus,
  type NextAction,
  type PhaseRoadmapEntry,
  type WorkflowRoadmap,
} from "../admin-workflow/schemas";
