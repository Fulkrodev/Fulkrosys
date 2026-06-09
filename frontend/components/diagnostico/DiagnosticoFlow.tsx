/**
 * Diagnóstico previo · flujo del lead account-less (Batch B).
 *
 * Consume magic-link → consentimiento Art.13 (gate Batch A) → una pregunta por
 * pantalla con barra de progreso → gracias. Marca Fulkro existente (violeta
 * #6C63FF vía tokens primary · isotipo en el shell (public)). R29 friendly:
 * sin tecnicismos, sin presión, "sin prisa por tu parte".
 */
"use client";

import * as React from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import {
  type AnswerValue,
  type DiagnosticoAuth,
  type DiagnosticoQuestion,
  DiagnosticoError,
  consumeDiagnosticoToken,
  getConsentText,
  getNextQuestion,
  recordConsent,
  saveAnswer,
  submitDiagnostico,
} from "@/lib/api/diagnostico-precliente";

type Phase = "loading" | "consent" | "question" | "submitting" | "done" | "error";

export function DiagnosticoFlow({ token }: { token: string }) {
  const [phase, setPhase] = React.useState<Phase>("loading");
  const [auth, setAuth] = React.useState<DiagnosticoAuth | null>(null);
  const [consentText, setConsentText] = React.useState("");
  const [question, setQuestion] = React.useState<DiagnosticoQuestion | null>(null);
  const [progress, setProgress] = React.useState(0);
  const [errorMsg, setErrorMsg] = React.useState("");
  const [inflight, setInflight] = React.useState(false);

  // ── Arranque: consume el token + carga el texto de consentimiento ──
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const consumed = await consumeDiagnosticoToken(token);
        const a: DiagnosticoAuth = {
          sessionId: consumed.session_id,
          sessionSecret: consumed.session_secret,
        };
        const ct = await getConsentText(a);
        if (cancelled) return;
        setAuth(a);
        setConsentText(ct.text);
        setProgress(consumed.progress_percentage);
        setPhase("consent");
      } catch (e) {
        if (cancelled) return;
        setErrorMsg(describeError(e));
        setPhase("error");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const loadNext = React.useCallback(async (a: DiagnosticoAuth) => {
    const nq = await getNextQuestion(a);
    setProgress(nq.progress_percentage);
    if (nq.done || !nq.question) {
      setPhase("submitting");
      await submitDiagnostico(a);
      setPhase("done");
      return;
    }
    setQuestion(nq.question);
    setPhase("question");
  }, []);

  async function handleAccept() {
    if (!auth || inflight) return;
    setInflight(true);
    setErrorMsg("");
    try {
      await recordConsent(auth);
      await loadNext(auth);
    } catch (e) {
      setErrorMsg(describeError(e));
      setPhase("error");
    } finally {
      setInflight(false);
    }
  }

  async function handleAnswer(value: AnswerValue) {
    if (!auth || !question || inflight) return;
    setInflight(true);
    setErrorMsg("");
    try {
      await saveAnswer(auth, question.id, value);
      await loadNext(auth);
    } catch (e) {
      // 422 de validación → mensaje inline, permanece en la pregunta.
      if (e instanceof DiagnosticoError && e.status === 422) {
        setErrorMsg(e.message);
      } else {
        setErrorMsg(describeError(e));
        setPhase("error");
      }
    } finally {
      setInflight(false);
    }
  }

  // ───────────────────────────── render ─────────────────────────────
  if (phase === "loading") {
    return <Centered><Loader2 className="size-5 animate-spin text-fulkro-primary-500" /> <span className="text-sm text-fulkro-ink-500">Preparando tu cuestionario…</span></Centered>;
  }

  if (phase === "error") {
    return (
      <Card>
        <CardContent className="space-y-3 p-6 text-center">
          <p className="text-base font-semibold text-fulkro-ink-700">No hemos podido abrir el cuestionario</p>
          <p className="text-sm text-fulkro-ink-500">{errorMsg}</p>
          <p className="text-xs text-fulkro-ink-400">
            Si el enlace ha caducado, escríbenos y te enviamos uno nuevo. Sin prisa.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (phase === "done") {
    return (
      <Card>
        <CardContent className="space-y-4 p-8 text-center">
          <CheckCircle2 className="mx-auto size-12 text-fulkro-primary-500" />
          <p className="text-lg font-semibold text-fulkro-ink-700">¡Gracias! Lo tenemos.</p>
          <p className="text-sm text-fulkro-ink-500">
            Revisaremos tus respuestas con calma y te diremos, con criterio, si el ENS
            os aplica y por dónde empezaríais. Te contactamos en breve.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (phase === "consent") {
    return (
      <Card>
        <CardContent className="space-y-4 p-6">
          <h1 className="text-lg font-semibold text-fulkro-ink-700">
            Antes de empezar
          </h1>
          <p className="text-sm text-fulkro-ink-500">
            Es un cuestionario breve y sin tecnicismos. Primero, cómo tratamos tus datos:
          </p>
          <div className="max-h-64 overflow-y-auto rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-4 text-xs leading-relaxed text-fulkro-ink-600 whitespace-pre-line">
            {consentText}
          </div>
          {errorMsg && <p className="text-xs text-fulkro-danger">{errorMsg}</p>}
          <Button
            variant="primary"
            size="lg"
            className="w-full"
            onClick={() => void handleAccept()}
            disabled={inflight}
            data-testid="diagnostico-consent-accept"
          >
            {inflight ? <Loader2 className="size-4 animate-spin" /> : "Acepto y empiezo"}
          </Button>
          <p className="text-center text-[11px] text-fulkro-ink-400">
            Al continuar aceptas el tratamiento de tus datos descrito arriba.
          </p>
        </CardContent>
      </Card>
    );
  }

  // phase === "question" | "submitting"
  return (
    <div className="space-y-4">
      <Progress value={progress} aria-label="Progreso del cuestionario" />
      {question && (
        <QuestionScreen
          key={question.id}
          question={question}
          inflight={inflight || phase === "submitting"}
          errorMsg={errorMsg}
          onAnswer={handleAnswer}
        />
      )}
    </div>
  );
}

// ───────────────────────── pantalla de pregunta ─────────────────────────

function QuestionScreen({
  question,
  inflight,
  errorMsg,
  onAnswer,
}: {
  question: DiagnosticoQuestion;
  inflight: boolean;
  errorMsg: string;
  onAnswer: (value: AnswerValue) => void;
}) {
  const [text, setText] = React.useState("");
  const required = question.validation?.required ?? false;
  const maxLen = question.validation?.max_length ?? undefined;
  const minLen = question.validation?.min_length ?? undefined;
  const isFreeText =
    question.type === "text" ||
    question.type === "long_text" ||
    question.type === "email" ||
    question.type === "url" ||
    question.type === "number" ||
    question.type === "date";

  const trimmed = text.trim();
  const tooShort = minLen !== undefined && minLen > 0 && trimmed.length < minLen;
  const canSubmitText = (!required || trimmed.length > 0) && !tooShort;

  function submitText() {
    if (inflight || !canSubmitText) return;
    if (!trimmed && !required) {
      onAnswer(""); // opcional vacío
      return;
    }
    onAnswer(question.type === "number" ? Number(trimmed) : trimmed);
  }

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <div className="space-y-1.5">
          <p className="text-[11px] uppercase tracking-wider text-fulkro-primary-500">
            {sectionLabel(question.section)}
          </p>
          <h2 className="text-lg font-semibold leading-snug text-fulkro-ink-700">
            {question.label}
          </h2>
          {question.tooltip && (
            <p className="text-sm text-fulkro-ink-400">{question.tooltip}</p>
          )}
        </div>

        {/* single_select → tarjetas grandes tocables (tap = responder) */}
        {question.type === "single_select" && question.options && (
          <div className="space-y-2">
            {question.options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                disabled={inflight}
                onClick={() => onAnswer(opt.value)}
                data-testid={`diagnostico-option-${opt.value}`}
                className="flex w-full items-center justify-between rounded-xl border border-fulkro-ink-200 bg-white px-4 py-3.5 text-left text-sm font-medium text-fulkro-ink-700 transition-all hover:border-fulkro-primary-500 hover:bg-fulkro-primary-50 active:scale-[0.99] disabled:opacity-50"
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}

        {/* multi_select → tarjetas con toggle (no usado en precliente, soportado) */}
        {question.type === "multi_select" && question.options && (
          <MultiSelect
            options={question.options}
            inflight={inflight}
            onSubmit={(vals) => onAnswer(vals)}
          />
        )}

        {/* texto libre / número / email … */}
        {isFreeText && (
          <div className="space-y-2">
            {question.type === "long_text" ? (
              <Textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={question.placeholder ?? ""}
                maxLength={maxLen}
                rows={4}
                aria-label={question.label}
                autoFocus
              />
            ) : (
              <Input
                type={inputType(question.type)}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={question.placeholder ?? ""}
                maxLength={maxLen}
                aria-label={question.label}
                autoFocus
              />
            )}
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-fulkro-ink-400">
                {required ? "Necesario para continuar" : "Opcional"}
              </span>
              {maxLen && (
                <span className="text-[11px] text-fulkro-ink-400">
                  {text.length}/{maxLen}
                </span>
              )}
            </div>
            <div className="flex gap-2">
              {!required && (
                <Button
                  variant="ghost"
                  size="md"
                  className="flex-1"
                  disabled={inflight}
                  onClick={() => onAnswer("")}
                  data-testid="diagnostico-skip"
                >
                  Omitir
                </Button>
              )}
              <Button
                variant="primary"
                size="md"
                className="flex-1"
                disabled={inflight || !canSubmitText}
                onClick={submitText}
                data-testid="diagnostico-next"
              >
                {inflight ? <Loader2 className="size-4 animate-spin" /> : "Siguiente"}
              </Button>
            </div>
          </div>
        )}

        {errorMsg && <p className="text-xs text-fulkro-danger">{errorMsg}</p>}
      </CardContent>
    </Card>
  );
}

function MultiSelect({
  options,
  inflight,
  onSubmit,
}: {
  options: { value: string; label: string }[];
  inflight: boolean;
  onSubmit: (vals: string[]) => void;
}) {
  const [selected, setSelected] = React.useState<string[]>([]);
  const toggle = (v: string) =>
    setSelected((prev) =>
      prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v],
    );
  return (
    <div className="space-y-2">
      {options.map((opt) => {
        const on = selected.includes(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            disabled={inflight}
            onClick={() => toggle(opt.value)}
            className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left text-sm font-medium transition-all disabled:opacity-50 ${
              on
                ? "border-fulkro-primary-500 bg-fulkro-primary-50 text-fulkro-ink-700"
                : "border-fulkro-ink-200 bg-white text-fulkro-ink-700 hover:border-fulkro-primary-500"
            }`}
          >
            {opt.label}
            {on && <CheckCircle2 className="size-4 text-fulkro-primary-500" />}
          </button>
        );
      })}
      <Button
        variant="primary"
        size="md"
        className="w-full"
        disabled={inflight || selected.length === 0}
        onClick={() => onSubmit(selected)}
      >
        Siguiente
      </Button>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16">{children}</div>
  );
}

function inputType(t: DiagnosticoQuestion["type"]): string {
  if (t === "email") return "email";
  if (t === "number") return "number";
  if (t === "url") return "url";
  if (t === "date") return "date";
  return "text";
}

const SECTION_LABELS: Record<string, string> = {
  empresa: "Sobre tu empresa",
  sector_publico: "Relación con el sector público",
  situacion_actual: "Vuestra situación actual",
  tecnologia: "Vuestra tecnología",
  cierre: "Para terminar",
};

function sectionLabel(section: string): string {
  return SECTION_LABELS[section] ?? section;
}

function describeError(e: unknown): string {
  if (e instanceof DiagnosticoError) {
    if (e.status === 410) return "Este enlace ha caducado o ya no está disponible.";
    if (e.status === 401) return "El enlace no es válido.";
    return e.message;
  }
  return "Ha ocurrido un problema de conexión. Inténtalo de nuevo en un momento.";
}
