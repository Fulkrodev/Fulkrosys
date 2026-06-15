"use client";

/**
 * /client-portal/magerit · cliente SIMPLIFIED · sub-atom 1.D.F.bis.III.A v3.11.
 *
 * Modelo "indispensable-cliente-only":
 *   - Cliente NO edita ni clasifica activos (Marcos opera análisis MAGERIT)
 *   - Cliente VE vista resumen activos identificados (read-only)
 *   - Cliente APORTA info adicional via "¿faltan activos críticos?" form
 *     → POST /portal/magerit/assets/{first_asset_id}/review con action="con_pregunta"
 *       (reuse endpoint existing · cliente nota = activos adicionales que conoce)
 *   - Cliente FIRMA validation final cuando Marcos marca ready_for_validation_sign
 *
 * R29 sostener: NO tabs analytic + NO filters review complex · cliente friendly
 * R30 inverso: NO admin lingo (severidad/valoración DICAT exposed) · solo lo
 * indispensable
 *
 * UI: Banner top + Summary card + Lista simple activos + Form aportar info +
 * Sign validation button.
 */
import { useState } from "react";
import { Briefcase, Info, MessageCircle, Send } from "lucide-react";
import { toast } from "sonner";

import { MageritSignValidationButton } from "@/components/client-portal/magerit/MageritSignValidationButton";
import { MageritSummaryCard } from "@/components/client-portal/magerit/MageritSummaryCard";
import { PageContainer } from "@/components/layout/PageContainer";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import { useMageritClient } from "@/hooks/useMageritClient";


const ASSET_TYPE_LABELS: Record<string, string> = {
  S: "Servicio",
  D: "Datos",
  SW: "Software",
  HW: "Hardware",
  COM: "Comunicaciones",
  SI: "Soportes",
  L: "Instalaciones",
  P: "Personal",
};


export default function ClientMageritPage() {
  const {
    loading,
    error,
    projectId,
    summary,
    assets,
    refetch,
    reviewAsset,
  } = useMageritClient();
  const [additionalInfo, setAdditionalInfo] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Sesión 3B-2B.8 Phase 1B · SSE subscribe admin → cliente sync
  useClientProjectEvents(projectId ?? null, {
    enabled: Boolean(projectId),
    onM02MageritUpdated: (evt) => {
      const nombre = evt.data.analysis_name ?? "el análisis MAGERIT";
      const totalAssets = evt.data.assets_count ?? 0;
      toast.success(
        `El consultor ha actualizado ${nombre} (${totalAssets} activos). Revisa los detalles más abajo.`,
      );
      void refetch();
    },
  });

  if (loading) {
    return (
      <PageContainer variant="app">
        <p className="text-sm text-[color:var(--fulkro-muted)]">
          Cargando inventario…
        </p>
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer variant="app">
        <Alert variant="danger">
          <AlertTitle>No se pudo cargar el inventario</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </PageContainer>
    );
  }

  if (!summary) {
    return (
      <PageContainer variant="app">
        <Alert>
          <Info className="size-4" />
          <AlertTitle>Marcos está preparando el análisis</AlertTitle>
          <AlertDescription>
            Cuando tu consultor termine de identificar los activos críticos te
            avisaremos para que aportes información adicional si lo consideras
            necesario.
          </AlertDescription>
        </Alert>
      </PageContainer>
    );
  }

  const handleAdditionalInfoSubmit = async () => {
    if (additionalInfo.trim().length < 10) {
      toast.error(
        "Cuéntanos un poco más (mínimo 10 caracteres) para que tu consultor pueda actuar.",
      );
      return;
    }
    // Reuse endpoint existing /assets/{id}/review con action=con_pregunta
    // El primer activo se usa como ancla · cliente nota = activos adicionales
    // que conoce. Pattern reuse · NO new endpoint backend.
    const anchor = assets[0];
    if (!anchor) {
      toast.error(
        "Aún no hay activos cargados · espera a que Marcos termine la primera carga.",
      );
      return;
    }
    setSubmitting(true);
    try {
      await reviewAsset(anchor.id, "con_pregunta", additionalInfo.trim());
      toast.success(
        "✓ Información enviada · Marcos la revisará y te avisará si necesita más detalle.",
      );
      setAdditionalInfo("");
    } catch (err) {
      toast.error(
        err instanceof Error
          ? err.message
          : "No se pudo enviar la información. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <PageContainer variant="app">
      <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-[color:var(--fulkro-title)]">
          Activos del análisis de riesgos
        </h1>
        <p className="text-sm leading-relaxed text-[color:var(--fulkro-muted)]">
          Tu consultor está analizando los riesgos del sistema. Aquí ves los{" "}
          <TooltipENS term="activo"><span className="underline decoration-dotted underline-offset-2">activos críticos</span></TooltipENS>{" "}
          identificados hasta ahora. Si conoces alguno adicional, cuéntanoslo
          abajo · cuando el análisis esté listo te pediremos validarlo.
        </p>
      </header>

      {/* Banner R30 inverso */}
      <Alert>
        <Info className="size-4" />
        <AlertTitle>Marcos opera el análisis técnico</AlertTitle>
        <AlertDescription>
          Tu papel es aportar información sobre tu organización · firmar las
          decisiones finales. La parte técnica (valoraciones, salvaguardas,
          cálculos de riesgo) la prepara tu consultor.
        </AlertDescription>
      </Alert>

      {/* Summary KPIs */}
      <MageritSummaryCard summary={summary} />

      {/* Lista activos read-only · sin filtros review · sin DICAT exposure */}
      <Card data-testid="magerit-cliente-assets-list">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Briefcase className="size-4 text-primary" />
            Activos identificados ({summary.total_assets})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {assets.length === 0 ? (
            <p className="text-sm italic text-[color:var(--fulkro-muted)]">
              Aún no hay activos cargados.
            </p>
          ) : (
            <ul className="space-y-2">
              {assets.slice(0, 30).map((asset) => (
                <li
                  key={asset.id}
                  className="flex items-start justify-between gap-3 rounded-md border bg-card px-3 py-2"
                  data-testid={`magerit-asset-row-${asset.code}`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{asset.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Badge variant="secondary" className="text-[10px]">
                        {asset.code}
                      </Badge>
                      <span className="text-[11px] text-foreground/70">
                        {ASSET_TYPE_LABELS[asset.asset_type_code] ??
                          asset.asset_type_code}
                      </span>
                    </div>
                  </div>
                </li>
              ))}
              {assets.length > 30 && (
                <p className="text-xs text-foreground/70 italic">
                  +{assets.length - 30} activos más · tu consultor los está
                  analizando.
                </p>
              )}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Form aportar info adicional · reuse endpoint /assets/{id}/review */}
      <Card data-testid="magerit-cliente-aportar-info">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <MessageCircle className="size-4 text-primary" />
            ¿Faltan activos críticos?
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-foreground/70">
            Si tu organización gestiona alguna información, servicio o sistema
            importante que no aparece arriba, cuéntanoslo. Tu consultor lo
            incluirá en el análisis.
          </p>
          <div className="space-y-1.5">
            <Label htmlFor="magerit-info-textarea">
              Cuéntanos qué activos críticos adicionales conoces
            </Label>
            <Textarea
              id="magerit-info-textarea"
              rows={4}
              value={additionalInfo}
              onChange={(e) => setAdditionalInfo(e.target.value)}
              placeholder="p.ej. también gestionamos una base de datos de proveedores externa en Azure · contratos firmados en DocuSign · etc."
              disabled={submitting}
              data-testid="magerit-info-textarea"
            />
          </div>
          <Button
            type="button"
            onClick={handleAdditionalInfoSubmit}
            disabled={
              submitting ||
              additionalInfo.trim().length < 10 ||
              assets.length === 0
            }
            data-testid="magerit-info-submit"
          >
            <Send className="mr-1.5 size-3.5" />
            {submitting ? "Enviando…" : "Enviar a Marcos"}
          </Button>
        </CardContent>
      </Card>

      {/* Firma final · sostener · solo cuando Marcos marca ready */}
      {summary.ready_for_validation_sign &&
        !summary.last_signed_at &&
        projectId && (
          <Card data-testid="magerit-cliente-sign-final">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">
                Validar el análisis de riesgos
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-foreground/70">
                Tu consultor terminó el análisis. Cuando lo revises y estés
                conforme, firma para que quede como decisión final auditable.
              </p>
              <MageritSignValidationButton
                projectId={projectId}
                totalAssets={summary.total_assets}
                totalRisks={summary.total_risks}
                ready={summary.ready_for_validation_sign}
                onSigningComplete={() => void refetch()}
              />
            </CardContent>
          </Card>
        )}
      </div>
    </PageContainer>
  );
}
