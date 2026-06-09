"use client";

/**
 * CategoryGate · renderiza children si feature/categoría aplica al
 * proyecto (ADR-036 SAN-D MB-17.2). Wrapper declarativo que consume
 * `useProjectFeatures()` context.
 *
 * Coherencia visual ADR-035: el gate NO añade styling propio · solo
 * controla visibility. Los children mantienen su composición shadcn
 * existente.
 */
import type { ReactNode } from "react";

import { useProjectFeatures } from "@/lib/contexts/ProjectFeaturesContext";
import type { EnsCategory, FeatureKey } from "@/lib/feature-flags.types";

interface CategoryGateProps {
  feature?: FeatureKey;
  categories?: EnsCategory[];
  fallback?: ReactNode;
  children: ReactNode;
}

export function CategoryGate({
  feature,
  categories,
  fallback = null,
  children,
}: CategoryGateProps) {
  const { data, isLoading, hasFeature } = useProjectFeatures();

  if (isLoading) return null;
  if (!data) return <>{fallback}</>;

  if (feature) {
    return hasFeature(feature) ? <>{children}</> : <>{fallback}</>;
  }

  if (categories) {
    return categories.includes(data.categoria) ? (
      <>{children}</>
    ) : (
      <>{fallback}</>
    );
  }

  return <>{children}</>;
}
