"use client";

/**
 * ProvidersGrid real · M14 wired (SAN-E v3.MB-3.3).
 *
 * Sustituye stub `EmptyStateUpcoming` con UI completa cableada al backend
 * M14 providers/c002 (commit MB-3.B 6800b5f · 7 endpoints).
 *
 * 3 secciones:
 * A. Header · stats inline + filters + btn add
 * B. Grid responsive 2-4 cols · ProviderCard per provider
 * C. AddProviderModal + C002GapsPanel state
 */
import * as React from "react";
import { Plus, Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useProviders } from "@/hooks/useProviders";
import type {
  Criticality,
  Provider,
  ProviderType,
} from "@/lib/admin-providers/api";

import { AddProviderModal } from "./AddProviderModal";
import { C002GapsPanel } from "./C002GapsPanel";
import { ProviderCard } from "./ProviderCard";

interface StatChipProps {
  label: string;
  value: number;
  variant?: "default" | "success" | "warning" | "danger";
}

function StatChip({ label, value, variant = "default" }: StatChipProps) {
  // Sub-atom Sesión 3B-2B.2 Phase A.3.X · WCAG color-contrast fix.
  // text-fulkro-{name} (-500 shade) on white parent bg gives ~3.87:1 (FAIL AA).
  // -700 shades give 7-10:1 (AAA). Border alpha /40 kept (visual cue · text
  // is the accessibility-critical concern).
  const accent = {
    default: "border-fulkro-ink-200 text-fulkro-ink-700",
    success: "border-fulkro-success/40 text-fulkro-success-700",
    warning: "border-fulkro-warning/40 text-fulkro-warning-700",
    danger: "border-fulkro-danger/40 text-fulkro-danger-700",
  }[variant];
  return (
    <div
      className={`flex flex-col gap-0.5 rounded-md border px-3 py-2 ${accent}`}
    >
      <span className="text-[10px] uppercase tracking-wide text-fulkro-ink-600">
        {label}
      </span>
      <span className="text-lg font-bold tabular-nums">{value}</span>
    </div>
  );
}

export function ProvidersGrid({ projectId }: { projectId: string }) {
  const ph = useProviders(projectId);
  const [typeFilter, setTypeFilter] = React.useState<ProviderType | "todos">(
    "todos",
  );
  const [critFilter, setCritFilter] = React.useState<Criticality | "todas">(
    "todas",
  );
  const [search, setSearch] = React.useState("");

  const [addOpen, setAddOpen] = React.useState(false);
  const [gapsOpenFor, setGapsOpenFor] = React.useState<Provider | null>(null);

  const providers = ph.list.data?.providers ?? [];
  const counts = ph.list.data?.counts;

  const filtered = React.useMemo(
    () =>
      providers.filter((p) => {
        if (typeFilter !== "todos" && p.type !== typeFilter) return false;
        if (critFilter !== "todas" && p.criticality !== critFilter) return false;
        if (
          search &&
          !p.name.toLowerCase().includes(search.toLowerCase()) &&
          !p.scope.toLowerCase().includes(search.toLowerCase())
        )
          return false;
        return true;
      }),
    [providers, typeFilter, critFilter, search],
  );

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8">
      {/* A · Header */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h1 className="text-2xl font-bold text-[color:var(--fulkro-title)]">
              Proveedores del proyecto
            </h1>
            <p className="text-sm text-fulkro-ink-500">
              Gestión proveedores críticos + cláusulas C-002 cross-compliance{" "}
              <TooltipENS
                text="Cuando un proveedor trata datos personales o información sensible para ENS, debes documentarlo (C-002) y verificar que cumple. FULKRO detecta gaps automáticamente y te dice qué falta."
                iconSize={13}
              />
            </p>
          </div>
          <Button variant="primary" onClick={() => setAddOpen(true)}>
            <Plus size={14} strokeWidth={2.4} className="mr-1" />
            Añadir proveedor
          </Button>
        </div>

        {/* Stats */}
        {counts ? (
          <div className="flex flex-wrap gap-3">
            <StatChip label="Total" value={counts.total} />
            <StatChip
              label="C-002 firmados"
              value={counts.firmados}
              variant="success"
            />
            <StatChip
              label="Con gaps"
              value={counts.con_gaps}
              variant="warning"
            />
            <StatChip
              label="Críticos"
              value={counts.critico}
              variant="danger"
            />
            <StatChip label="Alto" value={counts.alto} variant="warning" />
          </div>
        ) : null}

        {/* Filters */}
        <Card>
          <CardContent className="flex flex-wrap items-end gap-3 pt-6">
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs">Tipo</Label>
              <Select
                value={typeFilter}
                onValueChange={(v) =>
                  setTypeFilter(v as ProviderType | "todos")
                }
              >
                <SelectTrigger
                  className="w-[180px]"
                  aria-label="Filtrar por tipo de proveedor"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos</SelectItem>
                  <SelectItem value="cloud">Cloud</SelectItem>
                  <SelectItem value="saas">SaaS</SelectItem>
                  <SelectItem value="on-prem">On-Prem</SelectItem>
                  <SelectItem value="staffing">Staffing</SelectItem>
                  <SelectItem value="hardware">Hardware</SelectItem>
                  <SelectItem value="consultoria">Consultoría</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs">Criticidad</Label>
              <Select
                value={critFilter}
                onValueChange={(v) =>
                  setCritFilter(v as Criticality | "todas")
                }
              >
                <SelectTrigger
                  className="w-[180px]"
                  aria-label="Filtrar por criticidad del proveedor"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todas">Todas</SelectItem>
                  <SelectItem value="CRITICO">Crítico</SelectItem>
                  <SelectItem value="ALTO">Alto</SelectItem>
                  <SelectItem value="MEDIO">Medio</SelectItem>
                  <SelectItem value="BAJO">Bajo</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex min-w-[220px] flex-1 flex-col gap-1.5">
              <Label className="text-xs">Búsqueda</Label>
              <div className="relative">
                <Search
                  size={14}
                  strokeWidth={2.4}
                  className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fulkro-ink-600"
                />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Buscar por nombre o scope…"
                  className="pl-8"
                />
              </div>
            </div>
            <Badge variant="outline" className="ml-auto">
              {filtered.length}{" "}
              {filtered.length === 1 ? "proveedor" : "proveedores"}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* B · Grid cards */}
      {ph.list.isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-56" />
          ))}
        </div>
      ) : providers.length === 0 ? (
        <Card>
          <CardContent className="py-10">
            <EmptyState
              title="Sin proveedores registrados"
              description="Añade el primer proveedor para empezar a gestionar C-002 y cross-compliance."
              action={{
                label: "Añadir primer proveedor",
                onClick: () => setAddOpen(true),
                variant: "primary",
              }}
            />
          </CardContent>
        </Card>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-10">
            <EmptyState
              title="Sin coincidencias"
              description="Ajusta los filtros para ver proveedores."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((provider) => (
            <ProviderCard
              key={provider.id}
              projectId={projectId}
              provider={provider}
              onShowGaps={(p) => setGapsOpenFor(p)}
            />
          ))}
        </div>
      )}

      {/* C · Modal + Drawer */}
      <AddProviderModal
        projectId={projectId}
        open={addOpen}
        onOpenChange={setAddOpen}
      />
      <C002GapsPanel
        projectId={projectId}
        provider={gapsOpenFor}
        open={gapsOpenFor !== null}
        onOpenChange={(v) => {
          if (!v) setGapsOpenFor(null);
        }}
      />
    </div>
  );
}
