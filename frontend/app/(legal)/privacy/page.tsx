/**
 * /privacy · Política de Privacidad (Art. 13-14 RGPD).
 *
 * Content production-grade · Spanish legal Spanish proper · sin LEGAL
 * REVIEW STATUS footer (Marcos decision sostained).
 */
import Link from "next/link";

import { LegalArticle } from "@/components/legal/LegalArticle";

export const metadata = {
  title: "Política de Privacidad · FULKRO",
  description: "Política de privacidad de FULKRO conforme al RGPD UE 2016/679 y la LOPDGDD 3/2018.",
};

export default function PrivacyPage() {
  return (
    <LegalArticle title="Política de Privacidad" subtitle="Reglamento (UE) 2016/679 (RGPD) · LOPDGDD 3/2018">
      <section>
        <h2>1. Responsable del tratamiento</h2>
        <p>
          El responsable del tratamiento de tus datos personales es{" "}
          <strong>Marcos Mata García</strong> (en adelante, &laquo;FULKRO&raquo;),
          con domicilio profesional en Madrid, España y CIF/NIF
          77171140E. Actividad: consultoría de servicios IT
          especializada en el Esquema Nacional de Seguridad (RD 311/2022).
        </p>
        <p>
          Email general:{" "}
          <a href="mailto:marcosmata@fulkro.es">marcosmata@fulkro.es</a>
        </p>
      </section>

      <section>
        <h2>2. Delegado de Protección de Datos (DPO)</h2>
        <p>
          Marcos Mata García actúa como DPO en régimen interino.
          Contacto:{" "}
          <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
        </p>
      </section>

      <section>
        <h2>3. Finalidades del tratamiento</h2>
        <ul>
          <li>Prestación de los servicios de consultoría e implantación ENS contratados.</li>
          <li>Gestión administrativa, comercial y contable de la relación con el cliente.</li>
          <li>Generación, firma y archivo de documentos derivados del proyecto.</li>
          <li>Comunicaciones operacionales (notificaciones de hitos, recordatorios, alertas).</li>
          <li>Cumplimiento de obligaciones legales (fiscales, laborales, de seguridad).</li>
        </ul>
      </section>

      <section>
        <h2>4. Base jurídica del tratamiento</h2>
        <ul>
          <li>
            <strong>Art. 6.1.b RGPD</strong> · ejecución de un contrato en el que el
            interesado es parte.
          </li>
          <li>
            <strong>Art. 6.1.c RGPD</strong> · cumplimiento de obligaciones legales
            (conservación de evidencias ENS, obligaciones fiscales AEAT).
          </li>
          <li>
            <strong>Art. 6.1.f RGPD</strong> · interés legítimo en la
            comunicación comercial y la mejora del servicio, debidamente
            ponderado.
          </li>
          <li>
            <strong>Art. 6.1.a RGPD</strong> · consentimiento explícito para
            canales opt-in (WhatsApp, cookies analíticas, marketing).
          </li>
        </ul>
      </section>

      <section>
        <h2>5. Categorías de datos tratados</h2>
        <ul>
          <li>Datos identificativos: nombre, apellidos.</li>
          <li>Datos de contacto profesional: correo electrónico, teléfono.</li>
          <li>Datos laborales: cargo, organización a la que perteneces.</li>
          <li>
            Datos técnicos del sistema cliente (direcciones IP, identificadores
            técnicos) cuando aparecen incidentalmente en evidencias.
          </li>
          <li>
            Datos económicos derivados de la facturación (importes, formas de
            pago).
          </li>
        </ul>
        <p>
          No tratamos categorías especiales de datos (Art. 9 RGPD) ni datos
          relativos a condenas o infracciones penales (Art. 10 RGPD).
        </p>
      </section>

      <section>
        <h2>6. Destinatarios y sub-encargados</h2>
        <p>
          FULKRO recurre a los sub-encargados publicados en
          <Link href="/sub-processors"> /sub-processors</Link>. Todos cuentan con
          contrato de encargo de tratamiento (Art. 28 RGPD) firmado. Los
          datos no se comunican a otros terceros salvo obligación legal.
        </p>
      </section>

      <section>
        <h2>7. Transferencias internacionales de datos</h2>
        <p>
          Las únicas transferencias fuera del Espacio Económico Europeo se
          producen con Anthropic PBC (Estados Unidos), proveedor del modelo
          de lenguaje Claude. Estas transferencias están amparadas por:
        </p>
        <ul>
          <li>Cláusulas Contractuales Tipo de la Decisión (UE) 2021/914 firmadas con Anthropic.</li>
          <li>Contrato de encargo de tratamiento conforme al Art. 28 RGPD.</li>
          <li>Adhesión de Anthropic al Marco de Privacidad de Datos UE-EE.UU.</li>
        </ul>
        <p>
          El resto de proveedores (Hetzner, Postmark, 360dialog) operan
          exclusivamente desde la Unión Europea.
        </p>
      </section>

      <section>
        <h2>8. Plazos de conservación</h2>
        <ul>
          <li>
            <strong>Datos contractuales y de cliente</strong>: durante la
            vigencia del contrato y, posteriormente, 7 años a efectos de
            auditoría conforme al art. 24.1 del RD 311/2022 (ENS).
          </li>
          <li>
            <strong>Datos contables</strong>: 6 años conforme al art. 30 del
            Código de Comercio.
          </li>
          <li>
            <strong>Datos fiscales</strong>: 5 años conforme al art. 30 de la
            Ley General Tributaria.
          </li>
          <li>
            <strong>Cookies analíticas</strong>: máximo 24 meses (Guía AEPD
            2020).
          </li>
        </ul>
      </section>

      <section>
        <h2>9. Derechos de los interesados</h2>
        <p>
          Como interesado, puedes ejercer en cualquier momento los siguientes
          derechos:
        </p>
        <ul>
          <li>
            <strong>Acceso (Art. 15)</strong> · descarga estructurada desde el
            portal cliente:{" "}
            <code>GET /api/v1/portal/rgpd/access</code>.
          </li>
          <li>
            <strong>Rectificación (Art. 16)</strong> · escríbenos a{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
          </li>
          <li>
            <strong>Supresión (Art. 17)</strong> · solicítala desde el portal
            cliente:{" "}
            <code>POST /api/v1/portal/rgpd/erasure</code>.
          </li>
          <li>
            <strong>Portabilidad (Art. 20)</strong> · formato JSON-LD desde{" "}
            <code>GET /api/v1/portal/rgpd/portability</code>.
          </li>
          <li>
            <strong>Limitación (Art. 18)</strong> y{" "}
            <strong>oposición (Art. 21)</strong> · escríbenos a{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
          </li>
        </ul>
        <p>
          FULKRO tramitará tu solicitud en un plazo máximo de un mes
          (Art. 12.3 RGPD).
        </p>
      </section>

      <section>
        <h2>10. Reclamación ante la AEPD</h2>
        <p>
          Si consideras que el tratamiento de tus datos no se ajusta a la
          normativa puedes presentar una reclamación ante la Agencia Española
          de Protección de Datos: <a href="https://www.aepd.es">aepd.es</a>.
        </p>
      </section>

      <section>
        <h2>11. Medidas de seguridad</h2>
        <p>
          Aplicamos las medidas técnicas y organizativas previstas en el
          Art. 32 RGPD y detalladas en nuestro Anexo II del DPA cliente.
          Incluyen cifrado en tránsito (TLS 1.3), cifrado en reposo,
          autenticación reforzada 2FA TOTP del personal administrador, firma
          electrónica avanzada Ed25519 del registro de auditoría y copias de
          seguridad cifradas con prueba mensual de restauración.
        </p>
      </section>
    </LegalArticle>
  );
}
