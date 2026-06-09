"use client";

/**
 * OverridesManagementPanel · admin UI para feature_flag_overrides
 * (ADR-046 · MB-10 Atom 10.3.B · renamed post-audit B1.2 · was ADR-037 MB-10).
 *
 * Q5.3 cement sostained: componente SOLO en `(admin)/` route group ·
 * NUNCA cliente-facing. Render condicional gated por server-side
 * middleware admin pool.
 *
 * Funcionalidad:
 * - Lista overrides activos para el proyecto (project-level scope · Q4 cement)
 * - Grant nuevo override (feature select + boolean value + expires + reason)
 * - Revoke override existente (con reason opcional)
 * - Optimistic invalidation post-mutation (TanStack queryClient)
 *
 * Pattern: shadcn primitives only (Table · Dialog · Button · Badge · Label ·
 * Input · Textarea · Switch · Select) · loading skeleton · ApiError handling.
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, PlusCircle, ShieldOff, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { useProjectFeatures } from "@/lib/contexts/ProjectFeaturesContext";
import {
  featureFlagsApi,
  useFeatureFlagOverrides,
} from "@/lib/api/feature-flags";
import { ApiError } from "@/lib/api";
import type {
  FeatureFlagOverride,
  FeatureKey,
} from "@/lib/feature-flags.types";
import { cn } from "@/lib/utils";

interface OverridesManagementPanelProps {
  projectId: string;
}

function formatTs(value: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    return typeof error.message === "string"
      ? error.message
      : "Error en la solicitud";
  }
  if (error instanceof Error) return error.message;
  return "Error desconocido";
}

export function OverridesManagementPanel({
  projectId,
}: OverridesManagementPanelProps) {
  const qc = useQueryClient();
  const overridesQuery = useFeatureFlagOverrides(projectId);
  const featuresCtx = useProjectFeatures();
  const featureKeys = useMemo<FeatureKey[]>(() => {
    if (!featuresCtx.data) return [];
    return Object.keys(featuresCtx.data.features) as FeatureKey[];
  }, [featuresCtx.data]);

  // Grant dialog state
  const [isGrantOpen, setGrantOpen] = useState(false);
  const [grantFeatureKey, setGrantFeatureKey] = useState<string>("");
  const [grantValue, setGrantValue] = useState(true);
  const [grantExpiresAt, setGrantExpiresAt] = useState<string>("");
  const [grantReason, setGrantReason] = useState<string>("");

  // Revoke dialog state
  const [revokeTarget, setRevokeTarget] = useState<FeatureFlagOverride | null>(
    null,
  );
  const [revokeReason, setRevokeReason] = useState<string>("");

  const grantMutation = useMutation({
    mutationFn: featureFlagsApi.grantOverride,
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["feature-flag-overrides", projectId],
      });
      qc.invalidateQueries({ queryKey: ["feature-flags", projectId] });
      setGrantOpen(false);
      setGrantFeatureKey("");
      setGrantValue(true);
      setGrantExpiresAt("");
      setGrantReason("");
    },
  });

  const revokeMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      featureFlagsApi.revokeOverride(id, reason ? { reason } : undefined),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ["feature-flag-overrides", projectId],
      });
      qc.invalidateQueries({ queryKey: ["feature-flags", projectId] });
      setRevokeTarget(null);
      setRevokeReason("");
    },
  });

  const handleGrantSubmit = () => {
    if (!grantFeatureKey) return;
    grantMutation.mutate({
      feature_key: grantFeatureKey,
      override_value: grantValue,
      project_id: projectId,
      expires_at: grantExpiresAt
        ? new Date(grantExpiresAt).toISOString()
        : null,
      reason: grantReason || null,
    });
  };

  const handleRevokeSubmit = () => {
    if (!revokeTarget) return;
    revokeMutation.mutate({
      id: revokeTarget.id,
      reason: revokeReason || undefined,
    });
  };

  const overrides = overridesQuery.data ?? [];
  const currentFeatures = featuresCtx.data?.features ?? {};

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-base font-semibold text-foreground">
            <Sparkles className="h-4 w-4" aria-hidden />
            Overrides activos
          </h2>
          <p className="text-sm text-muted-foreground">
            Ajustes manuales aplicados sobre la evaluación automática del
            proyecto (categoría ENS + arquetipo PYME).
          </p>
        </div>
        <Button
          type="button"
          onClick={() => setGrantOpen(true)}
          disabled={featureKeys.length === 0}
        >
          <PlusCircle className="mr-2 h-4 w-4" aria-hidden />
          Conceder override
        </Button>
      </header>

      {overridesQuery.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : overridesQuery.error ? (
        <div
          role="alert"
          className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {describeError(overridesQuery.error)}
        </div>
      ) : overrides.length === 0 ? (
        <div className="rounded-md border border-dashed border-border bg-muted/40 p-8 text-center">
          <p className="text-sm text-muted-foreground">
            Sin overrides activos para este proyecto.
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Las capabilities se evalúan por defecto desde categoría +
            arquetipo. Concede un override manual cuando necesites forzar un
            valor distinto.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Feature</TableHead>
                <TableHead>Valor actual</TableHead>
                <TableHead>Override</TableHead>
                <TableHead>Concedido</TableHead>
                <TableHead>Expira</TableHead>
                <TableHead>Motivo</TableHead>
                <TableHead className="w-24 text-right">Acción</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {overrides.map((row) => {
                const resolved = (currentFeatures as Record<string, unknown>)[
                  row.feature_key
                ];
                const overrideBool = String(row.override_value);
                return (
                  <TableRow key={row.id}>
                    <TableCell className="font-mono text-xs">
                      {row.feature_key}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={resolved ? "default" : "outline"}
                        className={cn(
                          resolved
                            ? "bg-emerald-100 text-emerald-900 hover:bg-emerald-100"
                            : "bg-slate-100 text-slate-800 hover:bg-slate-100",
                        )}
                      >
                        {resolved ? "activa" : "inactiva"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs">{overrideBool}</span>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatTs(row.granted_at)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {row.expires_at ? formatTs(row.expires_at) : "Permanente"}
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-xs text-muted-foreground">
                      {row.reason || "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => setRevokeTarget(row)}
                        data-testid={`revoke-${row.feature_key}`}
                      >
                        <ShieldOff className="mr-1 h-3 w-3" aria-hidden />
                        Revocar
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Grant dialog */}
      <Dialog open={isGrantOpen} onOpenChange={setGrantOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Conceder override de capability</DialogTitle>
            <DialogDescription>
              Forzar un valor manual para una feature flag de este proyecto.
              El override prevalece sobre la evaluación automática hasta su
              revocación o expiración.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="grant-feature-key">Feature</Label>
              <Select
                value={grantFeatureKey}
                onValueChange={setGrantFeatureKey}
              >
                <SelectTrigger
                  id="grant-feature-key"
                  data-testid="grant-feature-select"
                >
                  <SelectValue placeholder="Selecciona una feature" />
                </SelectTrigger>
                <SelectContent>
                  {featureKeys.map((key) => (
                    <SelectItem key={key} value={key}>
                      {key}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center justify-between rounded-md border border-border p-3">
              <div>
                <Label
                  htmlFor="grant-value"
                  className="text-sm font-medium"
                >
                  Valor del override
                </Label>
                <p className="text-xs text-muted-foreground">
                  Activado fuerza la feature como habilitada · desactivado
                  fuerza deshabilitada.
                </p>
              </div>
              <Switch
                id="grant-value"
                checked={grantValue}
                onCheckedChange={setGrantValue}
                data-testid="grant-value-switch"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="grant-expires-at">
                Fecha de expiración (opcional)
              </Label>
              <Input
                id="grant-expires-at"
                type="datetime-local"
                value={grantExpiresAt}
                onChange={(e) => setGrantExpiresAt(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Dejar vacío para override permanente (hasta revocación).
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="grant-reason">Motivo (recomendado)</Label>
              <Textarea
                id="grant-reason"
                value={grantReason}
                onChange={(e) => setGrantReason(e.target.value)}
                placeholder="Justificación operativa o comercial del override"
                rows={3}
              />
            </div>

            {grantMutation.error ? (
              <div
                role="alert"
                className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-800"
              >
                {describeError(grantMutation.error)}
              </div>
            ) : null}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setGrantOpen(false)}
              disabled={grantMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              onClick={handleGrantSubmit}
              disabled={!grantFeatureKey || grantMutation.isPending}
              data-testid="grant-submit"
            >
              {grantMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
              ) : null}
              Conceder
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Revoke dialog */}
      <Dialog
        open={Boolean(revokeTarget)}
        onOpenChange={(open) => {
          if (!open) {
            setRevokeTarget(null);
            setRevokeReason("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revocar override</DialogTitle>
            <DialogDescription>
              {revokeTarget
                ? `La feature ${revokeTarget.feature_key} volverá a evaluarse según categoría ENS + arquetipo PYME.`
                : null}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            <Label htmlFor="revoke-reason">Motivo (opcional)</Label>
            <Textarea
              id="revoke-reason"
              value={revokeReason}
              onChange={(e) => setRevokeReason(e.target.value)}
              placeholder="Por qué se revoca este override"
              rows={3}
              data-testid="revoke-reason-input"
            />
          </div>

          {revokeMutation.error ? (
            <div
              role="alert"
              className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-800"
            >
              {describeError(revokeMutation.error)}
            </div>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setRevokeTarget(null);
                setRevokeReason("");
              }}
              disabled={revokeMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={handleRevokeSubmit}
              disabled={revokeMutation.isPending}
              data-testid="revoke-confirm"
            >
              {revokeMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
              ) : null}
              Revocar override
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
