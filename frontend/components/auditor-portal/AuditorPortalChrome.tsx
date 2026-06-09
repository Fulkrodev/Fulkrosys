"use client";

/**
 * AuditorPortalChrome · constrained layout para auditor ENAC portal.
 *
 * Sesión 3B-2B.6 CLUSTER 2 Phase 4 · pattern mirror pentester-portal + cliente
 * portal R29 branding propagation. Auditor ve cliente brand (NO FULKRO generic).
 *
 * Architecture:
 * - Token-bounded session (URL [token] param canonical)
 * - 9-section sidebar nav · read-only views
 * - Top bar · cliente razón social + audit status badge + session timer
 * - NO admin functions visible · NO write actions
 *
 * Children renderizan dentro layout · cada section fetcheable independiente
 * via auditor-portal API client.
 */
import {
  Activity,
  BadgeCheck,
  FileSearch,
  FileText,
  FolderArchive,
  Layers,
  Map,
  Shield,
  ShieldAlert,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";

import type { AuditorPortalMetadata } from "@/lib/api/auditor-portal";
import { cn } from "@/lib/utils";
import { ClarificationButton } from "@/components/auditor-portal/clarifications/ClarificationButton";

interface Props {
  token: string;
  metadata: AuditorPortalMetadata;
  children: React.ReactNode;
}

interface NavSection {
  slug: string;
  label: string;
  icon: typeof FileText;
  description: string;
}

const NAV_SECTIONS: NavSection[] = [
  { slug: "summary", label: "Resumen", icon: BadgeCheck, description: "Visión general del proyecto" },
  { slug: "audit/dda-evidence-gaps", label: "Cobertura DdA · Evidencias", icon: FileSearch, description: "Heatmap gaps + recomendaciones" },
  { slug: "dda", label: "DdA · Declaración Aplicabilidad", icon: FileText, description: "73 medidas aplicables firmadas" },
  { slug: "magerit", label: "MAGERIT · Riesgos", icon: ShieldAlert, description: "Análisis activos · amenazas · salvaguardas" },
  { slug: "plan", label: "Plan adecuación", icon: Map, description: "Gantt + PDA cronograma" },
  { slug: "evidence", label: "Evidencias por medida", icon: FolderArchive, description: "Vault WORM 7 años · per medida ENS" },
  { slug: "e041", label: "E-041 Declaración Conformidad", icon: Shield, description: "Firma Ed25519 cliente publicación CCN" },
  { slug: "audit-log", label: "Audit log inmutable", icon: Activity, description: "Hash chain R6 · trazabilidad ENS" },
  { slug: "pentest", label: "Reportes pentest", icon: ShieldAlert, description: "M08 verificación técnica E-702" },
  { slug: "documents", label: "Documentos canónicos", icon: Layers, description: "10 docs ENAC · ZIP completo" },
  { slug: "draft-report", label: "Borrador informe", icon: FileText, description: "Genera PDF firmado Ed25519" },
];

const CATEGORIA_VARIANT: Record<string, "secondary" | "warning" | "success"> = {
  BASICA: "secondary",
  MEDIA: "warning",
  ALTA: "success",
};

const AUDIT_RESULT_LABEL: Record<string, { label: string; color: string }> = {
  passed: { label: "Pasada", color: "bg-fulkro-success-700" },
  observed: { label: "Con observaciones", color: "bg-fulkro-warning-700" },
  correction_required: { label: "Requiere correcciones", color: "bg-fulkro-info-700" },
  failed: { label: "No pasada", color: "bg-fulkro-danger-700" },
};

function applyClientBranding(cliente: AuditorPortalMetadata["cliente"]) {
  if (typeof document === "undefined") return;
  if (cliente.primary_color) {
    document.documentElement.style.setProperty(
      "--client-primary-color", cliente.primary_color,
    );
  }
  if (cliente.secondary_color) {
    document.documentElement.style.setProperty(
      "--client-secondary-color", cliente.secondary_color,
    );
  }
}

export function AuditorPortalChrome({ token, metadata, children }: Props) {
  const pathname = usePathname();
  const { cliente, project, token_meta } = metadata;

  React.useEffect(() => {
    applyClientBranding(cliente);
  }, [cliente]);

  const expiresAtFmt = token_meta.expires_at
    ? new Date(token_meta.expires_at).toLocaleString()
    : "—";
  const categoriaVariant = CATEGORIA_VARIANT[project.categoria] ?? "secondary";
  const auditResult = project.audit_result
    ? AUDIT_RESULT_LABEL[project.audit_result]
    : null;

  return (
    <div className="min-h-dvh bg-fulkro-ink-50 text-fulkro-ink-700">
      {/* Top bar · cliente brand + project + session timer */}
      <header
        className="border-b border-fulkro-ink-300/60 bg-white"
        style={
          cliente.primary_color
            ? { borderTop: `3px solid ${cliente.primary_color}` }
            : undefined
        }
      >
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Portal auditor ENAC · {cliente.razon_social}
            </p>
            <p className="truncate text-sm font-semibold text-fulkro-ink-900">
              {project.nombre}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px]">
            <span
              className={cn(
                "rounded-full px-2 py-0.5 font-semibold uppercase tracking-wider",
                categoriaVariant === "warning" && "bg-fulkro-warning-700/10 text-fulkro-warning-700",
                categoriaVariant === "success" && "bg-fulkro-success-700/10 text-fulkro-success-700",
                categoriaVariant === "secondary" && "bg-fulkro-ink-300/20 text-fulkro-ink-700",
              )}
              data-testid="auditor-portal-categoria"
            >
              ENS {project.categoria}
            </span>
            {auditResult ? (
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 font-semibold text-white",
                  auditResult.color,
                )}
                data-testid="auditor-portal-audit-result"
              >
                {auditResult.label}
              </span>
            ) : null}
            <span className="text-fulkro-ink-500">
              Expira: <span className="font-mono">{expiresAtFmt}</span>
            </span>
            <ClarificationButton
              token={token}
              targetType="general"
              buttonVariant="secondary"
              compact
            />
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-7xl gap-6 px-4 py-6">
        {/* Sidebar · 9 sections */}
        <aside
          className="hidden w-64 shrink-0 lg:block"
          aria-label="Navegación auditor"
        >
          <nav className="space-y-1">
            {NAV_SECTIONS.map((section) => {
              const href = `/auditor-portal/${token}/${section.slug}`;
              const active = pathname?.endsWith(`/${section.slug}`) ?? false;
              const Icon = section.icon;
              return (
                <Link
                  key={section.slug}
                  href={href}
                  data-testid={`auditor-nav-${section.slug}`}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-start gap-2 rounded-md px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-fulkro-primary-700/10 text-fulkro-primary-700"
                      : "text-fulkro-ink-700 hover:bg-fulkro-ink-100",
                  )}
                >
                  <Icon size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
                  <span className="min-w-0">
                    <span className="block font-medium leading-tight">
                      {section.label}
                    </span>
                    <span className="block text-[11px] leading-tight text-fulkro-ink-600">
                      {section.description}
                    </span>
                  </span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="min-w-0 flex-1" data-testid="auditor-portal-main">
          {children}
        </main>
      </div>

      <footer className="border-t border-fulkro-ink-300/60 bg-white">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-start justify-between gap-1 px-4 py-3 text-[11px] text-fulkro-ink-500 sm:flex-row sm:items-center">
          <span>
            <FileSearch size={11} className="mr-1 inline-block" aria-hidden="true" />
            Portal auditor ENAC · enlace firmado Ed25519 · acceso restringido
          </span>
          <span>
            {cliente.footer_text || "Marcos Mata García · Consultor ENS independiente · RD 311/2022"}
          </span>
        </div>
      </footer>
    </div>
  );
}
