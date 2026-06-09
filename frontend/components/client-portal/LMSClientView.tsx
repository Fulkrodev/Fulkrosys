"use client";

import * as React from "react";
import {
  Award,
  BookOpen,
  CheckCircle2,
  GraduationCap,
  PlayCircle,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  useCompleteLMS,
  usePortalLMS,
} from "@/hooks/useOnboardingClient";
import type { PortalLMSAssignment } from "@/lib/client-onboarding/api";

export interface LMSClientViewProps {
  projectId: string;
}

const ESTADO_VARIANT: Record<string, "secondary" | "info" | "success" | "danger"> = {
  assigned: "secondary",
  in_progress: "info",
  completed: "success",
  failed: "danger",
  expired: "danger",
};

const ESTADO_LABEL: Record<string, string> = {
  assigned: "Pendiente",
  in_progress: "En curso",
  completed: "Completado",
  failed: "No superado",
  expired: "Expirado",
};

export function LMSClientView({ projectId }: LMSClientViewProps) {
  const { data, isLoading } = usePortalLMS(projectId);
  const completeMutation = useCompleteLMS(projectId);

  const assignments = data?.assignments ?? [];

  const handleComplete = (assignment: PortalLMSAssignment) => {
    completeMutation.mutate(assignment.id, {
      onSuccess: () => toast.success(`Curso "${assignment.course_titulo}" completado`),
      onError: () => toast.error("Error marcando completado"),
    });
  };

  if (isLoading) {
    return <p className="text-sm text-fulkro-ink-500">Cargando cursos asignados…</p>;
  }

  if (assignments.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <GraduationCap className="size-5 text-fulkro-primary-700" />
            Cursos asignados
          </CardTitle>
          <CardDescription>
            Marcos te asignará cursos de concienciación cuando aplique. Puedes ver el catálogo abajo.
          </CardDescription>
        </CardHeader>
        {data?.courses_available && data.courses_available.length > 0 ? (
          <CardContent>
            <p className="mb-2 text-xs font-medium text-fulkro-ink-700">
              Catálogo disponible ({data.courses_available.length})
            </p>
            <div className="space-y-1">
              {data.courses_available.map((c) => (
                <div
                  key={c.codigo}
                  className="flex items-center justify-between rounded border border-fulkro-ink-100 p-2 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <BookOpen size={12} className="text-fulkro-ink-500" />
                    <span className="font-mono">{c.codigo}</span>
                    <span>{c.titulo}</span>
                  </div>
                  <span className="text-fulkro-ink-500">{c.duracion_minutos} min</span>
                </div>
              ))}
            </div>
          </CardContent>
        ) : null}
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <GraduationCap size={18} className="text-fulkro-primary-700" />
        <h3 className="text-base font-semibold">
          Cursos asignados
          <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
            ({assignments.length})
          </span>
        </h3>
        <TooltipENS term="lms_assignment" />
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {assignments.map((a) => {
          const isCompleted = a.estado === "completed";
          return (
            <Card key={a.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-sm">{a.course_titulo}</CardTitle>
                  <Badge variant={ESTADO_VARIANT[a.estado] ?? "outline"}>
                    {ESTADO_LABEL[a.estado] ?? a.estado}
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  Asignado a <span className="font-medium">{a.asistente_nombre}</span>{" "}
                  ({a.asistente_email})
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                <div className="flex flex-wrap items-center gap-2 text-fulkro-ink-500">
                  <span className="font-mono">{a.course_codigo}</span>
                  {a.asignado_at ? (
                    <span>
                      asignado:{" "}
                      {new Date(a.asignado_at).toLocaleDateString("es-ES")}
                    </span>
                  ) : null}
                  {a.completado_at ? (
                    <span className="text-fulkro-success">
                      completado:{" "}
                      {new Date(a.completado_at).toLocaleDateString("es-ES")}
                    </span>
                  ) : null}
                </div>
                {a.quiz_score !== null ? (
                  <div className="flex items-center gap-2">
                    <Award size={12} className="text-fulkro-info" />
                    <span>Quiz: {a.quiz_score.toFixed(1)}</span>
                    {a.quiz_pass ? (
                      <Badge variant="success">aprobado</Badge>
                    ) : (
                      <Badge variant="danger">no superado</Badge>
                    )}
                  </div>
                ) : null}
                {!isCompleted ? (
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => handleComplete(a)}
                    disabled={completeMutation.isPending}
                    className="w-full"
                  >
                    {a.estado === "assigned" ? (
                      <>
                        <PlayCircle className="mr-1 size-3.5" />
                        Marcar como completado
                      </>
                    ) : (
                      <>
                        <CheckCircle2 className="mr-1 size-3.5" />
                        Marcar como completado
                      </>
                    )}
                  </Button>
                ) : (
                  <div className="flex items-center justify-center gap-2 rounded bg-fulkro-success/10 p-2 text-xs text-fulkro-success">
                    <CheckCircle2 className="size-3.5" />
                    Curso completado · evidencia generada
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
