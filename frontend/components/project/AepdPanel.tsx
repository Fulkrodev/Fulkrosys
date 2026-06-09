/**
 * AepdPanel · Árbol decisión RGPD art.33-34 + countdown 72h (SAN-C MB-11.2).
 *
 * POST /api/v1/projects/{id}/aepd/evaluate · run decision tree + persist
 * GET  /api/v1/projects/{id}/aepd/notifications · lista con countdown
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Clock, Loader2 } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
  type AepdEvaluateRequest,
  type AepdEvaluateResponse,
  type AepdNotification,
  evaluateAepd,
  listAepdNotifications,
} from "@/lib/admin-aepd/api";

interface Props {
  projectId: string;
}

export function AepdPanel({ projectId }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState<AepdEvaluateRequest>({
    affects_personal_data: true,
    risk_to_rights: "medium",
    severity: "medium",
    description: "",
  });

  const notifKey = ["aepd-notifications", projectId];
  const { data: notifications } = useQuery<AepdNotification[]>({
    queryKey: notifKey,
    queryFn: () => listAepdNotifications(projectId),
  });

  const mutation = useMutation<AepdEvaluateResponse, Error, AepdEvaluateRequest>({
    mutationFn: (body) => evaluateAepd(projectId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: notifKey }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>
            Notificaciones AEPD activas{" "}
            <TooltipENS term="incidente_seguridad" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!notifications && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando…
            </div>
          )}
          {notifications && notifications.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Sin notificaciones registradas. Evalúa un incidente abajo.
            </p>
          )}
          {notifications && notifications.length > 0 && (
            <ul className="space-y-3">
              {notifications.map((n) => (
                <li key={n.id} className="border rounded p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        n.severity === "critical" || n.severity === "high"
                          ? "danger"
                          : "default"
                      }
                    >
                      {n.severity}
                    </Badge>
                    <Badge variant="outline">{n.notification_status}</Badge>
                    {n.notify_subjects && (
                      <Badge variant="warning">Comunicar interesados</Badge>
                    )}
                  </div>
                  {n.deadline_hours_remaining !== null &&
                    n.requires_notification && (
                      <div className="flex items-center gap-2 text-sm">
                        <Clock className="h-4 w-4" />
                        <span
                          className={
                            n.deadline_hours_remaining < 24
                              ? "text-destructive font-bold"
                              : ""
                          }
                        >
                          {n.deadline_hours_remaining > 0
                            ? `${n.deadline_hours_remaining.toFixed(1)} h restantes`
                            : `Plazo vencido (${(-n.deadline_hours_remaining).toFixed(1)} h excedidas)`}
                        </span>
                      </div>
                    )}
                  {n.decision_tree_path && (
                    <details className="text-xs text-muted-foreground">
                      <summary className="cursor-pointer">Razonamiento</summary>
                      <ul className="list-disc pl-5 mt-1 space-y-0.5">
                        {n.decision_tree_path.map((step, i) => (
                          <li key={i}>{step}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            Evaluar incidente · árbol decisión{" "}
            <InfoTag term="RGPD" display="RGPD" /> art.33-34
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <input
              id="personal"
              type="checkbox"
              checked={form.affects_personal_data}
              onChange={(e) =>
                setForm({ ...form, affects_personal_data: e.target.checked })
              }
            />
            <Label htmlFor="personal">Afecta datos personales</Label>
          </div>
          <div>
            <Label htmlFor="risk">Riesgo derechos/libertades</Label>
            <select
              id="risk"
              value={form.risk_to_rights}
              onChange={(e) =>
                setForm({
                  ...form,
                  risk_to_rights: e.target
                    .value as AepdEvaluateRequest["risk_to_rights"],
                })
              }
              className="w-full border rounded px-3 py-2"
            >
              <option value="low">Bajo</option>
              <option value="medium">Medio</option>
              <option value="high">Alto</option>
            </select>
          </div>
          <div>
            <Label htmlFor="severity">Severidad</Label>
            <select
              id="severity"
              value={form.severity}
              onChange={(e) =>
                setForm({
                  ...form,
                  severity: e.target.value as AepdEvaluateRequest["severity"],
                })
              }
              className="w-full border rounded px-3 py-2"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div>
            <Label htmlFor="desc">Descripción</Label>
            <Input
              id="desc"
              value={form.description ?? ""}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
            />
          </div>
          <Button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
          >
            {mutation.isPending && (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            )}
            Evaluar
          </Button>

          {mutation.data && (
            <Alert
              variant={
                mutation.data.requires_notification ? "warning" : "default"
              }
            >
              {mutation.data.requires_notification ? (
                <AlertTriangle className="h-4 w-4" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              <AlertTitle>
                {mutation.data.requires_notification
                  ? `Notificación AEPD obligatoria · ${mutation.data.deadline_hours} h`
                  : mutation.data.register_only
                    ? "Registro interno · NO notificar AEPD"
                    : "No aplica RGPD art.33"}
              </AlertTitle>
              <AlertDescription className="space-y-2 mt-2">
                {mutation.data.notify_subjects && (
                  <Badge variant="danger">
                    + Comunicar interesados (art.34)
                  </Badge>
                )}
                <ul className="list-disc pl-5 text-xs">
                  {mutation.data.decision_path.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
                {mutation.data.submission_url && (
                  <a
                    href={mutation.data.submission_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs underline"
                  >
                    Abrir portal AEPD →
                  </a>
                )}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
