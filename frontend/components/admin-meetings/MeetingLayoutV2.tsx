"use client";

/**
 * MeetingLayoutV2 — admin-meetings v2 backend-real (sub-bloque 7.B.3 FASE 7).
 *
 * Reemplaza incrementalmente legacy `components/meeting/MeetingLayout.tsx`
 * mock-driven. Sub-bloques B3-B7 amplían:
 *   B3 (este) · skeleton + metadata fields + status + workflow buttons
 *   B4       · ContactQuickPicker M30 + mini-card interlocutor
 *   B5       · MeetingTimer + MeetingNotes autosave
 *   B6       · MeetingLivePanel SSE consumer
 *   B7       · PostMeetingActions component (post-completion)
 *   B10      · rename componentes + retire legacy MeetingLayout
 */
import * as React from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useMeeting } from "@/hooks/useMeeting";
import { MeetingInterlocutorCard } from "./MeetingInterlocutorCard";
import { MeetingLivePanel } from "./MeetingLivePanel";
import { MeetingNotes } from "./MeetingNotes";
import { MeetingTimer } from "./MeetingTimer";
import { PostMeetingActions } from "./PostMeetingActions";
import {
  ETAPA_K_LABELS,
  MEETING_ETAPAS_K,
  MEETING_PLATFORMS,
  PLATFORM_LABELS,
  STATUS_LABELS,
  type MeetingEtapaK,
  type MeetingPlatform,
  type MeetingStatus,
} from "@/lib/admin-meetings/schemas";

interface MeetingLayoutV2Props {
  meetingId: string;
}

const STATUS_BADGE_VARIANTS: Record<MeetingStatus, "default" | "secondary"> = {
  scheduled: "secondary",
  in_progress: "default",
  completed: "default",
  cancelled: "secondary",
};

export function MeetingLayoutV2({ meetingId }: MeetingLayoutV2Props) {
  const {
    meeting,
    loading,
    error,
    patchMeeting,
    complete,
    cancel,
    postAction,
    savedAt,
  } = useMeeting(meetingId);

  // Local form state (sync con meeting on load)
  const [title, setTitle] = React.useState("");
  const [platform, setPlatform] = React.useState<MeetingPlatform | "">("");
  const [meetingUrl, setMeetingUrl] = React.useState("");
  const [etapaK, setEtapaK] = React.useState<MeetingEtapaK | "">("");
  const [trackedMinutes, setTrackedMinutes] = React.useState(0);

  React.useEffect(() => {
    if (meeting) {
      setTitle(meeting.title);
      setPlatform((meeting.platform ?? "") as MeetingPlatform | "");
      setMeetingUrl(meeting.meeting_url ?? "");
      setEtapaK((meeting.etapa_k ?? "") as MeetingEtapaK | "");
      setTrackedMinutes(meeting.duration_minutes ?? 0);
    }
  }, [meeting]);

  const isLocked =
    meeting?.status === "completed" || meeting?.status === "cancelled";

  async function handleSaveMetadata() {
    if (!meeting) return;
    try {
      await patchMeeting({
        title: title.trim() || meeting.title,
        platform: platform || null,
        meeting_url: meetingUrl.trim() || null,
        etapa_k: etapaK || null,
      });
      toast.success("Metadata guardada.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error guardando metadata.");
    }
  }

  async function handleComplete() {
    if (!meeting) return;
    if (
      !window.confirm(
        "¿Marcar reunión como completada? Después no se podrán editar campos.",
      )
    ) {
      return;
    }
    try {
      await complete({
        duration_minutes: trackedMinutes > 0 ? trackedMinutes : undefined,
      });
      toast.success("Reunión completada. M30 timeline actualizado.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error completando.");
    }
  }

  async function handleCancel() {
    if (!meeting) return;
    const reason = window.prompt("Motivo de cancelación (opcional):") || null;
    try {
      await cancel({ reason });
      toast.success("Reunión cancelada.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Error cancelando.");
    }
  }

  if (loading) {
    return (
      <div className="space-y-3 p-6">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        Error: {error}
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="rounded-md border border-fulkro-ink-200 bg-white p-6 text-sm text-fulkro-ink-500">
        Reunión no encontrada.
      </div>
    );
  }

  return (
    <div className="-m-6 flex h-[calc(100dvh-3.5rem)] flex-col bg-fulkro-ink-50">
      <header className="border-b border-fulkro-ink-300/60 bg-white px-6 py-3">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
              Reunión exploratoria · M_meetings
            </p>
            <h1 className="text-lg font-semibold text-fulkro-primary-700">
              {meeting.title || "(sin título)"}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={STATUS_BADGE_VARIANTS[meeting.status]}>
              {STATUS_LABELS[meeting.status]}
            </Badge>
            {savedAt && (
              <span className="text-xs text-fulkro-ink-500">
                Guardado{" "}
                {savedAt.toLocaleTimeString("es-ES", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2 gap-6 p-6 overflow-y-auto">
        {/* COLUMNA IZQUIERDA — Metadata + Notas placeholder */}
        <section className="space-y-4">
          <div className="rounded-md border border-fulkro-ink-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-semibold text-fulkro-primary-700">
              Metadata reunión
            </h2>
            <div className="space-y-3">
              <div>
                <Label htmlFor="meeting-title">Título</Label>
                <Input
                  id="meeting-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={isLocked}
                  maxLength={200}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="meeting-platform">Plataforma</Label>
                  <select
                    id="meeting-platform"
                    value={platform}
                    onChange={(e) =>
                      setPlatform(e.target.value as MeetingPlatform | "")
                    }
                    disabled={isLocked}
                    className="mt-1 w-full rounded-md border border-fulkro-ink-300 px-2 py-1.5 text-sm"
                  >
                    <option value="">— elegir —</option>
                    {MEETING_PLATFORMS.map((p) => (
                      <option key={p} value={p}>
                        {PLATFORM_LABELS[p]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <Label htmlFor="meeting-etapa">Etapa K</Label>
                  <select
                    id="meeting-etapa"
                    value={etapaK}
                    onChange={(e) =>
                      setEtapaK(e.target.value as MeetingEtapaK | "")
                    }
                    disabled={isLocked}
                    className="mt-1 w-full rounded-md border border-fulkro-ink-300 px-2 py-1.5 text-sm"
                  >
                    <option value="">— elegir —</option>
                    {MEETING_ETAPAS_K.map((e) => (
                      <option key={e} value={e}>
                        {ETAPA_K_LABELS[e]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              {platform && platform !== "presencial" && (
                <div>
                  <Label htmlFor="meeting-url">URL plataforma</Label>
                  <Input
                    id="meeting-url"
                    value={meetingUrl}
                    onChange={(e) => setMeetingUrl(e.target.value)}
                    disabled={isLocked}
                    placeholder="https://meet.google.com/..."
                    maxLength={500}
                  />
                  {meetingUrl && (
                    <a
                      href={meetingUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-block text-xs text-fulkro-primary-600 hover:underline"
                    >
                      Abrir {PLATFORM_LABELS[platform]} ↗
                    </a>
                  )}
                </div>
              )}
              {!isLocked && (
                <div className="flex justify-end">
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleSaveMetadata}
                  >
                    Guardar metadata
                  </Button>
                </div>
              )}
            </div>
          </div>

          <MeetingTimer
            initialMinutes={meeting.duration_minutes ?? 0}
            disabled={isLocked}
            onElapsedMinutes={(minutes) => setTrackedMinutes(minutes)}
          />
          <MeetingNotes
            initialNotes={meeting.notes_markdown ?? ""}
            disabled={isLocked}
            saving={false}
            savedAt={savedAt}
            onSave={async (notesMarkdown) => {
              await patchMeeting({ notes_markdown: notesMarkdown });
            }}
          />

          {/* Interlocutor — ContactQuickPicker M30 cross-motor reuse */}
          <MeetingInterlocutorCard
            clientId={meeting.client_id}
            contactId={meeting.interlocutor_contact_id}
            interlocutor={meeting.interlocutor}
            disabled={isLocked}
            onChange={async (newId) => {
              await patchMeeting({ interlocutor_contact_id: newId });
              toast.success(
                newId ? "Interlocutor actualizado." : "Interlocutor eliminado.",
              );
            }}
          />
        </section>

        {/* COLUMNA DERECHA — Live Panel SSE A18 */}
        <section>
          <MeetingLivePanel
            meetingId={meeting.id}
            notesMarkdown={meeting.notes_markdown ?? ""}
            disabled={isLocked}
            onInsight={async (insight) => {
              // Persist insight outputs_agente_18 vía complete con outputs
              // (solo si meeting está in_progress / scheduled — en
              // completed el flow ya ha terminado).
              if (!isLocked) {
                try {
                  await patchMeeting({});
                  // Note: outputs_agente_18 se persiste via complete_meeting
                  // payload; aquí solo refresca state. Future enhancement:
                  // backend MeetingUpdate.outputs_agente_18 para persistir
                  // sin completar.
                } catch {
                  /* silent */
                }
              }
            }}
          />
        </section>
      </div>

      <footer className="border-t border-fulkro-ink-300/60 bg-white px-6 py-3">
        <div className="flex items-center justify-end gap-2">
          {meeting.status === "scheduled" || meeting.status === "in_progress" ? (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
              >
                Cancelar reunión
              </Button>
              <Button type="button" onClick={handleComplete}>
                Marcar completada
              </Button>
            </>
          ) : meeting.status === "completed" ? (
            <div className="w-full">
              <PostMeetingActions
                meeting={meeting}
                onAction={postAction}
              />
            </div>
          ) : (
            <p className="text-sm text-fulkro-ink-500">
              Reunión cancelada.
            </p>
          )}
        </div>
      </footer>
    </div>
  );
}
