"use client";

/**
 * TransparencyLogCard · sub-atom 1.E.1.B.2.
 *
 * AI Act art.50 transparency log cliente-facing · R29 firmísimo:
 *   - NO presión · NO destructive · NO red default
 *   - Friendly explainer + empty state celebrativo
 *   - NO leak technical fields (llm_provider/llm_model/metadata)
 *
 * Endpoint: /api/v1/client-portal/transparency/log
 */
import { useClientTransparencyLog } from "@/hooks/useClientTransparencyLog";
import { EVENT_TYPE_LABEL } from "@/lib/api/transparency-client";

function formatRelativeDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export function TransparencyLogCard({ days = 180 }: { days?: number }) {
  const { loading, error, items, total } = useClientTransparencyLog(days);

  return (
    <section
      data-testid="transparency-log-card"
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
    >
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Transparencia IA · AI Act art.50
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Aquí puedes ver cuándo se utilizó inteligencia artificial para
          ayudar a generar documentos o realizar análisis en tu proyecto.
          Cumplimos transparencia europea por defecto.
        </p>
      </header>

      {loading && (
        <p
          className="text-sm text-slate-500"
          data-testid="transparency-loading"
        >
          Cargando registro…
        </p>
      )}

      {error && !loading && (
        <p
          className="text-sm text-amber-700"
          data-testid="transparency-error"
        >
          {error}
        </p>
      )}

      {!loading && !error && total === 0 && (
        <p
          className="rounded-md bg-slate-50 p-4 text-sm text-slate-600"
          data-testid="transparency-empty"
        >
          Aún no se ha utilizado IA en este proyecto. Cuando se haga, cada
          uso aparecerá aquí con su propósito explicado.
        </p>
      )}

      {!loading && !error && total > 0 && (
        <div
          className="overflow-x-auto rounded-md border border-slate-100"
          data-testid="transparency-list"
        >
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Fecha</th>
                <th className="px-4 py-2">Acción</th>
                <th className="px-4 py-2">Asistente</th>
                <th className="px-4 py-2">Propósito</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {items.map((item) => (
                <tr
                  key={item.id}
                  data-testid={`transparency-row-${item.id}`}
                >
                  <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                    {formatRelativeDate(item.created_at)}
                  </td>
                  <td className="px-4 py-3 text-slate-900">
                    {EVENT_TYPE_LABEL[item.event_type] ?? item.event_type}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                    {item.agent_name}
                  </td>
                  <td className="px-4 py-3 text-slate-700">{item.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
