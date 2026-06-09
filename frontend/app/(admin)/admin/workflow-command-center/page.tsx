/**
 * /admin/workflow-command-center · sub-atom 1.C.D.B.1 v3.8.
 *
 * Dashboard multi-cliente · 4 zones cronológicas:
 *   Zone 1 · 🔴 URGENTE HOY (hero pinned top)
 *   Zone 2 · 🟡 ESTA SEMANA (cards)
 *   Zone 3 · 🟢 EN MARCHA (compact rows)
 *   Zone 4 · 📅 PRÓXIMOS 30 DÍAS (forecast timeline)
 *
 * Consume backend m_workflow_engine 1.C.D.A · 8 endpoints.
 * Auto-refresh 30s polling (deferred SSE 1.D.G T1).
 */
import { WorkflowCommandCenterDashboard } from "@/components/workflow-command-center/WorkflowCommandCenterDashboard";

export const metadata = {
  title: "Workflow Command Center · FULKRO",
};

export default function WorkflowCommandCenterPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold text-foreground">
          Workflow Command Center
        </h1>
        <p className="text-sm text-muted-foreground">
          Vista cronológica multi-cliente · urgencias hoy · pendientes semana ·
          status verde · forecast 30 días. Refresca cada 30 segundos.
        </p>
      </header>
      <WorkflowCommandCenterDashboard />
    </div>
  );
}
