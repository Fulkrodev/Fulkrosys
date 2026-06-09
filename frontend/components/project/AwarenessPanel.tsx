/**
 * AwarenessPanel · Sesiones formación + asistencia + coverage (SAN-C MB-11.5).
 *
 * GET  /api/v1/projects/{id}/awareness/sessions · lista
 * POST /api/v1/projects/{id}/awareness/sessions · schedule
 * POST /api/v1/awareness/sessions/{sid}/attendance · record
 * GET  /api/v1/projects/{id}/awareness/coverage?expected · % coverage
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type AwarenessSession,
  type CoverageResponse,
  type SessionCreate,
  getCoverage,
  listAwarenessSessions,
  scheduleSession,
} from "@/lib/admin-awareness/api";

interface Props {
  projectId: string;
}

export function AwarenessPanel({ projectId }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState<SessionCreate>({
    title: "",
    scheduled_date: new Date().toISOString().slice(0, 16),
    mandatory: true,
  });
  const [expected, setExpected] = useState<number>(10);

  const sessKey = ["awareness-sessions", projectId];
  const { data: sessions, isLoading } = useQuery<AwarenessSession[]>({
    queryKey: sessKey,
    queryFn: () => listAwarenessSessions(projectId),
  });

  const coverageMutation = useMutation<CoverageResponse, Error, number>({
    mutationFn: (n: number) => getCoverage(projectId, n),
  });

  const scheduleMutation = useMutation({
    mutationFn: (body: SessionCreate) => scheduleSession(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: sessKey });
      setForm({
        title: "",
        scheduled_date: new Date().toISOString().slice(0, 16),
        mandatory: true,
      });
    },
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Coverage formación</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Label htmlFor="expected">Empleados esperados</Label>
              <Input
                id="expected"
                type="number"
                value={expected}
                onChange={(e) => setExpected(Number(e.target.value))}
              />
            </div>
            <Button
              onClick={() => coverageMutation.mutate(expected)}
              disabled={coverageMutation.isPending || expected <= 0}
            >
              {coverageMutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Calcular
            </Button>
          </div>
          {coverageMutation.data && (
            <div className="text-sm space-y-1">
              <div>
                Asistentes únicos último año:{" "}
                <strong>{coverageMutation.data.unique_attendees}</strong> /{" "}
                {coverageMutation.data.expected_attendees}
              </div>
              <Badge
                variant={
                  coverageMutation.data.coverage_pct >= 80
                    ? "default"
                    : "danger"
                }
              >
                Coverage: {coverageMutation.data.coverage_pct.toFixed(1)}%
              </Badge>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Sesiones formación</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando…
            </div>
          )}
          {sessions && sessions.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Sin sesiones programadas. Añade la primera abajo.
            </p>
          )}
          {sessions && sessions.length > 0 && (
            <ul className="space-y-2 text-sm">
              {sessions.map((s) => (
                <li key={s.id} className="border-b pb-2">
                  <div className="flex items-center gap-2">
                    <strong>{s.title}</strong>
                    {s.mandatory && (
                      <Badge variant="outline">Obligatoria</Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Programada: {new Date(s.scheduled_date).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Programar sesión</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label htmlFor="title">Título</Label>
            <Input
              id="title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="date">Fecha programada</Label>
            <Input
              id="date"
              type="datetime-local"
              value={form.scheduled_date}
              onChange={(e) =>
                setForm({ ...form, scheduled_date: e.target.value })
              }
            />
          </div>
          <Button
            onClick={() =>
              scheduleMutation.mutate({
                ...form,
                scheduled_date: new Date(form.scheduled_date).toISOString(),
              })
            }
            disabled={scheduleMutation.isPending || !form.title}
          >
            {scheduleMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Plus className="h-4 w-4 mr-2" />
            )}
            Programar
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
