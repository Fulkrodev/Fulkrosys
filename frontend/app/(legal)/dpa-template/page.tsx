/**
 * /dpa-template · DPA Article 28 GDPR download page (atom 9.bis.3).
 *
 * Static landing page that explains what the DPA is and links to the
 * backend download endpoint. The DOCX itself is generated server-side
 * (see backend/app/motors/m_compliance/dpa_template.py).
 */
import { ArrowLeft, Download, FileText, ShieldCheck } from "lucide-react";
import Link from "next/link";

export const metadata = {
  title: "DPA · Plantilla Art. 28 RGPD · FULKRO",
};

const SECTIONS: Array<{ heading: string; body: string }> = [
  {
    heading: "Qué es este documento",
    body:
      "El Contrato de Encargo del Tratamiento (Data Processing Addendum) es el contrato exigido por el Artículo 28 del Reglamento (UE) 2016/679 entre el Cliente (responsable) y FULKRO (encargado). Regula cómo FULKRO trata los datos personales por cuenta del Cliente y articula las garantías de seguridad, sub-encargados, derechos de los interesados y notificación de incidentes.",
  },
  {
    heading: "Qué incluye la plantilla",
    body:
      "12 secciones alineadas al Artículo 28 RGPD (objeto, duración, naturaleza, datos tratados, obligaciones del encargado, sub-encargados, medidas de seguridad, derechos de los interesados, notificación de brechas, finalización del tratamiento, jurisdicción) y 3 anexos: lista de sub-encargados autorizados, medidas técnicas y organizativas (Anexo II SCC), y categorías de datos y operaciones.",
  },
  {
    heading: "Cómo firmarlo",
    body:
      "Descarga la plantilla, completa los campos del Cliente (nombre legal, CIF, domicilio social, DPO, fecha de firma) y devuélvenosla firmada. FULKRO la contra-firma y archiva la versión definitiva en MinIO con sellado horario. La firma queda registrada en la cuenta del Cliente.",
  },
];

export default function DPATemplatePage() {
  return (
    <div className="space-y-12">
      <header>
        <Link
          href="/trust"
          className="inline-flex items-center gap-1 text-sm text-fulkro-ink-600 hover:text-fulkro-ink-900"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Trust Center
        </Link>
        <div className="mt-3 flex items-center gap-3">
          <FileText className="h-7 w-7 text-fulkro-ink-700" />
          <h1 className="text-3xl font-semibold tracking-tight">
            DPA · Plantilla Artículo 28 RGPD
          </h1>
        </div>
        <p className="mt-3 max-w-2xl text-base text-fulkro-ink-700">
          Plantilla pre-firmable del contrato de encargo del tratamiento que
          FULKRO suscribe con cada cliente. Generada dinámicamente con los
          datos del responsable (FULKRO) ya cumplimentados.
        </p>
      </header>

      <section className="flex flex-col items-start gap-4 rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 text-emerald-700" />
          <div>
            <h2 className="text-lg font-semibold">Descargar plantilla DPA</h2>
            <p className="text-sm text-fulkro-ink-700">
              Formato Word (.docx) · versión 1.0 · 12 secciones + 3 anexos
            </p>
          </div>
        </div>
        <a
          href="/api/v1/legal/dpa-template/download"
          download
          className="btn-action inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold text-white"
        >
          <Download className="h-4 w-4" />
          Descargar DOCX
        </a>
      </section>

      <section>
        <dl className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {SECTIONS.map((s) => (
            <div key={s.heading} className="rounded-md border border-fulkro-ink-200 bg-white p-5">
              <dt className="text-base font-semibold text-fulkro-ink-900">{s.heading}</dt>
              <dd className="mt-2 text-sm text-fulkro-ink-700">{s.body}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="rounded-md border border-fulkro-ink-200 bg-white p-6">
        <h2 className="text-lg font-semibold">Anexos incluidos</h2>
        <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-fulkro-ink-700">
          <li>
            <strong>Anexo I</strong> · Sub-encargados autorizados.{" "}
            <Link href="/sub-processors" className="underline">
              Ver lista actualizada
            </Link>{" "}
            (Hetzner · Postmark · Anthropic + SCC · 360dialog · MinIO).
          </li>
          <li>
            <strong>Anexo II</strong> · Medidas técnicas y organizativas
            (Art. 32 RGPD): cifrado TLS 1.3 + RLS multi-tenant + 2FA TOTP
            + firma Ed25519 + backups cifrados + restore test mensual.
          </li>
          <li>
            <strong>Anexo III</strong> · Categorías de datos y operaciones de
            tratamiento (alineadas con el RoPA Art. 30).
          </li>
        </ul>
      </section>

      <section className="rounded-md border border-fulkro-ink-200 bg-fulkro-ink-50 p-6 text-sm text-fulkro-ink-700">
        <p>
          ¿Necesitas una versión adaptada con cláusulas adicionales (por
          ejemplo, sector financiero o sanitario)? Escribe a{" "}
          <a href="mailto:dpo@fulkro.es" className="underline hover:text-fulkro-ink-900">
            dpo@fulkro.es
          </a>{" "}
          y la negociamos.
        </p>
      </section>
    </div>
  );
}
