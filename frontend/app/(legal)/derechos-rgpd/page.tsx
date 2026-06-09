/**
 * /derechos-rgpd · Ejercicio de derechos RGPD (Arts. 15-22).
 *
 * Página dedicada para que titulares de datos ejerzan sus derechos:
 * acceso · rectificación · supresión · limitación · portabilidad · oposición.
 * Spanish legal Spanish proper · canal explícito DPO + endpoints self-service
 * (access · erasure · portability) ya disponibles en el portal cliente.
 */
import Link from "next/link";

import { LegalArticle } from "@/components/legal/LegalArticle";

export const metadata = {
  title: "Derechos RGPD · FULKRO",
  description:
    "Cómo ejercer tus derechos como titular de datos personales (acceso, rectificación, supresión, limitación, portabilidad, oposición) conforme al RGPD UE 2016/679 y la LOPDGDD 3/2018.",
};

export default function DerechosRgpdPage() {
  return (
    <LegalArticle
      title="Ejercicio de derechos RGPD"
      subtitle="Arts. 15-22 Reglamento (UE) 2016/679 · Arts. 13-18 LOPDGDD 3/2018"
    >
      <section>
        <h2>1. Quién puede ejercer estos derechos</h2>
        <p>
          Cualquier persona física (en adelante, &laquo;titular&raquo;) cuyos
          datos personales estén siendo tratados por FULKRO puede ejercer en
          cualquier momento los derechos reconocidos por el RGPD y la LOPDGDD.
          Incluye clientes activos, ex-clientes, personas de contacto en
          organizaciones cliente y, en general, cualquier persona que aparezca
          identificada en datos que tratamos.
        </p>
      </section>

      <section>
        <h2>2. Canal de ejercicio</h2>
        <p>Para ejercer cualquiera de los derechos descritos puedes:</p>
        <ul>
          <li>
            Escribir al Delegado de Protección de Datos:{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a> con asunto{" "}
            <code>[RGPD] Solicitud de [derecho]</code>.
          </li>
          <li>
            Si eres cliente con cuenta activa, utilizar los endpoints
            self-service del portal cliente (ver cada derecho abajo).
          </li>
        </ul>
        <p>
          Esta página enumera los derechos y los procedimientos disponibles.
          La <Link href="/privacy">Política de Privacidad</Link> contiene el
          marco completo del tratamiento (responsable, finalidades, bases
          jurídicas, plazos de conservación, sub-encargados).
        </p>
      </section>

      <section>
        <h2>3. Identificación previa</h2>
        <p>
          Para evitar ejercicio fraudulento de derechos por terceros, FULKRO
          puede solicitarte que acredites tu identidad antes de tramitar la
          solicitud (Art. 12.6 RGPD): copia de DNI/NIE/pasaporte vigente o
          autenticación a través del portal cliente cuando el derecho se
          ejerce vía endpoint.
        </p>
      </section>

      <section>
        <h2>4. Derecho de acceso (Art. 15 RGPD)</h2>
        <p>
          Tienes derecho a obtener confirmación de si FULKRO trata datos
          personales que te conciernen y, en tal caso, acceso a esos datos
          junto con información sobre fines, categorías de datos,
          destinatarios, plazos de conservación previstos y origen de los
          datos cuando no se hayan obtenido directamente de ti.
        </p>
        <ul>
          <li>
            <strong>Self-service</strong> (clientes con cuenta):{" "}
            <code>GET /api/v1/portal/rgpd/access</code> · descarga JSON
            estructurado.
          </li>
          <li>
            <strong>Vía DPO</strong>:{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
          </li>
        </ul>
      </section>

      <section>
        <h2>5. Derecho de rectificación (Art. 16 RGPD)</h2>
        <p>
          Tienes derecho a obtener sin dilación indebida la rectificación de
          los datos personales inexactos o incompletos. Indica en tu
          solicitud el dato concreto a corregir y el valor correcto,
          acompañando documentación acreditativa cuando proceda.
        </p>
        <ul>
          <li>
            Vía DPO:{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
          </li>
        </ul>
      </section>

      <section>
        <h2>
          6. Derecho de supresión &laquo;al olvido&raquo; (Art. 17 RGPD)
        </h2>
        <p>
          Tienes derecho a obtener la supresión de tus datos cuando ya no
          sean necesarios para el fin que motivó su recogida, retires el
          consentimiento, te opongas al tratamiento sin motivo legítimo
          prevalente, o el tratamiento sea ilícito.
        </p>
        <p>
          <strong>Limitaciones legales</strong> · FULKRO conservará
          determinados datos durante los plazos exigidos por la normativa
          aplicable (7 años evidencias ENS, 6 años contables, 5 años
          fiscales; ver{" "}
          <Link href="/privacy">Política de Privacidad</Link>, sección 8).
          Estos datos quedarán bloqueados y solo accesibles para esas
          finalidades.
        </p>
        <ul>
          <li>
            <strong>Self-service</strong>:{" "}
            <code>POST /api/v1/portal/rgpd/erasure</code>.
          </li>
          <li>
            <strong>Vía DPO</strong>:{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
          </li>
        </ul>
      </section>

      <section>
        <h2>7. Derecho a la limitación del tratamiento (Art. 18 RGPD)</h2>
        <p>
          Puedes solicitar que FULKRO marque tus datos para limitar su
          tratamiento futuro mientras se verifica la exactitud impugnada,
          mientras se resuelve una oposición prevalente, cuando el
          tratamiento sea ilícito pero no desees la supresión, o cuando
          necesites los datos para reclamaciones aunque FULKRO ya no los
          requiera.
        </p>
        <ul>
          <li>
            Vía DPO:{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
          </li>
        </ul>
      </section>

      <section>
        <h2>8. Derecho a la portabilidad de los datos (Art. 20 RGPD)</h2>
        <p>
          Cuando el tratamiento se basa en consentimiento o en la ejecución
          de un contrato y se efectúa por medios automatizados, tienes
          derecho a recibir los datos personales que te conciernen en un
          formato estructurado, comúnmente utilizado y de lectura mecánica,
          así como a transmitirlos a otro responsable del tratamiento.
        </p>
        <ul>
          <li>
            <strong>Self-service</strong>:{" "}
            <code>GET /api/v1/portal/rgpd/portability</code> · formato
            JSON-LD.
          </li>
        </ul>
      </section>

      <section>
        <h2>9. Derecho de oposición (Art. 21 RGPD)</h2>
        <p>
          Puedes oponerte al tratamiento de tus datos por motivos
          relacionados con tu situación particular cuando dicho tratamiento
          se base en interés legítimo (Art. 6.1.f RGPD). FULKRO dejará de
          tratar tus datos salvo que acredite motivos legítimos imperiosos
          que prevalezcan sobre tus intereses, derechos y libertades, o
          para la formulación, ejercicio o defensa de reclamaciones.
        </p>
        <ul>
          <li>
            Vía DPO:{" "}
            <a href="mailto:dpo@fulkro.es">dpo@fulkro.es</a>.
          </li>
        </ul>
      </section>

      <section>
        <h2>10. Decisiones individuales automatizadas (Art. 22 RGPD)</h2>
        <p>
          FULKRO no adopta decisiones que produzcan efectos jurídicos sobre
          ti o te afecten significativamente de modo similar, basadas
          únicamente en el tratamiento automatizado de tus datos, incluida
          la elaboración de perfiles. Los modelos de lenguaje (Claude) que
          asisten en la generación de borradores documentales son siempre
          revisados y firmados por una persona física.
        </p>
      </section>

      <section>
        <h2>11. Plazos y gratuidad (Art. 12 RGPD)</h2>
        <ul>
          <li>
            FULKRO responderá en un plazo máximo de un mes desde la
            recepción de la solicitud, ampliable a dos meses adicionales
            cuando la complejidad o el número de solicitudes lo justifique.
            Te informaremos de la prórroga durante el primer mes.
          </li>
          <li>
            El ejercicio de derechos es <strong>gratuito</strong>. FULKRO
            solo podrá denegar la tramitación o cobrar un canon razonable
            cuando las solicitudes sean manifiestamente infundadas o
            excesivas, en particular por su carácter repetitivo (Art. 12.5
            RGPD).
          </li>
        </ul>
      </section>

      <section>
        <h2>12. Reclamación ante la AEPD</h2>
        <p>
          Si consideras que tu solicitud no ha sido atendida correctamente,
          puedes presentar una reclamación ante la Agencia Española de
          Protección de Datos (autoridad de control competente):{" "}
          <a
            href="https://www.aepd.es"
            rel="noreferrer noopener"
            target="_blank"
          >
            aepd.es
          </a>
          . La reclamación es gratuita y no requiere abogado ni
          representación legal.
        </p>
      </section>
    </LegalArticle>
  );
}
