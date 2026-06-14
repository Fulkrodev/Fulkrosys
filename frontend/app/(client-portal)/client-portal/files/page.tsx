"use client";

/**
 * /client-portal/files · SAN-E v3.MB-6 atom 7 · Files extended.
 *
 * 7 decisiones Marcos (Q1-Q7):
 * - Q1 B · scope evidence + documents (workspace defer 7.bis)
 * - Q2 D · hybrid ILIKE backend (SearchBar debounced 300ms)
 * - Q3 D · NO diff (version listing only via FileVersionDialog)
 * - Q4 B · iframe browser native PDF preview (FilePreviewModal)
 * - Q5 A · scan_clean_only filter toggle (evidence tab) + badge visible todos
 * - Q6 B · current + collapsed history
 * - Q7 B · tabs separated documents + evidence
 *
 * Sub-atom 1.C.G.B v3.10 · enriquecimiento gestor documental cliente:
 * - Sidebar tree izq (DocumentTreeClient · friendly mode · counts per folder)
 * - Botón Upload cliente top-right (ClientUploadModal · permission-limited)
 * - Folder filter integrado en useFileSearch
 * - Mantiene tabs hybrid docs+evidence + search + preview existing (NO breaking)
 * - R29 + R30 inverso sostenidos · NO admin metadata · NO presión coercitiva
 */
import {
  AlertCircle,
  FileText,
  FolderSearch,
  Info,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { useMemo, useState } from "react";

import { ClientUploadModal } from "@/components/client-portal/files/ClientUploadModal";
import { DocumentTreeClient } from "@/components/client-portal/files/DocumentTreeClient";
import { FileCard } from "@/components/client-portal/files/FileCard";
import { FilePreviewModal } from "@/components/client-portal/files/FilePreviewModal";
import { FileVersionDialog } from "@/components/client-portal/files/FileVersionDialog";
import { SearchBar } from "@/components/client-portal/files/SearchBar";
import { AgentSuggestionBanner } from "@/components/client-portal/inline-agents/AgentSuggestionBanner";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";
import { useFileSearch } from "@/hooks/useFileSearch";
import { clientApi } from "@/lib/client-portal-api";
import {
  documentDownloadUrl,
  documentPreviewUrl,
  evidenceDownloadUrl,
  evidencePreviewUrl,
  getClientFoldersTree,
  type ClientFolderNode,
} from "@/lib/api/files-extended";
import { useEffect } from "react";
import { cn } from "@/lib/utils";

export default function FilesPage() {
  const {
    tab,
    setTab,
    search,
    setSearch,
    scanCleanOnly,
    setScanCleanOnly,
    folderId,
    setFolderId,
    documents,
    evidence,
    loading,
    error,
    refetch,
  } = useFileSearch("documents");

  const [previewState, setPreviewState] = useState<{
    open: boolean;
    title: string;
    previewUrl: string | null;
    downloadUrl: string | null;
  }>({ open: false, title: "", previewUrl: null, downloadUrl: null });

  const [versionsDocId, setVersionsDocId] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);

  // FIX P2-3 · realtime: cuando Marcos comparte un documento nuevo, la lista del
  // cliente se refresca sola (antes sólo al recargar la página). projectId vía
  // /client-auth/me (single-project · mismo patrón que /certificacion).
  const [projectId, setProjectId] = useState<string | null>(null);
  useEffect(() => {
    void clientApi<{ project_id: string | null }>("/client-auth/me")
      .then((data) => setProjectId(data?.project_id ?? null))
      .catch(() => setProjectId(null));
  }, []);
  useClientProjectEvents(projectId, {
    onDocumentUploaded: () => {
      void refetch();
    },
  });

  // Folders flat (mismo fetch que tree · usados upload modal selector)
  const [folders, setFolders] = useState<ClientFolderNode[]>([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await getClientFoldersTree();
        if (cancelled) return;
        // Reconstituye tree para upload modal
        const map = new Map<string, ClientFolderNode>(
          list.map((f) => [f.id, { ...f, children: [] }]),
        );
        const roots: ClientFolderNode[] = [];
        map.forEach((node) => {
          if (node.parent_folder_id && map.has(node.parent_folder_id)) {
            map.get(node.parent_folder_id)!.children!.push(node);
          } else {
            roots.push(node);
          }
        });
        setFolders(roots);
      } catch {
        // Silent · sidebar muestra su propio error
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Counts per folder client-side (R30 inverso · NO solicitar endpoint admin)
  const countsByFolder = useMemo(() => {
    const out: Record<string, number> = {};
    documents.forEach((d) => {
      if (d.folder_id) out[d.folder_id] = (out[d.folder_id] ?? 0) + 1;
    });
    return out;
  }, [documents]);

  const openDocumentPreview = (id: string) => {
    const doc = documents.find((d) => d.id === id);
    setPreviewState({
      open: true,
      title: doc?.nombre ?? doc?.codigo ?? "Documento",
      previewUrl: documentPreviewUrl(id),
      downloadUrl: documentDownloadUrl(id),
    });
  };

  const openEvidencePreview = (id: string) => {
    const ev = evidence.find((e) => e.id === id);
    setPreviewState({
      open: true,
      title: ev?.fichero_nombre_original ?? "Evidencia",
      previewUrl: evidencePreviewUrl(id),
      downloadUrl: evidenceDownloadUrl(id),
    });
  };

  const downloadDocument = (id: string) => {
    window.location.href = documentDownloadUrl(id);
  };

  const downloadEvidence = (id: string) => {
    window.location.href = evidenceDownloadUrl(id);
  };

  const items = tab === "documents" ? documents : evidence;

  return (
    <div className="space-y-6 px-4 py-6 sm:px-6 md:px-8 max-w-6xl mx-auto pb-32">
      <header className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-fulkro-primary-700">
              <FolderSearch className="h-5 w-5" aria-hidden />
              <span className="text-xs uppercase tracking-wide font-semibold">
                Portal cliente · Mis Documentos
              </span>
            </div>
            <h1 className="text-2xl font-bold text-fulkro-ink-800">
              Mis Documentos
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              size="md"
              onClick={() => {
                window.location.href =
                  "/api/v1/client-portal/dossier/download";
              }}
              data-testid="client-dossier-download-button"
              title="Descarga tu expediente ENS completo: todos los entregables + pentest + remediaciones (ZIP)"
            >
              <FileText size={14} />
              Descargar expediente ENS completo
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={() => setUploadOpen(true)}
              data-testid="client-upload-button"
            >
              <Upload size={14} />
              Compartir documento
            </Button>
          </div>
        </div>
        <p className="text-sm text-fulkro-ink-600 max-w-3xl">
          Sube los documentos que tu consultor te pida (DNI representante,
          contratos proveedores, evidencias internas…). Aquí también verás
          los documentos que Marcos prepara para ti (políticas, procedimientos,
          declaraciones). Navega tus carpetas, busca por nombre, descarga
          cuando lo necesites.
        </p>
      </header>

      {/* Banner R30 inverso · 1.D.F.bis.III.A v3.11 */}
      <Alert data-testid="cliente-files-banner">
        <Info className="size-4" />
        <AlertTitle>Sube los documentos que Marcos te pida</AlertTitle>
        <AlertDescription>
          Tu consultor te indicará desde el chat o &quot;Mis tareas&quot; qué
          documentos necesita de ti (DNI representante · contratos cloud ·
          inventarios internos…). Usa &quot;Compartir documento&quot; arriba a
          la derecha para subirlos. La organización de carpetas la gestiona
          Marcos · tú solo seleccionas dónde guardar cada archivo.
        </AlertDescription>
      </Alert>

      <AgentSuggestionBanner
        slug="a21_discrepancias_scan"
        pageUrl="/client-portal/files"
        dismissKey="files_discrepancias_dismissed"
        tierGatedNote="Detector de discrepancias cross-doc disponible desde categoría MEDIA."
      />

      <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
        {/* Sidebar tree izq · only docs tab (evidence tab NO folder structure) */}
        {tab === "documents" ? (
          <aside
            className="rounded-lg border border-fulkro-ink-200 bg-fulkro-ink-50/40"
            data-testid="client-folders-tree"
          >
            <p className="border-b border-fulkro-ink-200 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-fulkro-ink-600">
              Mis carpetas
            </p>
            <DocumentTreeClient
              selectedFolderId={folderId}
              onSelectFolder={setFolderId}
              countsByFolder={countsByFolder}
            />
          </aside>
        ) : (
          <div className="hidden lg:block" />
        )}

        {/* Main content */}
        <main className="min-w-0 space-y-4">
          <div
            data-testid="files-tabs"
            className="flex gap-2 border-b border-fulkro-ink-200"
          >
            <TabButton
              active={tab === "documents"}
              onClick={() => setTab("documents")}
              testId="files-tab-documents"
              icon={<FileText className="h-4 w-4" aria-hidden />}
              label="Documentos"
            />
            <TabButton
              active={tab === "evidence"}
              onClick={() => setTab("evidence")}
              testId="files-tab-evidence"
              icon={<ShieldCheck className="h-4 w-4" aria-hidden />}
              label="Evidencias"
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <SearchBar
              value={search}
              onChange={setSearch}
              className="flex-1"
            />
            {tab === "evidence" && (
              <label
                data-testid="evidence-scan-clean-toggle"
                className="inline-flex items-center gap-2 rounded-lg border border-fulkro-ink-200 bg-white px-3 py-2 text-xs text-fulkro-ink-700 cursor-pointer hover:bg-fulkro-ink-50"
              >
                <input
                  type="checkbox"
                  checked={scanCleanOnly}
                  onChange={(e) => setScanCleanOnly(e.target.checked)}
                  className="h-3.5 w-3.5"
                />
                <ShieldCheck className="h-3.5 w-3.5 text-fulkro-success" aria-hidden />
                <span>Solo limpios</span>
              </label>
            )}
          </div>

          {loading && (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          )}

          {error && (
            <Card className="p-5 border-destructive/40 bg-destructive/5">
              <div className="flex items-start gap-2 text-sm">
                <AlertCircle
                  className="h-5 w-5 mt-0.5 text-destructive flex-shrink-0"
                  aria-hidden
                />
                <div>
                  <div className="font-semibold text-destructive">
                    Error cargando archivos
                  </div>
                  <p className="text-fulkro-ink-600 mt-1">{error}</p>
                </div>
              </div>
            </Card>
          )}

          {!loading && !error && items.length === 0 && (
            <Card className="p-5">
              <div className="flex items-start gap-3 text-sm">
                <AlertCircle
                  className="h-5 w-5 mt-0.5 text-fulkro-info flex-shrink-0"
                  aria-hidden
                />
                <div className="flex-1">
                  <div className="font-semibold text-fulkro-ink-800">
                    {tab === "documents"
                      ? search
                        ? `Sin documentos para "${search}"`
                        : folderId
                          ? "Aún no hay documentos en esta carpeta"
                          : "Sin documentos disponibles"
                      : search
                        ? `Sin evidencias para "${search}"`
                        : "Sin evidencias disponibles"}
                  </div>
                  <p className="text-fulkro-ink-600 mt-1">
                    {tab === "documents"
                      ? folderId
                        ? "Puedes compartir un documento desde el botón de arriba o seleccionar otra carpeta."
                        : "Cuando Marcos genere nuevos documentos para tu proyecto, aparecerán aquí. También puedes compartir los tuyos."
                      : "Cuando subas evidencias en la sección Subir evidencias, aparecerán aquí con su estado de análisis antivirus."}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {!loading && !error && items.length > 0 && (
            <div className="space-y-2" data-testid="files-list">
              {tab === "documents"
                ? documents.map((d) => (
                    <FileCard
                      key={d.id}
                      mode="document"
                      item={d}
                      onPreview={openDocumentPreview}
                      onVersions={(id) => setVersionsDocId(id)}
                      onDownload={downloadDocument}
                    />
                  ))
                : evidence.map((e) => (
                    <FileCard
                      key={e.id}
                      mode="evidence"
                      item={e}
                      onPreview={openEvidencePreview}
                      onDownload={downloadEvidence}
                    />
                  ))}
            </div>
          )}
        </main>
      </div>

      <FilePreviewModal
        open={previewState.open}
        onClose={() =>
          setPreviewState({
            open: false,
            title: "",
            previewUrl: null,
            downloadUrl: null,
          })
        }
        previewUrl={previewState.previewUrl}
        downloadUrl={previewState.downloadUrl}
        title={previewState.title}
      />

      <FileVersionDialog
        open={versionsDocId !== null}
        onClose={() => setVersionsDocId(null)}
        documentId={versionsDocId}
      />

      <ClientUploadModal
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        folders={folders}
        defaultFolderId={folderId}
        onUploaded={() => {
          void refetch();
        }}
      />
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
  testId,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  testId: string;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      data-active={active}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "border-fulkro-primary-700 text-fulkro-primary-800"
          : "border-transparent text-fulkro-ink-600 hover:text-fulkro-ink-800",
      )}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
