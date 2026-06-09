import { redirect } from "next/navigation";

/**
 * RADAR DESACTIVADO Batch 2 (dormido · reversible · ver
 * docs/audits/EJECUTABLE_8_BATCH2_FASE0_RECORRIDO_AUDIT.md).
 *
 * El pipeline de leads (m13 comercial) sale del flujo: nav link retirado +
 * endpoints backend 404. Este layout redirige /admin/pipeline y
 * /admin/pipeline/* a /admin/projects para no tropezar con páginas muertas.
 * Las páginas originales (pipeline/page.tsx + leads/[id]/page.tsx) quedan
 * INTACTAS (dormidas). Reactivar = borrar este fichero.
 */
export default function PipelineDisabledLayout() {
  redirect("/admin/projects");
}
