/**
 * /imprint · Aviso legal de un proyecto cerrado.
 */
import { LegalArticle } from "@/components/legal/LegalArticle";
import { AvisoProyectoCerrado, REPO_URL, Titular } from "@/components/legal/ProyectoCerrado";

export const metadata = {
  title: "Aviso legal · FULKRO",
  description: "Aviso legal de Fulkro, un proyecto cerrado cuyo código se publica bajo Apache-2.0.",
};

export default function ImprintPage() {
  return (
    <LegalArticle title="Aviso legal" subtitle="Proyecto cerrado en septiembre de 2026">
      <section>
        <h2>1. Titular</h2>
        <Titular />
      </section>
      <section>
        <h2>2. Qué es esta aplicación</h2>
        <AvisoProyectoCerrado />
      </section>
      <section>
        <h2>3. Propiedad intelectual</h2>
        <p>
          El código se publica bajo la licencia Apache-2.0 en{" "}
          <a href={REPO_URL}>GitHub</a>. Esa licencia dice qué puedes hacer con
          él. Se publica tal cual, sin mantenimiento. Las normas que se citan
          (el RD 311/2022 y la legislación de la Unión Europea) pertenecen a sus
          autores.
        </p>
      </section>
      <section>
        <h2>4. Responsabilidad</h2>
        <p>
          Quien ejecuta una copia de esta aplicación es responsable de ella y de
          los datos que guarde. Lo que muestra no es asesoramiento jurídico ni
          técnico. Fulkro no emitía certificados: la certificación del ENS en
          las categorías Media y Alta la emite una entidad acreditada por ENAC.
        </p>
      </section>
      <section>
        <h2>5. Legislación aplicable</h2>
        <p>Este aviso se rige por la legislación española.</p>
      </section>
    </LegalArticle>
  );
}
