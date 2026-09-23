/**
 * /trust · El proyecto está cerrado: no hay servicio sobre el que dar garantías.
 */
import { LegalArticle } from "@/components/legal/LegalArticle";
import { AvisoProyectoCerrado, REPO_URL } from "@/components/legal/ProyectoCerrado";

export const metadata = {
  title: "Seguridad · FULKRO",
  description: "Fulkro está cerrado: no hay servicio en producción.",
};

export default function TrustPage() {
  return (
    <LegalArticle title="Seguridad" subtitle="Proyecto cerrado en septiembre de 2026">
      <section>
        <h2>No hay servicio en producción</h2>
        <AvisoProyectoCerrado />
        <p>
          Cómo se protegía la plataforma (RLS en PostgreSQL, registro de
          auditoría encadenado, firmas Ed25519, doble factor) está en el código
          y en su documentación, en <a href={REPO_URL}>GitHub</a>.
        </p>
      </section>
    </LegalArticle>
  );
}
