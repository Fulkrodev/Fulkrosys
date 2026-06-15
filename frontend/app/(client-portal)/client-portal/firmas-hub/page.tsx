"use client";

/**
 * /client-portal/firmas-hub · SAN-E v3.MB-6 atom 0.2.
 *
 * Cliente VE TODAS sus firmas ENS previas + chain integrity status:
 *  1. Progress bar X / 4 firmas completadas
 *  2. Chain integrity banner (intacta / con incidencias / sin firmas)
 *  3. 4 cards per signable_type (DdA · MAGERIT · Pentest · Conformidad)
 *  4. Chain visualizer post-firmas (cadena lineal hashes vinculados)
 *  5. Readiness snapshot expand · post-conformidad firma (audit trail ENAC)
 *
 * Backend wire-up: GET /api/v1/portal/signing/projects/{id}/history.
 */
import { useState } from "react";
import { AlertCircle, ChevronDown, ChevronUp, FileSignature } from "lucide-react";

import { ChainIntegrityBanner } from "@/components/client-portal/firmas-hub/ChainIntegrityBanner";
import { ChainVisualizer } from "@/components/client-portal/firmas-hub/ChainVisualizer";
import { SignatureCard } from "@/components/client-portal/firmas-hub/SignatureCard";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useSigningHistoryClient } from "@/hooks/useSigningHistoryClient";

export default function FirmasHubPage() {
  const { loading, error, history } = useSigningHistoryClient();
  const [snapshotOpen, setSnapshotOpen] = useState(false);

  return (
    <div className="space-y-6 px-4 py-6 sm:px-6 md:px-8 max-w-5xl mx-auto">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-fulkro-primary-700">
          <FileSignature className="h-5 w-5" aria-hidden />
          <span className="text-xs uppercase tracking-wide font-semibold">
            Portal cliente
          </span>
        </div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-fulkro-ink-800">
          Mis firmas <TooltipENS term="ENS" />
        </h1>
        <p className="text-sm text-fulkro-ink-600 max-w-3xl">
          Historial completo de tus firmas in-portal a lo largo del proyecto{" "}
          <TooltipENS term="ENS" />. Cada firma queda enlazada
          criptográficamente con la anterior (<TooltipENS term="Ed25519" />{" "}
          + <TooltipENS term="SHA256" />) para garantizar trazabilidad{" "}
          <TooltipENS term="ENAC" /> y detectar manipulación.
        </p>
      </header>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {error && (
        <Card className="p-5 border-destructive/40 bg-destructive/5">
          <div className="flex items-start gap-2 text-sm">
            <AlertCircle className="h-5 w-5 mt-0.5 text-destructive flex-shrink-0" aria-hidden />
            <div>
              <div className="font-semibold text-destructive">
                Error cargando historial de firmas
              </div>
              <p className="text-fulkro-ink-600 mt-1">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && history && (
        <>
          <Card className="p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <div className="text-sm font-semibold text-fulkro-ink-700">
                  Progreso del proyecto
                </div>
                <div className="text-xs text-fulkro-ink-500 mt-0.5">
                  {history.total_signed} de {history.total_expected} firmas
                  completadas
                </div>
              </div>
              <div className="text-2xl font-bold text-fulkro-primary-700 font-mono tabular-nums">
                {history.total_expected > 0
                  ? Math.round(
                      (history.total_signed / history.total_expected) * 100,
                    )
                  : 0}
                %
              </div>
            </div>
            <Progress
              value={
                history.total_expected > 0
                  ? (history.total_signed / history.total_expected) * 100
                  : 0
              }
              className="h-2"
            />
          </Card>

          <ChainIntegrityBanner
            chainValid={history.chain_valid}
            brokenLinksCount={history.broken_links_count}
            totalSigned={history.total_signed}
          />

          <section className="space-y-3" aria-label="Firmas por documento">
            {history.signatures.map((sig) => (
              <SignatureCard key={sig.signable_type} card={sig} />
            ))}
          </section>

          {history.total_signed > 0 && (
            <ChainVisualizer signatures={history.signatures} />
          )}

          {history.readiness_snapshot && (
            <Card className="p-5">
              <button
                type="button"
                onClick={() => setSnapshotOpen((v) => !v)}
                className="w-full flex items-center justify-between text-left"
                aria-expanded={snapshotOpen}
              >
                <div>
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-fulkro-ink-700">
                    Detalles auditoría <TooltipENS term="ENAC" />
                  </div>
                  <div className="text-xs text-fulkro-ink-500 mt-0.5">
                    Snapshot capturado al firmar la Declaración de Conformidad{" "}
                    <TooltipENS term="ENS" />
                  </div>
                </div>
                {snapshotOpen ? (
                  <ChevronUp className="h-4 w-4 text-fulkro-ink-500" aria-hidden />
                ) : (
                  <ChevronDown className="h-4 w-4 text-fulkro-ink-500" aria-hidden />
                )}
              </button>
              {snapshotOpen && (
                <pre className="mt-4 p-3 rounded-lg bg-fulkro-ink-50 text-xs font-mono text-fulkro-ink-700 overflow-x-auto whitespace-pre-wrap break-words">
                  {JSON.stringify(history.readiness_snapshot, null, 2)}
                </pre>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
}
