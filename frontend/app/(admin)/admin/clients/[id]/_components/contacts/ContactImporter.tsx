"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

import { ApiError } from "@/lib/api";
import {
  exportContactsCsv,
  importContactsCsv,
} from "@/lib/admin-contacts/api";

const CSV_HEADER =
  "full_name,email,role_title,role_category,preferred_name,phone," +
  "linkedin_url,is_primary,is_signatory,has_portal_access," +
  "notes_marcos,preferred_communication,timezone";

const CSV_SAMPLE =
  CSV_HEADER +
  "\n" +
  'Ana Pérez,ana@example.com,CISO,ciso,,+34 600 11 22 33,,true,true,false,"Sponsor exigente",email,Europe/Madrid';

type Props = {
  clientId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onImported?: () => void;
};

export function ContactImporter({
  clientId,
  open,
  onOpenChange,
  onImported,
}: Props) {
  const [csvText, setCsvText] = useState(CSV_SAMPLE);
  const [busy, setBusy] = useState(false);

  const previewRows = csvText
    .trim()
    .split("\n")
    .slice(1) // skip header
    .filter(Boolean);

  const handleImport = async () => {
    if (csvText.trim().split("\n").length < 2) {
      toast.error("CSV vacío — añade al menos una fila además del header");
      return;
    }
    setBusy(true);
    try {
      const created = await importContactsCsv(clientId, csvText);
      toast.success(
        `Importados ${created.length} contacto${
          created.length === 1 ? "" : "s"
        }${
          created.length < previewRows.length
            ? ` (${previewRows.length - created.length} omitidos por email duplicado)`
            : ""
        }`,
      );
      onImported?.();
      onOpenChange(false);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error importando";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  const handleExport = async () => {
    try {
      const csv = await exportContactsCsv(clientId);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `contactos_${clientId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error exportando";
      toast.error(msg);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Importar / exportar contactos</DialogTitle>
          <DialogDescription>
            Pega filas CSV con la cabecera estándar. Filas con email
            duplicado para el cliente se omiten silenciosamente.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Cabecera obligatoria: <code className="text-[11px]">{CSV_HEADER}</code>
          </p>

          <Textarea
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            rows={10}
            className="font-mono text-xs"
          />

          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Filas a importar (preview): <strong>{previewRows.length}</strong>
          </p>

          <div className="flex flex-wrap items-center gap-2 border-t border-fulkro-ink-100 pt-3">
            <Button
              type="button"
              onClick={() => void handleImport()}
              disabled={busy}
            >
              {busy ? "Importando…" : "Importar"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => void handleExport()}
            >
              Exportar contactos actuales (CSV)
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
