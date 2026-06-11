"use client";

/**
 * ProjectCategoryBanner · Card contextual ENS categoría + arquetipo
 * (ADR-036 SAN-D MB-17.3). Aparece debajo de ProjectHeader · informa
 * de un vistazo qué obligaciones aplican a este proyecto.
 *
 * Coherencia visual: shadcn Card + Badge composition · solo fulkro
 * palette · iconos lucide-react · sin styling hardcoded.
 *
 * Sector Salud sub-banner usa <ArchetypeGate feature="art9_rgpd_data">
 * para visibility declarativa · tracks feature flag catalog real.
 */
import { Award, Stethoscope } from "lucide-react";

import { ArchetypeGate } from "@/components/feature-flags/ArchetypeGate";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useProjectFeatures } from "@/lib/contexts/ProjectFeaturesContext";
import type { EnsCategory, PymeArchetype } from "@/lib/feature-flags.types";
import { cn } from "@/lib/utils";

interface CategoryConfig {
  borderClass: string;
  iconClass: string;
  badgeVariant: "secondary" | "warning" | "success";
  description: string;
}

const CATEGORY_THEME: Record<EnsCategory, CategoryConfig> = {
  BASICA: {
    borderClass: "border-l-fulkro-success",
    iconClass: "text-fulkro-success",
    badgeVariant: "secondary",
    description:
      "Autoevaluación CCN-STIC 808 · sin auditoría externa obligatoria",
  },
  MEDIA: {
    borderClass: "border-l-fulkro-warning",
    iconClass: "text-fulkro-warning",
    badgeVariant: "warning",
    description:
      "Auditoría externa ENAC obligatoria · 3-5 jornadas · refuerzos R1",
  },
  ALTA: {
    borderClass: "border-l-fulkro-success",
    iconClass: "text-fulkro-success",
    badgeVariant: "success",
    description:
      "Pentest CPSTIC · productos certificados · criptografía 807 · refuerzos R2-R4 · Red Team",
  },
};

const ARCHETYPE_LABEL: Record<PymeArchetype, string> = {
  saas_only: "SaaS only",
  teletrabajo_total: "Teletrabajo total",
  sector_salud: "Sector salud",
  sector_educacion: "Sector educación",
  desarrollador_aapp: "Desarrollador AAPP",
  proveedor_financiero: "Proveedor financiero",
  generico: "Genérico",
};

export function ProjectCategoryBanner() {
  const { data, isLoading } = useProjectFeatures();

  if (isLoading || !data) return null;

  const theme = CATEGORY_THEME[data.categoria];
  const archetypeLabel = data.archetype
    ? ARCHETYPE_LABEL[data.archetype]
    : null;

  return (
    <Card className={cn("border-l-4", theme.borderClass)}>
      <CardContent className="flex flex-wrap items-center gap-3 p-4">
        <Award className={cn("h-7 w-7 shrink-0", theme.iconClass)} />
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold">
              ENS Categoría {data.categoria}
            </h3>
            <Badge variant={theme.badgeVariant}>{data.categoria}</Badge>
            {archetypeLabel && data.archetype !== "generico" && (
              <Badge variant="outline">{archetypeLabel}</Badge>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {theme.description}
          </p>
          <ArchetypeGate feature="art9_rgpd_data">
            <div className="mt-2 flex items-start gap-2 rounded-md bg-fulkro-warning/10 p-2 text-xs text-fulkro-warning">
              <Stethoscope className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                <strong>Sector salud · Art.9 RGPD:</strong> tratamiento datos
                especiales · Ley 41/2002 historia clínica · DPIA obligatoria ·
                medidas reforzadas aplicables
              </span>
            </div>
          </ArchetypeGate>
        </div>
      </CardContent>
    </Card>
  );
}
