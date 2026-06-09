"use client";

/**
 * McpProjectScopedPanel · Sub-atom 1.D.E.B v3.11.
 *
 * Panel principal de MCPs project-scoped. Renderiza el catálogo agrupado
 * por familia (vulnscan · cloud · config · phishing) con cards por tool +
 * launcher modal + active execution panel + historial.
 *
 * R23 sostener firmísimo · TODO project-scoped (directiva Marcos 20 May).
 * NO sidebar global · NO entrar a un MCP sin proyecto activo · contexto
 * sostener en todo momento.
 */
import { useState } from "react";
import {
  Bug,
  Cloud,
  FileSearch,
  Fingerprint,
  Shield,
  type LucideIcon,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  MCP_FAMILY_LABELS,
  type MCPExecution,
  type MCPFamily,
  type MCPToolSchema,
} from "@/lib/api/mcps";

import { useMCPsCatalog } from "@/hooks/useMCPs";

import { McpExecutionProgress } from "./McpExecutionProgress";
import { McpExecutionResult } from "./McpExecutionResult";
import { McpExecutionsHistory } from "./McpExecutionsHistory";
import { McpToolCard } from "./McpToolCard";
import { McpToolFormModal } from "./McpToolFormModal";

interface McpProjectScopedPanelProps {
  projectId: string;
}

const FAMILY_ORDER: MCPFamily[] = ["vulnscan", "cloud", "config", "phishing"];

const FAMILY_ICON: Record<MCPFamily, LucideIcon> = {
  vulnscan: Bug,
  cloud: Cloud,
  config: FileSearch,
  phishing: Fingerprint,
};

export function McpProjectScopedPanel({
  projectId,
}: McpProjectScopedPanelProps) {
  const catalogQuery = useMCPsCatalog();
  const [formTool, setFormTool] = useState<MCPToolSchema | null>(null);
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(
    null,
  );
  const [activeExecution, setActiveExecution] = useState<MCPExecution | null>(
    null,
  );
  const [tab, setTab] = useState<MCPFamily>("vulnscan");

  const handleSelectExecution = (e: MCPExecution) => {
    setActiveExecution(e);
    setActiveExecutionId(e.execution_id);
  };

  return (
    <div className="space-y-4" data-testid="mcp-project-scoped-panel">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield size={18} /> Pentest MCPs · acciones project-scoped
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            13 tools production-grade en 4 familias · escaneos accionables
            con reporte JSON descargable + auto-attach al IDMS folder{" "}
            <code>13_Informes_Tecnicos</code>. R23 sostener: todo
            project-scoped · NO sidebar global.
          </p>
        </CardHeader>
      </Card>

      {activeExecutionId && (
        <Card data-testid="mcp-active-execution-panel">
          <CardHeader>
            <CardTitle className="text-sm">Ejecución activa</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <McpExecutionProgress
              projectId={projectId}
              executionId={activeExecutionId}
              onFinished={() => {
                // No-op · el polling hook se encarga del refresh
              }}
            />
            {activeExecution &&
              (activeExecution.status === "completed" ||
                activeExecution.status === "failed") && (
                <McpExecutionResult
                  projectId={projectId}
                  execution={activeExecution}
                />
              )}
          </CardContent>
        </Card>
      )}

      {catalogQuery.isLoading ? (
        <CatalogSkeleton />
      ) : catalogQuery.isError ? (
        <Alert variant="danger">
          <AlertTitle>No se pudo cargar el catálogo MCP</AlertTitle>
          <AlertDescription>
            {catalogQuery.error instanceof Error
              ? catalogQuery.error.message
              : "Error desconocido"}
          </AlertDescription>
        </Alert>
      ) : (
        <Tabs value={tab} onValueChange={(v) => setTab(v as MCPFamily)}>
          <TabsList data-testid="mcp-family-tabs">
            {FAMILY_ORDER.map((f) => {
              const Icon = FAMILY_ICON[f];
              const count = catalogQuery.data?.families[f]?.length ?? 0;
              return (
                <TabsTrigger
                  key={f}
                  value={f}
                  data-testid={`mcp-family-tab-${f}`}
                >
                  <Icon size={14} className="mr-1.5" />
                  {MCP_FAMILY_LABELS[f]} ({count})
                </TabsTrigger>
              );
            })}
          </TabsList>
          {FAMILY_ORDER.map((f) => {
            const tools = catalogQuery.data?.families[f] ?? [];
            return (
              <TabsContent
                key={f}
                value={f}
                className="mt-4"
                data-testid={`mcp-family-content-${f}`}
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {tools.map((tool) => (
                    <McpToolCard
                      key={tool.tool_name}
                      tool={tool}
                      onLaunch={(t) => setFormTool(t)}
                    />
                  ))}
                </div>
              </TabsContent>
            );
          })}
        </Tabs>
      )}

      <McpToolFormModal
        projectId={projectId}
        tool={formTool}
        open={Boolean(formTool)}
        onOpenChange={(o) => !o && setFormTool(null)}
        onExecutionStarted={(execId) => {
          setActiveExecutionId(execId);
          setActiveExecution(null);
        }}
      />

      <McpExecutionsHistory
        projectId={projectId}
        onSelectExecution={handleSelectExecution}
      />
    </div>
  );
}

function CatalogSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-10 w-full" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
    </div>
  );
}
