"use client";

/**
 * /client-portal/certificacion · cliente acompañamiento ciclo timeline read-only.
 * Sesión 3B-4 Ejecutable 7.5 Phase 7.5.3 (2026-05-27).
 *
 * R29 cliente friendly · SSE auto-update via useClientProjectEvents.
 * R23 cliente-mínimo filosofía: cliente RECIBE updates · NO opera proceso.
 */
import { AuditAccompanimentClienteView } from "@/components/client-portal/AuditAccompanimentClienteView";
import { useClientProjectId } from "@/hooks/useClientProjectId";

export default function ClienteCertificacionPage() {
  // FIX(roleplay visual): antes llamaba /client-auth/me (inexistente → 404)
  // dejando projectId=null y la vista vacía. Hook canónico → /client-portal/project.
  const { projectId } = useClientProjectId();

  return (
    <div className="space-y-4 p-4 md:p-6">
      <h1 className="text-2xl font-bold">Tu certificación ENS</h1>
      <p className="text-sm text-muted-foreground">
        Sigue en tiempo real cómo avanza tu cumplimiento del Esquema Nacional de
        Seguridad. Tu consultor va marcando los hitos según los completamos.
      </p>
      <AuditAccompanimentClienteView projectId={projectId} />
    </div>
  );
}
