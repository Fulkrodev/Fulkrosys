"use client";

/**
 * /client-portal/dpc-anual · SAN-E v3.MB-6 atom 2.
 *
 * Declaración Protección Continuidad (DPC) anual · art.25 RD 311/2022 · CCN-STIC 806.
 *
 * Workflow Q1.C híbrida (review individual + firma única anual):
 *  1. Header anniversary + countdown
 *  2. Context section · 4 sub-sections expandables (SLA + Recovery + Incidents + Roadmap)
 *  3. Review actions (revisada_ok / con_pregunta / suggest_change)
 *  4. Sign button sticky bottom · SigningFlow step-up OTP
 *  5. History DPC anuales anteriores
 */
import { AlertCircle, CheckCircle2, Calendar, HelpCircle, Info, Lightbulb, Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { DpcAnualHeader } from "@/components/client-portal/dpc-anual/DpcAnualHeader";
import { DpcAnualSignButton } from "@/components/client-portal/dpc-anual/DpcAnualSignButton";
import { DpcContextSection } from "@/components/client-portal/dpc-anual/DpcContextSection";
import { PageContainer } from "@/components/layout/PageContainer";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useDpcAnualClient } from "@/hooks/useDpcAnualClient";
import { type DpcReviewAction } from "@/lib/api/dpc-anual";

export default function DpcAnualPage() {
  const {
    loading,
    error,
    declarations,
    currentDeclaration,
    currentDetail,
    reviewDeclaration,
    refetch,
  } = useDpcAnualClient();

  const [pendingAction, setPendingAction] = useState<DpcReviewAction | null>(
    null,
  );
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleAction = async (action: DpcReviewAction) => {
    if (!currentDeclaration) return;
    if (action === "revisada_ok") {
      setSubmitting(true);
      try {
        await reviewDeclaration(currentDeclaration.id, action);
        toast.success("DPC anual marcada como revisada");
      } catch {
        // toast viene del hook
      } finally {
        setSubmitting(false);
      }
      return;
    }
    setPendingAction(action);
    setNote(currentDeclaration.client_concerns_note ?? "");
  };

  const submitWithNote = async () => {
    if (!pendingAction || !currentDeclaration) return;
    if (note.trim().length < 5) {
      toast.error("La nota debe tener al menos 5 caracteres");
      return;
    }
    setSubmitting(true);
    try {
      await reviewDeclaration(currentDeclaration.id, pendingAction, note.trim());
      toast.success("DPC actualizada");
      setPendingAction(null);
    } catch {
      // toast viene del hook
    } finally {
      setSubmitting(false);
    }
  };

  const reviewed = currentDeclaration?.client_reviewed_at != null;
  const historicalSigned = declarations.filter(
    (d) => d.status === "signed" && d.id !== currentDeclaration?.id,
  );

  return (
    <PageContainer variant="reading">
      <div className="space-y-6 pb-32">
      <header className="space-y-2">
        <div className="flex items-center gap-2 text-fulkro-primary-700">
          <Calendar className="h-5 w-5" aria-hidden />
          <span className="text-xs uppercase tracking-wide font-semibold">
            Portal cliente · DPC anual
          </span>
        </div>
        <h1 className="text-2xl font-bold text-fulkro-ink-800">
          Declaración Protección Continuidad anual
        </h1>
        <p className="text-sm text-fulkro-ink-600 max-w-3xl">
          Tu consultor preparó la confirmación anual del estado de continuidad
          de tus servicios. Revisa las 4 secciones de contexto (SLA,
          recuperación, incidents y roadmap) · firma con{" "}
          <TooltipENS term="OTP" /> step-up cuando estés conforme. Requerido por
          el Art.25 del{" "}
          <TooltipENS term="RD_311_2022">
            <span className="underline decoration-dotted underline-offset-2">
              RD 311/2022
            </span>
          </TooltipENS>{" "}
          y la guía CCN-STIC 806.
        </p>
      </header>

      {/* Banner R30 inverso · 1.D.F.bis.III.B v3.11 */}
      <Alert data-testid="cliente-dpc-banner">
        <Info className="size-4" />
        <AlertTitle>Marcos preparó el DPC anual</AlertTitle>
        <AlertDescription>
          Tu consultor recopiló SLA, plan de recuperación, incidentes del año y
          roadmap de mejoras. Tu papel es revisar las 4 secciones · abrir
          pregunta o sugerir cambio si algo no encaja · firmar la declaración
          cuando estés conforme. La firma también aparece en{" "}
          <code>/firmas-hub</code>.
        </AlertDescription>
      </Alert>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {error && (
        <Card className="p-5 border-destructive/40 bg-destructive/5">
          <div className="flex items-start gap-2 text-sm">
            <AlertCircle
              className="h-5 w-5 mt-0.5 text-destructive flex-shrink-0"
              aria-hidden
            />
            <div>
              <div className="font-semibold text-destructive">
                Error cargando DPC anual
              </div>
              <p className="text-fulkro-ink-600 mt-1">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {!loading && !error && !currentDeclaration && declarations.length === 0 && (
        <Card className="p-5">
          <div className="text-sm text-fulkro-ink-600">
            Todavía no hay DPC anual programada. Se generará automáticamente
            30 días antes del aniversario de tu firma de Conformidad inicial.
          </div>
        </Card>
      )}

      {!loading && !error && currentDeclaration && currentDetail && (
        <>
          <DpcAnualHeader declaration={currentDeclaration} />

          <DpcContextSection detail={currentDetail} />

          {currentDeclaration.status !== "signed" && (
            <Card className="p-5">
              <div className="font-semibold text-sm text-fulkro-ink-800 mb-3">
                Revisión cliente
              </div>
              {reviewed && currentDeclaration.client_concerns_note && (
                <div className="text-xs text-fulkro-ink-600 mb-3 p-2 rounded bg-fulkro-ink-50 italic">
                  &ldquo;{currentDeclaration.client_concerns_note}&rdquo;
                </div>
              )}
              {pendingAction === null ? (
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant={reviewed ? "outline" : "primary"}
                    onClick={() => handleAction("revisada_ok")}
                    disabled={submitting}
                    data-testid="dpc-review-ok"
                  >
                    {submitting ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3 w-3" />
                    )}
                    <span className="ml-1.5">
                      {reviewed ? "Revisada OK" : "Marcar revisada OK"}
                    </span>
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAction("con_pregunta")}
                    disabled={submitting}
                  >
                    <HelpCircle className="h-3 w-3" />
                    <span className="ml-1.5">Tengo una pregunta</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleAction("suggest_change")}
                    disabled={submitting}
                  >
                    <Lightbulb className="h-3 w-3" />
                    <span className="ml-1.5">Sugerir cambio</span>
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder={
                      pendingAction === "con_pregunta"
                        ? "¿Qué duda tienes sobre la DPC anual?"
                        : "¿Qué cambio sugieres?"
                    }
                    rows={3}
                    className="text-sm"
                    maxLength={4000}
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={submitWithNote}
                      disabled={submitting || note.trim().length < 5}
                    >
                      {submitting && <Loader2 className="h-3 w-3 animate-spin" />}
                      Guardar
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setPendingAction(null);
                        setNote("");
                      }}
                      disabled={submitting}
                    >
                      Cancelar
                    </Button>
                  </div>
                </div>
              )}
            </Card>
          )}

          <DpcAnualSignButton
            declaration={currentDeclaration}
            reviewed={reviewed}
            onSigningComplete={refetch}
          />
        </>
      )}

      {historicalSigned.length > 0 && (
        <Card className="p-5">
          <div className="font-semibold text-sm text-fulkro-ink-800 mb-3">
            DPC anteriores firmadas
          </div>
          <ul className="space-y-2">
            {historicalSigned.map((d) => (
              <li
                key={d.id}
                className="flex items-center justify-between gap-3 text-sm"
              >
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-fulkro-success" aria-hidden />
                  <span className="font-mono">DPC {d.anniversary_year}</span>
                  <span className="text-fulkro-ink-500">
                    {d.signed_at && new Date(d.signed_at).toLocaleDateString("es-ES")}
                  </span>
                </div>
                <Badge variant="success">Firmada</Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}
      </div>
    </PageContainer>
  );
}
