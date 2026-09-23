/**
 * /terms · Términos de uso de un proyecto cerrado.
 */
import { LegalArticle } from "@/components/legal/LegalArticle";
import { AvisoProyectoCerrado, REPO_URL } from "@/components/legal/ProyectoCerrado";

export const metadata = {
  title: "Términos · FULKRO",
  description: "Términos de uso del código de Fulkro, un proyecto cerrado.",
};

export default function TermsPage() {
  return (
    <LegalArticle title="Términos" subtitle="Proyecto cerrado en septiembre de 2026">
      <section>
        <h2>1. No hay servicio que contratar</h2>
        <AvisoProyectoCerrado />
      </section>
      <section>
        <h2>2. Uso del código</h2>
        <p>
          El uso del código se rige por la licencia Apache-2.0 publicada en{" "}
          <a href={REPO_URL}>GitHub</a>. Se ofrece tal cual, sin garantía de
          ningún tipo, como dice esa licencia.
        </p>
      </section>
    </LegalArticle>
  );
}
