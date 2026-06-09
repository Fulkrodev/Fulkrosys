/**
 * AuditMode · K.5 Modo auditoría / cross-project search (MB-4.D.2).
 *
 * Backend: GET /api/v1/audit/search?q=...&types=...&date_from=...&date_to=...
 * UNION cross-motor: findings (M04 gaps + M08 verification) + evidence (M07)
 * + documents (M06/M24).
 *
 * Búsqueda lexical (ILIKE) · MVP sin embedding semántico (futuro upgrade).
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  FileSearch,
  FileText,
  Loader2,
  Paperclip,
  Search,
  ShieldAlert,
} from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

interface AuditSearchHit {
  type:
    | "finding_gap"
    | "finding_verification"
    | "evidence"
    | "document";
  id: string;
  project_id: string;
  title: string;
  snippet: string | null;
  severity: string | null;
  estado: string | null;
  measure_code: string | null;
  created_at: string | null;
}

interface AuditSearchResponse {
  query: string;
  types_filter: string[];
  total: number;
  hits: AuditSearchHit[];
}

const TYPE_OPTIONS: { value: AuditSearchHit["type"]; label: string; icon: React.ReactNode }[] = [
  {
    value: "finding_gap",
    label: "Gaps (M04)",
    icon: <ShieldAlert size={11} />,
  },
  {
    value: "finding_verification",
    label: "Findings (M08)",
    icon: <AlertCircle size={11} />,
  },
  { value: "evidence", label: "Evidencias", icon: <Paperclip size={11} /> },
  { value: "document", label: "Documentos", icon: <FileText size={11} /> },
];

const TYPE_LABEL: Record<string, string> = Object.fromEntries(
  TYPE_OPTIONS.map((o) => [o.value, o.label]),
);

export function AuditMode({ projectId }: { projectId: string }) {
  const [q, setQ] = React.useState("");
  const [debouncedQ, setDebouncedQ] = React.useState("");
  const [enabledTypes, setEnabledTypes] = React.useState<Set<string>>(
    new Set(TYPE_OPTIONS.map((o) => o.value)),
  );
  const [scopeProject, setScopeProject] = React.useState(true);

  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(t);
  }, [q]);

  const { data, isFetching, isError, error } = useQuery<AuditSearchResponse>({
    queryKey: [
      "audit-search",
      debouncedQ,
      Array.from(enabledTypes).sort().join(","),
      scopeProject ? projectId : null,
    ],
    queryFn: () => {
      const sp = new URLSearchParams();
      if (debouncedQ.trim()) sp.set("q", debouncedQ.trim());
      Array.from(enabledTypes).forEach((t) => sp.append("types", t));
      if (scopeProject && projectId) sp.set("project_id", projectId);
      sp.set("limit", "50");
      return api<AuditSearchResponse>(
        `/api/v1/audit/search?${sp.toString()}`,
      );
    },
    enabled: enabledTypes.size > 0,
    staleTime: 30_000,
    retry: false,
  });

  function toggleType(t: string) {
    setEnabledTypes((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileSearch size={16} /> Modo auditoría · cross-motor search
          </CardTitle>
          <p className="mt-1 text-xs text-fulkro-ink-500">
            Búsqueda lexical sobre findings (M04 gaps + M08 verification) +
            evidencias (M07) + documentos (M06/M24)
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="audit-search-q">Buscar</Label>
            <div className="relative">
              <Search
                size={14}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-fulkro-ink-500"
              />
              <Input
                id="audit-search-q"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="palabra clave, código de medida, host afectado…"
                className="pl-8"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {TYPE_OPTIONS.map((opt) => {
              const active = enabledTypes.has(opt.value);
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => toggleType(opt.value)}
                  className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[11px] font-medium transition-colors ${
                    active
                      ? "border-fulkro-primary-700 bg-fulkro-primary-700/10 text-fulkro-primary-700"
                      : "border-fulkro-ink-300/60 bg-white text-fulkro-ink-500"
                  }`}
                >
                  {opt.icon}
                  {opt.label}
                </button>
              );
            })}
            <label className="ml-auto inline-flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={scopeProject}
                onChange={(e) => setScopeProject(e.target.checked)}
              />
              Solo este proyecto
            </label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">
            Resultados {data ? `(${data.total})` : ""}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isError ? (
            <Alert variant="danger">
              <AlertTitle>Error en la búsqueda</AlertTitle>
              <AlertDescription>
                {error instanceof Error ? error.message : "Error desconocido"}
              </AlertDescription>
            </Alert>
          ) : isFetching ? (
            <div className="flex items-center gap-2 text-xs text-fulkro-ink-500">
              <Loader2 size={12} className="animate-spin" /> buscando…
            </div>
          ) : !data || data.hits.length === 0 ? (
            <EmptyState
              title={q.trim() ? "Sin resultados" : "Empieza a escribir"}
              description={
                q.trim()
                  ? "Prueba con otros términos o amplía los tipos de filtro."
                  : "El cuadro de búsqueda actualiza resultados al teclear."
              }
            />
          ) : (
            <ul className="space-y-1.5">
              {data.hits.map((hit) => (
                <HitRow key={`${hit.type}-${hit.id}`} hit={hit} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

const TYPE_TONE: Record<string, string> = {
  finding_gap: "border-amber-300 bg-amber-50/50",
  finding_verification: "border-red-300 bg-red-50/50",
  evidence: "border-blue-300 bg-blue-50/50",
  document: "border-fulkro-ink-300/60 bg-white",
};

function HitRow({ hit }: { hit: AuditSearchHit }) {
  return (
    <li
      className={`flex items-start justify-between gap-3 rounded-md border px-3 py-2 ${TYPE_TONE[hit.type] ?? ""}`}
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-fulkro-ink-700">
          {hit.title}
        </p>
        <p className="mt-0.5 flex flex-wrap items-center gap-x-2 font-mono text-[10px] text-fulkro-ink-500">
          <span>{TYPE_LABEL[hit.type] ?? hit.type}</span>
          {hit.measure_code ? <span>· {hit.measure_code}</span> : null}
          {hit.created_at ? (
            <span>· {new Date(hit.created_at).toLocaleDateString()}</span>
          ) : null}
        </p>
        {hit.snippet ? (
          <p className="mt-0.5 line-clamp-2 text-[11px] text-fulkro-ink-700">
            {hit.snippet}
          </p>
        ) : null}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        {hit.severity ? (
          <Badge variant="outline" className="font-mono">
            {hit.severity}
          </Badge>
        ) : null}
        {hit.estado ? (
          <Badge variant="secondary" className="text-[10px]">
            {hit.estado}
          </Badge>
        ) : null}
      </div>
    </li>
  );
}
