/**
 * DocumentTreeClient · 1.C.G.B v3.10 · arborescencia carpetas friendly mode cliente.
 *
 * Mirror DocumentTreeAdmin (1.C.G.A) adaptado tono cliente · R29 + R30 inverso:
 * - Tono warm + organizado · NO técnico denso admin
 * - Counts badges per folder (ayudan organización · NO presión)
 * - NO admin lingo (audit · permissions · workflow status)
 *
 * Backend endpoint flat list: GET /api/v1/client-portal/folders/tree.
 * Frontend reconstituye árbol jerárquico via parent_folder_id.
 */
"use client";

import {
  ChevronDown,
  ChevronRight,
  Folder,
  FolderOpen,
  Inbox,
} from "lucide-react";
import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ClientApiError } from "@/lib/client-portal-api";
import {
  getClientFoldersTree,
  type ClientFolderNode,
} from "@/lib/api/files-extended";
import { cn } from "@/lib/utils";

interface DocumentTreeClientProps {
  selectedFolderId: string | null;
  onSelectFolder: (folderId: string | null) => void;
  countsByFolder?: Record<string, number>;
}

interface UseClientFoldersResult {
  nodes: ClientFolderNode[];
  loading: boolean;
  error: string | null;
}

function useClientFolders(): UseClientFoldersResult {
  const [flat, setFlat] = React.useState<ClientFolderNode[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await getClientFoldersTree();
        if (!cancelled) setFlat(list);
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ClientApiError) setError(err.message);
        else setError("No se pudieron cargar las carpetas");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const nodes = React.useMemo<ClientFolderNode[]>(() => {
    if (flat.length === 0) return [];
    const map = new Map<string, ClientFolderNode>(
      flat.map((f) => [f.id, { ...f, children: [] }]),
    );
    const roots: ClientFolderNode[] = [];
    map.forEach((node) => {
      if (node.parent_folder_id && map.has(node.parent_folder_id)) {
        map.get(node.parent_folder_id)!.children!.push(node);
      } else {
        roots.push(node);
      }
    });
    return roots;
  }, [flat]);

  return { nodes, loading, error };
}

export function DocumentTreeClient({
  selectedFolderId,
  onSelectFolder,
  countsByFolder = {},
}: DocumentTreeClientProps) {
  const { nodes, loading, error } = useClientFolders();

  if (loading) {
    return (
      <div className="space-y-1.5 p-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-6 w-full" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="p-3 text-xs text-fulkro-danger">{error}</p>;
  }

  if (nodes.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-fulkro-ink-600">
        <Inbox className="mx-auto mb-2 h-4 w-4" />
        Aún no hay carpetas en este proyecto.
      </div>
    );
  }

  return (
    <div className="space-y-0.5 p-1">
      <button
        type="button"
        onClick={() => onSelectFolder(null)}
        className={cn(
          "flex w-full items-center gap-1.5 rounded px-2 py-1.5 text-left text-sm text-fulkro-ink-700 hover:bg-fulkro-ink-100",
          selectedFolderId === null && "bg-fulkro-primary-50 font-semibold",
        )}
      >
        <FolderOpen size={14} aria-hidden />
        <span>Todos mis documentos</span>
      </button>
      {nodes.map((node) => (
        <ClientFolderRow
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

function ClientFolderRow({
  node,
  depth,
  selectedFolderId,
  onSelectFolder,
  countsByFolder,
}: {
  node: ClientFolderNode;
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
          "flex items-center gap-1 rounded px-2 py-1.5 text-sm text-fulkro-ink-700 hover:bg-fulkro-ink-100",
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
          {count > 0 ? (
            <Badge
              variant="secondary"
              className="ml-auto h-4 px-1.5 text-[9px] tabular-nums"
              aria-label={`${count} documentos`}
            >
              {count}
            </Badge>
          ) : null}
        </button>
      </div>
      {expanded && hasChildren ? (
        <div>
          {node.children!.map((child) => (
            <ClientFolderRow
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
