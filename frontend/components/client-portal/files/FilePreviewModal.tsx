"use client";

/**
 * FilePreviewModal · same-origin iframe PDF preview.
 * SAN-E v3.MB-6 atom 7 · Q4 B browser native (zero deps).
 *
 * Backend serves Content-Disposition: inline + X-Frame-Options: SAMEORIGIN.
 * Future atom 7.bis: upgrade react-pdf si Marcos quiere zoom/annotation.
 */
import { Download, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useEscapeKey } from "@/hooks/useEscapeKey";

interface Props {
  open: boolean;
  onClose: () => void;
  previewUrl: string | null;
  downloadUrl: string | null;
  title: string;
}

export function FilePreviewModal({
  open,
  onClose,
  previewUrl,
  downloadUrl,
  title,
}: Props) {
  useEscapeKey(onClose, open);
  if (!open || !previewUrl) return null;

  return (
    <div
      data-testid="file-preview-modal"
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="relative flex h-[85vh] w-full max-w-5xl flex-col rounded-lg bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between gap-3 border-b border-fulkro-ink-200 px-4 py-3">
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold text-sm text-fulkro-ink-800 truncate">
              {title}
            </h2>
            <p className="text-xs text-fulkro-ink-500">
              Vista previa PDF · same-origin
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            {downloadUrl && (
              <a
                href={downloadUrl}
                download
                className="inline-flex"
                data-testid="file-preview-download"
              >
                <Button size="sm" variant="outline">
                  <Download className="h-3.5 w-3.5" aria-hidden />
                  <span className="ml-1.5">Descargar</span>
                </Button>
              </a>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={onClose}
              aria-label="Cerrar"
              data-testid="file-preview-close"
            >
              <X className="h-4 w-4" aria-hidden />
            </Button>
          </div>
        </header>
        <iframe
          src={previewUrl}
          title={title}
          className="flex-1 w-full rounded-b-lg"
          data-testid="file-preview-iframe"
        />
      </div>
    </div>
  );
}
