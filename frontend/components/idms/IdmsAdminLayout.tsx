/**
 * IdmsAdminLayout · 1.C.G.A v3.10 · 2-col workbench gestor documental admin.
 *
 * Composición:
 *   - sidebar izq: DocumentTreeAdmin (15 folders K.0..K.6+retainer)
 *   - main centro: DocumentList per folder selected
 *   - top actions: Upload · Create Folder · Initialize 15 std (idempotent)
 *   - modales overlay: Upload · Viewer · Folder Create · Version History
 *
 * Reuse 27 endpoints existing m24_idms (NO new endpoints backend).
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  FolderPlus,
  FolderTree,
  Loader2,
  Sparkles,
  Upload,
} from "lucide-react";
import * as React from "react";

import { DocumentList } from "@/components/idms/DocumentList";
import { DocumentTreeAdmin } from "@/components/idms/DocumentTreeAdmin";
import { DocumentVersionHistoryModal } from "@/components/idms/DocumentVersionHistoryModal";
import { DocumentViewerModal } from "@/components/idms/DocumentViewerModal";
import { FolderCreateModal } from "@/components/idms/FolderCreateModal";
import { UploadDocumentModal } from "@/components/idms/UploadDocumentModal";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useProjectEvents } from "@/lib/admin-dashboard/useProjectEvents";
import { idmsApi, type IdmsFolderNode } from "@/lib/api/idms";

interface IdmsAdminLayoutProps {
  projectId: string;
}

export function IdmsAdminLayout({ projectId }: IdmsAdminLayoutProps) {
  const queryClient = useQueryClient();
  const [selectedFolderId, setSelectedFolderId] = React.useState<string | null>(
    null,
  );
  const [uploadOpen, setUploadOpen] = React.useState(false);
  const [createFolderOpen, setCreateFolderOpen] = React.useState(false);
  const [viewerDocumentId, setViewerDocumentId] = React.useState<string | null>(
    null,
  );
  const [versionsDocumentId, setVersionsDocumentId] = React.useState<string | null>(
    null,
  );

  const tree = useQuery({
    queryKey: ["idms", "folder-tree", projectId],
    queryFn: () => idmsApi.folderTree(projectId),
    enabled: Boolean(projectId),
    staleTime: 30_000,
  });

  // FIX P2-3 · realtime: cuando el cliente comparte un documento, el gestor
  // documental admin se refresca solo (antes sólo al recargar / cambiar carpeta).
  useProjectEvents({
    projectId,
    onDocumentUploaded: () => {
      queryClient.invalidateQueries({ queryKey: ["idms"] });
    },
  });

  const folderNodes: IdmsFolderNode[] = React.useMemo(() => {
    if (!tree.data) return [];
    if (Array.isArray(tree.data)) return tree.data;
    return tree.data.tree ?? [];
  }, [tree.data]);

  const flatFolders = React.useMemo(() => {
    const out: IdmsFolderNode[] = [];
    function walk(nodes: IdmsFolderNode[]) {
      nodes.forEach((n) => {
        out.push(n);
        if (n.children) walk(n.children);
      });
    }
    walk(folderNodes);
    return out;
  }, [folderNodes]);

  const initialize = useMutation({
    mutationFn: () => idmsApi.initializeFolders(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["idms"] });
    },
  });

  const hasNoFolders = !tree.isLoading && folderNodes.length === 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <FolderTree size={16} />
          Gestor documental (IDMS)
        </CardTitle>
        <div className="flex items-center gap-2">
          {hasNoFolders ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => initialize.mutate()}
              disabled={initialize.isPending}
            >
              {initialize.isPending ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Inicializando…
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  Inicializar 15 carpetas estándar
                </>
              )}
            </Button>
          ) : (
            <>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCreateFolderOpen(true)}
              >
                <FolderPlus size={14} />
                Nueva subcarpeta
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => setUploadOpen(true)}
              >
                <Upload size={14} />
                Subir documento
              </Button>
            </>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 lg:grid-cols-[280px_1fr]">
          <aside className="rounded-lg border border-fulkro-ink-300 bg-fulkro-ink-50/40">
            <p className="border-b border-fulkro-ink-300 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-fulkro-ink-500">
              Estructura · K.0..K.6+retainer
            </p>
            <DocumentTreeAdmin
              projectId={projectId}
              selectedFolderId={selectedFolderId}
              onSelectFolder={setSelectedFolderId}
            />
          </aside>
          <main className="min-w-0">
            <DocumentList
              projectId={projectId}
              folderId={selectedFolderId}
              onOpenDocument={setViewerDocumentId}
              onOpenVersions={setVersionsDocumentId}
            />
          </main>
        </div>
      </CardContent>

      <UploadDocumentModal
        projectId={projectId}
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        folders={folderNodes}
        defaultFolderId={selectedFolderId}
      />
      <FolderCreateModal
        projectId={projectId}
        open={createFolderOpen}
        onOpenChange={setCreateFolderOpen}
        folders={flatFolders}
      />
      <DocumentViewerModal
        projectId={projectId}
        documentId={viewerDocumentId}
        open={viewerDocumentId !== null}
        onOpenChange={(open) => {
          if (!open) setViewerDocumentId(null);
        }}
      />
      <DocumentVersionHistoryModal
        projectId={projectId}
        documentId={versionsDocumentId}
        open={versionsDocumentId !== null}
        onOpenChange={(open) => {
          if (!open) setVersionsDocumentId(null);
        }}
      />
    </Card>
  );
}
