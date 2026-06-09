"use client";

/**
 * Signature card · SAN-E v3.MB-6 atom 0.2.
 *
 * Card por signable_type · adapta UI según status:
 *  - pending_creation · gris · CTA "Iniciar firma" link al portal correspondiente
 *  - pending / otp_required · azul · "Firma en curso" link al portal
 *  - signed · verde · fecha + chain position + hash preview
 *  - rejected / expired · rojo claro · informativo
 */
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  FileSignature,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { type SignatureCardView } from "@/lib/api/signing-history";
import { cn } from "@/lib/utils";

interface SignatureCardProps {
  card: SignatureCardView;
}

function formatSignedAt(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortHash(hash: string | null): string {
  if (!hash) return "";
  return `${hash.slice(0, 8)}…${hash.slice(-6)}`;
}

export function SignatureCard({ card }: SignatureCardProps) {
  const isSigned = card.status === "signed";
  const isInFlight =
    card.status === "pending" ||
    card.status === "otp_required" ||
    card.status === "otp_verified";
  const isRejected = card.status === "rejected" || card.status === "expired";

  return (
    <Card
      data-signable-type={card.signable_type}
      data-status={card.status}
      className={cn(
        "p-5",
        isSigned && "border-fulkro-success/30",
        isInFlight && "border-fulkro-info/30",
        isRejected && "border-destructive/30",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {isSigned ? (
            <CheckCircle2
              className="h-5 w-5 mt-0.5 flex-shrink-0 text-fulkro-success"
              aria-hidden
            />
          ) : isRejected ? (
            <XCircle
              className="h-5 w-5 mt-0.5 flex-shrink-0 text-destructive"
              aria-hidden
            />
          ) : isInFlight ? (
            <Clock
              className="h-5 w-5 mt-0.5 flex-shrink-0 text-fulkro-info"
              aria-hidden
            />
          ) : (
            <FileSignature
              className="h-5 w-5 mt-0.5 flex-shrink-0 text-fulkro-ink-600"
              aria-hidden
            />
          )}
          <div className="min-w-0">
            <div className="font-semibold text-sm text-fulkro-ink-800 truncate">
              {card.signable_label}
            </div>
            {isSigned && card.signed_at && (
              <div className="text-xs text-fulkro-ink-500 mt-1">
                Firmada el {formatSignedAt(card.signed_at)}
              </div>
            )}
            {isInFlight && (
              <div className="text-xs text-fulkro-info mt-1">
                Firma en curso · pendiente de finalizar
              </div>
            )}
            {isRejected && (
              <div className="text-xs text-destructive mt-1">
                Rechazada · contacta con el consultor para reabrir
              </div>
            )}
            {card.status === "pending_creation" && (
              <div className="text-xs text-fulkro-ink-500 mt-1">
                Aún no se ha iniciado el flujo de firma
              </div>
            )}
          </div>
        </div>
        {isSigned ? (
          <Badge variant="success" className="flex-shrink-0">
            Firmada
          </Badge>
        ) : isInFlight ? (
          <Badge variant="info" className="flex-shrink-0">
            En curso
          </Badge>
        ) : isRejected ? (
          <Badge variant="danger" className="flex-shrink-0">
            Rechazada
          </Badge>
        ) : (
          <Badge variant="secondary" className="flex-shrink-0">
            Pendiente
          </Badge>
        )}
      </div>

      {isSigned && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div>
            <div className="text-fulkro-ink-500 uppercase tracking-wide">
              Posición en cadena
            </div>
            <div className="font-mono text-fulkro-ink-700 mt-0.5">
              #{card.chain_position}
            </div>
          </div>
          <div className="min-w-0">
            <div className="text-fulkro-ink-500 uppercase tracking-wide">
              Hash documento
            </div>
            <div
              className="font-mono text-fulkro-ink-700 mt-0.5 truncate"
              title={card.document_hash_sha256 ?? ""}
            >
              {shortHash(card.document_hash_sha256)}
            </div>
          </div>
          <div className="min-w-0">
            <div className="text-fulkro-ink-500 uppercase tracking-wide">
              Hash evento
            </div>
            <div
              className="font-mono text-fulkro-ink-700 mt-0.5 truncate"
              title={card.event_hash_sha256 ?? ""}
            >
              {shortHash(card.event_hash_sha256)}
            </div>
          </div>
        </div>
      )}

      <div className="mt-4">
        <Link
          href={card.portal_path}
          className={cn(
            "inline-flex items-center gap-1 text-sm font-medium",
            "text-fulkro-primary-700 hover:text-fulkro-primary-800",
            "focus:outline-none focus:ring-2 focus:ring-fulkro-primary-700 rounded",
          )}
        >
          {isSigned
            ? "Ver detalle de la firma"
            : isInFlight
              ? "Continuar firma"
              : "Ir al flujo de firma"}
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </Card>
  );
}
