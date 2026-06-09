/**
 * Legacy redirect · Sesión 3B-2B.3 Phase X.4c (architectural cleanup).
 *
 * `/admin/clients/[id]/meetings` (per-cliente histórico table 44 LOC)
 * consolidates into top-level cross-cliente calendar `/admin/meetings`.
 * Per R23 strict: cliente-scoped sub-views move out · either into
 * project-scoped (cliente-info · users · etc.) or absorb into cross-cliente
 * tools (meetings · finance · pipeline) where multi-tenant makes sense.
 *
 * Meetings cross-cliente IS legitimate per directive · "Reuniones" remains
 * in admin TOP_NAV. Per-cliente historic filter is lost in MVP simplification
 * (Marcos scrolls calendar by date · NOT by cliente).
 *
 * Future-1.E.per-project-meetings-subpage: if Marcos demand-driven post-piloto,
 * create /admin/projects/[id]/meetings sub-page filtered by project_id (needs
 * backend extension to MeetingsHistoryTable accept project_id param).
 */
import { redirect } from "next/navigation";

export default function LegacyClientMeetingsRedirect() {
  redirect("/admin/meetings");
}
