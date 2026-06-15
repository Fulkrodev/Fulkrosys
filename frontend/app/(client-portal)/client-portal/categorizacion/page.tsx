"use client";

/**
 * /client-portal/categorizacion · Sesión 3B-2B.8 CLUSTER 1 Phase 1A.
 *
 * Cliente READ-ONLY view de M01 categorización · sync admin → cliente:
 * - GET /api/v1/client-portal/categorizacion (audit_log emit on access)
 * - SSE subscribe `m01.categorizacion.completed` (admin completion event)
 * - Toast cliente friendly cuando admin actualiza categorización (R29)
 * - Display project.categoria_objetivo + per-system categorización summary
 *
 * Cliente NO edita · admin owns write (Marcos opera ENS prep · cliente VE).
 * R29 friendly tone · R30 inverso NO admin lingo (no DICAT exposed crudo).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  BadgeCheck,
  CalendarClock,
  Loader2,
  Sparkles,
  UserCheck,
} from "lucide-react";
import { useEffect } from "react";
import { toast } from "sonner";

import { PageContainer } from "@/components/layout/PageContainer";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import {
  CATEGORIA_LABEL,
  CATEGORIA_VARIANT,
  type ClientCategorizacionResponse,
  getClientCategorizacion,
} from "@/lib/api/client-categorizacion";

export default function ClientCategorizacionPage() {
  const queryClient = useQueryClient();
  const query = useQuery<ClientCategorizacionResponse>({
    queryKey: ["cliente", "categorizacion"],
    queryFn: getClientCategorizacion,
    staleTime: 30_000,
    retry: false,
  });

  // SSE subscribe m01.categorizacion.completed
  useClientProjectEvents(query.data?.project_id ?? null, {
    enabled: Boolean(query.data?.project_id),
    invalidateQueries: [["cliente", "categorizacion"]],
    onM01CategorizacionCompleted: (evt) => {
      const sistemaNombre = evt.data.system_nombre ?? "tu sistema";
      const categoria = evt.data.categoria_resultante ?? "—";
      toast.success(
        `El consultor ha completado la categorización de ${sistemaNombre} (categoría ${categoria}). Revísala más abajo cuando quieras.`,
      );
      queryClient.invalidateQueries({
        queryKey: ["cliente", "categorizacion"],
      });
    },
  });

  if (query.isLoading) {
    return (
      <PageContainer variant="reading">
        <div
          className="flex items-center gap-2 text-sm text-fulkro-ink-500"
          data-testid="cat-loading"
        >
          <Loader2 size={14} className="animate-spin" aria-hidden="true" />
          Cargando categorización…
        </div>
      </PageContainer>
    );
  }

  if (query.isError || !query.data) {
    return (
      <PageContainer variant="reading">
        <Alert variant="danger" data-testid="cat-error">
          <AlertCircle size={14} aria-hidden="true" />
          <AlertTitle>No se pudo cargar la categorización</AlertTitle>
          <AlertDescription>
            Reintenta más tarde o contacta con el consultor responsable.
          </AlertDescription>
        </Alert>
      </PageContainer>
    );
  }

  const data = query.data;
  const allCategorized = data.categorized_systems === data.total_systems && data.total_systems > 0;

  return (
    <PageContainer variant="reading">
      <div className="space-y-4" data-testid="cat-view">
      <header>
        <h1 className="text-2xl font-bold text-fulkro-ink-900">
          Categorización ENS
        </h1>
        <p className="text-sm text-fulkro-ink-500">
          {data.project_nombre}
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BadgeCheck
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Categoría del proyecto
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {data.categoria_objetivo ? (
            <div className="flex items-center gap-2">
              <Badge
                variant={
                  CATEGORIA_VARIANT[data.categoria_objetivo] ?? "secondary"
                }
                data-testid="cat-categoria-objetivo"
              >
                Categoría {CATEGORIA_LABEL[data.categoria_objetivo] ?? data.categoria_objetivo}
              </Badge>
              <span className="text-[12px] text-fulkro-ink-500">
                (categoría aplicable según el alcance del proyecto)
              </span>
            </div>
          ) : (
            <Alert>
              <Sparkles size={14} aria-hidden="true" />
              <AlertTitle>Categoría pendiente</AlertTitle>
              <AlertDescription>
                El consultor aún está determinando la categoría aplicable a
                este proyecto. Recibirás un aviso aquí cuando esté lista.
              </AlertDescription>
            </Alert>
          )}
          <p className="text-[12px] text-fulkro-ink-500">
            {data.categorized_systems} de {data.total_systems} sistema
            {data.total_systems !== 1 ? "s" : ""} categorizados
            {allCategorized && data.total_systems > 0 ? " · listo" : null}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sistemas del proyecto</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {data.systems.length === 0 ? (
            <Alert>
              <AlertTitle>Sin sistemas</AlertTitle>
              <AlertDescription>
                Aún no hay sistemas registrados en este proyecto.
              </AlertDescription>
            </Alert>
          ) : (
            data.systems.map((s) => (
              <div
                key={s.id}
                className="rounded-md border border-fulkro-ink-300/60 bg-white p-3"
                data-testid={`cat-system-${s.id}`}
              >
                <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-medium text-fulkro-ink-900">{s.nombre}</p>
                  {s.categoria_resultante ? (
                    <Badge
                      variant={
                        CATEGORIA_VARIANT[s.categoria_resultante] ?? "secondary"
                      }
                    >
                      {CATEGORIA_LABEL[s.categoria_resultante] ?? s.categoria_resultante}
                    </Badge>
                  ) : (
                    <Badge variant="outline">Pendiente</Badge>
                  )}
                </div>
                {s.descripcion ? (
                  <p className="text-[12px] text-fulkro-ink-700">
                    {s.descripcion}
                  </p>
                ) : null}
                {s.fecha_acta || s.aprobado_por ? (
                  <div className="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-fulkro-ink-500">
                    {s.fecha_acta ? (
                      <span className="inline-flex items-center gap-1">
                        <CalendarClock size={10} aria-hidden="true" />
                        {new Date(s.fecha_acta).toLocaleDateString()}
                      </span>
                    ) : null}
                    {s.aprobado_por ? (
                      <span className="inline-flex items-center gap-1">
                        <UserCheck size={10} aria-hidden="true" />
                        {s.aprobado_por}
                      </span>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Alert>
        <AlertTitle>Sin prisa por tu parte</AlertTitle>
        <AlertDescription>
          El consultor mantiene esta información actualizada en tiempo real. Si
          tienes dudas sobre la categoría asignada, puedes preguntar desde el
          chat sin presiones.
        </AlertDescription>
      </Alert>
      </div>
    </PageContainer>
  );
}
