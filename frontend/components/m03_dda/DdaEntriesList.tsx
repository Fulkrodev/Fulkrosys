/**
 * DdaEntriesList · listado 73 medidas Anexo II per proyecto · sub-atom 1.D.F.A v3.11.
 *
 * Tabla simple (NO TanStack v8 reuse · sosten DRY pattern existing m14_contracts).
 * Filtros: marco (org/op/mp · all) · familia · estado_implementacion.
 */
"use client";

import * as React from "react";
import { Filter, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import { useDdaAdminEntries } from "@/hooks/useDdaAdmin";
import {
  DDA_ESTADO_LABELS,
  DDA_ESTADO_VARIANT,
  DDA_MARCO_LABELS,
  type DdaAdminEntry,
  type DdaMarco,
} from "@/lib/api/dda";

interface DdaEntriesListProps {
  projectId: string;
  onSelectEntry?: (entry: DdaAdminEntry) => void;
}

type MarcoFilter = DdaMarco | "all";
type EstadoFilter =
  | "all"
  | "no_valorado"
  | "no_aplica"
  | "no_implantada"
  | "parcial"
  | "implantada";

const MARCO_FILTERS: { value: MarcoFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "org", label: "Organizativo" },
  { value: "op", label: "Operacional" },
  { value: "mp", label: "Protección" },
];

const ESTADO_FILTERS: { value: EstadoFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "no_valorado", label: "No valorado" },
  { value: "no_implantada", label: "No implantada" },
  { value: "parcial", label: "Parcial" },
  { value: "implantada", label: "Implantada" },
  { value: "no_aplica", label: "No aplica" },
];

export function DdaEntriesList({
  projectId,
  onSelectEntry,
}: DdaEntriesListProps) {
  const [marcoFilter, setMarcoFilter] = React.useState<MarcoFilter>("all");
  const [estadoFilter, setEstadoFilter] = React.useState<EstadoFilter>("all");

  const { data, isLoading, isError, error } = useDdaAdminEntries(
    projectId,
    marcoFilter === "all" ? undefined : { marco: marcoFilter },
  );

  const filteredEntries = React.useMemo(() => {
    if (!data) return [];
    if (estadoFilter === "all") return data;
    return data.filter((e) => e.estado_implementacion === estadoFilter);
  }, [data, estadoFilter]);

  return (
    <Card data-testid="dda-entries-list">
      <CardContent className="py-4 space-y-4">
        {/* Filters */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-xs font-medium text-foreground/70">
            <Filter className="size-3.5" />
            <span>Marco:</span>
            <div className="flex flex-wrap gap-1">
              {MARCO_FILTERS.map((f) => (
                <Button
                  key={f.value}
                  type="button"
                  size="sm"
                  variant={marcoFilter === f.value ? "primary" : "outline"}
                  onClick={() => setMarcoFilter(f.value)}
                  data-testid={`dda-filter-marco-${f.value}`}
                >
                  {f.label}
                </Button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs font-medium text-foreground/70">
            <Filter className="size-3.5" />
            <span>Estado:</span>
            <div className="flex flex-wrap gap-1">
              {ESTADO_FILTERS.map((f) => (
                <Button
                  key={f.value}
                  type="button"
                  size="sm"
                  variant={estadoFilter === f.value ? "primary" : "outline"}
                  onClick={() => setEstadoFilter(f.value)}
                  data-testid={`dda-filter-estado-${f.value}`}
                >
                  {f.label}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {/* List */}
        {isLoading && (
          <div
            className="flex items-center gap-2 py-6 text-sm text-foreground/70"
            data-testid="dda-entries-loading"
          >
            <Loader2 className="size-4 animate-spin" />
            Cargando medidas DdA…
          </div>
        )}

        {isError && (
          <div
            className="py-6 text-sm text-foreground/70"
            data-testid="dda-entries-error"
          >
            <p className="font-medium">No se pudieron cargar las medidas</p>
            <p className="text-xs text-foreground/70 mt-1">
              {error instanceof Error ? error.message : "Error desconocido"}
            </p>
          </div>
        )}

        {!isLoading && !isError && filteredEntries.length === 0 && (
          <div
            className="py-6 text-sm text-foreground/70 italic"
            data-testid="dda-entries-empty"
          >
            ✨ No hay medidas con los filtros actuales · ajusta el filtro o
            genera la DdA si aún no existe.
          </div>
        )}

        {!isLoading && filteredEntries.length > 0 && (
          <div className="overflow-x-auto">
            <table
              className="w-full text-sm border-separate border-spacing-y-1"
              data-testid="dda-entries-table"
            >
              <thead>
                <tr className="text-left text-xs uppercase text-foreground/70 tracking-wide">
                  <th className="px-2 py-1">Código</th>
                  <th className="px-2 py-1">Medida</th>
                  <th className="px-2 py-1">Marco</th>
                  <th className="px-2 py-1">Estado</th>
                  <th className="px-2 py-1">Responsable</th>
                  <th className="px-2 py-1 text-right">Acción</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntries.map((entry) => (
                  <tr
                    key={entry.id}
                    className="bg-card border rounded"
                    data-testid={`dda-entry-row-${entry.measure_codigo}`}
                  >
                    <td className="px-2 py-2 font-mono text-xs">
                      {entry.measure_codigo}
                    </td>
                    <td className="px-2 py-2">{entry.measure_nombre}</td>
                    <td className="px-2 py-2 text-xs">
                      <Badge variant="secondary" className="text-[10px]">
                        {DDA_MARCO_LABELS[
                          entry.measure_marco as DdaMarco
                        ] ?? entry.measure_marco}
                      </Badge>
                    </td>
                    <td className="px-2 py-2">
                      <Badge
                        variant={
                          DDA_ESTADO_VARIANT[entry.estado_implementacion] ??
                          "secondary"
                        }
                        className="text-[10px]"
                      >
                        {DDA_ESTADO_LABELS[entry.estado_implementacion] ??
                          entry.estado_implementacion}
                      </Badge>
                    </td>
                    <td className="px-2 py-2 text-xs text-foreground/70">
                      {entry.responsable ?? "—"}
                    </td>
                    <td className="px-2 py-2 text-right">
                      {onSelectEntry && (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => onSelectEntry(entry)}
                          data-testid={`dda-entry-detail-${entry.measure_codigo}`}
                        >
                          Detalle
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
