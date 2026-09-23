/**
 * /derechos-rgpd · Cómo ejercer los derechos RGPD ante un proyecto cerrado.
 */
import { LegalArticle } from "@/components/legal/LegalArticle";
import { AvisoProyectoCerrado } from "@/components/legal/ProyectoCerrado";

export const metadata = {
  title: "Tus derechos RGPD · FULKRO",
  description: "Cómo ejercer tus derechos de protección de datos.",
};

export default function DerechosRgpdPage() {
  return (
    <LegalArticle title="Tus derechos RGPD" subtitle="Proyecto cerrado en septiembre de 2026">
      <section>
        <h2>A quién dirigirte</h2>
        <AvisoProyectoCerrado />
        <p>
          El titular del proyecto no guarda datos de esta aplicación. Si tus
          datos están en una copia, los derechos de acceso, rectificación,
          supresión, oposición, limitación y portabilidad se ejercen ante quien
          la ejecuta. Para cualquier duda sobre el proyecto, escribe a
          marcosmata@fulkro.es. Puedes reclamar ante la Agencia Española de
          Protección de Datos (<a href="https://www.aepd.es">www.aepd.es</a>).
        </p>
      </section>
    </LegalArticle>
  );
}
