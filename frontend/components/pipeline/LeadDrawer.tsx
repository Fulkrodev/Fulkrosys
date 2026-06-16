"use client";

import {
  Brain,
  FileText,
  Handshake,
  Loader2,
  Phone,
  Sparkles,
  Video,
  X,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { toast } from "sonner";

import { RAGBadge } from "@/components/data/RAGBadge";
import { Button, buttonVariants } from "@/components/ui/button";
import { useEscapeKey } from "@/hooks/useEscapeKey";
import { useUpdateLeadStage } from "@/hooks/useLeads";
import { ROUTES } from "@/lib/constants";
import type { Lead } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

function formatEuros(v: number): string {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(v);
}

export function LeadDrawer({
  lead,
  open,
  onClose,
}: {
  lead: Lead | null;
  open: boolean;
  onClose: () => void;
}) {
  const markLost = useUpdateLeadStage();
  const [busyAgent, setBusyAgent] = React.useState<number | null>(null);
  useEscapeKey(onClose, open);

  if (!open || !lead) return null;

  async function invokeAgent(agentId: number, label: string) {
    if (!lead) return;
    setBusyAgent(agentId);
    // Sprint 2: surface the intent; the real agent invocation is wired when
    // the backend lead model exists.
    try {
      await new Promise((r) => setTimeout(r, 350));
      toast.success(`Agente ${agentId} — ${label} (simulado)`);
    } finally {
      setBusyAgent(null);
    }
  }

  return (
    <div
      className="fixed inset-0 z-40 flex"
      role="dialog"
      aria-modal
      aria-labelledby="lead-drawer-title"
    >
      <button
        type="button"
        aria-label="Cerrar"
        className="flex-1 bg-fulkro-ink-900/30"
        onClick={onClose}
      />
      <aside className="h-full w-[420px] max-w-full overflow-y-auto border-l border-[color:var(--fulkro-surface-glass-border)] bg-white shadow-ink animate-slide-in-right">
        <div className="flex items-start justify-between border-b border-[color:var(--fulkro-surface-glass-border)] px-5 py-4">
          <div>
            <p className="text-[13px] font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
              Lead
            </p>
            <h2 id="lead-drawer-title">{lead.empresa}</h2>
            <p className="mt-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
              {lead.sector ?? "Sector sin especificar"}
              {lead.cif ? ` · ${lead.cif}` : ""}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Cerrar drawer"
          >
            <X size={16} />
          </Button>
        </div>

        <div className="space-y-6 p-5">
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Score" value={String(lead.score)}>
              <RAGBadge status={lead.rag} size="sm" />
            </Stat>
            <Stat label="Valor" value={formatEuros(lead.value_eur)} />
            <Stat
              label="Última actualización"
              value={formatDate(lead.last_touched_at)}
            />
            <Stat label="Origen" value={lead.source ?? "—"} />
          </div>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
              Contacto
            </h3>
            <ul className="space-y-1 text-sm">
              {lead.contact_name && (
                <li className="flex items-center gap-2 text-fulkro-ink-700">
                  <Handshake size={14} className="text-fulkro-ink-500" />
                  {lead.contact_name}
                </li>
              )}
              {lead.contact_email && (
                <li className="flex items-center gap-2 text-fulkro-ink-700">
                  <FileText size={14} className="text-fulkro-ink-500" />
                  <a
                    href={`mailto:${lead.contact_email}`}
                    className="text-fulkro-info hover:underline"
                  >
                    {lead.contact_email}
                  </a>
                </li>
              )}
              {lead.contact_phone && (
                <li className="flex items-center gap-2 text-fulkro-ink-700">
                  <Phone size={14} className="text-fulkro-ink-500" />
                  <a
                    href={`tel:${lead.contact_phone}`}
                    className="text-fulkro-info hover:underline"
                  >
                    {lead.contact_phone}
                  </a>
                </li>
              )}
              {!lead.contact_name &&
                !lead.contact_email &&
                !lead.contact_phone && (
                  <p className="text-base font-medium text-[color:var(--fulkro-muted)]">
                    Sin contacto registrado.
                  </p>
                )}
            </ul>
          </section>

          {lead.notes && (
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
                Notas
              </h3>
              <p className="text-base font-medium text-[color:var(--fulkro-body)]">{lead.notes}</p>
            </section>
          )}

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
              Acciones
            </h3>
            <div className="flex flex-col gap-2">
              <Button
                variant="outline"
                size="md"
                disabled={busyAgent !== null}
                onClick={() => invokeAgent(17, "Cualificador comercial")}
              >
                {busyAgent === 17 ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Brain size={14} />
                )}
                Cualificar (Agente 17)
              </Button>
              <Button
                variant="outline"
                size="md"
                disabled={busyAgent !== null || !lead.pliego_attached}
                onClick={() => invokeAgent(2, "Analizador de pliegos")}
              >
                {busyAgent === 2 ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <FileText size={14} />
                )}
                Analizar pliego (Agente 2)
              </Button>
              <Button
                variant="outline"
                size="md"
                disabled={busyAgent !== null}
                onClick={() => invokeAgent(19, "Redactor de propuestas")}
              >
                {busyAgent === 19 ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Sparkles size={14} />
                )}
                Generar propuesta (Agente 19)
              </Button>
              <Link
                href={`${ROUTES.meetings}/new?lead=${lead.id}`}
                className={cn(
                  buttonVariants({ variant: "primary", size: "md" }),
                  "justify-center",
                )}
              >
                <Video size={14} />
                Programar reunión exploratoria
              </Link>
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
              Cerrar como perdido
            </h3>
            <LostForm
              lead={lead}
              pending={markLost.isPending}
              onSubmit={async (reason) => {
                try {
                  // FIX(#9): persistencia real vía /commercial/leads/{id}/stage
                  // (antes useUpdateLead era un mock sleep(80) → no persistía).
                  // notes → razon_perdida + fecha_perdida en el backend.
                  await markLost.mutateAsync({
                    leadId: lead.id,
                    stage: "lost",
                    notes: reason,
                  });
                  toast.success("Lead cerrado como perdido");
                  onClose();
                } catch (err) {
                  toast.error("No se pudo actualizar el lead");
                }
              }}
            />
          </section>
        </div>
      </aside>
    </div>
  );
}

function Stat({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-[color:var(--fulkro-surface-glass-border)] p-3">
      <p className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
        {label}
      </p>
      <div className="mt-1 flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-fulkro-primary-700">{value}</p>
        {children}
      </div>
    </div>
  );
}

function LostForm({
  lead,
  onSubmit,
  pending,
}: {
  lead: Lead;
  onSubmit: (reason: string) => Promise<void>;
  pending: boolean;
}) {
  const [reason, setReason] = React.useState(lead.lost_reason ?? "");
  return (
    <form
      className="space-y-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (reason.trim().length === 0) {
          toast.error("Introduce un motivo");
          return;
        }
        onSubmit(reason.trim());
      }}
    >
      <textarea
        rows={2}
        required
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Motivo del cierre…"
        className="min-h-[64px] w-full rounded-md border border-fulkro-ink-300 bg-white p-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700"
      />
      <Button
        type="submit"
        variant="danger"
        size="sm"
        disabled={pending}
        className="w-full"
      >
        {pending ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          "Marcar perdido"
        )}
      </Button>
    </form>
  );
}
