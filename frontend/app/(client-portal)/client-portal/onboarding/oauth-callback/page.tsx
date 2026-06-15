"use client";

import * as React from "react";
import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { oauthCallback } from "@/lib/client-onboarding/api";

type CallbackStatus = "processing" | "success" | "error";

function OAuthCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = React.useState<CallbackStatus>("processing");
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const ranRef = React.useRef(false);

  React.useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;

    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const errorParam = searchParams.get("error") ?? searchParams.get("error_description");
    const projectId = searchParams.get("project_id");
    const connectorType = searchParams.get("connector");

    if (errorParam) {
      setStatus("error");
      setErrorMsg(errorParam);
      return;
    }

    if (!code || !state || !projectId || !connectorType) {
      setStatus("error");
      setErrorMsg("Parámetros OAuth faltantes (code/state/project_id/connector)");
      return;
    }

    oauthCallback(projectId, connectorType, { code, state })
      .then(() => {
        setStatus("success");
        setTimeout(() => {
          router.push(
            `/client-portal/onboarding?connector=${connectorType}&connected=true`,
          );
        }, 1500);
      })
      .catch((err: unknown) => {
        setStatus("error");
        // §2.7 · no exponer el detalle crudo del backend al cliente (R29/R30-inv).
        // eslint-disable-next-line no-console
        console.error("OAuth callback error:", err);
        setErrorMsg("No se pudo completar la conexión con el proveedor.");
      });
  }, [searchParams, router]);

  return (
    <div className="mx-auto max-w-md p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {status === "processing" ? (
              <>
                <Loader2 className="size-5 animate-spin text-fulkro-primary-700" />
                Procesando autorización…
              </>
            ) : status === "success" ? (
              <>
                <CheckCircle2 className="size-5 text-fulkro-success" />
                Conectado correctamente
              </>
            ) : (
              <>
                <XCircle className="size-5 text-destructive" />
                Error en la autorización
              </>
            )}
          </CardTitle>
          <CardDescription>
            {status === "processing"
              ? "Estamos validando tu autorización con el proveedor."
              : status === "success"
                ? "Te llevamos de vuelta al portal en unos segundos…"
                : "No se pudo completar la conexión. Inténtalo de nuevo desde el portal."}
          </CardDescription>
        </CardHeader>
        {status === "error" && errorMsg ? (
          <CardContent className="space-y-3">
            <p className="text-sm text-fulkro-ink-500">{errorMsg}</p>
            <Button
              variant="primary"
              onClick={() => router.push("/client-portal/onboarding")}
            >
              Volver al portal
            </Button>
          </CardContent>
        ) : null}
      </Card>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 className="size-4 animate-spin" />
          Cargando…
        </div>
      }
    >
      <OAuthCallbackInner />
    </Suspense>
  );
}
