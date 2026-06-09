"use client";

/**
 * ChangeRequestWizard · Sub-atom 1.D.D.B v3.11.
 *
 * Wizard 5 pasos solicitud de cambio · materialidad determinista R1.
 *
 *   1) Descripción + solicitante + fecha propuesta · POST intake
 *   2) Evaluación impacto · 10 preguntas binarias (matrix Anexo K)
 *   3) Materiality preview · POST assess + render score+level+required_*
 *   4) Notificación E-042 + acciones cliente + workflows pendientes
 *   5) Confirmación · change_id pinned + tracking link
 *
 * Backend reuse:
 *   POST /api/v1/changes/projects/{pid}/changes (intake)
 *   POST /api/v1/changes/projects/{pid}/changes/{cid}/assess
 *
 * R1 + R32 v3.11 + OPS-045 18ª sostenidos · NO inventa levels custom ·
 * usa MaterialityLevel canonical MINOR/RELEVANT/MATERIAL del materiality
 * engine determinista (NO LLM · trazabilidad ENAC).
 */
import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  GitBranch,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { Stepper } from "@/components/ui/stepper";
import { Textarea } from "@/components/ui/textarea";
import {
  type ChangeAssessmentOut,
  type ImpactQuestion,
  IMPACT_QUESTION_LABELS,
  IMPACT_QUESTIONS,
  MATERIALITY_LEVEL_LABELS,
  MATERIALITY_LEVEL_VARIANTS,
  changesApi,
} from "@/lib/api/changes";

interface ChangeRequestWizardProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCompleted?: () => void;
}

const STEPS = [
  { id: "descripcion", label: "Descripción" },
  { id: "impacto", label: "Evaluación impacto" },
  { id: "materiality", label: "Materiality" },
  { id: "notificacion", label: "Notificación" },
  { id: "tracking", label: "Tracking" },
];

export function ChangeRequestWizard({
  projectId,
  open,
  onOpenChange,
  onCompleted,
}: ChangeRequestWizardProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [description, setDescription] = useState("");
  const [requestedBy, setRequestedBy] = useState("marcos");
  const [proposedDate, setProposedDate] = useState("");
  const [answers, setAnswers] = useState<Record<ImpactQuestion, boolean>>(
    Object.fromEntries(IMPACT_QUESTIONS.map((q) => [q, false])) as Record<
      ImpactQuestion,
      boolean
    >,
  );
  const [changeId, setChangeId] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<ChangeAssessmentOut | null>(
    null,
  );

  useEffect(() => {
    if (!open) {
      setStepIndex(0);
      setDescription("");
      setRequestedBy("marcos");
      setProposedDate("");
      setAnswers(
        Object.fromEntries(
          IMPACT_QUESTIONS.map((q) => [q, false]),
        ) as Record<ImpactQuestion, boolean>,
      );
      setChangeId(null);
      setAssessment(null);
    }
  }, [open]);

  const intakeMutation = useMutation({
    mutationFn: () =>
      changesApi.intake(projectId, {
        description: description.trim(),
        requested_by: requestedBy.trim(),
        proposed_date: proposedDate.trim() || null,
      }),
    onSuccess: (result) => {
      setChangeId(result.change_id);
      setStepIndex(1);
      toast.success("Cambio registrado", {
        description: `#${result.change_id.slice(0, 8)} · ${result.state}`,
      });
      onCompleted?.();
    },
    onError: (err) => {
      toast.error("No se pudo registrar el cambio", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const assessMutation = useMutation({
    mutationFn: () => {
      if (!changeId) throw new Error("Falta change_id (paso 1)");
      return changesApi.assess(projectId, changeId, answers);
    },
    onSuccess: (result) => {
      setAssessment(result);
      setStepIndex(2);
      toast.success(`Materiality evaluada: ${result.materiality_level}`, {
        description: `Score ${result.materiality_score} / 100`,
      });
      onCompleted?.();
    },
    onError: (err) => {
      toast.error("No se pudo evaluar el impacto", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const canSubmitDescription =
    description.trim().length >= 10 && requestedBy.trim().length >= 2;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl"
        data-testid="change-request-wizard"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitBranch size={18} /> Solicitar cambio
          </DialogTitle>
          <DialogDescription>
            Wizard 5 pasos · materialidad determinista MINOR / RELEVANT /
            MATERIAL · trazabilidad ENAC.
          </DialogDescription>
        </DialogHeader>

        <Stepper steps={STEPS} currentIndex={stepIndex} className="my-2" />

        {stepIndex === 0 && (
          <StepDescription
            description={description}
            setDescription={setDescription}
            requestedBy={requestedBy}
            setRequestedBy={setRequestedBy}
            proposedDate={proposedDate}
            setProposedDate={setProposedDate}
          />
        )}

        {stepIndex === 1 && (
          <StepImpacto answers={answers} setAnswers={setAnswers} />
        )}

        {stepIndex === 2 && assessment && (
          <StepMateriality assessment={assessment} />
        )}

        {stepIndex === 3 && assessment && (
          <StepNotificacion assessment={assessment} />
        )}

        {stepIndex === 4 && assessment && changeId && (
          <StepTracking changeId={changeId} assessment={assessment} />
        )}

        <DialogFooter className="flex justify-between gap-2">
          <Button
            variant="outline"
            onClick={() =>
              stepIndex === 0
                ? onOpenChange(false)
                : setStepIndex((s) => Math.max(0, s - 1))
            }
            disabled={intakeMutation.isPending || assessMutation.isPending}
            data-testid="changes-wizard-back"
          >
            <ChevronLeft size={14} className="mr-1" />
            {stepIndex === 0 ? "Cancelar" : "Atrás"}
          </Button>
          {stepIndex === 0 && (
            <Button
              onClick={() => intakeMutation.mutate()}
              disabled={!canSubmitDescription || intakeMutation.isPending}
              data-testid="changes-wizard-submit-intake"
            >
              {intakeMutation.isPending ? (
                <Loader2 size={14} className="mr-1 animate-spin" />
              ) : (
                <ChevronRight size={14} className="mr-1" />
              )}
              Registrar y continuar
            </Button>
          )}
          {stepIndex === 1 && (
            <Button
              onClick={() => assessMutation.mutate()}
              disabled={assessMutation.isPending}
              data-testid="changes-wizard-submit-assess"
            >
              {assessMutation.isPending ? (
                <Loader2 size={14} className="mr-1 animate-spin" />
              ) : (
                <ChevronRight size={14} className="mr-1" />
              )}
              Evaluar impacto
            </Button>
          )}
          {(stepIndex === 2 || stepIndex === 3) && (
            <Button
              onClick={() => setStepIndex((s) => s + 1)}
              data-testid="changes-wizard-next"
            >
              Siguiente
              <ChevronRight size={14} className="ml-1" />
            </Button>
          )}
          {stepIndex === 4 && (
            <Button
              onClick={() => onOpenChange(false)}
              data-testid="changes-wizard-close"
            >
              <CheckCircle2 size={14} className="mr-1" />
              Finalizar
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function StepDescription({
  description,
  setDescription,
  requestedBy,
  setRequestedBy,
  proposedDate,
  setProposedDate,
}: {
  description: string;
  setDescription: (s: string) => void;
  requestedBy: string;
  setRequestedBy: (s: string) => void;
  proposedDate: string;
  setProposedDate: (s: string) => void;
}) {
  return (
    <div className="space-y-3" data-testid="wizard-step-descripcion">
      <p className="text-sm text-muted-foreground">
        Describe el cambio propuesto. Tras el intake se evalúa la
        materialidad y se disparan los workflows pertinentes.
      </p>
      <div className="space-y-1">
        <Label htmlFor="change-description">
          Descripción <span className="text-fulkro-warning">*</span> (mín. 10)
        </Label>
        <Textarea
          id="change-description"
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Migración de la base de datos de PostgreSQL 14 a 16..."
          data-testid="wizard-description-textarea"
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="change-requested-by">
          Solicitante <span className="text-fulkro-warning">*</span>
        </Label>
        <Input
          id="change-requested-by"
          value={requestedBy}
          onChange={(e) => setRequestedBy(e.target.value)}
          data-testid="wizard-requested-by"
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="change-proposed-date">
          Fecha propuesta (opcional)
        </Label>
        <Input
          id="change-proposed-date"
          type="date"
          value={proposedDate}
          onChange={(e) => setProposedDate(e.target.value)}
          data-testid="wizard-proposed-date"
        />
      </div>
    </div>
  );
}

function StepImpacto({
  answers,
  setAnswers,
}: {
  answers: Record<ImpactQuestion, boolean>;
  setAnswers: (a: Record<ImpactQuestion, boolean>) => void;
}) {
  return (
    <div
      className="max-h-[420px] space-y-2 overflow-y-auto"
      data-testid="wizard-step-impacto"
    >
      <p className="text-sm text-muted-foreground">
        Responde sí/no a cada pregunta. El motor determinista calcula la
        materialidad (NO LLM · trazabilidad ENAC).
      </p>
      {IMPACT_QUESTIONS.map((q) => (
        <button
          key={q}
          type="button"
          onClick={() =>
            setAnswers({ ...answers, [q]: !answers[q] })
          }
          className={`flex w-full items-center justify-between gap-3 rounded-md border p-3 text-left transition-colors ${
            answers[q]
              ? "border-fulkro-warning bg-fulkro-warning/10"
              : "border-fulkro-ink-300/40 hover:bg-fulkro-surface-glass"
          }`}
          data-testid={`wizard-question-${q}`}
        >
          <span className="text-sm">{IMPACT_QUESTION_LABELS[q]}</span>
          <Badge variant={answers[q] ? "warning" : "secondary"}>
            {answers[q] ? "Sí" : "No"}
          </Badge>
        </button>
      ))}
    </div>
  );
}

function StepMateriality({
  assessment,
}: {
  assessment: ChangeAssessmentOut;
}) {
  return (
    <div className="space-y-3" data-testid="wizard-step-materiality">
      <p className="text-sm text-muted-foreground">
        Resultado del materiality engine determinista.
      </p>
      <div className="grid grid-cols-2 gap-3 rounded-md border p-4">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase text-muted-foreground">
            Nivel
          </span>
          <Badge
            variant={MATERIALITY_LEVEL_VARIANTS[assessment.materiality_level]}
            data-testid="wizard-materiality-level"
          >
            {MATERIALITY_LEVEL_LABELS[assessment.materiality_level]}
          </Badge>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase text-muted-foreground">
            Score (0-100)
          </span>
          <span
            className="text-3xl font-bold"
            data-testid="wizard-materiality-score"
          >
            {assessment.materiality_score}
          </span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase text-muted-foreground">
            Plazo deadline
          </span>
          <span>{assessment.deadline_policy}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold uppercase text-muted-foreground">
            Firmantes
          </span>
          <span>{assessment.required_signoffs.join(" · ") || "—"}</span>
        </div>
      </div>

      <div className="rounded-md border p-3 text-sm">
        <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
          Documentos requeridos
        </p>
        <div className="flex flex-wrap gap-1.5">
          {assessment.required_documents.map((doc) => (
            <Badge
              key={doc}
              variant="outline"
              data-testid={`wizard-required-doc-${doc}`}
            >
              {doc}
            </Badge>
          ))}
        </div>
      </div>

      <div className="rounded-md border p-3 text-sm">
        <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
          Workflows requeridos
        </p>
        {assessment.required_workflows.length === 0 ? (
          <span className="text-muted-foreground">
            Ninguno · cambio MINOR sin workflow disparado.
          </span>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {assessment.required_workflows.map((w) => (
              <Badge
                key={w}
                variant="warning"
                data-testid={`wizard-required-workflow-${w}`}
              >
                {w.replace(/_/g, " ")}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StepNotificacion({
  assessment,
}: {
  assessment: ChangeAssessmentOut;
}) {
  return (
    <div className="space-y-3" data-testid="wizard-step-notificacion">
      <Alert variant="info">
        <AlertTitle>Notificación E-042 al cliente</AlertTitle>
        <AlertDescription>
          Tras la aprobación se generará automáticamente el documento{" "}
          <code>E-042</code> (notificación cambio) con la descripción y nivel
          de materialidad para el cliente.
        </AlertDescription>
      </Alert>

      {assessment.customer_actions.length > 0 && (
        <div className="rounded-md border p-3" data-testid="customer-actions">
          <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
            Acciones del cliente
          </p>
          <ul className="list-inside list-disc space-y-1 text-sm">
            {assessment.customer_actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-md border bg-fulkro-success/5 p-3 text-sm">
        <p className="mb-1 text-xs font-semibold uppercase text-muted-foreground">
          Firmantes requeridos
        </p>
        <div className="flex flex-wrap gap-1.5">
          {assessment.required_signoffs.map((s) => (
            <Badge key={s} variant="success">
              {s}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}

function StepTracking({
  changeId,
  assessment,
}: {
  changeId: string;
  assessment: ChangeAssessmentOut;
}) {
  return (
    <div className="space-y-3" data-testid="wizard-step-tracking">
      <Alert variant="success">
        <AlertTitle>Cambio registrado y evaluado</AlertTitle>
        <AlertDescription>
          Puedes consultar el detalle desde la lista (click en la fila) o
          desde la API <code>GET /api/v1/changes/projects/.../impact</code>.
        </AlertDescription>
      </Alert>
      <div className="rounded-md border p-3 text-sm">
        <p className="text-xs font-semibold uppercase text-muted-foreground">
          ID del cambio
        </p>
        <code
          className="break-all font-mono text-xs"
          data-testid="wizard-tracking-change-id"
        >
          {changeId}
        </code>
      </div>
      <div className="rounded-md border p-3 text-sm">
        <p className="text-xs font-semibold uppercase text-muted-foreground">
          Materiality final
        </p>
        <div className="mt-1 flex items-center gap-2">
          <Badge
            variant={
              MATERIALITY_LEVEL_VARIANTS[assessment.materiality_level]
            }
          >
            {MATERIALITY_LEVEL_LABELS[assessment.materiality_level]}
          </Badge>
          <span>Score {assessment.materiality_score} / 100</span>
        </div>
      </div>
    </div>
  );
}
