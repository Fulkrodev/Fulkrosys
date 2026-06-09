"use client";

/**
 * LiveRecordDetail · sheet drawer detalle entrada registro vivo.
 *
 * Sub-atom 1.C.B fase 4c. Read view + archive action. Edit form completo
 * diferido: actualmente solo se puede archivar (action mas comun cliente)
 * o ver el detalle entry_data como key-value list.
 */
import { Archive, Loader2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { getFieldConfig } from "@/lib/schemas/live-records";
import {
  REGISTER_TYPE_LABELS,
  type LiveRecord,
} from "@/lib/types/live-records";


interface LiveRecordDetailProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  record: LiveRecord | null;
  onArchive?: (recordId: string) => Promise<void>;
}


function formatDateLong(iso: string): string {
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}


function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length === 0 ? "—" : value.join(", ");
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}


export function LiveRecordDetail({
  open,
  onOpenChange,
  record,
  onArchive,
}: LiveRecordDetailProps) {
  const [archiving, setArchiving] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  if (!record) return null;

  const fields = getFieldConfig(record.register_type);
  const entry = record.entry_data || {};

  async function handleArchive() {
    if (!record || !onArchive) return;
    setArchiving(true);
    setArchiveError(null);
    try {
      await onArchive(record.id);
      onOpenChange(false);
    } catch (err) {
      setArchiveError(err instanceof Error ? err.message : "Error al archivar");
    } finally {
      setArchiving(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-lg overflow-y-auto">
        <SheetHeader className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-fulkro-primary-700">
              {record.register_type}
            </span>
            <StatusBadge status={record.status} />
          </div>
          <SheetTitle className="text-fulkro-ink-800">
            {REGISTER_TYPE_LABELS[record.register_type]}
          </SheetTitle>
          <SheetDescription className="text-xs text-fulkro-ink-500">
            ID {record.id.slice(0, 8)}… · creado{" "}
            {formatDateLong(record.created_at)} · actualizado{" "}
            {formatDateLong(record.updated_at)}
          </SheetDescription>
        </SheetHeader>

        <div className="my-6 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-fulkro-ink-600">
            Datos de la entrada
          </h3>
          <dl className="space-y-2 text-sm">
            {fields.map((f) => (
              <div
                key={f.key}
                className="grid grid-cols-3 gap-2 border-b border-fulkro-ink-100 py-1"
              >
                <dt className="col-span-1 text-xs font-medium text-fulkro-ink-600">
                  {f.label}
                </dt>
                <dd className="col-span-2 break-words text-fulkro-ink-800">
                  {formatValue(entry[f.key])}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        {archiveError && (
          <p className="mb-3 rounded border border-red-300 bg-red-50 p-2 text-xs text-red-800">
            {archiveError}
          </p>
        )}

        {record.status === "active" && onArchive && (
          <div className="border-t border-fulkro-ink-200 pt-4">
            <Button
              variant="outline"
              onClick={handleArchive}
              disabled={archiving}
              className="w-full"
            >
              {archiving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
              ) : (
                <Archive className="mr-2 h-4 w-4" aria-hidden />
              )}
              Archivar entrada
            </Button>
            <p className="mt-2 text-[11px] text-fulkro-ink-500">
              Archivar mantiene la entrada visible en el filtro &ldquo;Archivadas&rdquo; y
              en las exportaciones. No la elimina.
            </p>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}


function StatusBadge({ status }: { status: "active" | "archived" }) {
  if (status === "active") {
    return (
      <span className="rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-green-800">
        activa
      </span>
    );
  }
  return (
    <span className="rounded-full bg-fulkro-ink-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-fulkro-ink-600">
      archivada
    </span>
  );
}
