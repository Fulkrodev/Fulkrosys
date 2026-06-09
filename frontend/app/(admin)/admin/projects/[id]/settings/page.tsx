/**
 * /admin/projects/[id]/settings · Sub-area 2C Sesión 3B-2B.9 CLUSTER 2.
 *
 * Settings HUB landing thin · Pattern P-CL2-4 ENRICH (NO duplica funcionalidad existing):
 * sections-cards linking a 6 routes settings scattered existing pre-CLUSTER 2.
 *
 * REFACTOR+EXTEND scope refined per OPS-052 manifestación 66ª empirical:
 * settings infrastructure ya distribuida cross 6+ routes · briefing target
 * "consolidated full" mejor servido como HUB navigation que duplicate logic.
 *
 * Routes linked (existing · NO new endpoints needed · OPS-026 DRY):
 *   - cliente-info: datos del cliente (CIF · razón social · sector · contacto)
 *   - personalizacion: branding portal cliente (colores · logo · footer)
 *   - users: usuarios del portal cliente (invite · revoke · MFA)
 *   - auditor-handoff: magic links auditor ENAC (M12 · 3 purposes)
 *   - feature-flags: per-project feature flags admin override
 *   - equipo: equipo y roles topology
 *
 * Future-X placeholders (Pattern P-CL2-3 honest defer):
 *   - Future-1.E.settings-notification-preferences-section (~1-2h post-piloto)
 *     · mute · DND · quiet hours admin per project
 *   - Future-1.E.settings-danger-zone-archive-delete (~1-2h post-piloto)
 *     · archive proyecto · soft delete · supervision_mode toggle live (backend
 *       ProjectUpdate endpoint requerido primero)
 */
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  Building2,
  FileSignature,
  Flag,
  Palette,
  ScrollText,
  Settings,
  UserCog,
  Users2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

export const metadata = {
  title: "Configuración del proyecto · FULKRO",
};

interface SettingsSection {
  href: string;
  label: string;
  description: string;
  icon: typeof Settings;
  testId: string;
  disabled?: boolean;
  disabledReason?: string;
  futureRef?: string;
}

interface PageProps {
  params: { id: string };
}

export default function ProjectSettingsPage({ params }: PageProps) {
  const projectId = params.id;

  const sections: SettingsSection[] = [
    {
      href: `/admin/projects/${projectId}/cliente-info`,
      label: "Datos del cliente",
      description:
        "CIF · razón social · sector · provincia · empleados · contacto · suspend/reactivate.",
      icon: Building2,
      testId: "settings-card-cliente-info",
    },
    {
      href: `/admin/projects/${projectId}/personalizacion`,
      label: "Branding y portal cliente",
      description:
        "Colores corporativos (primary · secondary) · logo cliente · texto pie portal.",
      icon: Palette,
      testId: "settings-card-personalizacion",
    },
    {
      href: `/admin/projects/${projectId}/users`,
      label: "Usuarios del portal",
      description:
        "Invitar · resetear contraseña · reenviar invitación · desactivar usuarios cliente.",
      icon: Users2,
      testId: "settings-card-users",
    },
    {
      href: `/admin/projects/${projectId}/auditor-handoff`,
      label: "Magic links auditor",
      description:
        "Generación + histórico magic links Ed25519 para auditor ENAC (3 purposes · M12).",
      icon: ScrollText,
      testId: "settings-card-auditor-handoff",
    },
    {
      href: `/admin/projects/${projectId}/feature-flags`,
      label: "Feature flags",
      description:
        "Override per-project feature flags ENS · profile gates · workflow toggles.",
      icon: Flag,
      testId: "settings-card-feature-flags",
    },
    {
      href: `/admin/projects/${projectId}/equipo`,
      label: "Equipo y roles",
      description:
        "Topología roles ENS · responsables medidas · áreas funcionales · asignaciones.",
      icon: UserCog,
      testId: "settings-card-equipo",
    },
    {
      href: "#",
      label: "Preferencias de notificaciones",
      description:
        "Mute · DND · quiet hours admin · canales preferidos per project.",
      icon: Bell,
      testId: "settings-card-notifications-future",
      disabled: true,
      disabledReason: "Próximamente",
      futureRef: "Future-1.E.settings-notification-preferences-section",
    },
    {
      href: "#",
      label: "Zona peligrosa",
      description:
        "Archivar proyecto · soft delete · supervision_mode toggle live (admin only).",
      icon: AlertTriangle,
      testId: "settings-card-danger-zone-future",
      disabled: true,
      disabledReason: "Próximamente",
      futureRef: "Future-1.E.settings-danger-zone-archive-delete",
    },
  ];

  return (
    <div className="space-y-6" data-testid="project-settings-page">
      <header className="space-y-1">
        <h2 className="flex items-center gap-2 text-xl font-semibold text-fulkro-primary-700">
          <Settings className="h-5 w-5" aria-hidden="true" />
          Configuración del proyecto
        </h2>
        <p className="text-sm text-fulkro-ink-600">
          Hub de configuración del proyecto: datos del cliente · branding ·
          usuarios del portal · magic links auditor · feature flags y equipo.
          Selecciona una sección para gestionar.
        </p>
      </header>

      <div
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
        role="list"
        aria-label="Secciones de configuración"
      >
        {sections.map((section) => (
          <SettingsCard key={section.testId} section={section} />
        ))}
      </div>
    </div>
  );
}

function SettingsCard({ section }: { section: SettingsSection }) {
  const Icon = section.icon;
  const isDisabled = section.disabled === true;

  const cardInner = (
    <Card
      className={cn(
        "h-full transition-colors",
        isDisabled
          ? "opacity-60"
          : "hover:border-fulkro-primary-300 hover:shadow-md",
      )}
      data-testid={section.testId}
    >
      <CardHeader className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <Icon
            className={cn(
              "h-5 w-5",
              isDisabled
                ? "text-fulkro-ink-600"
                : "text-fulkro-primary-700",
            )}
            aria-hidden="true"
          />
          {isDisabled && section.disabledReason ? (
            <Badge variant="outline" className="text-xs">
              {section.disabledReason}
            </Badge>
          ) : null}
        </div>
        <CardTitle className="text-base">{section.label}</CardTitle>
        <CardDescription>{section.description}</CardDescription>
      </CardHeader>
      <CardContent>
        {isDisabled ? (
          <p
            className="text-xs italic text-fulkro-ink-500"
            data-testid={`${section.testId}-future-ref`}
          >
            {section.futureRef}
          </p>
        ) : (
          <span
            className={cn(
              buttonVariants({ variant: "outline", size: "sm" }),
              "inline-flex w-full justify-center",
            )}
            aria-hidden="true"
          >
            Abrir
            <ArrowRight className="ml-2 h-3 w-3" aria-hidden="true" />
          </span>
        )}
      </CardContent>
    </Card>
  );

  if (isDisabled) {
    return (
      <div role="listitem" aria-disabled="true">
        {cardInner}
      </div>
    );
  }

  return (
    <Link
      href={section.href}
      role="listitem"
      className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700 focus-visible:rounded-lg"
      aria-label={`${section.label} · ${section.description}`}
    >
      {cardInner}
    </Link>
  );
}
