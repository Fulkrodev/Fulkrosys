"use client";

/**
 * /trust · FULKRO Trust Center (atom 9.bis.5).
 *
 * Public page consumed by clientes durante due diligence. Sections:
 * 1. Hero — FULKRO Compliance & Trust
 * 2. Live compliance status (consumes /api/v1/legal/compliance/status)
 * 3. Regulatory frameworks badges
 * 4. Sub-processors brief + link to /sub-processors
 * 5. Document downloads (DPA, Whitepaper, Privacy, Cookies)
 * 6. Contact DPO + last updated badge
 *
 * Static content is factual; live status drives the green/yellow/red badge.
 */
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  Circle,
  Download,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getPublicComplianceStatus } from "@/lib/legal/api";
import {
  SUB_PROCESSORS,
  type OverallHealth,
} from "@/lib/legal/schemas";
import { cn } from "@/lib/utils";

const HEALTH_LABEL: Record<OverallHealth, string> = {
  green: "Operacional",
  yellow: "Bajo seguimiento",
  red: "Incidencia",
  unknown: "Pendiente primer barrido",
};

const HEALTH_DOT: Record<OverallHealth, string> = {
  green: "bg-emerald-500",
  yellow: "bg-amber-500",
  red: "bg-red-500",
  unknown: "bg-fulkro-ink-400",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function TrustCenterPage() {
  const statusQuery = useQuery({
    queryKey: ["legal", "compliance-status"],
    queryFn: getPublicComplianceStatus,
    refetchInterval: 5 * 60_000,
  });
  const s = statusQuery.data;

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section>
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-7 w-7 text-fulkro-ink-700" />
          <h1 className="text-3xl font-semibold tracking-tight">
            FULKRO Trust Center
          </h1>
        </div>
        <p className="mt-3 max-w-2xl text-base text-fulkro-ink-700">
          Transparencia sobre cómo FULKRO trata los datos de sus clientes,
          qué normativa cumple y qué proveedores intervienen en la cadena.
          Esta página se actualiza automáticamente desde el sistema interno
          de monitorización de cumplimiento.
        </p>
        <div className="mt-6 flex items-center gap-3 text-sm">
          {statusQuery.isLoading || !s ? (
            <Skeleton className="h-6 w-48" />
          ) : (
            <>
              <span
                className={cn(
                  "inline-block h-2.5 w-2.5 rounded-full",
                  HEALTH_DOT[s.overall_health],
                )}
                aria-hidden
              />
              <span className="font-medium">
                {HEALTH_LABEL[s.overall_health]}
              </span>
              <span className="text-fulkro-ink-500">·</span>
              <span className="text-fulkro-ink-600">
                Último barrido: {formatDate(s.last_check)}
              </span>
            </>
          )}
        </div>
      </section>

      {/* Compliance frameworks */}
      <section>
        <h2 className="text-xl font-semibold">Marcos normativos aplicados</h2>
        <p className="mt-2 max-w-2xl text-sm text-fulkro-ink-700">
          FULKRO opera bajo las siguientes normativas. Cada marco se verifica
          mediante checks automatizados ejecutados diariamente, semanalmente
          o mensualmente según corresponda.
        </p>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {statusQuery.isLoading || !s
            ? [...Array(6)].map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
            : s.compliance_frameworks.map((f) => (
                <Card key={f.name} className="border-fulkro-ink-200">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-base">{f.name}</CardTitle>
                      <Badge
                        variant={
                          f.status === "active" || f.status === "aligned"
                            ? "success"
                            : "outline"
                        }
                      >
                        {f.status === "active"
                          ? "En vigor"
                          : f.status === "aligned"
                            ? "Alineado"
                            : f.status === "preparedness"
                              ? "Preparación"
                              : "Planificado"}
                      </Badge>
                    </div>
                  </CardHeader>
                  {f.regulatory_basis ? (
                    <CardContent className="pt-0 text-xs text-fulkro-ink-600">
                      {f.regulatory_basis}
                    </CardContent>
                  ) : null}
                </Card>
              ))}
        </div>
      </section>

      {/* Per-norma compliance scores (live) */}
      <section>
        <div className="flex items-baseline justify-between">
          <h2 className="text-xl font-semibold">Posición de cumplimiento (live)</h2>
          <span className="text-xs text-fulkro-ink-500">
            Generado por el motor interno de Self-Monitoring · {formatDate(s?.last_check ?? null)}
          </span>
        </div>
        <p className="mt-2 max-w-3xl text-sm text-fulkro-ink-700">
          Scores ponderados por normativa que FULKRO reporta automáticamente
          con cadencia semanal / mensual / trimestral. Cada plugin de norma
          combina los checks técnicos que le aplican y emite un score
          0-100 %.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {statusQuery.isLoading || !s
            ? [...Array(3)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)
            : s.compliance_scores_per_norma.map((n) => (
                <a
                  key={n.norma_key}
                  href={n.regulatory_basis_url}
                  target="_blank"
                  rel="noreferrer"
                  className="block rounded-md border border-fulkro-ink-200 bg-white p-4 transition hover:border-fulkro-ink-400"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-2xl font-bold text-fulkro-ink-900">
                      {n.score !== null ? `${n.score.toFixed(1)}%` : "—"}
                    </span>
                    <span
                      className={cn(
                        "inline-block h-2.5 w-2.5 rounded-full",
                        HEALTH_DOT[n.status],
                      )}
                      aria-hidden
                    />
                  </div>
                  <div className="mt-1 text-sm font-medium text-fulkro-ink-900">
                    {n.norma_name}
                  </div>
                  <div className="mt-1 text-xs text-fulkro-ink-500">
                    Último reporte: {n.last_report ?? "—"}
                  </div>
                </a>
              ))}
        </div>
      </section>

      {/* ISMS certifications */}
      <section>
        <h2 className="text-xl font-semibold">Certificaciones ISMS</h2>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {statusQuery.isLoading || !s
            ? [...Array(2)].map((_, i) => <Skeleton key={i} className="h-20 w-full" />)
            : s.isms_certifications.map((c) => (
                <div
                  key={c.name}
                  className="rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{c.name}</span>
                    <Badge variant="outline">
                      {c.status === "certified"
                        ? "Certificada"
                        : c.status === "preparedness"
                          ? "Preparación"
                          : "Planificada"}
                    </Badge>
                  </div>
                  {c.expected ? (
                    <p className="mt-1 text-xs text-fulkro-ink-600">
                      Auditoría externa prevista: {c.expected}
                    </p>
                  ) : null}
                </div>
              ))}
        </div>
      </section>

      {/* Sub-processors brief */}
      <section>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Sub-procesadores</h2>
          <Link
            href="/sub-processors"
            className="text-sm text-fulkro-ink-700 hover:underline"
          >
            Ver lista completa →
          </Link>
        </div>
        <p className="mt-2 max-w-2xl text-sm text-fulkro-ink-700">
          FULKRO utiliza {statusQuery.data?.sub_processors_count ?? SUB_PROCESSORS.length}{" "}
          proveedores externos en su cadena de procesamiento. Todos cuentan con
          DPA firmado conforme al Art. 28 RGPD y mecanismo de transferencia
          válido (datos en UE o SCC 2021/914 cuando aplica).
        </p>
        <ul className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {SUB_PROCESSORS.map((p) => (
            <li
              key={p.slug}
              className="flex items-center gap-2 text-sm text-fulkro-ink-700"
            >
              <CheckCircle2 className="h-4 w-4 text-emerald-700" />
              <span className="font-medium">{p.name}</span>
              <span className="text-xs text-fulkro-ink-500">
                · {p.data_location}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* Document downloads */}
      <section>
        <h2 className="text-xl font-semibold">Documentación</h2>
        <p className="mt-2 max-w-2xl text-sm text-fulkro-ink-700">
          Plantilla DPA pre-firmable, política de privacidad, política de
          cookies y whitepaper de seguridad. Los enlaces se activan cuando los
          atoms posteriores publican los artefactos.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <DocLink
            title="Plantilla DPA (Art. 28 RGPD)"
            desc="Contrato de encargo de tratamiento pre-firmable por el cliente."
            href="/api/v1/legal/dpa-template/download"
            available={true}
            pending=""
          />
          <DocLink
            title="Security Whitepaper"
            desc="Arquitectura de seguridad, controles ISO 27001:2022 implantados, soberanía de datos."
            href="/legal/security-whitepaper.pdf"
            available={false}
            pending="atom 9.bis.4"
          />
          <DocLink
            title="Política de privacidad"
            desc="Art. 13-14 RGPD: información sobre el tratamiento, derechos del interesado."
            href="/privacy"
            available={false}
            pending="atom 9.bis.1"
          />
          <DocLink
            title="Política de cookies"
            desc="Guía AEPD 2020: categorías de cookies, base jurídica, retención."
            href="/cookies"
            available={false}
            pending="atom 9.bis.1"
          />
        </div>
      </section>

      {/* Contact + breach status */}
      <section className="rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-6">
        <h2 className="text-xl font-semibold">Contacto y notificación</h2>
        <dl className="mt-4 grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-fulkro-ink-900">
              Delegado de Protección de Datos (DPO)
            </dt>
            <dd className="mt-1 text-fulkro-ink-700">
              Marcos Mata García · interim ·{" "}
              <a
                href="mailto:dpo@fulkro.es"
                className="underline hover:text-fulkro-ink-900"
              >
                dpo@fulkro.es
              </a>
            </dd>
          </div>
          <div>
            <dt className="font-medium text-fulkro-ink-900">
              Notificación de brechas de seguridad
            </dt>
            <dd className="mt-1 flex items-center gap-2 text-fulkro-ink-700">
              {s?.last_breach_reported ? (
                <>
                  <AlertTriangle className="h-4 w-4 text-amber-500" />
                  Última brecha reportada: {formatDate(s.last_breach_reported)}
                </>
              ) : (
                <>
                  <Circle className="h-4 w-4 fill-emerald-500 text-emerald-500" />
                  Sin brechas reportadas hasta la fecha
                </>
              )}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-fulkro-ink-900">
              Reporte de vulnerabilidades
            </dt>
            <dd className="mt-1 text-fulkro-ink-700">
              <a
                href="/.well-known/security.txt"
                className="inline-flex items-center gap-1 underline hover:text-fulkro-ink-900"
              >
                security.txt (RFC 9116)
                <ExternalLink className="h-3 w-3" />
              </a>
            </dd>
          </div>
          <div>
            <dt className="font-medium text-fulkro-ink-900">Autoridad de control</dt>
            <dd className="mt-1 text-fulkro-ink-700">
              Agencia Española de Protección de Datos (AEPD) ·{" "}
              <a
                href="https://www.aepd.es"
                className="underline hover:text-fulkro-ink-900"
                target="_blank"
                rel="noreferrer"
              >
                aepd.es
              </a>
            </dd>
          </div>
        </dl>
      </section>
    </div>
  );
}

function DocLink({
  title,
  desc,
  href,
  available,
  pending,
}: {
  title: string;
  desc: string;
  href: string;
  available: boolean;
  pending: string;
}) {
  return (
    <div
      className={cn(
        "rounded-md border p-4",
        available
          ? "border-fulkro-ink-200 bg-white"
          : "border-fulkro-ink-200 bg-fulkro-ink-50",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium">{title}</h3>
        {available ? (
          <a
            href={href}
            className="inline-flex items-center gap-1 text-xs text-fulkro-ink-700 hover:underline"
          >
            <Download className="h-3.5 w-3.5" />
            Descargar
          </a>
        ) : (
          <span className="rounded bg-fulkro-ink-200 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-fulkro-ink-700">
            disp. en breve
          </span>
        )}
      </div>
      <p className="mt-1.5 text-xs text-fulkro-ink-600">{desc}</p>
      {!available ? (
        <p className="mt-2 text-[11px] text-fulkro-ink-500">
          Publicación prevista: {pending}
        </p>
      ) : null}
    </div>
  );
}
