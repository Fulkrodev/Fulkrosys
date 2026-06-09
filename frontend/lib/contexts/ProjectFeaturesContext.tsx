"use client";

/**
 * ProjectFeaturesProvider · context compartido feature flags per proyecto
 * (ADR-036 SAN-D MB-17.2).
 *
 * TanStack Query staleTime 60s · cache compartido entre todos los gates
 * y components que usen `useProjectFeatures()` con mismo `projectId`.
 *
 * Wrap el árbol que necesite gating, típicamente:
 *   - layout admin proyecto (`/admin/projects/[id]/layout.tsx`)
 *   - layout client-portal cuando hay proyecto activo
 *   - cualquier sub-tree con CategoryGate / ArchetypeGate
 */
import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { featureFlagsApi } from "@/lib/api/feature-flags";
import type {
  FeatureKey,
  ProjectFeatureFlags,
} from "@/lib/feature-flags.types";

interface ProjectFeaturesContextValue {
  data: ProjectFeatureFlags | undefined;
  isLoading: boolean;
  hasFeature: (feature: FeatureKey) => boolean;
}

const ProjectFeaturesContext = createContext<ProjectFeaturesContextValue | null>(
  null,
);

interface ProjectFeaturesProviderProps {
  projectId: string;
  children: ReactNode;
}

export function ProjectFeaturesProvider({
  projectId,
  children,
}: ProjectFeaturesProviderProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["feature-flags", projectId],
    queryFn: () => featureFlagsApi.getProjectFeatureFlags(projectId),
    staleTime: 60_000,
    enabled: Boolean(projectId),
  });

  const hasFeature = (feature: FeatureKey): boolean => {
    if (!data) return false;
    return data.features[feature] === true;
  };

  return (
    <ProjectFeaturesContext.Provider value={{ data, isLoading, hasFeature }}>
      {children}
    </ProjectFeaturesContext.Provider>
  );
}

export function useProjectFeatures(): ProjectFeaturesContextValue {
  const ctx = useContext(ProjectFeaturesContext);
  if (!ctx) {
    throw new Error(
      "useProjectFeatures debe usarse dentro de ProjectFeaturesProvider",
    );
  }
  return ctx;
}
