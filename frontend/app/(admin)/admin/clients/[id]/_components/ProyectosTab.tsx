"use client";

import { useEffect, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DataTable } from "@/components/ui/data-table";

import { ApiError } from "@/lib/api";
import { listClientProjects } from "@/lib/admin-clients/api";
import type { ProjectOut } from "@/lib/admin-clients/schemas";

export function ProyectosTab({ clientId }: { clientId: string }) {
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listClientProjects(clientId)
      .then(setProjects)
      .catch((err) => {
        setError(
          err instanceof ApiError
            ? `Error ${err.status}: ${err.message}`
            : "Error al cargar proyectos",
        );
      })
      .finally(() => setLoading(false));
  }, [clientId]);

  const columns: ColumnDef<ProjectOut>[] = [
    {
      accessorKey: "nombre",
      header: "Nombre proyecto",
      cell: ({ row }) => (
        <span className="font-medium text-fulkro-primary-700">
          {row.original.nombre}
        </span>
      ),
    },
    {
      accessorKey: "categoria_objetivo",
      header: "Categoría ENS",
      cell: ({ row }) =>
        row.original.categoria_objetivo ? (
          <Badge variant="secondary">{row.original.categoria_objetivo}</Badge>
        ) : (
          "—"
        ),
    },
    {
      accessorKey: "fase",
      header: "Fase",
      cell: ({ row }) => row.original.fase ?? "—",
    },
    {
      accessorKey: "estado",
      header: "Estado",
      cell: ({ row }) =>
        row.original.estado ? (
          <Badge variant="outline">{row.original.estado}</Badge>
        ) : (
          "—"
        ),
    },
    {
      accessorKey: "created_at",
      header: "Creado",
      cell: ({ row }) =>
        new Date(row.original.created_at).toLocaleDateString("es-ES"),
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Proyectos asociados</CardTitle>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 rounded border border-fulkro-danger/40 bg-fulkro-danger/10 p-3 text-sm text-fulkro-danger">
            {error}
          </div>
        )}
        <DataTable
          columns={columns}
          data={projects}
          loading={loading}
          pageSize={25}
        />
      </CardContent>
    </Card>
  );
}
