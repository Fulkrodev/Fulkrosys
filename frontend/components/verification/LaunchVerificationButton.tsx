"use client";

import { Loader2, PlayCircle, X } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { InfoTag } from "@/components/ui/info-tag";
import { useCreateRun } from "@/hooks/useVerification";
import type {
  VerificationCategory,
  VerificationMode,
} from "@/lib/verification-types";
import { cn } from "@/lib/utils";

const CATEGORY_LIST: Array<{
  value: VerificationCategory;
  title: string;
  description: string;
  tools: string;
}> = [
  {
    value: "BASICO",
    title: "Básica",
    description:
      "Scan nocturno ligero (nmap + nuclei + testssl + dns_checker). Recomendado para operación continua.",
    tools: "nmap · nuclei · testssl · dns",
  },
  {
    value: "MEDIO",
    title: "Media",
    description:
      "Scan ampliado con análisis web (ZAP) y hardening de sistemas (Lynis).",
    tools: "+ zap · lynis · ad",
  },
  {
    value: "ALTO",
    title: "Alta (interna)",
    description:
      "Scan completo con prowler y openvas. Para categoría Alta combinar con handoff a pentester externo.",
    tools: "+ prowler · openvas",
  },
];

export function LaunchVerificationButton({ projectId }: { projectId: string }) {
  const [open, setOpen] = React.useState(false);
  const [category, setCategory] = React.useState<VerificationCategory>("BASICO");
  const [mode] = React.useState<VerificationMode>("internal");
  const [scheduleNow, setScheduleNow] = React.useState(false);
  const createRun = useCreateRun(projectId);

  async function handleLaunch() {
    try {
      const run = await createRun.mutateAsync({
        category,
        mode,
        schedule_now: scheduleNow,
      });
      toast.success(
        `Verificación ${category} creada (${run.id.slice(0, 8)}…)`,
        {
          description: scheduleNow
            ? "Ejecución inmediata solicitada."
            : "En cola hasta la ventana 22:00-06:00.",
        },
      );
      setOpen(false);
    } catch (err) {
      toast.error("No se pudo crear la verificación", {
        description: (err as Error).message,
      });
    }
  }

  return (
    <>
      <Button
        onClick={() => setOpen(true)}
        className="gap-2"
      >
        <PlayCircle size={16} /> Lanzar verificación
      </Button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-fulkro-primary-700/30 px-4 animate-fade-in"
          role="dialog"
          aria-modal="true"
          aria-labelledby="launch-verification-title"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded-lg border border-[color:var(--fulkro-surface-glass-border)] bg-white shadow-ink"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-fulkro-ink-300/40 p-4">
              <h2 id="launch-verification-title" className="text-xl font-bold text-[color:var(--fulkro-title)]">
                <InfoTag term="workflow_verificacion" display="Lanzar verificación técnica" />
              </h2>
              <button
                type="button"
                aria-label="Cerrar"
                onClick={() => setOpen(false)}
                className="rounded p-1 text-fulkro-ink-500 hover:bg-fulkro-ink-100"
              >
                <X size={16} />
              </button>
            </div>
            <div className="flex flex-col gap-3 p-4">
              {CATEGORY_LIST.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setCategory(c.value)}
                  className={cn(
                    "rounded-md border p-3 text-left transition-colors",
                    category === c.value
                      ? "border-fulkro-primary-700 bg-fulkro-primary-700/5"
                      : "border-[color:var(--fulkro-surface-glass-border)] hover:bg-fulkro-ink-100",
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-fulkro-primary-700">
                      {c.title}
                    </span>
                    {category === c.value && (
                      <span className="rounded-full bg-fulkro-primary-700 px-2 py-0.5 text-[10px] font-semibold uppercase text-white">
                        Seleccionada
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm font-medium text-[color:var(--fulkro-muted)]">
                    {c.description}
                  </p>
                  <p className="mt-1 font-mono text-sm font-medium text-[color:var(--fulkro-muted)]/80">
                    {c.tools}
                  </p>
                </button>
              ))}
              <label className="flex items-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]">
                <input
                  type="checkbox"
                  checked={scheduleNow}
                  onChange={(e) => setScheduleNow(e.target.checked)}
                  className="rounded border-[color:var(--fulkro-surface-glass-border)]"
                />
                Ejecutar ya (bypass ventana nocturna)
              </label>
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-fulkro-ink-300/40 p-4">
              <Button
                variant="outline"
                onClick={() => setOpen(false)}
                disabled={createRun.isPending}
              >
                Cancelar
              </Button>
              <Button
                onClick={handleLaunch}
                disabled={createRun.isPending}
                className="gap-2"
              >
                {createRun.isPending && <Loader2 size={14} className="animate-spin" />}
                Lanzar {category.toLowerCase()}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
