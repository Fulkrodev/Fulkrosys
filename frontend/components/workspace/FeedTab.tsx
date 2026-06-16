"use client";

import * as React from "react";
import {
  Activity,
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Eye,
  FileSignature,
  FileText,
  ListChecks,
  MessageSquare,
  ScanLine,
  ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import {
  useFeedItems,
  useFeedUnreadCount,
  useMarkFeedRead,
} from "@/hooks/useWorkspace";
import type { FeedItem, FeedItemTipo } from "@/lib/admin-workspace/api";

export interface FeedTabProps {
  projectId: string;
}

const TIPO_META: Record<
  FeedItemTipo,
  { label: string; icon: typeof Activity; variant: "info" | "success" | "warning" | "danger" | "secondary" }
> = {
  hito_completado: { label: "Hito", icon: CheckCircle2, variant: "success" },
  documento_generado: { label: "Documento", icon: FileText, variant: "info" },
  evidencia_aportada: { label: "Evidencia", icon: ListChecks, variant: "info" },
  finding_detectado: { label: "Finding", icon: ScanLine, variant: "warning" },
  tarea_completada: { label: "Tarea", icon: CheckCircle2, variant: "success" },
  firma_pendiente: { label: "Firma", icon: FileSignature, variant: "warning" },
  comentario: { label: "Comentario", icon: MessageSquare, variant: "secondary" },
  alerta: { label: "Alerta", icon: AlertTriangle, variant: "danger" },
  reunion_programada: { label: "Reunión", icon: Calendar, variant: "info" },
};

const AUTOR_VARIANT: Record<string, "info" | "success" | "secondary"> = {
  marcos: "info",
  cliente: "success",
  plataforma: "secondary",
};

const TIPO_OPTIONS: FeedItemTipo[] = [
  "hito_completado",
  "documento_generado",
  "evidencia_aportada",
  "finding_detectado",
  "tarea_completada",
  "firma_pendiente",
  "comentario",
  "alerta",
  "reunion_programada",
];

const AUTOR_OPTIONS = ["marcos", "cliente", "plataforma"];

export function FeedTab({ projectId }: FeedTabProps) {
  const [tipoFilter, setTipoFilter] = React.useState<string>("all");
  const [autorFilter, setAutorFilter] = React.useState<string>("all");
  const [unreadOnly, setUnreadOnly] = React.useState(false);
  const [detail, setDetail] = React.useState<FeedItem | null>(null);

  const { data: items = [], isLoading } = useFeedItems(projectId, {
    tipo: tipoFilter === "all" ? undefined : tipoFilter,
    limit: 100,
    offset: 0,
  });
  const { data: unread } = useFeedUnreadCount(projectId);
  const markReadMutation = useMarkFeedRead(projectId);

  const filtered = React.useMemo(
    () =>
      items.filter((i) => {
        if (autorFilter !== "all" && i.autor !== autorFilter) return false;
        if (unreadOnly && i.leido) return false;
        return true;
      }),
    [items, autorFilter, unreadOnly],
  );

  const handleMarkRead = (item: FeedItem) => {
    if (item.leido) return;
    markReadMutation.mutate(item.id);
  };

  const handleViewDetail = (item: FeedItem) => {
    setDetail(item);
    if (!item.leido) {
      handleMarkRead(item);
    }
  };

  const handleExportCsv = () => {
    if (filtered.length === 0) {
      toast.info("No hay eventos que exportar");
      return;
    }
    const headers = ["fecha", "tipo", "autor", "leido", "titulo", "descripcion"];
    const esc = (v: unknown) =>
      `"${(v === null || v === undefined ? "" : String(v)).replace(/"/g, '""')}"`;
    const rows = filtered.map((i) =>
      [
        i.created_at ?? "",
        i.tipo,
        i.autor,
        i.leido ? "leido" : "sin_leer",
        i.titulo ?? "",
        i.descripcion ?? "",
      ]
        .map(esc)
        .join(","),
    );
    // BOM ﻿ para que Excel lea UTF-8 (acentos) correctamente.
    const csv = `﻿${[headers.join(","), ...rows].join("\r\n")}`;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `timeline-${projectId.slice(0, 8)}-${new Date()
      .toISOString()
      .slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success(`${filtered.length} eventos exportados`);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Activity size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Timeline del proyecto
            <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
              ({filtered.length})
            </span>
          </h3>
          <TooltipENS term="audit_log" />
        </div>
        <div className="flex items-center gap-2">
          {unread && unread.unread_count > 0 ? (
            <Badge variant="warning">
              <Eye className="mr-1 size-3" />
              {unread.unread_count} sin leer
            </Badge>
          ) : null}
          <Button type="button" variant="outline" size="sm" onClick={handleExportCsv}>
            Exportar CSV
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 rounded border border-fulkro-ink-100 bg-fulkro-canvas/50 p-3">
        <Select value={tipoFilter} onValueChange={setTipoFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los tipos</SelectItem>
            {TIPO_OPTIONS.map((t) => (
              <SelectItem key={t} value={t}>
                {TIPO_META[t].label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={autorFilter} onValueChange={setAutorFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Autor" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los autores</SelectItem>
            {AUTOR_OPTIONS.map((a) => (
              <SelectItem key={a} value={a}>
                {a}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <label className="ml-auto inline-flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(e) => setUnreadOnly(e.target.checked)}
            className="size-4"
          />
          Solo sin leer
        </label>
      </div>

      {isLoading ? (
        <p className="text-sm text-fulkro-ink-500">Cargando timeline…</p>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded border border-dashed border-fulkro-ink-200 py-10 text-fulkro-ink-500">
          <Activity className="size-8" />
          <p className="text-sm">Sin eventos para los filtros aplicados</p>
        </div>
      ) : (
        <div className="relative space-y-3 pl-6 before:absolute before:inset-y-0 before:left-2 before:w-px before:bg-fulkro-ink-100">
          {filtered.map((item) => {
            const tipoKey = (TIPO_OPTIONS as string[]).includes(item.tipo)
              ? (item.tipo as FeedItemTipo)
              : "comentario";
            const meta = TIPO_META[tipoKey];
            const Icon = meta.icon;
            return (
              <div key={item.id} className="relative">
                <div
                  className={cn(
                    "absolute -left-6 top-3 size-3 rounded-full border-2",
                    item.leido
                      ? "border-fulkro-ink-200 bg-white"
                      : "border-fulkro-primary-700 bg-fulkro-primary-700",
                  )}
                />
                <Card
                  className={cn(
                    "cursor-pointer transition-colors hover:border-fulkro-primary-700",
                    !item.leido && "border-fulkro-primary-700/40",
                  )}
                  onClick={() => handleViewDetail(item)}
                >
                  <CardHeader className="pb-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Icon className="size-4 text-fulkro-ink-500" />
                        <Badge variant={meta.variant}>{meta.label}</Badge>
                        <Badge variant={AUTOR_VARIANT[item.autor] ?? "outline"}>
                          {item.autor}
                        </Badge>
                        {!item.leido ? <Badge variant="warning">nuevo</Badge> : null}
                      </div>
                      <span className="text-xs text-fulkro-ink-500">
                        {item.created_at
                          ? new Date(item.created_at).toLocaleString("es-ES", {
                              dateStyle: "short",
                              timeStyle: "short",
                            })
                          : "—"}
                      </span>
                    </div>
                    <CardTitle className="text-sm">{item.titulo}</CardTitle>
                  </CardHeader>
                  {item.descripcion ? (
                    <CardContent className="pt-0">
                      <p className="line-clamp-2 text-sm text-fulkro-ink-500">
                        {item.descripcion}
                      </p>
                    </CardContent>
                  ) : null}
                </Card>
              </div>
            );
          })}
        </div>
      )}

      <Sheet
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null);
        }}
      >
        <SheetContent className="w-full sm:max-w-md">
          {detail ? (
            <>
              <SheetHeader>
                <SheetTitle>{detail.titulo}</SheetTitle>
                <SheetDescription>
                  {detail.tipo} · {detail.autor}
                </SheetDescription>
              </SheetHeader>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Descripción</dt>
                  <dd>{detail.descripcion ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Estado lectura</dt>
                  <dd>
                    {detail.leido ? (
                      <Badge variant="success">leído</Badge>
                    ) : (
                      <Badge variant="warning">sin leer</Badge>
                    )}
                  </dd>
                </div>
                {detail.leido_at ? (
                  <div>
                    <dt className="font-medium text-fulkro-ink-700">Leído</dt>
                    <dd>{new Date(detail.leido_at).toLocaleString("es-ES")}</dd>
                  </div>
                ) : null}
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Metadata</dt>
                  <dd>
                    <pre className="mt-1 max-h-60 overflow-auto rounded bg-fulkro-canvas p-2 text-xs">
                      {JSON.stringify(detail.metadata ?? {}, null, 2)}
                    </pre>
                  </dd>
                </div>
                <div className="pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      navigator.clipboard
                        .writeText(JSON.stringify(detail, null, 2))
                        .then(() => toast.success("JSON copiado"))
                        .catch(() => toast.error("No se pudo copiar"));
                    }}
                  >
                    Copiar JSON
                  </Button>
                </div>
              </dl>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
