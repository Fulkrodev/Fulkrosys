/**
 * /diagnostico/[token] · cuestionario de diagnóstico previo del lead (Batch B).
 *
 * Ruta pública account-less (middleware: "Resto: público"). Hereda el shell
 * branded del grupo (public) (isotipo Fulkro + header/footer). El flujo completo
 * (consume → consent Art.13 → preguntas → gracias) vive en DiagnosticoFlow.
 */
import { DiagnosticoFlow } from "@/components/diagnostico/DiagnosticoFlow";

export default function DiagnosticoTokenPage({
  params,
}: {
  params: { token: string };
}) {
  return <DiagnosticoFlow token={params.token} />;
}
