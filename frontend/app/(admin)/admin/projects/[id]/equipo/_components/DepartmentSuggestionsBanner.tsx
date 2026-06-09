"use client";

/**
 * DepartmentSuggestionsBanner · sub-atom 1.C.F.2.2.
 *
 * Banner UX que muestra sugerencias ENS-aware (B=1 · M=2 · A=4 áreas) al
 * cargar areas page con 0 departments y categoría project definida.
 * Bulk-accept o skip · re-clic seguro (bulk endpoint skipea duplicados).
 */
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { ApiError } from "@/lib/api";
import {
  bulkCreateDepartments,
  type DepartmentSuggestionsResponse,
} from "@/lib/api/departments";

type Props = {
  projectId: string;
  data: DepartmentSuggestionsResponse;
  onAccepted: () => void;
  onSkip: () => void;
};

export function DepartmentSuggestionsBanner({
  projectId,
  data,
  onAccepted,
  onSkip,
}: Props) {
  const [submitting, setSubmitting] = useState(false);

  const accept = async () => {
    setSubmitting(true);
    try {
      const created = await bulkCreateDepartments(
        projectId,
        data.suggestions.map((s) => ({
          code: s.code,
          name: s.name,
          description: s.description,
        })),
      );
      toast.success(`${created.length} área(s) creada(s).`);
      onAccepted();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error aceptando sugerencias";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (data.suggestions.length === 0) {
    return null;
  }

  return (
    <Card className="border-fulkro-primary-200 bg-fulkro-primary-50/50">
      <CardHeader>
        <CardTitle className="text-base">
          Sugerencias para categoría {data.project_category ?? "—"}
        </CardTitle>
        <p className="mt-1 text-sm text-[color:var(--fulkro-muted)]">
          Pre-carga {data.suggestions.length} área(s) ENS-recomendadas para esta
          categoría. Podrás editarlas o añadir más después.
        </p>
      </CardHeader>
      <CardContent>
        <ul className="mb-4 grid grid-cols-1 gap-2 md:grid-cols-2">
          {data.suggestions.map((s) => (
            <li
              key={s.code}
              className="rounded-md border border-fulkro-ink-100 bg-white px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <span className="rounded bg-fulkro-primary-100 px-2 py-0.5 text-xs font-bold text-fulkro-primary-800">
                  {s.code}
                </span>
                <span className="font-medium text-fulkro-ink-800">
                  {s.name}
                </span>
              </div>
              <p className="mt-1 text-xs text-[color:var(--fulkro-muted)]">
                {s.description}
              </p>
            </li>
          ))}
        </ul>
        <div className="flex items-center justify-end gap-2">
          <Button
            variant="outline"
            onClick={onSkip}
            disabled={submitting}
          >
            Crear manualmente
          </Button>
          <Button onClick={() => void accept()} disabled={submitting}>
            {submitting ? "Creando…" : "Aceptar sugerencias"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
