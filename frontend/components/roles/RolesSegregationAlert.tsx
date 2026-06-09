"use client";

/**
 * RolesSegregationAlert · SAN-C.MB-9.bis.4.
 *
 * Valida segregación funcional roles ENS (CCN-STIC 801) + roles
 * obligatorios per categoría. Resuelve el client_id internamente desde
 * el endpoint composer ``GET /api/v1/projects/{id}/header`` para que
 * el caller solo necesite el projectId.
 *
 * Render:
 *  - Conformes → Alert variant default verde con OK
 *  - No conformes → Alert variant destructive con violations + missing
 *
 * Refs: SAN-C.MB-9.bis.4 · cierra fantasma frontend MB-9.5.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import {
  type EnsCategoryTarget,
  type RoleValidationResult,
  validateRolesEns,
} from "@/lib/api/contacts";

interface ProjectHeaderClienteOnly {
  cliente: {
    id: string;
  };
  project?: {
    categoria_objetivo: string | null;
  };
}

interface RolesSegregationAlertProps {
  projectId: string;
  /** Sobrescribe la categoría inferida del project header. */
  targetCategory?: EnsCategoryTarget;
}

const CATEGORY_NORMALIZE: Record<string, EnsCategoryTarget> = {
  BASICA: "BASICA",
  MEDIA: "MEDIA",
  ALTA: "ALTA",
  BÁSICA: "BASICA",
};

export function RolesSegregationAlert({
  projectId,
  targetCategory,
}: RolesSegregationAlertProps) {
  const headerQuery = useQuery<ProjectHeaderClienteOnly>({
    queryKey: ["project-header-clientid", projectId],
    queryFn: () => api(`/api/v1/projects/${projectId}/header`),
    staleTime: 5 * 60 * 1000,
  });

  const clientId = headerQuery.data?.cliente.id;
  const inferredCategory: EnsCategoryTarget = (() => {
    const raw = headerQuery.data?.project?.categoria_objetivo ?? null;
    if (!raw) return "BASICA";
    return CATEGORY_NORMALIZE[raw.toUpperCase()] ?? "BASICA";
  })();
  const effectiveCategory: EnsCategoryTarget = targetCategory ?? inferredCategory;

  const validationQuery = useQuery<RoleValidationResult>({
    queryKey: ["validate-roles-ens", clientId, effectiveCategory],
    queryFn: () => {
      if (!clientId) return Promise.reject(new Error("clientId not resolved"));
      return validateRolesEns(clientId, effectiveCategory);
    },
    enabled: Boolean(clientId),
    staleTime: 60 * 1000,
  });

  if (headerQuery.isLoading || validationQuery.isLoading) {
    return <Skeleton className="h-24 w-full" />;
  }

  if (headerQuery.isError || !clientId) {
    return null; // silent fail · no bloquea UI principal
  }

  const result = validationQuery.data;
  if (!result) return null;

  if (result.compliant) {
    return (
      <Alert>
        <CheckCircle2 className="h-4 w-4" />
        <AlertTitle>Roles ENS conformes</AlertTitle>
        <AlertDescription>
          Categoría {result.target_category} · todos los roles obligatorios
          asignados · segregación CCN-STIC 801 cumplida.
        </AlertDescription>
      </Alert>
    );
  }

  const mayorViolations = result.violations.filter(
    (v) => v.severity === "mayor",
  );
  const menorViolations = result.violations.filter(
    (v) => v.severity === "menor",
  );

  return (
    <Alert variant="danger">
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>No conformidad CCN-STIC 801 detectada</AlertTitle>
      <AlertDescription>
        <div className="mt-2 space-y-2 text-sm">
          {mayorViolations.length > 0 ? (
            <div>
              <strong>Violaciones segregación funcional (mayor):</strong>
              <ul className="list-disc pl-5">
                {mayorViolations.map((v, i) => (
                  <li key={`mayor-${i}`}>
                    <span className="font-medium">{v.rule}</span> — {v.detail}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {result.missing_roles.length > 0 ? (
            <div>
              <strong>
                Roles faltantes para categoría {result.target_category}:
              </strong>
              <ul className="list-disc pl-5">
                {result.missing_roles.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {menorViolations.length > 0 && result.missing_roles.length === 0 ? (
            <div>
              <strong>Otras observaciones (menor):</strong>
              <ul className="list-disc pl-5">
                {menorViolations.map((v, i) => (
                  <li key={`menor-${i}`}>{v.detail}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </AlertDescription>
    </Alert>
  );
}
