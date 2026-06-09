"use client";

/**
 * /admin/projects/[id]/equipo · sub-atom 1.C.F.1.
 *
 * Page admin project-scoped para gestion equipo del proyecto: usuario
 * portal cliente (m21 ClientUser + m30 portal contact) + empleados del
 * proyecto (m30 ClientContact has_portal_access=false) + areas/departments
 * (1.C.F.2 placeholder) + roles ENS (m30 ENS_REQUIRED · 1.C.F.4 prefill).
 *
 * 4 tabs:
 *   - Usuario portal (PortalUserPanel)
 *   - Empleados (ProjectContactsList filter=employees + create modal)
 *   - Áreas (placeholder · habilitada en 1.C.F.2)
 *   - Roles ENS (EnsRolesStatusPanel · auto-prefill 1.C.F.4)
 */
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

import { AreasPanel } from "./_components/AreasPanel";
import { EnsRolesStatusPanel } from "./_components/EnsRolesStatusPanel";
import { PortalUserPanel } from "./_components/PortalUserPanel";
import { ProjectContactCreateModal } from "./_components/ProjectContactCreateModal";
import { ProjectContactsList } from "./_components/ProjectContactsList";

export default function EquipoPage({
  params,
}: {
  params: { id: string };
}) {
  const projectId = params.id;
  const [reloadKey, setReloadKey] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);

  const reload = () => setReloadKey((k) => k + 1);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-[color:var(--fulkro-title)]">
          Equipo del proyecto
        </h1>
        <p className="mt-1 text-sm text-[color:var(--fulkro-muted)]">
          Usuario portal cliente, empleados del proyecto, áreas y roles ENS
          asignados. Todo project-scoped (R23 sostenido).
        </p>
      </div>

      <Tabs defaultValue="portal" className="w-full">
        <TabsList>
          <TabsTrigger value="portal">Usuario portal</TabsTrigger>
          <TabsTrigger value="employees">Empleados</TabsTrigger>
          <TabsTrigger value="areas">Áreas</TabsTrigger>
          <TabsTrigger value="ens-roles">Roles ENS</TabsTrigger>
        </TabsList>

        <TabsContent value="portal" className="mt-4">
          <PortalUserPanel projectId={projectId} />
          <div className="mt-4">
            <ProjectContactsList
              projectId={projectId}
              filter="portal"
              reloadKey={reloadKey}
              onReload={reload}
            />
          </div>
        </TabsContent>

        <TabsContent value="employees" className="mt-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <p className="text-sm text-[color:var(--fulkro-muted)]">
              Empleados del proyecto cliente. Se usan para asignar roles ENS,
              firmas de actas y referencias internas.
            </p>
            <Button onClick={() => setCreateOpen(true)}>
              + Nuevo empleado
            </Button>
          </div>
          <ProjectContactsList
            projectId={projectId}
            filter="employees"
            reloadKey={reloadKey}
            onReload={reload}
            onAssignmentChanged={reload}
          />
        </TabsContent>

        <TabsContent value="areas" className="mt-4">
          <AreasPanel projectId={projectId} reloadKey={reloadKey} />
        </TabsContent>

        <TabsContent value="ens-roles" className="mt-4">
          <EnsRolesStatusPanel
            projectId={projectId}
            reloadKey={reloadKey}
          />
        </TabsContent>
      </Tabs>

      <ProjectContactCreateModal
        projectId={projectId}
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={reload}
        defaultHasPortalAccess={false}
      />
    </div>
  );
}
