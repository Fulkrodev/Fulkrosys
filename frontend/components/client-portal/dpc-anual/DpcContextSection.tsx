"use client";

/**
 * DPC anual context section · 4 sub-sections (Q3.A · Marcos decision).
 *
 * - SLA actual · uptime measured + committed
 * - Plan recuperación · RTO + RPO + backups
 * - Incidents últimos 12 meses · severity histogram
 * - Roadmap mejoras · evidence + improvements
 */
import { Activity, AlertTriangle, ChevronDown, ChevronRight, Server, TrendingUp } from "lucide-react";
import { useState } from "react";

import { Card } from "@/components/ui/card";
import { type DpcContextDetail } from "@/lib/api/dpc-anual";
import { cn } from "@/lib/utils";

interface Props {
  detail: DpcContextDetail;
}

interface SectionItem {
  key: keyof Pick<
    DpcContextDetail,
    "sla_section" | "recovery_section" | "incidents_section" | "roadmap_section"
  >;
  label: string;
  icon: typeof Activity;
}

const SECTIONS: SectionItem[] = [
  { key: "sla_section", label: "SLA actual", icon: Activity },
  { key: "recovery_section", label: "Plan recuperación", icon: Server },
  { key: "incidents_section", label: "Incidents últimos 12 meses", icon: AlertTriangle },
  { key: "roadmap_section", label: "Roadmap mejoras", icon: TrendingUp },
];

function renderSlaSection(data: Record<string, unknown>) {
  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
      <DataItem label="Uptime comprometido" value={`${data.uptime_committed_pct ?? "—"}%`} />
      <DataItem label="Análisis BIA registrados" value={String(data.bia_analyses_count ?? 0)} />
      <DataItem
        label="Última actualización BIA"
        value={data.last_bia_update ? new Date(String(data.last_bia_update)).toLocaleDateString("es-ES") : "—"}
      />
    </dl>
  );
}

function renderRecoverySection(data: Record<string, unknown>) {
  return (
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
      <DataItem label="RTO documentado" value={`${data.rto_documented_hours ?? "—"}h`} />
      <DataItem label="RPO documentado" value={`${data.rpo_documented_hours ?? "—"}h`} />
      <DataItem label="Backups últimos 12m" value={String(data.backup_jobs_last_12m ?? 0)} />
      <DataItem
        label="Último backup"
        value={data.last_backup_at ? new Date(String(data.last_backup_at)).toLocaleDateString("es-ES") : "—"}
      />
    </dl>
  );
}

function renderIncidentsSection(data: Record<string, unknown>) {
  const total = Number(data.total_incidents_last_12m ?? 0);
  const histogram = (data.severity_histogram ?? {}) as Record<string, number>;
  return (
    <div className="space-y-3 text-sm">
      <DataItem label="Total incidents 12m" value={String(total)} />
      {Object.keys(histogram).length > 0 && (
        <div>
          <div className="text-xs text-fulkro-ink-500 uppercase tracking-wide mb-1">
            Severidad distribution
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(histogram).map(([sev, cnt]) => (
              <span
                key={sev}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-fulkro-ink-100 text-fulkro-ink-700"
              >
                <span className="font-mono">{sev}</span>
                <span className="font-semibold">{cnt}</span>
              </span>
            ))}
          </div>
        </div>
      )}
      {total === 0 && (
        <div className="text-fulkro-ink-500 italic">
          Sin incidents registrados último año
        </div>
      )}
    </div>
  );
}

function renderRoadmapSection(data: Record<string, unknown>) {
  const planned = (data.improvements_planned_next_year ?? []) as string[];
  return (
    <div className="space-y-3 text-sm">
      <DataItem
        label="Evidencias nuevas últimos 12m"
        value={String(data.new_evidences_last_12m ?? 0)}
      />
      {planned.length > 0 ? (
        <ul className="list-disc pl-5 space-y-1">
          {planned.map((item, i) => (
            <li key={i} className="text-fulkro-ink-700">{item}</li>
          ))}
        </ul>
      ) : (
        <div className="text-fulkro-ink-500 italic">
          No hay mejoras documentadas para el próximo año todavía.
        </div>
      )}
    </div>
  );
}

function DataItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-fulkro-ink-500 uppercase tracking-wide">
        {label}
      </dt>
      <dd className="font-semibold text-fulkro-ink-800 mt-0.5">{value}</dd>
    </div>
  );
}

export function DpcContextSection({ detail }: Props) {
  const [openSections, setOpenSections] = useState<Set<string>>(
    new Set(SECTIONS.map((s) => s.key)),
  );

  const toggle = (key: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const renderers: Record<string, (data: Record<string, unknown>) => JSX.Element> = {
    sla_section: renderSlaSection,
    recovery_section: renderRecoverySection,
    incidents_section: renderIncidentsSection,
    roadmap_section: renderRoadmapSection,
  };

  return (
    <div className="space-y-3">
      {SECTIONS.map(({ key, label, icon: Icon }) => {
        const isOpen = openSections.has(key);
        const data = detail[key] as Record<string, unknown>;
        return (
          <Card key={key} data-section={key} className="overflow-hidden">
            <button
              type="button"
              onClick={() => toggle(key)}
              className="w-full flex items-center justify-between gap-2 px-5 py-4 hover:bg-fulkro-ink-50 transition-colors"
              aria-expanded={isOpen}
            >
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-fulkro-primary-700" aria-hidden />
                <span className="font-semibold text-sm text-fulkro-ink-800">
                  {label}
                </span>
              </div>
              {isOpen ? (
                <ChevronDown className="h-4 w-4 text-fulkro-ink-500" aria-hidden />
              ) : (
                <ChevronRight className="h-4 w-4 text-fulkro-ink-500" aria-hidden />
              )}
            </button>
            {isOpen && (
              <div className={cn("px-5 pb-5")}>{renderers[key](data)}</div>
            )}
          </Card>
        );
      })}
    </div>
  );
}
