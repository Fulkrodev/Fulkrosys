"use client";

/**
 * /client-portal/retainer · Oferta de retainer post-certificación (defecto P0).
 *
 * El cliente, una vez certificado su ENS, ve aquí la oferta de mantenimiento
 * (retainer) y la acepta/rechaza in-portal (sesión cookie · NO magic-link).
 * R29 friendly · congrats tone · "sin prisa por tu parte".
 *
 * Distinto de /client-portal/retainer-checkin (revisión trimestral del retainer
 * ya activo). Aquí es la oferta INICIAL pre-activación (lifecycle CERTIFIED).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  getRetainerOffer,
  submitRetainerDecision,
  type RetainerDecision,
} from "@/lib/api/retainer-offer";

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("es-ES", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function RetainerOfferPage() {
  const qc = useQueryClient();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["retainer-offer"],
    queryFn: getRetainerOffer,
    retry: false,
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [done, setDone] = useState<RetainerDecision | null>(null);

  const decide = useMutation({
    mutationFn: (vars: { decision: RetainerDecision; tier?: string }) =>
      submitRetainerDecision(data!.project_id, vars),
    onSuccess: (_r, vars) => {
      setDone(vars.decision);
      void qc.invalidateQueries({ queryKey: ["retainer-offer"] });
    },
  });

  if (isLoading) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-16 text-center text-fulkro-muted">
        Cargando tu oferta de mantenimiento…
      </main>
    );
  }

  if (isError || !data) {
    return (
      <main
        className="mx-auto max-w-2xl px-6 py-16 text-center space-y-3"
        data-testid="retainer-offer-empty"
      >
        <p className="text-3xl">🔒</p>
        <h1 className="text-xl font-bold">Aún no hay oferta de mantenimiento</h1>
        <p className="text-fulkro-muted">
          Cuando tu certificación ENS esté completa, aquí verás la propuesta de
          retainer. Sin prisa por tu parte.
        </p>
        <a
          href="/client-portal/dashboard"
          className="inline-block mt-2 text-fulkro-accent underline-offset-2 hover:underline"
        >
          Volver al panel
        </a>
      </main>
    );
  }

  const activated = done === "accept" || data.lifecycle_state === "RETAINER";

  if (activated) {
    return (
      <main
        className="mx-auto max-w-2xl px-6 py-16 text-center space-y-3"
        data-testid="retainer-offer-accepted"
      >
        <p className="text-4xl">🎉</p>
        <h1 className="text-2xl font-bold">¡Mantenimiento activado!</h1>
        <p className="text-fulkro-muted">
          Gracias por confiar en Fulkro para el mantenimiento continuo de tu ENS.
          Te avisaremos del primer comité trimestral.
        </p>
        <a
          href="/client-portal/retainer-checkin"
          className="inline-block mt-2 text-fulkro-accent underline-offset-2 hover:underline"
        >
          Ver el seguimiento del retainer
        </a>
      </main>
    );
  }

  return (
    <main
      className="mx-auto max-w-5xl px-6 py-10 space-y-8"
      data-testid="retainer-offer-page"
    >
      <header className="space-y-2 text-center">
        <p className="text-3xl">🛡️</p>
        <h1 className="text-2xl font-bold">
          ¡Enhorabuena! {data.project_name} está certificado
        </h1>
        {data.certified_at && (
          <p className="text-sm text-fulkro-muted">
            Certificación ENS {data.categoria ?? ""} ·{" "}
            {fmtDate(data.certified_at)}
          </p>
        )}
        <p className="mx-auto max-w-2xl text-fulkro-body">
          El ENS no es un trámite de una vez: hay que mantenerlo vivo (revisiones,
          evidencias al día, próxima renovación). Elige el plan de mantenimiento
          que mejor encaje. Sin prisa por tu parte.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {data.tiers.map((t) => {
          const isSel = selected === t.tier_code;
          return (
            <button
              key={t.tier_code}
              type="button"
              onClick={() => setSelected(t.tier_code)}
              data-testid={`retainer-tier-${t.tier_code}`}
              data-recommended={t.recommended ? "1" : "0"}
              className={`flex flex-col gap-2 rounded-2xl border bg-white p-5 text-left transition ${
                isSel
                  ? "border-fulkro-accent ring-2 ring-fulkro-accent"
                  : "border-fulkro-surface-glass-border hover:border-fulkro-accent/60"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-base font-bold">{t.label}</span>
                {t.recommended && (
                  <span className="rounded-full bg-fulkro-accent/10 px-2 py-0.5 text-xs font-semibold text-fulkro-accent">
                    ★ Recomendado
                  </span>
                )}
              </div>
              <div className="text-2xl font-extrabold">
                {t.precio_mensual.toLocaleString("es-ES")}€
                <span className="text-sm font-medium text-fulkro-muted">
                  {" "}
                  / mes
                </span>
              </div>
              <p className="text-sm text-fulkro-muted">{t.sla}</p>
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
        <button
          type="button"
          disabled={!selected || decide.isPending}
          onClick={() =>
            selected && decide.mutate({ decision: "accept", tier: selected })
          }
          data-testid="retainer-accept"
          className="rounded-xl bg-fulkro-accent px-6 py-3 font-semibold text-white disabled:opacity-50"
        >
          {decide.isPending
            ? "Activando…"
            : selected
              ? `Aceptar mantenimiento (${selected})`
              : "Elige un plan arriba"}
        </button>
        <button
          type="button"
          disabled={decide.isPending}
          onClick={() => decide.mutate({ decision: "thinking" })}
          data-testid="retainer-thinking"
          className="rounded-xl border border-fulkro-surface-glass-border px-5 py-3 font-medium text-fulkro-body"
        >
          Me lo pienso
        </button>
        <button
          type="button"
          disabled={decide.isPending}
          onClick={() => decide.mutate({ decision: "decline" })}
          data-testid="retainer-decline"
          className="rounded-xl px-4 py-3 text-sm text-fulkro-muted hover:underline"
        >
          De momento no
        </button>
      </div>

      {decide.isError && (
        <p className="text-center text-sm text-red-600">
          No se ha podido registrar tu decisión. Inténtalo de nuevo en unos
          segundos.
        </p>
      )}
    </main>
  );
}
