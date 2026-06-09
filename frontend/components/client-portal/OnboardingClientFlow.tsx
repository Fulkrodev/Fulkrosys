"use client";

import * as React from "react";
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  PartyPopper,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import {
  useFinishOnboarding,
  useNextQuestion,
  usePortalStatus,
  useSubmitAnswer,
} from "@/hooks/useOnboardingClient";
import type { PortalQuestion } from "@/lib/client-onboarding/api";

export interface OnboardingClientFlowProps {
  projectId: string;
  onOpenConnectors?: () => void;
  onOpenLMS?: () => void;
}

export function OnboardingClientFlow({
  projectId,
  onOpenConnectors,
  onOpenLMS,
}: OnboardingClientFlowProps) {
  const { data: status, isLoading: statusLoading } = usePortalStatus(projectId);
  const {
    data: nextQuestion,
    isLoading: nextLoading,
    refetch: refetchNext,
  } = useNextQuestion(projectId);
  const submitMutation = useSubmitAnswer(projectId);
  const finishMutation = useFinishOnboarding(projectId);

  const [answer, setAnswer] = React.useState<unknown>(null);

  const question = nextQuestion?.question ?? null;
  const done = nextQuestion?.done ?? false;

  // Reset local answer when question changes
  React.useEffect(() => {
    setAnswer(null);
  }, [question?.id]);

  const handleSubmit = () => {
    if (!question) return;
    if (question.validation.required && (answer === null || answer === undefined || answer === "")) {
      toast.warning("Esta pregunta es obligatoria");
      return;
    }
    submitMutation.mutate(
      { question_id: question.id, answer },
      {
        onSuccess: () => {
          void refetchNext();
        },
        onError: () => toast.error("Error guardando respuesta"),
      },
    );
  };

  const handleFinish = () => {
    finishMutation.mutate(undefined, {
      onSuccess: () => toast.success("Onboarding completado · gracias!"),
      onError: (err) => toast.error(`No se pudo finalizar: ${String(err)}`),
    });
  };

  if (statusLoading || nextLoading) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
        <Loader2 className="size-4 animate-spin" />
        Cargando wizard de onboarding…
      </div>
    );
  }

  if (!status) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Onboarding no disponible</CardTitle>
          <CardDescription>
            Marcos debe crear una sesión desde su panel admin antes de continuar.
            Te avisaremos cuando esté listo.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (done) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-fulkro-success">
            <PartyPopper className="size-5" />
            Onboarding completado
          </CardTitle>
          <CardDescription>
            Has respondido las {status.total_questions} preguntas. Marcos puede ahora
            avanzar el proyecto a la siguiente fase.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span>Progreso</span>
              <span className="font-mono">100%</span>
            </div>
            <div className="h-2 overflow-hidden rounded bg-fulkro-canvas">
              <div className="h-full w-full bg-fulkro-success" />
            </div>
          </div>
          <Button
            type="button"
            variant="primary"
            onClick={handleFinish}
            disabled={finishMutation.isPending}
          >
            {finishMutation.isPending ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Finalizando…
              </>
            ) : (
              <>
                <CheckCircle2 className="mr-2 size-4" />
                Finalizar onboarding
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <ProgressHeader
        answered={status.answered_questions}
        total={status.total_questions}
        section={nextQuestion?.current_section ?? null}
        remainingRequired={nextQuestion?.remaining_required ?? 0}
      />

      {question ? (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-2">
              <div>
                <CardTitle className="text-base">
                  {question.label}
                  {question.validation.required ? (
                    <span className="ml-1 text-fulkro-warning">*</span>
                  ) : null}
                </CardTitle>
                {question.tooltip ? (
                  <CardDescription className="mt-1">{question.tooltip}</CardDescription>
                ) : null}
                {question.example ? (
                  <p className="mt-1 text-xs italic text-fulkro-ink-500">
                    Ejemplo: {question.example}
                  </p>
                ) : null}
              </div>
              <Badge variant="outline">{question.section}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <QuestionInput
              question={question}
              value={answer}
              onChange={setAnswer}
            />
            <div className="flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="primary"
                onClick={handleSubmit}
                disabled={submitMutation.isPending}
              >
                {submitMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" />
                    Guardando…
                  </>
                ) : (
                  <>
                    Siguiente <ArrowRight className="ml-2 size-4" />
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <SidebarTasks
        onOpenConnectors={onOpenConnectors}
        onOpenLMS={onOpenLMS}
      />
    </div>
  );
}

function ProgressHeader({
  answered,
  total,
  section,
  remainingRequired,
}: {
  answered: number;
  total: number;
  section: string | null;
  remainingRequired: number;
}) {
  const pct = total > 0 ? Math.round((answered * 100) / total) : 0;
  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-fulkro-primary-700" />
            <span className="font-medium">
              Pregunta {answered + 1} de {total}
            </span>
            {section ? (
              <Badge variant="outline">{section}</Badge>
            ) : null}
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="font-mono">{pct}%</span>
            {remainingRequired > 0 ? (
              <Badge variant="warning">{remainingRequired} obligatorias restantes</Badge>
            ) : null}
          </div>
        </div>
        <div className="h-2 overflow-hidden rounded bg-fulkro-canvas">
          <div
            className={cn(
              "h-full transition-all",
              pct >= 90 ? "bg-fulkro-success" : "bg-fulkro-primary-700",
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: PortalQuestion;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  switch (question.type) {
    case "text":
    case "email":
    case "url":
      return (
        <Input
          type={question.type === "email" ? "email" : question.type === "url" ? "url" : "text"}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={question.placeholder ?? ""}
          maxLength={question.validation.max_length ?? undefined}
        />
      );
    case "long_text":
      return (
        <textarea
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={question.placeholder ?? ""}
          maxLength={question.validation.max_length ?? undefined}
          rows={4}
          className="w-full rounded border border-fulkro-ink-200 bg-white p-2 text-sm focus:border-fulkro-primary-700 focus:outline-none"
        />
      );
    case "number":
      return (
        <Input
          type="number"
          value={typeof value === "number" || typeof value === "string" ? String(value) : ""}
          onChange={(e) => {
            const n = e.target.value;
            onChange(n === "" ? null : Number(n));
          }}
          min={question.validation.min_value ?? undefined}
          max={question.validation.max_value ?? undefined}
        />
      );
    case "date":
      return (
        <Input
          type="date"
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );
    case "boolean":
      return (
        <div className="flex items-center gap-3">
          <label className="inline-flex cursor-pointer items-center gap-2">
            <input
              type="radio"
              name={`q-${question.id}`}
              checked={value === true}
              onChange={() => onChange(true)}
              className="size-4"
            />
            Sí
          </label>
          <label className="inline-flex cursor-pointer items-center gap-2">
            <input
              type="radio"
              name={`q-${question.id}`}
              checked={value === false}
              onChange={() => onChange(false)}
              className="size-4"
            />
            No
          </label>
        </div>
      );
    case "single_select":
      return (
        <div className="space-y-2">
          {(question.options ?? []).map((opt) => (
            <label
              key={opt.value}
              className="flex cursor-pointer items-center gap-2 rounded border border-fulkro-ink-200 p-2 hover:bg-fulkro-canvas"
            >
              <input
                type="radio"
                name={`q-${question.id}`}
                checked={value === opt.value}
                onChange={() => onChange(opt.value)}
                className="size-4"
              />
              <span className="text-sm">{opt.label}</span>
            </label>
          ))}
        </div>
      );
    case "multi_select": {
      const arr = Array.isArray(value) ? (value as string[]) : [];
      return (
        <div className="space-y-2">
          {(question.options ?? []).map((opt) => {
            const checked = arr.includes(opt.value);
            return (
              <label
                key={opt.value}
                className="flex cursor-pointer items-center gap-2 rounded border border-fulkro-ink-200 p-2 hover:bg-fulkro-canvas"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => {
                    onChange(
                      checked ? arr.filter((v) => v !== opt.value) : [...arr, opt.value],
                    );
                  }}
                  className="size-4"
                />
                <span className="text-sm">{opt.label}</span>
              </label>
            );
          })}
        </div>
      );
    }
    default:
      return (
        <Input
          value={typeof value === "string" ? value : ""}
          onChange={(e) => onChange(e.target.value)}
          placeholder={question.placeholder ?? ""}
        />
      );
  }
}

function SidebarTasks({
  onOpenConnectors,
  onOpenLMS,
}: {
  onOpenConnectors?: () => void;
  onOpenLMS?: () => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Otras tareas de onboarding</CardTitle>
        <CardDescription>
          Conecta tu workspace y completa los cursos asignados cuando quieras.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        {onOpenConnectors ? (
          <Button type="button" variant="outline" onClick={onOpenConnectors}>
            Conectar workspace
          </Button>
        ) : null}
        {onOpenLMS ? (
          <Button type="button" variant="outline" onClick={onOpenLMS}>
            Cursos asignados
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
