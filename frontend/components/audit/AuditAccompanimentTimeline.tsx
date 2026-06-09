"use client";

/**
 * AuditAccompanimentTimeline · admin · Sesión 3B-4 Ejecutable 7.5 Phase 7.5.2.
 *
 * Pattern P-CL2-4 ENRICH project page existing /audit · NO new route.
 * Branch auto-derived per project.categoria_objetivo (BASICA → 7 states · MEDIA/ALTA → 11).
 * R30 admin tutor TooltipENS per fase.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  CheckCircle2,
  Circle,
  ChevronRight,
  Loader2,
  Upload,
} from "lucide-react";
import { useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  auditAccompanimentApi,
  type AccompanimentTimeline,
} from "@/lib/api/audit-accompaniment";

interface Props {
  projectId: string;
}

const BASICO_STATES = [
  "not_started",
  "declaration_drafted",
  "declaration_signed",
  "declaration_published",
  "ccn_communicated",
  "periodic_review_scheduled",
  "completed",
] as const;

const MEDIO_ALTO_STATES = [
  "not_started",
  "preparation",
  "docs_collected",
  "internal_audit_scheduled",
  "internal_audit_completed",
  "enac_audit_scheduled",
  "enac_audit_in_progress",
  "enac_findings_resolution",
  "enac_audit_passed",
  "certificate_issued",
  "biannual_renewal_scheduled",
] as const;

const STATE_LABELS: Record<string, string> = {
  not_started: "Sin iniciar",
  declaration_drafted: "Declaración borrador",
  declaration_signed: "Declaración firmada",
  declaration_published: "Declaración publicada",
  ccn_communicated: "Comunicado al CCN (AMPARO)",
  periodic_review_scheduled: "Revisión periódica programada",
  completed: "Ciclo completado",
  preparation: "Preparación",
  docs_collected: "Documentación recogida",
  internal_audit_scheduled: "Auditoría interna programada",
  internal_audit_completed: "Auditoría interna completada",
  enac_audit_scheduled: "Auditoría ENAC programada",
  enac_audit_in_progress: "Auditoría ENAC en curso",
  enac_findings_resolution: "Resolución de hallazgos ENAC",
  enac_audit_passed: "Auditoría ENAC aprobada",
  certificate_issued: "Certificado emitido",
  biannual_renewal_scheduled: "Renovación bianual programada",
};

const STATE_TUTOR_HINTS: Record<string, string> = {
  not_started: "Inicia el ciclo de acompañamiento post-implantación cuando el cliente esté listo.",
  declaration_drafted: "Redacta la autodeclaración ENS BÁSICO siguiendo CCN-STIC-808.",
  declaration_signed: "Cliente firma la declaración · subir PDF firmado a artifacts.",
  declaration_published: "Publicar declaración en sede electrónica del cliente · subir captura.",
  ccn_communicated: "Comunica la Declaración al CCN por AMPARO (canal oficial · trámite manual) y sube el acuse/justificante como constancia.",
  periodic_review_scheduled: "Programar revisión anual de la declaración · cliente confirma fecha.",
  completed: "Ciclo BÁSICO completado · cliente ha cumplido autodeclaración ENS.",
  preparation: "Preparar plan de implantación + recopilar evidencias.",
  docs_collected: "Documentación completa según Anexo II RD 311/2022 · subir índice.",
  internal_audit_scheduled: "Programar auditoría interna pre-ENAC · cliente acepta fecha.",
  internal_audit_completed: "Auditoría interna completada · informe revisado.",
  enac_audit_scheduled: "Acordar fecha con auditor ENAC externo · subir confirmación.",
  enac_audit_in_progress: "Auditoría ENAC en curso · soporte cliente durante la visita.",
  enac_findings_resolution: "Resolver hallazgos NC del auditor · plan correctivo cliente.",
  enac_audit_passed: "Auditoría ENAC aprobada · esperando emisión certificado.",
  certificate_issued: "Certificado ENS emitido · 2 años de vigencia.",
  biannual_renewal_scheduled: "Programar renovación bianual · vuelta a preparación.",
};

function ariaLabelForState(state: string): string {
  return STATE_LABELS[state] ?? state;
}

export function AuditAccompanimentTimeline({ projectId }: Props) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activeUploadState, setActiveUploadState] = useState<string | null>(null);
  const [activeUploadType, setActiveUploadType] = useState<string>("");

  const { data: timeline, isLoading } = useQuery<AccompanimentTimeline>({
    queryKey: ["audit-accompaniment-timeline", projectId],
    queryFn: () => auditAccompanimentApi.getAdminTimeline(projectId),
    staleTime: 30_000,
  });

  const advanceMutation = useMutation({
    mutationFn: (target_state: string) =>
      auditAccompanimentApi.advanceState(projectId, target_state),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["audit-accompaniment-timeline", projectId],
      });
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async ({
      state,
      artifact_type,
      file,
    }: {
      state: string;
      artifact_type: string;
      file: File;
    }) => auditAccompanimentApi.uploadArtifact(projectId, state, artifact_type, file),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["audit-accompaniment-timeline", projectId],
      });
    },
  });

  if (isLoading || !timeline) {
    return (
      <Card>
        <CardContent className="py-6 text-sm text-muted-foreground">
          Cargando timeline acompañamiento...
        </CardContent>
      </Card>
    );
  }

  const orderedStates =
    timeline.category_branch === "MEDIO_ALTO" ? MEDIO_ALTO_STATES : BASICO_STATES;
  const currentStateIdx = orderedStates.findIndex(
    (s) => s === timeline.current_state,
  );

  const artifactsByState = timeline.artifacts.reduce<Record<string, typeof timeline.artifacts>>(
    (acc, art) => {
      const list = acc[art.state] ?? [];
      list.push(art);
      acc[art.state] = list;
      return acc;
    },
    {},
  );

  return (
    <Card data-testid="audit-accompaniment-timeline">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Acompañamiento auditoría ·{" "}
          <Badge variant={timeline.category_branch === "MEDIO_ALTO" ? "default" : "success"}>
            {timeline.category_branch === "MEDIO_ALTO" ? "MEDIO/ALTO (ENAC)" : "BÁSICO (autodeclaración)"}
          </Badge>{" "}
          <TooltipENS text="Ciclo post-implantación: BÁSICO 6 estados autodeclaración / MEDIO+ALTO 11 estados con auditoría ENAC bianual." />
        </CardTitle>
        <CardDescription>
          Estado actual: <strong>{ariaLabelForState(timeline.current_state)}</strong>
          {timeline.last_advanced_at && (
            <span className="ml-2 text-xs text-muted-foreground">
              · avanzado {format(new Date(timeline.last_advanced_at), "PPp", { locale: es })}
            </span>
          )}
          {timeline.is_terminal && (
            <Badge variant="success" className="ml-2">
              Terminal
            </Badge>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ol className="space-y-3" data-testid="accompaniment-states-list">
          {orderedStates.map((state, idx) => {
            const isCompleted = idx < currentStateIdx;
            const isCurrent = idx === currentStateIdx;
            const isPending = idx > currentStateIdx;
            const artifactsForState = artifactsByState[state] ?? [];
            const transitionsForState = timeline.transitions.filter((t) => t.to_state === state);

            return (
              <li
                key={state}
                className={`rounded-md border p-3 ${
                  isCurrent ? "border-fulkro-info bg-fulkro-info/5" : ""
                }`}
                data-testid={`accompaniment-state-${state}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2">
                    {isCompleted ? (
                      <CheckCircle2 className="h-5 w-5 text-fulkro-success" strokeWidth={2.3} />
                    ) : isCurrent ? (
                      <Circle className="h-5 w-5 text-fulkro-info animate-pulse" strokeWidth={2.3} />
                    ) : (
                      <Circle className="h-5 w-5 text-muted-foreground" strokeWidth={2.3} />
                    )}
                    <div className="flex-1">
                      <p className="font-medium">
                        {ariaLabelForState(state)}{" "}
                        <TooltipENS text={STATE_TUTOR_HINTS[state] ?? ""} />
                      </p>
                      {transitionsForState[0] && (
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(transitionsForState[0].advanced_at), "PPp", { locale: es })}
                          {transitionsForState[0].advanced_by &&
                            ` · por ${transitionsForState[0].advanced_by}`}
                        </p>
                      )}
                    </div>
                  </div>
                  {isCurrent && idx + 1 < orderedStates.length && (
                    <Button
                      size="sm"
                      onClick={() => advanceMutation.mutate(orderedStates[idx + 1])}
                      disabled={advanceMutation.isPending}
                      data-testid={`accompaniment-advance-${state}`}
                    >
                      {advanceMutation.isPending ? (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" strokeWidth={2.3} />
                      ) : (
                        <ChevronRight className="mr-1 h-3 w-3" strokeWidth={2.3} />
                      )}
                      Avanzar
                    </Button>
                  )}
                </div>

                {(isCompleted || isCurrent) && (
                  <div className="mt-3 ml-7 space-y-2">
                    {artifactsForState.length > 0 && (
                      <ul className="space-y-1 text-xs" data-testid={`artifacts-${state}`}>
                        {artifactsForState.map((art) => (
                          <li key={art.id} className="flex items-center gap-2">
                            <span className="font-mono">{art.artifact_type}</span>
                            <span className="text-muted-foreground">
                              ({(art.file_size_bytes / 1024).toFixed(1)} KB)
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {isCurrent && (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          placeholder="Tipo artifact (e.g. declaration_pdf)"
                          className="rounded-md border px-2 py-1 text-xs"
                          onChange={(e) => {
                            setActiveUploadState(state);
                            setActiveUploadType(e.target.value);
                          }}
                          data-testid={`artifact-type-input-${state}`}
                        />
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={!activeUploadType || uploadMutation.isPending}
                          data-testid={`artifact-upload-btn-${state}`}
                        >
                          <Upload className="mr-1 h-3 w-3" strokeWidth={2.3} />
                          Subir
                        </Button>
                        <input
                          ref={fileInputRef}
                          type="file"
                          hidden
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file && activeUploadState && activeUploadType) {
                              uploadMutation.mutate({
                                state: activeUploadState,
                                artifact_type: activeUploadType,
                                file,
                              });
                            }
                          }}
                        />
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      </CardContent>
    </Card>
  );
}
