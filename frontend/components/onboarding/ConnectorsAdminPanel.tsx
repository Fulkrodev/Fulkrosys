"use client";

import * as React from "react";
import { Cloud, RefreshCw, Server, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  useProjectConnectors,
  useValidateConnector,
} from "@/hooks/useOnboardingAdmin";
import type { ConnectorAdminStatus } from "@/lib/admin-onboarding/api";

export interface ConnectorsAdminPanelProps {
  projectId: string;
}

const PROVIDER_META: Record<string, { label: string; description: string; auth: string }> = {
  github: {
    label: "GitHub",
    description: "Repositorios · usuarios · permisos · branches",
    auth: "OAuth Apps",
  },
  microsoft: {
    label: "Microsoft 365",
    description: "Tenant Azure AD · usuarios · grupos · directorio",
    auth: "OAuth + PKCE",
  },
  azure: {
    label: "Azure",
    description: "Recursos cloud · ARM API · suscripciones",
    auth: "OAuth + PKCE",
  },
  aws: {
    label: "AWS",
    description: "Cuentas IAM · recursos · regiones",
    auth: "IAM access key",
  },
  google: {
    label: "Google Workspace",
    description: "Admin SDK · usuarios · grupos",
    auth: "OAuth + PKCE",
  },
  base: {
    label: "Base custom",
    description: "Conector configurable por el operador",
    auth: "OAuth + PKCE",
  },
};

const STATUS_VARIANT: Record<string, "secondary" | "info" | "success" | "warning" | "danger"> = {
  not_connected: "secondary",
  configured: "success",
  pending_oauth: "info",
  sync_triggered: "info",
  error: "danger",
};

export function ConnectorsAdminPanel({ projectId }: ConnectorsAdminPanelProps) {
  const { data: connectors = [], isLoading } = useProjectConnectors(projectId);
  const validateMutation = useValidateConnector(projectId);

  const handleValidate = (provider: string) => {
    validateMutation.mutate(provider, {
      onSuccess: (res) => {
        if (res.valid) toast.success(`${provider}: credenciales válidas`);
        else toast.error(`${provider}: ${res.error ?? "validación falló"}`);
      },
      onError: () => toast.error(`${provider}: error de red`),
    });
  };

  // Construye listado completo · 6 providers · merge con configured backend
  const configuredMap = new Map(connectors.map((c) => [c.provider, c]));
  const allProviders = Object.keys(PROVIDER_META);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Cloud size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Connectors cloud
            <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
              ({connectors.length}/{allProviders.length} configurados)
            </span>
          </h3>
          <TooltipENS term="oauth_real" />
        </div>
        <p className="text-xs text-fulkro-ink-500">
          El cliente conecta cada workspace desde su portal · admin solo monitor
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {allProviders.map((p) => {
          const meta = PROVIDER_META[p];
          const cfg = configuredMap.get(p) as ConnectorAdminStatus | undefined;
          const status = cfg?.status ?? "not_connected";
          return (
            <Card key={p}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Server size={14} />
                    {meta.label}
                  </CardTitle>
                  <Badge variant={STATUS_VARIANT[status] ?? "outline"}>{status}</Badge>
                </div>
                <CardDescription className="line-clamp-2 text-xs">
                  {meta.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                <div className="flex items-center gap-1 text-fulkro-ink-500">
                  <ShieldCheck size={12} />
                  Auth: {meta.auth}
                </div>
                {cfg?.last_discovery_at ? (
                  <div className="text-fulkro-ink-500">
                    Última sync:{" "}
                    {new Date(cfg.last_discovery_at).toLocaleString("es-ES", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </div>
                ) : null}
                {cfg?.scopes ? (
                  <div className="font-mono text-fulkro-ink-500" title={cfg.scopes}>
                    Scopes: {cfg.scopes.length > 50 ? `${cfg.scopes.slice(0, 47)}…` : cfg.scopes}
                  </div>
                ) : null}
                {cfg ? (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleValidate(p)}
                    disabled={validateMutation.isPending}
                    className="w-full"
                  >
                    <RefreshCw className="mr-1 size-3" />
                    Validar credenciales
                  </Button>
                ) : (
                  <p className="rounded bg-fulkro-canvas p-2 text-fulkro-ink-500">
                    Cliente debe conectar desde portal
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {isLoading ? (
        <p className="text-xs text-fulkro-ink-500">Cargando estado conectores…</p>
      ) : null}
    </div>
  );
}
