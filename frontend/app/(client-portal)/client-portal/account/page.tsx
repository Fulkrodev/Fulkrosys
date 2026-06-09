"use client";

import { useEffect, useState } from "react";


import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ClientApiError,
  clientApi,
  type ClientMeResponse,
} from "@/lib/client-portal-api";

export default function AccountPage() {
  const [me, setMe] = useState<ClientMeResponse | null>(null);
  const [oldPwd, setOldPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [pwdMsg, setPwdMsg] = useState<string | null>(null);
  const [pwdError, setPwdError] = useState<string | null>(null);

  useEffect(() => {
    clientApi<ClientMeResponse>("/client-portal/me")
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  async function changePwd(e: React.FormEvent) {
    e.preventDefault();
    setPwdMsg(null);
    setPwdError(null);
    try {
      await clientApi("/client-auth/change-password", {
        json: { old_password: oldPwd, new_password: newPwd },
      });
      setPwdMsg("Contraseña actualizada correctamente");
      setOldPwd("");
      setNewPwd("");
    } catch (err) {
      // R29 firmísimo · friendly Spanish · backend message preserved cuando útil
      if (err instanceof ClientApiError) {
        const raw = err.message?.toLowerCase() ?? "";
        if (raw.includes("password") || raw.includes("contraseña") || raw.includes("invalid")) {
          setPwdError(
            "La contraseña actual no es correcta. Inténtalo de nuevo.",
          );
        } else {
          setPwdError(
            "No pudimos cambiar tu contraseña. Vuelve a intentarlo · si sigue pasando avisa a Marcos.",
          );
        }
      } else {
        setPwdError(
          "No pudimos cambiar tu contraseña. Vuelve a intentarlo · si sigue pasando avisa a Marcos.",
        );
      }
    }
  }

  const inputClass =
    "mt-1 block w-full rounded-md border border-[color:var(--fulkro-surface-glass-border)] bg-white px-3.5 py-2.5 text-base font-medium text-[color:var(--fulkro-body)] focus:border-fulkro-primary-700 focus:outline-none focus:ring-2 focus:ring-fulkro-primary-700/30";
  const labelClass =
    "block text-sm font-bold text-[color:var(--fulkro-subtitle)]";
  const primaryButtonClass =
    "btn-action rounded-md px-5 py-2.5 text-base font-bold";

  return (
    <>

      <main className="mx-auto max-w-3xl space-y-6 px-6 py-8">
        <h1>Mi cuenta</h1>

        <Card>
          <CardHeader>
            <CardTitle>Notificaciones</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-base text-[color:var(--fulkro-body)] mb-3">
              Configura los canales y la ventana de silencio
              para los avisos del proyecto.
            </p>
            <a
              href="/client-portal/account/notifications"
              className="inline-flex items-center font-semibold text-fulkro-primary-700 hover:underline"
              data-testid="link-account-notifications"
            >
              Ir a preferencias de notificación →
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Mis facturas</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-base text-[color:var(--fulkro-body)] mb-3">
              Consulta tus facturas y los datos para el pago por
              transferencia bancaria.
            </p>
            <a
              href="/client-portal/billing"
              className="inline-flex items-center font-semibold text-fulkro-primary-700 hover:underline"
              data-testid="link-account-billing"
            >
              Ir a mis facturas →
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Cambiar contraseña</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={changePwd} className="space-y-4">
              <div>
                <label htmlFor="account-old-pwd" className={labelClass}>
                  Contraseña actual
                </label>
                <input
                  id="account-old-pwd"
                  type="password"
                  autoComplete="current-password"
                  value={oldPwd}
                  onChange={(e) => setOldPwd(e.target.value)}
                  required
                  className={inputClass}
                />
              </div>
              <div>
                <label htmlFor="account-new-pwd" className={labelClass}>
                  Nueva contraseña (mínimo 12 caracteres)
                </label>
                <input
                  id="account-new-pwd"
                  type="password"
                  autoComplete="new-password"
                  value={newPwd}
                  onChange={(e) => setNewPwd(e.target.value)}
                  minLength={12}
                  required
                  className={inputClass}
                />
              </div>
              {pwdError && (
                <p className="rounded-md border border-fulkro-danger/30 bg-fulkro-danger/10 px-4 py-2.5 text-base font-semibold text-fulkro-danger">
                  {pwdError}
                </p>
              )}
              {pwdMsg && (
                <p className="rounded-md border border-fulkro-success/30 bg-fulkro-success/10 px-4 py-2.5 text-base font-semibold text-fulkro-success">
                  {pwdMsg}
                </p>
              )}
              <button type="submit" className={primaryButtonClass}>
                Cambiar contraseña
              </button>
            </form>
          </CardContent>
        </Card>

      </main>
    </>
  );
}
