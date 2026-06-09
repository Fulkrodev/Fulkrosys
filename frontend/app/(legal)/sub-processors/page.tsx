"use client";

/**
 * /sub-processors · FULKRO Sub-processor transparency page (atom 9.bis.5).
 *
 * Lists every sub-processor declared in the chain plus their data
 * location, GDPR mechanism, DPA status, and purpose. Includes an opt-in
 * email subscription to receive notifications when the list changes
 * (Art. 28.2 RGPD obligation).
 *
 * Static sub-processor data comes from `lib/legal/schemas.SUB_PROCESSORS`,
 * which mirrors `docs/compliance/06-Sub_Processors/sub_processors.md`
 * (the source of truth published in atom 9.bis.4).
 */
import { useMutation } from "@tanstack/react-query";
import { ExternalLink, Mail, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { subscribeSubProcessorUpdates } from "@/lib/legal/api";
import { SUB_PROCESSORS } from "@/lib/legal/schemas";

export default function SubProcessorsPage() {
  return (
    <div className="space-y-12">
      <section>
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-7 w-7 text-fulkro-ink-700" />
          <h1 className="text-3xl font-semibold tracking-tight">
            Sub-procesadores
          </h1>
        </div>
        <p className="mt-3 max-w-3xl text-base text-fulkro-ink-700">
          Conforme al Art. 28.2 del Reglamento (UE) 2016/679 (RGPD), FULKRO
          informa de los sub-procesadores autorizados que intervienen en el
          tratamiento de datos de los clientes. La lista se mantiene en
          sincronía con la documentación oficial en{" "}
          <code className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 text-xs">
            docs/compliance/06-Sub_Processors
          </code>
          .
        </p>
      </section>

      {/* Table */}
      <section className="overflow-hidden rounded-md border border-fulkro-ink-200">
        <table className="w-full text-sm">
          <thead className="bg-fulkro-ink-50">
            <tr className="text-left text-xs uppercase tracking-wide text-fulkro-ink-600">
              <th className="px-4 py-3">Proveedor</th>
              <th className="px-4 py-3">Servicio</th>
              <th className="px-4 py-3">Ubicación de datos</th>
              <th className="px-4 py-3">Mecanismo GDPR</th>
              <th className="px-4 py-3">DPA</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-fulkro-ink-200 bg-white">
            {SUB_PROCESSORS.map((p) => (
              <tr key={p.slug} className="align-top">
                <td className="px-4 py-3">
                  <div className="font-medium">{p.name}</div>
                  {p.privacy_url ? (
                    <a
                      href={p.privacy_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-flex items-center gap-1 text-xs text-fulkro-ink-600 hover:underline"
                    >
                      Política de privacidad
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : null}
                </td>
                <td className="px-4 py-3 text-fulkro-ink-700">{p.service_es}</td>
                <td className="px-4 py-3 text-fulkro-ink-700">{p.data_location}</td>
                <td className="px-4 py-3 text-fulkro-ink-700">{p.gdpr_mechanism}</td>
                <td className="px-4 py-3">
                  <Badge
                    variant={
                      p.dpa_status === "vigente"
                        ? "success"
                        : p.dpa_status === "no-aplica"
                          ? "outline"
                          : "warning"
                    }
                  >
                    {p.dpa_status === "vigente"
                      ? "Vigente"
                      : p.dpa_status === "no-aplica"
                        ? "No aplica"
                        : "Pendiente"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* Purpose details */}
      <section>
        <h2 className="text-xl font-semibold">Finalidad por proveedor</h2>
        <dl className="mt-4 space-y-4">
          {SUB_PROCESSORS.map((p) => (
            <div
              key={p.slug}
              className="rounded-md border border-fulkro-ink-200 bg-white p-4"
            >
              <dt className="text-sm font-medium">{p.name}</dt>
              <dd className="mt-1 text-sm text-fulkro-ink-700">{p.purpose_es}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* Subscribe to updates */}
      <SubscribeForm />

      {/* Footer note */}
      <section className="rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-6 text-sm text-fulkro-ink-700">
        <p>
          ¿Preguntas sobre la cadena de procesamiento? Escribe a{" "}
          <a
            href="mailto:dpo@fulkro.es"
            className="underline hover:text-fulkro-ink-900"
          >
            dpo@fulkro.es
          </a>{" "}
          o vuelve al{" "}
          <Link href="/trust" className="underline hover:text-fulkro-ink-900">
            Trust Center
          </Link>
          .
        </p>
      </section>
    </div>
  );
}

function SubscribeForm() {
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => subscribeSubProcessorUpdates(email.trim().toLowerCase(), consent),
    onSuccess: (res) => {
      setSuccess(res.message);
      setEmail("");
      setConsent(false);
    },
  });

  const error = mutation.error instanceof ApiError ? mutation.error.message : null;

  return (
    <section className="rounded-md border border-fulkro-ink-200 bg-white p-6">
      <div className="flex items-start gap-3">
        <Mail className="mt-0.5 h-5 w-5 text-fulkro-ink-700" />
        <div>
          <h2 className="text-lg font-semibold">
            Recibir notificación de cambios
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-fulkro-ink-700">
            Suscríbete para recibir un email cuando esta lista de
            sub-procesadores cambie. Esta notificación cumple la obligación
            de transparencia del Art. 28.2 RGPD para los responsables de
            tratamiento que delegan en FULKRO.
          </p>
        </div>
      </div>
      <form
        className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start"
        onSubmit={(e) => {
          e.preventDefault();
          if (!email.trim() || !consent) return;
          setSuccess(null);
          mutation.mutate();
        }}
      >
        <Input
          type="email"
          placeholder="tu-email@empresa.com"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="sm:max-w-sm"
        />
        <Button
          type="submit"
          variant="primary"
          disabled={!email.trim() || !consent || mutation.isPending}
        >
          {mutation.isPending ? "Suscribiendo…" : "Suscribirme"}
        </Button>
      </form>
      <label className="mt-3 flex cursor-pointer items-start gap-2 text-xs text-fulkro-ink-700">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5"
        />
        <span>
          Acepto recibir, por correo electrónico, notificaciones sobre cambios
          en la lista de sub-procesadores. Puedo darme de baja en cualquier
          momento desde el enlace incluido en cada email. Los datos se
          tratarán conforme a nuestra{" "}
          <Link href="/privacy" className="underline">
            política de privacidad
          </Link>
          .
        </span>
      </label>
      {success ? (
        <p className="mt-3 text-sm text-emerald-700">{success}</p>
      ) : null}
      {error ? (
        <p className="mt-3 text-sm text-red-700">{error}</p>
      ) : null}
    </section>
  );
}
