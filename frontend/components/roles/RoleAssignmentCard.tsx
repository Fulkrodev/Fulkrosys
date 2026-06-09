"use client";

/**
 * RoleAssignmentCard · per rol en grid (SAN-E v3.MB-3.5).
 *
 * Card visual con header rol + body contact (si assigned) o empty state ·
 * DropdownMenu 3 acciones + alert ENS si rol required vacante.
 */
import * as React from "react";
import {
  AlertTriangle,
  Loader2,
  Mail,
  MoreVertical,
  Phone,
  ShieldCheck,
  UserPlus,
  UserX,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useRoleTopology } from "@/hooks/useRoleTopology";
import {
  type RoleAssignment,
  type RoleMeta,
  ROLE_LABELS,
} from "@/lib/admin-roles/api";
import type { GlossaryKey } from "@/lib/glosario-ens";

const ROLE_TERM_KEY: Partial<Record<string, GlossaryKey>> = {
  sponsor: "rol_sponsor",
  responsable_informacion: "rol_RI",
  responsable_servicio: "rol_RS",
  responsable_seguridad: "rol_RSEG",
  responsable_sistema: "rol_RSIS",
};

const ROLE_BADGE_VARIANT: Record<
  RoleMeta["short"],
  "info" | "accent" | "danger" | "warning" | "success" | "secondary"
> = {
  Sponsor: "success",
  RI: "info",
  RS: "accent",
  RSEG: "danger",
  RSIS: "warning",
  DPO: "info",
  CISO: "accent",
  Auditor: "secondary",
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return (parts[0]?.[0] ?? "?").toUpperCase() + (parts[1]?.[0] ?? "").toUpperCase();
}

function relativeDate(s: string | null): string {
  if (!s) return "—";
  const days = Math.floor((Date.now() - new Date(s).getTime()) / 86400000);
  if (days < 1) return "Hoy";
  if (days < 7) return `Hace ${days}d`;
  if (days < 30) return `Hace ${Math.floor(days / 7)}sem`;
  return `Hace ${Math.floor(days / 30)}m`;
}

interface RoleAssignmentCardProps {
  projectId: string;
  assignment: RoleAssignment;
  onAssignClick: (assignment: RoleAssignment) => void;
  isCrossCompliance?: boolean;
}

export function RoleAssignmentCard({
  projectId,
  assignment,
  onAssignClick,
  isCrossCompliance,
}: RoleAssignmentCardProps) {
  const rt = useRoleTopology(projectId);
  const meta = ROLE_LABELS[assignment.role_code];
  const termKey = ROLE_TERM_KEY[assignment.role_code];
  const variant = meta ? ROLE_BADGE_VARIANT[meta.short] ?? "secondary" : "secondary";
  const isAssigned = Boolean(assignment.contact);
  const [confirmVacate, setConfirmVacate] = React.useState(false);

  const onVacate = async () => {
    try {
      await rt.vacateRole.mutateAsync(assignment.role_code);
      toast.success(`Rol ${meta?.short ?? assignment.role_code} vacado`);
      setConfirmVacate(false);
    } catch {
      toast.error("Error al vacar rol");
    }
  };

  return (
    <>
      <Card className="flex h-full flex-col">
        <CardContent className="flex flex-1 flex-col gap-3 pt-5">
          {/* Header */}
          <div className="flex items-start gap-2">
            <Badge variant={variant} className="shrink-0">
              {meta?.short ?? assignment.role_code}
            </Badge>
            <div className="flex flex-1 flex-col gap-0.5">
              <h3 className="flex items-center gap-1 text-sm font-bold text-[color:var(--fulkro-title)]">
                {meta?.label ?? assignment.role_code}
                {termKey ? (
                  <TooltipENS term={termKey} iconSize={12} />
                ) : (
                  <TooltipENS
                    text={meta?.description ?? "Rol cross-compliance · framework no ENS oficial."}
                    iconSize={12}
                  />
                )}
              </h3>
              <p className="text-xs text-fulkro-ink-500">
                {meta?.description ?? ""}
              </p>
            </div>
            {isAssigned ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <MoreVertical size={14} strokeWidth={2.4} />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onAssignClick(assignment)}>
                    <UserPlus size={14} strokeWidth={2.4} className="mr-2" />
                    Cambiar asignación
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-fulkro-danger"
                    onClick={() => setConfirmVacate(true)}
                  >
                    <UserX size={14} strokeWidth={2.4} className="mr-2" />
                    Vacar rol
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : null}
          </div>

          {/* Body */}
          {isAssigned && assignment.contact ? (
            <div className="flex flex-col gap-2 rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50 p-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-fulkro-primary-700 text-xs font-bold text-white">
                  {initials(assignment.contact.full_name)}
                </div>
                <div className="flex flex-1 flex-col gap-0.5">
                  <p className="text-sm font-bold text-[color:var(--fulkro-title)]">
                    {assignment.contact.full_name}
                  </p>
                  <p className="text-xs text-fulkro-ink-500">
                    {assignment.contact.role_title}
                  </p>
                </div>
                {assignment.contact.has_portal_access ? (
                  <Badge variant="info" className="text-[10px]">
                    <ShieldCheck size={10} strokeWidth={2.4} className="mr-1" />
                    Portal
                  </Badge>
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <a
                  href={`mailto:${assignment.contact.email}`}
                  className="inline-flex items-center gap-1 text-fulkro-info hover:underline"
                >
                  <Mail size={11} strokeWidth={2.4} />
                  {assignment.contact.email}
                </a>
                {assignment.contact.phone ? (
                  <a
                    href={`tel:${assignment.contact.phone}`}
                    className="inline-flex items-center gap-1 text-fulkro-ink-500 hover:underline"
                  >
                    <Phone size={11} strokeWidth={2.4} />
                    {assignment.contact.phone}
                  </a>
                ) : null}
              </div>
              <p className="text-[10px] text-fulkro-ink-600">
                Asignado {relativeDate(assignment.assigned_at)}
                {assignment.assigned_by ? ` · ${assignment.assigned_by}` : ""}
              </p>
              {assignment.notes ? (
                <p className="rounded-md bg-white p-2 text-xs text-fulkro-ink-700">
                  {assignment.notes}
                </p>
              ) : null}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-fulkro-ink-200 bg-white p-4 text-center">
              <UserPlus
                size={20}
                strokeWidth={2.4}
                className="text-fulkro-ink-600"
              />
              <p className="text-xs font-medium text-fulkro-ink-500">
                Rol sin asignar
              </p>
              {assignment.is_required ? (
                <p className="flex items-center gap-1 text-[10px] text-fulkro-warning">
                  <AlertTriangle size={10} strokeWidth={2.4} />
                  Rol obligatorio ENS · bloquea certificación
                </p>
              ) : null}
              <Button
                variant="primary"
                size="sm"
                className="mt-1"
                onClick={() => onAssignClick(assignment)}
              >
                Asignar contacto
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Confirm vacate */}
      <Dialog open={confirmVacate} onOpenChange={setConfirmVacate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Vacar rol {meta?.short ?? assignment.role_code}
            </DialogTitle>
            <DialogDescription>
              {assignment.contact
                ? `Se desasignará a ${assignment.contact.full_name} de este rol. El contacto sigue existiendo en la lista del proyecto.`
                : ""}
              {assignment.is_required && !isCrossCompliance
                ? " Recuerda que es un rol obligatorio ENS."
                : ""}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmVacate(false)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={() => void onVacate()}
              disabled={rt.vacateRole.isPending}
            >
              {rt.vacateRole.isPending ? (
                <Loader2 size={14} className="animate-spin" strokeWidth={2.4} />
              ) : null}
              Vacar rol
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
