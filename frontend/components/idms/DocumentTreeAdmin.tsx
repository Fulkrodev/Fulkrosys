/**
 * DocumentTreeAdmin · 1.C.G.A v3.10 · admin tree view 15 carpetas K.0..K.6+retainer.
 *
 * Reuse endpoint existing GET /api/v1/idms/projects/{id}/idms/folders/tree.
 * Recursive render expandible · count documents per folder badge.
 */
"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Folder, FolderOpen } from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { idmsApi, type IdmsFolderNode } from "@/lib/api/idms";
import { cn } from "@/lib/utils";

interface DocumentTreeAdminProps {
  projectId: string;
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
}

export function DocumentTreeAdmin({
  projectId,
  selectedFolderId,
  onSelectFolder,
}: DocumentTreeAdminProps) {
  const tree = useQuery({
    queryKey: ["idms", "folder-tree", projectId],
    queryFn: () => idmsApi.folderTree(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  // Counts per folder via single GET documents (client-side aggregation · evita N+1).
  const allDocuments = useQuery({
    queryKey: ["idms", "documents", projectId, "ALL"],
    queryFn: () => idmsApi.listDocuments(projectId),
    enabled: Boolean(projectId),
    staleTime: 15_000,
  });

  const countsByFolder: Record<string, number> = React.useMemo(() => {
    const out: Record<string, number> = {};
    (allDocuments.data?.documents ?? []).forEach((d) => {
      if (d.folder_id) {
        out[d.folder_id] = (out[d.folder_id] ?? 0) + 1;
      }
    });
    return out;
  }, [allDocuments.data]);

  const nodes: IdmsFolderNode[] = React.useMemo(() => {
    if (!tree.data) return [];
    if (Array.isArray(tree.data)) return tree.data;
    return tree.data.tree ?? [];
  }, [tree.data]);

  if (tree.isLoading) {
    return (
      <div className="space-y-1.5 p-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-6 w-full" />
        ))}
      </div>
    );
  }

  if (tree.isError) {
    return (
      <p className="p-3 text-xs text-fulkro-danger">
        Error al cargar árbol de carpetas
      </p>
    );
  }

  if (nodes.length === 0) {
    return (
      <p className="p-3 text-xs text-fulkro-ink-500">
        Sin carpetas. Inicializa las 15 estándar desde el botón superior.
      </p>
    );
  }

  return (
    <div className="space-y-0.5 p-1">
      <button
        type="button"
        onClick={() => onSelectFolder(null)}
        className={cn(
          "flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-sm hover:bg-fulkro-ink-100",
          selectedFolderId === null && "bg-fulkro-primary-50 font-semibold",
        )}
      >
        <FolderOpen size={14} />
        <span>Todos los documentos</span>
      </button>
      {nodes.map((node) => (
        <FolderRow
          key={node.id}
          node={node}
          depth={0}
          selectedFolderId={selectedFolderId}
          onSelectFolder={onSelectFolder}
          countsByFolder={countsByFolder}
        />
      ))}
    </div>
  );
}

function FolderRow({
  node,
  depth,
  selectedFolderId,
  onSelectFolder,
  countsByFolder,
}: {
  node: IdmsFolderNode;
  depth: number;
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  countsByFolder: Record<string, number>;
}) {
  const hasChildren = Boolean(node.children && node.children.length > 0);
  const [expanded, setExpanded] = React.useState(depth === 0);
  const isActive = selectedFolderId === node.id;
  const count = countsByFolder[node.id] ?? 0;

  return (
    <div>
      <div
        className={cn(
          "flex items-center gap-1 rounded px-2 py-1 text-sm hover:bg-fulkro-ink-100",
          isActive && "bg-fulkro-primary-50 font-semibold",
        )}
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        {hasChildren ? (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="rounded p-0.5 hover:bg-fulkro-ink-200"
            aria-label={expanded ? "Colapsar" : "Expandir"}
          >
            {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          </button>
        ) : (
          <span className="w-4" />
        )}
        <button
          type="button"
          onClick={() => onSelectFolder(node.id)}
          className="flex flex-1 items-center gap-1.5 text-left"
        >
          {expanded && hasChildren ? <FolderOpen size={13} /> : <Folder size={13} />}
          <span className="truncate">{node.name}</span>
          <span className="ml-auto flex items-center gap-1">
            {count > 0 ? (
              <Badge
                variant="secondary"
                className="h-4 px-1.5 text-[9px] tabular-nums"
                aria-label={`${count} documentos`}
              >
                {count}
              </Badge>
            ) : null}
            {node.is_standard && node.standard_code ? (
              <Badge variant="outline" className="h-4 px-1 text-[9px]">
                K.{node.standard_code}
              </Badge>
            ) : null}
          </span>
        </button>
      </div>
      {expanded && hasChildren ? (
        <div>
          {node.children!.map((child) => (
            <FolderRow
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedFolderId={selectedFolderId}
              onSelectFolder={onSelectFolder}
              countsByFolder={countsByFolder}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
