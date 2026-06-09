"use client";

import * as React from "react";
import {
  AlertTriangle,
  Beaker,
  Bug,
  Cloud,
  Cpu,
  Eye,
  FileSearch,
  Fingerprint,
  Key,
  Lock,
  Network,
  ScanLine,
  Server,
  ShieldAlert,
  Smartphone,
  Wifi,
  type LucideIcon,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

import { KPICard } from "@/components/data/KPICard";
import { useMCPsStatus } from "@/hooks/useMCPs";
import type {
  MCPCategory,
  MCPState,
  MCPStatus,
} from "@/lib/api/mcps";
import { cn } from "@/lib/utils";

// ─── Iconos por categoria ─────────────────────────────────────────────

const CATEGORY_ICON: Record<MCPCategory, LucideIcon> = {
  scope: ShieldAlert,
  recon: Eye,
  vulnscan: ScanLine,
  webpentest: Bug,
  infra: Server,
  redteam: AlertTriangle,
  cloud: Cloud,
  config: FileSearch,
  phishing: Fingerprint,
  apisec: Network,
  mobile: Smartphone,
  wireless: Wifi,
  cracking: Key,
  sast: Beaker,
};

const STATE_LABEL: Record<MCPState, string> = {
  real: "Real",
  available: "Disponible",
  coming_soon: "Proximamente",
  blocked: "Bloqueado",
};

const STATE_VARIANT: Record<
  MCPState,
  "success" | "info" | "warning" | "danger"
> = {
  real: "success",
  available: "info",
  coming_soon: "warning",
  blocked: "danger",
};

// ─── MCPCard ──────────────────────────────────────────────────────────

interface MCPCardProps {
  mcp: MCPStatus;
}

function MCPCard({ mcp }: MCPCardProps) {
  const Icon = CATEGORY_ICON[mcp.category] ?? Cpu;
  return (
    <Card data-mcp-card data-mcp-state={mcp.state} className="h-full">
      <CardContent className="flex h-full flex-col gap-4 p-5 pt-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <span
              style={{
                backgroundColor: "var(--fulkro-surface-glass-strong)",
                color: "var(--fulkro-subtitle)",
              }}
              className="shrink-0 rounded-lg p-2.5"
            >
              <Icon size={20} strokeWidth={2.3} />
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-base font-bold text-[color:var(--fulkro-title)]">
                {mcp.label}
              </h3>
              <p className="truncate font-mono text-xs text-[color:var(--fulkro-muted)]">
                {mcp.name}
              </p>
            </div>
          </div>
          <Badge variant={STATE_VARIANT[mcp.state]} className="shrink-0">
            {STATE_LABEL[mcp.state]}
          </Badge>
        </div>

        <p className="flex-1 text-sm leading-relaxed text-[color:var(--fulkro-body)]">
          {mcp.description}
        </p>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-[var(--fulkro-surface-glass-border)] pt-3 text-xs text-[color:var(--fulkro-muted)]">
          {mcp.tools_count > 0 && (
            <span className="font-medium">
              {mcp.tools_count}{" "}
              {mcp.tools_count === 1 ? "herramienta" : "herramientas"}
            </span>
          )}
          {mcp.version && (
            <span className="font-mono">v{mcp.version}</span>
          )}
          {mcp.docker_image && (
            <span className="truncate font-mono" title={mcp.docker_image}>
              {mcp.docker_image}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Skeleton grid ────────────────────────────────────────────────────

function MCPGridSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <Card key={i} className="h-[180px]">
          <CardContent className="p-5 pt-5">
            <div className="flex items-start gap-3">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-20" />
              </div>
            </div>
            <Skeleton className="mt-4 h-3 w-full" />
            <Skeleton className="mt-2 h-3 w-3/4" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ─── Filtros ──────────────────────────────────────────────────────────

type FilterTab = "all" | MCPState;

const FILTER_TABS: { value: FilterTab; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "real", label: "Real" },
  { value: "available", label: "Disponible" },
  { value: "coming_soon", label: "Proximamente" },
  { value: "blocked", label: "Bloqueado" },
];

// ─── Grid principal ──────────────────────────────────────────────────

export function MCPStatusGrid() {
  const { data, isLoading, isError, error } = useMCPsStatus();
  const [filter, setFilter] = React.useState<FilterTab>("all");

  if (isLoading) return <MCPGridSkeleton />;

  if (isError) {
    return (
      <Alert variant="danger">
        <AlertTitle>No se pudo cargar el estado de los MCPs</AlertTitle>
        <AlertDescription>
          {(error as Error)?.message ?? "Error desconocido."}
        </AlertDescription>
      </Alert>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        icon={<Lock className="h-7 w-7" />}
        title="No hay MCPs registrados"
        description="El registry esta vacio. Despliega los servicios pentest desde docker-compose.pentest.yml."
      />
    );
  }

  const items =
    filter === "all"
      ? data.items
      : data.items.filter((m) => m.state === filter);

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <KPICard
          icon={Cpu}
          title="Total MCPs"
          value={String(data.total)}
          subtitle="Registrados"
        />
        <KPICard
          icon={ShieldAlert}
          title="Real"
          value={String(data.real_count)}
          subtitle="Integrados"
          rag={data.real_count > 0 ? "green" : "amber"}
        />
        <KPICard
          icon={Server}
          title="Disponibles"
          value={String(data.available_count)}
          subtitle="Dockerizados"
          rag="amber"
        />
        <KPICard
          icon={ScanLine}
          title="Proximamente"
          value={String(data.coming_soon_count)}
          subtitle="Pendientes"
        />
      </div>

      {/* Tabs */}
      <Tabs
        value={filter}
        onValueChange={(v) => setFilter(v as FilterTab)}
        className="w-full"
      >
        <TabsList>
          {FILTER_TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value={filter} className="mt-6">
          {items.length === 0 ? (
            <EmptyState
              title="Sin MCPs en este estado"
              description={`No hay servidores con estado "${
                STATE_LABEL[filter as MCPState] ?? filter
              }".`}
            />
          ) : (
            <div
              className={cn(
                "grid grid-cols-1 gap-4",
                "sm:grid-cols-2",
                "lg:grid-cols-3 xl:grid-cols-4",
              )}
            >
              {items.map((mcp) => (
                <MCPCard key={mcp.name} mcp={mcp} />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
