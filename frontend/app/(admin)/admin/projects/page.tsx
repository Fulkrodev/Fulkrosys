"use client";

import {
  ArrowRight,
  FolderOpen,
  Search,
  SortAsc,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { ArchiveProjectButton } from "@/components/admin/projects/ArchiveProjectButton";
import { CreateProjectModal } from "@/components/admin/projects/CreateProjectModal";
import { EditClientMetaModal } from "@/components/admin/projects/EditClientMetaModal";
import { RAGDot } from "@/components/data/RAGBadge";
import { DevHint } from "@/components/dev/DevHint";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useClients } from "@/hooks/useClients";
import { ROUTES } from "@/lib/constants";
import { formatSector } from "@/lib/labels";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";
import type { Client } from "@/lib/types";
import { cn } from "@/lib/utils";

// Sub-atom Sesión 3B-1 Phase A.1 · sort mode for selector
type SortMode = "name-asc" | "name-desc" | "sector" | "recent";

const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "recent", label: "Último usado" },
  { value: "name-asc", label: "Nombre A→Z" },
  { value: "name-desc", label: "Nombre Z→A" },
  { value: "sector", label: "Sector" },
];

export default function ProjectsPage() {
  const { data, isLoading } = useClients();
  const clients = React.useMemo(() => data ?? [], [data]);
  const lastUsedProjectId = useActiveProjectStore((s) => s.lastUsedProjectId);
  const [searchQuery, setSearchQuery] = React.useState("");
  const [sectorFilter, setSectorFilter] = React.useState<string>("");
  const [sortMode, setSortMode] = React.useState<SortMode>("recent");

  // El selector es el GATE de entrada al sistema: nada arranca hasta que el
  // admin elige EXPLÍCITAMENTE un proyecto (decisión de producto · 2026-06-10).
  // Antes había un auto-redirect cuando existía un único proyecto; se retiró a
  // propósito para que el flujo siempre pase por aquí y lo guíe el copiloto.

  // Sub-atom Sesión 3B-1 Phase A.1 · sectors available derived from clients.
  const availableSectors = React.useMemo(() => {
    const set = new Set<string>();
    for (const c of clients) {
      if (c.sector) set.add(c.sector);
    }
    return Array.from(set).sort();
  }, [clients]);

  const filtered = React.useMemo(() => {
    let result = clients;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (c) =>
          c.nombre.toLowerCase().includes(q) ||
          c.cif.toLowerCase().includes(q) ||
          (c.sector && c.sector.toLowerCase().includes(q)),
      );
    }

    if (sectorFilter) {
      result = result.filter((c) => c.sector === sectorFilter);
    }

    // Sort
    const sorted = [...result];
    switch (sortMode) {
      case "name-asc":
        sorted.sort((a, b) => a.nombre.localeCompare(b.nombre));
        break;
      case "name-desc":
        sorted.sort((a, b) => b.nombre.localeCompare(a.nombre));
        break;
      case "sector":
        sorted.sort((a, b) =>
          (a.sector ?? "").localeCompare(b.sector ?? "") ||
          a.nombre.localeCompare(b.nombre),
        );
        break;
      case "recent":
      default:
        // Last used first, then alphabetical
        sorted.sort((a, b) => {
          if (a.id === lastUsedProjectId) return -1;
          if (b.id === lastUsedProjectId) return 1;
          return a.nombre.localeCompare(b.nombre);
        });
        break;
    }
    return sorted;
  }, [clients, searchQuery, sectorFilter, sortMode, lastUsedProjectId]);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-fulkro-primary-700">
            Selecciona un proyecto
          </h1>
          <p className="text-sm text-fulkro-ink-700">
            Escoge el proyecto sobre el que quieres trabajar. Tu selección queda
            activa en el sidebar hasta que la cambies.{" "}
            <DevHint>L3 hybrid · ADR-054 active project context</DevHint>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CreateProjectModal />
        </div>
      </header>

      {clients.length > 0 ? (
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative max-w-md flex-1 min-w-[240px]">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-fulkro-ink-600"
              aria-hidden
            />
            <Input
              type="search"
              placeholder="Buscar por cliente, CIF o sector…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
              data-testid="projects-search-input"
            />
          </div>

          {/* Sub-atom Sesión 3B-1 Phase A.1 · sector filter chips */}
          {availableSectors.length > 1 ? (
            <div className="flex flex-wrap items-center gap-1.5">
              <button
                type="button"
                onClick={() => setSectorFilter("")}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                  !sectorFilter
                    ? "border-fulkro-info bg-fulkro-info/10 text-fulkro-info"
                    : "border-fulkro-ink-300 text-fulkro-ink-500 hover:bg-fulkro-ink-100",
                )}
                data-testid="projects-sector-filter-all"
              >
                Todos
              </button>
              {availableSectors.map((sector) => (
                <button
                  key={sector}
                  type="button"
                  onClick={() => setSectorFilter(sector)}
                  className={cn(
                    "rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
                    sectorFilter === sector
                      ? "border-fulkro-info bg-fulkro-info/10 text-fulkro-info"
                      : "border-fulkro-ink-300 text-fulkro-ink-500 hover:bg-fulkro-ink-100",
                  )}
                  data-testid={`projects-sector-filter-${sector}`}
                >
                  {formatSector(sector)}
                </button>
              ))}
            </div>
          ) : null}

          {/* Sort dropdown */}
          <label className="ml-auto inline-flex items-center gap-1.5 text-xs font-medium text-fulkro-ink-500">
            <SortAsc size={14} className="text-fulkro-ink-600" aria-hidden />
            <span className="sr-only md:not-sr-only">Ordenar:</span>
            <select
              value={sortMode}
              onChange={(e) => setSortMode(e.target.value as SortMode)}
              className="rounded-md border border-fulkro-ink-300 bg-white px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-fulkro-info"
              data-testid="projects-sort-select"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      ) : null}

      {isLoading ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-32 animate-pulse rounded-lg border border-fulkro-ink-300/60 bg-fulkro-ink-100/50"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
            <FolderOpen size={24} className="text-fulkro-ink-500" />
            <div>
              {clients.length === 0 ? (
                <>
                  <p className="font-medium text-fulkro-ink-700">
                    Crea tu primer proyecto ENS · el copiloto te guía paso a paso.
                  </p>
                  <p className="text-sm text-fulkro-ink-500">
                    Pulsa «Crear proyecto» para empezar el alta del cliente.
                  </p>
                </>
              ) : (
                <>
                  <p className="font-medium text-fulkro-ink-700">
                    Ningún proyecto coincide con los filtros aplicados.
                  </p>
                  <p className="text-sm text-fulkro-ink-500">
                    Prueba quitar el filtro de sector o cambiar la búsqueda.
                  </p>
                  {(sectorFilter || searchQuery) ? (
                    <button
                      type="button"
                      onClick={() => {
                        setSectorFilter("");
                        setSearchQuery("");
                      }}
                      className="mt-1 text-sm font-medium text-fulkro-info underline hover:opacity-80"
                      data-testid="projects-clear-filters"
                    >
                      Limpiar filtros
                    </button>
                  ) : null}
                </>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div
          className="grid gap-3 md:grid-cols-2 xl:grid-cols-3"
          data-testid="projects-grid"
        >
          {filtered.map((client) => (
            <ProjectCard
              key={client.id}
              client={client}
              isLastUsed={lastUsedProjectId === client.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Sub-atom 1.E.2.bis Phase B · General info display per project
// Status pill labels (lifecycle_state) y heuristic mapping a tone.
const STATUS_LABEL: Record<string, { label: string; tone: "secondary" | "warning" | "success" | "info" }> = {
  DRAFT: { label: "Borrador", tone: "secondary" },
  NEGOTIATING: { label: "Negociación", tone: "info" },
  SIGNED: { label: "Firmado", tone: "info" },
  ACTIVE: { label: "Activo", tone: "success" },
  CERTIFIED: { label: "Certificado", tone: "success" },
  RETAINER: { label: "Retainer", tone: "success" },
  ARCHIVED: { label: "Archivado", tone: "secondary" },
  PURGED: { label: "Purgado", tone: "secondary" },
};

function ProjectCard({
  client,
  isLastUsed,
}: {
  client: Client;
  isLastUsed: boolean;
}) {
  // For piloto MEDIA 1 cliente ≈ 1 proyecto: derivamos status display
  // desde client metadata · multi-project per cliente requires per-project
  // lookup (Future-1.E.2.bis.multi-project capability).
  // CRITICAL #1 · navegar con project_id REAL (client.id da 404 en el header).
  const href = client.project_id
    ? `${ROUTES.projects}/${client.project_id}/roadmap`
    : null;
  const cardInner = (
    <Card
        className={cn(
          "h-full transition-colors",
          href && "group-hover:border-fulkro-info group-hover:shadow-md",
          // 2026-06-09 · Polish gate: opacity-80 atenuaba TODO el contenido de
          // la tarjeta (ink-500 → ~3.6:1 · badge → FAIL AA serious ×10 nodos).
          // Pista visual sin pérdida de contraste: borde discontinuo.
          !href && "border-dashed",
          isLastUsed && "border-fulkro-info/60 bg-fulkro-info/5",
        )}
      >
        <CardHeader>
          <CardTitle className="flex items-center justify-between gap-2 text-base">
            <span className="flex items-center gap-2">
              <RAGDot status={client.rag ?? "green"} className="h-2 w-2" />
              {client.nombre}
            </span>
            {isLastUsed ? (
              <Badge variant="info" className="text-[10px]">
                Último usado
              </Badge>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-0 text-sm">
          <p className="text-fulkro-ink-500">
            CIF <span className="font-mono">{client.cif}</span>
            {client.sector ? ` · ${formatSector(client.sector)}` : ""}
          </p>
          {/* Sub-atom 1.E.2.bis Phase B · status pill (active default
              piloto MEDIA · scope-out per-project fetch hasta multi-project demand) */}
          <div className="flex items-center gap-2 text-[11px] text-fulkro-ink-500">
            <Badge
              variant={STATUS_LABEL.ACTIVE.tone}
              className="text-[10px]"
              data-testid={`project-card-status-${client.id}`}
            >
              {STATUS_LABEL.ACTIVE.label}
            </Badge>
            <span aria-hidden>·</span>
            <span className="font-mono">{client.id.slice(0, 8)}</span>
          </div>
          <div className="flex items-center justify-between gap-2">
            {href ? (
              <span className="inline-flex items-center gap-1 text-fulkro-info group-hover:underline">
                Entrar al proyecto <ArrowRight size={12} />
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-fulkro-ink-600">
                Sin proyecto activo
              </span>
            )}
            <div className="flex items-center gap-1.5">
              {/* Sub-atom Sesión 3B-1 Phase A.2 · edit metadata inline */}
              <EditClientMetaModal
                clientId={client.id}
                currentName={client.nombre}
                currentSector={client.sector}
              />
              {client.project_id ? (
                <ArchiveProjectButton
                  projectId={client.project_id}
                  projectName={client.nombre}
                  clientId={client.id}
                  variant="compact"
                />
              ) : null}
            </div>
          </div>
        </CardContent>
      </Card>
  );
  if (!href) {
    return (
      <div className="block" data-testid={`project-card-${client.id}`}>
        {cardInner}
      </div>
    );
  }
  return (
    <Link
      href={href}
      className={cn(
        "group block transition-transform focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-info",
        "hover:-translate-y-0.5",
      )}
      data-testid={`project-card-${client.id}`}
    >
      {cardInner}
    </Link>
  );
}
