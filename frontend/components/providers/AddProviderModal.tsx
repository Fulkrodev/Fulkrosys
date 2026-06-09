"use client";

/**
 * AddProviderModal · alta proveedor con auto-detect cross-compliance preview.
 *
 * Form react-hook-form + zod. Realtime preview de gaps según type+criticality
 * (alineado con backend M14 service-layer detect_cross_compliance_gaps).
 */
import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

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
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useProviders } from "@/hooks/useProviders";
import type {
  Criticality,
  ProviderType,
} from "@/lib/admin-providers/api";

const schema = z.object({
  name: z.string().min(2, "Nombre requerido (mín. 2)").max(255),
  type: z.enum([
    "cloud",
    "saas",
    "on-prem",
    "staffing",
    "hardware",
    "consultoria",
  ]),
  scope: z.string().min(2, "Descripción del scope requerida").max(2000),
  criticality: z.enum(["CRITICO", "ALTO", "MEDIO", "BAJO"]),
});

type FormData = z.infer<typeof schema>;

interface AutoDetectPreview {
  framework: "ENS" | "GDPR" | "NIS2";
  article: string;
  hint: string;
}

function previewCrossCompliance(
  type: ProviderType,
  criticality: Criticality,
): AutoDetectPreview[] {
  const out: AutoDetectPreview[] = [];
  const highRisk = criticality === "CRITICO" || criticality === "ALTO";
  const cloudOrSaas = type === "cloud" || type === "saas";
  if (cloudOrSaas && highRisk) {
    out.push({
      framework: "ENS",
      article: "Art. 18",
      hint: "Encadenamiento medidas seguridad y nivel cumplimiento ENS.",
    });
    out.push({
      framework: "GDPR",
      article: "Art. 28",
      hint: "Encargado del tratamiento · cláusulas obligatorias RGPD.",
    });
  }
  if (type === "cloud" && criticality === "CRITICO") {
    out.push({
      framework: "NIS2",
      article: "Art. 21",
      hint: "Gestión riesgos cadena suministro · NIS2 transposición.",
    });
  }
  return out;
}

interface AddProviderModalProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AddProviderModal({
  projectId,
  open,
  onOpenChange,
}: AddProviderModalProps) {
  const ph = useProviders(projectId);
  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      type: "saas",
      scope: "",
      criticality: "MEDIO",
    },
  });

  const watchType = form.watch("type");
  const watchCrit = form.watch("criticality");
  const preview = React.useMemo(
    () => previewCrossCompliance(watchType, watchCrit),
    [watchType, watchCrit],
  );

  const onSubmit = async (values: FormData) => {
    try {
      const result = await ph.create.mutateAsync(values);
      toast.success(
        `${values.name} añadido · ${
          result.auto_detected_gaps.length
        } gap(s) cross-compliance detectados`,
      );
      form.reset();
      onOpenChange(false);
    } catch {
      toast.error("Error al añadir proveedor");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Añadir proveedor</DialogTitle>
          <DialogDescription>
            El backend detecta automáticamente cláusulas cross-compliance
            requeridas según tipo y criticidad.
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-4"
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="provider-name">Nombre</Label>
            <Input
              id="provider-name"
              {...form.register("name")}
              placeholder="AWS Spain · Microsoft 365 · Acme Consulting"
            />
            {form.formState.errors.name ? (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.name.message}
              </p>
            ) : null}
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label>Tipo</Label>
              <Select
                value={watchType}
                onValueChange={(v) => form.setValue("type", v as ProviderType)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cloud">Cloud (IaaS)</SelectItem>
                  <SelectItem value="saas">SaaS</SelectItem>
                  <SelectItem value="on-prem">On-Prem</SelectItem>
                  <SelectItem value="staffing">Staffing</SelectItem>
                  <SelectItem value="hardware">Hardware</SelectItem>
                  <SelectItem value="consultoria">Consultoría</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Criticidad</Label>
              <Select
                value={watchCrit}
                onValueChange={(v) =>
                  form.setValue("criticality", v as Criticality)
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CRITICO">CRÍTICO</SelectItem>
                  <SelectItem value="ALTO">ALTO</SelectItem>
                  <SelectItem value="MEDIO">MEDIO</SelectItem>
                  <SelectItem value="BAJO">BAJO</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="provider-scope">Scope (servicios prestados)</Label>
            <Textarea
              id="provider-scope"
              {...form.register("scope")}
              rows={3}
              placeholder="Hosting + base de datos + backups · datos clínicos cifrados…"
            />
            {form.formState.errors.scope ? (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.scope.message}
              </p>
            ) : null}
          </div>

          {/* Auto-detect preview realtime */}
          {preview.length > 0 ? (
            <div className="rounded-md border border-fulkro-warning/30 bg-fulkro-warning/5 p-3">
              <p className="mb-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-fulkro-warning">
                <AlertTriangle size={12} strokeWidth={2.4} />
                Cross-compliance detectado
              </p>
              <ul className="flex flex-col gap-1.5 text-xs">
                {preview.map((p, i) => (
                  <li key={i} className="flex flex-col gap-0.5">
                    <span className="font-bold text-fulkro-ink-700">
                      {p.framework} {p.article}{" "}
                      <TooltipENS
                        text={p.hint}
                        iconSize={11}
                      />
                    </span>
                    <span className="text-fulkro-ink-500">{p.hint}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button type="submit" variant="primary" disabled={ph.create.isPending}>
              {ph.create.isPending ? (
                <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
              ) : null}
              Añadir proveedor
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
