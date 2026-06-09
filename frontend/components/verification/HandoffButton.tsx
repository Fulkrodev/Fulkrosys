"use client";

import { Briefcase, Loader2, X } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useCreateHandoff, useVerificationRuns } from "@/hooks/useVerification";

export function HandoffButton({ projectId }: { projectId: string }) {
  const [open, setOpen] = React.useState(false);
  const runs = useVerificationRuns(projectId);
  const create = useCreateHandoff(projectId);

  const [runId, setRunId] = React.useState<string>("");
  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [cert, setCert] = React.useState("OSCP");
  const [deadline, setDeadline] = React.useState("");

  const altaRuns = (runs.data?.runs ?? []).filter(
    (r) => r.category === "ALTO" || r.mode === "external_handoff",
  );

  async function submit() {
    if (!runId || !name || !email || !cert) {
      toast.error("Faltan datos del pentester");
      return;
    }
    try {
      const h = await create.mutateAsync({
        run_id: runId,
        pentester_name: name,
        pentester_email: email,
        pentester_cert: cert,
        deadline: deadline ? new Date(deadline).toISOString() : undefined,
        findings_submission_method: "both",
      });
      toast.success("Traspaso creado", {
        description: `${h.package_documents.length} documentos generados para ${name}`,
      });
      setOpen(false);
      setRunId("");
      setName("");
      setEmail("");
      setDeadline("");
    } catch (err) {
      toast.error("No se pudo crear el traspaso", {
        description: (err as Error).message,
      });
    }
  }

  return (
    <>
      <Button
        variant="outline"
        onClick={() => setOpen(true)}
        className="gap-2 border-fulkro-primary-700/40 text-fulkro-primary-700 hover:bg-fulkro-primary-700/5"
      >
        <Briefcase size={14} /> Traspaso al pentester
      </Button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-fulkro-primary-700/30 px-4 animate-fade-in"
          role="dialog"
          aria-modal="true"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-lg rounded-lg border border-[color:var(--fulkro-surface-glass-border)] bg-white shadow-ink"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-fulkro-ink-300/40 p-4">
              <h2 className="text-xl font-bold text-[color:var(--fulkro-title)]">
                Preparar traspaso al pentester externo{" "}
                <TooltipENS term="purple_team" />
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
              <div className="flex flex-col gap-1">
                <Label htmlFor="handoff-run">Run asociado</Label>
                <select
                  id="handoff-run"
                  value={runId}
                  onChange={(e) => setRunId(e.target.value)}
                  className="rounded border border-[color:var(--fulkro-surface-glass-border)] bg-white px-2 py-1.5 text-sm"
                >
                  <option value="">
                    — Selecciona run con categoría Alta —
                  </option>
                  {altaRuns.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.id.slice(0, 8)}… · {r.category} · {r.status}
                    </option>
                  ))}
                </select>
                {altaRuns.length === 0 && (
                  <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                    No hay runs de categoría Alta. Crea uno primero.
                  </p>
                )}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="flex flex-col gap-1">
                  <Label htmlFor="p-name">Nombre del pentester</Label>
                  <Input
                    id="p-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Ej. Laura García"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <Label htmlFor="p-email">Email</Label>
                  <Input
                    id="p-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="pentester@empresa.es"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <Label htmlFor="p-cert">Certificación</Label>
                  <Input
                    id="p-cert"
                    value={cert}
                    onChange={(e) => setCert(e.target.value)}
                    placeholder="OSCP, OSEP, GPEN…"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <Label htmlFor="p-deadline">Vencimiento</Label>
                  <Input
                    id="p-deadline"
                    type="date"
                    value={deadline}
                    onChange={(e) => setDeadline(e.target.value)}
                  />
                </div>
              </div>
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                Se generarán 7 documentos (scope + ROE, inventario, red, NDA,
                autorización) y un enlace mágico con VPN cifrada.
              </p>
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-fulkro-ink-300/40 p-4">
              <Button
                variant="outline"
                onClick={() => setOpen(false)}
                disabled={create.isPending}
              >
                Cancelar
              </Button>
              <Button
                onClick={submit}
                disabled={create.isPending || !runId}
                className="gap-2"
              >
                {create.isPending && (
                  <Loader2 size={14} className="animate-spin" />
                )}
                Generar paquete
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
