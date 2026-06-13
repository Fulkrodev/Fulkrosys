"use client";

import * as React from "react";
import { Loader2, Plus, ShieldCheck, Wrench } from "lucide-react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useAuthorizeRemediationJob,
  useCreateRemediationJob,
  useExecuteRemediationJob,
  useRemediationCatalog,
  useRemediationConnectors,
  useRemediationJobs,
} from "@/hooks/useRemediationAdmin";
import type {
  RemediationJob,
  RemediationTier,
} from "@/lib/api/remediation-admin";

const TIER_META: Record<RemediationTier, { label: string; className: string }> = {
  safe_auto: {
    label: "Seguro · automático",
    className: "bg-emerald-600 text-white",
  },
  guarded: {
    label: "Riesgo · autorización previa",
    className: "bg-amber-600 text-white",
  },
  blocked: {
    label: "Destructivo · manual",
    className: "bg-rose-700 text-white",
  },
};

const STATUS_META: Record<string, { label: string; className: string }> = {
  queued: { label: "En cola", className: "bg-slate-600 text-white" },
  awaiting_authorization: {
    label: "Esperando autorización",
    className: "bg-amber-600 text-white",
  },
  blocked: { label: "Bloqueado (manual)", className: "bg-slate-700 text-white" },
  preflight: { label: "Comprobando", className: "bg-sky-600 text-white" },
  snapshotting: { label: "Copia de seguridad", className: "bg-sky-600 text-white" },
  applying: { label: "Aplicando", className: "bg-sky-700 text-white" },
  verifying: { label: "Verificando", className: "bg-sky-700 text-white" },
  succeeded: { label: "Resuelto", className: "bg-emerald-700 text-white" },
  skipped_compliant: {
    label: "Ya cumplía",
    className: "bg-emerald-600 text-white",
  },
  failed: { label: "Falló", className: "bg-rose-700 text-white" },
  rolled_back: { label: "Revertido", className: "bg-amber-700 text-white" },
};

function statusMeta(status: string) {
  return STATUS_META[status] ?? { label: status, className: "bg-slate-600 text-white" };
}

export function RemediationConsolePanel({ projectId }: { projectId: string }) {
  const jobsQ = useRemediationJobs(projectId);
  const catalogQ = useRemediationCatalog(projectId);
  const [createOpen, setCreateOpen] = React.useState(false);

  const jobs = jobsQ.data?.jobs ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold text-slate-900">
            <Wrench className="size-6 text-fulkro-primary-900" />
            Remediación automática
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">
            Aplica arreglos a los hallazgos detectados. Lo que no tiene riesgo se
            aplica solo; lo que sí, requiere autorización previa del cliente.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} data-testid="remediation-create-open">
          <Plus className="mr-1.5 size-4" /> Crear acción
        </Button>
      </div>

      <Alert className="border-sky-200 bg-sky-50">
        <ShieldCheck className="size-4 text-sky-700" />
        <AlertTitle className="text-sky-900">Seguridad por diseño</AlertTitle>
        <AlertDescription className="text-sky-800">
          La escritura en sistemas del cliente está desactivada por defecto
          (kill-switch en 3 capas). Cada acción es reversible: se guarda una copia
          previa y se revierte sola si la verificación falla. Todo queda en el
          registro de auditoría (cadena hash R6).
        </AlertDescription>
      </Alert>

      <Card className="border-slate-200 bg-white">
        <CardHeader>
          <CardTitle className="text-lg text-slate-900">Cola de remediación</CardTitle>
          <CardDescription className="text-slate-600">
            Estado de cada acción · {jobs.length} en total
          </CardDescription>
        </CardHeader>
        <CardContent>
          {jobsQ.isLoading ? (
            <div className="flex items-center gap-2 py-6 text-slate-600">
              <Loader2 className="size-4 animate-spin" /> Cargando…
            </div>
          ) : jobsQ.isError ? (
            <Alert variant="danger">
              <AlertTitle>No pudimos cargar la cola</AlertTitle>
              <AlertDescription>
                Reintenta en unos segundos.
              </AlertDescription>
              <Button
                variant="outline"
                size="sm"
                className="mt-2"
                onClick={() => void jobsQ.refetch()}
                data-testid="remediation-jobs-retry"
              >
                Reintentar
              </Button>
            </Alert>
          ) : jobs.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">
              Sin acciones todavía. Crea una desde un hallazgo o con el botón
              «Crear acción».
            </p>
          ) : (
            <ul className="space-y-3">
              {jobs.map((job) => (
                <JobRow key={job.id} projectId={projectId} job={job} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <CreateJobDialog
        projectId={projectId}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      {catalogQ.data ? (
        <CatalogReference actions={catalogQ.data.actions} />
      ) : null}
    </div>
  );
}

function JobRow({ projectId, job }: { projectId: string; job: RemediationJob }) {
  const authorize = useAuthorizeRemediationJob(projectId);
  const execute = useExecuteRemediationJob(projectId);
  const tier = TIER_META[job.tier];
  const st = statusMeta(job.status);

  return (
    <li className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-slate-900">{job.title}</p>
          <p className="mt-0.5 text-xs text-slate-500">
            {job.target_ref ?? "—"} · {job.ens_measures.join(", ") || "—"}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge className={tier?.className}>{tier?.label ?? job.tier}</Badge>
          <Badge className={st.className}>{st.label}</Badge>
        </div>
      </div>

      {job.error_message ? (
        <p className="mt-2 rounded bg-rose-50 px-2 py-1 text-xs text-rose-800">
          {job.error_message}
        </p>
      ) : null}

      <div className="mt-3 flex items-center gap-2">
        {job.status === "awaiting_authorization" ? (
          <Button
            size="sm"
            disabled={authorize.isPending}
            onClick={() =>
              authorize.mutate(job.id, {
                onSuccess: () => toast.success("Acción autorizada"),
                onError: (e) => toast.error(String(e)),
              })
            }
            data-testid="remediation-authorize"
          >
            {authorize.isPending ? (
              <Loader2 className="mr-1 size-3.5 animate-spin" />
            ) : null}
            Autorizar
          </Button>
        ) : null}
        {job.status === "queued" ? (
          <Button
            size="sm"
            variant="outline"
            disabled={execute.isPending}
            onClick={() =>
              execute.mutate(job.id, {
                onSuccess: (j) =>
                  toast.success(`Ejecutado · ${statusMeta(j.status).label}`),
                onError: (e) => toast.error(String(e)),
              })
            }
            data-testid="remediation-execute"
          >
            {execute.isPending ? (
              <Loader2 className="mr-1 size-3.5 animate-spin" />
            ) : null}
            Ejecutar
          </Button>
        ) : null}
        {job.status === "blocked" ? (
          <span className="text-xs text-slate-500">
            Acción destructiva · la aplica una persona manualmente.
          </span>
        ) : null}
      </div>
    </li>
  );
}

function CreateJobDialog({
  projectId,
  open,
  onOpenChange,
}: {
  projectId: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const catalogQ = useRemediationCatalog(projectId);
  const connectorsQ = useRemediationConnectors(projectId);
  const create = useCreateRemediationJob(projectId);

  const [actionType, setActionType] = React.useState("");
  const [connectorId, setConnectorId] = React.useState("");
  const [targetRef, setTargetRef] = React.useState("");
  const [dryRun, setDryRun] = React.useState(true);

  const actions = catalogQ.data?.actions ?? [];
  const connectors = connectorsQ.data ?? [];

  const submit = () => {
    if (!actionType) {
      toast.error("Elige una acción");
      return;
    }
    create.mutate(
      {
        action_type: actionType,
        source_kind: "cloud_gap",
        connector_id: connectorId || null,
        target_ref: targetRef || null,
        dry_run: dryRun,
      },
      {
        onSuccess: () => {
          toast.success("Acción creada");
          onOpenChange(false);
          setActionType("");
          setTargetRef("");
        },
        onError: (e) => toast.error(String(e)),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-white">
        <DialogHeader>
          <DialogTitle className="text-slate-900">Crear acción de remediación</DialogTitle>
          <DialogDescription className="text-slate-600">
            Elige qué corregir. El nivel de riesgo se asigna de forma automática.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <label className="block text-sm font-medium text-slate-800">
            Acción
            <select
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              value={actionType}
              onChange={(e) => setActionType(e.target.value)}
              data-testid="remediation-action-select"
            >
              <option value="">— Elige —</option>
              {actions.map((a) => (
                <option key={a.action_type} value={a.action_type}>
                  {a.title} ({a.tier})
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-medium text-slate-800">
            Conector cloud
            <select
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              value={connectorId}
              onChange={(e) => setConnectorId(e.target.value)}
            >
              <option value="">— Ninguno —</option>
              {connectors.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.provider} ({c.status})
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-medium text-slate-800">
            Recurso objetivo (ARN / ID / host)
            <input
              type="text"
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              value={targetRef}
              onChange={(e) => setTargetRef(e.target.value)}
              placeholder="arn:aws:s3:::mi-bucket"
            />
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-800">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
            />
            Ensayo (dry-run · no aplica cambios reales)
          </label>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button
            onClick={submit}
            disabled={create.isPending}
            data-testid="remediation-create-submit"
          >
            {create.isPending ? (
              <Loader2 className="mr-1 size-3.5 animate-spin" />
            ) : null}
            Crear
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CatalogReference({
  actions,
}: {
  actions: ReadonlyArray<{
    action_type: string;
    title: string;
    tier: RemediationTier;
    cliente_blurb: string;
    ens_measures: string[];
  }>;
}) {
  return (
    <Card className="border-slate-200 bg-white">
      <CardHeader>
        <CardTitle className="text-base text-slate-900">
          Catálogo de acciones disponibles
        </CardTitle>
        <CardDescription className="text-slate-600">
          Qué puede corregir el sistema y con qué nivel de riesgo.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {actions.map((a) => {
            const tier = TIER_META[a.tier];
            return (
              <li
                key={a.action_type}
                className="flex items-start justify-between gap-3 rounded-md border border-slate-100 bg-slate-50 p-3"
              >
                <div className="min-w-0">
                  <p className="font-medium text-slate-900">{a.title}</p>
                  <p className="mt-0.5 text-xs text-slate-600">{a.cliente_blurb}</p>
                  <p className="mt-0.5 text-[11px] text-slate-400">
                    {a.ens_measures.join(", ")}
                  </p>
                </div>
                <Badge className={tier?.className}>{tier?.label ?? a.tier}</Badge>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
