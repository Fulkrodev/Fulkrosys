/**
 * /imprint · Aviso Legal (LSSI-CE Art. 10).
 */
import Link from "next/link";

import { LegalArticle } from "@/components/legal/LegalArticle";

export const metadata = {
  title: "Aviso Legal · FULKRO",
  description: "Aviso legal de FULKRO conforme al Art. 10 de la Ley 34/2002 (LSSI-CE).",
};

export default function ImprintPage() {
  return (
    <LegalArticle title="Aviso Legal" subtitle="Ley 34/2002 (LSSI-CE) · Art. 10">
      <section>
        <h2>1. Datos identificativos del prestador</h2>
        <ul>
          <li>
            <strong>Denominación comercial:</strong> FULKRO
          </li>
          <li>
            <strong>Titular:</strong> Marcos Mata García
          </li>
          <li>
            <strong>CIF/NIF:</strong> 77171140E
          </li>
          <li>
            <strong>Domicilio profesional:</strong> Madrid, España
          </li>
          <li>
            <strong>Email general:</strong>{" "}
            <a href="mailto:marcosmata@fulkro.es">marcosmata@fulkro.es</a>
          </li>
          <li>
            <strong>Email DPO:</strong>{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>
          </li>
          <li>
            <strong>Email seguridad:</strong>{" "}
            <a href="mailto:security@fulkro.es">security@fulkro.es</a> · ver{" "}
            <a href="/.well-known/security.txt">security.txt</a> (RFC 9116)
          </li>
        </ul>
      </section>

      <section>
        <h2>2. Actividad</h2>
        <p>
          Consultoría de servicios IT especializada en la implantación,
          mantenimiento y auditoría del Esquema Nacional de Seguridad
          (RD 311/2022) para entidades del sector público y sus
          proveedores. No está sujeto a colegiación profesional obligatoria.
        </p>
      </section>

      <section>
        <h2>3. Información sobre el sitio web</h2>
        <p>
          fulkro.es es operado por Marcos Mata García. La infraestructura de
          hosting es proporcionada por Hetzner Online GmbH (Falkenstein,
          Alemania · Unión Europea). La lista completa de sub-procesadores
          implicados está publicada en{" "}
          <Link href="/sub-processors">/sub-processors</Link>.
        </p>
      </section>

      <section>
        <h2>4. Protección de datos personales</h2>
        <p>
          El tratamiento de los datos personales recogidos a través de este
          sitio se rige por la{" "}
          <Link href="/privacy">Política de Privacidad</Link> de FULKRO,
          conforme al Reglamento (UE) 2016/679 y a la Ley Orgánica 3/2018.
        </p>
      </section>

      <section>
        <h2>5. Términos de servicio</h2>
        <p>
          El uso de la plataforma y la contratación de los servicios
          ofrecidos está sometido a los{" "}
          <Link href="/terms">Términos de Servicio</Link>.
        </p>
      </section>

      <section>
        <h2>6. Propiedad intelectual</h2>
        <p>
          Salvo indicación expresa, todos los contenidos publicados en
          fulkro.es (textos, gráficos, código, marca FULKRO) son propiedad
          de Marcos Mata García y están protegidos por la legislación
          española e internacional sobre propiedad intelectual e industrial.
        </p>
      </section>

      <section>
        <h2>7. Responsabilidad</h2>
        <p>
          FULKRO no garantiza la inexistencia de errores u omisiones en los
          contenidos, ni la ausencia de virus u otros elementos lesivos. No
          asume responsabilidad por los enlaces a sitios web de terceros
          incluidos en la plataforma.
        </p>
      </section>

      <section>
        <h2>8. Resolución de conflictos</h2>
        <p>
          Las partes se someten, con renuncia expresa a cualquier otro
          fuero, a la jurisdicción de los Juzgados y Tribunales de Madrid.
          Los consumidores pueden recurrir asimismo a la plataforma europea
          de resolución de litigios en línea (ODR):{" "}
          <a
            href="https://ec.europa.eu/consumers/odr"
            target="_blank"
            rel="noreferrer"
          >
            ec.europa.eu/consumers/odr
          </a>
          .
        </p>
      </section>
    </LegalArticle>
  );
}
