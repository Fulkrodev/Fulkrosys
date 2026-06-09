/**
 * DdaCatalogView · catálogo Anexo II read-only · sub-atom 1.D.F.A v3.11.
 *
 * 73 medidas Anexo II ENS (RD 311/2022) read-only. Útil para Marcos verificar
 * si una medida específica existe + ver descripción canonical.
 *
 * Filtros marco.
 */
"use client";

import * as React from "react";
import { Filter, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import { useDdaAdminCatalog } from "@/hooks/useDdaAdmin";
import { DDA_MARCO_LABELS, type DdaMarco } from "@/lib/api/dda";

type MarcoFilter = DdaMarco | "all";

const MARCO_FILTERS: { value: MarcoFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "org", label: "Organizativo" },
  { value: "op", label: "Operacional" },
  { value: "mp", label: "Protección" },
];

export function DdaCatalogView() {
  const [marcoFilter, setMarcoFilter] = React.useState<MarcoFilter>("all");

  const { data, isLoading, isError, error } = useDdaAdminCatalog(
    marcoFilter === "all" ? undefined : marcoFilter,
  );

  return (
    <Card data-testid="dda-catalog-view">
      <CardContent className="py-4 space-y-4">
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
                data-testid={`dda-catalog-filter-${f.value}`}
              >
                {f.label}
              </Button>
            ))}
          </div>
          {data && (
            <span className="ml-auto text-foreground/70">
              {data.length} medidas
            </span>
          )}
        </div>

        {isLoading && (
          <div
            className="flex items-center gap-2 py-6 text-sm text-foreground/70"
            data-testid="dda-catalog-loading"
          >
            <Loader2 className="size-4 animate-spin" />
            Cargando catálogo Anexo II…
          </div>
        )}

        {isError && (
          <div
            className="py-6 text-sm text-foreground/70"
            data-testid="dda-catalog-error"
          >
            <p className="font-medium">No se pudo cargar el catálogo</p>
            <p className="text-xs text-foreground/70 mt-1">
              {error instanceof Error ? error.message : "Error desconocido"}
            </p>
          </div>
        )}

        {!isLoading && !isError && data && data.length === 0 && (
          <p className="py-6 text-sm text-foreground/70 italic">
            Sin medidas con este filtro.
          </p>
        )}

        {!isLoading && data && data.length > 0 && (
          <div
            className="space-y-1.5 max-h-[60vh] overflow-y-auto pr-1"
            data-testid="dda-catalog-list"
          >
            {data.map((measure) => (
              <div
                key={measure.codigo}
                className="flex items-start gap-3 rounded border px-3 py-2 bg-card"
                data-testid={`dda-catalog-row-${measure.codigo}`}
              >
                <div className="flex flex-col items-start gap-1 min-w-[6rem]">
                  <span className="font-mono text-xs font-semibold">
                    {measure.codigo}
                  </span>
                  <Badge variant="secondary" className="text-[9px]">
                    {DDA_MARCO_LABELS[measure.marco as DdaMarco] ??
                      measure.marco}
                  </Badge>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{measure.nombre}</p>
                  {measure.familia && (
                    <p className="text-[10px] text-foreground/70 uppercase tracking-wide">
                      Familia: {measure.familia}
                    </p>
                  )}
                  {measure.descripcion && (
                    <p className="text-xs text-foreground/70 mt-1 whitespace-pre-line">
                      {measure.descripcion}
                    </p>
                  )}
                  {measure.categoria_minima && (
                    <Badge variant="outline" className="text-[9px] mt-1">
                      Categ. mínima: {measure.categoria_minima}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
