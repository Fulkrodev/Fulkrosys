/**
 * ChangeImpactConsole · K.11 Consola de Change Requests (M28).
 *
 * Lista de cambios abiertos del proyecto con state badge + nuevo cambio
 * via dialog. Cada cambio puede pasar por states `intake → assessed →
 * closed`. La materiality (MATERIAL/RELEVANT/MINOR) se determina al
 * `assess`.
 *
 * Backend: m28_change_governance prefix `/api/v1/changes`.
 *   GET  /projects/{id}/changes/open
 *   POST /projects/{id}/changes
 *   POST /projects/{id}/changes/{cid}/assess (no expuesto inline aún ·
 *        flujo asistido en otra vista)
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, ScrollText } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { changesApi, type OpenChangeItem } from "@/lib/api/changes";

const STATE_LABELS: Record<string, string> = {
  intake: "En intake",
  assessed: "Evaluado",
  approved: "Aprobado",
  rejected: "Rechazado",
  closed: "Cerrado",
};

const STATE_VARIANTS: Record<string, "secondary" | "warning" | "success"> = {
  intake: "secondary",
  assessed: "warning",
  approved: "success",
  rejected: "secondary",
};

export function ChangeImpactConsole({ projectId }: { projectId: string }) {
  const qc = useQueryClient();
  const open = useQuery<OpenChangeItem[]>({
    queryKey: ["m28", "changes-open", projectId],
    queryFn: () => changesApi.listOpen(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <ScrollText size={16} /> Cambios e impacto
            </CardTitle>
            <p className="mt-1 text-xs text-fulkro-ink-500">
              Solicitudes de cambio · clasificación automática MATERIAL /
              RELEVANT / MINOR (Motor 28).
            </p>
          </div>
          <NewChangeDialog
            projectId={projectId}
            onCreated={() =>
              qc.invalidateQueries({ queryKey: ["m28", "changes-open", projectId] })
            }
          />
        </CardHeader>
      </Card>

      {open.isLoading ? (
        <Card>
          <CardContent className="space-y-2 p-4">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </CardContent>
        </Card>
      ) : open.isError ? (
        <Alert variant="danger">
          <AlertTitle>No se pudo cargar la lista de cambios</AlertTitle>
          <AlertDescription>
            {open.error instanceof Error ? open.error.message : "Error desconocido"}
          </AlertDescription>
        </Alert>
      ) : !open.data || open.data.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <EmptyState
              title="Sin cambios abiertos"
              description="Cuando se registre una solicitud de cambio aparecerá aquí con su clasificación de materialidad."
            />
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="space-y-2 p-4">
            {open.data.map((c) => (
              <ChangeRow key={c.change_id} item={c} />
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function ChangeRow({ item }: { item: OpenChangeItem }) {
  const variant = STATE_VARIANTS[item.state] ?? "secondary";
  const label = STATE_LABELS[item.state] ?? item.state;

  return (
    <div className="flex items-start justify-between gap-3 rounded-md border border-fulkro-ink-300/60 px-3 py-2">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-fulkro-ink-700">
          {item.description}
        </p>
        <p className="mt-0.5 font-mono text-[10px] text-fulkro-ink-500">
          #{item.change_id.slice(0, 8)}
        </p>
      </div>
      <Badge variant={variant} className="shrink-0">
        {label}
      </Badge>
    </div>
  );
}

function NewChangeDialog({
  projectId,
  onCreated,
}: {
  projectId: string;
  onCreated: () => void;
}) {
  const [open, setOpen] = React.useState(false);
  const [description, setDescription] = React.useState("");
  const [requestedBy, setRequestedBy] = React.useState("marcos");
  const [proposedDate, setProposedDate] = React.useState("");

  const mutation = useMutation({
    mutationFn: () =>
      changesApi.intake(projectId, {
        description: description.trim(),
        requested_by: requestedBy.trim(),
        proposed_date: proposedDate.trim() || null,
      }),
    onSuccess: (result) => {
      toast.success("Cambio registrado", {
        description: `#${result.change_id.slice(0, 8)} · ${result.state}`,
      });
      setOpen(false);
      setDescription("");
      setProposedDate("");
      onCreated();
    },
    onError: (err) => {
      toast.error("No se pudo registrar el cambio", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const canSubmit =
    description.trim().length >= 10 && requestedBy.trim().length >= 2;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus size={14} /> Nuevo cambio
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Registrar cambio</DialogTitle>
          <DialogDescription>
            Describe el cambio propuesto. Tras el intake, el M28 evaluará la
            materialidad y disparará workflows de impacto.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="description">Descripción</Label>
            <Textarea
              id="description"
              rows={4}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe el cambio (mínimo 10 caracteres)…"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="requested-by">Solicitante</Label>
            <Input
              id="requested-by"
              value={requestedBy}
              onChange={(e) => setRequestedBy(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="proposed-date">Fecha propuesta (opcional)</Label>
            <Input
              id="proposed-date"
              type="date"
              value={proposedDate}
              onChange={(e) => setProposedDate(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={mutation.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!canSubmit || mutation.isPending}
          >
            {mutation.isPending ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Plus size={14} />
            )}
            Registrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
