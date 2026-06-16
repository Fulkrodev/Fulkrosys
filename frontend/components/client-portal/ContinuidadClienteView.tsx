"use client";

/**
 * ContinuidadClienteView · cuestionario de continuidad (BIA/DRP) + aprobación.
 * feat/fulkro-100 (2026-06-12).
 *
 * Cliente-mínimo (R29): el cliente nos cuenta qué procesos son críticos y cuánto
 * tiempo puede aguantar sin ellos (su "tolerancia"); su consultor prepara el Plan
 * de Continuidad (BIA/DRP) y el cliente lo APRUEBA o pide cambios. NO opera técnico.
 *
 * SSE realtime: cuando Marcos deja un borrador listo (continuidad.draft_ready) la
 * lista se refresca sola; cuando el cliente aprueba/comenta, el admin lo ve en vivo.
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { LifeBuoy, ShieldCheck, MessageSquarePlus } from "lucide-react";

import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  continuidadApi,
  type ContinuidadDraft,
  type ContinuidadQuestionnaire,
} from "@/lib/api/continuidad";

interface Props {
  projectId?: string | null;
}

const Q_KEY = ["client-continuidad-questionnaire"];
const D_KEY = ["client-continuidad-drafts"];

function linesToItems(text: string): { nombre: string }[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((nombre) => ({ nombre }));
}

function itemsToLines(items?: { nombre: string }[] | null): string {
  return (items ?? []).map((i) => i.nombre).join("\n");
}

export function ContinuidadClienteView({ projectId }: Props) {
  const queryClient = useQueryClient();

  const { data: questionnaire, isLoading: qLoading } =
    useQuery<ContinuidadQuestionnaire | null>({
      queryKey: Q_KEY,
      queryFn: () => continuidadApi.getQuestionnaire(),
      staleTime: 30_000,
    });

  const { data: draftsResp, isLoading: dLoading } = useQuery({
    queryKey: D_KEY,
    queryFn: () => continuidadApi.listDrafts(),
    staleTime: 30_000,
  });

  // SSE: admin deja borrador / el cliente aprueba → refresco en vivo.
  useClientProjectEvents(projectId ?? null, {
    invalidateQueries: [Q_KEY, D_KEY],
  });

  // ── Form local state (hidratado desde el cuestionario guardado) ──
  const [procesos, setProcesos] = useState("");
  const [activos, setActivos] = useState("");
  const [rto, setRto] = useState("");
  const [rpo, setRpo] = useState("");
  const [impacto, setImpacto] = useState("");
  const [notas, setNotas] = useState("");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    if (questionnaire && !hydrated) {
      setProcesos(itemsToLines(questionnaire.procesos_criticos));
      setActivos(itemsToLines(questionnaire.activos_core));
      setRto(questionnaire.rto_horas_tolerancia?.toString() ?? "");
      setRpo(questionnaire.rpo_horas_tolerancia?.toString() ?? "");
      setImpacto(questionnaire.impacto_diario_eur ?? "");
      setNotas(questionnaire.notas_cliente ?? "");
      setHydrated(true);
    }
  }, [questionnaire, hydrated]);

  const save = useMutation({
    mutationFn: (completed: boolean) =>
      continuidadApi.saveQuestionnaire({
        procesos_criticos: linesToItems(procesos),
        activos_core: linesToItems(activos),
        rto_horas_tolerancia: rto ? Number(rto) : null,
        rpo_horas_tolerancia: rpo ? Number(rpo) : null,
        impacto_diario_eur: impacto && Number.isFinite(Number(impacto)) ? impacto : null,
        notas_cliente: notas || null,
        completed,
      }),
    onSuccess: (_data, completed) => {
      void queryClient.invalidateQueries({ queryKey: Q_KEY });
      toast.success(
        completed
          ? "¡Enviado a tu consultor! Preparará tu Plan de Continuidad."
          : "Guardado. Puedes seguir cuando quieras, sin prisa.",
      );
    },
    onError: () =>
      toast.error("No hemos podido guardarlo. Inténtalo de nuevo en un momento."),
  });

  const drafts = draftsResp?.drafts ?? [];

  return (
    <div className="space-y-6">
      {/* ── Cuestionario ── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LifeBuoy className="h-5 w-5" /> Tu continuidad de negocio
          </CardTitle>
          <CardDescription>
            Cuéntanos qué es lo más importante de tu actividad para que, si algo
            fallara, sepamos por dónde empezar a recuperarte. No hace falta que
            seas técnico: con tus palabras nos vale.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {qLoading && !hydrated ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="procesos">
                  ¿Qué procesos no pueden parar? (uno por línea)
                </Label>
                <Textarea
                  id="procesos"
                  value={procesos}
                  onChange={(e) => setProcesos(e.target.value)}
                  placeholder={"Facturación a clientes\nAtención telefónica\nAcceso a la aplicación"}
                  rows={4}
                  data-testid="continuidad-procesos"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="activos">
                  ¿Qué sistemas o herramientas son imprescindibles? (uno por línea)
                </Label>
                <Textarea
                  id="activos"
                  value={activos}
                  onChange={(e) => setActivos(e.target.value)}
                  placeholder={"Servidor de correo\nBase de datos de clientes\nERP"}
                  rows={3}
                  data-testid="continuidad-activos"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="rto">Horas que aguantas sin servicio</Label>
                  <Input
                    id="rto"
                    type="number"
                    min={0}
                    value={rto}
                    onChange={(e) => setRto(e.target.value)}
                    placeholder="p. ej. 8"
                    data-testid="continuidad-rto"
                  />
                  <p className="text-xs text-muted-foreground">
                    Tiempo máximo que tu actividad puede estar parada sin causar
                    un daño serio.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rpo">Horas de datos que puedes perder</Label>
                  <Input
                    id="rpo"
                    type="number"
                    min={0}
                    value={rpo}
                    onChange={(e) => setRpo(e.target.value)}
                    placeholder="p. ej. 1"
                    data-testid="continuidad-rpo"
                  />
                  <p className="text-xs text-muted-foreground">
                    Cuántas horas de información reciente podrías permitirte
                    perder en una incidencia.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="impacto">Coste aproximado por día parado (€)</Label>
                  <Input
                    id="impacto"
                    type="number"
                    min={0}
                    value={impacto}
                    onChange={(e) => setImpacto(e.target.value)}
                    placeholder="opcional"
                    data-testid="continuidad-impacto"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="notas">¿Algo más que debamos saber?</Label>
                <Textarea
                  id="notas"
                  value={notas}
                  onChange={(e) => setNotas(e.target.value)}
                  rows={2}
                  placeholder="Opcional: cualquier detalle que nos ayude."
                  data-testid="continuidad-notas"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Button
                  variant="outline"
                  onClick={() => save.mutate(false)}
                  disabled={save.isPending}
                  data-testid="continuidad-guardar"
                >
                  Guardar borrador
                </Button>
                <Button
                  onClick={() => save.mutate(true)}
                  disabled={save.isPending}
                  data-testid="continuidad-enviar"
                >
                  Enviar a mi consultor
                </Button>
                {questionnaire?.completed && (
                  <Badge variant="secondary" className="gap-1">
                    <ShieldCheck className="h-3.5 w-3.5" /> Enviado
                  </Badge>
                )}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Borradores BIA/DRP para aprobar ── */}
      <Card>
        <CardHeader>
          <CardTitle>Tu Plan de Continuidad</CardTitle>
          <CardDescription>
            Cuando tu consultor prepare tu plan, aparecerá aquí para que lo
            revises. Si te encaja, lo apruebas; si quieres cambios, nos lo dices.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {dLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : drafts.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="continuidad-drafts-empty">
              Aún no hay nada que revisar. En cuanto tengamos tu plan listo te
              avisaremos aquí. Sin prisa por tu parte.
            </p>
          ) : (
            drafts.map((d) => (
              <DraftRow key={d.draft_id} draft={d} queryKeyToInvalidate={D_KEY} />
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function DraftRow({
  draft,
  queryKeyToInvalidate,
}: {
  draft: ContinuidadDraft;
  queryKeyToInvalidate: string[];
}) {
  const queryClient = useQueryClient();
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState("");

  const approve = useMutation({
    mutationFn: () =>
      continuidadApi.approveDraft(draft.draft_id, draft.artifact_type),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeyToInvalidate });
      toast.success("¡Aprobado! Gracias, lo dejamos registrado.");
    },
    onError: () => toast.error("No se pudo aprobar. Inténtalo de nuevo."),
  });

  const sendComment = useMutation({
    mutationFn: () =>
      continuidadApi.commentDraft(draft.draft_id, draft.artifact_type, comment),
    onSuccess: () => {
      setShowComment(false);
      setComment("");
      void queryClient.invalidateQueries({ queryKey: queryKeyToInvalidate });
      toast.success("Enviado. Tu consultor revisará tus comentarios.");
    },
    onError: () => toast.error("No se pudo enviar. Inténtalo de nuevo."),
  });

  const label = draft.artifact_type === "drp"
    ? "Plan de Recuperación (DRP)"
    : "Análisis de Impacto (BIA)";

  return (
    <div
      className="rounded-lg border bg-white p-4 space-y-3"
      data-testid={`continuidad-draft-${draft.draft_id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{label}</p>
          <p className="text-sm text-muted-foreground">{draft.summary}</p>
        </div>
        <Badge variant="outline" className="uppercase">
          {draft.artifact_type}
        </Badge>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          onClick={() => approve.mutate()}
          disabled={approve.isPending}
          data-testid={`continuidad-approve-${draft.draft_id}`}
        >
          <ShieldCheck className="mr-1 h-4 w-4" /> Aprobar
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => setShowComment((v) => !v)}
          data-testid={`continuidad-comment-toggle-${draft.draft_id}`}
        >
          <MessageSquarePlus className="mr-1 h-4 w-4" /> Pedir cambios
        </Button>
      </div>
      {showComment && (
        <div className="space-y-2">
          <Textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
            placeholder="Cuéntanos qué te gustaría ajustar."
            data-testid={`continuidad-comment-input-${draft.draft_id}`}
          />
          <Button
            size="sm"
            onClick={() => sendComment.mutate()}
            disabled={sendComment.isPending || comment.trim().length === 0}
          >
            Enviar comentarios
          </Button>
        </div>
      )}
    </div>
  );
}
