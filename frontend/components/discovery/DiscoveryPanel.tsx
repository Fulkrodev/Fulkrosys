"use client";

import * as React from "react";
import {
  Activity,
  AlertTriangle,
  Bug,
  Database,
  GitBranch,
  Layers,
  Loader2,
  PlayCircle,
  ScrollText,
  Server,
  Settings,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import {
  useAlertsSummary,
  useAssetsSummary,
  useConfigsSummary,
  useCreateDiscoveryRun,
  useDataStoresSummary,
  useDiscoveryRuns,
  useDiscoverySummary,
  useIdentitiesSummary,
  useVulnsSummary,
} from "@/hooks/useDiscovery";

import { AssetsTab } from "./AssetsTab";
import { ConfigTab } from "./ConfigTab";
import { ConsolidatedTab } from "./ConsolidatedTab";
import { ContinuityTab } from "./ContinuityTab";
import { DataFlowTab } from "./DataFlowTab";
import { DataTab } from "./DataTab";
import { IdentityTab } from "./IdentityTab";
import { LogsTab } from "./LogsTab";
import { VulnsTab } from "./VulnsTab";

export interface DiscoveryPanelProps {
  projectId: string;
}

const TAB_DEFS = [
  { id: "consolidated", label: "Consolidado", icon: Layers },
  { id: "assets", label: "Activos", icon: Server },
  { id: "identity", label: "Identidad", icon: Users },
  { id: "data", label: "Datos", icon: Database },
  { id: "vulns", label: "Vulns", icon: Bug },
  { id: "config", label: "Config", icon: Settings },
  { id: "dataflow", label: "Flujos", icon: GitBranch },
  { id: "continuity", label: "Continuidad", icon: Activity },
  { id: "logs", label: "Logs", icon: ScrollText },
] as const;

type TabId = (typeof TAB_DEFS)[number]["id"];

function formatRelative(iso: string | null): string {
  if (!iso) return "nunca";
  const dt = new Date(iso);
  const diffMs = Date.now() - dt.getTime();
  const min = Math.floor(diffMs / 60_000);
  if (min < 1) return "ahora";
  if (min < 60) return `${min} min`;
  const hours = Math.floor(min / 60);
  if (hours < 24) return `hace ${hours}h`;
  const days = Math.floor(hours / 24);
  return `hace ${days}d`;
}

export function DiscoveryPanel({ projectId }: DiscoveryPanelProps) {
  const [activeTab, setActiveTab] = React.useState<TabId>("assets");

  const { data: summary } = useDiscoverySummary(projectId);
  const { data: runs = [] } = useDiscoveryRuns(projectId);
  const { data: assetsSummary } = useAssetsSummary(projectId);
  const { data: identitiesSummary } = useIdentitiesSummary(projectId);
  const { data: dataStoresSummary } = useDataStoresSummary(projectId);
  const { data: vulnsSummary } = useVulnsSummary(projectId);
  const { data: configsSummary } = useConfigsSummary(projectId);
  const { data: alertsSummary } = useAlertsSummary(projectId);

  const createRun = useCreateDiscoveryRun(projectId);

  const lastRun = runs[0] ?? null;
  const isRunning = lastRun?.status === "running" || lastRun?.status === "pending";

  const handleFullScan = () => {
    createRun.mutate(
      { execute: true, triggered_by: "manual" },
      {
        onSuccess: (run) => {
          toast.success(`Scan iniciado · run ${run.id.slice(0, 8)}`);
        },
        onError: () => {
          toast.error("Error al iniciar scan");
        },
      },
    );
  };

  const tabCount = (id: TabId): number | null => {
    switch (id) {
      case "assets":
        return assetsSummary?.total ?? null;
      case "identity":
        return identitiesSummary?.total ?? null;
      case "data":
        return dataStoresSummary?.total ?? null;
      case "vulns":
        return vulnsSummary?.total ?? null;
      case "config":
        return configsSummary?.total ?? null;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-fulkro-primary-700">
              Descubrimiento automático
            </h1>
            <p className="text-sm text-fulkro-ink-500">
              Inventario · vulnerabilidades · flujos · continuidad y logging del sistema.{" "}
              <TooltipENS term="DICAT" />
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              Último scan: {formatRelative(summary?.last_run_at ?? null)}
            </Badge>
            <Button
              type="button"
              onClick={handleFullScan}
              disabled={isRunning || createRun.isPending}
            >
              {isRunning || createRun.isPending ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  Scan en curso…
                </>
              ) : (
                <>
                  <PlayCircle className="mr-2 size-4" />
                  Ejecutar scan completo
                </>
              )}
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="secondary">
            <Server className="mr-1 size-3" /> {summary?.assets_total ?? 0} activos
          </Badge>
          <Badge variant="secondary">
            <Users className="mr-1 size-3" /> {summary?.identities_total ?? 0} identidades
          </Badge>
          <Badge variant="secondary">
            <Database className="mr-1 size-3" /> {summary?.data_stores_total ?? 0} datos
          </Badge>
          <Badge variant="secondary">
            <Bug className="mr-1 size-3" /> {summary?.vulnerabilities_total ?? 0} vulns
          </Badge>
          <Badge variant="secondary">
            <Settings className="mr-1 size-3" /> {summary?.configurations_total ?? 0} checks
          </Badge>
          <Badge variant="secondary">
            <GitBranch className="mr-1 size-3" /> {summary?.dataflows_total ?? 0} flujos
          </Badge>
          {alertsSummary && alertsSummary.total > 0 ? (
            <Badge variant="warning">
              <AlertTriangle className="mr-1 size-3" /> {alertsSummary.total} alertas
            </Badge>
          ) : null}
        </div>
      </header>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 bg-transparent p-0">
          {TAB_DEFS.map((tab) => {
            const Icon = tab.icon;
            const count = tabCount(tab.id);
            return (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                className={cn(
                  "data-[state=active]:bg-fulkro-primary-700 data-[state=active]:text-white",
                  "border border-fulkro-ink-100 bg-white",
                )}
              >
                <Icon className="mr-1.5 size-3.5" />
                {tab.label}
                {count !== null ? (
                  <span className="ml-1.5 rounded-full bg-fulkro-canvas px-1.5 py-0.5 text-[10px] font-mono text-fulkro-ink-700">
                    {count}
                  </span>
                ) : null}
              </TabsTrigger>
            );
          })}
        </TabsList>

        <TabsContent value="consolidated" className="mt-6">
          <ConsolidatedTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="assets" className="mt-6">
          <AssetsTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="identity" className="mt-6">
          <IdentityTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="data" className="mt-6">
          <DataTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="vulns" className="mt-6">
          <VulnsTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="config" className="mt-6">
          <ConfigTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="dataflow" className="mt-6">
          <DataFlowTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="continuity" className="mt-6">
          <ContinuityTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="logs" className="mt-6">
          <LogsTab projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
