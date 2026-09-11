"use client";

/**
 * ScanStatusBadge · SAN-E v3.MB-6 atom 6 · ENS op.exp.6.
 *
 * 5 variants color-coded scan_status (Q5 A cement · cliente VE siempre):
 *  - clean       · green CheckCircle2 · "Limpio"
 *  - scanning    · blue Loader2 animate-spin · "Escaneando..."
 *  - infected    · red AlertTriangle · "Infectado"
 *  - quarantined · orange ShieldAlert · "En cuarentena"
 *  - error       · amber AlertCircle · "Error escaneo"
 *
 * Reusable cross-portal (cliente list evidencias + admin quarantine review).
 */
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type EvidenceScanStatus =
  | "clean"
  | "scanning"
  | "infected"
  | "error"
  | "quarantined";

interface ScanStatusInfo {
  label: string;
  icon: LucideIcon;
  spinning?: boolean;
  badgeVariant:
    | "default"
    | "info"
    | "success"
    | "warning"
    | "danger"
    | "secondary";
  iconClassName: string;
  tooltip: string;
}

const SCAN_STATUS_INFO: Record<EvidenceScanStatus, ScanStatusInfo> = {
  clean: {
    label: "Limpio",
    icon: CheckCircle2,
    badgeVariant: "success",
    iconClassName: "text-fulkro-success",
    tooltip: "Archivo escaneado · sin amenazas detectadas",
  },
  scanning: {
    label: "Escaneando…",
    icon: Loader2,
    spinning: true,
    badgeVariant: "info",
    iconClassName: "text-fulkro-info",
    tooltip: "Análisis antivirus en curso (ClamAV)",
  },
  infected: {
    label: "Infectado",
    icon: AlertTriangle,
    badgeVariant: "danger",
    iconClassName: "text-destructive",
    tooltip: "Amenaza detectada · archivo bloqueado",
  },
  quarantined: {
    label: "En cuarentena",
    icon: ShieldAlert,
    badgeVariant: "warning",
    iconClassName: "text-fulkro-warning",
    tooltip: "Archivo aislado · admin revisará posibles falsos positivos",
  },
  error: {
    label: "Error escaneo",
    icon: AlertCircle,
    badgeVariant: "secondary",
    iconClassName: "text-fulkro-ink-500",
    tooltip: "Análisis antivirus no completado · admin revisará",
  },
};

interface Props {
  status: EvidenceScanStatus;
  size?: "sm" | "md";
  showLabel?: boolean;
  className?: string;
}

export function ScanStatusBadge({
  status,
  size = "sm",
  showLabel = true,
  className,
}: Props) {
  const info = SCAN_STATUS_INFO[status];
  const Icon = info.icon;
  const iconSize = size === "sm" ? "h-3 w-3" : "h-4 w-4";

  return (
    <Badge
      variant={info.badgeVariant}
      title={info.tooltip}
      data-testid={`scan-status-${status}`}
      data-scan-status={status}
      className={cn("inline-flex items-center gap-1", className)}
    >
      <Icon
        className={cn(
          iconSize,
          info.iconClassName,
          info.spinning && "animate-spin",
        )}
        aria-hidden
      />
      {showLabel && <span>{info.label}</span>}
    </Badge>
  );
}
