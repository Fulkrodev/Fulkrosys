/**
 * /cookies · Política de Cookies (Guía AEPD 2020).
 */
import Link from "next/link";

import { LegalArticle } from "@/components/legal/LegalArticle";
import { FooterCookiesLink } from "@/components/legal/FooterCookiesLink";
import { COOKIE_INVENTORY } from "@/lib/cookies/inventory";

export const metadata = {
  title: "Política de Cookies · FULKRO",
  description:
    "Política de cookies de FULKRO conforme a la Guía AEPD 2020 y la LSSI-CE.",
};

export default function CookiesPolicyPage() {
  return (
    <LegalArticle
      title="Política de Cookies"
      subtitle="Guía AEPD 2020 · LSSI-CE Art. 22.2"
    >
      <section>
        <h2>1. Qué son las cookies</h2>
        <p>
          Las cookies son pequeños archivos de texto que un sitio web instala
          en tu navegador para recordar información sobre tu visita: la
          sesión, tus preferencias o estadísticas agregadas de uso. Algunas
          son imprescindibles para que la plataforma funcione (cookies
          necesarias) y otras requieren tu consentimiento explícito previo
          (cookies funcionales y analíticas).
        </p>
      </section>

      <section>
        <h2>2. Cómo gestionar tus preferencias</h2>
        <p>
          La primera vez que visitas FULKRO se muestra un aviso con tres
          opciones de igual visibilidad (<strong>Rechazar todo</strong>,{" "}
          <strong>Configurar</strong>, <strong>Aceptar todo</strong>), de
          acuerdo con la Guía de la AEPD de 2020. Puedes modificar tu
          decisión cuando quieras pulsando el enlace{" "}
          <FooterCookiesLink label="Preferencias cookies" /> presente en el
          pie de página, o desde tu perfil de cliente.
        </p>
        <p>
          Tu consentimiento se renueva automáticamente cada 24 meses, conforme
          al §4.4 de la Guía AEPD.
        </p>
      </section>

      <section>
        <h2>3. Categorías de cookies utilizadas</h2>
        {COOKIE_INVENTORY.map((category) => (
          <div key={category.id} style={{ marginBottom: "1.5rem" }}>
            <h3
              style={{
                fontSize: "1rem",
                fontWeight: 600,
                color: "#0f172a",
                marginBottom: "0.5rem",
              }}
            >
              {category.label}
              {category.fixed_on ? " (siempre activas)" : " (opt-in)"}
            </h3>
            <p>{category.description_es}</p>
            <div style={{ overflowX: "auto" }}>
            <table
              aria-label={`Cookies de la categoría ${category.label}`}
              style={{
                width: "100%",
                borderCollapse: "collapse",
                marginTop: "0.5rem",
                fontSize: "0.85rem",
                minWidth: "32rem",
              }}
            >
              <thead>
                <tr style={{ background: "#f1f5f9" }}>
                  <th style={{ textAlign: "left", padding: "6px 10px" }}>Cookie</th>
                  <th style={{ textAlign: "left", padding: "6px 10px" }}>Proveedor</th>
                  <th style={{ textAlign: "left", padding: "6px 10px" }}>Duración</th>
                  <th style={{ textAlign: "left", padding: "6px 10px" }}>Propósito</th>
                </tr>
              </thead>
              <tbody>
                {category.cookies.map((c) => (
                  <tr key={c.name} style={{ borderBottom: "1px solid #e2e8f0" }}>
                    <td style={{ padding: "6px 10px", fontFamily: "ui-monospace, monospace" }}>{c.name}</td>
                    <td style={{ padding: "6px 10px" }}>{c.provider}</td>
                    <td style={{ padding: "6px 10px" }}>{c.duration}</td>
                    <td style={{ padding: "6px 10px" }}>{c.purpose_es}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        ))}
      </section>

      <section>
        <h2>4. Sub-procesadores implicados en cookies</h2>
        <p>
          Las cookies funcionales son íntegramente de FULKRO (first-party).
          Las cookies analíticas se sirven desde PostHog auto-hospedado en la
          Unión Europea — no compartimos datos con terceros publicitarios. La
          lista completa de sub-procesadores está publicada en{" "}
          <Link href="/sub-processors">/sub-processors</Link>.
        </p>
      </section>

      <section>
        <h2>5. Trazabilidad del consentimiento</h2>
        <p>
          Cada decisión que tomas sobre cookies queda registrada en nuestro
          log de auditoría con marca temporal, dirección IP y user-agent, en
          cumplimiento del Art. 7.1 RGPD (capacidad de demostrar el
          consentimiento). Esta información se conserva durante 7 años.
        </p>
      </section>

      <section>
        <h2>6. Contacto</h2>
        <p>
          Para cualquier consulta sobre el uso de cookies escribe a{" "}
          <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
        </p>
      </section>
    </LegalArticle>
  );
}
