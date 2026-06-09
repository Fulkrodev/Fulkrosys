"use client";

/**
 * McpToolCard · Sub-atom 1.D.E.B v3.11.
 *
 * Card individual por MCP tool · muestra icon · label · descripción ·
 * risk level · estimated duration · botón "Iniciar escaneo" que abre
 * el McpToolFormModal con los parámetros específicos del tool.
 *
 * Project-scoped · NO sidebar global (R23 sostener firmísimo).
 */
import {
  Beaker,
  Bug,
  Cloud,
  FileSearch,
  Fingerprint,
  Play,
  Server,
  Timer,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  MCP_RISK_LABELS,
  MCP_RISK_VARIANTS,
  type MCPFamily,
  type MCPToolSchema,
} from "@/lib/api/mcps";

interface McpToolCardProps {
  tool: MCPToolSchema;
  onLaunch: (tool: MCPToolSchema) => void;
  disabled?: boolean;
}

const FAMILY_ICON: Record<MCPFamily, LucideIcon> = {
  vulnscan: Bug,
  cloud: Cloud,
  config: FileSearch,
  phishing: Fingerprint,
};

const TOOL_ICON_OVERRIDE: Record<string, LucideIcon> = {
  trivy_scan: Server,
  grype_sbom_scan: Beaker,
};

export function McpToolCard({ tool, onLaunch, disabled }: McpToolCardProps) {
  const Icon = TOOL_ICON_OVERRIDE[tool.tool_name] ?? FAMILY_ICON[tool.mcp_name];
  const minutes = Math.max(1, Math.round(tool.estimated_duration_s / 60));
  return (
    <Card
      className="h-full"
      data-testid={`mcp-tool-card-${tool.tool_name}`}
    >
      <CardContent className="flex h-full flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="shrink-0 rounded-lg bg-fulkro-surface-glass-strong p-2 text-fulkro-subtitle">
              <Icon size={18} strokeWidth={2.2} />
            </span>
            <div className="min-w-0">
              <h3 className="truncate text-sm font-bold text-fulkro-title">
                {tool.label}
              </h3>
              <p className="truncate font-mono text-[10px] text-muted-foreground">
                {tool.mcp_name}/{tool.tool_name}
              </p>
            </div>
          </div>
          <Badge variant={MCP_RISK_VARIANTS[tool.risk_level]}>
            {MCP_RISK_LABELS[tool.risk_level]}
          </Badge>
        </div>

        <p className="flex-1 text-xs leading-relaxed text-fulkro-body">
          {tool.description}
        </p>

        <div className="flex items-center justify-between gap-2 border-t border-fulkro-surface-glass-border pt-2">
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <Timer size={12} />
            <span>~{minutes} min</span>
          </div>
          <Button
            size="sm"
            onClick={() => onLaunch(tool)}
            disabled={disabled}
            data-testid={`mcp-tool-launch-${tool.tool_name}`}
          >
            <Play size={12} className="mr-1" />
            Iniciar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
