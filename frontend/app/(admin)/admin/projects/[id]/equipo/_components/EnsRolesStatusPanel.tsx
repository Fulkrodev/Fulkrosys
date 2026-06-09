"use client";

/**
 * EnsRolesStatusPanel · sub-atom 1.C.F.1 (placeholder) + 1.C.F.4 v3.10
 * (interactivo).
 *
 * Muestra status ENS_REQUIRED roles per project via m30 ens_required_api.
 * 1.C.F.4 añade:
 *   - Priority badge per role (critical/recommended/optional) según category.
 *   - Click row "Pendiente"/"Asignado" → modal asignar/vacate.
 *   - Gap banner top si quedan críticos sin asignar.
 *   - Roles INVISIBLES al cliente · ADR-020 v5 Q5.3.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { ApiError } from "@/lib/api";
import {
  ENS_ROLE_DESCRIPTIONS_FRONTEND,
  ENS_ROLE_LABELS_FRONTEND,
  getEnsRequiredRolesStatus,
  type EnsRequiredRolesStatus,
  type EnsRolePriority,
} from "@/lib/api/project-contacts";

import { EnsRoleAssignModal } from "./EnsRoleAssignModal";
import { EnsRolesGapBanner } from "./EnsRolesGapBanner";

type Props = {
  projectId: string;
  /** Bump value desde el padre para forzar refetch externo. */
  reloadKey?: number;
};

function priorityBadgeVariant(
  priority: EnsRolePriority,
): "danger" | "warning" | "outline" {
  if (priority === "critical") return "danger";
  if (priority === "recommended") return "warning";
  return "outline";
}

function priorityLabel(priority: EnsRolePriority): string {
  if (priority === "critical") return "Crítico";
  if (priority === "recommended") return "Recomendado";
  return "Opcional";
}

export function EnsRolesStatusPanel({ projectId, reloadKey }: Props) {
  const [status, setStatus] = useState<EnsRequiredRolesStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingRole, setEditingRole] = useState<string | null>(null);
  const [localReload, setLocalReload] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getEnsRequiredRolesStatus(projectId)
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch((err) => {
        if (cancelled) return;
        const msg =
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error cargando roles ENS";
        toast.error(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, reloadKey, localReload]);

  if (loading && !status) {
    return <Skeleton className="h-32" />;
  }

  if (!status) {
    return (
      <Card>
        <CardContent className="py-6 text-center text-sm text-[color:var(--fulkro-muted)]">
          No se pudo cargar el estado de roles ENS.
        </CardContent>
      </Card>
    );
  }

  const handleSaved = () => {
    setEditingRole(null);
    setLocalReload((k) => k + 1);
  };

  const currentContactId = editingRole
    ? status.roles[editingRole]?.contact_id ?? null
    : null;

  return (
    <div className="flex flex-col gap-4">
      <EnsRolesGapBanner status={status} />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base">
              Roles ENS · RD 311/2022
              {status.project_category ? (
                <Badge variant="outline" className="ml-2">
                  Categoría {status.project_category}
                </Badge>
              ) : null}
            </CardTitle>
            <Badge variant={status.all_assigned ? "success" : "warning"}>
              {status.total_assigned} / {status.total_required} asignados
            </Badge>
          </div>
          <p className="mt-1 text-sm text-[color:var(--fulkro-muted)]">
            Stakeholders nombrados para documentos ENS auto-generados (E-002,
            E-012, E-040, E-027, E-028, E-041, E-042, E-006). Marcos-managed ·
            INVISIBLES al cliente. La asignación detallada vive también en{" "}
            <Link
              href={`/admin/projects/${projectId}/roles`}
              className="text-fulkro-primary-700 underline-offset-2 hover:underline"
            >
              Topología de roles
            </Link>
            .
          </p>
        </CardHeader>
        <CardContent>
          <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {Object.entries(status.roles).map(([role, assignment]) => {
              const priority = status.priority[role] ?? "recommended";
              return (
                <li
                  key={role}
                  className="flex items-start justify-between gap-2 rounded-md border border-fulkro-ink-100 px-3 py-2"
                >
                  <div className="flex flex-col gap-1">
                    <span className="text-sm font-medium text-fulkro-ink-800">
                      {ENS_ROLE_LABELS_FRONTEND[role] ?? role}
                    </span>
                    <span className="text-xs text-[color:var(--fulkro-muted)]">
                      {assignment
                        ? `${assignment.full_name} · ${assignment.email}`
                        : ENS_ROLE_DESCRIPTIONS_FRONTEND[role] ??
                          "Pendiente asignar"}
                    </span>
                    <div className="mt-1 flex gap-1">
                      <Badge variant={priorityBadgeVariant(priority)}>
                        {priorityLabel(priority)}
                      </Badge>
                      {assignment ? (
                        <Badge variant="success">Asignado</Badge>
                      ) : (
                        <Badge variant="warning">Pendiente</Badge>
                      )}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setEditingRole(role)}
                  >
                    {assignment ? "Cambiar" : "Asignar"}
                  </Button>
                </li>
              );
            })}
          </ul>
        </CardContent>
      </Card>

      <EnsRoleAssignModal
        projectId={projectId}
        role={editingRole}
        currentContactId={currentContactId}
        onClose={() => setEditingRole(null)}
        onSaved={handleSaved}
      />
    </div>
  );
}
