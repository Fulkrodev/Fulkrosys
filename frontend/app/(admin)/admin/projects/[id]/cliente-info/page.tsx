"use client";

/**
 * /admin/projects/[id]/cliente-info · Sesión 3B-2B.3 Phase X.4a NEW.
 *
 * Migrates "Datos cliente" tab (was inside /admin/clients/[id] before R23
 * strict cleanup) to project-scoped location. Per directive Marcos:
 * cliente entity ≈ project entity 1:1 MVP · cliente metadata lives where the
 * project lives.
 *
 * Functionality preserved feature-parity:
 *  - Datos cliente form (CIF · razón social · sector · provincia · empleados ·
 *    contacto email/teléfono · lead_source) editable inline (DatosTab).
 *  - Contactos lista per cliente entity (ContactosTab · 95 LOC existing).
 *  - Suspend/Reactivate cliente action button (SuspendDialog · 135 LOC existing).
 *
 * Reuses shared client-data components from `@/components/admin-clients/`.
 * Estos componentes vivían antes en la carpeta privada `_components/` de la
 * ruta `/admin/clients/[id]` y se importaban por path relativo profundo
 * (acoplamiento cross-route · §4.5/380). Ahora están en una ubicación común no
 * enrutada y se importan vía alias `@/components/...`.
 *
 * Data flow:
 *  1. projectId from URL param
 *  2. Fetch /api/v1/projects/{id}/header → { project, cliente: { id, ... } }
 *  3. Fetch /api/v1/admin/clients/{cliente.id} → full ClientDetail
 *  4. Render Datos + Contactos cards + Suspend/Resume action
 */
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { use } from "react";
import { toast } from "sonner";
import { useState } from "react";
import { Building2, ChevronLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

import { api, ApiError } from "@/lib/api";
import { getClientDetail, resumeClient } from "@/lib/admin-clients/api";
import type { ClientDetail } from "@/lib/admin-clients/schemas";

import { DatosTab } from "@/components/admin-clients/DatosTab";
import { ContactosTab } from "@/components/admin-clients/ContactosTab";
import { SuspendDialog } from "@/components/admin-clients/SuspendDialog";

interface ProjectHeaderResponse {
  project: { id: string; nombre: string };
  cliente: { id: string; nombre: string; cif: string };
}

export default function AdminProjectClienteInfoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: projectId } = use(params);
  const [resuming, setResuming] = useState(false);

  // 1. Resolve cliente.id from project header
  const projectHeaderQ = useQuery<ProjectHeaderResponse>({
    queryKey: ["project-composer", "header", projectId],
    queryFn: () => api<ProjectHeaderResponse>(`/api/v1/projects/${projectId}/header`),
    staleTime: 60_000,
  });

  const clientId = projectHeaderQ.data?.cliente.id ?? null;

  // 2. Fetch full ClientDetail when clientId available
  const clientDetailQ = useQuery<ClientDetail>({
    queryKey: ["admin-clients", "detail", clientId],
    queryFn: () => getClientDetail(clientId!),
    enabled: !!clientId,
    staleTime: 30_000,
  });

  const handleResume = async () => {
    if (!clientId) return;
    setResuming(true);
    try {
      await resumeClient(clientId);
      toast.success("Cliente reactivado");
      await clientDetailQ.refetch();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al reactivar",
      );
    } finally {
      setResuming(false);
    }
  };

  if (projectHeaderQ.isLoading || clientDetailQ.isLoading || !clientDetailQ.data) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (projectHeaderQ.isError || clientDetailQ.isError) {
    return (
      <div className="flex flex-col gap-3">
        <Link
          href={`/admin/projects/${projectId}/summary`}
          className="inline-flex items-center gap-1 text-sm font-bold text-fulkro-primary-700 hover:underline"
        >
          <ChevronLeft className="h-4 w-4" /> Volver al proyecto
        </Link>
        <div
          role="alert"
          className="rounded border border-fulkro-danger/40 bg-fulkro-danger/10 p-3 text-sm text-fulkro-danger"
        >
          Error al cargar datos del cliente.
        </div>
      </div>
    );
  }

  const detail = clientDetailQ.data;
  const isSuspended = detail.deleted_at !== null;

  return (
    <div className="flex flex-col gap-6">
      <Link
        href={`/admin/projects/${projectId}/summary`}
        className="inline-flex w-fit items-center gap-1 text-sm font-bold text-fulkro-primary-700 hover:underline"
      >
        <ChevronLeft className="h-4 w-4" /> Volver al proyecto
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <Building2 className="h-7 w-7 text-fulkro-primary-700" />
            <h1 className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
              {detail.nombre}
            </h1>
            {isSuspended ? (
              <Badge variant="outline">Suspendido</Badge>
            ) : (
              <Badge variant="default">Activo</Badge>
            )}
          </div>
          <p className="font-mono text-base font-medium text-fulkro-ink-700">
            {detail.cif}
          </p>
          <p className="text-sm font-medium text-fulkro-ink-700">
            Datos del cliente asociado al proyecto.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isSuspended ? (
            <Button
              variant="outline"
              onClick={() => void handleResume()}
              disabled={resuming}
            >
              {resuming ? "Reactivando..." : "Reactivar cliente"}
            </Button>
          ) : (
            <SuspendDialog
              clientId={detail.id}
              clientName={detail.nombre}
              onSuspended={async () => {
                await clientDetailQ.refetch();
              }}
            />
          )}
        </div>
      </header>

      <section aria-labelledby="datos-cliente">
        <h2
          id="datos-cliente"
          className="mb-3 text-xl font-bold text-[color:var(--fulkro-title)]"
        >
          Datos identificativos
        </h2>
        <DatosTab
          detail={detail}
          onUpdated={async () => {
            await clientDetailQ.refetch();
          }}
        />
      </section>

      <section aria-labelledby="contactos">
        <h2
          id="contactos"
          className="mb-3 text-xl font-bold text-[color:var(--fulkro-title)]"
        >
          Contactos cliente
        </h2>
        <ContactosTab clientId={detail.id} />
      </section>
    </div>
  );
}
