import { redirect } from "next/navigation";

/**
 * #28 · Las preferencias de notificación del cliente se fusionaron en una sola
 * página: /client-portal/settings/notifications (entrada única desde el hub de
 * Ajustes #27). Esta ruta se conserva como redirect para no romper enlaces
 * antiguos.
 */
export default function LegacyNotificationsRedirect() {
  redirect("/client-portal/settings/notifications");
}
