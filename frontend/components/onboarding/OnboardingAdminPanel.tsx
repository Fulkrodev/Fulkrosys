"use client";

import * as React from "react";
import {
  Cloud,
  GraduationCap,
  ListTree,
  Sparkles,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import {
  useLMSProgress,
  useProjectConnectors,
  useProjectSessions,
} from "@/hooks/useOnboardingAdmin";

import { ConnectorsAdminPanel } from "./ConnectorsAdminPanel";
import { LMSPanel } from "./LMSPanel";
import { SessionsList } from "./SessionsList";
import { TemplateCatalogViewer } from "./TemplateCatalogViewer";

export interface OnboardingAdminPanelProps {
  projectId: string;
}

const TAB_DEFS = [
  { id: "sessions", label: "Sessions", icon: Sparkles },
  { id: "catalog", label: "Catálogo", icon: ListTree },
  { id: "connectors", label: "Connectors", icon: Cloud },
  { id: "lms", label: "LMS", icon: GraduationCap },
] as const;

type TabId = (typeof TAB_DEFS)[number]["id"];

export function OnboardingAdminPanel({ projectId }: OnboardingAdminPanelProps) {
  const [activeTab, setActiveTab] = React.useState<TabId>("sessions");
  const { data: sessions = [] } = useProjectSessions(projectId);
  const { data: connectors = [] } = useProjectConnectors(projectId);
  const { data: progress } = useLMSProgress(projectId);

  const activeSession = sessions.find(
    (s) => s.state === "in_progress" || s.state === "sent",
  );
  const completedSessions = sessions.filter((s) => s.state === "completed").length;

  return (
    <div className="space-y-6 p-4 sm:p-6">
      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-fulkro-primary-700">
              Onboarding adaptativo
            </h1>
            <p className="text-sm text-fulkro-ink-500">
              Catálogo de plantillas · sessions · connectors · LMS para el proyecto.{" "}
              <TooltipENS term="branching_logic" />
            </p>
          </div>
          {activeSession ? (
            <Badge variant="info">
              Session activa · {activeSession.progress_percentage.toFixed(0)}%
            </Badge>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="secondary">
            <Sparkles className="mr-1 size-3" /> {sessions.length} sessions
          </Badge>
          <Badge variant="success">{completedSessions} completadas</Badge>
          <Badge variant="info">
            <Cloud className="mr-1 size-3" /> {connectors.length}/6 connectors
          </Badge>
          {progress ? (
            <Badge variant="info">
              <GraduationCap className="mr-1 size-3" />
              {progress.por_estado.completed ?? 0}/{progress.total_assignments} LMS
            </Badge>
          ) : null}
        </div>
      </header>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)}>
        <TabsList className="flex h-auto w-full flex-wrap justify-start gap-1 bg-transparent p-0">
          {TAB_DEFS.map((tab) => {
            const Icon = tab.icon;
            return (
              <TabsTrigger
                key={tab.id}
                value={tab.id}
                className={cn(
                  "data-[state=active]:bg-fulkro-primary-700 data-[state=active]:text-white",
                  "border border-fulkro-ink-100 bg-white",
                )}
              >
                <Icon className="mr-1.5 size-3.5" />
                {tab.label}
              </TabsTrigger>
            );
          })}
        </TabsList>

        <TabsContent value="sessions" className="mt-6">
          <SessionsList projectId={projectId} />
        </TabsContent>
        <TabsContent value="catalog" className="mt-6">
          <TemplateCatalogViewer />
        </TabsContent>
        <TabsContent value="connectors" className="mt-6">
          <ConnectorsAdminPanel projectId={projectId} />
        </TabsContent>
        <TabsContent value="lms" className="mt-6">
          <LMSPanel projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
