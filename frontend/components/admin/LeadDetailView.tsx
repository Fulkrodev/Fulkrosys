"use client";

/**
 * LeadDetailView · SAN-D MB-19.16 cosecha B (ADR-041 · DEC-MB19A-LEAD-DETAIL-PAGE).
 *
 * Vista detalle Lead CRM con tabs:
 * - Overview: campos base + estado_contacto + temperature + categoria
 * - Activity: lead_stage_history audit trail transiciones
 * - Proposals: revisiones lifecycle (superseded badges + version DESC)
 * - Contract: si existe · firmado_*_at · vigente
 * - Notes: notas Marcos + razon_perdida
 *
 * Wire: page /admin/pipeline/leads/[id] usa este component.
 *
 * Refs: ADR-041 · MB-19.16 cosecha B.
 */

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Building2,
  CheckCircle2,
  ClipboardList,
  FileText,
  Loader2,
  StickyNote,
  Thermometer,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { api } from "@/lib/api";

interface LeadDetailLead {
  id: string;
  empresa: string;
  cif?: string;
  sector?: string;
  contact_email?: string;
  contact_phone?: string;
  source?: string;
  stage: string;
  estado_contacto: string;
  temperature_level?: number | null;
  categoria_objetivo_ens?: string | null;
  archetype_ens?: string | null;
  notes?: string;
  lost_reason?: string | null;
  fecha_perdida?: string | null;
  fecha_conversion?: string | null;
  convertido_a_proyecto_id?: string | null;
  primer_contacto_at?: string | null;
}

interface StageHistoryItem {
  id: string;
  estado_anterior: string | null;
  estado_nuevo: string;
  cambiado_por_user_id: string | null;
  notas: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

interface ProposalItem {
  id: string;
  version: number;
  estado: string;
  categoria_objetivo: string | null;
  importe_total: number | null;
  duracion_semanas: number | null;
  validez_hasta: string | null;
  enviado_at: string | null;
  fecha_aceptacion: string | null;
  superseded: boolean;
  feedback_cliente: string | null;
  cambios_desde_anterior: string | null;
  notas_marcos: string | null;
  created_at: string | null;
}

interface ContractInfo {
  id: string;
  estado: string;
  tipo: string | null;
  cliente_firmante_nombre: string | null;
  firmado_marcos_at: string | null;
  firmado_cliente_at: string | null;
  vigente_desde: string | null;
  vigente_hasta: string | null;
  firmado_cliente_link_id: string | null;
  created_at: string | null;
}

interface LeadDetailResponse {
  lead: LeadDetailLead;
  stage_history: StageHistoryItem[];
  proposals: ProposalItem[];
  contract: ContractInfo | null;
}

async function fetchLeadDetail(leadId: string): Promise<LeadDetailResponse> {
  return api<LeadDetailResponse>(
    `/api/v1/commercial/leads/${encodeURIComponent(leadId)}`,
  );
}

interface LeadDetailViewProps {
  leadId: string;
}

export function LeadDetailView({ leadId }: LeadDetailViewProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["lead-detail", leadId],
    queryFn: () => fetchLeadDetail(leadId),
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div
        className="flex h-40 items-center justify-center gap-2 text-base font-medium text-[color:var(--fulkro-muted)]"
        data-testid="lead-detail-loading"
      >
        <Loader2 size={14} className="animate-spin" />
        Cargando lead…
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-4 text-sm text-fulkro-danger">
        Error cargando lead {leadId}
      </div>
    );
  }

  const { lead, stage_history, proposals, contract } = data;

  return (
    <div className="space-y-4" data-testid="lead-detail-view">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
            {lead.empresa}
          </h1>
          <p className="text-base font-medium text-[color:var(--fulkro-body)]">
            {lead.cif ? `CIF ${lead.cif} · ` : ""}
            {lead.sector || "Sector no especificado"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="capitalize">
            {lead.estado_contacto.replace(/_/g, " ")}
          </Badge>
          {lead.temperature_level !== null && lead.temperature_level !== undefined ? (
            <Badge variant="secondary" className="gap-1">
              <Thermometer className="h-3 w-3" />
              {lead.temperature_level}/7
            </Badge>
          ) : null}
          {lead.categoria_objetivo_ens ? (
            <Badge variant="secondary">{lead.categoria_objetivo_ens}</Badge>
          ) : null}
        </div>
      </header>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList>
          <TabsTrigger value="overview" data-testid="tab-overview">
            <Building2 className="mr-2 h-4 w-4" /> Overview
          </TabsTrigger>
          <TabsTrigger value="activity" data-testid="tab-activity">
            <Activity className="mr-2 h-4 w-4" /> Activity
            {stage_history.length > 0 && ` (${stage_history.length})`}
          </TabsTrigger>
          <TabsTrigger value="proposals" data-testid="tab-proposals">
            <ClipboardList className="mr-2 h-4 w-4" /> Proposals
            {proposals.length > 0 && ` (${proposals.length})`}
          </TabsTrigger>
          <TabsTrigger value="contract" data-testid="tab-contract">
            <FileText className="mr-2 h-4 w-4" /> Contract
          </TabsTrigger>
          <TabsTrigger value="notes" data-testid="tab-notes">
            <StickyNote className="mr-2 h-4 w-4" /> Notes
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <Card>
            <CardHeader>
              <CardTitle>Datos generales</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2 md:grid-cols-2">
              <DataRow label="Empresa" value={lead.empresa} />
              <DataRow label="CIF" value={lead.cif || "-"} />
              <DataRow label="Sector" value={lead.sector || "-"} />
              <DataRow label="Email contacto" value={lead.contact_email || "-"} />
              <DataRow label="Teléfono" value={lead.contact_phone || "-"} />
              <DataRow label="Origen" value={lead.source || "-"} />
              <DataRow
                label="Categoría objetivo ENS"
                value={lead.categoria_objetivo_ens || "-"}
              />
              <DataRow
                label="Arquetipo PYME"
                value={lead.archetype_ens || "-"}
              />
              <DataRow
                label="Primer contacto"
                value={formatDate(lead.primer_contacto_at)}
              />
              {lead.fecha_conversion ? (
                <DataRow
                  label="Convertido el"
                  value={formatDate(lead.fecha_conversion)}
                />
              ) : null}
              {lead.convertido_a_proyecto_id ? (
                <div className="md:col-span-2">
                  <Link
                    href={`/admin/projects/${lead.convertido_a_proyecto_id}/summary`}
                    className="inline-flex items-center gap-1 text-sm text-fulkro-info hover:underline"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    Ver proyecto convertido
                  </Link>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardHeader>
              <CardTitle>Audit trail · transiciones estado_contacto</CardTitle>
            </CardHeader>
            <CardContent>
              {stage_history.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Sin transiciones registradas para este lead
                </p>
              ) : (
                <ul className="space-y-2" role="list">
                  {stage_history.map((row) => (
                    <li
                      key={row.id}
                      className="rounded-md border-l-2 border-l-fulkro-info/40 bg-fulkro-info/5 p-2"
                    >
                      <p className="text-sm font-medium">
                        {row.estado_anterior
                          ? `${row.estado_anterior} → ${row.estado_nuevo}`
                          : `Creación · ${row.estado_nuevo}`}
                      </p>
                      {row.notas ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {row.notas}
                        </p>
                      ) : null}
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatDate(row.created_at)}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="proposals">
          <Card>
            <CardHeader>
              <CardTitle>Revisiones de propuesta</CardTitle>
            </CardHeader>
            <CardContent>
              {proposals.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Sin propuestas asociadas a este lead
                </p>
              ) : (
                <ul className="space-y-3" role="list">
                  {proposals.map((p) => (
                    <li
                      key={p.id}
                      className="rounded-md border p-3"
                      data-superseded={p.superseded}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold">
                            v{p.version}
                          </span>
                          <Badge
                            variant={
                              p.superseded ? "outline" : "secondary"
                            }
                            className="capitalize"
                          >
                            {p.estado}
                          </Badge>
                          {p.superseded ? (
                            <Badge variant="outline" className="text-xs">
                              superseded
                            </Badge>
                          ) : null}
                        </div>
                        {p.importe_total !== null ? (
                          <span className="text-sm font-semibold">
                            {p.importe_total.toLocaleString("es-ES")} €
                          </span>
                        ) : null}
                      </div>
                      {p.cambios_desde_anterior ? (
                        <p className="mt-2 text-xs text-muted-foreground">
                          <span className="font-medium">Cambios:</span>{" "}
                          {p.cambios_desde_anterior}
                        </p>
                      ) : null}
                      {p.feedback_cliente ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                          <span className="font-medium">Feedback cliente:</span>{" "}
                          {p.feedback_cliente}
                        </p>
                      ) : null}
                      <p className="mt-2 text-xs text-muted-foreground">
                        Creado {formatDate(p.created_at)}
                        {p.enviado_at ? ` · enviado ${formatDate(p.enviado_at)}` : ""}
                        {p.fecha_aceptacion
                          ? ` · aceptado ${formatDate(p.fecha_aceptacion)}`
                          : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="contract">
          <Card>
            <CardHeader>
              <CardTitle>Contrato</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2 md:grid-cols-2">
              {!contract ? (
                <p className="text-sm text-muted-foreground md:col-span-2">
                  Sin contrato asociado a este lead
                </p>
              ) : (
                <>
                  <DataRow label="Estado" value={contract.estado} />
                  <DataRow label="Tipo" value={contract.tipo || "-"} />
                  <DataRow
                    label="Firmante cliente"
                    value={contract.cliente_firmante_nombre || "-"}
                  />
                  <DataRow
                    label="Firmado por Marcos"
                    value={formatDate(contract.firmado_marcos_at)}
                  />
                  <DataRow
                    label="Firmado por cliente"
                    value={formatDate(contract.firmado_cliente_at)}
                  />
                  <DataRow
                    label="Vigente desde"
                    value={formatDate(contract.vigente_desde)}
                  />
                  <DataRow
                    label="Vigente hasta"
                    value={formatDate(contract.vigente_hasta)}
                  />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notes">
          <Card>
            <CardHeader>
              <CardTitle>Notas</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {lead.notes ? (
                <p className="whitespace-pre-wrap text-sm">{lead.notes}</p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Sin notas registradas
                </p>
              )}
              {lead.lost_reason ? (
                <div className="rounded-md border border-fulkro-danger/40 bg-fulkro-danger/5 p-3">
                  <p className="text-xs font-medium text-fulkro-danger">
                    Razón de pérdida
                  </p>
                  <p className="mt-1 text-sm">{lead.lost_reason}</p>
                  {lead.fecha_perdida ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDate(lead.fecha_perdida)}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function DataRow({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm">{value ?? "-"}</span>
    </div>
  );
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    return d.toLocaleString("es-ES", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "-";
  }
}
