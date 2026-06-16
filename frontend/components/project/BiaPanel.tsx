/**
 * BiaPanel · Business Impact Analysis (SAN-C MB-11.5).
 *
 * GET /api/v1/projects/{id}/bia/analyses · lista entries
 * GET /api/v1/projects/{id}/bia/summary  · agregado
 * POST /api/v1/projects/{id}/bia/analyses · crea entry
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  type BiaEntry,
  type BiaEntryCreate,
  type BiaSummary,
  createBiaEntry,
  getBiaSummary,
  listBiaEntries,
} from "@/lib/admin-bia/api";

interface Props {
  projectId: string;
}

export function BiaPanel({ projectId }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState<BiaEntryCreate>({
    service_name: "",
    rto_hours: 4,
    rpo_hours: 1,
  });

  const entriesKey = ["bia-entries", projectId];
  const summaryKey = ["bia-summary", projectId];

  const { data: entries, isLoading: entriesLoading } = useQuery<BiaEntry[]>({
    queryKey: entriesKey,
    queryFn: () => listBiaEntries(projectId),
  });

  const { data: summary } = useQuery<BiaSummary>({
    queryKey: summaryKey,
    queryFn: () => getBiaSummary(projectId),
  });

  const mutation = useMutation({
    mutationFn: (body: BiaEntryCreate) => createBiaEntry(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: entriesKey });
      qc.invalidateQueries({ queryKey: summaryKey });
      setForm({ service_name: "", rto_hours: 4, rpo_hours: 1 });
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>
            <InfoTag term="BIA" display="BIA" /> · Resumen agregado
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {summary ? (
            <>
              <div>Servicios analizados: <strong>{summary.services_count}</strong></div>
              <div>Max RTO: <strong>{summary.max_rto_hours ?? "—"} h</strong></div>
              <div>Max RPO: <strong>{summary.max_rpo_hours ?? "—"} h</strong></div>
              <div>Impacto diario total: <strong>{summary.total_daily_impact_eur ?? "—"} €</strong></div>
            </>
          ) : (
            <span className="text-muted-foreground">Cargando…</span>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            Servicios críticos{" "}
            <TooltipENS text="Los servicios que más te dolería que cayeran (operativa · financiera · reputacionalmente). El BIA mide cuánto y por cuánto tiempo." />
          </CardTitle>
        </CardHeader>
        <CardContent>
          {entriesLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando…
            </div>
          )}
          {entries && entries.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Sin servicios analizados aún. Añade el primero abajo.
            </p>
          )}
          {entries && entries.length > 0 && (
            <table aria-label="Análisis de impacto en el negocio (BIA)" className="w-full text-sm">
              <thead>
                <tr className="text-left">
                  <th className="py-2">Servicio</th>
                  <th>RTO (h)</th>
                  <th>RPO (h)</th>
                  <th>Impacto/día</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id} className="border-t">
                    <td className="py-2">{e.service_name}</td>
                    <td>{e.rto_hours}</td>
                    <td>{e.rpo_hours}</td>
                    <td>{e.daily_impact_eur ?? "—"} €</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Añadir servicio</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label htmlFor="svc">Nombre servicio</Label>
            <Input
              id="svc"
              value={form.service_name}
              onChange={(e) => setForm({ ...form, service_name: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <Label htmlFor="rto">
                RTO (horas) <TooltipENS term="RTO" />
              </Label>
              <Input
                id="rto"
                type="number"
                value={form.rto_hours}
                onChange={(e) =>
                  setForm({ ...form, rto_hours: Number(e.target.value) })
                }
              />
            </div>
            <div>
              <Label htmlFor="rpo">
                RPO (horas) <TooltipENS term="RPO" />
              </Label>
              <Input
                id="rpo"
                type="number"
                value={form.rpo_hours}
                onChange={(e) =>
                  setForm({ ...form, rpo_hours: Number(e.target.value) })
                }
              />
            </div>
            <div>
              <Label htmlFor="impact">Impacto diario (€)</Label>
              <Input
                id="impact"
                type="number"
                value={form.daily_impact_eur ?? ""}
                onChange={(e) =>
                  setForm({ ...form, daily_impact_eur: e.target.value || undefined })
                }
              />
            </div>
          </div>
          <Button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending || !form.service_name}
          >
            {mutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Plus className="h-4 w-4 mr-2" />
            )}
            Añadir
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
