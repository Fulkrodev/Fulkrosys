"use client";

/**
 * CapacityTile · MB-7.bis atom 7.bis.1 (Q7.C slim).
 *
 * Slim capacity stat card para top de RetainerOpsCenter:
 *  - Capacity: X activos / Y capacidad estimada
 *  - MRR (already computed by parent)
 *  - Top 3 retainers por horas Marcos (timesheet · atom 7.bis.5)
 *
 * Heuristic capacidad Marcos: 12 clientes simultáneos · ajustable env
 * NEXT_PUBLIC_MARCOS_CAPACITY (default 12 · derivado experiencia ENS
 * consultancy small-team capacity benchmark).
 */
import { Activity, Briefcase, Clock } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";


export interface TopClientHours {
  client_name: string;
  total_minutes: number;
}


interface Props {
  activeRetainers: number;
  capacityMax?: number;
  topClientsByHours?: TopClientHours[];
}


const DEFAULT_CAPACITY = Number(
  process.env.NEXT_PUBLIC_MARCOS_CAPACITY ?? 12,
);


function minutesToHours(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}


function capacityClass(active: number, max: number): string {
  const pct = (active / max) * 100;
  if (pct >= 90) return "text-rose-700";
  if (pct >= 70) return "text-amber-700";
  return "text-emerald-700";
}


export function CapacityTile({
  activeRetainers,
  capacityMax = DEFAULT_CAPACITY,
  topClientsByHours = [],
}: Props) {
  const usage = activeRetainers / capacityMax;
  const colorClass = capacityClass(activeRetainers, capacityMax);

  return (
    <Card data-testid="capacity-tile">
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <Briefcase className="h-6 w-6 text-[color:var(--fulkro-subtitle)]" />
          <div className="flex-1">
            <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Capacidad Marcos
            </p>
            <p className={`mt-1 text-3xl font-bold tracking-tight ${colorClass}`}>
              {activeRetainers}
              <span className="text-base font-medium text-[color:var(--fulkro-muted)]">
                {" "}/ {capacityMax} clientes
              </span>
            </p>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-fulkro-surface-glass-strong">
              <div
                className={`h-full ${
                  usage >= 0.9
                    ? "bg-rose-500"
                    : usage >= 0.7
                    ? "bg-amber-500"
                    : "bg-emerald-500"
                }`}
                style={{ width: `${Math.min(100, usage * 100)}%` }}
              />
            </div>
          </div>
        </div>

        {topClientsByHours.length > 0 && (
          <div className="mt-4 border-t border-fulkro-surface-glass-border pt-3">
            <p className="mb-2 flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              <Clock className="h-3 w-3" /> Top 3 clientes (este mes)
            </p>
            <ul className="space-y-1 text-sm">
              {topClientsByHours.slice(0, 3).map((c) => (
                <li
                  key={c.client_name}
                  className="flex items-center justify-between"
                >
                  <span className="font-medium text-[color:var(--fulkro-body)]">
                    {c.client_name}
                  </span>
                  <span className="font-bold text-[color:var(--fulkro-title)]">
                    {minutesToHours(c.total_minutes)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {topClientsByHours.length === 0 && (
          <p className="mt-3 flex items-center gap-1 text-xs italic text-[color:var(--fulkro-muted)]">
            <Activity className="h-3 w-3" /> Top clientes pendiente activar timesheet (atom 7.bis.5)
          </p>
        )}
      </CardContent>
    </Card>
  );
}
