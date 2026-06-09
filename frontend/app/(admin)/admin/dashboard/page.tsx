"use client";

import { ActivityCard } from "@/components/dashboard/ActivityCard";
import { AlertsCard } from "@/components/dashboard/AlertsCard";
import { ChurnRiskWidget } from "@/components/dashboard/ChurnRiskWidget";
import { KpiRow } from "@/components/dashboard/KpiRow";
import { MyDayCard } from "@/components/dashboard/MyDayCard";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { useAuthStore } from "@/lib/stores/auth-store";

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
          Buenas, {user?.display_name?.split(" ")[0] ?? user?.email ?? "FULKRO"}
        </h1>
        <p className="text-base font-medium text-[color:var(--fulkro-body)]">
          Resumen del negocio hoy.
        </p>
      </header>

      <KpiRow />

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <MyDayCard />
        <AlertsCard />
        <ActivityCard />
      </section>

      {/* Sub-atom Sesión 3B-2B.3 Phase X.4d · churn-risk widget migrated from
          standalone route /admin/retainers/churn-risk (now redirect). Compact
          top-3 high+critical retainers at risk · "Ver todos en Finanzas"
          drill-down. */}
      <section aria-label="Retainers en riesgo">
        <ChurnRiskWidget />
      </section>

      <section aria-label="Acciones rápidas">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
          Acciones rápidas
        </h2>
        <QuickActions />
      </section>
    </div>
  );
}
