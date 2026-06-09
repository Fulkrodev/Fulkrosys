"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert, UserPlus, Users } from "lucide-react";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  useDiscoveryIdentities,
  useIdentitiesSummary,
} from "@/hooks/useDiscovery";
import type { DiscoveryIdentity } from "@/lib/admin-discovery/api";

export interface IdentityTabProps {
  projectId: string;
}

export function IdentityTab({ projectId }: IdentityTabProps) {
  const router = useRouter();
  const { data: identities = [], isLoading } = useDiscoveryIdentities(projectId);
  const { data: summary } = useIdentitiesSummary(projectId);

  const columns: ColumnDef<DiscoveryIdentity>[] = [
    {
      accessorKey: "username",
      header: "Usuario",
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-medium">
            {row.original.display_name ?? row.original.username ?? "—"}
          </span>
          {row.original.email ? (
            <span className="text-xs text-fulkro-ink-500">{row.original.email}</span>
          ) : null}
        </div>
      ),
    },
    {
      accessorKey: "tipo_cuenta",
      header: "Tipo",
      cell: ({ row }) =>
        row.original.tipo_cuenta ? (
          <Badge variant="outline">{row.original.tipo_cuenta}</Badge>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      accessorKey: "directorio",
      header: "Directorio",
      cell: ({ row }) => row.original.directorio ?? "—",
    },
    {
      accessorKey: "es_privilegiada",
      header: "Privilegiada",
      cell: ({ row }) =>
        row.original.es_privilegiada ? (
          <Badge variant="warning">Sí</Badge>
        ) : (
          <Badge variant="secondary">No</Badge>
        ),
    },
    {
      accessorKey: "mfa_activo",
      header: "MFA",
      cell: ({ row }) => {
        if (row.original.mfa_activo === null)
          return <span className="text-fulkro-ink-300">—</span>;
        return row.original.mfa_activo ? (
          <Badge variant="success">activo</Badge>
        ) : (
          <Badge variant="danger">sin MFA</Badge>
        );
      },
    },
    {
      accessorKey: "dias_inactiva",
      header: "Inactiva",
      cell: ({ row }) => {
        const dias = row.original.dias_inactiva;
        if (dias === null || dias === undefined) return "—";
        return (
          <span className={dias > 90 ? "text-fulkro-warning" : ""}>{dias}d</span>
        );
      },
    },
    {
      id: "acciones",
      header: "Acciones",
      cell: ({ row }) => (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => router.push(`/admin/projects/${projectId}/roles`)}
        >
          <UserPlus className="mr-1 size-3.5" />
          Asignar rol ENS
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Users size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Identidades descubiertas
            {summary ? (
              <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
                ({summary.total})
              </span>
            ) : null}
          </h3>
        </div>
        {summary ? (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {summary.privilegiadas > 0 ? (
              <Badge variant="warning">
                <ShieldAlert className="mr-1 size-3" /> {summary.privilegiadas} privilegiadas
              </Badge>
            ) : null}
            {summary.sin_mfa > 0 ? (
              <Badge variant="danger">{summary.sin_mfa} sin MFA</Badge>
            ) : null}
            {summary.inactivas > 0 ? (
              <Badge variant="secondary">{summary.inactivas} inactivas</Badge>
            ) : null}
          </div>
        ) : null}
      </div>

      <DataTable
        columns={columns}
        data={identities}
        searchKey="username"
        searchPlaceholder="Buscar identidades…"
        loading={isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <Users className="size-8" />
            <p className="text-sm">Sin identidades descubiertas</p>
          </div>
        }
      />
    </div>
  );
}
