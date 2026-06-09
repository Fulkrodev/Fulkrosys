/**
 * TokenScaffold · placeholder UI compartido para 5 rutas magic link cuya
 * implementación real se difiere a FASE 9 (Frontend v0.2).
 *
 * Rutas que lo consumen (todas en (public)/):
 *   - /meeting/[token]    → invitacion_reunion (#24)
 *   - /incident/[token]   → comunicacion_incidente_seguridad (#30)
 *   - /download/[token]   → descarga_certificado_conformidad (#33)
 *   - /vote/[token]       → votacion_comite_seguridad (#34)
 *   - /nps/[token]        → encuesta_satisfaccion_nps (#35)
 *
 * Comportamiento:
 *   1. Resuelve el token contra el backend (useMagicLinkStatus).
 *   2. Si el purpose del link no coincide con expectedPurpose, muestra un
 *      Alert de "purpose mismatch" (token genuino pero abierto en ruta
 *      equivocada).
 *   3. Si el link no existe / expiró / fue revocado, muestra un Alert
 *      "Enlace inválido o caducado".
 *   4. Si todo OK, renderiza el placeholder "Funcionalidad en preparación".
 *
 * Future: backlog ID FASE-9-MAGIC-LINK-FRONTEND-ROUTES-001 ·
 * Future: implement real flow in FASE 9 (Frontend v0.2).
 */
"use client";

import { CalendarClock, Loader2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useMagicLinkStatus } from "@/hooks/magic-link";
import {
  isMagicLinkActive,
  type MagicLinkBackendPurpose,
} from "@/lib/magic-link-types";

interface TokenScaffoldProps {
  token: string;
  expectedPurpose: MagicLinkBackendPurpose;
  title: string;
  description: string;
}

export function TokenScaffold({
  token,
  expectedPurpose,
  title,
  description,
}: TokenScaffoldProps) {
  const { data: status, isLoading, isError } = useMagicLinkStatus(token);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
          <Loader2 size={14} className="animate-spin" /> validando enlace…
        </CardContent>
      </Card>
    );
  }

  if (isError || !status) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="warning">
            <AlertTitle>Enlace no disponible</AlertTitle>
            <AlertDescription>
              Este enlace no es válido o ha caducado. Si necesita avanzar,
              contacte con su responsable del proyecto para que le envíe un
              nuevo enlace.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (status.tipo_operacion !== expectedPurpose) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="info">
            <AlertTitle>Enlace de otra funcionalidad</AlertTitle>
            <AlertDescription>
              Este enlace corresponde a una operación distinta. Compruebe el
              email original o contacte con su responsable del proyecto.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!isMagicLinkActive(status)) {
    return (
      <Card>
        <CardContent className="p-6">
          <Alert variant="warning">
            <AlertTitle>Enlace caducado o revocado</AlertTitle>
            <AlertDescription>
              Este enlace ya no está disponible. Solicite uno nuevo a su
              responsable del proyecto.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CalendarClock size={16} /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-fulkro-ink-700">{description}</p>
        <Alert variant="info">
          <AlertTitle>Funcionalidad en preparación</AlertTitle>
          <AlertDescription>
            Esta funcionalidad estará disponible próximamente. Si necesita
            avanzar antes, contacte con su responsable del proyecto.
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
}
