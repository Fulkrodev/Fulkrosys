/**
 * /cookies · Las dos cookies técnicas que pone la aplicación.
 */
import { LegalArticle } from "@/components/legal/LegalArticle";

export const metadata = {
  title: "Cookies · FULKRO",
  description: "Las cookies técnicas que usa la aplicación Fulkro.",
};

export default function CookiesPage() {
  return (
    <LegalArticle title="Cookies" subtitle="Solo cookies técnicas">
      <section>
        <h2>1. Qué cookies pone la aplicación</h2>
        <p>Dos, las dos técnicas y necesarias para iniciar sesión:</p>
        <ul>
          <li>
            <strong>fulkro_session</strong>: la sesión. No es accesible desde
            JavaScript (<code>httpOnly</code>) y caduca al cerrar sesión.
          </li>
          <li>
            <strong>fulkro_csrf</strong>: protege los formularios frente a
            peticiones falsificadas (CSRF).
          </li>
        </ul>
      </section>
      <section>
        <h2>2. Lo que no hay</h2>
        <p>
          No hay cookies de analítica ni de publicidad, ni propias ni de
          terceros. Por eso no se pide consentimiento.
        </p>
      </section>
    </LegalArticle>
  );
}
