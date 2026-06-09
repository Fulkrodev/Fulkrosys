"use client";

/**
 * ProviderCard · per provider en grid (SAN-E v3.MB-3.3).
 *
 * Card visual con avatar/icono según type · criticality badge ·
 * C-002 status row · gaps alert · DropdownMenu 4 acciones.
 */
import * as React from "react";
import {
  AlertTriangle,
  Boxes,
  Cloud,
  HardDrive,
  Loader2,
  MoreVertical,
  Server,
  ShieldCheck,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useProviders } from "@/hooks/useProviders";
import type {
  C002Status,
  Criticality,
  Provider,
  ProviderType,
} from "@/lib/admin-providers/api";

const TYPE_LABELS: Record<ProviderType, string> = {
  cloud: "Cloud",
  saas: "SaaS",
  "on-prem": "On-Prem",
  staffing: "Staffing",
  hardware: "Hardware",
  consultoria: "Consultoría",
};

function TypeIcon({ type }: { type: ProviderType }) {
  const Icon = (
    {
      cloud: Cloud,
      saas: Boxes,
      "on-prem": Server,
      staffing: Users,
      hardware: HardDrive,
      consultoria: Users,
    } as const
  )[type];
  return <Icon size={18} strokeWidth={2.4} />;
}

function CriticalityBadge({ value }: { value: Criticality }) {
  const variant: "danger" | "warning" | "info" | "secondary" = (
    {
      CRITICO: "danger",
      ALTO: "warning",
      MEDIO: "info",
      BAJO: "secondary",
    } as const
  )[value];
  return <Badge variant={variant}>{value}</Badge>;
}

function C002Badge({ status }: { status: C002Status }) {
  const cfg: Record<
    C002Status,
    { variant: "success" | "warning" | "secondary" | "danger"; label: string }
  > = {
    firmado: { variant: "success", label: "Firmado" },
    pendiente: { variant: "warning", label: "Pendiente" },
    no_aplica: { variant: "secondary", label: "No aplica" },
    revocado: { variant: "danger", label: "Revocado" },
  };
  const c = cfg[status];
  return <Badge variant={c.variant}>{c.label}</Badge>;
}

function relativeDate(s: string | null): string {
  if (!s) return "Nunca";
  const d = new Date(s);
  const days = Math.floor(
    (Date.now() - d.getTime()) / (1000 * 60 * 60 * 24),
  );
  if (days < 1) return "Hoy";
  if (days < 7) return `Hace ${days}d`;
  if (days < 30) return `Hace ${Math.floor(days / 7)}sem`;
  if (days < 365) return `Hace ${Math.floor(days / 30)}m`;
  return `Hace ${Math.floor(days / 365)}a`;
}

interface ProviderCardProps {
  projectId: string;
  provider: Provider;
  onShowGaps: (provider: Provider) => void;
}

export function ProviderCard({
  projectId,
  provider,
  onShowGaps,
}: ProviderCardProps) {
  const ph = useProviders(projectId);
  const [confirmDelete, setConfirmDelete] = React.useState(false);

  const onMarkReviewed = async () => {
    try {
      await ph.markReviewed.mutateAsync(provider.id);
      toast.success(`${provider.name} marcado como revisado`);
    } catch {
      toast.error("Error al marcar revisado");
    }
  };

  const onGenerateC002 = async () => {
    try {
      await ph.generateC002.mutateAsync(provider.id);
      toast.success(`C-002 generado para ${provider.name}`);
    } catch {
      toast.error("Error al generar C-002");
    }
  };

  const onDelete = async () => {
    try {
      await ph.remove.mutateAsync(provider.id);
      toast.success(`${provider.name} eliminado`);
      setConfirmDelete(false);
    } catch {
      toast.error("Error al eliminar proveedor");
    }
  };

  return (
    <>
      <Card className="flex h-full flex-col">
        <CardContent className="flex flex-1 flex-col gap-3 pt-5">
          {/* Header */}
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-fulkro-ink-50 text-fulkro-ink-700">
              <TypeIcon type={provider.type} />
            </div>
            <div className="flex flex-1 flex-col gap-1">
              <h3 className="text-sm font-bold text-[color:var(--fulkro-title)]">
                {provider.name}
              </h3>
              <div className="flex flex-wrap gap-1">
                <Badge variant="outline" className="text-[10px]">
                  {TYPE_LABELS[provider.type]}
                </Badge>
                <CriticalityBadge value={provider.criticality} />
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreVertical size={14} strokeWidth={2.4} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => void onMarkReviewed()}
                  disabled={ph.markReviewed.isPending}
                >
                  <ShieldCheck size={14} strokeWidth={2.4} className="mr-2" />
                  Marcar revisado
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => void onGenerateC002()}
                  disabled={ph.generateC002.isPending}
                >
                  Generar / regenerar C-002
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-fulkro-danger"
                  onClick={() => setConfirmDelete(true)}
                >
                  Eliminar proveedor
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          {/* Scope */}
          <p
            className="line-clamp-2 text-xs text-fulkro-ink-500"
            title={provider.scope}
          >
            {provider.scope}
          </p>

          {/* C002 status row */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-fulkro-ink-50 px-3 py-2">
            <div className="flex items-center gap-1.5 text-xs">
              <span className="font-bold text-[color:var(--fulkro-title)]">
                C-002
              </span>
              <TooltipENS
                text="Cláusula 002 · contrato encargado del tratamiento del proveedor (RGPD Art. 28 / ENS Art. 18). Documenta qué datos trata, cómo, durante cuánto tiempo y con qué garantías."
                iconSize={11}
              />
            </div>
            <div className="flex items-center gap-2">
              <C002Badge status={provider.c002_status} />
              <span className="text-[10px] text-fulkro-ink-600">
                {relativeDate(provider.last_reviewed_at)}
              </span>
            </div>
          </div>

          {/* Gaps alert */}
          {provider.gaps_count > 0 ? (
            <button
              type="button"
              onClick={() => onShowGaps(provider)}
              className="flex items-center justify-between gap-2 rounded-md border border-fulkro-warning/30 bg-fulkro-warning/5 px-3 py-2 text-left transition-colors hover:bg-fulkro-warning/10"
            >
              <span className="flex items-center gap-1.5 text-xs font-medium text-fulkro-warning">
                <AlertTriangle size={12} strokeWidth={2.4} />
                {provider.gaps_count}{" "}
                {provider.gaps_count === 1 ? "gap" : "gaps"} cross-compliance
              </span>
              <span className="text-[10px] font-bold text-fulkro-warning">
                Ver gaps →
              </span>
            </button>
          ) : provider.c002_status === "firmado" ? (
            <div className="flex items-center gap-1.5 text-xs text-fulkro-success">
              <ShieldCheck size={12} strokeWidth={2.4} />
              C-002 firmado · sin gaps detectados
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* Confirm delete */}
      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar {provider.name}</DialogTitle>
            <DialogDescription>
              El proveedor se marcará como eliminado (soft delete). Las
              evidencias C-002 vinculadas se preservan pero quedan
              desconectadas.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDelete(false)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={() => void onDelete()}
              disabled={ph.remove.isPending}
            >
              {ph.remove.isPending ? (
                <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
              ) : null}
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
