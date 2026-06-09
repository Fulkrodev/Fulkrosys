"use client";

/**
 * ExitChecklist real · M25 wired (SAN-E v3.MB-3.1).
 *
 * Sustituye stub `EmptyStateUpcoming` post-FASE-9 con UI completa
 * cableada al backend M25 exit-checklist (commit MB-3.A 2447fd6).
 *
 * 4 secciones:
 * A. Header readiness · progress global + check button + blockers preview
 * B. Filtros · categoria / status / busqueda
 * C. TanStack Table · 16 default items con acciones por row
 * D. Footer cerrar proyecto · solo visible si ready_to_close=true
 *
 * ADR-046 v3 SAN-E.MB-3.A: capa validacion granular pre-cierre proyecto
 * sobre lifecycle FSM existing. NO sustituye state machine M25 ·
 * pre-condicion para transitar a ENDED_*.
 */
import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  HelpCircle,
  Loader2,
  Search,
  XCircle,
} from "lucide-react";
import { type ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useExitChecklist } from "@/hooks/useExitChecklist";
import type {
  ExitCategory,
  ExitChecklistItem,
  ExitStatus,
} from "@/lib/admin-exit/api";

const CATEGORY_LABELS: Record<ExitCategory, string> = {
  legal: "Legal",
  tecnico: "Técnico",
  documentacion: "Documentación",
  operacional: "Operacional",
};

const STATUS_LABELS: Record<ExitStatus, string> = {
  pendiente: "Pendiente",
  completado: "Completado",
  bloqueado: "Bloqueado",
  no_aplica: "No aplica",
};

function StatusBadge({ status }: { status: ExitStatus }) {
  const map: Record<
    ExitStatus,
    {
      variant: "default" | "secondary" | "outline" | "success" | "warning" | "danger";
      icon: React.ReactNode;
    }
  > = {
    completado: {
      variant: "success",
      icon: <CheckCircle2 size={12} strokeWidth={2.4} />,
    },
    pendiente: { variant: "secondary", icon: null },
    bloqueado: {
      variant: "danger",
      icon: <XCircle size={12} strokeWidth={2.4} />,
    },
    no_aplica: { variant: "outline", icon: null },
  };
  const cfg = map[status];
  return (
    <Badge variant={cfg.variant} className="gap-1">
      {cfg.icon}
      {STATUS_LABELS[status]}
    </Badge>
  );
}

function CategoryBadge({ category }: { category: ExitCategory }) {
  const variant: "info" | "warning" | "accent" | "default" = (
    {
      legal: "info",
      tecnico: "warning",
      documentacion: "accent",
      operacional: "default",
    } as const
  )[category];
  return <Badge variant={variant}>{CATEGORY_LABELS[category]}</Badge>;
}

interface CompleteDialogState {
  open: boolean;
  itemId: string | null;
  itemLabel: string;
  evidenceId: string;
  note: string;
}

interface SetStatusDialogState {
  open: boolean;
  itemId: string | null;
  itemLabel: string;
  status: ExitStatus;
  note: string;
}

export function ExitChecklist({ projectId }: { projectId: string }) {
  const cl = useExitChecklist(projectId);
  const [categoryFilter, setCategoryFilter] = React.useState<
    ExitCategory | "todas"
  >("todas");
  const [statusFilter, setStatusFilter] = React.useState<ExitStatus | "todos">(
    "todos",
  );
  const [search, setSearch] = React.useState("");

  const [completeDialog, setCompleteDialog] = React.useState<CompleteDialogState>(
    {
      open: false,
      itemId: null,
      itemLabel: "",
      evidenceId: "",
      note: "",
    },
  );

  const [statusDialog, setStatusDialog] = React.useState<SetStatusDialogState>({
    open: false,
    itemId: null,
    itemLabel: "",
    status: "no_aplica",
    note: "",
  });

  const [closeConfirmOpen, setCloseConfirmOpen] = React.useState(false);
  const [closeAck, setCloseAck] = React.useState(false);

  const items = cl.data?.items ?? [];
  const progress = cl.data?.progress;

  const filtered = React.useMemo(
    () =>
      items.filter((it) => {
        if (categoryFilter !== "todas" && it.category !== categoryFilter)
          return false;
        if (statusFilter !== "todos" && it.status !== statusFilter) return false;
        if (search && !it.label.toLowerCase().includes(search.toLowerCase()))
          return false;
        return true;
      }),
    [items, categoryFilter, statusFilter, search],
  );

  const readiness = cl.checkReadiness.data;

  const openComplete = (item: ExitChecklistItem) =>
    setCompleteDialog({
      open: true,
      itemId: item.id,
      itemLabel: item.label,
      evidenceId: item.evidence_id ?? "",
      note: item.note ?? "",
    });

  const submitComplete = async () => {
    if (!completeDialog.itemId) return;
    await cl.completeItem.mutateAsync({
      itemId: completeDialog.itemId,
      evidence_id: completeDialog.evidenceId.trim() || null,
      note: completeDialog.note.trim() || null,
    });
    setCompleteDialog({
      open: false,
      itemId: null,
      itemLabel: "",
      evidenceId: "",
      note: "",
    });
  };

  const openSetStatus = (item: ExitChecklistItem, status: ExitStatus) =>
    setStatusDialog({
      open: true,
      itemId: item.id,
      itemLabel: item.label,
      status,
      note: item.note ?? "",
    });

  const submitSetStatus = async () => {
    if (!statusDialog.itemId) return;
    await cl.setStatus.mutateAsync({
      itemId: statusDialog.itemId,
      status: statusDialog.status,
      note: statusDialog.note.trim() || null,
    });
    setStatusDialog({
      open: false,
      itemId: null,
      itemLabel: "",
      status: "no_aplica",
      note: "",
    });
  };

  const columns: ColumnDef<ExitChecklistItem>[] = [
    {
      accessorKey: "label",
      header: "Item",
      cell: ({ row }) => (
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-[color:var(--fulkro-title)]">
            {row.original.label}
          </span>
          <span className="text-xs text-fulkro-ink-500">
            {row.original.item_code}
          </span>
        </div>
      ),
    },
    {
      accessorKey: "category",
      header: "Categoría",
      cell: ({ row }) => <CategoryBadge category={row.original.category} />,
    },
    {
      accessorKey: "status",
      header: "Estado",
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: "evidence_id",
      header: () => (
        // WCAG nested-interactive: este header se renderiza DENTRO del botón
        // de ordenación del DataTable · el trigger del tooltip debe ser un
        // <span> no focusable, nunca un <button> anidado.
        <span className="inline-flex items-center gap-1">
          Evidencia{" "}
          <TooltipENS term="evidencia">
            <span className="inline-flex items-center text-fulkro-primary-500/70 hover:text-fulkro-primary-700">
              <HelpCircle size={14} aria-hidden />
            </span>
          </TooltipENS>
        </span>
      ),
      cell: ({ row }) =>
        row.original.evidence_id ? (
          <span className="font-mono text-xs text-fulkro-info">
            {row.original.evidence_id.slice(0, 8)}…
          </span>
        ) : (
          <span className="text-xs text-fulkro-ink-600">—</span>
        ),
    },
    {
      accessorKey: "completed_at",
      header: "Completado",
      cell: ({ row }) =>
        row.original.completed_at ? (
          <div className="flex flex-col gap-0.5 text-xs">
            <span className="text-fulkro-ink-700">
              {new Date(row.original.completed_at).toLocaleDateString("es-ES")}
            </span>
            {row.original.completed_by ? (
              <span className="text-fulkro-ink-600">
                {row.original.completed_by}
              </span>
            ) : null}
          </div>
        ) : (
          <span className="text-xs text-fulkro-ink-600">—</span>
        ),
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => {
        const it = row.original;
        return (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                Acciones <ChevronDown size={14} strokeWidth={2.4} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {it.status !== "completado" ? (
                <DropdownMenuItem onClick={() => openComplete(it)}>
                  Marcar completado
                </DropdownMenuItem>
              ) : (
                <DropdownMenuItem
                  onClick={() => cl.uncompleteItem.mutate(it.id)}
                  className="text-fulkro-warning"
                >
                  Revertir a pendiente
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onClick={() => openSetStatus(it, "no_aplica")}>
                Marcar no aplica
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => openSetStatus(it, "bloqueado")}>
                Marcar bloqueado
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        );
      },
    },
  ];

  const completedPct = progress?.completed_pct ?? 0;
  const blockersPreview = readiness?.blockers ?? [];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      {/* A · Header readiness */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[color:var(--fulkro-title)]">
            Checklist de cierre{" "}
            <TooltipENS term="workflow_retainer_cierre" iconSize={16} />
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-xs uppercase tracking-wide text-fulkro-ink-600">
                Progreso
              </span>
              <span className="text-2xl font-bold text-[color:var(--fulkro-title)]">
                {progress?.completed ?? 0} / {progress?.total ?? 0}
              </span>
              <span className="text-xs text-fulkro-ink-500">
                {completedPct.toFixed(0)}% completado
              </span>
            </div>
            <div className="flex-1" />
            {readiness ? (
              readiness.ready_to_close ? (
                <Badge
                  variant="success"
                  className="gap-1 px-3 py-1 text-sm font-semibold"
                >
                  <CheckCircle2 size={16} strokeWidth={2.4} /> Listo para cerrar
                </Badge>
              ) : (
                <Badge
                  variant="danger"
                  className="gap-1 px-3 py-1 text-sm font-semibold"
                >
                  <AlertTriangle size={16} strokeWidth={2.4} /> Bloqueado ·{" "}
                  {readiness.blockers.length}
                </Badge>
              )
            ) : null}
            <Button
              variant="outline"
              onClick={() => cl.checkReadiness.mutate()}
              disabled={cl.checkReadiness.isPending}
            >
              {cl.checkReadiness.isPending ? (
                <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
              ) : null}
              Verificar readiness
            </Button>
          </div>
          {blockersPreview.length > 0 ? (
            <div className="rounded-md border border-fulkro-warning/30 bg-fulkro-warning/5 p-3">
              <p className="mb-1 text-xs font-bold uppercase tracking-wide text-fulkro-warning">
                Bloqueantes
              </p>
              <ul className="list-disc space-y-0.5 pl-5 text-sm text-fulkro-ink-700">
                {blockersPreview.slice(0, 5).map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
                {blockersPreview.length > 5 ? (
                  <li className="text-fulkro-ink-600">
                    + {blockersPreview.length - 5} adicionales…
                  </li>
                ) : null}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* B · Filtros */}
      <Card>
        <CardContent className="flex flex-wrap items-end gap-3 pt-6">
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">Categoría</Label>
            <Select
              value={categoryFilter}
              onValueChange={(v) =>
                setCategoryFilter(v as ExitCategory | "todas")
              }
            >
              <SelectTrigger
                className="w-[180px]"
                aria-label="Filtrar por categoría"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas</SelectItem>
                <SelectItem value="legal">Legal</SelectItem>
                <SelectItem value="tecnico">Técnico</SelectItem>
                <SelectItem value="documentacion">Documentación</SelectItem>
                <SelectItem value="operacional">Operacional</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs">Estado</Label>
            <Select
              value={statusFilter}
              onValueChange={(v) => setStatusFilter(v as ExitStatus | "todos")}
            >
              <SelectTrigger
                className="w-[180px]"
                aria-label="Filtrar por estado"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos</SelectItem>
                <SelectItem value="pendiente">Pendiente</SelectItem>
                <SelectItem value="completado">Completado</SelectItem>
                <SelectItem value="bloqueado">Bloqueado</SelectItem>
                <SelectItem value="no_aplica">No aplica</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex min-w-[220px] flex-1 flex-col gap-1.5">
            <Label className="text-xs">Búsqueda</Label>
            <div className="relative">
              <Search
                size={14}
                strokeWidth={2.4}
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-fulkro-ink-600"
              />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Buscar por descripción…"
                className="pl-8"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* C · TanStack Table */}
      <DataTable
        columns={columns}
        data={filtered}
        loading={cl.isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-1 py-6 text-center">
            <p className="text-sm font-bold text-[color:var(--fulkro-title)]">
              No hay items que coincidan con los filtros
            </p>
            <p className="text-xs text-fulkro-ink-500">
              Ajusta los filtros o verifica los items completados.
            </p>
          </div>
        }
      />

      {/* D · Footer cerrar proyecto */}
      {readiness?.ready_to_close ? (
        <Card className="border-fulkro-success/40 bg-fulkro-success/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
            <div className="flex flex-col gap-0.5">
              <p className="text-sm font-bold text-[color:var(--fulkro-title)]">
                Todos los bloqueantes resueltos
              </p>
              <p className="text-xs text-fulkro-ink-500">
                El proyecto está listo para transitar a estado cerrado vía M25
                lifecycle.
              </p>
            </div>
            <Button variant="primary" onClick={() => setCloseConfirmOpen(true)}>
              Cerrar proyecto
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {/* Modal · complete con evidencia + note */}
      <Dialog
        open={completeDialog.open}
        onOpenChange={(v) => setCompleteDialog((s) => ({ ...s, open: v }))}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Marcar completado · {completeDialog.itemLabel}
            </DialogTitle>
            <DialogDescription>
              Vincula opcionalmente una evidencia (UUID) y añade una nota
              auditoría.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>
                Evidencia ID (opcional){" "}
                <TooltipENS term="evidencia" iconSize={14} />
              </Label>
              <Input
                value={completeDialog.evidenceId}
                onChange={(e) =>
                  setCompleteDialog((s) => ({
                    ...s,
                    evidenceId: e.target.value,
                  }))
                }
                placeholder="00000000-…"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Nota</Label>
              <Textarea
                value={completeDialog.note}
                onChange={(e) =>
                  setCompleteDialog((s) => ({ ...s, note: e.target.value }))
                }
                placeholder="Razón / contexto / referencia documento"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setCompleteDialog((s) => ({ ...s, open: false }))}
            >
              Cancelar
            </Button>
            <Button
              onClick={submitComplete}
              disabled={cl.completeItem.isPending}
            >
              {cl.completeItem.isPending ? (
                <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
              ) : null}
              Confirmar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal · set-status (bloqueado / no_aplica) */}
      <Dialog
        open={statusDialog.open}
        onOpenChange={(v) => setStatusDialog((s) => ({ ...s, open: v }))}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {STATUS_LABELS[statusDialog.status]} · {statusDialog.itemLabel}
            </DialogTitle>
            <DialogDescription>
              Justifica el cambio de estado para el log de auditoría.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-1.5">
            <Label>Justificación</Label>
            <Textarea
              value={statusDialog.note}
              onChange={(e) =>
                setStatusDialog((s) => ({ ...s, note: e.target.value }))
              }
              placeholder="Razón del cambio…"
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setStatusDialog((s) => ({ ...s, open: false }))}
            >
              Cancelar
            </Button>
            <Button onClick={submitSetStatus} disabled={cl.setStatus.isPending}>
              {cl.setStatus.isPending ? (
                <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
              ) : null}
              Confirmar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal · cerrar proyecto */}
      <Dialog open={closeConfirmOpen} onOpenChange={setCloseConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cerrar proyecto</DialogTitle>
            <DialogDescription>
              Esta acción dispara la transición lifecycle a estado terminal. El
              cliente será notificado y el workflow quedará bloqueado.
            </DialogDescription>
          </DialogHeader>
          <label className="flex cursor-pointer items-start gap-2 rounded-md border border-fulkro-ink-200 p-3 text-sm">
            <input
              type="checkbox"
              checked={closeAck}
              onChange={(e) => setCloseAck(e.target.checked)}
              className="mt-0.5 h-4 w-4"
            />
            <span className="text-fulkro-ink-700">
              Entiendo que esto bloquea el workflow + notifica al cliente.
            </span>
          </label>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCloseConfirmOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              disabled={!closeAck}
              onClick={() => {
                // Wired backend M25 lifecycle transition: POST
                // /api/v1/lifecycle/projects/{id}/lifecycle/transition.
                // Cabla en MB-3.next con confirmación manual Marcos.
                setCloseConfirmOpen(false);
                setCloseAck(false);
              }}
            >
              Cerrar proyecto
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
