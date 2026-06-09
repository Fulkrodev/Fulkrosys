"use client";

/**
 * E041View · Phase 5.6 auditor portal · declaración conformidad read-only.
 *
 * Display:
 * - List basic_declarations (BÁSICA + commitment_pre_certification + dpc_anual)
 * - Per-declaration: tipo + responsable + signed_at + signed_hash visible
 * - Signature verification status (signed_hash present + signed_at present)
 * - Published evidence URL (cliente publicó CCN/sede electrónica)
 */
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ExternalLink, Loader2, Shield } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  getAuditorPortalE041,
  type AuditorPortalE041,
  type AuditorPortalE041Declaration,
} from "@/lib/api/auditor-portal";

interface Props {
  token: string;
}

const TYPE_LABEL: Record<string, string> = {
  initial: "Declaración de conformidad inicial (E-041 BÁSICA)",
  commitment_pre_certification:
    "Compromiso pre-auditoría (MEDIA · ALTA)",
  recategorization: "Re-categorización",
  dpc_anual: "Declaración anual (DPC)",
};

function DeclarationCard({
  declaration,
}: {
  declaration: AuditorPortalE041Declaration;
}) {
  return (
    <Card data-testid={`auditor-e041-decl-${declaration.id}`}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Shield
            size={16}
            className="text-fulkro-success-700"
            aria-hidden="true"
          />
          {TYPE_LABEL[declaration.declaration_type] ?? declaration.declaration_type}
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            Estado
          </p>
          <p className="font-medium text-fulkro-ink-900">
            {declaration.status}
          </p>
          {declaration.anniversary_year ? (
            <p className="text-[11px] text-fulkro-ink-500">
              Anualidad: {declaration.anniversary_year}
            </p>
          ) : null}
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            Responsable firmante
          </p>
          <p className="font-medium text-fulkro-ink-900">
            {declaration.responsible_person_name ?? "—"}
          </p>
          {declaration.responsible_person_email ? (
            <p className="text-[11px] text-fulkro-ink-500">
              {declaration.responsible_person_email}
            </p>
          ) : null}
        </div>
        <div className="sm:col-span-2">
          <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
            Firma Ed25519
          </p>
          {declaration.is_signed ? (
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Badge
                  variant="success"
                  data-testid="auditor-e041-signed-badge"
                >
                  Firmada
                </Badge>
                {declaration.signed_at ? (
                  <span className="text-[12px] text-fulkro-ink-700">
                    {new Date(declaration.signed_at).toLocaleString()}
                  </span>
                ) : null}
              </div>
              {declaration.signed_hash ? (
                <p className="font-mono text-[10px] text-fulkro-ink-500">
                  hash: {declaration.signed_hash.slice(0, 32)}…
                </p>
              ) : null}
            </div>
          ) : (
            <Badge variant="warning" data-testid="auditor-e041-unsigned-badge">
              Pendiente de firma
            </Badge>
          )}
        </div>
        {declaration.published_evidence_url ? (
          <div className="sm:col-span-2">
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Evidencia publicada
            </p>
            <a
              href={declaration.published_evidence_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[13px] text-fulkro-info-700 underline hover:no-underline"
              data-testid="auditor-e041-published-link"
            >
              <ExternalLink size={12} aria-hidden="true" />
              {declaration.published_evidence_url}
            </a>
          </div>
        ) : null}
        {declaration.client_concerns_note ? (
          <div className="sm:col-span-2">
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Observaciones del cliente
            </p>
            <p className="text-[13px] italic text-fulkro-ink-700">
              {declaration.client_concerns_note}
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function E041View({ token }: Props) {
  const data = useQuery<AuditorPortalE041>({
    queryKey: ["auditor-portal", "e041", token],
    queryFn: () => getAuditorPortalE041(token),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  if (data.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="auditor-e041-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Cargando declaraciones de conformidad…
      </div>
    );
  }

  if (data.isError || !data.data) {
    return (
      <Alert variant="danger" data-testid="auditor-e041-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudo cargar la declaración</AlertTitle>
        <AlertDescription>
          Reintenta más tarde o solicita un enlace nuevo al consultor responsable.
        </AlertDescription>
      </Alert>
    );
  }

  if (data.data.declarations.length === 0) {
    return (
      <Alert data-testid="auditor-e041-empty">
        <AlertTitle>Sin declaraciones</AlertTitle>
        <AlertDescription>
          No hay declaraciones de conformidad registradas para este proyecto.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4" data-testid="auditor-e041-view">
      {data.data.declarations.map((d) => (
        <DeclarationCard key={d.id} declaration={d} />
      ))}
    </div>
  );
}
