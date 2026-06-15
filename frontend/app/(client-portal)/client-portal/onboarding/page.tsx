"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";

import { PageContainer } from "@/components/layout/PageContainer";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ClientApiError, clientApi } from "@/lib/client-portal-api";

import { CloudConnectFirstStep } from "@/components/client-portal/CloudConnectFirstStep";
import { ConnectorsClientView } from "@/components/client-portal/ConnectorsClientView";
import { LMSClientView } from "@/components/client-portal/LMSClientView";
import { OnboardingClientFlow } from "@/components/client-portal/OnboardingClientFlow";

interface ClientProjectResponse {
  id?: string;
  nombre?: string;
  estado?: string;
}

type ResolveStatus = "loading" | "ready" | "no-project" | "error";

export default function ClientOnboardingPage() {
  const [status, setStatus] = React.useState<ResolveStatus>("loading");
  const [projectId, setProjectId] = React.useState<string | null>(null);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const [tab, setTab] = React.useState<
    "connect" | "wizard" | "connectors" | "lms"
  >("connect");

  React.useEffect(() => {
    let cancelled = false;
    clientApi<ClientProjectResponse>("/client-portal/project")
      .then((res) => {
        if (cancelled) return;
        if (!res.id) {
          setStatus("no-project");
          return;
        }
        setProjectId(res.id);
        setStatus("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ClientApiError && err.status === 404) {
          setStatus("no-project");
          return;
        }
        setStatus("error");
        setErrorMsg(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === "loading") {
    return (
      <PageContainer variant="reading">
        <div className="flex items-center gap-2 text-sm text-fulkro-ink-500">
          <Loader2 className="size-4 animate-spin" />
          Cargando proyecto…
        </div>
      </PageContainer>
    );
  }

  if (status === "error") {
    return (
      <PageContainer variant="reading">
        <Card>
          <CardHeader>
            <CardTitle>No se pudo cargar el proyecto</CardTitle>
            <CardDescription>
              {errorMsg ?? "Inténtalo de nuevo más tarde."}
            </CardDescription>
          </CardHeader>
        </Card>
      </PageContainer>
    );
  }

  if (status === "no-project" || !projectId) {
    return (
      <PageContainer variant="reading">
        <Card>
          <CardHeader>
            <CardTitle>Sin proyecto activo</CardTitle>
            <CardDescription>
              Aún no tienes un proyecto asignado. Marcos te avisará cuando esté listo.
            </CardDescription>
          </CardHeader>
        </Card>
      </PageContainer>
    );
  }

  return (
    <PageContainer variant="reading">
      <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-xl font-semibold text-fulkro-primary-700">Onboarding</h1>
        <p className="text-sm text-fulkro-ink-500">
          Empieza conectando tus sistemas (5 min · solo lectura) · luego responde
          el wizard adaptativo y completa los cursos asignados.
        </p>
      </header>

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList>
          <TabsTrigger value="connect">Conecta sistemas</TabsTrigger>
          <TabsTrigger value="wizard">Wizard</TabsTrigger>
          <TabsTrigger value="connectors">Connectors</TabsTrigger>
          <TabsTrigger value="lms">Cursos</TabsTrigger>
        </TabsList>
        <TabsContent value="connect" className="mt-4">
          <CloudConnectFirstStep
            projectId={projectId}
            onSkip={() => setTab("wizard")}
          />
        </TabsContent>
        <TabsContent value="wizard" className="mt-4">
          <OnboardingClientFlow
            projectId={projectId}
            onOpenConnectors={() => setTab("connectors")}
            onOpenLMS={() => setTab("lms")}
          />
        </TabsContent>
        <TabsContent value="connectors" className="mt-4">
          <ConnectorsClientView projectId={projectId} />
        </TabsContent>
        <TabsContent value="lms" className="mt-4">
          <LMSClientView projectId={projectId} />
        </TabsContent>
      </Tabs>
      </div>
    </PageContainer>
  );
}
