"use client";

/**
 * AreasPanel · sub-atom 1.C.F.2.2.
 *
 * Composer del Tab Áreas dentro de page Equipo. Maneja:
 *  - Carga inicial (departments + suggestions)
 *  - Banner ENS-aware si existing=0 y categoría conocida
 *  - List + create modal
 *  - Skip banner persiste por sesión (state local)
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";

import { ApiError } from "@/lib/api";
import {
  getDepartmentSuggestions,
  listDepartments,
  type Department,
  type DepartmentSuggestionsResponse,
} from "@/lib/api/departments";

import { DepartmentCreateModal } from "./DepartmentCreateModal";
import { DepartmentReportPanel } from "./DepartmentReportPanel";
import { DepartmentSuggestionsBanner } from "./DepartmentSuggestionsBanner";
import { DepartmentsList } from "./DepartmentsList";

type Props = {
  projectId: string;
  /** Bump value desde el padre cuando asignación cambia externamente. */
  reloadKey?: number;
};

export function AreasPanel({ projectId, reloadKey }: Props) {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [suggestions, setSuggestions] =
    useState<DepartmentSuggestionsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [bannerSkipped, setBannerSkipped] = useState(false);

  const reload = async () => {
    setLoading(true);
    try {
      const [depts, sugg] = await Promise.all([
        listDepartments(projectId),
        getDepartmentSuggestions(projectId),
      ]);
      setDepartments(depts);
      setSuggestions(sugg);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error cargando áreas";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, reloadKey]);

  if (loading) {
    return (
      <div className="rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50/40 px-3 py-6 text-center text-sm text-[color:var(--fulkro-muted)]">
        Cargando áreas…
      </div>
    );
  }

  const showBanner =
    !bannerSkipped &&
    departments.length === 0 &&
    suggestions !== null &&
    suggestions.suggestions.length > 0;

  return (
    <div className="flex flex-col gap-4">
      {showBanner && suggestions ? (
        <DepartmentSuggestionsBanner
          projectId={projectId}
          data={suggestions}
          onAccepted={() => void reload()}
          onSkip={() => setBannerSkipped(true)}
        />
      ) : null}

      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-[color:var(--fulkro-muted)]">
          Áreas/departamentos del proyecto cliente. Empleados se asignarán a
          áreas en sub-atom 1.C.F.3.
        </p>
        <Button onClick={() => setCreateOpen(true)}>+ Nueva área</Button>
      </div>

      <DepartmentsList
        projectId={projectId}
        departments={departments}
        onChanged={() => void reload()}
        reportReloadKey={reloadKey}
      />

      {departments.length > 0 ? (
        <DepartmentReportPanel
          projectId={projectId}
          reloadKey={reloadKey}
        />
      ) : null}

      <DepartmentCreateModal
        projectId={projectId}
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={() => void reload()}
      />
    </div>
  );
}
