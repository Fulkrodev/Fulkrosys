"use client";

import * as React from "react";
import { Cloud, Key, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  useAWSCredentials,
  useOAuthInit,
  usePortalConnectors,
  useSyncConnector,
} from "@/hooks/useOnboardingClient";
import type { PortalConnectorView } from "@/lib/client-onboarding/api";

export interface ConnectorsClientViewProps {
  projectId: string;
  oauthRedirectPath?: string;
}

const PROVIDERS_META: Record<
  string,
  { label: string; description: string; auth: "oauth" | "iam" }
> = {
  github: {
    label: "GitHub",
    description: "Repositorios · usuarios · organizaciones",
    auth: "oauth",
  },
  microsoft: {
    label: "Microsoft 365",
    description: "Tenant Azure AD · usuarios · grupos",
    auth: "oauth",
  },
  azure: {
    label: "Azure",
    description: "Recursos cloud · ARM · suscripciones",
    auth: "oauth",
  },
  aws: {
    label: "AWS",
    description: "Cuentas IAM · recursos cloud",
    auth: "iam",
  },
  google: {
    label: "Google Workspace",
    description: "Admin SDK · usuarios · grupos",
    auth: "oauth",
  },
  base: {
    label: "Base",
    description: "Conector configurable",
    auth: "oauth",
  },
};

const STATUS_VARIANT: Record<string, "secondary" | "info" | "success" | "warning" | "danger"> = {
  not_connected: "secondary",
  pending_oauth: "info",
  configured: "success",
  sync_triggered: "info",
  error: "danger",
};

const REGIONS = [
  "us-east-1",
  "us-west-2",
  "eu-west-1",
  "eu-central-1",
  "eu-south-2",
  "ap-southeast-1",
];

export function ConnectorsClientView({
  projectId,
  oauthRedirectPath = "/client-portal/onboarding/oauth-callback",
}: ConnectorsClientViewProps) {
  const { data: connectors = [], isLoading } = usePortalConnectors(projectId);
  const oauthInitMutation = useOAuthInit(projectId);
  const awsMutation = useAWSCredentials(projectId);
  const syncMutation = useSyncConnector(projectId);

  const [awsOpen, setAwsOpen] = React.useState(false);
  const [warningOpen, setWarningOpen] = React.useState<string | null>(null);
  const [awsForm, setAwsForm] = React.useState({
    access_key_id: "",
    secret_access_key: "",
    region: "eu-west-1",
  });

  const handleConnect = (provider: string) => {
    if (provider === "aws") {
      setAwsOpen(true);
      return;
    }
    setWarningOpen(provider);
  };

  const confirmConnect = (provider: string) => {
    setWarningOpen(null);
    const redirectUri = `${
      typeof window !== "undefined" ? window.location.origin : ""
    }${oauthRedirectPath}?project_id=${projectId}&connector=${provider}`;

    oauthInitMutation.mutate(
      { connectorType: provider, redirectUri },
      {
        onSuccess: (res) => {
          window.location.href = res.authorize_url;
        },
        onError: (err) => {
          toast.error(`No se pudo iniciar OAuth: ${String(err)}`);
        },
      },
    );
  };

  const handleSync = (provider: string) => {
    syncMutation.mutate(provider, {
      onSuccess: () => toast.success(`${provider} sincronizado`),
      onError: () => toast.error(`Error sincronizando ${provider}`),
    });
  };

  const handleAWSSubmit = () => {
    if (!awsForm.access_key_id || !awsForm.secret_access_key) {
      toast.warning("Pega access key y secret antes de conectar");
      return;
    }
    awsMutation.mutate(awsForm, {
      onSuccess: (res) => {
        toast.success(`AWS conectado · cuenta ${res.account_id ?? "?"}`);
        setAwsOpen(false);
        setAwsForm({ access_key_id: "", secret_access_key: "", region: "eu-west-1" });
      },
      onError: (err) => toast.error(`AWS validation falló: ${String(err)}`),
    });
  };

  const allProviders = Object.keys(PROVIDERS_META);
  const connectorsMap = new Map(connectors.map((c) => [c.connector_type, c]));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Cloud size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Conecta tu workspace
            <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
              ({connectors.filter((c) => c.connected).length}/{allProviders.length})
            </span>
          </h3>
          <TooltipENS term="oauth_real" />
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-fulkro-ink-500">Cargando connectors…</p>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {allProviders.map((p) => {
            const meta = PROVIDERS_META[p];
            const cfg = connectorsMap.get(p) as PortalConnectorView | undefined;
            const status = cfg?.status ?? "not_connected";
            return (
              <Card key={p}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-sm">{meta.label}</CardTitle>
                    <Badge variant={STATUS_VARIANT[status] ?? "outline"}>{status}</Badge>
                  </div>
                  <CardDescription className="line-clamp-2 text-xs">
                    {meta.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-xs">
                  <div className="flex items-center gap-1 text-fulkro-ink-500">
                    {meta.auth === "iam" ? (
                      <>
                        <Key size={12} /> IAM access key
                      </>
                    ) : (
                      <>
                        <ShieldCheck size={12} /> OAuth seguro
                      </>
                    )}
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
                  {cfg?.connected ? (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleSync(p)}
                        disabled={syncMutation.isPending}
                        className="flex-1"
                      >
                        <RefreshCw className="mr-1 size-3" />
                        Sincronizar
                      </Button>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      variant="primary"
                      onClick={() => handleConnect(p)}
                      disabled={oauthInitMutation.isPending}
                      className="w-full"
                    >
                      {oauthInitMutation.isPending && oauthInitMutation.variables?.connectorType === p ? (
                        <>
                          <Loader2 className="mr-1 size-3 animate-spin" />
                          Iniciando…
                        </>
                      ) : (
                        `Conectar ${meta.label}`
                      )}
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Dialog
        open={warningOpen !== null}
        onOpenChange={(open) => {
          if (!open) setWarningOpen(null);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Conectar {warningOpen ? PROVIDERS_META[warningOpen]?.label : ""}</DialogTitle>
            <DialogDescription>
              Te llevamos al login de {warningOpen ? PROVIDERS_META[warningOpen]?.label : ""} para que autorices.
              FULKRO recibirá un token revocable que cifra inmediatamente.
              Tus credenciales nunca pasan por nosotros · puedes desconectar cuando quieras.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setWarningOpen(null)}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={() => warningOpen && confirmConnect(warningOpen)}
            >
              Continuar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={awsOpen} onOpenChange={setAwsOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Conectar AWS · IAM access key</DialogTitle>
            <DialogDescription>
              AWS no usa OAuth estándar. Pega tu IAM access key con permisos
              de lectura · validamos via STS GetCallerIdentity y cifrarmos
              inmediatamente.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium">Access Key ID</label>
              <Input
                value={awsForm.access_key_id}
                onChange={(e) =>
                  setAwsForm({ ...awsForm, access_key_id: e.target.value })
                }
                placeholder="AKIAXXXXXXXXXXXXXXXX"
                autoComplete="off"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Secret Access Key</label>
              <Input
                type="password"
                value={awsForm.secret_access_key}
                onChange={(e) =>
                  setAwsForm({ ...awsForm, secret_access_key: e.target.value })
                }
                autoComplete="off"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Región</label>
              <Select
                value={awsForm.region}
                onValueChange={(v) => setAwsForm({ ...awsForm, region: v })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {REGIONS.map((r) => (
                    <SelectItem key={r} value={r}>{r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAwsOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={handleAWSSubmit}
              disabled={awsMutation.isPending}
            >
              {awsMutation.isPending ? "Validando…" : "Validar y conectar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
