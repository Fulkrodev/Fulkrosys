"use client";

import * as React from "react";
import { ChevronDown, FileText, GitBranch, ListTree } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import {
  useOnboardingCatalog,
  useTemplateDetail,
} from "@/hooks/useOnboardingAdmin";
import type { TemplateSummary } from "@/lib/admin-onboarding/api";

export interface TemplateCatalogViewerProps {
  initialSector?: string;
}

export function TemplateCatalogViewer({ initialSector }: TemplateCatalogViewerProps) {
  const { data: catalog, isLoading } = useOnboardingCatalog();
  const [sectorFilter, setSectorFilter] = React.useState<string>(initialSector ?? "all");
  const [selectedId, setSelectedId] = React.useState<string | null>(null);

  const { data: detail, isLoading: detailLoading } = useTemplateDetail(selectedId);

  if (isLoading) {
    return <p className="text-sm text-fulkro-ink-500">Cargando catálogo…</p>;
  }
  if (!catalog) {
    return (
      <div className="rounded border border-dashed border-fulkro-ink-200 p-6 text-center text-sm text-fulkro-ink-500">
        Catálogo de templates no disponible
      </div>
    );
  }

  const filtered = catalog.templates.filter(
    (t) => sectorFilter === "all" || t.sector === sectorFilter,
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <ListTree size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Catálogo de plantillas
            <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
              ({catalog.total})
            </span>
          </h3>
          <TooltipENS term="branching_logic" />
        </div>
        <select
          value={sectorFilter}
          onChange={(e) => setSectorFilter(e.target.value)}
          className="rounded border border-fulkro-ink-200 bg-white px-3 py-1.5 text-sm"
        >
          <option value="all">Todos los sectores ({catalog.templates.length})</option>
          {catalog.available_sectors.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((tpl) => (
          <Card
            key={tpl.id}
            className="cursor-pointer transition-colors hover:border-fulkro-primary-700"
            onClick={() => setSelectedId(tpl.id)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-sm">{tpl.nombre}</CardTitle>
                <Badge variant="outline">v{tpl.version}</Badge>
              </div>
              <CardDescription className="line-clamp-2">{tpl.descripcion}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-xs">
              <div className="flex flex-wrap gap-1">
                <Badge variant="secondary">{tpl.sector}</Badge>
                <Badge variant="info">{tpl.role}</Badge>
                <Badge variant="outline">{tpl.language}</Badge>
              </div>
              <div className="flex items-center justify-between text-fulkro-ink-500">
                <span>{tpl.total_questions} preguntas</span>
                <span>~{tpl.tiempo_estimado_minutos} min</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Sheet
        open={selectedId !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null);
        }}
      >
        <SheetContent className="w-full sm:max-w-xl">
          {detailLoading ? (
            <p className="text-sm text-fulkro-ink-500">Cargando detalle…</p>
          ) : detail ? (
            <TemplateDetailViewer template={detail} />
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function TemplateDetailViewer({ template }: { template: NonNullable<ReturnType<typeof useTemplateDetail>["data"]> }) {
  const [openSections, setOpenSections] = React.useState<Set<string>>(
    new Set(template.sections.slice(0, 1)),
  );

  const toggleSection = (s: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });
  };

  return (
    <>
      <SheetHeader>
        <SheetTitle>{template.nombre}</SheetTitle>
        <SheetDescription>
          {template.id} · v{template.version} · {template.total_questions} preguntas · ~
          {template.tiempo_estimado_minutos} min
        </SheetDescription>
      </SheetHeader>

      <div className="mt-4 space-y-3">
        <div className="flex flex-wrap gap-1">
          <Badge variant="secondary">{template.sector}</Badge>
          <Badge variant="info">{template.role}</Badge>
          <Badge variant="outline">{template.language}</Badge>
        </div>

        <p className="text-sm text-fulkro-ink-700">{template.descripcion}</p>

        <div className="space-y-2">
          {template.sections.map((section) => {
            const sectionQuestions = template.questions.filter(
              (q) => q.section === section,
            );
            const isOpen = openSections.has(section);
            return (
              <div
                key={section}
                className="rounded border border-fulkro-ink-100 bg-white"
              >
                <button
                  type="button"
                  onClick={() => toggleSection(section)}
                  className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium hover:bg-fulkro-canvas"
                >
                  <span className="flex items-center gap-2">
                    <FileText size={14} />
                    {section}
                    <Badge variant="outline">{sectionQuestions.length}</Badge>
                  </span>
                  <ChevronDown
                    size={14}
                    className={cn("transition-transform", isOpen && "rotate-180")}
                  />
                </button>
                {isOpen ? (
                  <div className="space-y-2 border-t border-fulkro-ink-100 p-3">
                    {sectionQuestions.map((q) => (
                      <div key={q.id} className="rounded bg-fulkro-canvas p-2 text-xs">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-fulkro-ink-500">{q.id}</span>
                          <Badge variant="outline">{q.type}</Badge>
                        </div>
                        <p className="mt-1 text-fulkro-ink-700">{q.label}</p>
                        {q.skip_if ? (
                          <div className="mt-1 inline-flex items-center gap-1 text-xs text-fulkro-info">
                            <GitBranch size={11} />
                            skip_if {q.skip_if.question_id} {q.skip_if.operator}{" "}
                            {String(q.skip_if.value)}
                          </div>
                        ) : null}
                        {q.options && q.options.length > 0 ? (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {q.options.slice(0, 5).map((o) => (
                              <Badge key={o.value} variant="secondary" className="text-xs">
                                {o.label}
                              </Badge>
                            ))}
                            {q.options.length > 5 ? (
                              <span className="text-fulkro-ink-300">
                                +{q.options.length - 5}
                              </span>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
