"use client";

/**
 * MeetingInterlocutorCard — ContactQuickPicker M30 + mini-card display
 * (sub-bloque 7.B.4 FASE 7).
 *
 * Cross-motor reuse ADR-023 dominio compartido:
 *   ContactQuickPicker pre-anticipado en M30 con comentario fuente
 *   "M29 destinatario mensajería" y ahora también M_meetings.
 *
 * Display:
 *   - Picker (cuando interlocutor null o disabled=false)
 *   - Mini-card (full_name + role + email + notes_excerpt) si selected
 *   - Botón "Cambiar" para volver al picker post-selección
 */
import { Mail, User } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { ContactQuickPicker } from "@/components/admin-clients/contacts/ContactQuickPicker";
import { Button } from "@/components/ui/button";
import type { MeetingContactSummary } from "@/lib/admin-meetings/schemas";

interface MeetingInterlocutorCardProps {
  clientId: string;
  contactId: string | null | undefined;
  interlocutor: MeetingContactSummary | null | undefined;
  disabled?: boolean;
  onChange: (contactId: string | null) => Promise<void>;
}

export function MeetingInterlocutorCard({
  clientId,
  contactId,
  interlocutor,
  disabled = false,
  onChange,
}: MeetingInterlocutorCardProps) {
  const [editing, setEditing] = React.useState(false);

  async function handleChange(newId: string | null) {
    try {
      await onChange(newId);
      setEditing(false);
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : "Error guardando interlocutor.",
      );
    }
  }

  const showPicker = editing || !interlocutor;

  return (
    <div className="rounded-md border border-fulkro-ink-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-fulkro-primary-700">
          Interlocutor
        </h3>
        {!disabled && interlocutor && !editing && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setEditing(true)}
          >
            Cambiar
          </Button>
        )}
      </div>

      {showPicker ? (
        <div className="mt-3 space-y-2">
          <ContactQuickPicker
            clientId={clientId}
            value={contactId ?? null}
            onChange={(id) => void handleChange(id)}
            placeholder="Selecciona contacto del cliente…"
            disabled={disabled}
          />
          {!disabled && interlocutor && (
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="text-xs text-fulkro-ink-500 hover:text-fulkro-ink-700"
            >
              Cancelar edición
            </button>
          )}
        </div>
      ) : interlocutor ? (
        <article className="mt-3 space-y-2 text-sm">
          <div className="flex items-start gap-3">
            <div className="flex size-9 items-center justify-center rounded-full bg-fulkro-primary-50 text-fulkro-primary-700">
              <User size={16} aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-semibold text-fulkro-ink-900">
                {interlocutor.full_name}
              </p>
              <p className="truncate text-xs text-fulkro-ink-500">
                {interlocutor.role_title} · {interlocutor.role_category}
              </p>
              <a
                href={`mailto:${interlocutor.email}`}
                className="mt-1 inline-flex items-center gap-1 text-xs text-fulkro-primary-600 hover:underline"
              >
                <Mail size={12} aria-hidden />
                {interlocutor.email}
              </a>
            </div>
          </div>
          {interlocutor.notes_excerpt && (
            <p className="rounded bg-fulkro-ink-50 p-2 text-xs italic text-fulkro-ink-600">
              {interlocutor.notes_excerpt}
            </p>
          )}
        </article>
      ) : null}
    </div>
  );
}
