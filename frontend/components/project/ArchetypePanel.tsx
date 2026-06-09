/**
 * ArchetypePanel · 6 arquetipos PYME classification (SAN-C MB-11.6).
 *
 * Backend:
 *   POST /api/v1/projects/{id}/classify-archetype · ejecuta classifier
 *   GET  /api/v1/projects/{id}/archetype · retorna persisted
 *
 * Flujo UI:
 *   1. Carga inicial: GET archetype (404 si nunca clasificado).
 *   2. Form para overrides (cnae, sector, infra, workforce, aapp_dev).
 *   3. POST classify-archetype · re-fetch + render reasoning + adjustments.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Sparkles } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  classifyArchetype,
  getArchetype,
} from "@/lib/admin-archetype/api";
import {
  ARQUETIPO_LABELS,
  type ArchetypeResponse,
  type ClassifyArchetypeRequest,
} from "@/lib/admin-archetype/schemas";

interface Props {
  projectId: string;
}

export function ArchetypePanel({ projectId }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState<ClassifyArchetypeRequest>({});

  const queryKey = ["project-archetype", projectId];
  const { data, isLoading, error } = useQuery<ArchetypeResponse>({
    queryKey,
    queryFn: () => getArchetype(projectId),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: (body: ClassifyArchetypeRequest) =>
      classifyArchetype(projectId, body),
    onSuccess: (res) => {
      qc.setQueryData(queryKey, res);
    },
  });

  const notClassified = !data && error !== null;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Arquetipo PYME{" "}
            <TooltipENS text="Tu proyecto se ha clasificado en uno de los 7 arquetipos PYME (SaaS · teletrabajo · sector salud · educación · proveedor financiero · desarrollador AAPP · genérico) que determinan qué medidas ENS son prioritarias." />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando…
            </div>
          )}

          {notClassified && (
            <Alert>
              <AlertTitle>Sin clasificar</AlertTitle>
              <AlertDescription>
                Este proyecto aún no tiene arquetipo asignado. Usa el formulario
                abajo para clasificar.
              </AlertDescription>
            </Alert>
          )}

          {data && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Badge variant="default" className="text-base">
                  {ARQUETIPO_LABELS[data.archetype]}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  Confianza {(data.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-sm">{data.adjustments.notes}</p>
              {data.adjustments.highlight_marcos.length > 0 && (
                <div>
                  <Label>
                    Marcos destacados{" "}
                    <TooltipENS text="Las medidas del Anexo II ENS que más relevantes son para tu arquetipo · te toca priorizarlas en la implantación." />
                  </Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {data.adjustments.highlight_marcos.map((m) => (
                      <Badge key={m} variant="secondary">
                        {m}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {data.adjustments.skip_marcos.length > 0 && (
                <div>
                  <Label>
                    Marcos no aplicables{" "}
                    <TooltipENS text="Medidas del Anexo II que NO aplican según tu arquetipo · puedes excluirlas justificando en la DdA por qué no son relevantes." />
                  </Label>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {data.adjustments.skip_marcos.map((m) => (
                      <Badge key={m} variant="outline">
                        {m}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <details className="text-xs text-muted-foreground">
                <summary className="cursor-pointer">
                  Razonamiento ({data.reasoning_path.length} pasos)
                </summary>
                <ul className="list-disc pl-5 mt-1 space-y-0.5">
                  {data.reasoning_path.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ul>
              </details>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Reclasificar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="cnae">CNAE (4 dígitos)</Label>
              <Input
                id="cnae"
                value={form.cnae_code ?? ""}
                onChange={(e) =>
                  setForm({ ...form, cnae_code: e.target.value })
                }
                placeholder="86, 85, 64…"
              />
            </div>
            <div>
              <Label htmlFor="sector">Sector textual</Label>
              <Input
                id="sector"
                value={form.sector ?? ""}
                onChange={(e) => setForm({ ...form, sector: e.target.value })}
                placeholder="salud · educación · banca…"
              />
            </div>
            <div>
              <Label htmlFor="infra">Infrastructure type</Label>
              <Input
                id="infra"
                value={form.infrastructure_type ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    infrastructure_type: e.target
                      .value as ClassifyArchetypeRequest["infrastructure_type"],
                  })
                }
                placeholder="saas_only · on_prem · hybrid"
              />
            </div>
            <div>
              <Label htmlFor="workforce">Workforce type</Label>
              <Input
                id="workforce"
                value={form.workforce_type ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    workforce_type: e.target
                      .value as ClassifyArchetypeRequest["workforce_type"],
                  })
                }
                placeholder="fully_remote · hybrid · on_site"
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input
              id="aapp"
              type="checkbox"
              checked={form.is_aapp_developer ?? false}
              onChange={(e) =>
                setForm({ ...form, is_aapp_developer: e.target.checked })
              }
            />
            <Label htmlFor="aapp">
              Desarrollador AAPP{" "}
              <TooltipENS term="archetype_desarrollador_aapp" />
            </Label>
          </div>
          <Button
            onClick={() => mutation.mutate(form)}
            disabled={mutation.isPending}
          >
            {mutation.isPending && (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            )}
            Clasificar
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
