/**
 * /ml/consume?token=... → /sign/{token} · #43 (C · routing por purpose).
 *
 * El backend construye el enlace de TODOS los magic-links como
 * {base_url}/ml/consume?token=... (m12 service.py:317) pero el dispatch por
 * purpose vive en /sign/[token]. Esta ruta —que ANTES no existía → 404 para
 * CUALQUIER purpose— reenvía el token al dispatch. ADITIVA: desbloquea el acceso
 * por email de TODO el sistema (auditor ENAC, DPA, conformidad, contrato…), no
 * solo el contrato. Pública (middleware "resto público" · NextResponse.next()).
 */
import { redirect } from "next/navigation";

export default function MlConsumeRedirectPage({
  searchParams,
}: {
  searchParams: { token?: string };
}) {
  const token = searchParams?.token;
  if (token) {
    redirect(`/sign/${encodeURIComponent(token)}`);
  }
  // Sin token → enlace inválido; la raíz decide según rol (middleware).
  redirect("/");
}
