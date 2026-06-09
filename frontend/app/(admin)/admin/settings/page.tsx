"use client";

import { RefreshCw } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { useAdminSettings } from "@/lib/admin-settings/hooks";

import { AboutTab } from "./_components/AboutTab";
import { BrandingTab } from "./_components/BrandingTab";
import { FiscalTab } from "./_components/FiscalTab";
import { GeneralTab } from "./_components/GeneralTab";
import { NotificationsTab } from "./_components/NotificationsTab";
import { PricingTab } from "./_components/PricingTab";
import { SmtpTab } from "./_components/SmtpTab";

export default function SettingsPage() {
  const { data, loading, error, updateSection, refetch } = useAdminSettings();

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-3xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
          Ajustes
        </h1>
        <p className="mt-1 text-base font-medium text-[color:var(--fulkro-muted)]">
          Configuración del panel: branding, notificaciones, SMTP,
          datos fiscales, preferencias generales e info del sistema.
        </p>
      </header>

      {loading && (
        <div className="flex flex-col gap-3" aria-busy>
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {/* Sub-atom Sesión 3B-2B Phase B · error retry button consistent pattern. */}
      {error && (
        <Alert variant="danger" className="flex flex-col gap-3">
          <div>
            <AlertTitle>No se pudieron cargar los ajustes</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void refetch()}
            className="self-start"
            data-testid="settings-page-retry"
          >
            <RefreshCw size={14} />
            Reintentar
          </Button>
        </Alert>
      )}

      {data && !loading && (
        <Tabs defaultValue="branding" className="w-full">
          <TabsList className="grid w-full grid-cols-7">
            <TabsTrigger value="branding">Branding</TabsTrigger>
            <TabsTrigger value="notifications">Notificaciones</TabsTrigger>
            <TabsTrigger value="smtp">SMTP</TabsTrigger>
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="fiscal">Fiscal</TabsTrigger>
            <TabsTrigger value="pricing">Precios</TabsTrigger>
            <TabsTrigger value="about">Acerca</TabsTrigger>
          </TabsList>

          <TabsContent value="branding" className="mt-6">
            <BrandingTab
              branding={data.branding}
              onUpdate={(payload) => updateSection("branding", payload)}
              onLogoUploaded={() => {
                void refetch();
              }}
            />
          </TabsContent>
          <TabsContent value="notifications" className="mt-6">
            <NotificationsTab
              notifications={data.notifications}
              onUpdate={(payload) => updateSection("notifications", payload)}
            />
          </TabsContent>
          <TabsContent value="smtp" className="mt-6">
            <SmtpTab
              smtp={data.smtp}
              onUpdate={(payload) => updateSection("smtp", payload)}
            />
          </TabsContent>
          <TabsContent value="general" className="mt-6">
            <GeneralTab
              general={data.general}
              onUpdate={(payload) => updateSection("general", payload)}
            />
          </TabsContent>
          <TabsContent value="fiscal" className="mt-6">
            <FiscalTab
              fiscal={data.fiscal}
              onUpdate={(payload) => updateSection("fiscal", payload)}
            />
          </TabsContent>
          <TabsContent value="pricing" className="mt-6">
            <PricingTab />
          </TabsContent>
          <TabsContent value="about" className="mt-6">
            <AboutTab
              analyticsPrefs={data.analytics_prefs}
              onUpdateAnalyticsPrefs={(payload) =>
                updateSection("analytics_prefs", payload)
              }
            />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
