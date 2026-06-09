/**
 * Página 403 forbidden — mostrada vía rewrite del middleware cuando
 * role/capability falla en zona protegida.
 *
 * AuthGuard client-side (SUB-FASE 3.D) puede mostrar variante inline
 * dentro del layout admin para casos pre-hydration o sin JS,
 * pero esta página es la fuente de verdad server-side.
 */
import Link from "next/link";
import { Suspense } from "react";

const REASON_MESSAGES: Record<string, string> = {
  role: "Tu rol no tiene acceso a esta zona.",
  capability: "No tienes la capacidad necesaria para esta zona.",
};

function ForbiddenContent({
  searchParams,
}: {
  searchParams: { reason?: string };
}) {
  const reason = searchParams.reason;
  const message =
    (reason && REASON_MESSAGES[reason]) || "Acceso restringido.";

  return (
    <div className="flex min-h-dvh items-center justify-center bg-fulkro-ink-50 px-6">
      <div className="max-w-md space-y-4 text-center">
        <h1 className="text-4xl font-semibold text-fulkro-ink-900">403</h1>
        <p className="text-lg text-fulkro-ink-700">{message}</p>
        <div className="pt-4">
          <Link
            href="/"
            className="text-fulkro-primary-600 hover:underline focus-visible:underline"
          >
            Volver al inicio
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function ForbiddenPage({
  searchParams,
}: {
  searchParams: { reason?: string };
}) {
  return (
    <Suspense fallback={<div />}>
      <ForbiddenContent searchParams={searchParams} />
    </Suspense>
  );
}
