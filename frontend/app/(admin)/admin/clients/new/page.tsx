/**
 * Legacy redirect · sub-atom 1.D.F.0.A v3.11.
 *
 * `/admin/clients/new` se consolida en `/admin/projects/new` (entry point
 * único con wizard diagnóstico ENS 6 steps). URL legacy preservada para
 * bookmarks · redirect inmediato.
 *
 * R23 sostener firmísimo · sin duda técnica · única ruta de creación.
 */
import { redirect } from "next/navigation";

export default function LegacyNewClientRedirect() {
  redirect("/admin/projects/new");
}
