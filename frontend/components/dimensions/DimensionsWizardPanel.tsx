/**
 * DimensionsWizardPanel · admin page consolidada 19 dimensiones (1.C.D.A.0.2 v3.8).
 *
 * Wizard 5 steps + 1 resumen capturando 16 dims editables. Marcos completa
 * (con cliente o admin solo) · source of truth canónico.
 *
 * Pattern reusado: Stepper primitive · TooltipENS · react-hook-form + Zod.
 * R30 sostenido · tooltips ENS asume cero conocimiento técnico.
 */
"use client";

import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { ChevronLeft, ChevronRight, Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Stepper } from "@/components/ui/stepper";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  getProjectDimensions,
  updateProjectDimensions,
  type ProjectDimensionsRead,
} from "@/lib/api/dimensions";
import {
  APLICA_AI_ACT_LABELS,
  APLICA_DORA_LABELS,
  APLICA_NIS2_LABELS,
  ARQUITECTURA_LABELS,
  CertificacionPreviaEnum,
  COMPROMISO_LABELS,
  DIMENSION_TOOLTIPS,
  DimensionsWizardSchema,
  DPO_LABELS,
  EQUIPO_TI_LABELS,
  GEOGRAFIA_LABELS,
  HORAS_SEMANA_LABELS,
  MADUREZ_ENS_LABELS,
  MULTI_TENANCY_LABELS,
  PRESUPUESTO_LABELS,
  TAMANO_EMPLEADOS_LABELS,
  URGENCIA_LABELS,
  type DimensionsWizardFormValues,
} from "@/lib/schemas/dimensions";

const STEPS = [
  { id: "empresa", label: "Empresa básica" },
  { id: "madurez", label: "Madurez actual" },
  { id: "legales", label: "Marcos legales" },
  { id: "arquitectura", label: "Arquitectura" },
  { id: "operacional", label: "Operacional" },
  { id: "resumen", label: "Resumen" },
];

interface DimensionsWizardPanelProps {
  projectId: string;
}

export function DimensionsWizardPanel({ projectId }: DimensionsWizardPanelProps) {
  const [dims, setDims] = React.useState<ProjectDimensionsRead | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [stepIndex, setStepIndex] = React.useState(0);

  const form = useForm<DimensionsWizardFormValues>({
    resolver: zodResolver(DimensionsWizardSchema),
    defaultValues: {
      tamano_empleados: "pequeno",
      madurez_ens_actual: "L0",
      geografia_operacion: "spain",
      procesa_datos_sensibles_rgpd9: false,
      aplica_nis2: "no",
      aplica_dora: "no",
      aplica_ai_act: "no",
      dpo_designado: "no_designado",
      arquitectura_sistemas: "cloud_native",
      multi_tenancy: "single",
      equipo_ti_tamano: "1_3",
      certificaciones_previas: [],
      urgencia_certificacion: "6m",
      presupuesto_disponible: "estandar",
      compromiso_interno: "reactivo",
      horas_cliente_semana: "5_15h",
    },
  });

  React.useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getProjectDimensions(projectId)
      .then((data) => {
        if (cancelled) return;
        setDims(data);
        form.reset({
          tamano_empleados: data.tamano_empleados,
          madurez_ens_actual: data.madurez_ens_actual,
          geografia_operacion: data.geografia_operacion,
          procesa_datos_sensibles_rgpd9: data.procesa_datos_sensibles_rgpd9,
          aplica_nis2: data.aplica_nis2,
          aplica_dora: data.aplica_dora,
          aplica_ai_act: data.aplica_ai_act,
          dpo_designado: data.dpo_designado,
          arquitectura_sistemas: data.arquitectura_sistemas,
          multi_tenancy: data.multi_tenancy,
          equipo_ti_tamano: data.equipo_ti_tamano,
          certificaciones_previas: data.certificaciones_previas,
          urgencia_certificacion: data.urgencia_certificacion,
          presupuesto_disponible: data.presupuesto_disponible,
          compromiso_interno: data.compromiso_interno,
          horas_cliente_semana: data.horas_cliente_semana,
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, form]);

  const onSubmit = async (values: DimensionsWizardFormValues) => {
    setSaving(true);
    try {
      const updated = await updateProjectDimensions(projectId, values);
      setDims(updated);
      toast.success(
        `Dimensiones guardadas · ${updated.dims_captured_count}/${updated.dims_total} capturadas`,
      );
    } catch (err) {
      toast.error(
        `Error guardando · ${err instanceof Error ? err.message : String(err)}`,
      );
    } finally {
      setSaving(false);
    }
  };

  const goNext = () => setStepIndex((s) => Math.min(s + 1, STEPS.length - 1));
  const goPrev = () => setStepIndex((s) => Math.max(s - 1, 0));

  if (loading) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Cargando dimensiones del proyecto…
      </div>
    );
  }

  if (error || !dims) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Error cargando dimensiones</CardTitle>
          <CardDescription>{error ?? "Sin datos"}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">
            Dimensiones capturadas
          </p>
          <p className="text-2xl font-semibold">
            {dims.dims_captured_count}/{dims.dims_total}
          </p>
        </div>
        <div className="text-right text-sm text-muted-foreground">
          <p>
            Categoría: <span className="font-medium">{dims.categoria_objetivo ?? "—"}</span>
          </p>
          <p>
            Arquetipo: <span className="font-medium">{dims.archetype ?? "—"}</span>
          </p>
          <p>
            Fase: <span className="font-medium">{dims.fase}</span>
          </p>
        </div>
      </div>

      <Stepper steps={STEPS} currentIndex={stepIndex} />

      <Card>
        <CardContent className="space-y-6 pt-6">
          {stepIndex === 0 && (
            <Step1Empresa form={form} />
          )}
          {stepIndex === 1 && (
            <Step2Madurez form={form} />
          )}
          {stepIndex === 2 && (
            <Step3Legales form={form} />
          )}
          {stepIndex === 3 && (
            <Step4Arquitectura form={form} />
          )}
          {stepIndex === 4 && (
            <Step5Operacional form={form} />
          )}
          {stepIndex === 5 && (
            <Step6Resumen form={form} dims={dims} />
          )}
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={goPrev}
          disabled={stepIndex === 0 || saving}
        >
          <ChevronLeft className="mr-1 size-4" />
          Anterior
        </Button>

        {stepIndex < STEPS.length - 1 ? (
          <Button type="button" onClick={goNext} disabled={saving}>
            Siguiente
            <ChevronRight className="ml-1 size-4" />
          </Button>
        ) : (
          <Button
            type="button"
            onClick={form.handleSubmit(onSubmit)}
            disabled={saving}
          >
            {saving ? (
              <>
                <Loader2 className="mr-1 size-4 animate-spin" />
                Guardando…
              </>
            ) : (
              <>
                <Save className="mr-1 size-4" />
                Guardar dimensiones
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}

// ================================================================
// Steps · sub-components
// ================================================================

type WizardForm = ReturnType<typeof useForm<DimensionsWizardFormValues>>;

function FieldWithTooltip({
  field,
  label,
  children,
}: {
  field: string;
  label: string;
  children: React.ReactNode;
}) {
  const tooltip = DIMENSION_TOOLTIPS[field];
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5">
        <Label htmlFor={field}>{label}</Label>
        {tooltip ? <TooltipENS text={tooltip} side="right" /> : null}
      </div>
      {children}
    </div>
  );
}

function SelectField({
  form,
  name,
  options,
}: {
  form: WizardForm;
  name: keyof DimensionsWizardFormValues;
  options: Record<string, string>;
}) {
  const value = form.watch(name) as string;
  return (
    <Select
      value={value}
      onValueChange={(v) => form.setValue(name, v as never, { shouldDirty: true })}
    >
      <SelectTrigger id={name as string}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {Object.entries(options).map(([k, lbl]) => (
          <SelectItem key={k} value={k}>
            {lbl}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function Step1Empresa({ form }: { form: WizardForm }) {
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Información básica sobre la empresa y su perímetro operativo.
      </p>
      <FieldWithTooltip field="tamano_empleados" label="Tamaño empleados">
        <SelectField
          form={form}
          name="tamano_empleados"
          options={TAMANO_EMPLEADOS_LABELS}
        />
      </FieldWithTooltip>
      <FieldWithTooltip field="geografia_operacion" label="Geografía operación">
        <SelectField
          form={form}
          name="geografia_operacion"
          options={GEOGRAFIA_LABELS}
        />
      </FieldWithTooltip>
      <p className="text-xs italic text-muted-foreground">
        Categoría ENS y arquetipo se gestionan desde sus motores
        correspondientes (M01 categorización · m13 commercial / m_meetings).
      </p>
    </div>
  );
}

function Step2Madurez({ form }: { form: WizardForm }) {
  const opts = Object.values(CertificacionPreviaEnum.options);
  const currentCerts = form.watch("certificaciones_previas") as string[];

  const toggleCert = (cert: string, checked: boolean) => {
    const next = checked
      ? Array.from(new Set([...currentCerts, cert]))
      : currentCerts.filter((c) => c !== cert);
    form.setValue("certificaciones_previas", next, { shouldDirty: true });
  };

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Punto de partida del proyecto · ¿qué hay implementado ya?
      </p>
      <FieldWithTooltip field="madurez_ens_actual" label="Madurez ENS actual">
        <SelectField
          form={form}
          name="madurez_ens_actual"
          options={MADUREZ_ENS_LABELS}
        />
      </FieldWithTooltip>
      <FieldWithTooltip field="equipo_ti_tamano" label="Equipo TI">
        <SelectField
          form={form}
          name="equipo_ti_tamano"
          options={EQUIPO_TI_LABELS}
        />
      </FieldWithTooltip>
      <FieldWithTooltip field="dpo_designado" label="DPO designado">
        <SelectField form={form} name="dpo_designado" options={DPO_LABELS} />
      </FieldWithTooltip>
      <FieldWithTooltip
        field="certificaciones_previas"
        label="Certificaciones previas"
      >
        <div className="space-y-2">
          {opts.map((cert) => (
            <div key={cert} className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`cert-${cert}`}
                checked={currentCerts.includes(cert)}
                onChange={(e) => toggleCert(cert, e.target.checked)}
                className="size-4 rounded border-input"
              />
              <Label htmlFor={`cert-${cert}`} className="font-normal">
                {cert}
              </Label>
            </div>
          ))}
        </div>
      </FieldWithTooltip>
    </div>
  );
}

function Step3Legales({ form }: { form: WizardForm }) {
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Marcos legales aplicables más allá del ENS · adapta el workflow.
      </p>
      <FieldWithTooltip field="aplica_nis2" label="¿Aplica NIS2?">
        <SelectField form={form} name="aplica_nis2" options={APLICA_NIS2_LABELS} />
      </FieldWithTooltip>
      <FieldWithTooltip field="aplica_dora" label="¿Aplica DORA?">
        <SelectField form={form} name="aplica_dora" options={APLICA_DORA_LABELS} />
      </FieldWithTooltip>
      <FieldWithTooltip field="aplica_ai_act" label="¿Aplica AI Act?">
        <SelectField
          form={form}
          name="aplica_ai_act"
          options={APLICA_AI_ACT_LABELS}
        />
      </FieldWithTooltip>
      <FieldWithTooltip
        field="procesa_datos_sensibles_rgpd9"
        label="¿Procesa datos sensibles RGPD art.9?"
      >
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="procesa_datos_sensibles_rgpd9"
            checked={Boolean(form.watch("procesa_datos_sensibles_rgpd9"))}
            onChange={(e) =>
              form.setValue("procesa_datos_sensibles_rgpd9", e.target.checked, {
                shouldDirty: true,
              })
            }
            className="size-4 rounded border-input"
          />
          <Label
            htmlFor="procesa_datos_sensibles_rgpd9"
            className="font-normal"
          >
            Sí · procesa datos especiales (biométricos · salud · etc)
          </Label>
        </div>
      </FieldWithTooltip>
    </div>
  );
}

function Step4Arquitectura({ form }: { form: WizardForm }) {
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Modelo arquitectónico técnico · drives scope pentest + controles.
      </p>
      <FieldWithTooltip field="arquitectura_sistemas" label="Arquitectura sistemas">
        <SelectField
          form={form}
          name="arquitectura_sistemas"
          options={ARQUITECTURA_LABELS}
        />
      </FieldWithTooltip>
      <FieldWithTooltip field="multi_tenancy" label="Multi-tenancy">
        <SelectField
          form={form}
          name="multi_tenancy"
          options={MULTI_TENANCY_LABELS}
        />
      </FieldWithTooltip>
    </div>
  );
}

function Step5Operacional({ form }: { form: WizardForm }) {
  return (
    <div className="space-y-5">
      <p className="text-sm text-muted-foreground">
        Cadencia · plazos · compromiso. Drives velocidad implementación.
      </p>
      <FieldWithTooltip field="urgencia_certificacion" label="Urgencia certificación">
        <SelectField
          form={form}
          name="urgencia_certificacion"
          options={URGENCIA_LABELS}
        />
      </FieldWithTooltip>
      <FieldWithTooltip field="presupuesto_disponible" label="Presupuesto disponible">
        <SelectField
          form={form}
          name="presupuesto_disponible"
          options={PRESUPUESTO_LABELS}
        />
      </FieldWithTooltip>
      <FieldWithTooltip field="compromiso_interno" label="Compromiso interno cliente">
        <SelectField
          form={form}
          name="compromiso_interno"
          options={COMPROMISO_LABELS}
        />
      </FieldWithTooltip>
      <FieldWithTooltip field="horas_cliente_semana" label="Horas cliente / semana">
        <SelectField
          form={form}
          name="horas_cliente_semana"
          options={HORAS_SEMANA_LABELS}
        />
      </FieldWithTooltip>
    </div>
  );
}

function Step6Resumen({
  form,
  dims,
}: {
  form: WizardForm;
  dims: ProjectDimensionsRead;
}) {
  const v = form.getValues();
  const rows: Array<[string, string]> = [
    ["Tamaño empleados", TAMANO_EMPLEADOS_LABELS[v.tamano_empleados]],
    ["Geografía", GEOGRAFIA_LABELS[v.geografia_operacion]],
    ["Madurez ENS", MADUREZ_ENS_LABELS[v.madurez_ens_actual]],
    ["Equipo TI", EQUIPO_TI_LABELS[v.equipo_ti_tamano]],
    ["DPO", DPO_LABELS[v.dpo_designado]],
    [
      "Certificaciones previas",
      v.certificaciones_previas.length > 0
        ? v.certificaciones_previas.join(" · ")
        : "Ninguna",
    ],
    ["Aplica NIS2", APLICA_NIS2_LABELS[v.aplica_nis2]],
    ["Aplica DORA", APLICA_DORA_LABELS[v.aplica_dora]],
    ["Aplica AI Act", APLICA_AI_ACT_LABELS[v.aplica_ai_act]],
    [
      "Datos sensibles RGPD art.9",
      v.procesa_datos_sensibles_rgpd9 ? "Sí" : "No",
    ],
    ["Arquitectura", ARQUITECTURA_LABELS[v.arquitectura_sistemas]],
    ["Multi-tenancy", MULTI_TENANCY_LABELS[v.multi_tenancy]],
    ["Urgencia", URGENCIA_LABELS[v.urgencia_certificacion]],
    ["Presupuesto", PRESUPUESTO_LABELS[v.presupuesto_disponible]],
    ["Compromiso", COMPROMISO_LABELS[v.compromiso_interno]],
    ["Horas/semana", HORAS_SEMANA_LABELS[v.horas_cliente_semana]],
  ];

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Revisa las 16 dimensiones capturadas + 3 dims base (categoría · arquetipo ·
        fase). Click <strong>Guardar</strong> para persistir.
      </p>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
        {rows.map(([key, val]) => (
          <div key={key} className="flex flex-col">
            <dt className="text-xs font-medium uppercase text-muted-foreground">
              {key}
            </dt>
            <dd className="text-sm">{val}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
