"use client";

/**
 * /client-portal/cloud-connections · Sesión 3B-2B.8 Phase 1C steady-state mgmt.
 *
 * Vista daily-mgmt cliente · diferencia onboarding wizard (`/onboarding`):
 *   - Hero header steady-state (NO presión · NO "Saltar")
 *   - Sección "Mis conexiones activas" · per-connector card con:
 *       · status badge + last_synced_at
 *       · remediations count badge → /remediaciones?connector_id (DRY)
 *       · "Solicitar disconnect" → modal chat-mediated (ADR-014 sostained)
 *   - Sección "Añadir / re-conectar" · render CloudConnectFirstStep AS-IS
 *     (component-level reuse · DRY OPS-026 · NO duplicación)
 *
 * SSE subscribe cloud.connector.* eventos + cloud_remediation_* eventos.
 * audit_log entries emitidos backend (cliente.cloud_connector.viewed/connect_initiated/
 * disconnect_requested) con project_id + client_id Sub-atom 5.A pattern.
 *
 * R29 firmísimo · friendly · NO admin lingo · NO presión coercitiva.
 * ADR-014 read-only OAuth sostained · cliente NUNCA ejecuta revoke.
 */

import * as React from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Cloud,
  Loader2,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { CloudConnectFirstStep } from "@/components/client-portal/CloudConnectFirstStep";
import { PageContainer } from "@/components/layout/PageContainer";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  REMEDIATIONS_QUERY_KEY,
  useClientRemediations,
} from "@/hooks/useClientCloudRemediations";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import {
  cloudConnectorsClientApi,
  type CloudConnectorPublicSummary,
} from "@/lib/api/cloud-connectors-client";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

interface ClientProjectResponse {
  id?: string;
}

interface ConnectorsListResponse {
  items: CloudConnectorPublicSummary[];
  project_id: string;
}

const PROVIDER_PRETTY: Record<string, string> = {
  microsoft_365: "Microsoft 365",
  google_workspace: "Google Workspace",
  azure: "Azure",
  aws: "AWS",
  github: "GitHub",
  manual_import: "Inventario manual",
};

function prettyProvider(p: string): string {
  return PROVIDER_PRETTY[p] ?? p.replace(/_/g, " ");
}

function statusVariant(
  status: string,
): "secondary" | "success" | "warning" | "danger" {
  if (status === "connected") return "success";
  if (status === "syncing" || status === "pending_oauth") return "warning";
  if (status === "sync_error" || status === "expired" || status === "revoked")
    return "danger";
  return "secondary";
}

function statusLabel(status: string): string {
  switch (status) {
    case "connected":
      return "Conectado";
    case "syncing":
      return "Sincronizando";
    case "pending_oauth":
      return "Esperando autorización";
    case "sync_error":
      return "Error de sincronización";
    case "expired":
      return "Sesión expirada";
    case "revoked":
      return "Desconectado";
    default:
      return status;
  }
}

export default function CloudConnectionsPage() {
  const [projectId, setProjectId] = React.useState<string | null>(null);
  const [projectStatus, setProjectStatus] = React.useState<
    "loading" | "ready" | "no-project" | "error"
  >("loading");
  const [projectError, setProjectError] = React.useState<string | null>(null);

  const [connectorsData, setConnectorsData] =
    React.useState<ConnectorsListResponse | null>(null);
  const [connectorsLoading, setConnectorsLoading] = React.useState(true);
  const [connectorsError, setConnectorsError] = React.useState<string | null>(
    null,
  );

  const remediationsQuery = useClientRemediations(projectStatus === "ready");

  // Disconnect modal state
  const [disconnectTarget, setDisconnectTarget] = React.useState<{
    connectorId: string;
    provider: string;
  } | null>(null);
  const [disconnectJustification, setDisconnectJustification] =
    React.useState("");
  const [disconnectSubmitting, setDisconnectSubmitting] = React.useState(false);

  // Resolve project_id cliente
  React.useEffect(() => {
    let cancelled = false;
    clientApi<ClientProjectResponse>("/client-portal/project")
      .then((res) => {
        if (cancelled) return;
        if (!res.id) {
          setProjectStatus("no-project");
          return;
        }
        setProjectId(res.id);
        setProjectStatus("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ClientApiError && err.status === 404) {
          setProjectStatus("no-project");
          return;
        }
        setProjectStatus("error");
        setProjectError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadConnectors = React.useCallback(async () => {
    setConnectorsLoading(true);
    setConnectorsError(null);
    try {
      const res = await cloudConnectorsClientApi.list();
      setConnectorsData(res);
    } catch (err) {
      setConnectorsError(err instanceof Error ? err.message : String(err));
    } finally {
      setConnectorsLoading(false);
    }
  }, []);

  React.useEffect(() => {
    if (projectStatus === "ready") {
      void loadConnectors();
    }
  }, [projectStatus, loadConnectors]);

  // SSE subscribe · cloud.connector.* + cloud_remediation_* invalidate
  useClientProjectEvents(projectId, {
    invalidateQueries: [REMEDIATIONS_QUERY_KEY as unknown as string[]],
    onCloudConnectorConnected: () => void loadConnectors(),
    onCloudConnectorDisconnected: () => void loadConnectors(),
    onCloudConnectorSyncCompleted: () => void loadConnectors(),
    onCloudConnectorError: () => void loadConnectors(),
    onCloudConnectorDisconnectRequested: () => {
      /* Confirmation toast handled inline post-submit */
    },
  });

  // Remediations counts grouped by connector_id (DRY · remediation source-of-truth)
  // RemediationGap currently includes project_id but NOT connector_id at top-level
  // (backend lookup via gap.connector_id available on admin schema only). We use
  // total pending as the badge count fallback · per-connector grouping wired si
  // backend exposes connector_id en cliente schema (Future-X demand-driven).
  const totalPendingRemediations = React.useMemo(() => {
    const gaps = remediationsQuery.data?.gaps ?? [];
    return gaps.filter((g) => g.approval_status === "proposed_to_cliente")
      .length;
  }, [remediationsQuery.data]);

  const openDisconnectModal = (connectorId: string, provider: string) => {
    setDisconnectTarget({ connectorId, provider });
    setDisconnectJustification("");
  };

  const closeDisconnectModal = () => {
    if (disconnectSubmitting) return;
    setDisconnectTarget(null);
    setDisconnectJustification("");
  };

  const submitDisconnect = async () => {
    if (!disconnectTarget) return;
    const justification = disconnectJustification.trim();
    if (justification.length < 1) {
      toast.warning("Cuéntale a Marcos por qué quieres desconectar.");
      return;
    }
    setDisconnectSubmitting(true);
    try {
      const res = await cloudConnectorsClientApi.requestDisconnect(
        disconnectTarget.connectorId,
        justification,
      );
      toast.success(res.friendly_message);
      setDisconnectTarget(null);
      setDisconnectJustification("");
      // refresh in case backend emits cloud.connector.* later
      void loadConnectors();
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "No pudimos enviar tu solicitud. Inténtalo de nuevo.",
      );
    } finally {
      setDisconnectSubmitting(false);
    }
  };

  if (projectStatus === "loading") {
    return (
      <div
        className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500"
        data-testid="cloud-connections-loading"
      >
        <Loader2 className="size-4 animate-spin" />
        Cargando proyecto…
      </div>
    );
  }

  if (projectStatus === "error") {
    return (
      <div className="p-6">
        <Alert variant="danger" data-testid="cloud-connections-error">
          <AlertTitle>No se pudo cargar el proyecto</AlertTitle>
          <AlertDescription>
            {projectError ?? "Inténtalo de nuevo más tarde."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (projectStatus === "no-project" || !projectId) {
    return (
      <div className="p-6">
        <Card>
          <CardHeader>
            <CardTitle>Sin proyecto activo</CardTitle>
            <CardDescription>
              Aún no tienes un proyecto asignado. Marcos te avisará cuando esté
              listo.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  const connectors = connectorsData?.items ?? [];
  const connectedConnectors = connectors.filter(
    (c) => c.status === "connected",
  );

  return (
    <PageContainer variant="app">
      <div
        className="space-y-8"
        data-testid="cloud-connections-page"
      >
      {/* Hero steady-state */}
      <header className="space-y-2">
        <h1 className="flex items-center gap-2 text-2xl font-semibold text-fulkro-primary-700">
          <Cloud className="size-6" />
          Conexiones cloud
        </h1>
        <p className="text-sm text-fulkro-ink-500">
          Gestiona tus conexiones a Microsoft 365, Google Workspace, AWS, Azure
          y otros sistemas. FULKRO usa lectura segura para detectar mejoras de
          cumplimiento ENS.
        </p>
      </header>

      {/* Sección: Mis conexiones activas */}
      <section
        className="space-y-3"
        aria-labelledby="cloud-connections-active-heading"
        data-testid="cloud-connections-active"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2
            id="cloud-connections-active-heading"
            className="text-lg font-medium"
          >
            Mis conexiones activas{" "}
            <span className="text-sm font-normal text-fulkro-ink-500">
              ({connectedConnectors.length})
            </span>
          </h2>
          {totalPendingRemediations > 0 && (
            <Link
              href="/client-portal/remediaciones"
              className="inline-flex items-center gap-2 text-sm font-medium text-fulkro-primary-700 underline-offset-2 hover:underline"
              data-testid="cloud-connections-remediations-link"
            >
              <ShieldCheck className="size-4" />
              {totalPendingRemediations} mejoras propuestas pendientes
            </Link>
          )}
        </div>

        {connectorsLoading ? (
          <div className="space-y-3" data-testid="cloud-connections-skeleton">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : connectorsError ? (
          <Alert variant="danger">
            <AlertTitle>No pudimos cargar tus conexiones</AlertTitle>
            <AlertDescription>{connectorsError}</AlertDescription>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => void loadConnectors()}
              data-testid="cloud-connections-retry"
            >
              Reintentar
            </Button>
          </Alert>
        ) : connectedConnectors.length === 0 ? (
          <EmptyState
            icon={<Cloud className="h-12 w-12" />}
            title="Aún no hay conexiones activas"
            description="Conecta tu primer sistema en la sección de abajo. Sin prisa por tu parte."
          />
        ) : (
          <ul
            className="grid grid-cols-1 gap-3 md:grid-cols-2"
            data-testid="cloud-connections-list"
          >
            {connectedConnectors.map((c) => (
              <li key={c.id}>
                <Card
                  className="bg-white"
                  data-testid={`cloud-connection-card-${c.provider}`}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-base">
                        {prettyProvider(c.provider)}
                      </CardTitle>
                      <Badge variant={statusVariant(c.status)}>
                        {statusLabel(c.status)}
                      </Badge>
                    </div>
                    {c.last_sync_at && (
                      <CardDescription className="text-xs">
                        Última lectura:{" "}
                        {new Date(c.last_sync_at).toLocaleString("es-ES", {
                          dateStyle: "short",
                          timeStyle: "short",
                        })}{" "}
                        · {c.resources_count} elementos detectados
                      </CardDescription>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p
                      className="text-xs italic text-fulkro-ink-500"
                      data-testid={`cloud-connection-friendly-${c.provider}`}
                    >
                      {c.friendly_message}
                    </p>
                    <div className="flex items-center gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => openDisconnectModal(c.id, c.provider)}
                        data-testid={`cloud-connection-request-disconnect-${c.provider}`}
                      >
                        Solicitar disconnect
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Sección: Añadir / re-conectar · DRY component reuse */}
      <section
        className="space-y-3"
        aria-labelledby="cloud-connections-add-heading"
        data-testid="cloud-connections-add"
      >
        <h2 id="cloud-connections-add-heading" className="text-lg font-medium">
          Añadir nuevas conexiones
        </h2>
        <p className="text-sm text-fulkro-ink-500">
          Estos sistemas son los que detectamos automáticamente. Pulsa para
          autorizar uno nuevo.
        </p>
        {/* CloudConnectFirstStep tiene su propio fetch interno · su Hero NO
            está oculto pero es coherente con la sección "Añadir nuevas
            conexiones". Si necesitas variante sin hero ver
            Future-1.E.cloud-connect-step-headerless-mode. */}
        <CloudConnectFirstStep projectId={projectId} />
      </section>

      {/* Modal · Solicitar disconnect (chat-mediated · ADR-014 sostained) */}
      <Dialog
        open={disconnectTarget !== null}
        onOpenChange={(open) => {
          if (!open) closeDisconnectModal();
        }}
      >
        <DialogContent
          className="sm:max-w-md"
          data-testid="cloud-connect-disconnect-modal"
        >
          <DialogHeader>
            <DialogTitle>
              Solicitar desconexión
              {disconnectTarget
                ? ` · ${prettyProvider(disconnectTarget.provider)}`
                : ""}
            </DialogTitle>
            <DialogDescription>
              Marcos revisará tu solicitud y te contactará por chat para
              confirmar. Tus datos siguen seguros · sin pasos urgentes por tu
              parte.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label
              htmlFor="cloud-disconnect-justification"
              className="text-xs font-medium text-fulkro-ink-700"
            >
              Cuéntale a Marcos por qué
            </label>
            <Textarea
              id="cloud-disconnect-justification"
              value={disconnectJustification}
              onChange={(e) => setDisconnectJustification(e.target.value)}
              rows={4}
              maxLength={1000}
              placeholder="Ejemplo: Cambiamos a otro proveedor de identidad…"
              data-testid="cloud-disconnect-justification"
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={closeDisconnectModal}
              disabled={disconnectSubmitting}
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={() => void submitDisconnect()}
              disabled={disconnectSubmitting}
              data-testid="cloud-disconnect-submit"
            >
              {disconnectSubmitting ? (
                <>
                  <Loader2 className="mr-2 size-3.5 animate-spin" />
                  Enviando…
                </>
              ) : (
                "Enviar solicitud"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      </div>
    </PageContainer>
  );
}
