"use client";

/**
 * /admin/meetings/new — Crear nueva reunión (sub-bloque 7.B.10).
 *
 * Form mínimo: cliente Select + título. Crea meeting backend +
 * redirige a /admin/meetings/{id} para ampliar metadata.
 */
import { ArrowRight } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useClients } from "@/hooks/useClients";

import { createMeeting } from "@/lib/admin-meetings/api";
import {
  ETAPA_K_LABELS,
  MEETING_ETAPAS_K,
  MEETING_PLATFORMS,
  PLATFORM_LABELS,
  type MeetingEtapaK,
  type MeetingPlatform,
} from "@/lib/admin-meetings/schemas";

export default function NewMeetingPage() {
  const router = useRouter();
  const params = useSearchParams();
  const presetClientId = params.get("client_id") ?? "";
  const presetLeadName = params.get("lead") ?? "";

  const { data: clients } = useClients();

  const [clientId, setClientId] = React.useState(presetClientId);
  const [title, setTitle] = React.useState(
    presetLeadName ? `Reunión con ${presetLeadName}` : "",
  );
  const [platform, setPlatform] = React.useState<MeetingPlatform | "">("");
  const [etapaK, setEtapaK] = React.useState<MeetingEtapaK | "">("");
  const [submitting, setSubmitting] = React.useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!clientId) {
      toast.error("Selecciona un cliente.");
      return;
    }
    if (!title.trim()) {
      toast.error("Escribe un título.");
      return;
    }
    setSubmitting(true);
    try {
      const meeting = await createMeeting({
        client_id: clientId,
        title: title.trim(),
        platform: platform || null,
        etapa_k: etapaK || null,
      });
      toast.success("Reunión creada.");
      router.push(`/admin/meetings/${meeting.id}`);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Error creando reunión.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <Card>
        <CardHeader>
          <CardTitle>Nueva reunión</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="meeting-client">Cliente</Label>
              <select
                id="meeting-client"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                className="mt-1 w-full rounded-md border border-fulkro-ink-300 px-2 py-1.5 text-sm"
                disabled={submitting || !!presetClientId}
                required
              >
                <option value="">Selecciona cliente…</option>
                {clients?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="meeting-title">Título</Label>
              <Input
                id="meeting-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={200}
                disabled={submitting}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="meeting-platform">Plataforma (opcional)</Label>
                <select
                  id="meeting-platform"
                  value={platform}
                  onChange={(e) =>
                    setPlatform(e.target.value as MeetingPlatform | "")
                  }
                  className="mt-1 w-full rounded-md border border-fulkro-ink-300 px-2 py-1.5 text-sm"
                  disabled={submitting}
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
                <Label htmlFor="meeting-etapa">Etapa K (opcional)</Label>
                <select
                  id="meeting-etapa"
                  value={etapaK}
                  onChange={(e) =>
                    setEtapaK(e.target.value as MeetingEtapaK | "")
                  }
                  className="mt-1 w-full rounded-md border border-fulkro-ink-300 px-2 py-1.5 text-sm"
                  disabled={submitting}
                >
                  <option value="">— elegir —</option>
                  {MEETING_ETAPAS_K.map((k) => (
                    <option key={k} value={k}>
                      {ETAPA_K_LABELS[k]}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex justify-end">
              <Button type="submit" disabled={submitting}>
                {submitting ? "Creando…" : "Crear reunión"}
                <ArrowRight size={14} className="ml-1" />
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
