"use client";

/**
 * FileVersionDialog · current + collapsed history list.
 * SAN-E v3.MB-6 atom 7 · Q6 B cement.
 *
 * Empty state si NO versions previas · "v1.0 inicial" (audit-friendly).
 */
import { useEffect, useState } from "react";
import { History, Loader2, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ClientApiError } from "@/lib/client-portal-api";
import {
  type DocumentVersionsResponse,
  getDocumentVersions,
} from "@/lib/api/files-extended";

interface Props {
  open: boolean;
  onClose: () => void;
  documentId: string | null;
}

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES");
  } catch {
    return iso;
  }
}

export function FileVersionDialog({ open, onClose, documentId }: Props) {
  const [data, setData] = useState<DocumentVersionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !documentId) {
      setData(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    void getDocumentVersions(documentId)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ClientApiError) setError(err.message);
        else setError("Error cargando versiones");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, documentId]);

  if (!open) return null;

  return (
    <div
      data-testid="file-version-dialog"
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg rounded-lg bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 border-b border-fulkro-ink-200 px-4 py-3">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <History
              className="h-4 w-4 text-fulkro-primary-700 flex-shrink-0"
              aria-hidden
            />
            <h2 className="font-semibold text-sm text-fulkro-ink-800 truncate">
              Historial de versiones
            </h2>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={onClose}
            aria-label="Cerrar"
          >
            <X className="h-4 w-4" aria-hidden />
          </Button>
        </header>
        <div className="p-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-fulkro-ink-500">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              <span>Cargando versiones…</span>
            </div>
          )}
          {error && (
            <div className="text-sm text-destructive">{error}</div>
          )}
          {data && (
            <>
              <div className="rounded-md bg-fulkro-primary-700/5 border border-fulkro-primary-700/20 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm font-semibold text-fulkro-ink-800">
                    Versión actual{" "}
                    <Badge variant="info">{data.current_version ?? "—"}</Badge>
                  </div>
                </div>
                {data.codigo && (
                  <div className="text-xs text-fulkro-ink-600 mt-1">
                    {data.codigo}
                  </div>
                )}
              </div>
              {data.history.length === 0 ? (
                <div className="text-sm text-fulkro-ink-500 italic">
                  No hay versiones anteriores · documento inicial v
                  {data.current_version ?? "1.0"}.
                </div>
              ) : (
                <ol className="space-y-2 text-sm">
                  {data.history.map((v) => (
                    <li
                      key={v.id}
                      className="rounded border border-fulkro-ink-200 p-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-fulkro-ink-800">
                          v{v.version}
                        </span>
                        {v.firmado_at && (
                          <Badge variant="success">Firmada</Badge>
                        )}
                      </div>
                      <div className="text-xs text-fulkro-ink-600 mt-1 space-y-0.5">
                        {v.generado_at && (
                          <div>Generada: {fmtDateTime(v.generado_at)}</div>
                        )}
                        {v.firmado_por && v.firmado_at && (
                          <div>
                            Firmada por {v.firmado_por} ({fmtDateTime(v.firmado_at)})
                          </div>
                        )}
                        {v.hash_sha256 && (
                          <div className="font-mono break-all text-fulkro-ink-500">
                            SHA-256: {v.hash_sha256.slice(0, 16)}…
                          </div>
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
