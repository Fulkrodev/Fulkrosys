"use client";

/**
 * Admin project users page · sub-atom 1.E.2.bis Phase C.
 *
 * Lista los client_users (M21) asociados al CLIENT del project activo
 * (FK client_users.client_id). Reusa cockpit_router endpoints existing:
 *   - GET    /api/v1/clients/{client_id}/users
 *   - POST   /api/v1/clients/{client_id}/users
 *   - POST   /api/v1/clients/{client_id}/users/{user_id}/reset-password
 *   - POST   /api/v1/clients/{client_id}/users/{user_id}/resend-invite
 *   - DELETE /api/v1/clients/{client_id}/users/{user_id}
 *
 * Cliente_users belong to a CLIENT, not project (ADR-013 v3) · same set
 * cross all projects of the client. Para piloto MEDIA 1 cliente ≈ 1 proyecto
 * típico esto = "usuarios del portal cliente".
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  KeyRound,
  Loader2,
  Mail,
  RotateCw,
  UserMinus,
  UserPlus,
} from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TempPasswordReveal } from "@/components/admin/TempPasswordReveal";
import {
  cockpitCreateUser,
  cockpitDeactivate,
  cockpitResendInvite,
  cockpitResetPassword,
  listCockpitUsers,
} from "@/lib/admin-clients/api";
import type { CockpitUserOut } from "@/lib/admin-clients/schemas";
import { useActiveProjectStore } from "@/lib/stores/active-project-store";

interface PageProps {
  params: { id: string };
}

export default function ProjectUsersPage(_props: PageProps) {
  const activeProject = useActiveProjectStore((s) => s.activeProject);
  const clientId = activeProject?.clientId ?? "";

  const usersQuery = useQuery({
    queryKey: ["client-users", clientId],
    queryFn: () => listCockpitUsers(clientId),
    enabled: Boolean(clientId),
    staleTime: 30_000,
  });

  if (!clientId) {
    return (
      <Alert variant="info">
        <AlertTitle>Cargando proyecto…</AlertTitle>
        <AlertDescription>
          Esperando contexto del proyecto activo para mostrar usuarios.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="flex flex-col gap-5" data-testid="project-users-page">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-fulkro-primary-700">
            Usuarios del portal cliente
          </h2>
          <p className="text-sm text-fulkro-ink-600">
            Gestiona quién accede al portal de {activeProject?.clientName}.
            Los usuarios reciben un email con su contraseña temporal al ser
            invitados y deben cambiarla en el primer acceso.
          </p>
        </div>
        <InviteUserDialog clientId={clientId} />
      </header>

      {usersQuery.isLoading ? (
        <Card>
          <CardContent className="flex items-center gap-2 p-6 text-sm text-fulkro-ink-500">
            <Loader2 size={14} className="animate-spin" /> cargando usuarios…
          </CardContent>
        </Card>
      ) : usersQuery.isError ? (
        <Alert variant="danger">
          <AlertTitle>No se pudo cargar usuarios</AlertTitle>
          <AlertDescription>
            {usersQuery.error instanceof Error
              ? usersQuery.error.message
              : "Error desconocido"}
          </AlertDescription>
        </Alert>
      ) : (
        <UsersTable
          users={usersQuery.data ?? []}
          clientId={clientId}
        />
      )}
    </div>
  );
}

function UsersTable({
  users,
  clientId,
}: {
  users: CockpitUserOut[];
  clientId: string;
}) {
  if (users.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
          <Mail size={24} className="text-fulkro-ink-500" />
          <div>
            <p className="font-medium text-fulkro-ink-700">
              Aún no hay usuarios del portal para este cliente.
            </p>
            <p className="text-sm text-fulkro-ink-500">
              Pulsa &ldquo;Invitar usuario&rdquo; para enviar el primer acceso.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <table
          className="w-full text-sm"
          data-testid="client-users-table"
        >
          <thead className="border-b border-fulkro-ink-200 bg-fulkro-ink-50/50 text-left text-xs uppercase tracking-wider text-fulkro-ink-600">
            <tr>
              <th className="px-4 py-2 font-semibold">Email</th>
              <th className="px-4 py-2 font-semibold">Nombre</th>
              <th className="px-4 py-2 font-semibold">Estado</th>
              <th className="px-4 py-2 font-semibold">Último acceso</th>
              <th className="px-4 py-2 text-right font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <UserRow key={u.id} user={u} clientId={clientId} />
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function UserRow({
  user,
  clientId,
}: {
  user: CockpitUserOut;
  clientId: string;
}) {
  const queryClient = useQueryClient();
  const [resetPwd, setResetPwd] = React.useState<string | null>(null);

  const resetMut = useMutation({
    mutationFn: () => cockpitResetPassword(clientId, user.id),
    onSuccess: (data) => {
      // §1.8: la contraseña se muestra en un diálogo persistente con botón
      // "Copiar" (no en un toast auto-desechable que podía perderse).
      setResetPwd(data.temp_password);
    },
    onError: (err: Error) => toast.error(`Reset falló: ${err.message}`),
  });

  const resendMut = useMutation({
    mutationFn: () => cockpitResendInvite(clientId, user.id),
    onSuccess: () => toast.success("Email de invitación reenviado"),
    onError: (err: Error) => toast.error(`Reenvío falló: ${err.message}`),
  });

  const deactivateMut = useMutation({
    mutationFn: () => cockpitDeactivate(clientId, user.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["client-users", clientId],
      });
      toast.success("Usuario revocado");
    },
    onError: (err: Error) => toast.error(`Revocación falló: ${err.message}`),
  });

  const busy =
    resetMut.isPending || resendMut.isPending || deactivateMut.isPending;

  return (
    <>
      <TempPasswordReveal
        tempPassword={resetPwd}
        onClose={() => setResetPwd(null)}
        title="Contraseña temporal generada"
        description={`Nueva contraseña temporal para ${user.email}. Cópiala y entrégasela por un canal seguro. El usuario deberá cambiarla en su primer acceso.`}
      />
      <tr
        className="border-b border-fulkro-ink-100"
        data-testid={`client-user-row-${user.id}`}
      >
      <td className="px-4 py-3 font-mono text-xs">{user.email}</td>
      <td className="px-4 py-3">{user.full_name ?? "—"}</td>
      <td className="px-4 py-3">
        {user.deactivated ? (
          <Badge variant="secondary" className="text-[10px]">
            Revocado
          </Badge>
        ) : user.locked ? (
          <Badge variant="warning" className="text-[10px]">
            Bloqueado
          </Badge>
        ) : user.must_change_password ? (
          <Badge variant="info" className="text-[10px]">
            Pendiente activar
          </Badge>
        ) : (
          <Badge variant="success" className="text-[10px]">
            <CheckCircle2 size={10} /> Activo
          </Badge>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-fulkro-ink-500">
        {user.last_login ? new Date(user.last_login).toLocaleString("es-ES") : "—"}
      </td>
      <td className="px-4 py-3 text-right">
        {!user.deactivated && (
          <div className="inline-flex items-center gap-1">
            <Button
              size="sm"
              variant="outline"
              onClick={() => resendMut.mutate()}
              disabled={busy}
              data-testid={`user-resend-${user.id}`}
            >
              <RotateCw size={11} />
              Reenviar
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => resetMut.mutate()}
              disabled={busy}
              data-testid={`user-reset-${user.id}`}
            >
              <KeyRound size={11} />
              Reset
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => deactivateMut.mutate()}
              disabled={busy}
              data-testid={`user-revoke-${user.id}`}
            >
              <UserMinus size={11} />
              Revocar
            </Button>
          </div>
        )}
        </td>
      </tr>
    </>
  );
}

function InviteUserDialog({ clientId }: { clientId: string }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [email, setEmail] = React.useState("");
  const [fullName, setFullName] = React.useState("");
  const [invitePwd, setInvitePwd] = React.useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      cockpitCreateUser(clientId, {
        email: email.trim(),
        full_name: fullName.trim(),
      }),
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({
        queryKey: ["client-users", clientId],
      });
      const tempPwd = data.temp_password;
      setOpen(false);
      setEmail("");
      setFullName("");
      if (tempPwd) {
        // §1.8: contraseña en diálogo persistente con "Copiar", no en toast.
        setInvitePwd(tempPwd);
      } else {
        toast.success("Usuario invitado · email enviado");
      }
    },
    onError: (err: Error) => toast.error(`Invitación falló: ${err.message}`),
  });

  const canSubmit =
    email.includes("@") && fullName.trim().length >= 3 && !mutation.isPending;

  return (
    <>
      <TempPasswordReveal
        tempPassword={invitePwd}
        onClose={() => setInvitePwd(null)}
        title="Usuario creado"
        description="Contraseña temporal del nuevo usuario. Cópiala y entrégasela por un canal seguro. Deberá cambiarla en su primer acceso."
      />
      <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="primary" size="md" data-testid="invite-user-trigger">
          <UserPlus size={13} />
          Invitar usuario
        </Button>
      </DialogTrigger>
      <DialogContent
        className="sm:max-w-md"
        data-testid="invite-user-modal"
      >
        <DialogHeader>
          <DialogTitle>Invitar usuario al portal</DialogTitle>
          <DialogDescription>
            Se enviará un email con la contraseña temporal. El usuario debe
            cambiarla en su primer acceso.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="invite-email">Email</Label>
            <Input
              id="invite-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="usuario@cliente.com"
              disabled={mutation.isPending}
              data-testid="invite-email-input"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="invite-name">Nombre completo</Label>
            <Input
              id="invite-name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Nombre y apellidos"
              disabled={mutation.isPending}
              data-testid="invite-name-input"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={mutation.isPending}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            variant="primary"
            disabled={!canSubmit}
            onClick={() => mutation.mutate()}
            data-testid="invite-user-submit"
          >
            {mutation.isPending ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <UserPlus size={13} />
            )}
            Invitar
          </Button>
        </DialogFooter>
      </DialogContent>
      </Dialog>
    </>
  );
}
