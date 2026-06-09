/**
 * /terms · Términos de Servicio.
 */
import Link from "next/link";

import { LegalArticle } from "@/components/legal/LegalArticle";

export const metadata = {
  title: "Términos de Servicio · FULKRO",
  description: "Términos y condiciones generales del servicio FULKRO.",
};

export default function TermsPage() {
  return (
    <LegalArticle title="Términos de Servicio" subtitle="Ley 7/1998 LCGC · Código Civil · LGDCU 1/2007">
      <section>
        <h2>1. Objeto</h2>
        <p>
          Los presentes términos regulan la relación contractual entre{" "}
          <strong>Marcos Mata García (FULKRO)</strong> y el Cliente para la
          prestación de servicios de consultoría e implantación del Esquema
          Nacional de Seguridad (RD 311/2022) a través de la plataforma
          tecnológica fulkro.es.
        </p>
      </section>

      <section>
        <h2>2. Servicios prestados</h2>
        <ul>
          <li>
            Diagnóstico inicial y categorización del sistema cliente conforme
            al Anexo I del ENS.
          </li>
          <li>
            Análisis de riesgos MAGERIT y declaración de aplicabilidad (DdA).
          </li>
          <li>
            Generación, firma electrónica y archivo de políticas, procedimientos
            y evidencias documentales.
          </li>
          <li>
            Acompañamiento durante la auditoría externa y mantenimiento
            continuo (retainer) en el periodo de conformidad.
          </li>
          <li>
            Comunicaciones operacionales por los canales que el Cliente haya
            consentido (email, WhatsApp opt-in).
          </li>
        </ul>
      </section>

      <section>
        <h2>3. Precio y facturación</h2>
        <p>
          El precio de los servicios se establece en la oferta económica
          aceptada por el Cliente. La facturación se emite mensual o
          trimestralmente según el modelo contratado (proyecto cerrado o
          retainer). Las cuotas se domiciliarán o transferirán según se
          acuerde en la oferta, con vencimiento a 30 días naturales.
        </p>
      </section>

      <section>
        <h2>4. Cancelación y resolución</h2>
        <ul>
          <li>
            <strong>Retainer mensual</strong> · cualquiera de las partes puede
            resolverlo con preaviso de 30 días.
          </li>
          <li>
            <strong>Proyecto cerrado</strong> · la resolución anticipada
            genera derecho a facturar las horas realmente trabajadas más un
            10 % de gestión.
          </li>
          <li>
            <strong>Por incumplimiento</strong> · cualquiera de las partes
            puede resolver con efecto inmediato en caso de incumplimiento
            esencial no subsanado tras requerimiento por escrito durante 15
            días naturales.
          </li>
        </ul>
      </section>

      <section>
        <h2>5. Niveles de servicio</h2>
        <p>
          FULKRO se compromete a un tiempo de respuesta inicial inferior a 24
          horas laborables para incidencias operativas no críticas. Las
          incidencias clasificadas como críticas se atienden con respuesta
          dentro del horario laboral más próximo, comunicando una primera
          estimación en un plazo no superior a 4 horas.
        </p>
      </section>

      <section>
        <h2>6. Protección de datos</h2>
        <p>
          El tratamiento de datos personales se regula por la{" "}
          <Link href="/privacy">Política de Privacidad</Link> y, en lo que
          corresponde a tratamientos por cuenta del Cliente, por el Contrato
          de Encargo del Tratamiento (DPA Art. 28 RGPD) firmado entre las
          partes (descargable desde la página de{" "}
          <Link href="/dpa-template">DPA</Link>).
        </p>
      </section>

      <section>
        <h2>7. Confidencialidad</h2>
        <p>
          Las partes guardarán la más estricta confidencialidad respecto de
          la información intercambiada durante la vigencia del contrato y
          durante los cinco años posteriores a su extinción. Esta obligación
          no se aplica a la información que sea de dominio público, a la
          obtenida lícitamente de terceros sin obligación de
          confidencialidad, ni a la que deba revelarse por imperativo legal
          o judicial.
        </p>
      </section>

      <section>
        <h2>8. Limitación de responsabilidad</h2>
        <p>
          La responsabilidad de FULKRO se limita al importe total de las
          cantidades facturadas en los doce meses previos al hecho
          generador. Quedan expresamente excluidos los daños indirectos,
          lucro cesante, pérdida de oportunidad y daños reputacionales,
          salvo cuando concurra dolo o culpa grave de FULKRO.
        </p>
      </section>

      <section>
        <h2>9. Propiedad intelectual</h2>
        <p>
          Los entregables generados durante la prestación (políticas,
          procedimientos, informes) son propiedad del Cliente desde su
          aceptación. La plataforma fulkro.es, su software y la metodología
          aplicada son propiedad de FULKRO y se licencian al Cliente
          únicamente para su uso interno durante la vigencia del contrato.
        </p>
      </section>

      <section>
        <h2>10. Modificaciones</h2>
        <p>
          FULKRO podrá modificar estos Términos comunicándolo al Cliente con
          un preaviso de 30 días naturales. Si el Cliente no acepta los
          nuevos términos, podrá resolver el contrato sin penalización.
        </p>
      </section>

      <section>
        <h2>11. Ley aplicable y jurisdicción</h2>
        <p>
          Estos Términos se rigen por la legislación española. Para la
          resolución de cualquier controversia, las partes se someten a los
          Juzgados y Tribunales de Madrid, con renuncia expresa a cualquier
          otro fuero que pudiera corresponderles.
        </p>
      </section>
    </LegalArticle>
  );
}
