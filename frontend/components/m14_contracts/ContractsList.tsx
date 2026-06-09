"use client";

/**
 * ContractsList · Sub-atom 1.D.D.A v3.11.
 *
 * Tabla de contratos del proyecto con filtros estado · click row abre
 * ContractDetailModal. Reuse patrón ActionPlansPanel (1.D.C.B): badges
 * estado · loading skeleton · empty state · error alert · data-testid
 * completo para E2E fase_24.
 *
 * Backend: m14_contracts `/api/v1/contracts/projects/{id}/contracts`.
 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileSignature, Plus } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CONTRACT_ESTADO_LABELS,
  CONTRACT_ESTADO_VARIANTS,
  type Contract,
  type ContractEstado,
  contractsApi,
} from "@/lib/api/contracts";

import { ContractDetailModal } from "./ContractDetailModal";
import { ContractGenerateWizard } from "./ContractGenerateWizard";

interface ContractsListProps {
  projectId: string;
}

const ESTADO_FILTERS: { id: ContractEstado | "all"; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "draft", label: "Borrador" },
  { id: "firmado_marcos", label: "Firmado Marcos" },
  { id: "sent", label: "Enviado" },
  { id: "firmado_cliente", label: "Firmado cliente" },
  { id: "vigente", label: "Vigente" },
];

export function ContractsList({ projectId }: ContractsListProps) {
  const [estadoFilter, setEstadoFilter] = useState<ContractEstado | "all">(
    "all",
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);

  const listQuery = useQuery({
    queryKey: ["m14", "contracts", projectId],
    queryFn: () => contractsApi.list(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const filteredContracts = useMemo(() => {
    const items = listQuery.data?.contracts ?? [];
    if (estadoFilter === "all") return items;
    return items.filter((c) => c.estado === estadoFilter);
  }, [listQuery.data, estadoFilter]);

  const counts = useMemo(() => {
    const items = listQuery.data?.contracts ?? [];
    const map = new Map<ContractEstado | "all", number>();
    map.set("all", items.length);
    for (const c of items) {
      map.set(c.estado, (map.get(c.estado) ?? 0) + 1);
    }
    return map;
  }, [listQuery.data]);

  return (
    <div className="space-y-4" data-testid="contracts-list">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileSignature size={18} /> Contratos del proyecto
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Lifecycle C-001 servicios ENS · C-002 adenda proveedores · C-003
              retainer · C-004 NDA · C-005 SLA · firma DOCX + magic link.
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => setWizardOpen(true)}
            data-testid="contracts-generate-button"
          >
            <Plus size={14} className="mr-1" />
            Generar contrato
          </Button>
        </CardHeader>
      </Card>

      <div
        className="flex flex-wrap items-center gap-2"
        data-testid="contracts-filters"
      >
        {ESTADO_FILTERS.map((f) => {
          const active = estadoFilter === f.id;
          const count = counts.get(f.id) ?? 0;
          return (
            <Button
              key={f.id}
              size="sm"
              variant={active ? "primary" : "outline"}
              onClick={() => setEstadoFilter(f.id)}
              data-testid={`contracts-filter-${f.id}`}
            >
              {f.label}
              <Badge variant="secondary" className="ml-2">
                {count}
              </Badge>
            </Button>
          );
        })}
      </div>

      {listQuery.isLoading ? (
        <Card>
          <CardContent className="space-y-2 p-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      ) : listQuery.isError ? (
        <Alert variant="danger" data-testid="contracts-error">
          <AlertTitle>No se pudo cargar la lista de contratos</AlertTitle>
          <AlertDescription>
            {listQuery.error instanceof Error
              ? listQuery.error.message
              : "Error desconocido"}
          </AlertDescription>
        </Alert>
      ) : filteredContracts.length === 0 ? (
        <Card>
          <CardContent className="p-6" data-testid="contracts-empty">
            <EmptyState
              title="Sin contratos"
              description={
                estadoFilter === "all"
                  ? "Genera el primer contrato cuando tengas una propuesta won."
                  : "Ningún contrato en ese estado."
              }
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <ContractsTable
              contracts={filteredContracts}
              onSelect={(id) => setSelectedId(id)}
            />
          </CardContent>
        </Card>
      )}

      {selectedId && (
        <ContractDetailModal
          projectId={projectId}
          contractId={selectedId}
          open={Boolean(selectedId)}
          onOpenChange={(o) => !o && setSelectedId(null)}
        />
      )}

      <ContractGenerateWizard
        projectId={projectId}
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        onGenerated={() => {
          setWizardOpen(false);
          listQuery.refetch();
        }}
      />
    </div>
  );
}

function ContractsTable({
  contracts,
  onSelect,
}: {
  contracts: Contract[];
  onSelect: (id: string) => void;
}) {
  return (
    <table
      className="w-full text-sm"
      data-testid="contracts-table"
    >
      <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
        <tr>
          <th className="px-3 py-2 text-left font-semibold">Plantilla</th>
          <th className="px-3 py-2 text-left font-semibold">Tipo</th>
          <th className="px-3 py-2 text-left font-semibold">Firmante cliente</th>
          <th className="px-3 py-2 text-left font-semibold">Vigencia</th>
          <th className="px-3 py-2 text-left font-semibold">Estado</th>
        </tr>
      </thead>
      <tbody>
        {contracts.map((c) => (
          <tr
            key={c.id}
            className="cursor-pointer border-t border-fulkro-ink-300/40 hover:bg-fulkro-surface-glass-strong/50"
            onClick={() => onSelect(c.id)}
            data-testid={`contracts-row-${c.id}`}
          >
            <td className="px-3 py-2">
              <code className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 text-[10px] font-mono">
                {c.plantilla_id}
              </code>
            </td>
            <td className="px-3 py-2 text-fulkro-ink-700">{c.tipo}</td>
            <td className="px-3 py-2">
              <div className="flex flex-col">
                <span className="font-medium">{c.cliente_firmante_nombre}</span>
                <span className="text-xs text-muted-foreground">
                  {c.cliente_firmante_cargo}
                </span>
              </div>
            </td>
            <td className="px-3 py-2 text-xs text-muted-foreground">
              {c.vigente_desde ? formatDate(c.vigente_desde) : "—"}
              {c.vigente_hasta ? ` → ${formatDate(c.vigente_hasta)}` : ""}
            </td>
            <td className="px-3 py-2">
              <Badge variant={CONTRACT_ESTADO_VARIANTS[c.estado]}>
                {CONTRACT_ESTADO_LABELS[c.estado]}
              </Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}
