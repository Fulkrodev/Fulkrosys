"use client";

/**
 * ClientTasksList · REFACTOR sub-atom 1.D.F.bis.III.C v3.11 · indispensable-only.
 *
 * Categorías "lo que TÚ haces" prominent (NO solo status filter genérico):
 *   - 🔥 PRIORIDAD: Firmas pendientes (DdA · Conformidad · MAGERIT · DPC)
 *   - 🟡 IMPLEMENTACIÓN: Acciones M04 plan adecuación marcar implementadas
 *   - 📤 EVIDENCIAS: Documentos solicitados subir
 *   - 🎓 FORMACIÓN: Cursos LMS asignados empleados
 *   - 🛡️ AUTORIZACIONES: Pentest autorización pre-ejecución
 *   - 📝 INFO REQUESTED: Marcos pidió info adicional
 *
 * Status filters secundario (todas/pendientes/curso/bloqueadas/completadas).
 * Empty state celebratory R29: "✨ Marcos está trabajando · sin tareas tuyas pendientes".
 *
 * Categorías son derivadas client-side desde task.template_id + cta_url patterns
 * (NO new backend endpoint · backward compat sostener · OPS-045 26ª aplicación).
 */
import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  Edit3,
  FileSignature,
  GraduationCap,
  Loader2,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { useMemo, useState } from "react";

import { ClientTaskCard } from "@/components/client-portal/ClientTaskCard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ClientTask,
  ClientTaskStatus,
  clientTasksApi,
} from "@/lib/api/client-portal-tasks";

type StatusFilter = "all" | ClientTaskStatus;

const STATUS_FILTERS: { key: StatusFilter; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "pending", label: "Pendientes" },
  { key: "in_progress", label: "En curso" },
  { key: "blocked", label: "Bloqueadas" },
  { key: "done", label: "Completadas" },
];

// Categorías indispensable-only (heuristic per template_id + cta_url patterns)
type TaskCategory =
  | "firmas"
  | "implementacion"
  | "evidencias"
  | "formacion"
  | "autorizaciones"
  | "info"
  | "otros";

interface CategoryDef {
  key: TaskCategory;
  label: string;
  icon: React.ReactNode;
  description: string;
}

const CATEGORIES: CategoryDef[] = [
  {
    key: "firmas",
    label: "🔥 Firmas pendientes",
    icon: <FileSignature className="size-4" />,
    description: "Documentos preparados por Marcos que necesitan tu firma",
  },
  {
    key: "implementacion",
    label: "🟡 Implementación",
    icon: <CheckCircle2 className="size-4" />,
    description: "Acciones del plan de adecuación · marca cuando estén hechas",
  },
  {
    key: "evidencias",
    label: "📤 Subir documentos",
    icon: <Upload className="size-4" />,
    description: "Documentos solicitados por Marcos · sube cuando los tengas",
  },
  {
    key: "formacion",
    label: "🎓 Formación",
    icon: <GraduationCap className="size-4" />,
    description: "Cursos LMS asignados a tu equipo",
  },
  {
    key: "autorizaciones",
    label: "🛡️ Autorizaciones",
    icon: <ShieldCheck className="size-4" />,
    description: "Pentest u otras autorizaciones pre-ejecución",
  },
  {
    key: "info",
    label: "📝 Info solicitada",
    icon: <Edit3 className="size-4" />,
    description: "Marcos te pidió información adicional",
  },
];

/**
 * Categoriza task per template_id + cta_url heuristic.
 * NO modifica backend · derivación client-side.
 */
function categorize(task: ClientTask): TaskCategory {
  const templ = task.template_id?.toLowerCase() ?? "";
  const cta = (task.cta_url ?? "").toLowerCase();
  const expected = (task.expected_evidence_type ?? "").toLowerCase();

  // Firmas keywords
  if (
    cta.includes("firmas-hub") ||
    cta.includes("/conformidad") ||
    cta.includes("/dpc-anual") ||
    cta.includes("/policies") ||
    cta.includes("/dda") ||
    cta.includes("/magerit") ||
    cta.includes("/pentest-authorization") ||
    templ.includes("sign") ||
    templ.includes("firma")
  ) {
    if (cta.includes("/pentest-authorization") || templ.includes("pentest_auth")) {
      return "autorizaciones";
    }
    return "firmas";
  }
  // Pentest authorizations
  if (templ.includes("pentest") || cta.includes("pentest")) return "autorizaciones";
  // Formación / LMS
  if (
    templ.includes("lms") ||
    templ.includes("formacion") ||
    templ.includes("g1") ||
    templ.includes("g2") ||
    cta.includes("/onboarding") ||
    expected.includes("lms")
  ) {
    return "formacion";
  }
  // Evidencias upload
  if (
    cta.includes("/evidencias") ||
    cta.includes("/files") ||
    templ.includes("evidence") ||
    templ.includes("upload") ||
    (task.expected_evidence_count > 0 && !cta)
  ) {
    return "evidencias";
  }
  // Implementación plan
  if (
    templ.includes("implement") ||
    templ.includes("medida") ||
    templ.includes("m04") ||
    templ.includes("gap")
  ) {
    return "implementacion";
  }
  // Info request
  if (
    templ.includes("info") ||
    templ.includes("pregunta") ||
    templ.includes("aporta")
  ) {
    return "info";
  }
  return "otros";
}

export function ClientTasksList() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState<TaskCategory | "all">(
    "all",
  );

  const { data: allTasks = [], isLoading } = useQuery<ClientTask[]>({
    queryKey: ["client-tasks", statusFilter],
    queryFn: () =>
      clientTasksApi.list(statusFilter === "all" ? undefined : statusFilter),
    staleTime: 15_000,
  });

  // Categoriza + counts per categoría
  const { categorized, counts } = useMemo(() => {
    const map: Record<TaskCategory, ClientTask[]> = {
      firmas: [],
      implementacion: [],
      evidencias: [],
      formacion: [],
      autorizaciones: [],
      info: [],
      otros: [],
    };
    for (const t of allTasks) {
      const cat = categorize(t);
      map[cat].push(t);
    }
    const c: Record<TaskCategory | "all", number> = {
      all: allTasks.length,
      firmas: map.firmas.length,
      implementacion: map.implementacion.length,
      evidencias: map.evidencias.length,
      formacion: map.formacion.length,
      autorizaciones: map.autorizaciones.length,
      info: map.info.length,
      otros: map.otros.length,
    };
    return { categorized: map, counts: c };
  }, [allTasks]);

  const filteredTasks = useMemo(() => {
    if (categoryFilter === "all") return allTasks;
    return categorized[categoryFilter] ?? [];
  }, [categoryFilter, categorized, allTasks]);

  // Foco: tasks indispensable cliente (NO done · NO admin internal)
  const indispensablePending = allTasks.filter(
    (t) => t.status !== "done",
  ).length;

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando tus tareas…
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4" data-testid="cliente-tasks-list">
      {/* Header con counts indispensable */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-lg">
            <span>Mis tareas</span>
            {indispensablePending === 0 ? (
              <Badge variant="success" className="text-xs">
                ✨ Todo al día
              </Badge>
            ) : (
              <Badge variant="warning" className="text-xs">
                {indispensablePending} pendientes
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-foreground/70">
            Aquí ves todo lo que Marcos necesita de ti. Filtra por tipo abajo o
            por estado.
          </p>

          {/* Categorías indispensable buttons · prominent */}
          <div className="flex flex-wrap gap-1.5">
            <Button
              size="sm"
              variant={categoryFilter === "all" ? "primary" : "outline"}
              onClick={() => setCategoryFilter("all")}
              data-testid="cliente-cat-filter-all"
            >
              Todas ({counts.all})
            </Button>
            {CATEGORIES.map((c) => {
              const count = counts[c.key];
              if (count === 0 && categoryFilter !== c.key) return null;
              return (
                <Button
                  key={c.key}
                  size="sm"
                  variant={categoryFilter === c.key ? "primary" : "outline"}
                  onClick={() => setCategoryFilter(c.key)}
                  data-testid={`cliente-cat-filter-${c.key}`}
                  title={c.description}
                >
                  {c.label} ({count})
                </Button>
              );
            })}
          </div>

          {/* Status filters · secundario */}
          <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t">
            <span className="text-[10px] uppercase tracking-wide text-foreground/70">
              Estado:
            </span>
            {STATUS_FILTERS.map((f) => (
              <Button
                key={f.key}
                size="sm"
                variant={statusFilter === f.key ? "primary" : "outline"}
                onClick={() => setStatusFilter(f.key)}
                data-testid={`cliente-status-filter-${f.key}`}
                className="text-xs"
              >
                {f.label}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {filteredTasks.length === 0 ? (
        <Card>
          <CardContent
            className="py-10 text-center space-y-2"
            data-testid="cliente-tasks-empty"
          >
            <p className="text-3xl">✨</p>
            <p className="text-base font-medium">Sin tareas pendientes</p>
            <p className="text-sm text-foreground/70 max-w-md mx-auto">
              {categoryFilter === "all" && statusFilter === "all"
                ? "Marcos está trabajando · sin acciones pendientes tuyas ahora mismo. Te avisaremos cuando necesite algo."
                : "No hay tareas en este filtro · prueba a quitar filtros o espera a que tu consultor te asigne más trabajo."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-3">
          {filteredTasks.map((task) => (
            <li key={task.id}>
              <ClientTaskCard task={task} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
