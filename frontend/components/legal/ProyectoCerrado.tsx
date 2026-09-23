/**
 * Identificación del titular y aviso de proyecto cerrado, comunes a las
 * páginas legales. Fulkro cerró en septiembre de 2026: no hay servicio, ni
 * clientes, ni tratamiento de datos por parte del titular. Solo se publica el
 * nombre, la ciudad y el email de contacto.
 */
export const REPO_URL = "https://github.com/Fulkrodev/Fulkrosys";

export function Titular() {
  return (
    <ul>
      <li>
        <strong>Titular:</strong> Marcos Mata García
      </li>
      <li>
        <strong>Domicilio:</strong> Madrid (España)
      </li>
      <li>
        <strong>Email de contacto:</strong>{" "}
        <a href="mailto:marcosmata@fulkro.es">marcosmata@fulkro.es</a>
      </li>
    </ul>
  );
}

export function AvisoProyectoCerrado() {
  return (
    <p>
      Fulkro fue una plataforma para implantar el Esquema Nacional de Seguridad
      (RD 311/2022). <strong>El proyecto cerró en septiembre de 2026</strong>:
      no presta servicios, no tiene clientes y no tiene actividad económica. Su
      código se publica como software libre bajo la licencia Apache-2.0 en{" "}
      <a href={REPO_URL}>GitHub</a>. Si estás viendo esta aplicación, es una
      copia que alguien ejecuta por su cuenta, por ejemplo el demo de{" "}
      <code>make demo</code>.
    </p>
  );
}
