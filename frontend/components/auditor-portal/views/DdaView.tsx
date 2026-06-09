"use client";

/**
 * DdaView · Phase 5.2 auditor portal · 73 medidas DdA read-only.
 *
 * Per medida display: código + nombre + familia + descripción +
 * justificación cliente + estado de implementación + review status.
 * Filter por familia (org · op · mp) · search por código/nombre client-side.
 *
 * Download DdA firmado PDF (button placeholder · backend M03 signing
 * service activation deferred sub-atom backend completion Phase 5.6 E-041).
 */
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, FileText, Loader2, Search } from "lucide-react";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  getAuditorPortalDda,
  type AuditorPortalDda,
  type AuditorPortalDdaMedida,
} from "@/lib/api/auditor-portal";
import { AnnotationPanel } from "@/components/auditor-portal/annotations/AnnotationPanel";

interface Props {
  token: string;
}

const FAMILY_LABEL: Record<string, string> = {
  org: "Marco organizativo (org)",
  op: "Marco operacional (op)",
  mp: "Medidas de protección (mp)",
};

const APLICABILIDAD_VARIANT: Record<
  string,
  "default" | "outline" | "secondary"
> = {
  aplica: "default",
  aplica_aceptado: "secondary",
  aplica_compensa: "secondary",
  aplica_refuerza: "default",
  no_aplica: "outline",
};

const REVIEW_LABEL: Record<string, string> = {
  revisada_ok: "Revisada",
  con_pregunta: "Con pregunta",
  suggest_change: "Sugiere cambio",
};

function MedidaRow({
  medida,
  token,
}: {
  medida: AuditorPortalDdaMedida;
  token: string;
}) {
  const reviewLabel = medida.client_review_status
    ? REVIEW_LABEL[medida.client_review_status] ?? medida.client_review_status
    : null;

  return (
    <div
      className="rounded-md border border-fulkro-ink-300/60 bg-white p-3"
      data-testid={`auditor-dda-medida-${medida.codigo}`}
    >
      <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-xs font-semibold text-fulkro-ink-900">
            {medida.codigo}
          </span>
          <span className="text-sm font-medium text-fulkro-ink-900">
            {medida.nombre}
          </span>
          {medida.aplicabilidad ? (
            <Badge
              variant={
                APLICABILIDAD_VARIANT[medida.aplicabilidad] ?? "outline"
              }
            >
              {medida.aplicabilidad}
            </Badge>
          ) : null}
        </div>
        {reviewLabel ? (
          <span className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            {reviewLabel}
          </span>
        ) : null}
      </div>
      {medida.descripcion ? (
        <p className="text-[13px] text-fulkro-ink-700">{medida.descripcion}</p>
      ) : null}
      {medida.aplicabilidad === "no_aplica" && medida.justificacion_no_aplica ? (
        <p className="mt-1 rounded bg-fulkro-warning-700/5 px-2 py-1 text-[12px] text-fulkro-warning-700">
          <strong>Justificación no aplica:</strong>{" "}
          {medida.justificacion_no_aplica}
        </p>
      ) : null}
      {medida.estado_implementacion ? (
        <p className="mt-1 text-[12px] text-fulkro-ink-500">
          Estado: {medida.estado_implementacion}
        </p>
      ) : null}
      {medida.observaciones ? (
        <p className="mt-1 text-[12px] italic text-fulkro-ink-500">
          {medida.observaciones}
        </p>
      ) : null}
      <div className="mt-2">
        <AnnotationPanel
          token={token}
          targetType="medida"
          targetId={medida.id}
          targetLabel={`Medida ${medida.codigo}`}
          compact
        />
      </div>
    </div>
  );
}

export function DdaView({ token }: Props) {
  const [family, setFamily] = React.useState<string>("all");
  const [search, setSearch] = React.useState<string>("");

  const dda = useQuery<AuditorPortalDda>({
    queryKey: ["auditor-portal", "dda", token, family],
    queryFn: () =>
      getAuditorPortalDda(token, family !== "all" ? { family } : undefined),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  const filtered = React.useMemo(() => {
    if (!dda.data) return [];
    if (!search.trim()) return dda.data.medidas;
    const lower = search.trim().toLowerCase();
    return dda.data.medidas.filter(
      (m) =>
        m.codigo.toLowerCase().includes(lower) ||
        m.nombre.toLowerCase().includes(lower),
    );
  }, [dda.data, search]);

  if (dda.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="auditor-dda-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Cargando declaración de aplicabilidad…
      </div>
    );
  }

  if (dda.isError || !dda.data) {
    return (
      <Alert variant="danger" data-testid="auditor-dda-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudo cargar la DdA</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4" data-testid="auditor-dda-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Declaración de Aplicabilidad
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex flex-wrap items-center gap-3">
            <span data-testid="auditor-dda-total">
              <strong>{dda.data.total}</strong> medidas registradas
            </span>
            {dda.data.is_signed ? (
              <Badge variant="default" data-testid="auditor-dda-signed-badge">
                Firmada
                {dda.data.signed_at
                  ? ` · ${new Date(dda.data.signed_at).toLocaleDateString()}`
                  : ""}
              </Badge>
            ) : (
              <Badge
                variant="outline"
                data-testid="auditor-dda-unsigned-badge"
              >
                Pendiente de firma
              </Badge>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <label className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Filtrar por familia
            </label>
            <Select value={family} onValueChange={setFamily}>
              <SelectTrigger
                className="h-9 w-60"
                aria-label="Filtrar medidas por familia"
                data-testid="auditor-dda-family-select"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las familias</SelectItem>
                <SelectItem value="org">{FAMILY_LABEL.org}</SelectItem>
                <SelectItem value="op">{FAMILY_LABEL.op}</SelectItem>
                <SelectItem value="mp">{FAMILY_LABEL.mp}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <Search
              size={14}
              className="text-fulkro-ink-500"
              aria-hidden="true"
            />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por código o nombre"
              aria-label="Buscar medida"
              data-testid="auditor-dda-search"
              className="h-9"
            />
          </div>
        </CardContent>
      </Card>

      <div className="space-y-2">
        {filtered.length === 0 ? (
          <Alert>
            <AlertTitle>Sin resultados</AlertTitle>
            <AlertDescription>
              No hay medidas que coincidan con los filtros aplicados.
            </AlertDescription>
          </Alert>
        ) : (
          filtered.map((m) => (
            <MedidaRow key={m.id} medida={m} token={token} />
          ))
        )}
      </div>
    </div>
  );
}
