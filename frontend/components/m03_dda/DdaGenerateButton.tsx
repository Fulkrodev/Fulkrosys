/**
 * DdaGenerateButton · genera DdA inicial 73 entries · sub-atom 1.D.F.A v3.11.
 *
 * Visible cuando status.exists=false (DdA aún no creada).
 * Selecciona categoría sistema + responsable opcional · POST /dda/generate.
 */
"use client";

import * as React from "react";
import { Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

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

import { useGenerateDda } from "@/hooks/useDdaAdmin";
import type { DdaCategoriaSistema } from "@/lib/api/dda";

interface DdaGenerateButtonProps {
  projectId: string;
}

const CATEGORIA_OPTIONS: { value: DdaCategoriaSistema; label: string }[] = [
  { value: "BASICA", label: "BÁSICA · 19 medidas core" },
  { value: "MEDIA", label: "MEDIA · 44 medidas" },
  { value: "ALTA", label: "ALTA · 73 medidas (full Anexo II)" },
];

export function DdaGenerateButton({ projectId }: DdaGenerateButtonProps) {
  const [open, setOpen] = React.useState(false);
  const [category, setCategory] = React.useState<DdaCategoriaSistema>("MEDIA");
  const [responsable, setResponsable] = React.useState("");

  const generateMutation = useGenerateDda();

  const handleGenerate = () => {
    generateMutation.mutate(
      {
        project_id: projectId,
        system_category: category,
        responsable: responsable.trim() || null,
      },
      {
        onSuccess: (result) => {
          toast.success(
            `DdA generada · ${result.total_entries} entries · ${result.aplicables} aplicables.`,
          );
          setOpen(false);
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
    <>
      <Button
        type="button"
        variant="primary"
        onClick={() => setOpen(true)}
        data-testid="dda-generate-button"
      >
        <Sparkles className="mr-1.5 size-3.5" />
        Generar DdA
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="dda-generate-modal">
          <DialogHeader>
            <DialogTitle>Generar DdA inicial</DialogTitle>
            <DialogDescription>
              Crea las entries de la Declaración de Aplicabilidad según
              categoría del sistema (Anexo II RD 311/2022).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="dda-generate-category">
                Categoría del sistema <span className="text-red-600">*</span>
              </Label>
              <Select
                value={category}
                onValueChange={(v) => setCategory(v as DdaCategoriaSistema)}
              >
                <SelectTrigger
                  id="dda-generate-category"
                  data-testid="dda-generate-category-select"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIA_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="dda-generate-responsable">
                Responsable (opcional)
              </Label>
              <Input
                id="dda-generate-responsable"
                value={responsable}
                onChange={(e) => setResponsable(e.target.value)}
                placeholder="p.ej. CISO · DPO · RSEG"
                data-testid="dda-generate-responsable-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={generateMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleGenerate}
              disabled={generateMutation.isPending}
              data-testid="dda-generate-confirm"
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="mr-1.5 size-3 animate-spin" />
                  Generando…
                </>
              ) : (
                <>
                  <Sparkles className="mr-1.5 size-3" />
                  Generar entries
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
