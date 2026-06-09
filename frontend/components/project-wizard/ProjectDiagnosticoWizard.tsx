"use client";

/**
 * ProjectDiagnosticoWizard · sub-atom 1.D.F.0.A v3.11.
 *
 * Entry point único `/admin/projects/new` · wizard 6 steps que recopila
 * info inicial cliente + contexto ENS + categoría preliminar + activos
 * críticos + primer user portal · backend atomic POST crea cliente +
 * proyecto + dims + M01 system + M02 magerit + departments + cockpit
 * user en 1 transacción.
 *
 * Reusable Stepper + react-hook-form + zod + TooltipENS.
 * R23 sostener firmísimo · admin-only (require_owner backend).
 * R30 sostener · tooltips ENS asume cero conocimiento ENS Marcos.
 */
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Loader2, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Stepper } from "@/components/ui/stepper";
import {
  projectDiagnosticoApi,
  type CreateProjectDiagnosticoRequest,
  type Step1DatosCliente,
  type Step2ContextoENS,
  type Step3CategoriaPreliminar,
  type Step4ActivosCriticos,
  type Step5FirstUser,
} from "@/lib/api/project-diagnostico";

import { StepActivosCriticos } from "./steps/StepActivosCriticos";
import { StepCategoriaPreliminar } from "./steps/StepCategoriaPreliminar";
import { StepContextoENS } from "./steps/StepContextoENS";
import { StepDatosCliente } from "./steps/StepDatosCliente";
import { StepFirstUser } from "./steps/StepFirstUser";
import { StepReview } from "./steps/StepReview";

const STEPS = [
  { id: "datos", label: "Datos cliente" },
  { id: "contexto", label: "Contexto ENS" },
  { id: "categoria", label: "Categoría preliminar" },
  { id: "activos", label: "Activos críticos" },
  { id: "usuario", label: "Primer usuario" },
  { id: "review", label: "Revisar y crear" },
];

type WizardState = {
  step1: Step1DatosCliente | null;
  step2: Step2ContextoENS | null;
  step3: Step3CategoriaPreliminar | null;
  step4: Step4ActivosCriticos | null;
  step5: Step5FirstUser | null;
};

const INITIAL_STATE: WizardState = {
  step1: null,
  step2: null,
  step3: null,
  step4: null,
  step5: null,
};

export function ProjectDiagnosticoWizard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const leadId = searchParams?.get("lead_id") ?? null;
  const [index, setIndex] = useState(0);
  const [state, setState] = useState<WizardState>(INITIAL_STATE);
  const [seeded, setSeeded] = useState(false);

  // #7.5 · hidratación desde lead: prerellena el Step 1 con los datos del lead.
  const prefillQuery = useQuery({
    queryKey: ["wizard-prefill", leadId],
    queryFn: () => projectDiagnosticoApi.prefillFromLead(leadId as string),
    enabled: !!leadId,
  });

  useEffect(() => {
    if (!prefillQuery.data || seeded) return;
    const p = prefillQuery.data;
    setState((s) => ({
      ...s,
      step1: {
        razon_social: p.razon_social ?? "",
        cif: p.cif ?? "",
        sector_industrial: p.sector_industrial ?? null,
        domicilio_fiscal: null,
        web: null,
        contacto_email: p.contacto_email ?? null,
        contacto_telefono: p.contacto_telefono ?? null,
        persona_contacto: null,
      },
    }));
    setSeeded(true);
  }, [prefillQuery.data, seeded]);

  const submitMutation = useMutation({
    mutationFn: () => {
      if (
        !state.step1 ||
        !state.step2 ||
        !state.step3 ||
        !state.step4 ||
        !state.step5
      ) {
        throw new Error("Wizard incompleto · faltan steps");
      }
      const payload: CreateProjectDiagnosticoRequest = {
        step1_datos_cliente: state.step1,
        step2_contexto_ens: state.step2,
        step3_categoria: state.step3,
        step4_activos: state.step4,
        step5_first_user: state.step5,
        lead_id: leadId,
      };
      return projectDiagnosticoApi.createProjectWithDiagnosis(payload);
    },
    onSuccess: (result) => {
      toast.success("Diagnóstico ENS completado", {
        description: result.summary,
        duration: 8000,
      });
      router.push(`/admin/projects/${result.project_id}/summary`);
    },
    onError: (err) => {
      toast.error("No se pudo crear el proyecto", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const goNext = () => setIndex((i) => Math.min(i + 1, STEPS.length - 1));
  const goBack = () => setIndex((i) => Math.max(i - 1, 0));

  // #7.5 · espera el prefill antes de montar el Step 1 (RHF fija sus
  // defaultValues al montar · evita la carrera con la hidratación asíncrona).
  if (leadId && !seeded && !prefillQuery.isError) {
    return (
      <div className="mx-auto flex max-w-4xl items-center justify-center gap-2 p-12 text-sm text-muted-foreground">
        <Loader2 size={18} className="animate-spin" />
        Cargando datos del lead…
      </div>
    );
  }

  return (
    <div
      className="mx-auto flex max-w-4xl flex-col gap-6 p-4 sm:p-6"
      data-testid="project-diagnostico-wizard"
    >
      <header className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-fulkro-title">
          <Sparkles size={22} className="text-fulkro-primary-700" />
          Diagnóstico ENS · Nuevo proyecto
        </h1>
        <p className="text-sm text-muted-foreground">
          6 pasos · recopilamos info inicial · creamos cliente + proyecto +
          análisis MAGERIT inicial + sistema M01 + departamentos sugeridos +
          primer usuario portal · todo atómico (1 transacción).
        </p>
      </header>

      {seeded && prefillQuery.data && (
        <Alert>
          <AlertTitle>Datos prerellenados desde el lead</AlertTitle>
          <AlertDescription>
            Hemos rellenado los datos básicos a partir del lead · revísalos y
            completa el resto.
            {prefillQuery.data.has_lightweight_project
              ? " Este lead ya respondió el cuestionario previo: al crear, completaremos ese mismo proyecto (no se duplica)."
              : ""}
          </AlertDescription>
        </Alert>
      )}

      {leadId && prefillQuery.isError && (
        <Alert variant="danger">
          <AlertTitle>No se pudo cargar el lead</AlertTitle>
          <AlertDescription>
            Continúa rellenando el formulario manualmente.
          </AlertDescription>
        </Alert>
      )}

      <Stepper steps={STEPS} currentIndex={index} />

      <Card>
        <CardContent className="space-y-4 p-6">
          {index === 0 && (
            <StepDatosCliente
              initialValue={state.step1}
              onSubmit={(data) => {
                setState((s) => ({ ...s, step1: data }));
                goNext();
              }}
            />
          )}
          {index === 1 && state.step1 && (
            <StepContextoENS
              initialValue={state.step2}
              onSubmit={(data) => {
                setState((s) => ({ ...s, step2: data }));
                goNext();
              }}
              onBack={goBack}
            />
          )}
          {index === 2 && state.step2 && (
            <StepCategoriaPreliminar
              initialValue={state.step3}
              contextEns={state.step2}
              onSubmit={(data) => {
                setState((s) => ({ ...s, step3: data }));
                goNext();
              }}
              onBack={goBack}
            />
          )}
          {index === 3 && state.step3 && (
            <StepActivosCriticos
              initialValue={state.step4}
              onSubmit={(data) => {
                setState((s) => ({ ...s, step4: data }));
                goNext();
              }}
              onBack={goBack}
            />
          )}
          {index === 4 && state.step4 && (
            <StepFirstUser
              initialValue={state.step5}
              onSubmit={(data) => {
                setState((s) => ({ ...s, step5: data }));
                goNext();
              }}
              onBack={goBack}
            />
          )}
          {index === 5 &&
            state.step1 &&
            state.step2 &&
            state.step3 &&
            state.step4 &&
            state.step5 && (
              <StepReview
                state={{
                  step1: state.step1,
                  step2: state.step2,
                  step3: state.step3,
                  step4: state.step4,
                  step5: state.step5,
                }}
                isSubmitting={submitMutation.isPending}
                onBack={goBack}
                onConfirm={() => submitMutation.mutate()}
              />
            )}
        </CardContent>
      </Card>

      {submitMutation.isError && (
        <Alert variant="danger">
          <AlertTitle>Error creando proyecto</AlertTitle>
          <AlertDescription>
            {submitMutation.error instanceof Error
              ? submitMutation.error.message
              : "Error desconocido"}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}

// Re-export icons for step files convenience
export { ChevronLeft, ChevronRight, Loader2 };
