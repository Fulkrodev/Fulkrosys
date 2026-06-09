"use client";

/**
 * Chain integrity banner · SAN-E v3.MB-6 atom 0.2.
 *
 * Status visual cadena criptográfica firmas:
 *  - chain_valid=true · ✅ intacta · tampering detectable
 *  - chain_valid=false · ⚠️ broken_links · contactar consultor
 *  - sin firmas todavía · estado informativo neutro
 */
import { ShieldCheck, ShieldAlert, Link2 } from "lucide-react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface ChainIntegrityBannerProps {
  chainValid: boolean;
  brokenLinksCount: number;
  totalSigned: number;
}

export function ChainIntegrityBanner({
  chainValid,
  brokenLinksCount,
  totalSigned,
}: ChainIntegrityBannerProps) {
  if (totalSigned === 0) {
    return (
      <Card className="p-5 flex items-start gap-3">
        <Link2 className="h-5 w-5 mt-0.5 flex-shrink-0 text-fulkro-ink-600" aria-hidden />
        <div>
          <div className="font-semibold text-sm text-fulkro-ink-700">
            Sin firmas todavía
          </div>
          <p className="text-sm text-fulkro-ink-500 mt-1">
            Cuando firmes el primer documento se creará una cadena criptográfica
            que vincula todas las firmas posteriores. Esto permite detectar
            cualquier intento de manipulación tras la firma.
          </p>
        </div>
      </Card>
    );
  }

  if (!chainValid) {
    return (
      <Card
        className={cn(
          "p-5 flex items-start gap-3",
          "border-fulkro-warning/40 bg-fulkro-warning/10",
        )}
      >
        <ShieldAlert
          className="h-5 w-5 mt-0.5 flex-shrink-0 text-fulkro-warning"
          aria-hidden
        />
        <div>
          <div className="font-semibold text-sm text-fulkro-warning">
            Cadena de firmas con incidencias
          </div>
          <p className="text-sm text-fulkro-ink-600 mt-1">
            Se han detectado {brokenLinksCount}{" "}
            {brokenLinksCount === 1 ? "enlace roto" : "enlaces rotos"} en la
            cadena criptográfica. Contacta con tu consultor ENS para revisar la
            integridad del histórico antes de continuar con nuevas firmas.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card
      className={cn(
        "p-5 flex items-start gap-3",
        "border-fulkro-success/40 bg-fulkro-success/10",
      )}
    >
      <ShieldCheck
        className="h-5 w-5 mt-0.5 flex-shrink-0 text-fulkro-success"
        aria-hidden
      />
      <div>
        <div className="font-semibold text-sm text-fulkro-success">
          Cadena criptográfica intacta · {totalSigned}{" "}
          {totalSigned === 1 ? "firma vinculada" : "firmas vinculadas"}
        </div>
        <p className="text-sm text-fulkro-ink-600 mt-1">
          Cada firma está enlazada criptográficamente con la anterior mediante
          SHA-256 + Ed25519. Cualquier modificación posterior se detecta de
          forma automática. Trazabilidad ENAC asegurada.
        </p>
      </div>
    </Card>
  );
}
