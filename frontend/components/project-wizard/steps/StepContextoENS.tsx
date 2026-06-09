"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { z } from "zod";

import { Button } from "@/components/ui/button";
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
  ARQUITECTURA_LABELS,
  DPO_LABELS,
  EQUIPO_TI_LABELS,
  GEOGRAFIA_LABELS,
  SECTOR_ENS_LABELS,
  TAMANO_EMPLEADOS_LABELS,
  TIPO_ORG_LABELS,
  type Arquitectura,
  type DpoDesignado,
  type EquipoTiTamano,
  type Geografia,
  type SectorEns,
  type Step2ContextoENS,
  type TamanoEmpleados,
  type TipoOrganizacion,
} from "@/lib/api/project-diagnostico";

const schema = z.object({
  sector_ens: z.enum([
    "aapp",
    "privado_licita_aapp",
    "privado_proveedor_aapp",
    "otros",
  ]),
  tipo_organizacion: z.enum(["pyme", "gran_empresa", "sector_publico", "ong"]),
  tamano_empleados: z.enum([
    "micro",
    "pequeno",
    "mediano",
    "grande",
    "enterprise",
  ]),
  sites_oficinas: z.coerce.number().int().min(1).max(999),
  it_interno: z.boolean(),
  ciso_interno: z.boolean(),
  dpo_designado: z.enum(["interno", "externo", "no_designado"]),
  equipo_ti_tamano: z.enum(["sin_equipo", "1_3", "4_10", "11_30", "gt30"]),
  geografia_operacion: z.enum(["spain", "ue", "global", "apac", "latam"]),
  arquitectura_sistemas: z.enum([
    "on_premise",
    "hibrido",
    "cloud_native",
    "multi_cloud",
    "hyperscaler",
  ]),
});

type FormValues = z.infer<typeof schema>;

interface StepContextoENSProps {
  initialValue: Step2ContextoENS | null;
  onSubmit: (data: Step2ContextoENS) => void;
  onBack: () => void;
}

export function StepContextoENS({
  initialValue,
  onSubmit,
  onBack,
}: StepContextoENSProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      sector_ens: initialValue?.sector_ens ?? "privado_licita_aapp",
      tipo_organizacion: initialValue?.tipo_organizacion ?? "pyme",
      tamano_empleados: initialValue?.tamano_empleados ?? "pequeno",
      sites_oficinas: initialValue?.sites_oficinas ?? 1,
      it_interno: initialValue?.it_interno ?? true,
      ciso_interno: initialValue?.ciso_interno ?? false,
      dpo_designado: initialValue?.dpo_designado ?? "no_designado",
      equipo_ti_tamano: initialValue?.equipo_ti_tamano ?? "1_3",
      geografia_operacion: initialValue?.geografia_operacion ?? "spain",
      arquitectura_sistemas:
        initialValue?.arquitectura_sistemas ?? "cloud_native",
    },
  });

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="space-y-4"
      data-testid="step-contexto-ens"
    >
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">
          Paso 2 · Contexto <TooltipENS term="ENS" />
        </h2>
        <p className="text-sm text-muted-foreground">
          Información que determinará obligaciones · alcance auditoría ·
          medidas mínimas <TooltipENS term="Anexo_II" />.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          id="sector_ens"
          label="Sector ENS"
          value={form.watch("sector_ens")}
          onValueChange={(v) => form.setValue("sector_ens", v as SectorEns)}
          options={
            Object.entries(SECTOR_ENS_LABELS) as [SectorEns, string][]
          }
          tooltip={
            <TooltipENS text="AAPP = Administración Pública directa · privado-licita = vende a AAPP en concursos · privado-proveedor = trabaja para una empresa que ya tiene AAPP · otros = sin contacto AAPP" />
          }
          dataTestid="field-sector-ens"
        />
        <SelectField
          id="tipo_organizacion"
          label="Tipo de organización"
          value={form.watch("tipo_organizacion")}
          onValueChange={(v) =>
            form.setValue("tipo_organizacion", v as TipoOrganizacion)
          }
          options={
            Object.entries(TIPO_ORG_LABELS) as [TipoOrganizacion, string][]
          }
          dataTestid="field-tipo-org"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          id="tamano_empleados"
          label="Tamaño en empleados"
          value={form.watch("tamano_empleados")}
          onValueChange={(v) =>
            form.setValue("tamano_empleados", v as TamanoEmpleados)
          }
          options={
            Object.entries(TAMANO_EMPLEADOS_LABELS) as [
              TamanoEmpleados,
              string,
            ][]
          }
          dataTestid="field-tamano-empleados"
        />
        <div className="flex flex-col gap-1">
          <Label htmlFor="sites_oficinas">Oficinas / sitios físicos</Label>
          <Input
            id="sites_oficinas"
            type="number"
            min={1}
            max={999}
            data-testid="field-sites"
            {...form.register("sites_oficinas", { valueAsNumber: true })}
          />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          id="equipo_ti_tamano"
          label="Tamaño del equipo TI"
          value={form.watch("equipo_ti_tamano")}
          onValueChange={(v) =>
            form.setValue("equipo_ti_tamano", v as EquipoTiTamano)
          }
          options={
            Object.entries(EQUIPO_TI_LABELS) as [EquipoTiTamano, string][]
          }
          dataTestid="field-equipo-ti"
        />
        <SelectField
          id="dpo_designado"
          label="DPO / Delegado Protección Datos"
          value={form.watch("dpo_designado")}
          onValueChange={(v) =>
            form.setValue("dpo_designado", v as DpoDesignado)
          }
          options={
            Object.entries(DPO_LABELS) as [DpoDesignado, string][]
          }
          tooltip={
            <TooltipENS text="DPO = Data Protection Officer · obligatorio si tratas datos sensibles a gran escala. Puede ser interno o servicio externo contratado." />
          }
          dataTestid="field-dpo"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <SelectField
          id="arquitectura_sistemas"
          label="Arquitectura predominante"
          value={form.watch("arquitectura_sistemas")}
          onValueChange={(v) =>
            form.setValue("arquitectura_sistemas", v as Arquitectura)
          }
          options={
            Object.entries(ARQUITECTURA_LABELS) as [Arquitectura, string][]
          }
          dataTestid="field-arquitectura"
        />
        <SelectField
          id="geografia_operacion"
          label="Geografía operación"
          value={form.watch("geografia_operacion")}
          onValueChange={(v) =>
            form.setValue("geografia_operacion", v as Geografia)
          }
          options={
            Object.entries(GEOGRAFIA_LABELS) as [Geografia, string][]
          }
          dataTestid="field-geografia"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <BooleanField
          id="it_interno"
          label="¿Tienen equipo TI interno propio?"
          checked={form.watch("it_interno")}
          onChange={(v) => form.setValue("it_interno", v)}
          dataTestid="field-it-interno"
        />
        <BooleanField
          id="ciso_interno"
          label={
            <>
              ¿<TooltipENS text="CISO = Chief Information Security Officer · responsable de seguridad de la información en la organización" />
              CISO interno designado?
            </>
          }
          checked={form.watch("ciso_interno")}
          onChange={(v) => form.setValue("ciso_interno", v)}
          dataTestid="field-ciso-interno"
        />
      </div>

      <div className="flex items-center justify-between gap-2 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          data-testid="step2-back"
        >
          <ChevronLeft size={14} className="mr-1" />
          Atrás
        </Button>
        <Button type="submit" data-testid="step2-next">
          Siguiente
          <ChevronRight size={14} className="ml-1" />
        </Button>
      </div>
    </form>
  );
}

function SelectField<T extends string>({
  id,
  label,
  value,
  onValueChange,
  options,
  tooltip,
  dataTestid,
}: {
  id: string;
  label: string;
  value: T;
  onValueChange: (v: string) => void;
  options: [T, string][];
  tooltip?: React.ReactNode;
  dataTestid?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id} className="flex items-center gap-1">
        <span>{label}</span>
        {tooltip}
      </Label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger id={id} data-testid={dataTestid}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map(([key, displayLabel]) => (
            <SelectItem key={key} value={key}>
              {displayLabel}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function BooleanField({
  id,
  label,
  checked,
  onChange,
  dataTestid,
}: {
  id: string;
  label: React.ReactNode;
  checked: boolean;
  onChange: (v: boolean) => void;
  dataTestid?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-2 rounded-md border p-3">
      <label htmlFor={id} className="flex-1 text-sm">
        {label}
      </label>
      <button
        id={id}
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? "bg-fulkro-primary-700" : "bg-fulkro-ink-300"
        }`}
        data-testid={dataTestid}
        aria-checked={checked}
        role="switch"
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}
