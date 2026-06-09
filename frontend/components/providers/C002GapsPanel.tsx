"use client";

/**
 * C002GapsPanel · Drawer lateral para revisar gaps cross-compliance.
 *
 * Wired backend M14 GET /providers/{id}/gaps + POST /c002/generate.
 * Filtros framework · cláusula sugerida copiable · CTA generar C-002.
 */
import * as React from "react";
import { CheckCircle2, Copy, Loader2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  useProviderGaps,
  useProviders,
} from "@/hooks/useProviders";
import type {
  GapFramework,
  Provider,
  ProviderGap,
} from "@/lib/admin-providers/api";

const FRAMEWORK_LABELS: Record<GapFramework, string> = {
  ENS: "ENS",
  GDPR: "GDPR",
  NIS2: "NIS2",
};

function FrameworkBadge({ framework }: { framework: GapFramework }) {
  const variant: "info" | "accent" | "warning" = (
    {
      ENS: "info",
      GDPR: "accent",
      NIS2: "warning",
    } as const
  )[framework];
  return <Badge variant={variant}>{FRAMEWORK_LABELS[framework]}</Badge>;
}

function SeverityBadge({ severity }: { severity: ProviderGap["severity"] }) {
  const variant: "danger" | "warning" | "info" | "secondary" = (
    {
      CRITICA: "danger",
      ALTA: "danger",
      MEDIA: "warning",
      BAJA: "info",
    } as const
  )[severity];
  return <Badge variant={variant}>{severity}</Badge>;
}

interface C002GapsPanelProps {
  projectId: string;
  provider: Provider | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function C002GapsPanel({
  projectId,
  provider,
  open,
  onOpenChange,
}: C002GapsPanelProps) {
  const ph = useProviders(projectId);
  const gapsQuery = useProviderGaps(projectId, provider?.id ?? null);
  const [filter, setFilter] = React.useState<GapFramework | "todos">("todos");

  const gaps = gapsQuery.data?.gaps ?? [];
  const filteredGaps = React.useMemo(
    () =>
      filter === "todos"
        ? gaps
        : gaps.filter((g) => g.framework === filter),
    [gaps, filter],
  );

  const onCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Cláusula copiada al portapapeles");
    } catch {
      toast.error("Error al copiar al portapapeles");
    }
  };

  const onGenerateC002 = async () => {
    if (!provider) return;
    try {
      const res = await ph.generateC002.mutateAsync(provider.id);
      toast.success(
        `C-002 generado · ${res.covered_gaps.length} gap(s) cubiertos`,
      );
      onOpenChange(false);
    } catch {
      toast.error("Error al generar C-002");
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full max-w-xl overflow-y-auto sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-[color:var(--fulkro-title)]">
            <ShieldAlert size={18} strokeWidth={2.4} className="text-fulkro-warning" />
            Gaps detectados · {provider?.name ?? ""}
          </SheetTitle>
          <SheetDescription>
            Cláusulas cross-compliance pendientes en C-002 ·{" "}
            <TooltipENS
              text="Cuando un proveedor trata datos personales o críticos para ENS, hay cláusulas obligatorias que tu contrato (C-002) debe contener. Si faltan, hay drift normativo."
              iconSize={12}
            />
          </SheetDescription>
        </SheetHeader>

        {/* Filter chips */}
        <div className="my-4 flex flex-wrap gap-2">
          {(["todos", "ENS", "GDPR", "NIS2"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                filter === f
                  ? "border-fulkro-primary-700 bg-fulkro-primary-700 text-white"
                  : "border-fulkro-ink-200 bg-white text-fulkro-ink-700 hover:bg-fulkro-ink-50"
              }`}
            >
              {f === "todos" ? "Todos" : f}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-3">
          {gapsQuery.isLoading ? (
            <p className="py-8 text-center text-sm text-fulkro-ink-400">
              Cargando gaps…
            </p>
          ) : filteredGaps.length === 0 ? (
            <div className="flex flex-col items-center gap-1 py-8 text-center">
              <CheckCircle2
                size={28}
                strokeWidth={2.4}
                className="text-fulkro-success"
              />
              <p className="text-sm font-bold text-[color:var(--fulkro-title)]">
                Sin gaps detectados
              </p>
              <p className="text-xs text-fulkro-ink-500">
                C-002 cubre todas las cláusulas requeridas para el tipo y
                criticidad de este proveedor.
              </p>
            </div>
          ) : (
            filteredGaps.map((gap, i) => (
              <div
                key={`${gap.framework}-${i}`}
                className="flex flex-col gap-2 rounded-md border border-fulkro-ink-200 bg-white p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <FrameworkBadge framework={gap.framework} />
                  <Badge variant="outline">{gap.article}</Badge>
                  <SeverityBadge severity={gap.severity} />
                </div>
                <p className="text-sm text-fulkro-ink-700">{gap.description}</p>
                <div className="flex flex-col gap-1.5">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-fulkro-ink-400">
                    Cláusula sugerida añadir a C-002
                  </p>
                  <div className="flex items-start gap-2 rounded-md bg-fulkro-ink-50 p-2">
                    <pre className="flex-1 whitespace-pre-wrap break-words font-mono text-xs text-fulkro-ink-700">
                      {gap.suggested_clause}
                    </pre>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void onCopy(gap.suggested_clause)}
                      className="shrink-0"
                    >
                      <Copy size={12} strokeWidth={2.4} />
                    </Button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <SheetFooter className="mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cerrar
          </Button>
          <Button
            variant="primary"
            onClick={() => void onGenerateC002()}
            disabled={ph.generateC002.isPending || !provider}
          >
            {ph.generateC002.isPending ? (
              <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
            ) : null}
            Generar C-002 con gaps cubiertos
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
