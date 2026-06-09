"use client";

/**
 * RenewalWarRoom real · M27 + M28 wired (SAN-E v3.MB-3.4).
 *
 * Sustituye stub `EmptyStateUpcoming` con UI completa cableada al backend
 * M27 renewal extensions (commit MB-3.D 4a17834) + M28 drift summary
 * (commit MB-3.E 6daaae2).
 *
 * 4 secciones:
 * A. Hero countdown · audit_window_due + auditor info + status overall
 * B. DriftMatrix 10×4 (sub-component)
 * C. RenewalTimeline 8 milestones (sub-component)
 * D. Action panel · 4 cards (preparación · contactar auditor · dossier · pentest)
 */
import * as React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  Mail,
  Play,
  ShieldAlert,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { TooltipENS } from "@/components/ui/tooltip-ens";

import { useRenewalStatus } from "@/hooks/useRenewalStatus";

import { DriftMatrix } from "./DriftMatrix";
import { RenewalTimeline } from "./RenewalTimeline";

const auditorSchema = z.object({
  auditor_name: z.string().min(2, "Nombre auditor requerido (mín. 2)"),
  auditor_email: z.string().email("Email inválido"),
  audit_entity: z.string().max(255).optional().or(z.literal("")),
  message: z.string().min(10, "Mensaje mín. 10 caracteres").max(2000),
});

type AuditorFormData = z.infer<typeof auditorSchema>;

function daysUntil(iso: string | null): number | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - Date.now();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

interface ContactAuditorDialogProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function ContactAuditorDialog({
  projectId,
  open,
  onOpenChange,
}: ContactAuditorDialogProps) {
  const { contactAuditor } = useRenewalStatus(projectId);
  const form = useForm<AuditorFormData>({
    resolver: zodResolver(auditorSchema),
    defaultValues: {
      auditor_name: "",
      auditor_email: "",
      audit_entity: "",
      message:
        "Solicito briefing inicial para preparar la auditoría de recertificación bienal ENS.",
    },
  });

  const onSubmit = async (values: AuditorFormData) => {
    try {
      await contactAuditor.mutateAsync({
        auditor_name: values.auditor_name,
        auditor_email: values.auditor_email,
        audit_entity: values.audit_entity?.trim() || null,
        message: values.message,
      });
      toast.success(`Auditor ${values.auditor_name} contactado`);
      form.reset();
      onOpenChange(false);
    } catch {
      toast.error("Error al contactar auditor");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-[color:var(--fulkro-title)]">
            Contactar auditor{" "}
            <TooltipENS
              text="Auditor ENAC habilitado para certificar tu sistema en ENS. Le enviamos un briefing y le pasamos un magic link de un solo uso para revisar tu dossier."
              iconSize={13}
            />
          </DialogTitle>
          <DialogDescription>
            Envía un briefing inicial al auditor ENAC. Se generará un magic
            link <code className="font-mono text-[11px]">ml_AUDITOR_ENAC_REVIEW</code>{" "}
            (cableado en MB-7).
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-3"
        >
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="auditor-name">Nombre auditor</Label>
            <Input id="auditor-name" {...form.register("auditor_name")} />
            {form.formState.errors.auditor_name ? (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.auditor_name.message}
              </p>
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="auditor-email">Email</Label>
            <Input
              id="auditor-email"
              type="email"
              {...form.register("auditor_email")}
            />
            {form.formState.errors.auditor_email ? (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.auditor_email.message}
              </p>
            ) : null}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="auditor-entity">Entidad auditora (opcional)</Label>
            <Input
              id="auditor-entity"
              {...form.register("audit_entity")}
              placeholder="ENAC-AC-XXXXX"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="auditor-message">Mensaje</Label>
            <Textarea
              id="auditor-message"
              rows={4}
              {...form.register("message")}
            />
            {form.formState.errors.message ? (
              <p className="text-xs text-fulkro-danger">
                {form.formState.errors.message.message}
              </p>
            ) : null}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={contactAuditor.isPending}
            >
              {contactAuditor.isPending ? (
                <Loader2
                  size={14}
                  className="animate-spin"
                  strokeWidth={2.4}
                />
              ) : null}
              Enviar briefing
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface ActionCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  cta: string;
  onClick: () => void;
  disabled?: boolean;
  tooltipText?: string;
  variant?: "primary" | "outline";
}

function ActionCard({
  icon,
  title,
  description,
  cta,
  onClick,
  disabled,
  tooltipText,
  variant = "outline",
}: ActionCardProps) {
  return (
    <Card>
      <CardContent className="flex h-full flex-col gap-3 pt-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-fulkro-ink-50 text-fulkro-ink-700">
          {icon}
        </div>
        <div className="flex flex-1 flex-col gap-1">
          <h3 className="flex items-center gap-1.5 text-sm font-bold text-[color:var(--fulkro-title)]">
            {title}
            {tooltipText ? (
              <TooltipENS text={tooltipText} iconSize={12} />
            ) : null}
          </h3>
          <p className="text-xs text-fulkro-ink-500">{description}</p>
        </div>
        <Button
          variant={variant}
          onClick={onClick}
          disabled={disabled}
          size="sm"
          className="w-fit"
        >
          {cta}
        </Button>
      </CardContent>
    </Card>
  );
}

export function RenewalWarRoom({ projectId }: { projectId: string }) {
  const status = useRenewalStatus(projectId);
  const [contactOpen, setContactOpen] = React.useState(false);

  if (status.timeline.isLoading || status.auditor.isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
        <Skeleton className="h-32" />
        <Skeleton className="h-64" />
        <Skeleton className="h-32" />
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  const auditor = status.auditor.data;
  const days = daysUntil(auditor?.audit_window_due ?? null);
  const totalOpenDrift = status.drift.data?.open_total ?? 0;

  // Status global derivado: BÁSICA derivation simplificado
  // CRITICAL si days_until < 30 + drift critico open · WARNING si days_until < 60 ·
  // ON_TRACK resto.
  const criticalDrift = status.drift.data?.open_by_severity?.CRITICA ?? 0;
  let overallStatus: "ON_TRACK" | "WARNING" | "BEHIND" | "CRITICAL" = "ON_TRACK";
  if (days !== null) {
    if (days < 30 && criticalDrift > 0) overallStatus = "CRITICAL";
    else if (days < 30) overallStatus = "BEHIND";
    else if (days < 60) overallStatus = "WARNING";
  }

  const statusBadge = {
    ON_TRACK: { variant: "success" as const, label: "ON TRACK", Icon: ShieldCheck },
    WARNING: { variant: "warning" as const, label: "ATENCIÓN", Icon: Clock },
    BEHIND: { variant: "warning" as const, label: "RETRASADO", Icon: AlertTriangle },
    CRITICAL: { variant: "danger" as const, label: "CRÍTICO", Icon: ShieldAlert },
  }[overallStatus];

  const StatusIcon = statusBadge.Icon;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-8">
      {/* A · Hero countdown */}
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-md bg-fulkro-info/10 text-fulkro-info">
              <CalendarClock size={26} strokeWidth={2.4} />
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-xs uppercase tracking-wide text-fulkro-ink-600">
                Próxima auditoría{" "}
                <TooltipENS
                  text="Recertificación bienal ENS: cada 2 años renueva tu conformidad. En MEDIA/ALTA con auditor ENAC externo · en BÁSICA con autoevaluación CCN-STIC 809."
                  iconSize={11}
                />
              </span>
              {days !== null ? (
                <>
                  <span className="text-3xl font-bold text-[color:var(--fulkro-title)]">
                    {days >= 0 ? days : 0} días
                  </span>
                  <span className="text-xs text-fulkro-ink-500">
                    {auditor?.audit_window_due
                      ? `Ventana ${new Date(auditor.audit_window_due).toLocaleDateString("es-ES")}`
                      : ""}
                  </span>
                </>
              ) : (
                <span className="text-sm text-fulkro-ink-500">
                  Sin campaña de renovación activa.
                </span>
              )}
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <Badge
              variant={statusBadge.variant}
              className="gap-1 px-3 py-1 text-sm font-semibold"
            >
              <StatusIcon size={14} strokeWidth={2.4} />
              {statusBadge.label}
            </Badge>
            {auditor?.auditor_contacted ? (
              <Badge variant="success" className="gap-1">
                <CheckCircle2 size={11} strokeWidth={2.4} />
                Auditor contactado
                {auditor.auditor_contacted_at
                  ? ` ${new Date(auditor.auditor_contacted_at).toLocaleDateString("es-ES")}`
                  : ""}
              </Badge>
            ) : (
              <Badge variant="outline">Auditor sin contactar</Badge>
            )}
            <span className="text-[10px] text-fulkro-ink-600">
              {totalOpenDrift} drifts abiertos
            </span>
          </div>
        </CardContent>

        {overallStatus === "CRITICAL" ? (
          <div className="mx-6 mb-4 flex items-center gap-2 rounded-md border border-fulkro-danger/30 bg-fulkro-danger/5 p-3 text-sm text-fulkro-danger">
            <ShieldAlert size={16} strokeWidth={2.4} />
            <span className="font-bold">Acción inmediata requerida</span>
            <span className="text-xs">
              · Drift crítico abierto + {days ?? 0} días para auditoría.
            </span>
          </div>
        ) : null}
      </Card>

      {/* B · DriftMatrix */}
      <DriftMatrix projectId={projectId} />

      {/* C · RenewalTimeline */}
      <RenewalTimeline projectId={projectId} />

      {/* D · Action panel */}
      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-bold text-[color:var(--fulkro-title)]">
          Acciones disponibles
        </h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          <ActionCard
            icon={<Play size={18} strokeWidth={2.4} />}
            title="Iniciar preparación"
            description="Marca el primer hito (prep) como en curso y activa la timeline de renovación."
            cta="Iniciar"
            disabled={overallStatus === "CRITICAL"}
            variant="primary"
            onClick={() => {
              toast.info(
                "Preparación · cableado MB-7 (mark milestone prep en_progreso)",
              );
            }}
          />
          <ActionCard
            icon={<Mail size={18} strokeWidth={2.4} />}
            title="Contactar auditor ENAC"
            description="Envía briefing al auditor + magic link revisión dossier."
            cta="Contactar"
            tooltipText="ENAC: la entidad española que acredita los auditores oficiales para certificación ENS."
            onClick={() => setContactOpen(true)}
          />
          <ActionCard
            icon={<FileText size={18} strokeWidth={2.4} />}
            title="Generar dossier"
            description="Bundle PDF con DdA + evidencia + drift summary para revisión auditor."
            cta="Generar"
            tooltipText="Bundle ENAC-ready: Declaración de Aplicabilidad firmada + evidencias frescas + drift summary. Lo que el auditor pide para empezar a revisar."
            onClick={() => {
              toast.info(
                "Dossier · cableado MB-7 (M27 dossier_generator + M24 IDMS bundle)",
              );
            }}
          />
          <ActionCard
            icon={<Wrench size={18} strokeWidth={2.4} />}
            title="Programar pentest refresh"
            description="Schedule pentest pre-auditoría para validar postura técnica."
            cta="Programar"
            tooltipText="Pentest pre-auditoría: validamos que las medidas técnicas siguen funcionando antes de que el auditor las revise. Si encontramos algo, lo arreglamos antes que él."
            onClick={() => {
              toast.info(
                "Pentest · cableado MB-7 (M08 verification + scan_window M14)",
              );
            }}
          />
        </div>
      </section>

      <ContactAuditorDialog
        projectId={projectId}
        open={contactOpen}
        onOpenChange={setContactOpen}
      />
    </div>
  );
}
