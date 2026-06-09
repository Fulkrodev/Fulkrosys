"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { ApiError } from "@/lib/api";
import {
  cockpitDeactivate,
  cockpitResendInvite,
  cockpitResetPassword,
  listCockpitUsers,
} from "@/lib/admin-clients/api";
import type { CockpitUserOut } from "@/lib/admin-clients/schemas";

export function UsuariosTab({ clientId }: { clientId: string }) {
  const [users, setUsers] = useState<CockpitUserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listCockpitUsers(clientId);
      setUsers(list);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al cargar usuarios",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchUsers();
    // fetchUsers depends only on clientId; declarando aquí evita
    // re-fetches innecesarios y satisface react-hooks/exhaustive-deps
    // sin useCallback (overkill para este caso simple).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId]);

  const handleResendInvite = async (userId: string) => {
    try {
      await cockpitResendInvite(clientId, userId);
      toast.success("Invitación reenviada");
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al reenviar invite",
      );
    }
  };

  const handleResetPassword = async (userId: string) => {
    try {
      const result = await cockpitResetPassword(clientId, userId);
      toast.success(
        `Password reset · temp: ${result.temp_password}`,
        { duration: 10000 },
      );
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al reset password",
      );
    }
  };

  const handleDeactivate = async (userId: string) => {
    try {
      await cockpitDeactivate(clientId, userId);
      toast.success("Usuario desactivado");
      await fetchUsers();
    } catch (err) {
      toast.error(
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error al desactivar",
      );
    }
  };

  const columns: ColumnDef<CockpitUserOut>[] = [
    { accessorKey: "email", header: "Email" },
    { accessorKey: "full_name", header: "Nombre" },
    {
      id: "scope",
      header: "Acceso",
      cell: () => (
        <Badge variant="secondary">RW</Badge>
      ),
    },
    {
      accessorKey: "deactivated",
      header: "Estado",
      cell: ({ row }) =>
        row.original.deactivated ? (
          <Badge variant="outline">Inactivo</Badge>
        ) : (
          <Badge variant="default">Activo</Badge>
        ),
    },
    {
      accessorKey: "last_login",
      header: "Última conexión",
      cell: ({ row }) =>
        row.original.last_login
          ? new Date(row.original.last_login).toLocaleDateString("es-ES")
          : "—",
    },
    {
      id: "actions",
      header: "",
      cell: ({ row }) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm">
              ⋯
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() => void handleResendInvite(row.original.id)}
            >
              Reenviar invitación
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => void handleResetPassword(row.original.id)}
            >
              Reset password
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => void handleDeactivate(row.original.id)}
              className="text-fulkro-danger"
            >
              Desactivar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Usuarios cliente</CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 rounded border border-fulkro-danger/40 bg-fulkro-danger/10 p-3 text-sm text-fulkro-danger">
            {error}
          </div>
        )}
        <DataTable
          columns={columns}
          data={users}
          loading={loading}
          searchKey="email"
          searchPlaceholder="Buscar por email..."
          pageSize={25}
        />
      </CardContent>
    </Card>
  );
}
