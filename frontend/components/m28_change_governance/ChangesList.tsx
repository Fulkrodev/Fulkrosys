"use client";

/**
 * ChangesList · Sub-atom 1.D.D.B v3.11.
 *
 * Lista de cambios del proyecto con filtros estado + botón "Solicitar
 * nuevo cambio" que abre el wizard 5 steps. Click row abre detalle.
 * Reuse patrón ContractsList (1.D.D.A) + ActionPlansPanel (1.D.C.B).
 *
 * Backend: m28 `/api/v1/changes/projects/{pid}/changes/open`.
 */
import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { GitBranch, Plus } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CHANGE_STATE_LABELS,
  CHANGE_STATE_VARIANTS,
  changesApi,
  type OpenChangeItem,
} from "@/lib/api/changes";

import { ChangeDetailModal } from "./ChangeDetailModal";
import { ChangeRequestWizard } from "./ChangeRequestWizard";

interface ChangesListProps {
  projectId: string;
}

const STATE_FILTERS: { id: string; label: string }[] = [
  { id: "all", label: "Todos" },
  { id: "intake", label: "Intake" },
  { id: "assessed", label: "Evaluados" },
  { id: "approved", label: "Aprobados" },
  { id: "rejected", label: "Rechazados" },
];

export function ChangesList({ projectId }: ChangesListProps) {
  const qc = useQueryClient();
  const [stateFilter, setStateFilter] = useState<string>("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);

  const listQuery = useQuery({
    queryKey: ["m28", "changes-open", projectId],
    queryFn: () => changesApi.listOpen(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  const filteredItems = useMemo(() => {
    const items = listQuery.data ?? [];
    if (stateFilter === "all") return items;
    return items.filter((c) => c.state === stateFilter);
  }, [listQuery.data, stateFilter]);

  const counts = useMemo(() => {
    const items = listQuery.data ?? [];
    const map = new Map<string, number>();
    map.set("all", items.length);
    for (const c of items) {
      map.set(c.state, (map.get(c.state) ?? 0) + 1);
    }
    return map;
  }, [listQuery.data]);

  return (
    <div className="space-y-4" data-testid="changes-list">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <GitBranch size={18} /> Cambios e impacto
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground">
              Materiality engine determinista (Motor 28) · 10 preguntas
              binarias · niveles MINOR / RELEVANT / MATERIAL · workflows
              requeridos auto-disparados (recategorización · auditoría
              extraordinaria · renovación · DdA · MAGERIT · roles).
            </p>
          </div>
          <Button
            size="sm"
            onClick={() => setWizardOpen(true)}
            data-testid="changes-request-button"
          >
            <Plus size={14} className="mr-1" />
            Solicitar cambio
          </Button>
        </CardHeader>
      </Card>

      <div
        className="flex flex-wrap items-center gap-2"
        data-testid="changes-filters"
      >
        {STATE_FILTERS.map((f) => {
          const active = stateFilter === f.id;
          const count = counts.get(f.id) ?? 0;
          return (
            <Button
              key={f.id}
              size="sm"
              variant={active ? "primary" : "outline"}
              onClick={() => setStateFilter(f.id)}
              data-testid={`changes-filter-${f.id}`}
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
        <Alert variant="danger" data-testid="changes-error">
          <AlertTitle>No se pudo cargar la lista de cambios</AlertTitle>
          <AlertDescription>
            {listQuery.error instanceof Error
              ? listQuery.error.message
              : "Error desconocido"}
          </AlertDescription>
        </Alert>
      ) : filteredItems.length === 0 ? (
        <Card>
          <CardContent className="p-6" data-testid="changes-empty">
            <EmptyState
              title="Sin cambios"
              description={
                stateFilter === "all"
                  ? "Cuando se solicite un cambio aparecerá aquí con su clasificación de materialidad."
                  : "Ningún cambio en ese estado."
              }
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="space-y-2 p-4" data-testid="changes-rows">
            {filteredItems.map((c) => (
              <ChangeRow
                key={c.change_id}
                item={c}
                onSelect={() => setSelectedId(c.change_id)}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {selectedId && (
        <ChangeDetailModal
          projectId={projectId}
          changeId={selectedId}
          open={Boolean(selectedId)}
          onOpenChange={(o) => !o && setSelectedId(null)}
        />
      )}

      <ChangeRequestWizard
        projectId={projectId}
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        onCompleted={() => {
          qc.invalidateQueries({
            queryKey: ["m28", "changes-open", projectId],
          });
        }}
      />
    </div>
  );
}

function ChangeRow({
  item,
  onSelect,
}: {
  item: OpenChangeItem;
  onSelect: () => void;
}) {
  const variant = CHANGE_STATE_VARIANTS[item.state] ?? "secondary";
  const label = CHANGE_STATE_LABELS[item.state] ?? item.state;
  return (
    <button
      type="button"
      onClick={onSelect}
      className="flex w-full items-start justify-between gap-3 rounded-md border border-fulkro-ink-300/60 px-3 py-2 text-left transition-colors hover:bg-fulkro-surface-glass-strong/50"
      data-testid={`changes-row-${item.change_id}`}
    >
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-fulkro-ink-700">
          {item.description}
        </p>
        <p className="mt-0.5 font-mono text-[10px] text-fulkro-ink-500">
          #{item.change_id.slice(0, 8)}
        </p>
      </div>
      <Badge variant={variant} className="shrink-0">
        {label}
      </Badge>
    </button>
  );
}
