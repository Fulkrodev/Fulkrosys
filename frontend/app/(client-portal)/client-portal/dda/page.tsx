"use client";

/**
 * /client-portal/dda · cliente SIMPLIFIED · sub-atom 1.D.F.bis.III.A v3.11.
 *
 * Modelo "indispensable-cliente-only":
 *   - Cliente NO marca aplicabilidad medidas (Marcos opera M03 DdA admin)
 *   - Cliente VE resumen DdA final preparada (read-only count)
 *   - Cliente FIRMA Ed25519 E-040 final cuando ready
 *   - Cliente puede ABRIR pregunta sobre cualquier medida (form simple)
 *
 * R29 sostener: NO filters family complex · NO review actions per medida · cliente friendly
 * R30 inverso: NO admin lingo · solo lo indispensable
 *
 * UI: Banner top + Summary card + Form pregunta simple + Sign final button.
 */
import { useState } from "react";
import { FileSignature, Info, MessageCircle, Send } from "lucide-react";
import { toast } from "sonner";

import { DdaSignFinalButton } from "@/components/client-portal/dda/DdaSignFinalButton";
import { DdaSummaryCard } from "@/components/client-portal/dda/DdaSummaryCard";
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useDdaClient } from "@/hooks/useDdaClient";

export default function ClientDdaPage() {
  const {
    loading,
    error,
    projectId,
    summary,
    entries,
    refetch,
    reviewEntry,
  } = useDdaClient();
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (loading) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <p className="text-sm text-[color:var(--fulkro-muted)]">
          Cargando <TooltipENS term="DdA" />…
        </p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <Alert variant="danger">
          <AlertTitle>No se pudo cargar la DdA</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </main>
    );
  }

  if (!summary) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 space-y-4">
        <Alert>
          <Info className="size-4" />
          <AlertTitle>Marcos está preparando la DdA</AlertTitle>
          <AlertDescription>
            La <TooltipENS term="DdA" /> es el documento donde tu consultor
            decide qué medidas del Esquema Nacional de Seguridad aplican a tu
            sistema. Te avisaremos cuando esté lista para revisar y firmar.
          </AlertDescription>
        </Alert>
      </main>
    );
  }

  const handleQuestionSubmit = async () => {
    if (question.trim().length < 10) {
      toast.error(
        "Escríbenos un poco más (mínimo 10 caracteres) para que Marcos pueda contestarte.",
      );
      return;
    }
    const anchor = entries[0];
    if (!anchor) {
      toast.error(
        "Aún no hay medidas cargadas · espera a que Marcos termine la DdA.",
      );
      return;
    }
    setSubmitting(true);
    try {
      await reviewEntry(anchor.id, "con_pregunta", question.trim());
      toast.success(
        "✓ Pregunta enviada · Marcos te responderá pronto desde el chat.",
      );
      setQuestion("");
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "No se pudo enviar la pregunta. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 space-y-6">
      <header className="space-y-2">
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-[color:var(--fulkro-title)]">
          <FileSignature className="size-6 text-primary" />
          <TooltipENS term="DdA">
            <span className="underline decoration-dotted underline-offset-2">
              Declaración de Aplicabilidad
            </span>
          </TooltipENS>{" "}
          <TooltipENS term="ENS" />
        </h1>
        <p className="text-sm leading-relaxed text-[color:var(--fulkro-muted)]">
          Tu consultor preparó la Declaración de Aplicabilidad con las medidas
          del Esquema Nacional de Seguridad (
          <TooltipENS term="RD_311_2022">
            <span className="underline decoration-dotted underline-offset-2">
              RD 311/2022
            </span>
          </TooltipENS>
          ) que aplican a tu sistema. Revisa el resumen y firma cuando estés
          conforme.
        </p>
      </header>

      {/* Banner R30 inverso */}
      <Alert>
        <Info className="size-4" />
        <AlertTitle>Marcos preparó las decisiones técnicas</AlertTitle>
        <AlertDescription>
          La selección de qué medidas aplican y cómo es decisión técnica de tu
          consultor. Tu papel es revisar el resumen, abrir preguntas si algo no
          queda claro · firmar el documento final cuando estés conforme.
        </AlertDescription>
      </Alert>

      {/* Summary card · KPIs read-only */}
      <DdaSummaryCard summary={summary} />

      <AgentSuggestionBanner
        slug="a11_auditor_virtual_check"
        pageUrl="/client-portal/dda"
        dismissKey="dda_auditor_dismissed"
      />

      {/* Form pregunta simple · reuse endpoint review con_pregunta */}
      <Card data-testid="dda-cliente-pregunta-form">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <MessageCircle className="size-4 text-primary" />
            ¿Alguna pregunta sobre la Declaración?
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-foreground/70">
            Si algo no queda claro · si una medida te genera dudas · si crees
            que falta o sobra algo, cuéntanoslo. Marcos te responderá desde el
            chat y ajustará la DdA si es necesario antes de firmar.
          </p>
          <div className="space-y-1.5">
            <Label htmlFor="dda-pregunta">Tu pregunta o comentario</Label>
            <Textarea
              id="dda-pregunta"
              rows={4}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="p.ej. no entiendo qué significa la medida sobre cifrado · ¿esto aplica al portátil de mi gerente? · ¿podemos delegar este control al proveedor X?"
              disabled={submitting}
              data-testid="dda-pregunta-textarea"
            />
          </div>
          <Button
            type="button"
            onClick={handleQuestionSubmit}
            disabled={
              submitting ||
              question.trim().length < 10 ||
              entries.length === 0
            }
            data-testid="dda-pregunta-submit"
          >
            <Send className="mr-1.5 size-3.5" />
            {submitting ? "Enviando…" : "Enviar a Marcos"}
          </Button>
        </CardContent>
      </Card>

      {/* Firma final · solo cuando Marcos marca ready */}
      {summary.ready_for_final_sign && !summary.last_signed_at && projectId && (
        <Card data-testid="dda-cliente-sign-final">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              Firmar la Declaración de Aplicabilidad
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-foreground/70">
              Tu consultor terminó la DdA. Cuando la revises y estés conforme,
              firma para que quede como decisión final auditable (
              <TooltipENS term="ENAC">
                <span className="underline decoration-dotted underline-offset-2">
                  ENAC
                </span>
              </TooltipENS>
              -ready).
            </p>
            <DdaSignFinalButton
              projectId={projectId}
              totalMeasures={summary.total_measures}
              ready={summary.ready_for_final_sign}
              onSigningComplete={() => void refetch()}
            />
          </CardContent>
        </Card>
      )}
    </main>
  );
}
