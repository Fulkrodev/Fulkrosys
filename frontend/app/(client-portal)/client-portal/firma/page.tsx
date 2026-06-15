/**
 * /client-portal/firma — "Cómo funciona la firma electrónica de FULKRO"
 * (sub-bloque 10.B).
 *
 * Página explicativa requerida por ADR-010 punto 2 + plantilla M06
 * cláusula 14 C-001 que cita la URL literal `/client-portal/firma`.
 * Contenido literal extraído de PLAN_MASTER.md líneas 499-553 (texto
 * canónico aprobado en consultoría L99 25 abril 2026).
 *
 * Server component (sin estado/efectos) → metadata Next.js +
 * pre-rendering. Link "Volver" usa <Link>/<a> standard.
 *
 * Ver ADR-009 (NO eIDAS/TSA preventivo), ADR-010 (cláusula C-001 +
 * página explicativa), CONSISTENCY-001.
 */
import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  FileSignature,
  HelpCircle,
  Mail,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";

import { PublicKeyVerifier } from "@/components/auth/PublicKeyVerifier";
import { PageContainer } from "@/components/layout/PageContainer";
import { Card } from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";

export const metadata: Metadata = {
  title: "Cómo funciona la firma · FULKRO",
  description:
    "Página explicativa sobre la firma electrónica simple eIDAS Art. 25.1 que ofrece FULKRO: alcance válido, alcance no válido, mecanismos técnicos, certificado cualificado y referencias legales.",
};

export default function ClientFirmaPage() {
  return (
    <PageContainer variant="reading">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-[color:var(--fulkro-title)]">
          Cómo funciona la firma electrónica de FULKRO
        </h1>
        <p className="mt-3 text-lg text-[color:var(--fulkro-muted)]">
          Esta página explica en lenguaje plano qué es y qué no es la firma
          electrónica que ofrece FULKRO, para que sepas exactamente qué puedes
          hacer con ella sin sorpresas.
        </p>
      </header>

      <Card className="space-y-10 p-8">
        <section className="space-y-3">
          <div className="flex items-center gap-3">
            <FileSignature
              size={28}
              strokeWidth={2.3}
              className="text-[color:var(--fulkro-primary-700)]"
            />
            <h2 className="text-xl font-semibold text-[color:var(--fulkro-title)]">
              Qué tipo de firma usa FULKRO
            </h2>
          </div>
          <p className="text-base text-[color:var(--fulkro-body)]">
            FULKRO usa{" "}
            <strong>
              <InfoTag term="firma_simple" display="firma electrónica simple" />
            </strong>{" "}
            con verificación criptográfica EC P-256 +{" "}
            <InfoTag term="OTP" display="OTP" />. Esta firma es:
          </p>
          <ul className="list-disc space-y-1 pl-6 text-base text-[color:var(--fulkro-body)]">
            <li>
              <strong>Válida</strong> para tus procesos internos del SGSI y
              para nuestro contrato.
            </li>
            <li>
              <strong>NO válida</strong> para documentos que vayas a presentar
              ante el CCN, Hacienda, Seguridad Social u otros organismos que
              exijan firma cualificada.
            </li>
          </ul>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-3">
            <Mail
              size={28}
              strokeWidth={2.3}
              className="text-[color:var(--fulkro-primary-700)]"
            />
            <h2 className="text-xl font-semibold text-[color:var(--fulkro-title)]">
              Qué pasa cuando firmas un documento desde el email que recibes
            </h2>
          </div>
          <p className="text-base text-[color:var(--fulkro-body)]">
            Cuando recibes un email con un{" "}
            <InfoTag term="magic_link" display="magic link" /> de firma:
          </p>
          <ol className="list-decimal space-y-1 pl-6 text-base text-[color:var(--fulkro-body)]">
            <li>Haces clic en el enlace.</li>
            <li>Te pedimos un OTP (código de 6 dígitos enviado a tu email).</li>
            <li>Confirmas que aceptas el contenido.</li>
            <li>FULKRO genera la firma criptográfica EC P-256.</li>
            <li>
              La firma se vincula a una{" "}
              <InfoTag term="hash_chain" display="cadena hash" /> inmutable.
            </li>
            <li>El documento queda firmado y archivado.</li>
          </ol>
          <p className="text-base text-[color:var(--fulkro-body)]">
            Esta firma es robusta para uso interno del SGSI y para nuestras
            relaciones contractuales.
          </p>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-3">
            <ShieldAlert
              size={28}
              strokeWidth={2.3}
              className="text-[color:var(--fulkro-primary-700)]"
            />
            <h2 className="text-xl font-semibold text-[color:var(--fulkro-title)]">
              Cuándo necesitas firmar con tu certificado cualificado
            </h2>
          </div>
          <p className="text-base text-[color:var(--fulkro-body)]">
            Necesitas tu certificado cualificado (FNMT, Camerfirma,
            Firmaprofesional) cuando:
          </p>
          <ul className="list-disc space-y-1 pl-6 text-base text-[color:var(--fulkro-body)]">
            <li>
              Vas a presentar el documento al CCN como evidencia ante auditor
              ENAC.
            </li>
            <li>
              Vas a presentarlo ante Hacienda, Seguridad Social o AEPD.
            </li>
            <li>El procedimiento administrativo lo exige expresamente.</li>
          </ul>
          <p className="text-base text-[color:var(--fulkro-body)]">
            Para estos casos, FULKRO te entregará el documento final en PDF y
            lo firmas tú con AutoFirma + tu certificado.
          </p>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-3">
            <HelpCircle
              size={28}
              strokeWidth={2.3}
              className="text-[color:var(--fulkro-primary-700)]"
            />
            <h2 className="text-xl font-semibold text-[color:var(--fulkro-title)]">
              Qué pasa si pierdes el email del magic link
            </h2>
          </div>
          <p className="text-base text-[color:var(--fulkro-body)]">
            Marcos puede regenerarte el magic link en cualquier momento. Tu
            firma anterior no se pierde si ya la hiciste, queda registrada en
            el log inmutable.
          </p>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-3">
            <CheckCircle2
              size={28}
              strokeWidth={2.3}
              className="text-[color:var(--fulkro-primary-700)]"
            />
            <h2 className="text-xl font-semibold text-[color:var(--fulkro-title)]">
              Cómo verificas que tu firma es válida
            </h2>
          </div>
          <p className="text-base text-[color:var(--fulkro-body)]">
            Cada firma genera una entrada en el log de auditoría con:
          </p>
          <ul className="list-disc space-y-1 pl-6 text-base text-[color:var(--fulkro-body)]">
            <li>Tu email.</li>
            <li>El documento.</li>
            <li>La fecha/hora UTC.</li>
            <li>Tu IP y dispositivo.</li>
            <li>El hash criptográfico.</li>
          </ul>
          <p className="text-base text-[color:var(--fulkro-body)]">
            Cuando esté disponible el histórico de firmas, podrás consultarlas
            desde tu sección de cuenta.
          </p>
        </section>

        <section className="space-y-3">
          <div className="flex items-center gap-3">
            <ShieldCheck
              size={28}
              strokeWidth={2.3}
              className="text-[color:var(--fulkro-primary-700)]"
            />
            <h2 className="text-xl font-semibold text-[color:var(--fulkro-title)]">
              Más información legal
            </h2>
          </div>
          <ul className="list-disc space-y-1 pl-6 text-base text-[color:var(--fulkro-body)]">
            <li>
              Reglamento UE 910/2014 (eIDAS) artículo 25.1 sobre firma
              electrónica simple.
            </li>
            <li>Ley 59/2003 española de firma electrónica.</li>
            <li>Documento contractual C-001 cláusula 14.</li>
            <li>
              Si tienes dudas legales específicas, escríbele a Marcos desde tu
              bandeja de entrada.
            </li>
          </ul>
        </section>
      </Card>

      {/* SAN-B.MB-7.5 · sección verificación pública clave Ed25519 */}
      <section className="mt-8">
        <PublicKeyVerifier />
      </section>

      <div className="mt-8 flex justify-center">
        <Link
          href="/client-portal/dashboard"
          className="inline-flex items-center gap-2 rounded-md border border-[color:var(--fulkro-surface-glass-border)] bg-[color:var(--fulkro-surface-glass)] px-4 py-2 text-sm font-semibold text-[color:var(--fulkro-title)] transition-colors hover:bg-[color:var(--fulkro-surface-glass-strong)]"
        >
          <ArrowLeft size={18} strokeWidth={2.3} />
          Volver al inicio
        </Link>
      </div>
    </PageContainer>
  );
}
