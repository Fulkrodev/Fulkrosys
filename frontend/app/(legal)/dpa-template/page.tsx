/**
 * /dpa-template · Sin servicio no hay contrato de encargo.
 */
import { LegalArticle } from "@/components/legal/LegalArticle";
import { AvisoProyectoCerrado } from "@/components/legal/ProyectoCerrado";

export const metadata = {
  title: "Contrato de encargo · FULKRO",
  description: "Fulkro está cerrado y no firma contratos de encargo.",
};

export default function DpaTemplatePage() {
  return (
    <LegalArticle title="Contrato de encargo" subtitle="No aplica">
      <section>
        <h2>No hay contrato de encargo que firmar</h2>
        <AvisoProyectoCerrado />
        <p>
          Fulkro no trata datos por cuenta de nadie, así que no firma
          contratos de encargo del tratamiento (art. 28 RGPD).
        </p>
      </section>
    </LegalArticle>
  );
}
