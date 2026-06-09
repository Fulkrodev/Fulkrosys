"use client";

/**
 * MeetingNotes — textarea markdown + autosave debounce 2s
 * (sub-bloque 7.B.5 FASE 7).
 *
 * - Textarea con state local sync con meeting.notes_markdown initial
 * - Debounce 2s post-typing → patchMeeting({notes_markdown})
 * - Tab Editar / Vista previa con SafeMarkdown render
 * - Indicador savingNotes / savedAt (último guardado)
 * - Disabled si meeting.status in (completed, cancelled)
 *
 * SafeMarkdown reuse desde lib/client-messages/markdown (ADR-023
 * cross-motor reuse).
 */
import { Check, Eye } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SafeMarkdown } from "@/lib/client-messages/markdown";

interface MeetingNotesProps {
  initialNotes: string;
  disabled?: boolean;
  saving?: boolean;
  savedAt: Date | null;
  onSave: (notesMarkdown: string) => Promise<void>;
}

const AUTOSAVE_DEBOUNCE_MS = 2_000;

export function MeetingNotes({
  initialNotes,
  disabled = false,
  saving = false,
  savedAt,
  onSave,
}: MeetingNotesProps) {
  const [notes, setNotes] = React.useState(initialNotes);
  const [showPreview, setShowPreview] = React.useState(false);
  const [pendingSave, setPendingSave] = React.useState(false);
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedRef = React.useRef(initialNotes);

  // Sync external initialNotes changes (e.g. parent reloads meeting)
  React.useEffect(() => {
    setNotes(initialNotes);
    lastSavedRef.current = initialNotes;
  }, [initialNotes]);

  React.useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
    };
  }, []);

  function handleChange(value: string) {
    setNotes(value);
    if (disabled) return;
    if (value === lastSavedRef.current) {
      // unchanged from last saved state
      setPendingSave(false);
      return;
    }
    setPendingSave(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        await onSave(value);
        lastSavedRef.current = value;
      } catch (e) {
        toast.error(
          e instanceof Error ? e.message : "Error guardando notas.",
        );
      } finally {
        setPendingSave(false);
      }
    }, AUTOSAVE_DEBOUNCE_MS);
  }

  const indicatorText = saving || pendingSave
    ? "Guardando…"
    : savedAt
      ? `Guardado ${savedAt.toLocaleTimeString("es-ES", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}`
      : "";

  return (
    <div className="rounded-md border border-fulkro-ink-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-fulkro-primary-700">
          Notas reunión
        </h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-fulkro-ink-500" aria-live="polite">
            {indicatorText && (
              <>
                {!pendingSave && !saving && savedAt && (
                  <Check size={12} className="mr-1 inline text-green-600" />
                )}
                {indicatorText}
              </>
            )}
          </span>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setShowPreview((p) => !p)}
            aria-pressed={showPreview}
          >
            <Eye size={14} className="mr-1" />
            {showPreview ? "Editar" : "Vista previa"}
          </Button>
        </div>
      </div>

      {showPreview ? (
        <div className="min-h-40 rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50/40 p-3">
          {notes.trim() ? (
            <SafeMarkdown body={notes} />
          ) : (
            <p className="text-sm italic text-fulkro-ink-600">
              (sin notas — escribe en pestaña Editar)
            </p>
          )}
        </div>
      ) : (
        <Textarea
          value={notes}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Escribe notas en markdown… (autosave cada 2s)"
          rows={12}
          className="min-h-40"
          aria-label="Notas markdown de la reunión"
          disabled={disabled}
        />
      )}

      {disabled && (
        <p className="mt-2 text-xs italic text-fulkro-ink-500">
          Reunión {disabled ? "completada / cancelada" : ""} — notas
          en modo lectura.
        </p>
      )}
    </div>
  );
}
