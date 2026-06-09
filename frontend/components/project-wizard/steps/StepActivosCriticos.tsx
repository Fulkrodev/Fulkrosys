"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  ACTIVO_TIPO_LABELS,
  type ActivoCritico,
  type ActivoTipo,
  type Step4ActivosCriticos,
} from "@/lib/api/project-diagnostico";

interface StepActivosCriticosProps {
  initialValue: Step4ActivosCriticos | null;
  onSubmit: (data: Step4ActivosCriticos) => void;
  onBack: () => void;
}

const MAX_ACTIVOS = 10;
const MAX_DEPENDENCIAS = 20;

export function StepActivosCriticos({
  initialValue,
  onSubmit,
  onBack,
}: StepActivosCriticosProps) {
  const [activos, setActivos] = useState<ActivoCritico[]>(
    initialValue?.activos ?? [],
  );
  const [dependencias, setDependencias] = useState<string[]>(
    initialValue?.dependencias_cloud ?? [],
  );
  const [draftDependencia, setDraftDependencia] = useState("");
  const [draftActivo, setDraftActivo] = useState<ActivoCritico>({
    nombre: "",
    tipo: "datos",
    descripcion: "",
  });

  const addActivo = () => {
    if (!draftActivo.nombre.trim()) return;
    if (activos.length >= MAX_ACTIVOS) return;
    setActivos((arr) => [
      ...arr,
      {
        nombre: draftActivo.nombre.trim(),
        tipo: draftActivo.tipo,
        descripcion: draftActivo.descripcion?.trim() || null,
      },
    ]);
    setDraftActivo({ nombre: "", tipo: "datos", descripcion: "" });
  };

  const removeActivo = (index: number) => {
    setActivos((arr) => arr.filter((_, i) => i !== index));
  };

  const addDependencia = () => {
    const v = draftDependencia.trim();
    if (!v || dependencias.length >= MAX_DEPENDENCIAS) return;
    if (dependencias.includes(v)) return;
    setDependencias((arr) => [...arr, v]);
    setDraftDependencia("");
  };

  const removeDependencia = (dep: string) => {
    setDependencias((arr) => arr.filter((d) => d !== dep));
  };

  return (
    <div className="space-y-4" data-testid="step-activos">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">
          Paso 4 · <TooltipENS term="activo" text="" />
          Activos críticos top 10
        </h2>
        <p className="text-sm text-muted-foreground">
          Identifica activos más importantes para tu organización. Seedearemos
          un análisis <TooltipENS term="MAGERIT" /> inicial con valor por
          defecto medio (5/10) en las 5 dimensiones ENS. Podrás editarlos
          después en la página MAGERIT.
        </p>
      </div>

      {/* Add activo form */}
      <Card>
        <CardContent className="space-y-2 p-3" data-testid="activo-form">
          <div className="grid gap-2 sm:grid-cols-3">
            <div className="flex flex-col gap-1 sm:col-span-2">
              <Label htmlFor="draft-activo-nombre">Nombre del activo</Label>
              <Input
                id="draft-activo-nombre"
                placeholder="Ej: Base datos clientes · Portal web · ERP financiero"
                value={draftActivo.nombre}
                onChange={(e) =>
                  setDraftActivo((d) => ({ ...d, nombre: e.target.value }))
                }
                data-testid="activo-nombre-input"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label htmlFor="draft-activo-tipo">Tipo</Label>
              <Select
                value={draftActivo.tipo}
                onValueChange={(v) =>
                  setDraftActivo((d) => ({ ...d, tipo: v as ActivoTipo }))
                }
              >
                <SelectTrigger id="draft-activo-tipo" data-testid="activo-tipo-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(ACTIVO_TIPO_LABELS) as ActivoTipo[]).map(
                    (t) => (
                      <SelectItem key={t} value={t}>
                        {ACTIVO_TIPO_LABELS[t]}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>
          <Input
            placeholder="Descripción opcional"
            value={draftActivo.descripcion ?? ""}
            onChange={(e) =>
              setDraftActivo((d) => ({ ...d, descripcion: e.target.value }))
            }
            data-testid="activo-descripcion-input"
          />
          <div className="flex justify-end">
            <Button
              size="sm"
              onClick={addActivo}
              disabled={
                !draftActivo.nombre.trim() || activos.length >= MAX_ACTIVOS
              }
              data-testid="activo-add-button"
            >
              <Plus size={14} className="mr-1" />
              Añadir activo
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* List activos */}
      <div className="space-y-2" data-testid="activos-list">
        {activos.length === 0 ? (
          <p className="rounded-md border p-3 text-center text-sm text-muted-foreground">
            Sin activos aún · puedes saltarte este paso · MAGERIT analysis NO
            se creará automáticamente.
          </p>
        ) : (
          activos.map((activo, i) => (
            <div
              key={`${activo.nombre}-${i}`}
              className="flex items-start justify-between gap-2 rounded-md border p-2"
              data-testid={`activo-row-${i}`}
            >
              <div className="flex-1 min-w-0">
                <p className="truncate text-sm font-medium">
                  ACT-{String(i + 1).padStart(3, "0")} · {activo.nombre}
                </p>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Badge variant="outline">{ACTIVO_TIPO_LABELS[activo.tipo]}</Badge>
                  {activo.descripcion && <span>· {activo.descripcion}</span>}
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => removeActivo(i)}
                data-testid={`activo-remove-${i}`}
              >
                <Trash2 size={14} />
              </Button>
            </div>
          ))
        )}
      </div>

      {/* Dependencias cloud */}
      <div className="space-y-2 rounded-md border p-3" data-testid="dependencias-section">
        <Label>Dependencias cloud / SaaS / ERP críticos</Label>
        <p className="text-[11px] text-muted-foreground">
          Proveedores tecnológicos críticos · AWS · Azure · GCP · Salesforce ·
          SAP · etc. Listalos para evaluar cadena suministro (
          <TooltipENS text="CCN-STIC 823 audita externalización + back-to-back DPA proveedores" />).
        </p>
        <div className="flex gap-2">
          <Input
            placeholder="Ej: AWS · Office 365 · Salesforce"
            value={draftDependencia}
            onChange={(e) => setDraftDependencia(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addDependencia();
              }
            }}
            data-testid="dependencia-input"
          />
          <Button
            size="sm"
            onClick={addDependencia}
            disabled={
              !draftDependencia.trim() ||
              dependencias.length >= MAX_DEPENDENCIAS
            }
            data-testid="dependencia-add"
          >
            <Plus size={14} />
          </Button>
        </div>
        <div className="flex flex-wrap gap-1">
          {dependencias.map((dep) => (
            <Badge
              key={dep}
              variant="secondary"
              className="cursor-pointer"
              onClick={() => removeDependencia(dep)}
              data-testid={`dependencia-${dep}`}
            >
              {dep} ×
            </Badge>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          data-testid="step4-back"
        >
          <ChevronLeft size={14} className="mr-1" />
          Atrás
        </Button>
        <Button
          onClick={() =>
            onSubmit({
              activos,
              dependencias_cloud: dependencias,
            })
          }
          data-testid="step4-next"
        >
          Siguiente
          <ChevronRight size={14} className="ml-1" />
        </Button>
      </div>
    </div>
  );
}
