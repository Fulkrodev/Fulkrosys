"use client";

import {
  BadgeCheck,
  ExternalLink,
  FileWarning,
  Fingerprint,
  Hash,
  Loader2,
  Search,
  ShieldOff,
  Upload,
  X,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  useEvidenceList,
  useUploadCatalog,
  useUploadEvidence,
} from "@/hooks/useEvidence";
import type { EvidenceListItem } from "@/lib/api/evidence";
import { cn, formatDay } from "@/lib/utils";

// ─── Status derivation (from M07 fields) ─────────────────────────────

type DerivedStatus =
  | "valid"
  | "expiring_soon"
  | "expired"
  | "no_expiry"
  | "pending_signature";

const STATUS_META: Record<
  DerivedStatus,
  { label: string; variant: "success" | "warning" | "danger" | "secondary" | "info" }
> = {
  valid: { label: "Vigente", variant: "success" },
  expiring_soon: { label: "Próxima a vencer", variant: "warning" },
  expired: { label: "Caducada", variant: "danger" },
  no_expiry: { label: "Sin caducidad", variant: "secondary" },
  pending_signature: { label: "Pendiente firma", variant: "warning" },
};

const STATUS_OPTIONS: { value: DerivedStatus | "all"; label: string }[] = [
  { value: "all", label: "Todos los estados" },
  ...(Object.keys(STATUS_META) as DerivedStatus[]).map((k) => ({
    value: k,
    label: STATUS_META[k].label,
  })),
];

function deriveStatus(item: EvidenceListItem): DerivedStatus {
  if (!item.hash_sha256) return "pending_signature";
  if (!item.fecha_caducidad) return "no_expiry";
  if (!item.vigente) return "expired";
  // expiring soon if <= 30 days remaining
  const days = Math.ceil(
    (new Date(item.fecha_caducidad).getTime() - Date.now()) /
      (1000 * 60 * 60 * 24),
  );
  if (days <= 30) return "expiring_soon";
  return "valid";
}

// ─── Component ───────────────────────────────────────────────────────

export function EvidenceVault({ projectId }: { projectId: string }) {
  const { data, isLoading, error } = useEvidenceList(projectId);
  const items = React.useMemo<EvidenceListItem[]>(() => data?.items ?? [], [data]);

  const [search, setSearch] = React.useState("");
  const [status, setStatus] = React.useState<DerivedStatus | "all">("all");
  const [selected, setSelected] = React.useState<EvidenceListItem | null>(null);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((e) => {
      const derived = deriveStatus(e);
      if (status !== "all" && derived !== status) return false;
      if (!q) return true;
      const measure = (e.measure_code ?? "").toLowerCase();
      const nombre = (e.nombre_tipo ?? "").toLowerCase();
      const fichero = (e.fichero_nombre_original ?? "").toLowerCase();
      return (
        measure.includes(q) || nombre.includes(q) || fichero.includes(q)
      );
    });
  }, [items, search, status]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Evidence Vault</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-14 w-full" />
            <Skeleton className="h-40 w-full" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Detalle de evidencia</CardTitle>
          </CardHeader>
          <CardContent>
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="danger">
        <ShieldOff className="h-4 w-4" strokeWidth={2.3} />
        <AlertTitle>No se pudo cargar la bóveda de evidencias</AlertTitle>
        <AlertDescription>{(error as Error).message}</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base">
            <span>
              <InfoTag term="evidencia" display="Evidence Vault" />
            </span>
            <span className="text-xs font-normal text-[color:var(--fulkro-muted)]">
              {filtered.length}/{items.length}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-2 md:grid-cols-4">
            <div className="relative md:col-span-3">
              <Search
                size={18}
                strokeWidth={2.3}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[color:var(--fulkro-muted)]"
              />
              <Input
                placeholder="Búsqueda por medida, tipo o fichero…"
                className="pl-9"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select
              aria-label="Filtrar evidencias por estado"
              value={status}
              onChange={(e) =>
                setStatus(e.target.value as DerivedStatus | "all")
              }
              className={cn(
                "h-10 rounded-md border px-2 text-sm font-medium",
                "border-[color:var(--fulkro-surface-glass-border)]",
                "bg-[color:var(--fulkro-surface-glass)]",
                "text-[color:var(--fulkro-body)]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700",
              )}
            >
              {STATUS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <AdminUploadForm projectId={projectId} />

          {items.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="overflow-x-auto rounded-md border border-[color:var(--fulkro-surface-glass-border)]">
              <table className="min-w-full divide-y divide-[color:var(--fulkro-surface-glass-border)] text-sm">
                <thead className="bg-[color:var(--fulkro-surface-glass-strong)] text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold">Tipo</th>
                    <th className="px-3 py-2 text-left font-semibold">
                      Fichero
                    </th>
                    <th className="px-3 py-2 text-left font-semibold">
                      Medida
                    </th>
                    <th className="px-3 py-2 text-left font-semibold">
                      Estado
                    </th>
                    <th className="px-3 py-2 text-left font-semibold">
                      Firma <TooltipENS term="evidencia_firmada" />
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--fulkro-surface-glass-border)]">
                  {filtered.map((item) => {
                    const active = selected?.id === item.id;
                    const derived = deriveStatus(item);
                    const meta = STATUS_META[derived];
                    const signed = !!item.hash_sha256;
                    return (
                      <tr
                        key={item.id}
                        onClick={() => setSelected(item)}
                        className={cn(
                          "cursor-pointer transition-colors",
                          active
                            ? "bg-fulkro-primary-700/5"
                            : "hover:bg-[color:var(--fulkro-surface-glass)]",
                        )}
                      >
                        <td className="whitespace-nowrap px-3 py-2 font-mono text-xs font-bold text-[color:var(--fulkro-subtitle)]">
                          {item.evidence_type_id ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <p className="font-bold text-[color:var(--fulkro-title)]">
                            {item.fichero_nombre_original ?? "(sin nombre)"}
                          </p>
                          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                            {item.nombre_tipo ?? item.fichero_mime_type ?? "—"}
                          </p>
                        </td>
                        <td className="px-3 py-2">
                          {item.measure_code ? (
                            <span className="rounded bg-[color:var(--fulkro-surface-glass-strong)] px-1.5 py-0.5 font-mono text-xs font-semibold text-[color:var(--fulkro-body)]">
                              {item.measure_code}
                            </span>
                          ) : (
                            <span className="text-xs text-[color:var(--fulkro-muted)]">
                              —
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2">
                          <Badge variant={meta.variant}>{meta.label}</Badge>
                        </td>
                        <td className="px-3 py-2">
                          {signed ? (
                            <span className="inline-flex items-center gap-1 text-fulkro-success">
                              <BadgeCheck size={16} strokeWidth={2.3} />
                              <span className="text-xs font-semibold">
                                <InfoTag term="Ed25519" display="Ed25519" />
                              </span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[color:var(--fulkro-muted)]">
                              <FileWarning size={16} strokeWidth={2.3} />
                              <span className="text-xs font-semibold">
                                Sin firma
                              </span>
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {filtered.length === 0 && (
                    <tr>
                      <td
                        colSpan={5}
                        className="px-3 py-6 text-center text-base font-medium text-[color:var(--fulkro-muted)]"
                      >
                        Ninguna evidencia coincide con los filtros.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <EvidenceDetailPanel
        item={selected}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────

function EmptyState() {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
        <div className="rounded-full bg-[color:var(--fulkro-surface-glass-strong)] p-4">
          <Fingerprint
            size={28}
            strokeWidth={2.3}
            className="text-[color:var(--fulkro-subtitle)]"
          />
        </div>
        <div>
          <p className="text-base font-bold text-[color:var(--fulkro-title)]">
            Bóveda vacía
          </p>
          <p className="mt-1 max-w-md text-sm font-medium text-[color:var(--fulkro-body)]">
            Aún no hay evidencias subidas para este proyecto. Arrastra ficheros
            o usa el botón superior para añadir la primera.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Admin upload form ───────────────────────────────────────────────

const SELECT_CLS = cn(
  "h-10 w-full rounded-md border px-2 text-sm font-medium",
  "border-[color:var(--fulkro-surface-glass-border)]",
  "bg-[color:var(--fulkro-surface-glass)]",
  "text-[color:var(--fulkro-body)]",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700",
  "disabled:cursor-not-allowed disabled:opacity-60",
);

function AdminUploadForm({ projectId }: { projectId: string }) {
  // §3.1 audit-2026-06-15 / W9-1 · ANTES esta zona no subía nada (botón
  // honest-disabled) porque ningún endpoint exponía el catálogo de tipos. Ahora
  // se cablea el formulario admin real (fichero + tipo + medida) contra
  // GET upload-catalog + POST .../upload (require_owner · solo Marcos).
  const { data: catalog, isLoading, error } = useUploadCatalog(projectId);
  const upload = useUploadEvidence(projectId);

  const [file, setFile] = React.useState<File | null>(null);
  const [evidenceTypeId, setEvidenceTypeId] = React.useState("");
  const [measureCode, setMeasureCode] = React.useState("");
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const selectedType = React.useMemo(
    () => catalog?.evidence_types.find((t) => t.id === evidenceTypeId) ?? null,
    [catalog, evidenceTypeId],
  );
  const acceptAttr = selectedType?.allowed_extensions.join(",") ?? undefined;

  const canSubmit =
    !!file && !!evidenceTypeId && !!measureCode && !upload.isPending;

  function reset() {
    setFile(null);
    setEvidenceTypeId("");
    setMeasureCode("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !evidenceTypeId || !measureCode) return;
    upload.mutate(
      { file, evidence_type_id: evidenceTypeId, measure_code: measureCode },
      {
        onSuccess: () => {
          toast.success(`Evidencia "${file.name}" subida y firmada (Ed25519).`);
          reset();
        },
        onError: (err) =>
          toast.error(
            `No se pudo subir la evidencia: ${(err as Error).message}`,
          ),
      },
    );
  }

  if (error) {
    return (
      <Alert variant="danger">
        <ShieldOff className="h-4 w-4" strokeWidth={2.3} />
        <AlertTitle>No se pudo cargar el catálogo de subida</AlertTitle>
        <AlertDescription>{(error as Error).message}</AlertDescription>
      </Alert>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-md border border-dashed border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)] p-3"
    >
      <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-[color:var(--fulkro-subtitle)]">
        <Upload size={16} strokeWidth={2.3} />
        Subir evidencia (admin)
      </div>

      <div className="grid gap-2 md:grid-cols-3">
        <div className="md:col-span-1">
          <label
            htmlFor="ev-type"
            className="mb-1 block text-xs font-semibold text-[color:var(--fulkro-muted)]"
          >
            Tipo de <InfoTag term="evidencia" display="evidencia" />
          </label>
          <select
            id="ev-type"
            aria-label="Tipo de evidencia"
            className={SELECT_CLS}
            value={evidenceTypeId}
            disabled={isLoading || !catalog}
            onChange={(e) => {
              setEvidenceTypeId(e.target.value);
              setFile(null);
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
          >
            <option value="">Selecciona un tipo…</option>
            {(catalog?.evidence_types ?? []).map((t) => (
              <option key={t.id} value={t.id}>
                {t.label} ({t.allowed_extensions.join(", ")} · {t.max_size_mb}MB)
              </option>
            ))}
          </select>
        </div>

        <div className="md:col-span-1">
          <label
            htmlFor="ev-measure"
            className="mb-1 block text-xs font-semibold text-[color:var(--fulkro-muted)]"
          >
            Medida ENS{catalog?.categoria ? ` · ${catalog.categoria}` : ""}
          </label>
          <select
            id="ev-measure"
            aria-label="Medida ENS asociada"
            className={SELECT_CLS}
            value={measureCode}
            disabled={isLoading || !catalog}
            onChange={(e) => setMeasureCode(e.target.value)}
          >
            <option value="">Selecciona una medida…</option>
            {(catalog?.measures ?? []).map((m) => (
              <option key={m.codigo} value={m.codigo}>
                {m.codigo} — {m.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className="md:col-span-1">
          <label
            htmlFor="ev-file"
            className="mb-1 block text-xs font-semibold text-[color:var(--fulkro-muted)]"
          >
            Fichero
          </label>
          <input
            id="ev-file"
            ref={fileInputRef}
            type="file"
            aria-label="Fichero de evidencia"
            accept={acceptAttr}
            disabled={isLoading || !catalog}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className={cn(
              "h-10 w-full rounded-md border px-2 py-1.5 text-sm",
              "border-[color:var(--fulkro-surface-glass-border)]",
              "bg-[color:var(--fulkro-surface-glass)]",
              "text-[color:var(--fulkro-body)]",
              "file:mr-2 file:rounded file:border-0 file:bg-fulkro-primary-700 file:px-2 file:py-1 file:text-xs file:font-semibold file:text-white",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          />
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="text-xs font-medium text-[color:var(--fulkro-muted)]">
          {selectedType
            ? selectedType.descripcion
            : "Selecciona tipo, medida y fichero para subir la evidencia."}
        </p>
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={!canSubmit}
          data-testid="evidence-admin-upload"
        >
          {upload.isPending ? (
            <>
              <Loader2 size={16} strokeWidth={2.3} className="animate-spin" />
              Subiendo…
            </>
          ) : (
            <>
              <Upload size={16} strokeWidth={2.3} /> Subir evidencia
            </>
          )}
        </Button>
      </div>
    </form>
  );
}

// ─── Detail panel ────────────────────────────────────────────────────

function EvidenceDetailPanel({
  item,
  onClose,
}: {
  item: EvidenceListItem | null;
  onClose: () => void;
}) {
  return (
    <Card className="xl:sticky xl:top-4 xl:max-h-[calc(100dvh-6rem)] xl:overflow-y-auto">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle>Detalle de evidencia</CardTitle>
        {item && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Cerrar"
          >
            <X size={18} strokeWidth={2.3} />
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {!item ? (
          <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
            <div className="mb-4 rounded-full bg-[color:var(--fulkro-surface-glass-strong)] p-4">
              <Search
                size={28}
                strokeWidth={2.3}
                className="text-[color:var(--fulkro-subtitle)]"
              />
            </div>
            <p className="max-w-xs text-base font-medium text-[color:var(--fulkro-body)]">
              Selecciona una evidencia para ver su detalle, hash y firma
              Ed25519.
            </p>
          </div>
        ) : (
          <>
            <div>
              <p className="font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
                {item.evidence_type_id ?? "—"}
              </p>
              <p className="text-xl font-bold text-[color:var(--fulkro-title)]">
                {item.fichero_nombre_original ?? "(sin nombre)"}
              </p>
              <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
                {item.nombre_tipo ?? item.fichero_mime_type ?? "—"}
              </p>
            </div>

            <dl className="grid grid-cols-2 gap-2 text-xs">
              <Field
                label="Estado"
                value={STATUS_META[deriveStatus(item)].label}
              />
              <Field label="Medida" value={item.measure_code ?? "—"} />
              <Field
                label="Fecha evidencia"
                value={item.fecha_evidencia ? formatDay(item.fecha_evidencia) : "—"}
              />
              <Field
                label="Vigencia"
                value={
                  item.fecha_caducidad ? formatDay(item.fecha_caducidad) : "—"
                }
              />
              <Field
                label="Tipo MIME"
                value={item.fichero_mime_type ?? "—"}
              />
              <Field
                label="Firma"
                value={item.hash_sha256 ? "Ed25519" : "Sin firma"}
              />
            </dl>

            {item.hash_sha256 && (
              <div className="rounded-md border border-[color:var(--fulkro-surface-glass-border)] p-3 text-xs">
                <p className="flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
                  <Hash size={14} strokeWidth={2.3} /> hash
                </p>
                <p className="mt-1 break-all font-mono text-[color:var(--fulkro-body)]">
                  {item.hash_sha256}
                </p>
              </div>
            )}

            {/* §3.1 · estos botones no tenían onClick (fingían completitud) ·
                deshabilitados con tooltip hasta cablear preview/verificación reales. */}
            <div className="space-y-2">
              <Button
                variant="primary"
                size="md"
                className="w-full"
                disabled
                title="Próximamente"
              >
                <ExternalLink size={16} strokeWidth={2.3} /> Abrir preview (próximamente)
              </Button>
              <Button
                variant="outline"
                size="md"
                className="w-full"
                disabled
                title="Próximamente"
              >
                <Fingerprint size={16} strokeWidth={2.3} /> Verificar firma (próximamente)
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-[color:var(--fulkro-surface-glass)] px-2 py-1.5">
      <dt className="text-xs font-bold uppercase tracking-wider text-[color:var(--fulkro-subtitle)]">
        {label}
      </dt>
      <dd className="text-sm font-medium text-[color:var(--fulkro-body)]">
        {value}
      </dd>
    </div>
  );
}
