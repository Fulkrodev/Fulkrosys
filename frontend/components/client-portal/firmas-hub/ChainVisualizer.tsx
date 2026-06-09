"use client";

/**
 * Chain visualizer · SAN-E v3.MB-6 atom 0.2.
 *
 * Visualización lineal de la cadena de firmas project ordenadas por
 * chain_position. Solo muestra signed cards. Útil para auditar trazabilidad
 * post-conformidad ENS.
 */
import { ArrowRight, Link2 } from "lucide-react";

import { Card } from "@/components/ui/card";
import { type SignatureCardView } from "@/lib/api/signing-history";

interface ChainVisualizerProps {
  signatures: SignatureCardView[];
}

function shortHash(hash: string | null): string {
  if (!hash) return "—";
  return `${hash.slice(0, 6)}…${hash.slice(-4)}`;
}

export function ChainVisualizer({ signatures }: ChainVisualizerProps) {
  const signed = signatures
    .filter((s) => s.status === "signed" && s.chain_position !== null)
    .sort((a, b) => (a.chain_position ?? 0) - (b.chain_position ?? 0));

  if (signed.length === 0) {
    return null;
  }

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2 mb-4">
        <Link2 className="h-4 w-4 text-fulkro-ink-500" aria-hidden />
        <h2 className="text-sm font-semibold text-fulkro-ink-700">
          Cadena criptográfica
        </h2>
        <span className="text-xs text-fulkro-ink-500">
          ({signed.length} {signed.length === 1 ? "eslabón" : "eslabones"})
        </span>
      </div>

      <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-stretch gap-2">
        {signed.map((sig, idx) => (
          <div
            key={sig.signature_event_id ?? sig.signable_type}
            className="flex items-center gap-2 flex-1 min-w-0"
          >
            <div
              className="flex-1 min-w-0 rounded-lg border border-fulkro-success/30 bg-fulkro-success/5 p-3"
              data-chain-position={sig.chain_position}
            >
              <div className="text-xs text-fulkro-ink-500 uppercase tracking-wide">
                #{sig.chain_position}
              </div>
              <div className="text-sm font-medium text-fulkro-ink-800 mt-1 truncate">
                {sig.signable_label}
              </div>
              <div className="text-xs font-mono text-fulkro-ink-500 mt-1 truncate">
                {shortHash(sig.event_hash_sha256)}
              </div>
            </div>
            {idx < signed.length - 1 && (
              <ArrowRight
                className="h-4 w-4 text-fulkro-ink-600 hidden sm:block flex-shrink-0"
                aria-hidden
              />
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
