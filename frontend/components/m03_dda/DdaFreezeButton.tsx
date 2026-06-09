/**
 * DdaFreezeButton · congelar/descongelar DdA · sub-atom 1.D.F.A v3.11.
 *
 * Reglas backend:
 *   - Freeze requiere ≥80% medidas valoradas (400 si incomplete)
 *   - Si frozen · botón Unfreeze para descongelar
 *   - Display fecha aprobación + aprobado_por cuando frozen
 */
"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Lock,
  Unlock,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import {
  useDdaAdminStats,
  useDdaAdminStatus,
  useFreezeDda,
  useUnfreezeDda,
} from "@/hooks/useDdaAdmin";

interface DdaFreezeButtonProps {
  projectId: string;
}

export function DdaFreezeButton({ projectId }: DdaFreezeButtonProps) {
  const { data: status } = useDdaAdminStatus(projectId);
  const { data: stats } = useDdaAdminStats(projectId);
  const freezeMutation = useFreezeDda();
  const unfreezeMutation = useUnfreezeDda();

  const [confirmOpen, setConfirmOpen] = React.useState(false);
  const [aprobadoPor, setAprobadoPor] = React.useState("");

  const isFrozen = status?.frozen ?? false;
  const completionPct = stats?.completion_pct ?? 0;
  const canFreeze = completionPct >= 80 && !isFrozen;

  const handleFreezeConfirm = () => {
    if (!aprobadoPor.trim() || aprobadoPor.trim().length < 3) {
      toast.error("Indica el nombre del RSEG que aprueba (mín. 3 caracteres).");
      return;
    }
    freezeMutation.mutate(
      { projectId, aprobadoPor: aprobadoPor.trim() },
      {
        onSuccess: (result) => {
          toast.success(
            `DdA congelada · ${result.frozen_entries} entries · aprobada por ${result.aprobado_por}.`,
          );
          setConfirmOpen(false);
          setAprobadoPor("");
        },
        onError: (err) => {
          toast.error(
            `Error: ${err instanceof Error ? err.message : String(err)}`,
          );
        },
      },
    );
  };

  const handleUnfreeze = () => {
    unfreezeMutation.mutate(
      { projectId },
      {
        onSuccess: () => {
          toast.success("DdA descongelada · ya puedes editar entries.");
        },
        onError: (err) => {
          toast.error(
            `Error: ${err instanceof Error ? err.message : String(err)}`,
          );
        },
      },
    );
  };

  return (
    <Card data-testid="dda-freeze-panel">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          {isFrozen ? (
            <Lock className="size-4 text-emerald-600" />
          ) : (
            <Unlock className="size-4 text-foreground/55" />
          )}
          {isFrozen ? "DdA congelada · audit-ready" : "DdA editable"}
          <Badge
            variant={isFrozen ? "success" : "secondary"}
            className="text-[9px] uppercase ml-1"
            data-testid="dda-freeze-status-badge"
          >
            {isFrozen ? "FROZEN" : "DRAFT"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {isFrozen ? (
          <>
            <p className="text-xs text-foreground/70">
              Aprobada por{" "}
              <span className="font-medium">
                {status?.frozen_by ?? "(sin nombre)"}
              </span>{" "}
              el{" "}
              <span className="font-medium">
                {status?.frozen_at
                  ? new Date(status.frozen_at).toLocaleString("es-ES")
                  : "(sin fecha)"}
              </span>
              .
            </p>
            <Alert>
              <CheckCircle2 className="size-4" />
              <AlertTitle>DdA inmutable</AlertTitle>
              <AlertDescription>
                Las medidas están bloqueadas para edición. Para volver a editar
                · descongela primero.
              </AlertDescription>
            </Alert>
            <Button
              type="button"
              variant="outline"
              onClick={handleUnfreeze}
              disabled={unfreezeMutation.isPending}
              data-testid="dda-unfreeze-button"
            >
              {unfreezeMutation.isPending ? (
                <>
                  <Loader2 className="mr-1.5 size-3 animate-spin" />
                  Descongelando…
                </>
              ) : (
                <>
                  <Unlock className="mr-1.5 size-3" />
                  Descongelar DdA
                </>
              )}
            </Button>
          </>
        ) : (
          <>
            <p className="text-xs text-foreground/70">
              Progreso actual:{" "}
              <span className="font-medium">
                {Math.round(completionPct)}%
              </span>{" "}
              · Se requiere ≥80% medidas valoradas para congelar.
            </p>
            {!canFreeze && (
              <Alert variant="warning">
                <AlertTriangle className="size-4" />
                <AlertTitle>Aún no se puede congelar</AlertTitle>
                <AlertDescription>
                  Faltan medidas por valorar · sube el progreso a ≥80% editando
                  estado en la lista de medidas.
                </AlertDescription>
              </Alert>
            )}
            <Button
              type="button"
              variant="primary"
              onClick={() => setConfirmOpen(true)}
              disabled={!canFreeze}
              data-testid="dda-freeze-button"
            >
              <Lock className="mr-1.5 size-3" />
              Congelar DdA
            </Button>
          </>
        )}
      </CardContent>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent data-testid="dda-freeze-confirm-modal">
          <DialogHeader>
            <DialogTitle>Confirmar congelación DdA</DialogTitle>
            <DialogDescription>
              Una vez congelada · las medidas quedan inmutables (audit-ready
              ENAC). Indica el nombre del RSEG / Responsable que aprueba.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="dda-aprobado-por">
                Aprobado por <span className="text-red-600">*</span>
              </Label>
              <Input
                id="dda-aprobado-por"
                value={aprobadoPor}
                onChange={(e) => setAprobadoPor(e.target.value)}
                placeholder="p.ej. Juan Pérez · RSEG"
                data-testid="dda-aprobado-por-input"
                maxLength={120}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmOpen(false)}
              disabled={freezeMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleFreezeConfirm}
              disabled={
                freezeMutation.isPending || aprobadoPor.trim().length < 3
              }
              data-testid="dda-freeze-confirm"
            >
              {freezeMutation.isPending ? (
                <>
                  <Loader2 className="mr-1.5 size-3 animate-spin" />
                  Congelando…
                </>
              ) : (
                <>
                  <Lock className="mr-1.5 size-3" />
                  Confirmar y congelar
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
