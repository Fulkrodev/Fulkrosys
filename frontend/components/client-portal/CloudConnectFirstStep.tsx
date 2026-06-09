"use client";

/**
 * CloudConnectFirstStep · sub-atom 1.D.X.I v3.12.
 *
 * "Conecta tus sistemas" primer paso onboarding cliente · super mega fácil.
 *
 * R29 firmísimo:
 * - Hero amistoso · cero presión · "saltar y conectar después" prominente
 * - Grid de cards per provider con icon emoji + blurb friendly
 * - Tooltips primer-principios para "¿Qué hago aquí?" + "¿Es seguro?"
 * - Status badge por conector conectado · friendly_message server-side
 *
 * Flow:
 *   1. Carga catalog providers + lista de conectores existentes
 *   2. Click en card → POST /connect/{provider} → backend devuelve next_step
 *      - oauth_redirect → window.location a m16_portal_init_path
 *      - manual_upload → muestra UI subir Excel/CSV
 *   3. Sync progress feedback via list re-fetch (SSE wire en 1.D.G existing)
 */

import * as React from "react";
import {
  CheckCircle2,
  Cloud,
  HelpCircle,
  Loader2,
  Shield,
  Upload,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  cloudConnectorsClientApi,
  type CloudConnectorProviderCatalogItem,
  type CloudConnectorPublicSummary,
  ClientApiError,
} from "@/lib/api/cloud-connectors-client";

interface Props {
  projectId: string;
  onSkip?: () => void;
}

type ModalState =
  | { kind: "closed" }
  | { kind: "help" }
  | { kind: "security" }
  | { kind: "manual_upload"; connectorId: string };

export function CloudConnectFirstStep({ projectId, onSkip }: Props) {
  const [catalog, setCatalog] = React.useState<CloudConnectorProviderCatalogItem[]>([]);
  const [connectors, setConnectors] = React.useState<CloudConnectorPublicSummary[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [connectingProvider, setConnectingProvider] = React.useState<string | null>(null);
  const [modal, setModal] = React.useState<ModalState>({ kind: "closed" });

  const loadAll = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cat, list] = await Promise.all([
        cloudConnectorsClientApi.getCatalog(),
        cloudConnectorsClientApi.list(),
      ]);
      setCatalog(cat);
      setConnectors(list.items);
    } catch (err) {
      const msg = err instanceof ClientApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadAll();
  }, [loadAll]);

  const statusByProvider = React.useMemo(() => {
    const map = new Map<string, CloudConnectorPublicSummary>();
    for (const c of connectors) map.set(c.provider, c);
    return map;
  }, [connectors]);

  async function handleConnect(provider: string) {
    setConnectingProvider(provider);
    setError(null);
    try {
      const res = await cloudConnectorsClientApi.initConnect(provider);
      if (res.next_step === "oauth_redirect" && res.m16_portal_init_path) {
        window.location.href = res.m16_portal_init_path;
        return;
      }
      if (res.next_step === "manual_upload") {
        setModal({ kind: "manual_upload", connectorId: res.connector_id });
      }
      await loadAll();
    } catch (err) {
      const msg = err instanceof ClientApiError
        ? err.message
        : err instanceof Error
        ? err.message
        : String(err);
      setError(msg);
    } finally {
      setConnectingProvider(null);
    }
  }

  return (
    <div className="space-y-6" data-testid="cloud-connect-first-step">
      {/* Hero R29 friendly */}
      <Card className="border-fulkro-primary-200 bg-fulkro-primary-50/40">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2 text-fulkro-primary-800">
                <Cloud className="size-5" />
                Conecta tus sistemas
              </CardTitle>
              <CardDescription className="mt-2 text-sm leading-relaxed text-fulkro-ink-700">
                Para hacer un diagnóstico ENS verdadero · necesitamos ver tu
                sistema real · no solo lo que nos cuentes. Tranquilo · solo
                lectura · 5 minutos. Puedes saltar y conectar después.
              </CardDescription>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-fulkro-ink-500">
                <button
                  type="button"
                  className="flex items-center gap-1 underline-offset-2 hover:underline"
                  onClick={() => setModal({ kind: "help" })}
                  data-testid="cloud-connect-help-btn"
                >
                  <HelpCircle className="size-3.5" />
                  ¿Qué hago aquí?
                </button>
                <button
                  type="button"
                  className="flex items-center gap-1 underline-offset-2 hover:underline"
                  onClick={() => setModal({ kind: "security" })}
                  data-testid="cloud-connect-security-btn"
                >
                  <Shield className="size-3.5" />
                  ¿Es seguro?
                </button>
              </div>
            </div>
            {onSkip && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onSkip}
                data-testid="cloud-connect-skip-btn"
              >
                Saltar por ahora
              </Button>
            )}
          </div>
        </CardHeader>
      </Card>

      {error && (
        <div
          className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          data-testid="cloud-connect-error"
          role="alert"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div
          className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500"
          data-testid="cloud-connect-loading"
        >
          <Loader2 className="size-4 animate-spin" />
          Cargando opciones…
        </div>
      ) : (
        <div
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
          data-testid="cloud-connect-grid"
        >
          {catalog.map((item) => {
            const status = statusByProvider.get(item.provider);
            const isConnected = status?.status === "connected";
            const isPending = status?.status === "pending_oauth";
            const isConnecting = connectingProvider === item.provider;
            return (
              <Card
                key={item.provider}
                className={`relative transition-all ${
                  isConnected
                    ? "border-emerald-300 bg-emerald-50/30"
                    : "hover:border-fulkro-primary-300 hover:shadow-md"
                }`}
                data-testid={`cloud-connect-card-${item.provider}`}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-2xl" aria-hidden="true">
                      {item.icon_emoji}
                    </span>
                    {isConnected && (
                      <CheckCircle2
                        className="size-5 text-emerald-700"
                        aria-label="Conectado"
                      />
                    )}
                  </div>
                  <CardTitle className="mt-2 text-base">{item.display_name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs leading-relaxed text-fulkro-ink-600">
                    {item.cliente_friendly_blurb}
                  </p>
                  {status && (
                    <p
                      className="mt-2 text-xs italic text-fulkro-ink-500"
                      data-testid={`cloud-connect-friendly-msg-${item.provider}`}
                    >
                      {status.friendly_message}
                    </p>
                  )}
                  <Button
                    type="button"
                    size="sm"
                    variant={isConnected ? "outline" : "primary"}
                    className="mt-3 w-full"
                    disabled={isConnecting || isPending}
                    onClick={() => handleConnect(item.provider)}
                    data-testid={`cloud-connect-action-${item.provider}`}
                  >
                    {isConnecting && (
                      <Loader2 className="mr-2 size-3.5 animate-spin" />
                    )}
                    {isConnected
                      ? "Volver a conectar"
                      : isPending
                      ? "Autorización pendiente…"
                      : item.requires_oauth
                      ? "Conectar"
                      : item.provider === "manual_import"
                      ? (
                        <>
                          <Upload className="mr-1.5 size-3.5" />
                          Subir Excel
                        </>
                      )
                      : "Configurar"}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Tip footer · "Tengo otro sistema" */}
      <div className="rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-3 text-xs text-fulkro-ink-600">
        ¿Tienes otro sistema que no aparece? Marcos te ayuda a integrarlo ·
        responde el wizard y déjanos un mensaje en la sección &quot;Notas&quot;.
      </div>

      {/* Modal helpers (simple overlay · no portal full-blown) */}
      {modal.kind === "help" && (
        <HelpModal onClose={() => setModal({ kind: "closed" })} />
      )}
      {modal.kind === "security" && (
        <SecurityModal onClose={() => setModal({ kind: "closed" })} />
      )}
      {modal.kind === "manual_upload" && (
        <ManualUploadHint
          projectId={projectId}
          onClose={() => setModal({ kind: "closed" })}
        />
      )}
    </div>
  );
}

// ============================================================
// Sub-modales (R29 friendly · primer-principios cliente)
// ============================================================

function HelpModal({ onClose }: { onClose: () => void }) {
  return (
    <ModalShell onClose={onClose} title="¿Qué hago aquí?">
      <p>
        Aquí conectas tus sistemas (Microsoft 365, AWS, Google Workspace…)
        para que FULKRO pueda detectar tu realidad técnica:{" "}
        <strong>cuántos usuarios tienes, si usan MFA, si los backups
        están activos, etc.</strong>
      </p>
      <p>
        Sin esta información trabajamos con lo que tú nos cuentas (puede tener
        errores). Con esta información{" "}
        <strong>te damos un diagnóstico verdadero</strong> y te ahorramos
        contestar 200 preguntas técnicas.
      </p>
      <p>
        Marcos siempre puede ayudarte si te atascas — pero la mayoría de
        clientes lo resuelven solos en 5 minutos.
      </p>
    </ModalShell>
  );
}

function SecurityModal({ onClose }: { onClose: () => void }) {
  return (
    <ModalShell onClose={onClose} title="¿Es seguro?">
      <ul className="list-inside list-disc space-y-1.5">
        <li>
          <strong>Solo lectura</strong> · FULKRO nunca puede crear, modificar
          ni borrar nada en tus sistemas.
        </li>
        <li>
          <strong>Revocable en 1 click</strong> · desconectar es inmediato
          desde la misma página.
        </li>
        <li>
          <strong>Tokens cifrados</strong> · los almacenamos cifrados (Fernet
          AES-128) · solo Marcos puede usarlos para diagnóstico.
        </li>
        <li>
          <strong>OAuth estándar</strong> · usamos los flujos oficiales de
          Microsoft, Google, AWS... · sin contraseñas tuyas en FULKRO.
        </li>
      </ul>
      <p className="text-xs italic text-fulkro-ink-500">
        Si tienes dudas legales · habla con Marcos antes de conectar.
      </p>
    </ModalShell>
  );
}

function ManualUploadHint({ projectId, onClose }: {
  projectId: string;
  onClose: () => void;
}) {
  return (
    <ModalShell onClose={onClose} title="Subir inventario manual">
      <p>
        Perfecto, puedes subir un Excel/CSV con tus sistemas en la sección{" "}
        <strong>&quot;Mis archivos&quot;</strong> del portal cliente. Te creamos el
        registro de inventario automáticamente.
      </p>
      <p className="text-xs italic text-fulkro-ink-500">
        Project ID: {projectId.slice(0, 8)}…
      </p>
      <a
        href="/client-portal/files"
        data-testid="cloud-connect-manual-upload-link"
        className="inline-flex w-full items-center justify-center rounded-md bg-fulkro-primary-600 px-3 py-2 text-sm font-medium text-white hover:bg-fulkro-primary-700"
      >
        Ir a Mis archivos
      </a>
    </ModalShell>
  );
}

function ModalShell({
  title,
  children,
  onClose,
}: {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-fulkro-ink-900/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
      data-testid="cloud-connect-modal"
    >
      <Card className="w-full max-w-md">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">{title}</CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Cerrar">
            <X className="size-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-relaxed text-fulkro-ink-700">
          {children}
        </CardContent>
      </Card>
    </div>
  );
}
