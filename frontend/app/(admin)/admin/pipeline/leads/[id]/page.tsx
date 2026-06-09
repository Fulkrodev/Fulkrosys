/**
 * SAN-D MB-19.16 cosecha B · DEC-MB19A-LEAD-DETAIL-PAGE.
 *
 * Page detalle Lead CRM con tabs:
 * - Overview: campos base lead (empresa · contacto · sector · stage · etc)
 * - Activity: lead_stage_history audit trail transiciones (MB-19.1)
 * - Proposals: revisiones ordered version DESC (MB-19.3 · superseded badge)
 * - Contract: si existe · firmado_marcos/cliente_at + vigente · estado
 * - Notes: notas + razon_perdida · readonly
 *
 * Refs: ADR-041 · DEC-MB19A-LEAD-DETAIL-PAGE asignado MB-19.C.
 */
import { LeadDetailView } from "@/components/admin/LeadDetailView";

export const metadata = {
  title: "Lead detalle · FULKRO",
};

export default function LeadDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <LeadDetailView leadId={params.id} />;
}
