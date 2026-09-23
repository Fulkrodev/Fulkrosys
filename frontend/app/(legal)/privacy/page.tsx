/**
 * /privacy · Privacidad de un proyecto cerrado: el titular no trata datos.
 */
import { LegalArticle } from "@/components/legal/LegalArticle";
import { AvisoProyectoCerrado, Titular } from "@/components/legal/ProyectoCerrado";

export const metadata = {
  title: "Privacidad · FULKRO",
  description: "Qué pasa con los datos en una copia de Fulkro, un proyecto cerrado.",
};

export default function PrivacyPage() {
  return (
    <LegalArticle title="Privacidad" subtitle="Proyecto cerrado en septiembre de 2026">
      <section>
        <h2>1. Titular del proyecto</h2>
        <Titular />
      </section>
      <section>
        <h2>2. El titular no trata tus datos</h2>
        <AvisoProyectoCerrado />
        <p>
          No hay ninguna instancia de Fulkro en servicio. Los datos que
          introduces en esta aplicación se guardan en la base de datos de quien
          la ejecuta, y es esa persona u organización quien responde de ellos.
          Al titular del proyecto no le llega nada.
        </p>
      </section>
      <section>
        <h2>3. Servicios externos</h2>
        <p>
          Si quien ejecuta la aplicación configura una clave de la API de
          Anthropic, el copiloto y los agentes envían a esa API el texto que
          necesitan para responder. Sin clave, no sale nada.
        </p>
      </section>
      <section>
        <h2>4. Contacto</h2>
        <p>
          Para cualquier duda sobre el proyecto, escribe a
          marcosmata@fulkro.es. Puedes reclamar ante la Agencia Española de
          Protección de Datos (<a href="https://www.aepd.es">www.aepd.es</a>).
        </p>
      </section>
    </LegalArticle>
  );
}
