/**
 * DdaAdminPanel · orquestador admin M03 DdA · sub-atom 1.D.F.A v3.11.
 *
 * Tabs: Stats · Medidas · Catálogo · Congelación.
 *
 * Si DdA aún no existe (status.exists=false) · muestra hero con
 * DdaGenerateButton + explicación primer principios R30.
 */
"use client";

import * as React from "react";
import {
  ClipboardCheck,
  FileSpreadsheet,
  ListChecks,
  Lock,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import { useDdaAdminStatus } from "@/hooks/useDdaAdmin";

import { DdaCatalogView } from "./DdaCatalogView";
import { DdaEntriesList } from "./DdaEntriesList";
import { DdaEntryDetailModal } from "./DdaEntryDetailModal";
import { DdaFreezeButton } from "./DdaFreezeButton";
import { DdaGenerateButton } from "./DdaGenerateButton";
import { DdaStatsCard } from "./DdaStatsCard";

import type { DdaAdminEntry } from "@/lib/api/dda";

interface DdaAdminPanelProps {
  projectId: string;
}

const TAB_DEFS = [
  { id: "stats", label: "Estadísticas", icon: ListChecks },
  { id: "entries", label: "Medidas", icon: ClipboardCheck },
  { id: "catalog", label: "Catálogo Anexo II", icon: FileSpreadsheet },
  { id: "freeze", label: "Congelación", icon: Lock },
] as const;

type TabId = (typeof TAB_DEFS)[number]["id"];

export function DdaAdminPanel({ projectId }: DdaAdminPanelProps) {
  const { data: status, isLoading } = useDdaAdminStatus(projectId);
  const [activeTab, setActiveTab] = React.useState<TabId>("stats");
  const [detailEntry, setDetailEntry] = React.useState<DdaAdminEntry | null>(
    null,
  );
  const [detailOpen, setDetailOpen] = React.useState(false);

  const handleSelectEntry = (entry: DdaAdminEntry) => {
    setDetailEntry(entry);
    setDetailOpen(true);
  };

  const ddaExists = status?.exists ?? false;

  return (
    <div className="space-y-6 p-4 sm:p-6" data-testid="dda-admin-panel">
      <header className="space-y-1">
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <ClipboardCheck className="size-5 text-primary" />
          Declaración de Aplicabilidad (DdA)
        </h1>
        <p className="text-sm text-foreground/55">
          Gestión de las 73 medidas Anexo II ENS · RD 311/2022 · audit-ready
          ENAC.
        </p>
      </header>

      {!isLoading && !ddaExists ? (
        <Card data-testid="dda-empty-hero">
          <CardHeader>
            <CardTitle className="text-base">DdA aún no creada</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-foreground/70">
              La Declaración de Aplicabilidad (DdA · es decir el documento
              donde decides qué medidas ENS aplicas al sistema y cuáles no)
              todavía no existe para este proyecto. Genérala según la
              categoría del sistema · luego puedes editar el estado de cada
              medida desde la pestaña <em>Medidas</em>.
            </p>
            <DdaGenerateButton projectId={projectId} />
          </CardContent>
        </Card>
      ) : (
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
          <TabsList
            className="flex h-auto w-full flex-wrap justify-start gap-1 bg-transparent p-0"
            data-testid="dda-tabs-list"
          >
            {TAB_DEFS.map((tab) => {
              const Icon = tab.icon;
              return (
                <TabsTrigger
                  key={tab.id}
                  value={tab.id}
                  className="border border-input bg-card data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                  data-testid={`dda-tab-${tab.id}`}
                >
                  <Icon className="mr-1.5 size-3.5" />
                  {tab.label}
                </TabsTrigger>
              );
            })}
          </TabsList>

          <TabsContent value="stats" className="mt-6">
            <DdaStatsCard projectId={projectId} />
          </TabsContent>
          <TabsContent value="entries" className="mt-6">
            <DdaEntriesList
              projectId={projectId}
              onSelectEntry={handleSelectEntry}
            />
          </TabsContent>
          <TabsContent value="catalog" className="mt-6">
            <DdaCatalogView />
          </TabsContent>
          <TabsContent value="freeze" className="mt-6">
            <DdaFreezeButton projectId={projectId} />
          </TabsContent>
        </Tabs>
      )}

      <DdaEntryDetailModal
        entry={detailEntry}
        projectId={projectId}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />
    </div>
  );
}
