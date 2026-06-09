"use client";

/**
 * AuditorPortalEntry · token validation gate + session start emit.
 *
 * Sesión 3B-2B.6 CLUSTER 2 Phase 4 · landing wrapper para /(portal)/auditor-portal/[token]/*.
 *
 * Flow:
 * 1. Fetch GET /api/v1/public/auditor-portal/{token} (peek · NO consume use)
 * 2. Si 403 invalid OR 410 expired/revoked · render error fallback
 * 3. Si OK · render AuditorPortalChrome con children section
 * 4. On first mount · POST /api/v1/public/auditor-portal/{token}/session
 *    (consume 1 use · emit auditor.session.start hash chain immutable)
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2 } from "lucide-react";
import * as React from "react";

import { AuditorPortalChrome } from "@/components/auditor-portal/AuditorPortalChrome";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  getAuditorPortalMetadata,
  startAuditorPortalSession,
  type AuditorPortalMetadata,
} from "@/lib/api/auditor-portal";

interface Props {
  token: string;
  children: React.ReactNode;
}

export function AuditorPortalEntry({ token, children }: Props) {
  const meta = useQuery<AuditorPortalMetadata>({
    queryKey: ["auditor-portal", "metadata", token],
    queryFn: () => getAuditorPortalMetadata(token),
    enabled: Boolean(token),
    staleTime: 60_000,
    retry: false,
  });

  const sessionMut = useMutation({
    mutationFn: () => startAuditorPortalSession(token),
  });
  const sessionStartedRef = React.useRef(false);

  React.useEffect(() => {
    if (
      meta.data &&
      !sessionStartedRef.current &&
      !sessionMut.isPending &&
      !sessionMut.isSuccess
    ) {
      sessionStartedRef.current = true;
      sessionMut.mutate();
    }
  }, [meta.data, sessionMut]);

  if (meta.isLoading) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50">
        <div className="flex items-center gap-2 text-sm text-fulkro-ink-500">
          <Loader2 size={16} className="animate-spin" aria-hidden="true" />
          Validando acceso al portal del auditor…
        </div>
      </div>
    );
  }

  if (meta.isError || !meta.data) {
    const errMsg = meta.error instanceof Error ? meta.error.message : "Error desconocido";
    return (
      <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50 px-4">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle size={16} className="text-fulkro-danger-700" />
              Acceso no disponible
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <Alert variant="danger">
              <AlertTitle>Enlace inválido, revocado o expirado</AlertTitle>
              <AlertDescription>
                Si has llegado aquí desde un enlace recibido por correo,
                puede haber expirado o haberse revocado. Solicita un enlace
                nuevo al consultor responsable.
              </AlertDescription>
            </Alert>
            <p className="text-[11px] text-fulkro-ink-500">
              Detalle técnico: {errMsg}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <AuditorPortalChrome token={token} metadata={meta.data}>
      {children}
    </AuditorPortalChrome>
  );
}
