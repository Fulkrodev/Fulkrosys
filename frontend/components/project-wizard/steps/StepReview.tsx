"use client";

import { CheckCircle2, ChevronLeft, Loader2, Sparkles } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ACTIVO_TIPO_LABELS,
  ARQUITECTURA_LABELS,
  CATEGORIA_LABELS,
  DPO_LABELS,
  EQUIPO_TI_LABELS,
  GEOGRAFIA_LABELS,
  IMPACT_LABELS,
  SECTOR_ENS_LABELS,
  TAMANO_EMPLEADOS_LABELS,
  TIPO_ORG_LABELS,
  type Step1DatosCliente,
  type Step2ContextoENS,
  type Step3CategoriaPreliminar,
  type Step4ActivosCriticos,
  type Step5FirstUser,
} from "@/lib/api/project-diagnostico";

interface StepReviewProps {
  state: {
    step1: Step1DatosCliente;
    step2: Step2ContextoENS;
    step3: Step3CategoriaPreliminar;
    step4: Step4ActivosCriticos;
    step5: Step5FirstUser;
  };
  isSubmitting: boolean;
  onBack: () => void;
  onConfirm: () => void;
}

export function StepReview({
  state,
  isSubmitting,
  onBack,
  onConfirm,
}: StepReviewProps) {
  const { step1, step2, step3, step4, step5 } = state;
  return (
    <div className="space-y-4" data-testid="step-review">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">Paso 6 · Revisar y crear</h2>
        <p className="text-sm text-muted-foreground">
          Confirma · al pulsar «Crear» se ejecuta una transacción atómica
          que crea cliente + proyecto + dimensiones + sistema M01 + activos
          MAGERIT + departamentos sugeridos + usuario portal. Si algo falla ·
          rollback completo.
        </p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Cliente</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p>
            <strong>{step1.razon_social}</strong> · CIF{" "}
            <code className="text-xs">{step1.cif}</code>
          </p>
          {step1.sector_industrial && (
            <p className="text-muted-foreground">
              Sector: {step1.sector_industrial}
            </p>
          )}
          {step1.web && (
            <p className="text-muted-foreground text-xs">{step1.web}</p>
          )}
          {step1.contacto_email && (
            <p className="text-muted-foreground text-xs">
              📧 {step1.contacto_email}
              {step1.persona_contacto && ` · ${step1.persona_contacto}`}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Contexto ENS</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-1 text-xs sm:grid-cols-2">
          <ReviewRow
            label="Sector ENS"
            value={SECTOR_ENS_LABELS[step2.sector_ens]}
          />
          <ReviewRow
            label="Tipo organización"
            value={TIPO_ORG_LABELS[step2.tipo_organizacion]}
          />
          <ReviewRow
            label="Empleados"
            value={TAMANO_EMPLEADOS_LABELS[step2.tamano_empleados]}
          />
          <ReviewRow label="Sites/oficinas" value={String(step2.sites_oficinas)} />
          <ReviewRow
            label="Equipo TI"
            value={EQUIPO_TI_LABELS[step2.equipo_ti_tamano]}
          />
          <ReviewRow label="DPO" value={DPO_LABELS[step2.dpo_designado]} />
          <ReviewRow
            label="Arquitectura"
            value={ARQUITECTURA_LABELS[step2.arquitectura_sistemas]}
          />
          <ReviewRow
            label="Geografía"
            value={GEOGRAFIA_LABELS[step2.geografia_operacion]}
          />
          <ReviewRow label="IT interno" value={step2.it_interno ? "Sí" : "No"} />
          <ReviewRow
            label="CISO interno"
            value={step2.ciso_interno ? "Sí" : "No"}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Categoría ENS preliminar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          <div className="flex items-center gap-2">
            <Badge
              variant={
                step3.categoria_preliminar === "ALTA"
                  ? "danger"
                  : step3.categoria_preliminar === "MEDIA"
                    ? "warning"
                    : "success"
              }
              className="text-sm"
            >
              {CATEGORIA_LABELS[step3.categoria_preliminar]}
            </Badge>
            <span className="text-muted-foreground">
              · Dimensiones ENS Anexo I
            </span>
          </div>
          <div className="grid gap-1 sm:grid-cols-5">
            {(
              Object.entries(step3.dims_anexo_i) as [string, "BAJO" | "MEDIO" | "ALTO"][]
            ).map(([key, value]) => (
              <div
                key={key}
                className="rounded-md border p-1 text-center"
                data-testid={`review-dim-${key}`}
              >
                <p className="text-[10px] uppercase text-muted-foreground">
                  {key}
                </p>
                <Badge
                  variant={
                    value === "ALTO"
                      ? "danger"
                      : value === "MEDIO"
                        ? "warning"
                        : "success"
                  }
                >
                  {IMPACT_LABELS[value]}
                </Badge>
              </div>
            ))}
          </div>
          {step3.justificacion && (
            <p className="rounded-md bg-fulkro-ink-50 p-2 text-muted-foreground italic">
              {step3.justificacion}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            Activos críticos ({step4.activos.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-xs">
          {step4.activos.length === 0 ? (
            <p className="italic text-muted-foreground">
              Sin activos · MAGERIT analysis NO se creará automáticamente
              (Marcos puede crearlo después en /magerit).
            </p>
          ) : (
            step4.activos.map((a, i) => (
              <div
                key={i}
                className="flex items-start justify-between gap-2 rounded-md border p-1.5"
              >
                <div>
                  <p className="font-medium">
                    ACT-{String(i + 1).padStart(3, "0")} · {a.nombre}
                  </p>
                  {a.descripcion && (
                    <p className="text-muted-foreground">{a.descripcion}</p>
                  )}
                </div>
                <Badge variant="outline">{ACTIVO_TIPO_LABELS[a.tipo]}</Badge>
              </div>
            ))
          )}
          {step4.dependencias_cloud.length > 0 && (
            <div className="pt-1">
              <p className="text-[10px] uppercase text-muted-foreground">
                Dependencias cloud
              </p>
              <div className="flex flex-wrap gap-1">
                {step4.dependencias_cloud.map((d) => (
                  <Badge key={d} variant="secondary">
                    {d}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Primer usuario portal</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-xs">
          <p>
            <strong>{step5.full_name}</strong>
            {step5.cargo && ` · ${step5.cargo}`}
          </p>
          <p className="text-muted-foreground">📧 {step5.email}</p>
          <Badge variant={step5.send_magic_link ? "success" : "warning"}>
            {step5.send_magic_link
              ? "Magic-link · email automático"
              : "Password temporal · transmitir por canal seguro"}
          </Badge>
        </CardContent>
      </Card>

      <Alert variant="info">
        <AlertTitle>Auto-seed atómico</AlertTitle>
        <AlertDescription>
          Al confirmar: <strong>1 cliente</strong> · <strong>1 proyecto</strong>{" "}
          · <strong>16 dimensiones</strong> Anexo L · <strong>1 sistema</strong>{" "}
          M01 + InformationType (5 dims ENS Anexo I) ·{" "}
          {step4.activos.length > 0 && (
            <>
              <strong>{step4.activos.length} activos</strong> MAGERIT initial ·
            </>
          )}{" "}
          <strong>departamentos sugeridos</strong> según categoría{" "}
          {CATEGORIA_LABELS[step3.categoria_preliminar]} ·{" "}
          <strong>1 usuario portal</strong>.
        </AlertDescription>
      </Alert>

      <div className="flex items-center justify-between gap-2 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          disabled={isSubmitting}
          data-testid="step6-back"
        >
          <ChevronLeft size={14} className="mr-1" />
          Atrás
        </Button>
        <Button
          onClick={onConfirm}
          disabled={isSubmitting}
          data-testid="step6-confirm"
        >
          {isSubmitting ? (
            <Loader2 size={14} className="mr-1 animate-spin" />
          ) : (
            <Sparkles size={14} className="mr-1" />
          )}
          {isSubmitting ? "Creando proyecto…" : "Crear cliente + proyecto"}
          {!isSubmitting && <CheckCircle2 size={14} className="ml-1" />}
        </Button>
      </div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2 border-b border-fulkro-ink-300/30 py-0.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
