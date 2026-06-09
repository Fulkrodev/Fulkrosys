"use client";

/**
 * /client-portal/registros · REDIRECT a /client-portal/tasks · sub-atom 1.D.F.bis.III.B v3.11.
 *
 * Modelo "indispensable-cliente-only":
 *   - Cliente NO gestiona registros vivos directamente (admin Marcos opera M_live_records)
 *   - Cliente aporta info via tasks específicas cuando Marcos solicita
 *   - Backward compat: redirect server-side a /tasks · UI explicativa transitoria
 *
 * Para acceso admin a 26 register_types ver /admin/projects/[id]/registros (admin owns).
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, BookOpenCheck, Loader2 } from "lucide-react";
import Link from "next/link";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";

export default function RegistrosRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    const t = setTimeout(() => {
      router.replace("/client-portal/tasks");
    }, 2500);
    return () => clearTimeout(t);
  }, [router]);

  return (
    <main
      className="mx-auto max-w-2xl px-4 py-12 sm:px-6 space-y-6"
      data-testid="cliente-registros-redirect"
    >
      <header className="space-y-2 text-center">
        <BookOpenCheck className="size-12 mx-auto text-primary" />
        <h1 className="text-xl font-semibold">Los registros los lleva tu consultor</h1>
        <p className="text-sm text-foreground/70">
          Marcos gestiona los registros vivos del proyecto (incidentes,
          formación, revisiones…). Cuando necesite información tuya te lo
          pedirá en &quot;Mis tareas&quot;.
        </p>
      </header>
      <Alert>
        <AlertTitle>Te llevamos a tus tareas</AlertTitle>
        <AlertDescription className="flex items-center gap-2 mt-2">
          <Loader2 className="size-4 animate-spin" />
          Redirigiendo a <code>/client-portal/tasks</code>…
        </AlertDescription>
      </Alert>
      <Card>
        <CardContent className="py-4 flex justify-center">
          <Link
            href="/client-portal/tasks"
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
            data-testid="cliente-registros-redirect-link"
          >
            Ir a mis tareas <ArrowRight className="size-3.5" />
          </Link>
        </CardContent>
      </Card>
    </main>
  );
}
