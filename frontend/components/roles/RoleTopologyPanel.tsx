"use client";

/**
 * RoleTopologyPanelView real · M28 + M30 EXTENDED wired (SAN-E v3.MB-3.5).
 *
 * Sustituye stub post-FASE-9 + preserva RolesSegregationAlert (CCN-STIC 801
 * RSEG ≠ RSIS · ya wired post-cleanup MB-9.bis.4).
 *
 * Wired al backend:
 *   M28 commit MB-3.E 6daaae2 + GET /role-topology (MB-3.5 backend extension)
 *   M30 EXTENDED commit MB-3.C 8f40347 (project-scoped contacts + constraint v3)
 *
 * 3 secciones:
 * A. Hero coverage_pct + progress bar + blockers list
 * B. 5 cards ENS_REQUIRED · grid responsive · RolesSegregationAlert preservado
 * C. Cross-compliance roles cards (DPO/CISO/Auditor)
 */
import * as React from "react";
import { ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";
import { useRoleTopology } from "@/hooks/useRoleTopology";
import {
  ROLE_LABELS,
  type RoleAssignment,
} from "@/lib/admin-roles/api";

import { AssignContactModal } from "./AssignContactModal";
import { RoleAssignmentCard } from "./RoleAssignmentCard";
import { RolesSegregationAlert } from "./RolesSegregationAlert";

function CoverageBadge({ pct }: { pct: number }) {
  if (pct === 100) {
    return (
      <Badge variant="success" className="gap-1 px-3 py-1 text-sm font-semibold">
        <ShieldCheck size={14} strokeWidth={2.4} />
        Listo para certificación
      </Badge>
    );
  }
  if (pct >= 80) {
    return <Badge variant="info" className="px-3 py-1 text-sm">Casi completo</Badge>;
  }
  if (pct >= 50) {
    return (
      <Badge variant="warning" className="px-3 py-1 text-sm">
        Parcial
      </Badge>
    );
  }
  return (
    <Badge variant="danger" className="px-3 py-1 text-sm font-semibold">
      Cobertura insuficiente
    </Badge>
  );
}

export function RoleTopologyPanelView({ projectId }: { projectId: string }) {
  const rt = useRoleTopology(projectId);
  const [assignFor, setAssignFor] = React.useState<RoleAssignment | null>(null);

  const data = rt.topology.data;

  if (rt.topology.isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
        <Skeleton className="h-32" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mx-auto w-full max-w-6xl px-6 py-8">
        <Card>
          <CardContent className="py-8 text-center text-sm text-fulkro-ink-500">
            No se pudo cargar la topología de roles.
          </CardContent>
        </Card>
      </div>
    );
  }

  const coveragePct = data.coverage_pct;
  const ensAssignments = data.roles_required;
  const crossAssignments = data.cross_compliance_extras;

  // Derivar si RSEG y RSIS comparten contacto · alimenta SegregationAlert visual
  const rseg = ensAssignments.find((a) => a.role_code === "responsable_seguridad");
  const rsis = ensAssignments.find((a) => a.role_code === "responsable_sistema");
  const rsegRsisShared = Boolean(
    rseg?.contact_id && rseg.contact_id === rsis?.contact_id,
  );

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      {/* A · Hero coverage */}
      <Card>
        <CardContent className="flex flex-col gap-4 pt-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-wide text-fulkro-ink-400">
                Cobertura roles ENS{" "}
                <TooltipENS
                  text="Los 5 roles obligatorios del ENS (Sponsor · RI · RS · RSEG · RSIS) deben estar asignados antes de certificar. Sin ellos, el auditor no firma. CCN-STIC 801 también exige que RSEG ≠ RSIS (segregación de funciones)."
                  iconSize={12}
                />
              </span>
              <span className="text-3xl font-bold text-[color:var(--fulkro-title)] tabular-nums">
                {coveragePct.toFixed(0)}%
              </span>
              <span className="text-xs text-fulkro-ink-500">
                {data.assigned_required} / {data.total_required} roles obligatorios asignados
              </span>
            </div>
            <CoverageBadge pct={coveragePct} />
          </div>

          {/* Progress bar */}
          <div className="h-2 w-full overflow-hidden rounded-full bg-fulkro-ink-100">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                coveragePct === 100
                  ? "bg-fulkro-success"
                  : coveragePct >= 50
                  ? "bg-fulkro-info"
                  : "bg-fulkro-danger",
              )}
              style={{ width: `${coveragePct}%` }}
            />
          </div>

          {/* Blockers chips */}
          {data.blockers.length > 0 ? (
            <div className="flex flex-col gap-2 rounded-md border border-fulkro-warning/30 bg-fulkro-warning/5 p-3">
              <p className="text-xs font-bold uppercase tracking-wide text-fulkro-warning">
                Roles obligatorios sin asignar
              </p>
              <div className="flex flex-wrap gap-2">
                {data.blockers.map((roleCode) => {
                  const meta = ROLE_LABELS[roleCode];
                  const assignment = ensAssignments.find(
                    (a) => a.role_code === roleCode,
                  );
                  return (
                    <button
                      key={roleCode}
                      type="button"
                      onClick={() => assignment && setAssignFor(assignment)}
                      className="rounded-full border border-fulkro-warning/40 bg-white px-3 py-1 text-xs font-bold text-fulkro-warning transition-colors hover:bg-fulkro-warning/10"
                    >
                      {meta?.short ?? roleCode} · asignar →
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* B · ENS_REQUIRED grid */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-bold text-[color:var(--fulkro-title)]">
            Roles ENS obligatorios{" "}
            <TooltipENS
              text="Anexo II del RD 311/2022. Los 5 roles que tu organización DEBE tener asignados para certificar ENS. CCN-STIC 801 detalla las responsabilidades de cada uno."
              iconSize={13}
            />
          </h2>
          <Badge variant="outline">
            {data.assigned_required} / {data.total_required}
          </Badge>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {ensAssignments.map((assignment) => (
            <RoleAssignmentCard
              key={assignment.role_code}
              projectId={projectId}
              assignment={assignment}
              onAssignClick={(a) => setAssignFor(a)}
            />
          ))}
        </div>
        {/* RolesSegregationAlert preservado · CCN-STIC 801 RSEG ≠ RSIS */}
        <RolesSegregationAlert projectId={projectId} />
        {rsegRsisShared ? (
          <Card className="border-fulkro-danger/40 bg-fulkro-danger/5">
            <CardContent className="py-3 text-xs text-fulkro-danger">
              ⚠️ <strong>RSEG y RSIS comparten contacto</strong> · CCN-STIC 801
              exige segregación de funciones. Asigna contactos distintos antes
              de certificar.
            </CardContent>
          </Card>
        ) : null}
      </section>

      {/* C · Cross-compliance */}
      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-bold text-[color:var(--fulkro-title)]">
            Roles cross-compliance{" "}
            <TooltipENS
              text="Roles requeridos por OTROS marcos regulatorios (RGPD · ISO 27001 · NIS2). Si tratas datos personales a gran escala, RGPD Art. 37 obliga a tener un DPO. Si pretendes certificar ISO 27001 además del ENS, necesitas un CISO."
              iconSize={13}
            />
          </h2>
          <Badge variant="outline">opcional</Badge>
        </div>
        <p className="text-xs text-fulkro-ink-500">
          Roles fuera del Anexo II ENS pero requeridos por marcos asociados
          (RGPD · ISO 27001 · auditoría interna). Su asignación NO bloquea
          certificación ENS.
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {crossAssignments.map((assignment) => (
            <RoleAssignmentCard
              key={assignment.role_code}
              projectId={projectId}
              assignment={assignment}
              onAssignClick={(a) => setAssignFor(a)}
              isCrossCompliance
            />
          ))}
        </div>
      </section>

      {/* Modal asignación */}
      <AssignContactModal
        projectId={projectId}
        assignment={assignFor}
        open={assignFor !== null}
        onOpenChange={(v) => {
          if (!v) setAssignFor(null);
        }}
      />
    </div>
  );
}
