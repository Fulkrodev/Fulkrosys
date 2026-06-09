"use client";

/**
 * PortalUserPanel · sub-atom 1.C.F.1.
 *
 * Muestra el estado del ClientUser portal del proyecto (m21) + portal
 * contact (m30 has_portal_access=true) · button para crear/asegurar
 * idempotente.
 *
 * ADR-013 v3: 1 ClientUser activo por client. Constraint v3 m30: 1
 * portal contact por project. Si ya existe · NO recrea · informa estado.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

import { ApiError } from "@/lib/api";
import {
  ensurePortalUser,
  getPortalUserStatus,
  type PortalUserStatus,
} from "@/lib/api/project-contacts";

type Props = {
  projectId: string;
};

export function PortalUserPanel({ projectId }: Props) {
  const [status, setStatus] = useState<PortalUserStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [tempPassword, setTempPassword] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getPortalUserStatus(projectId)
      .then((s) => {
        if (!cancelled) setStatus(s);
      })
      .catch((err) => {
        if (!cancelled) {
          const msg =
            err instanceof ApiError
              ? `Error ${err.status}: ${err.message}`
              : "Error cargando estado portal";
          toast.error(msg);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const submit = async () => {
    if (!email || !fullName) {
      toast.error("Email y nombre completo obligatorios");
      return;
    }
    setSubmitting(true);
    try {
      const res = await ensurePortalUser(projectId, {
        email: email.trim(),
        full_name: fullName.trim(),
      });
      if (res.created_user) {
        toast.success("Usuario portal creado");
        setTempPassword(res.temp_password);
      } else {
        toast.info("Usuario portal ya existía. No se duplicó.");
      }
      const refreshed = await getPortalUserStatus(projectId);
      setStatus(refreshed);
      if (!res.created_user) {
        setOpen(false);
      }
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error creando usuario portal";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <Skeleton className="h-32" />;
  }

  const user = status?.client_user;
  const contact = status?.portal_contact;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <div>
          <CardTitle className="text-base">Usuario portal cliente</CardTitle>
          <p className="mt-1 text-sm text-[color:var(--fulkro-muted)]">
            1 ClientUser activo por cliente · 1 contacto portal por proyecto
            (constraints ADR-013 / ADR-046).
          </p>
        </div>
        {!user ? (
          <Button onClick={() => setOpen(true)}>+ Crear usuario portal</Button>
        ) : !contact ? (
          <Button onClick={() => setOpen(true)} variant="outline">
            + Vincular contacto portal
          </Button>
        ) : (
          <Badge variant="success">Listo</Badge>
        )}
      </CardHeader>
      <CardContent>
        {!user ? (
          <p className="text-sm text-[color:var(--fulkro-muted)]">
            Aún no hay usuario portal para este cliente. Crea uno para que el
            cliente pueda acceder a su portal.
          </p>
        ) : (
          <div className="flex flex-col gap-2 text-sm">
            <div>
              <strong>{user.full_name ?? user.email}</strong>{" "}
              <span className="text-[color:var(--fulkro-muted)]">
                · {user.email}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {user.must_change_password ? (
                <Badge variant="warning">Debe cambiar contraseña</Badge>
              ) : (
                <Badge variant="outline">Contraseña activa</Badge>
              )}
              {user.last_login ? (
                <span className="text-[color:var(--fulkro-muted)]">
                  Último login: {new Date(user.last_login).toLocaleString("es-ES")}
                </span>
              ) : (
                <span className="text-[color:var(--fulkro-muted)]">
                  Sin login todavía
                </span>
              )}
            </div>
            {contact ? (
              <div className="mt-2 rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50/40 px-3 py-2">
                <p className="text-xs uppercase tracking-wide text-[color:var(--fulkro-muted)]">
                  Contacto portal · proyecto
                </p>
                <p className="mt-1 font-medium">{contact.full_name}</p>
                <p className="text-sm text-[color:var(--fulkro-muted)]">
                  {contact.role_title} · {contact.email}
                </p>
              </div>
            ) : null}
          </div>
        )}
      </CardContent>

      <Dialog
        open={open}
        onOpenChange={(next) => {
          if (!submitting) setOpen(next);
          if (!next) {
            setTempPassword(null);
            setEmail("");
            setFullName("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Crear usuario portal</DialogTitle>
            <DialogDescription>
              Crea un ClientUser activo para que el cliente acceda a su portal
              y un contacto portal en el proyecto. Idempotente: si ya existe
              se reutiliza.
            </DialogDescription>
          </DialogHeader>

          {tempPassword ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm">
                Contraseña temporal generada (cópiala y envíasela al cliente
                desde el flow de invitación):
              </p>
              <code className="rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50 px-3 py-2 font-mono text-sm">
                {tempPassword}
              </code>
              <DialogFooter>
                <Button
                  onClick={() => {
                    void navigator.clipboard.writeText(tempPassword);
                    toast.success("Contraseña copiada");
                  }}
                  variant="outline"
                >
                  Copiar
                </Button>
                <Button onClick={() => setOpen(false)}>Cerrar</Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              <div>
                <Label htmlFor="pu_email">Email cliente *</Label>
                <Input
                  id="pu_email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="cliente@empresa.com"
                />
              </div>
              <div>
                <Label htmlFor="pu_full_name">Nombre completo *</Label>
                <Input
                  id="pu_full_name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Nombre del usuario portal"
                />
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setOpen(false)}
                  disabled={submitting}
                >
                  Cancelar
                </Button>
                <Button onClick={() => void submit()} disabled={submitting}>
                  {submitting ? "Creando…" : "Crear"}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
