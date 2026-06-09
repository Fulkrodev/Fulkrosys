/**
 * MagicLinkHistoryTable · listado y revoke admin de magic links emitidos.
 *
 * FASE 4.5 sub-bloque B.2 · GET /api/v1/magic-links + revoke action.
 *
 * Filtros:
 *   - project_id (UUID opcional · si vacío lista cross-project)
 *   - purpose (multi via select)
 *   - active_only (toggle)
 *
 * Estados Badge: activo / expirado / revocado / agotado.
 */
"use client";

import * as React from "react";
import { Loader2, Undo2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useMagicLinkList,
  useRevokeMagicLink,
} from "@/hooks/magic-link";
import {
  MAGIC_LINK_BACKEND_CATEGORIES,
  MAGIC_LINK_BACKEND_LABELS,
  type MagicLinkBackendPurpose,
  type MagicLinkRecord,
} from "@/lib/magic-link-types";
import { fulkroToast } from "@/lib/toast";

type LinkStatus = "activo" | "expirado" | "revocado" | "agotado";

function deriveStatus(row: MagicLinkRecord): LinkStatus {
  if (row.revocado) return "revocado";
  if (new Date(row.expira_at) < new Date()) return "expirado";
  if (row.max_usos != null && row.usos >= row.max_usos) return "agotado";
  return "activo";
}

const STATUS_VARIANT: Record<LinkStatus, "outline" | "secondary" | "danger"> = {
  activo: "secondary",
  expirado: "outline",
  revocado: "danger",
  agotado: "outline",
};

export function MagicLinkHistoryTable() {
  const [projectId, setProjectId] = React.useState("");
  const [purpose, setPurpose] = React.useState<MagicLinkBackendPurpose | "">("");
  const [activeOnly, setActiveOnly] = React.useState(false);

  const { data: rows, isLoading } = useMagicLinkList({
    project_id: projectId || undefined,
    purpose: (purpose || undefined) as MagicLinkBackendPurpose | undefined,
    active_only: activeOnly,
    limit: 100,
  });

  const revoke = useRevokeMagicLink();

  async function handleRevoke(id: string) {
    if (!window.confirm("¿Revocar este enlace? La acción es inmediata.")) {
      return;
    }
    try {
      await revoke.mutateAsync(id);
      fulkroToast.success("Enlace revocado");
    } catch (err) {
      fulkroToast.error("No se pudo revocar el enlace", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Histórico de enlaces</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="space-y-1.5">
            <Label htmlFor="filter_project">Proyecto (UUID, opcional)</Label>
            <Input
              id="filter_project"
              placeholder="Cross-project si vacío"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value.trim())}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="filter_purpose">Tipo de operación</Label>
            <Select
              value={purpose}
              onValueChange={(v) => setPurpose(v as MagicLinkBackendPurpose | "")}
            >
              <SelectTrigger id="filter_purpose">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Todos</SelectItem>
                {Object.entries(MAGIC_LINK_BACKEND_CATEGORIES).map(
                  ([cat, items]) => (
                    <SelectGroup key={cat}>
                      <SelectLabel>{cat}</SelectLabel>
                      {items.map((p) => (
                        <SelectItem key={p} value={p}>
                          {MAGIC_LINK_BACKEND_LABELS[p]}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end justify-between rounded-md border border-fulkro-ink-300/60 px-3 py-2">
            <Label htmlFor="filter_active" className="cursor-pointer">
              Solo activos
            </Label>
            <Switch
              id="filter_active"
              checked={activeOnly}
              onCheckedChange={setActiveOnly}
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
            <Loader2 size={14} className="animate-spin" /> cargando…
          </div>
        ) : !rows || rows.length === 0 ? (
          <EmptyState
            title="Sin enlaces"
            description="Aún no se han generado enlaces seguros con estos filtros."
          />
        ) : (
          <div className="overflow-hidden rounded-md border border-fulkro-ink-300/60">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Creado</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Destinatario</TableHead>
                  <TableHead className="text-right">Usos</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => {
                  const st = deriveStatus(row);
                  return (
                    <TableRow key={row.id}>
                      <TableCell className="whitespace-nowrap text-xs text-fulkro-ink-500">
                        {new Date(row.created_at).toLocaleString("es-ES", {
                          day: "2-digit",
                          month: "2-digit",
                          year: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </TableCell>
                      <TableCell className="text-sm">
                        {MAGIC_LINK_BACKEND_LABELS[
                          row.tipo_operacion as MagicLinkBackendPurpose
                        ] ?? row.tipo_operacion}
                      </TableCell>
                      <TableCell className="truncate text-xs text-fulkro-ink-700">
                        {row.recipient_email ?? "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs">
                        {row.usos}/{row.max_usos ?? 1}
                      </TableCell>
                      <TableCell>
                        <Badge variant={STATUS_VARIANT[st]}>{st}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {st === "activo" ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRevoke(row.id)}
                            disabled={revoke.isPending}
                            title="Revocar enlace"
                          >
                            <Undo2 size={14} />
                          </Button>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
