/**
 * DdaEntryDetailModal · ver + editar entry DdA · sub-atom 1.D.F.A v3.11.
 *
 * Edit fields:
 *   - estado_implementacion (select)
 *   - justificacion_no_aplica (textarea · requerido si estado=no_aplica)
 *   - responsable
 *   - observaciones
 *
 * Refuerzos_aplicados readonly (de catálogo · admin upgrade T1).
 */
"use client";

import * as React from "react";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

import { MeasureLensesPanel } from "@/components/m04_gap/MeasureLensesPanel";
import { useUpdateDdaEntry } from "@/hooks/useDdaAdmin";
import {
  DDA_ESTADO_LABELS,
  DDA_ESTADO_VARIANT,
  DDA_MARCO_LABELS,
  type DdaAdminEntry,
  type DdaEstadoImplementacion,
  type DdaMarco,
} from "@/lib/api/dda";

interface DdaEntryDetailModalProps {
  entry: DdaAdminEntry | null;
  /** Ola 4 · necesario para la lente CMM/semáforo por medida (endpoint admin). */
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const ESTADO_OPTIONS: { value: DdaEstadoImplementacion; label: string }[] = [
  { value: "no_valorado", label: "No valorado" },
  { value: "no_aplica", label: "No aplica" },
  { value: "no_implantada", label: "No implantada" },
  { value: "parcial", label: "Parcial" },
  { value: "implantada", label: "Implantada" },
];

export function DdaEntryDetailModal({
  entry,
  projectId,
  open,
  onOpenChange,
}: DdaEntryDetailModalProps) {
  const updateMutation = useUpdateDdaEntry();

  const [estado, setEstado] = React.useState<DdaEstadoImplementacion>(
    "no_valorado",
  );
  const [justificacion, setJustificacion] = React.useState("");
  const [responsable, setResponsable] = React.useState("");
  const [observaciones, setObservaciones] = React.useState("");

  // Reset form on entry change
  React.useEffect(() => {
    if (entry) {
      setEstado(
        (entry.estado_implementacion as DdaEstadoImplementacion) ??
          "no_valorado",
      );
      setJustificacion(entry.justificacion_no_aplica ?? "");
      setResponsable(entry.responsable ?? "");
      setObservaciones(entry.observaciones ?? "");
    }
  }, [entry]);

  if (!entry) return null;

  const requiresJustificacion = estado === "no_aplica";
  const justificacionValid =
    !requiresJustificacion || justificacion.trim().length >= 10;

  const handleSave = () => {
    if (!justificacionValid) {
      toast.error(
        "Si la medida no aplica, debes explicar el motivo (≥10 caracteres).",
      );
      return;
    }
    updateMutation.mutate(
      {
        entryId: entry.id,
        updates: {
          estado_implementacion: estado,
          justificacion_no_aplica: requiresJustificacion
            ? justificacion.trim()
            : null,
          responsable: responsable.trim() || null,
          observaciones: observaciones.trim() || null,
        },
      },
      {
        onSuccess: () => {
          toast.success(
            `Medida ${entry.measure_codigo} actualizada correctamente.`,
          );
          onOpenChange(false);
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl"
        data-testid="dda-entry-detail-modal"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <span className="font-mono text-xs">{entry.measure_codigo}</span>
            <span>{entry.measure_nombre}</span>
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2 mt-1">
            <Badge variant="secondary" className="text-[10px]">
              {DDA_MARCO_LABELS[entry.measure_marco as DdaMarco] ??
                entry.measure_marco}
            </Badge>
            {entry.measure_familia && (
              <Badge variant="outline" className="text-[10px]">
                {entry.measure_familia}
              </Badge>
            )}
            <Badge
              variant={
                DDA_ESTADO_VARIANT[entry.estado_implementacion] ?? "secondary"
              }
              className="text-[10px]"
            >
              Actual: {DDA_ESTADO_LABELS[entry.estado_implementacion]}
            </Badge>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Ola 4 cierre · las 3 lentes (declarado + evidencia #20 + madurez #21) */}
          <MeasureLensesPanel
            variant="admin"
            projectId={projectId}
            measureCode={entry.measure_codigo}
            estadoImplementacion={entry.estado_implementacion}
          />

          <div className="space-y-1.5">
            <Label htmlFor="dda-estado-select">Estado implementación</Label>
            <Select
              value={estado}
              onValueChange={(v) => setEstado(v as DdaEstadoImplementacion)}
            >
              <SelectTrigger
                id="dda-estado-select"
                data-testid="dda-edit-estado-select"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ESTADO_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {requiresJustificacion && (
            <div className="space-y-1.5">
              <Label htmlFor="dda-justificacion">
                Justificación &quot;no aplica&quot; <span className="text-red-600">*</span>
              </Label>
              <Textarea
                id="dda-justificacion"
                rows={3}
                value={justificacion}
                onChange={(e) => setJustificacion(e.target.value)}
                placeholder="Explica por qué esta medida no aplica al sistema (mín. 10 caracteres · auditor ENAC lo revisará)…"
                data-testid="dda-edit-justificacion"
              />
              {!justificacionValid && (
                <p className="text-xs text-red-600">
                  Mínimo 10 caracteres requeridos.
                </p>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="dda-responsable">Responsable</Label>
              <Input
                id="dda-responsable"
                value={responsable}
                onChange={(e) => setResponsable(e.target.value)}
                placeholder="p.ej. CISO · DPO · RSEG"
                data-testid="dda-edit-responsable"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="dda-observaciones">Observaciones internas</Label>
            <Textarea
              id="dda-observaciones"
              rows={2}
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
              placeholder="Notas para Marcos / equipo (NO visible cliente)…"
              data-testid="dda-edit-observaciones"
            />
          </div>

          {entry.magerit_safeguards.length > 0 && (
            <div className="space-y-1.5">
              <Label>Safeguards MAGERIT vinculados</Label>
              <div className="flex flex-wrap gap-1">
                {entry.magerit_safeguards.map((sg) => (
                  <Badge key={sg} variant="outline" className="text-[10px]">
                    {sg}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={updateMutation.isPending}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={updateMutation.isPending || !justificacionValid}
            data-testid="dda-edit-save"
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="mr-1.5 size-3 animate-spin" />
                Guardando…
              </>
            ) : (
              <>
                <Save className="mr-1.5 size-3" />
                Guardar cambios
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
