"use client";

import * as React from "react";
import { ClipboardList, Mail, Plus, X } from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";

import {
  useCancelSession,
  useCreateSession,
  useMarkSessionSent,
  useProjectSessions,
} from "@/hooks/useOnboardingAdmin";
import type {
  CreateSessionBody,
  Role,
  Sector,
  SessionState,
  SessionSummary,
} from "@/lib/admin-onboarding/api";

export interface SessionsListProps {
  projectId: string;
}

const SECTORS: Sector[] = [
  "servicios_profesionales",
  "fintech",
  "sanidad_privada",
  "industria",
  "saas_tech",
  "retail_ecommerce",
  "energia",
  "logistica",
  "educacion_privada",
  "generico",
];

const ROLES: Role[] = [
  "sponsor",
  "ti_cto",
  "legal_dpo",
  "rrhh",
  "operaciones",
  "compras",
  "usuario_final",
];

const STATE_VARIANT: Record<string, "secondary" | "info" | "warning" | "success" | "danger"> = {
  created: "secondary",
  sent: "info",
  in_progress: "warning",
  completed: "success",
  expired: "danger",
  cancelled: "danger",
};

export function SessionsList({ projectId }: SessionsListProps) {
  const { data: sessions = [], isLoading } = useProjectSessions(projectId);
  const createMutation = useCreateSession(projectId);
  const cancelMutation = useCancelSession();
  const markSentMutation = useMarkSessionSent();

  const [createOpen, setCreateOpen] = React.useState(false);
  const [form, setForm] = React.useState<CreateSessionBody>({
    sector: "generico",
    role: "sponsor",
    interlocutor_email: "",
    interlocutor_name: "",
    ttl_hours: 168,
    language: "es",
  });

  const handleCreate = () => {
    if (!form.interlocutor_email) {
      toast.warning("Email del interlocutor requerido");
      return;
    }
    createMutation.mutate(form, {
      onSuccess: (res) => {
        toast.success(`Session creada · ${res.template_nombre}`);
        setCreateOpen(false);
      },
      onError: () => toast.error("Error creando session"),
    });
  };

  const columns: ColumnDef<SessionSummary>[] = [
    {
      accessorKey: "interlocutor_email",
      header: "Interlocutor",
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="font-medium">{row.original.interlocutor_name ?? "—"}</span>
          <span className="text-xs text-fulkro-ink-500">
            {row.original.interlocutor_email ?? "—"}
          </span>
        </div>
      ),
    },
    {
      accessorKey: "template_id",
      header: "Plantilla",
      cell: ({ row }) =>
        row.original.template_id ? (
          <span className="font-mono text-xs">{row.original.template_id}</span>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      accessorKey: "sector",
      header: "Sector / Rol",
      cell: ({ row }) => (
        <div className="flex flex-col gap-1">
          <Badge variant="secondary" className="w-fit">{row.original.sector ?? "—"}</Badge>
          <Badge variant="info" className="w-fit">{row.original.role ?? "—"}</Badge>
        </div>
      ),
    },
    {
      id: "progress",
      header: "Progreso",
      cell: ({ row }) => (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span>{row.original.answered_questions}/{row.original.total_questions}</span>
            <span className="font-mono">{row.original.progress_percentage.toFixed(0)}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded bg-fulkro-canvas">
            <div
              className="h-full bg-fulkro-primary-700"
              style={{ width: `${Math.min(100, row.original.progress_percentage)}%` }}
            />
          </div>
        </div>
      ),
    },
    {
      accessorKey: "state",
      header: "Estado",
      cell: ({ row }) => {
        const s = row.original.state ?? "created";
        return <Badge variant={STATE_VARIANT[s] ?? "outline"}>{s}</Badge>;
      },
    },
    {
      id: "acciones",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          {row.original.state === "created" ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                markSentMutation.mutate(row.original.id, {
                  onSuccess: () => toast.success("Marcada como enviada"),
                });
              }}
            >
              <Mail className="mr-1 size-3.5" />
              Enviada
            </Button>
          ) : null}
          {row.original.state !== "completed" && row.original.state !== "cancelled" ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                if (!confirm("¿Cancelar esta session?")) return;
                cancelMutation.mutate(
                  { sessionId: row.original.id, reason: "Manual cancel" },
                  { onSuccess: () => toast.success("Session cancelada") },
                );
              }}
            >
              <X className="size-3.5 text-destructive" />
            </Button>
          ) : null}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <ClipboardList size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Sessions onboarding
            <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
              ({sessions.length})
            </span>
          </h3>
        </div>
        <Button type="button" variant="primary" onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 size-4" />
          Crear session
        </Button>
      </div>

      <DataTable
        columns={columns}
        data={sessions}
        searchKey="interlocutor_email"
        searchPlaceholder="Buscar por email…"
        loading={isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <ClipboardList className="size-8" />
            <p className="text-sm">Sin sessions · crea la primera</p>
          </div>
        }
      />

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Crear onboarding session</DialogTitle>
            <DialogDescription>
              Selecciona sector y rol · plantilla cargada del catálogo.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs font-medium">Email interlocutor</label>
              <Input
                type="email"
                placeholder="cliente@ejemplo.es"
                value={form.interlocutor_email}
                onChange={(e) => setForm({ ...form, interlocutor_email: e.target.value })}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium">Nombre (opcional)</label>
              <Input
                placeholder="Nombre del interlocutor"
                value={form.interlocutor_name ?? ""}
                onChange={(e) => setForm({ ...form, interlocutor_name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs font-medium">Sector</label>
                <Select
                  value={form.sector}
                  onValueChange={(v) => setForm({ ...form, sector: v as Sector })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {SECTORS.map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium">Rol</label>
                <Select
                  value={form.role}
                  onValueChange={(v) => setForm({ ...form, role: v as Role })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {ROLES.map((r) => (
                      <SelectItem key={r} value={r}>{r}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? "Creando…" : "Crear"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
