"use client";

import * as React from "react";
import { BookOpen, GraduationCap, Plus, UserCheck } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import {
  useAssignCourse,
  useLMSCourses,
  useLMSProgress,
  useProjectLMSAssignments,
} from "@/hooks/useOnboardingAdmin";
import type {
  AssignCourseBody,
  LMSAssignmentAdmin,
  LMSCourse,
} from "@/lib/admin-onboarding/api";

export interface LMSPanelProps {
  projectId: string;
}

const ESTADO_VARIANT: Record<string, "secondary" | "info" | "warning" | "success" | "danger"> = {
  assigned: "secondary",
  in_progress: "info",
  completed: "success",
  failed: "danger",
  expired: "warning",
};

export function LMSPanel({ projectId }: LMSPanelProps) {
  const { data: courses = [], isLoading: coursesLoading } = useLMSCourses();
  const { data: assignments = [], isLoading: assignmentsLoading } =
    useProjectLMSAssignments(projectId);
  const { data: progress } = useLMSProgress(projectId);
  const assignMutation = useAssignCourse(projectId);

  const [assignOpen, setAssignOpen] = React.useState(false);
  const [form, setForm] = React.useState<AssignCourseBody>({
    course_codigo: "",
    asistente_nombre: "",
    asistente_email: "",
    asistente_cargo: "",
  });

  const handleAssign = () => {
    if (!form.course_codigo || !form.asistente_email || !form.asistente_nombre) {
      toast.warning("Completa curso · nombre · email");
      return;
    }
    assignMutation.mutate(form, {
      onSuccess: () => {
        toast.success("Curso asignado");
        setAssignOpen(false);
        setForm({
          course_codigo: "",
          asistente_nombre: "",
          asistente_email: "",
          asistente_cargo: "",
        });
      },
      onError: () => toast.error("Error asignando curso"),
    });
  };

  const courseColumns: ColumnDef<LMSCourse>[] = [
    {
      accessorKey: "codigo",
      header: "Código",
      cell: ({ row }) => (
        <span className="font-mono text-xs">{row.original.codigo}</span>
      ),
    },
    {
      accessorKey: "titulo",
      header: "Título",
    },
    {
      accessorKey: "duracion_minutos",
      header: "Duración",
      cell: ({ row }) => `${row.original.duracion_minutos} min`,
    },
    {
      id: "framework",
      header: "Framework",
      cell: ({ row }) =>
        row.original.framework ? (
          <Badge variant="info">{row.original.framework}</Badge>
        ) : (
          "—"
        ),
    },
    {
      id: "acciones",
      header: "Acciones",
      cell: ({ row }) => (
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            setForm({ ...form, course_codigo: row.original.codigo });
            setAssignOpen(true);
          }}
        >
          <Plus className="mr-1 size-3" />
          Asignar
        </Button>
      ),
    },
  ];

  const assignmentColumns: ColumnDef<LMSAssignmentAdmin>[] = [
    {
      accessorKey: "asistente_email",
      header: "Asistente",
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-medium">{row.original.asistente_nombre}</span>
          <span className="text-xs text-fulkro-ink-500">
            {row.original.asistente_email}
          </span>
        </div>
      ),
    },
    {
      accessorKey: "course_codigo",
      header: "Curso",
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-mono text-xs">{row.original.course_codigo}</span>
          <span className="text-xs text-fulkro-ink-500">
            {row.original.course_titulo}
          </span>
        </div>
      ),
    },
    {
      accessorKey: "estado",
      header: "Estado",
      cell: ({ row }) => (
        <Badge variant={ESTADO_VARIANT[row.original.estado] ?? "outline"}>
          {row.original.estado}
        </Badge>
      ),
    },
    {
      accessorKey: "quiz_score",
      header: "Quiz",
      cell: ({ row }) =>
        row.original.quiz_score !== null ? (
          <span className={row.original.quiz_pass ? "text-fulkro-success" : "text-fulkro-warning"}>
            {row.original.quiz_score.toFixed(1)}
          </span>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      accessorKey: "completado_at",
      header: "Completado",
      cell: ({ row }) =>
        row.original.completado_at
          ? new Date(row.original.completado_at).toLocaleDateString("es-ES")
          : "—",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <GraduationCap size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">LMS · capacitación</h3>
          <TooltipENS term="lms_assignment" />
        </div>
        {progress ? (
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <Badge variant="secondary">{progress.total_assignments} totales</Badge>
            <Badge variant="info">{progress.por_estado.in_progress ?? 0} en curso</Badge>
            <Badge variant="success">{progress.por_estado.completed ?? 0} completados</Badge>
          </div>
        ) : null}
      </div>

      <Tabs defaultValue="courses">
        <TabsList>
          <TabsTrigger value="courses">
            <BookOpen className="mr-1 size-3.5" /> Cursos
          </TabsTrigger>
          <TabsTrigger value="assignments">
            <UserCheck className="mr-1 size-3.5" /> Asignaciones
          </TabsTrigger>
        </TabsList>

        <TabsContent value="courses" className="mt-4">
          <DataTable
            columns={courseColumns}
            data={courses}
            searchKey="titulo"
            searchPlaceholder="Buscar cursos…"
            loading={coursesLoading}
            emptyState={
              <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
                <BookOpen className="size-8" />
                <p className="text-sm">Sin cursos disponibles</p>
              </div>
            }
          />
        </TabsContent>

        <TabsContent value="assignments" className="mt-4">
          <DataTable
            columns={assignmentColumns}
            data={assignments}
            searchKey="asistente_email"
            searchPlaceholder="Buscar por email…"
            loading={assignmentsLoading}
            emptyState={
              <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
                <UserCheck className="size-8" />
                <p className="text-sm">Sin asignaciones · ve a Cursos para asignar</p>
              </div>
            }
          />
        </TabsContent>
      </Tabs>

      <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Asignar curso a empleado</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium">Curso</label>
              <Select
                value={form.course_codigo}
                onValueChange={(v) => setForm({ ...form, course_codigo: v })}
              >
                <SelectTrigger><SelectValue placeholder="Selecciona curso…" /></SelectTrigger>
                <SelectContent>
                  {courses.map((c) => (
                    <SelectItem key={c.codigo} value={c.codigo}>
                      {c.codigo} · {c.titulo}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Nombre del empleado</label>
              <Input
                value={form.asistente_nombre}
                onChange={(e) => setForm({ ...form, asistente_nombre: e.target.value })}
                placeholder="Juan García"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Email</label>
              <Input
                type="email"
                value={form.asistente_email}
                onChange={(e) => setForm({ ...form, asistente_email: e.target.value })}
                placeholder="juan@empresa.es"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Cargo (opcional)</label>
              <Input
                value={form.asistente_cargo ?? ""}
                onChange={(e) => setForm({ ...form, asistente_cargo: e.target.value })}
                placeholder="Responsable de TI"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={handleAssign}
              disabled={assignMutation.isPending}
            >
              {assignMutation.isPending ? "Asignando…" : "Asignar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
