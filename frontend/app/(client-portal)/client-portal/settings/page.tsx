import Link from "next/link";
import { Bell, ShieldCheck, Smartphone, User } from "lucide-react";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/**
 * #27 · Hub de Ajustes del cliente · reúne en un solo sitio todo lo configurable
 * (antes disperso: /settings/notifications + /settings/mfa + /account + /whatsapp,
 * sin índice → /client-portal/settings daba 404). Accesible desde el sidebar.
 * R29 friendly · cards de fondo sólido (nada translúcido).
 */
const SETTINGS_LINKS = [
  {
    href: "/client-portal/settings/notifications",
    icon: Bell,
    title: "Tus avisos",
    description: "Cómo y cuándo te avisamos (email, horario, canales).",
  },
  {
    href: "/client-portal/settings/mfa",
    icon: ShieldCheck,
    title: "Seguridad (verificación en dos pasos)",
    description: "Activa o gestiona el segundo factor de tu cuenta.",
  },
  {
    href: "/client-portal/account",
    icon: User,
    title: "Mi cuenta",
    description: "Tus datos de acceso y tu contraseña.",
  },
  {
    href: "/client-portal/whatsapp",
    icon: Smartphone,
    title: "WhatsApp",
    description: "Recibe avisos por WhatsApp (opcional).",
  },
];

export default function ClientSettingsHubPage() {
  return (
    <main
      className="mx-auto max-w-3xl px-6 py-8"
      data-testid="client-settings-hub"
    >
      <h1 className="mb-2 text-2xl font-bold">Ajustes</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Todo lo que puedes configurar de tu portal, en un solo sitio. Sin prisa
        por tu parte · cambia lo que necesites cuando lo necesites.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {SETTINGS_LINKS.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700"
              data-testid={`client-settings-link-${item.href
                .split("/")
                .pop()}`}
            >
              <Card className="h-full bg-white transition-colors hover:border-fulkro-primary-700/40">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Icon
                      size={18}
                      className="text-fulkro-primary-700"
                      aria-hidden="true"
                    />
                    {item.title}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {item.description}
                  </p>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>
    </main>
  );
}
