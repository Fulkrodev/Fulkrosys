"use client";

/**
 * Policy family accordion · agrupación per familia CCN-STIC 805.
 *
 * Mitigación 25 cards fatiga UX · accordion expand por familia.
 * Pattern simple · sin dependencia shadcn accordion (lighter bundle).
 */
import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import { PolicyRow } from "@/components/client-portal/policies/PolicyRow";
import {
  type PolicyClientView,
  type PolicyFamily,
  type PolicyReviewAction,
} from "@/lib/api/policies";

const FAMILY_LABELS: Record<PolicyFamily, string> = {
  fundamental: "Fundamental (PSI)",
  identidad: "Identidad y acceso",
  personal: "Personas",
  informacion: "Información",
  continuidad: "Continuidad",
  criptografia: "Criptografía",
  operacion: "Operación",
  movilidad: "Movilidad",
  proveedores: "Proveedores",
  desarrollo: "Desarrollo seguro",
  redes: "Redes",
  fisica: "Seguridad física",
  otros: "Otros",
};

interface Props {
  policies: PolicyClientView[];
  onReview: (
    documentId: string,
    action: PolicyReviewAction,
    note?: string,
  ) => Promise<void>;
  disabled: boolean;
  defaultOpen?: boolean;
}

function groupByFamily(policies: PolicyClientView[]): Map<PolicyFamily, PolicyClientView[]> {
  const map = new Map<PolicyFamily, PolicyClientView[]>();
  for (const p of policies) {
    const arr = map.get(p.family) ?? [];
    arr.push(p);
    map.set(p.family, arr);
  }
  return map;
}

const FAMILY_ORDER: PolicyFamily[] = [
  "fundamental",
  "identidad",
  "personal",
  "informacion",
  "continuidad",
  "criptografia",
  "operacion",
  "movilidad",
  "proveedores",
  "desarrollo",
  "redes",
  "fisica",
  "otros",
];

export function PolicyFamilyAccordion({
  policies,
  onReview,
  disabled,
  defaultOpen = true,
}: Props) {
  const grouped = groupByFamily(policies);
  const [openFamilies, setOpenFamilies] = useState<Set<PolicyFamily>>(() => {
    if (defaultOpen) return new Set<PolicyFamily>(FAMILY_ORDER);
    return new Set<PolicyFamily>(["fundamental"]);
  });

  const toggle = (family: PolicyFamily) => {
    setOpenFamilies((prev) => {
      const next = new Set(prev);
      if (next.has(family)) next.delete(family);
      else next.add(family);
      return next;
    });
  };

  return (
    <div className="space-y-2">
      {FAMILY_ORDER.map((family) => {
        const items = grouped.get(family);
        if (!items || items.length === 0) return null;
        const isOpen = openFamilies.has(family);
        const reviewedCount = items.filter(
          (p) => p.client_review_status === "revisada_ok",
        ).length;

        return (
          <div
            key={family}
            data-family={family}
            className="rounded-lg border border-fulkro-ink-200 bg-white overflow-hidden"
          >
            <button
              type="button"
              onClick={() => toggle(family)}
              className="w-full flex items-center justify-between gap-2 px-4 py-3 hover:bg-fulkro-ink-50 transition-colors"
              aria-expanded={isOpen}
            >
              <div className="flex items-center gap-2">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4 text-fulkro-ink-500" aria-hidden />
                ) : (
                  <ChevronRight className="h-4 w-4 text-fulkro-ink-500" aria-hidden />
                )}
                <span className="font-semibold text-sm text-fulkro-ink-800">
                  {FAMILY_LABELS[family]}
                </span>
              </div>
              <span className="text-xs text-fulkro-ink-500 font-mono tabular-nums">
                {reviewedCount} / {items.length}
              </span>
            </button>
            {isOpen && (
              <div className="px-4 pb-4 space-y-2">
                {items.map((p) => (
                  <PolicyRow
                    key={p.template_codigo}
                    policy={p}
                    onReview={onReview}
                    disabled={disabled}
                  />
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
