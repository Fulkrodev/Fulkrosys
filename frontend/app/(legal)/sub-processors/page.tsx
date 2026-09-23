/**
 * /sub-processors · Sin servicio no hay encargados del tratamiento.
 */
import { LegalArticle } from "@/components/legal/LegalArticle";
import { AvisoProyectoCerrado } from "@/components/legal/ProyectoCerrado";

export const metadata = {
  title: "Encargados del tratamiento · FULKRO",
  description: "Fulkro está cerrado y no tiene encargados del tratamiento.",
};

export default function SubProcessorsPage() {
  return (
    <LegalArticle title="Encargados del tratamiento" subtitle="Ninguno">
      <section>
        <h2>No hay encargados del tratamiento</h2>
        <AvisoProyectoCerrado />
        <p>
          Sin servicio no hay tratamiento de datos por cuenta de nadie, y por
          tanto no hay encargados. Quien ejecuta una copia decide qué
          proveedores usa.
        </p>
      </section>
    </LegalArticle>
  );
}
