"use client";

/**
 * ArchetypeGate · renderiza children si feature/arquetipo PYME aplica
 * (ADR-036 SAN-D MB-17.2). Wrapper declarativo que consume
 * `useProjectFeatures()` context. Sin styling propio.
 */
import type { ReactNode } from "react";

import { useProjectFeatures } from "@/lib/contexts/ProjectFeaturesContext";
import type { FeatureKey, PymeArchetype } from "@/lib/feature-flags.types";

interface ArchetypeGateProps {
  feature?: FeatureKey;
  archetypes?: PymeArchetype[];
  fallback?: ReactNode;
  children: ReactNode;
}

export function ArchetypeGate({
  feature,
  archetypes,
  fallback = null,
  children,
}: ArchetypeGateProps) {
  const { data, isLoading, hasFeature } = useProjectFeatures();

  if (isLoading) return null;
  if (!data) return <>{fallback}</>;

  if (feature) {
    return hasFeature(feature) ? <>{children}</> : <>{fallback}</>;
  }

  if (archetypes && data.archetype) {
    return archetypes.includes(data.archetype) ? (
      <>{children}</>
    ) : (
      <>{fallback}</>
    );
  }

  return <>{fallback}</>;
}
