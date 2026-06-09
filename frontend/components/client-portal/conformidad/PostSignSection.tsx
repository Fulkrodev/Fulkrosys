"use client";

/**
 * PostSignSection · post-firma tier-aware response.
 *
 * SAN-E v3.MB-5.6.D · BASICA (distintivo + cert-id) vs MEDIA/ALTA (commitment summary).
 */
import { useEffect, useState } from "react";
import { Award, CheckCircle2, Download, Mail, Loader2 } from "lucide-react";

import {
  type PostSignatureResponse,
  getConformidadPostSignature,
} from "@/lib/api/conformidad";


interface Props {
  projectId: string;
}


export function PostSignSection({ projectId }: Props) {
  const [data, setData] = useState<PostSignatureResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await getConformidadPostSignature(projectId);
        if (!cancelled) setData(res);
      } catch {
        if (!cancelled) setError("Error cargando estado post-firma");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  if (loading) {
    return (
      <section className="rounded-lg border bg-card p-5 shadow-sm">
        <p className="flex items-center gap-2 text-sm text-[color:var(--fulkro-muted)]">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando estado de conformidad…
        </p>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="rounded-lg border bg-card p-5 shadow-sm">
        <p className="text-sm text-fulkro-danger">
          {error || "Sin datos post-firma disponibles"}
        </p>
      </section>
    );
  }

  if (data.declaration_type === "initial") {
    return (
      <section className="rounded-lg border-2 border-fulkro-success/30 bg-fulkro-success/5 p-5 shadow-sm">
        <h2 className="mb-3 flex items-center gap-2 text-xl font-semibold text-fulkro-success">
          <Award className="h-6 w-6" />
          Tu organización es conforme ENS BÁSICA
        </h2>

        <p className="mb-4 text-sm leading-relaxed text-[color:var(--fulkro-muted)]">
          {data.summary}
        </p>

        <div className="mb-4 rounded-md border bg-background p-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[color:var(--fulkro-muted)]">
            Distintivo de conformidad
          </p>
          <img
            src={data.distintivo_svg_url}
            alt="Distintivo conformidad ENS"
            className="h-40 w-auto"
          />
        </div>

        <div className="flex flex-wrap gap-3">
          <a
            href={data.declaration_docx_url}
            download
            className="inline-flex items-center gap-2 rounded-md border border-fulkro-primary-700 px-4 py-2 text-sm font-medium text-fulkro-primary-700 hover:bg-fulkro-primary-50"
          >
            <Download className="h-4 w-4" />
            Descargar declaración (.docx)
          </a>
          <a
            href={data.cert_id_url}
            className="inline-flex items-center gap-2 rounded-md border px-4 py-2 text-sm font-medium hover:bg-fulkro-ink-50"
          >
            Ver cert-id
          </a>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-lg border-2 border-fulkro-info/30 bg-fulkro-info/5 p-5 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-xl font-semibold text-fulkro-info">
        <CheckCircle2 className="h-6 w-6" />
        Compromiso firmado
      </h2>

      <p className="mb-4 text-sm leading-relaxed text-[color:var(--fulkro-muted)]">
        {data.next_step_summary}
      </p>

      <div className="mb-4 rounded-md border bg-background p-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[color:var(--fulkro-muted)]">
          Plazo estimado certificación formal
        </p>
        <p className="text-lg font-semibold text-[color:var(--fulkro-title)]">
          {data.next_step_eta_days_min}–{data.next_step_eta_days_max} días
        </p>
        <p className="mt-1 text-xs text-[color:var(--fulkro-muted)]">
          Firmaste el{" "}
          {new Date(data.commitment_signed_at).toLocaleString("es-ES")}
        </p>
      </div>

      <a
        href={`mailto:${data.contacto_marcos_email}`}
        className="inline-flex items-center gap-2 rounded-md border border-fulkro-primary-700 px-4 py-2 text-sm font-medium text-fulkro-primary-700 hover:bg-fulkro-primary-50"
      >
        <Mail className="h-4 w-4" />
        Contactar a Marcos
      </a>
    </section>
  );
}
