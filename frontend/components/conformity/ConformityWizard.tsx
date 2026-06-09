"use client";

/**
 * ConformityWizard · 12 steps adaptados per categoría ENS B/M/A
 * (ADR-036 SAN-D MB-17.7). Renderiza solo los steps aplicables al
 * proyecto (filtrados por feature flags · categories) · cada step
 * tiene CTA "Ir" enlazando a la ruta motor existing (mapping
 * ADR-036 · sub-routes dedicadas diferidas).
 *
 * Coherencia visual ADR-035 / TRAD-9-12 ADR-036:
 * - Card shadcn composition (no div bare)
 * - fulkro-success · fulkro-warning · fulkro-danger palette
 * - Badge variant=success para completed
 * - lucide icons (Check · Circle · ArrowRight)
 *
 * Status check M09 readiness: stub `# Future:` (TRAD-11 ADR-036)
 * hasta wire-up M09 readiness API · placeholder isCompleted=false ·
 * UI muestra todos como pendientes con CTA "Ir" al motor.
 */
import { ArrowRight, Check } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { useProjectFeatures } from "@/lib/contexts/ProjectFeaturesContext";
import type { EnsCategory, FeatureKey } from "@/lib/feature-flags.types";
import { cn } from "@/lib/utils";

interface Step {
  number: number;
  title: string;
  description: string;
  ctaPath: string;
  required_feature?: FeatureKey;
  required_categories?: EnsCategory[];
}

/**
 * 12 steps · ctaPath usa routes mapping ADR-036 (no sub-routes
 * dedicadas /conformity/{declaration|self-assessment|badge}).
 * Wizard renderiza inline · sub-routes deferrable a MB-19+.
 */
const CONFORMITY_STEPS: Step[] = [
  {
    number: 1,
    title: "DdA final firmada",
    description: "Declaración de Aplicabilidad firmada por RSEG",
    ctaPath: "/obligations",
    required_categories: ["BASICA", "MEDIA", "ALTA"],
  },
  {
    number: 2,
    title: "Plan adecuación implementado",
    description: "Todas las medidas DdA aplicadas con evidencias documentadas",
    ctaPath: "/implementation",
    required_categories: ["BASICA", "MEDIA", "ALTA"],
  },
  {
    number: 3,
    title: "Autoevaluación CCN-STIC 809",
    description: "Cuestionario de autoevaluación firmado por RSEG",
    ctaPath: "/conformity",
    required_feature: "basica_autoevaluacion",
  },
  {
    number: 4,
    title: "Declaración de Conformidad (Básica)",
    description: "DOCX firmado responsable + publicación en sede",
    ctaPath: "/conformity",
    required_feature: "basica_autoevaluacion",
  },
  {
    number: 5,
    title: "Auditor externo ENAC asignado",
    description: "Contacto rol auditor ENAC confirmado",
    ctaPath: "/roles?role=auditor_externo",
    required_feature: "media_auditor_enac",
  },
  {
    number: 6,
    title: "Auditoría externa ejecutada",
    description: "3-5 jornadas auditor ENAC · informe final entregado",
    ctaPath: "/audit",
    required_feature: "media_auditoria_externa",
  },
  {
    number: 7,
    title: "Pentest CPSTIC ejecutado",
    description: "CCN-STIC 105/140 · pentester acreditado · informe firmado",
    ctaPath: "/verification?focus=pentest_cpstic",
    required_feature: "alta_pentest_cpstic",
  },
  {
    number: 8,
    title: "Productos certificados CPSTIC inventariados",
    description: "Inventario marca explícitamente productos CPSTIC catálogo",
    ctaPath: "/verification?focus=cpstic_products",
    required_feature: "alta_productos_cpstic",
  },
  {
    number: 9,
    title: "Criptografía CCN-STIC 807",
    description: "Evidencias algoritmos acreditados + gestión de claves",
    ctaPath: "/evidence?type=criptografia_807",
    required_feature: "alta_criptografia_807",
  },
  {
    number: 10,
    title: "Red Team E-704 ejecutado",
    description: "Ejercicio Red Team obligatorio Categoría Alta",
    ctaPath: "/verification?focus=red_team",
    required_feature: "alta_red_team",
  },
  {
    number: 11,
    title: "Distintivo + certificado de conformidad",
    description: "Generación de distintivo SVG + DOCX certificado",
    ctaPath: "/conformity",
    required_categories: ["BASICA", "MEDIA", "ALTA"],
  },
  {
    number: 12,
    title: "Reporte INES anual",
    description: "Reporte CCN-STIC 824/844 anual al CCN",
    ctaPath: "/conformity",
    required_categories: ["BASICA", "MEDIA", "ALTA"],
  },
];

interface Props {
  projectId: string;
}

export function ConformityWizard({ projectId }: Props) {
  const { data, hasFeature, isLoading } = useProjectFeatures();

  if (isLoading || !data) return null;

  const applicableSteps = CONFORMITY_STEPS.filter((step) => {
    if (step.required_feature) return hasFeature(step.required_feature);
    if (step.required_categories) {
      return step.required_categories.includes(data.categoria);
    }
    return true;
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Camino a <InfoTag term="workflow_conformidad" display="Conformidad ENS" />{" "}
          {data.categoria}
        </CardTitle>
        <CardDescription>
          {applicableSteps.length} paso{applicableSteps.length === 1 ? "" : "s"}
          {" "}para alcanzar conformidad. Marcamos cada uno conforme se completa.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ol className="space-y-3">
          {applicableSteps.map((step, idx) => (
            <ConformityStep
              key={step.number}
              step={step}
              displayIndex={idx + 1}
              projectId={projectId}
            />
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

interface ConformityStepProps {
  step: Step;
  displayIndex: number;
  projectId: string;
}

function ConformityStep({ step, displayIndex, projectId }: ConformityStepProps) {
  // Future: M09 readiness API wire-up SAN-D MB-17.7-DEFERRED · hasta
  // entonces stub False · UI muestra todos pendientes con CTA Ir al
  // motor (TRAD-11 ADR-036 deferrable inline policy).
  const isCompleted = false;
  const url = `/admin/projects/${projectId}${step.ctaPath}`;

  return (
    <li
      className={cn(
        "rounded-md border p-4",
        isCompleted ? "bg-fulkro-success/5" : "bg-card",
      )}
    >
      <div className="flex flex-wrap items-start gap-3">
        <div
          className={cn(
            "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2",
            isCompleted
              ? "border-fulkro-success bg-fulkro-success text-white"
              : "border-muted-foreground text-muted-foreground",
          )}
        >
          {isCompleted ? (
            <Check className="h-4 w-4" strokeWidth={2.6} />
          ) : (
            <span className="text-xs font-semibold">{displayIndex}</span>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">{step.title}</h3>
            {isCompleted && <Badge variant="success">Completado</Badge>}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {step.description}
          </p>

          {!isCompleted && (
            <Link
              href={url}
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "mt-3",
              )}
            >
              Ir
              <ArrowRight className="ml-1 h-3 w-3" strokeWidth={2.3} />
            </Link>
          )}
        </div>
      </div>
    </li>
  );
}
