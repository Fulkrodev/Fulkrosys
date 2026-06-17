"use client";

import * as React from "react";
import {
  Download,
  File as FileIcon,
  FileImage,
  FileSpreadsheet,
  FileText,
  Loader2,
  Trash2,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import type { ColumnDef } from "@tanstack/react-table";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { cn } from "@/lib/utils";

import {
  useDeleteFile,
  useUploadFile,
  useWorkspaceFiles,
} from "@/hooks/useWorkspace";
import {
  downloadWorkspaceFile,
  fileToBase64,
  type WorkspaceFile,
} from "@/lib/admin-workspace/api";

export interface FilesTabProps {
  projectId: string;
}

const MAX_FILE_SIZE_MB = 50;

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function MimeIcon({ mime }: { mime: string | null }) {
  const m = mime ?? "";
  if (m.startsWith("image/")) return <FileImage className="size-4 text-fulkro-info" />;
  if (m.includes("spreadsheet") || m.includes("excel"))
    return <FileSpreadsheet className="size-4 text-fulkro-success" />;
  if (m.includes("pdf") || m.includes("document") || m.startsWith("text/"))
    return <FileText className="size-4 text-fulkro-primary-700" />;
  return <FileIcon className="size-4 text-fulkro-ink-500" />;
}

interface UploadingFile {
  id: string;
  name: string;
  size: number;
  status: "queued" | "uploading" | "done" | "error";
  error?: string;
}

export function FilesTab({ projectId }: FilesTabProps) {
  const { data: files = [], isLoading } = useWorkspaceFiles(projectId);
  const uploadMutation = useUploadFile(projectId);
  const deleteMutation = useDeleteFile(projectId);

  const [uploading, setUploading] = React.useState<UploadingFile[]>([]);
  const [detail, setDetail] = React.useState<WorkspaceFile | null>(null);
  const [isDragging, setIsDragging] = React.useState(false);
  const [downloading, setDownloading] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // S28b: descarga real del binario desde MinIO (antes el botón estaba disabled
  // y, de hecho, el upload ni guardaba el contenido). Obtiene el Blob y dispara
  // la descarga del navegador con el nombre original.
  const handleDownload = async (file: WorkspaceFile) => {
    setDownloading(true);
    try {
      const blob = await downloadWorkspaceFile(projectId, file.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = file.nombre;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(
        `No se pudo descargar: ${err instanceof Error ? err.message : "error"}`,
      );
    } finally {
      setDownloading(false);
    }
  };

  const handleUploadFiles = async (fileList: FileList | File[]) => {
    const arr = Array.from(fileList);
    if (arr.length === 0) return;

    const queued: UploadingFile[] = arr.map((f, i) => ({
      id: `${Date.now()}-${i}-${f.name}`,
      name: f.name,
      size: f.size,
      status: "queued",
    }));
    setUploading((prev) => [...prev, ...queued]);

    for (let i = 0; i < arr.length; i++) {
      const f = arr[i];
      const id = queued[i].id;

      if (f.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        setUploading((prev) =>
          prev.map((u) =>
            u.id === id ? { ...u, status: "error", error: `> ${MAX_FILE_SIZE_MB}MB` } : u,
          ),
        );
        toast.error(`${f.name}: excede ${MAX_FILE_SIZE_MB}MB`);
        continue;
      }

      setUploading((prev) =>
        prev.map((u) => (u.id === id ? { ...u, status: "uploading" } : u)),
      );

      try {
        const b64 = await fileToBase64(f);
        await uploadMutation.mutateAsync({
          nombre: f.name,
          carpeta: "/",
          contenido_base64: b64,
          tipo_mime: f.type || "application/octet-stream",
          subido_por: "marcos",
        });
        setUploading((prev) =>
          prev.map((u) => (u.id === id ? { ...u, status: "done" } : u)),
        );
        toast.success(`${f.name} subido`);
      } catch (err) {
        setUploading((prev) =>
          prev.map((u) =>
            u.id === id ? { ...u, status: "error", error: String(err) } : u,
          ),
        );
        toast.error(`${f.name}: error al subir`);
      }
    }

    // Limpia los completados después de 3s
    setTimeout(() => {
      setUploading((prev) => prev.filter((u) => u.status !== "done"));
    }, 3000);
  };

  const handleDelete = (file: WorkspaceFile) => {
    if (!confirm(`¿Eliminar "${file.nombre}"?`)) return;
    deleteMutation.mutate(file.id, {
      onSuccess: () => toast.success("Archivo eliminado"),
      onError: () => toast.error("Error al eliminar"),
    });
  };

  const columns: ColumnDef<WorkspaceFile>[] = [
    {
      accessorKey: "nombre",
      header: "Archivo",
      cell: ({ row }) => (
        <button
          type="button"
          onClick={() => setDetail(row.original)}
          className="flex items-center gap-2 text-left font-medium text-fulkro-primary-700 hover:underline"
        >
          <MimeIcon mime={row.original.tipo_mime} />
          {row.original.nombre}
        </button>
      ),
    },
    {
      accessorKey: "tamano_bytes",
      header: "Tamaño",
      cell: ({ row }) => formatBytes(row.original.tamano_bytes),
    },
    {
      accessorKey: "hash_sha256",
      header: () => (
        <span className="inline-flex items-center gap-1">
          SHA-256 <TooltipENS term="cadena_custodia" />
        </span>
      ),
      cell: ({ row }) =>
        row.original.hash_sha256 ? (
          <span className="font-mono text-xs text-fulkro-ink-500">
            {row.original.hash_sha256.slice(0, 12)}…
          </span>
        ) : (
          <span className="text-fulkro-ink-300">—</span>
        ),
    },
    {
      accessorKey: "subido_por",
      header: "Subido por",
      cell: ({ row }) => row.original.subido_por ?? "—",
    },
    {
      accessorKey: "subido_at",
      header: "Subido",
      cell: ({ row }) =>
        row.original.subido_at
          ? new Date(row.original.subido_at).toLocaleString("es-ES", {
              dateStyle: "short",
              timeStyle: "short",
            })
          : "—",
    },
    {
      accessorKey: "estado",
      header: "Estado",
      cell: ({ row }) => {
        const e = row.original.estado;
        if (e === "active") return <Badge variant="info">staging</Badge>;
        if (e === "archived") return <Badge variant="secondary">archivado</Badge>;
        if (e === "deleted") return <Badge variant="danger">borrado</Badge>;
        return <Badge variant="outline">{e}</Badge>;
      },
    },
    {
      id: "acciones",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => handleDelete(row.original)}
            disabled={deleteMutation.isPending}
            title="Eliminar"
          >
            <Trash2 className="size-3.5 text-destructive" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <FileIcon size={18} className="text-fulkro-primary-700" />
          <h3 className="text-base font-semibold">
            Archivos del workspace
            <span className="ml-2 text-sm font-normal text-fulkro-ink-500">
              ({files.length})
            </span>
          </h3>
          <TooltipENS term="cadena_custodia" />
        </div>
        <Button
          type="button"
          variant="primary"
          onClick={() => inputRef.current?.click()}
        >
          <Upload className="mr-2 size-4" />
          Subir archivos
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleUploadFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (e.dataTransfer.files.length > 0) {
            handleUploadFiles(e.dataTransfer.files);
          }
        }}
        className={cn(
          "rounded-lg border-2 border-dashed p-6 text-center transition-colors",
          isDragging
            ? "border-fulkro-primary-700 bg-fulkro-primary-700/5"
            : "border-fulkro-ink-200 bg-fulkro-canvas",
        )}
      >
        <Upload className="mx-auto size-6 text-fulkro-ink-500" />
        <p className="mt-2 text-sm text-fulkro-ink-700">
          Arrastra archivos aquí o{" "}
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="text-fulkro-primary-700 underline"
          >
            selecciona desde el equipo
          </button>
        </p>
        <p className="mt-1 text-xs text-fulkro-ink-500">
          Máximo {MAX_FILE_SIZE_MB}MB por archivo
        </p>
      </div>

      {uploading.length > 0 ? (
        <div className="space-y-1">
          {uploading.map((u) => (
            <div
              key={u.id}
              className="flex items-center justify-between rounded border border-fulkro-ink-100 bg-white p-2 text-sm"
            >
              <div className="flex items-center gap-2">
                {u.status === "uploading" || u.status === "queued" ? (
                  <Loader2 className="size-3.5 animate-spin text-fulkro-info" />
                ) : u.status === "done" ? (
                  <Badge variant="success">listo</Badge>
                ) : (
                  <Badge variant="danger">error</Badge>
                )}
                <span className="font-mono text-xs">{u.name}</span>
                <span className="text-xs text-fulkro-ink-500">{formatBytes(u.size)}</span>
              </div>
              {u.error ? <span className="text-xs text-destructive">{u.error}</span> : null}
            </div>
          ))}
        </div>
      ) : null}

      <DataTable
        columns={columns}
        data={files}
        searchKey="nombre"
        searchPlaceholder="Buscar archivos…"
        loading={isLoading}
        emptyState={
          <div className="flex flex-col items-center gap-2 py-10 text-fulkro-ink-500">
            <FileIcon className="size-8" />
            <p className="text-sm">Sin archivos · sube con drag-drop o el botón</p>
          </div>
        }
      />

      <Sheet
        open={detail !== null}
        onOpenChange={(open) => {
          if (!open) setDetail(null);
        }}
      >
        <SheetContent className="w-full sm:max-w-md">
          {detail ? (
            <>
              <SheetHeader>
                <SheetTitle className="break-all">{detail.nombre}</SheetTitle>
                <SheetDescription>
                  {detail.tipo_mime ?? "tipo desconocido"} · {formatBytes(detail.tamano_bytes)}
                </SheetDescription>
              </SheetHeader>
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Carpeta</dt>
                  <dd className="font-mono text-xs">{detail.carpeta ?? "/"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">SHA-256</dt>
                  <dd className="break-all font-mono text-xs">{detail.hash_sha256 ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Versión</dt>
                  <dd>{detail.version ?? "—"}</dd>
                </div>
                <div>
                  <dt className="font-medium text-fulkro-ink-700">Storage path</dt>
                  <dd className="break-all font-mono text-xs">{detail.storage_path ?? "—"}</dd>
                </div>
                <div className="pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={downloading}
                    onClick={() => void handleDownload(detail)}
                  >
                    {downloading ? (
                      <Loader2 className="mr-2 size-4 animate-spin" />
                    ) : (
                      <Download className="mr-2 size-4" />
                    )}
                    Descargar
                  </Button>
                </div>
              </dl>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
