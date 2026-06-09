"use client";

/**
 * AuditLogView · Phase 5.7 auditor portal · audit log inmutable hash chain.
 *
 * Display:
 * - Entries list ordered by seq DESC · timestamp + accion + tabla + usuario
 * - payload_new JSON preview compact + hash_current truncated
 * - Filter por accion (server-side query param)
 * - Total count para project (R6 hash chain verifiable separately)
 */
import { useQuery } from "@tanstack/react-query";
import { Activity, AlertCircle, Download, Loader2 } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  getAuditorPortalAuditLog,
  type AuditorPortalAuditLog,
  type AuditorPortalAuditLogEntry,
} from "@/lib/api/auditor-portal";

interface Props {
  token: string;
}

function EntryRow({ entry }: { entry: AuditorPortalAuditLogEntry }) {
  return (
    <div
      className="rounded-md border border-fulkro-ink-300/60 bg-white p-3"
      data-testid={`auditor-audit-log-entry-${entry.seq}`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-fulkro-ink-900">
            <Badge variant="outline" className="mr-2">
              #{entry.seq}
            </Badge>
            <span className="font-mono">{entry.accion}</span>
          </p>
          <p className="text-[11px] text-fulkro-ink-500">
            tabla: {entry.tabla} · usuario: {entry.usuario ?? "—"}
          </p>
        </div>
        <span className="text-[11px] text-fulkro-ink-500">
          {entry.timestamp
            ? new Date(entry.timestamp).toLocaleString()
            : "—"}
        </span>
      </div>
      {entry.payload_new && Object.keys(entry.payload_new).length > 0 ? (
        <pre className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap rounded bg-fulkro-ink-50 px-2 py-1 text-[10px] text-fulkro-ink-700">
          {JSON.stringify(entry.payload_new, null, 1)}
        </pre>
      ) : null}
      {entry.hash_current ? (
        <p className="mt-1 font-mono text-[10px] text-fulkro-ink-500">
          hash: {entry.hash_current}
        </p>
      ) : null}
    </div>
  );
}

export function AuditLogView({ token }: Props) {
  const [accion, setAccion] = React.useState<string>("");

  const data = useQuery<AuditorPortalAuditLog>({
    queryKey: ["auditor-portal", "audit-log", token, accion],
    queryFn: () =>
      getAuditorPortalAuditLog(token, accion ? { accion } : undefined),
    enabled: Boolean(token),
    staleTime: 30_000,
    retry: false,
  });

  if (data.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="auditor-audit-log-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Cargando registro de auditoría…
      </div>
    );
  }

  if (data.isError || !data.data) {
    return (
      <Alert variant="danger" data-testid="auditor-audit-log-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudo cargar el registro</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4" data-testid="auditor-audit-log-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Registro de auditoría inmutable
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p data-testid="auditor-audit-log-total">
            <strong>{data.data.total_for_project}</strong> entradas totales del
            proyecto · {data.data.returned} mostradas (límite{" "}
            {data.data.limit})
          </p>
          <Alert>
            <AlertTitle>Cadena de hash R6 verificable</AlertTitle>
            <AlertDescription>
              Cada entrada contiene un hash SHA-256 encadenado con la anterior.
              La integridad puede verificarse independientemente con la función
              <code className="font-mono">fn_audit_log_verify_chain()</code>.
            </AlertDescription>
          </Alert>
          <div>
            <label
              htmlFor="auditor-audit-log-accion-filter"
              className="text-[11px] uppercase tracking-wider text-fulkro-ink-500"
            >
              Filtrar por acción (valor exacto)
            </label>
            <Input
              id="auditor-audit-log-accion-filter"
              value={accion}
              onChange={(e) => setAccion(e.target.value)}
              placeholder="ej.: auditor_portal.view · evidence.upload"
              aria-label="Filtrar registro de auditoría por acción"
              data-testid="auditor-audit-log-accion-filter"
              className="h-9"
            />
          </div>
          {/* #7 · exportar el audit trail completo a CSV (streaming · hasta
              1000 filas · respeta el filtro de acción activo). Endpoint
              token-gated · la vista paginada solo muestra un tramo. */}
          <a
            href={`/api/v1/public/auditor-portal/${token}/audit-log.csv${
              accion ? `?accion=${encodeURIComponent(accion)}` : ""
            }`}
            download
            className="inline-flex w-fit items-center gap-1 rounded-md border border-fulkro-ink-300 bg-white px-3 py-1.5 text-[12px] font-medium text-fulkro-ink-700 hover:bg-fulkro-ink-50"
            data-testid="auditor-audit-log-export-csv"
            aria-label="Exportar el registro de auditoría a CSV"
          >
            <Download size={13} aria-hidden="true" />
            Exportar CSV
          </a>
        </CardContent>
      </Card>

      <div className="space-y-2">
        {data.data.entries.length === 0 ? (
          <Alert>
            <AlertTitle>Sin entradas</AlertTitle>
            <AlertDescription>
              No hay entradas que coincidan con el filtro aplicado.
            </AlertDescription>
          </Alert>
        ) : (
          data.data.entries.map((e) => <EntryRow key={e.id} entry={e} />)
        )}
      </div>
    </div>
  );
}
