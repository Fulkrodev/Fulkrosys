"use client";

/**
 * /client-portal/registros/[tipo] · Pagina dinamica per register_type.
 *
 * Sub-atom 1.C.B fase 4b. Lista entradas del register_type, permite filtrar
 * active/archived, exportar CSV/XLSX. Crear/editar/archivar quedan diferidos a
 * fase 4c (LiveRecordCreate + LiveRecordDetail components con form schemas).
 *
 * Validacion register_type: si el param no es un E-3XX valido, 404 inline.
 */
import { ArrowLeft, BookOpenCheck, Download, Inbox, Info, Plus } from "lucide-react";
import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { useState } from "react";

import { LiveRecordCreate } from "@/components/live-records/LiveRecordCreate";
import { LiveRecordDetail } from "@/components/live-records/LiveRecordDetail";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useClientProjectId } from "@/hooks/useClientProjectId";
import { useLiveRecords } from "@/hooks/useLiveRecords";
import { useProjectFeatures } from "@/lib/contexts/ProjectFeaturesContext";
import {
  BLOQUE_LABELS,
  REGISTER_TYPE_BLOQUES,
  REGISTER_TYPE_LABELS,
  REGISTER_TYPE_REQUIRED_CATEGORIES,
  isRegisterTypeApplicable,
  isValidRegisterType,
  type LiveRecord,
  type LiveRecordStatus,
  type RegisterType,
} from "@/lib/types/live-records";


type StatusFilter = "active" | "archived" | "all";


function formatDateShort(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso.slice(0, 10);
  }
}


function summarizeEntry(record: LiveRecord): string {
  const entry = record.entry_data || {};
  for (const key of [
    "codigo_incidente",
    "codigo_cambio",
    "codigo_activo",
    "codigo_sistema",
    "codigo_evaluacion",
    "codigo_indicador",
    "codigo_proveedor",
    "codigo_acta",
    "codigo_decision",
    "codigo_hallazgo",
    "codigo_auditoria",
    "codigo_backup",
    "codigo_vulnerabilidad",
    "codigo_notificacion",
    "codigo_excepcion",
    "codigo_adenda",
    "codigo_prueba",
    "codigo_prueba_bcp",
    "codigo_ejercicio_drp",
    "codigo_medicion",
    "codigo_verificacion",
    "codigo_cambio_material",
    "codigo_aplicacion",
    "nombre_completo",
    "nombre",
  ]) {
    const v = entry[key];
    if (v) return String(v);
  }
  return `(entrada ${record.id.slice(0, 8)})`;
}


export default function RegistroTipoPage() {
  const params = useParams<{ tipo: string }>();
  const rawTipo = (params?.tipo || "").toUpperCase();
  const validType = isValidRegisterType(rawTipo);
  // Hooks DEBEN llamarse incondicionalmente · early return defer post-hooks (react-hooks/rules-of-hooks).
  const registerType = validType ? rawTipo : ("E-300" as RegisterType);

  const bloque = REGISTER_TYPE_BLOQUES[registerType];
  const label = REGISTER_TYPE_LABELS[registerType];

  const { projectId, loading: loadingProject, error: errorProject } = useClientProjectId();
  const { data: features } = useProjectFeatures();
  const categoria = features?.categoria ?? null;
  const notApplicable =
    categoria !== null && !isRegisterTypeApplicable(registerType, categoria);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");

  const {
    records,
    total,
    loading: loadingRecords,
    error: errorRecords,
    create,
    archive,
    exportCsv,
    exportXlsx,
  } = useLiveRecords(projectId, registerType, {
    status: statusFilter,
    limit: 50,
    offset: 0,
  });

  const loading = loadingProject || loadingRecords;
  const error = errorProject ?? errorRecords;
  const [exportError, setExportError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<LiveRecord | null>(null);

  if (!validType) {
    return notFound();
  }

  async function safeExport(fn: () => Promise<void>) {
    setExportError(null);
    try {
      await fn();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error exportando";
      setExportError(msg);
    }
  }

  return (
    <div className="space-y-6 px-4 py-6 sm:px-6 md:px-8 max-w-6xl mx-auto pb-32">
      <nav className="text-xs text-fulkro-ink-500">
        <Link
          href="/client-portal/registros"
          className="inline-flex items-center gap-1 hover:text-fulkro-primary-700"
        >
          <ArrowLeft className="h-3 w-3" aria-hidden />
          Volver al dashboard de registros
        </Link>
      </nav>

      <header className="space-y-2">
        <div className="flex items-center gap-2 text-fulkro-primary-700">
          <BookOpenCheck className="h-5 w-5" aria-hidden />
          <span className="text-xs uppercase tracking-wide font-semibold">
            Registros vivos · {BLOQUE_LABELS[bloque]}
          </span>
        </div>
        <div className="flex flex-wrap items-baseline gap-3">
          <h1 className="text-2xl font-bold text-fulkro-ink-800">{label}</h1>
          <span className="font-mono text-sm font-semibold text-fulkro-primary-700">
            {registerType}
          </span>
        </div>
        <p className="text-xs text-fulkro-ink-500">
          {total} entrada{total === 1 ? "" : "s"}
          {statusFilter !== "all" ? ` (${statusFilter === "active" ? "activas" : "archivadas"})` : ""}.
        </p>
      </header>

      {notApplicable && categoria && (
        <Card className="flex items-start gap-3 border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div className="space-y-2">
            <p className="flex flex-wrap items-center gap-1.5 font-semibold">
              Este registro ({registerType}) no es obligatorio para su
              categoría <TooltipENS term="ENS" /> {categoria}.
            </p>
            <p className="text-xs text-blue-800">
              Aplica a categorías:{" "}
              <span className="font-mono">
                {REGISTER_TYPE_REQUIRED_CATEGORIES[registerType].join(" · ")}
              </span>
              . Si su categoría cambia en el futuro, lo verá automáticamente aquí.
            </p>
            <div>
              <Link
                href="/client-portal/registros"
                className="inline-flex items-center gap-1 text-xs font-semibold text-blue-900 underline-offset-2 hover:underline"
              >
                <ArrowLeft className="h-3 w-3" aria-hidden />
                Volver al dashboard
              </Link>
            </div>
          </div>
        </Card>
      )}

      <div className={`flex flex-wrap items-center gap-2 ${notApplicable ? "opacity-50 pointer-events-none" : ""}`}>
        <FilterTab
          active={statusFilter === "active"}
          onClick={() => setStatusFilter("active")}
          label="Activas"
        />
        <FilterTab
          active={statusFilter === "archived"}
          onClick={() => setStatusFilter("archived")}
          label="Archivadas"
        />
        <FilterTab
          active={statusFilter === "all"}
          onClick={() => setStatusFilter("all")}
          label="Todas"
        />
        <div className="ml-auto flex gap-2">
          <Button
            size="sm"
            onClick={() => setCreateOpen(true)}
            disabled={loading || !projectId}
          >
            <Plus className="mr-1 h-4 w-4" aria-hidden />
            Nueva entrada
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => safeExport(exportCsv)}
            disabled={loading}
          >
            <Download className="mr-1 h-4 w-4" aria-hidden />
            CSV
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => safeExport(exportXlsx)}
            disabled={loading}
          >
            <Download className="mr-1 h-4 w-4" aria-hidden />
            XLSX
          </Button>
        </div>
      </div>

      {(error || exportError) && !notApplicable && (
        <Card className="border-red-300 bg-red-50 p-4 text-sm text-red-800">
          {error || exportError}
        </Card>
      )}

      {loading && !notApplicable && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, idx) => (
            <Skeleton key={idx} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      )}

      {!loading && !notApplicable && records.length === 0 && (
        <Card className="flex flex-col items-center gap-3 border-dashed border-fulkro-ink-200 p-8 text-center">
          <Inbox className="h-10 w-10 text-fulkro-ink-600" aria-hidden />
          <h3 className="text-sm font-semibold text-fulkro-ink-700">
            Sin entradas{statusFilter !== "all" ? ` ${statusFilter === "active" ? "activas" : "archivadas"}` : ""}
          </h3>
          <p className="max-w-md text-xs text-fulkro-ink-500">
            Pulse &ldquo;Nueva entrada&rdquo; para crear la primera.
            {bloque === "incidentes" && " Los incidentes detectados por la plataforma generan entradas automáticamente."}
            {bloque === "cambios" && " Los cambios solicitados desde Comité generan entradas automáticamente."}
            {bloque === "proveedores" && registerType === "E-312" && " Las evaluaciones se crean automáticamente al completar el cuestionario de proveedor."}
          </p>
        </Card>
      )}

      {!loading && !notApplicable && records.length > 0 && (
        <ul className="space-y-2">
          {records.map((record) => (
            <li key={record.id}>
              <button
                type="button"
                onClick={() => setSelectedRecord(record)}
                className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-500 rounded-lg"
              >
                <Card className="flex flex-wrap items-center justify-between gap-3 border-fulkro-ink-200 p-4 hover:border-fulkro-primary-500 hover:shadow-md transition">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-fulkro-ink-800">
                        {summarizeEntry(record)}
                      </span>
                      <StatusPill status={record.status} />
                    </div>
                    <p className="text-xs text-fulkro-ink-500">
                      Creado {formatDateShort(record.created_at)} ·
                      actualizado {formatDateShort(record.updated_at)}
                    </p>
                  </div>
                  <span className="font-mono text-xs text-fulkro-ink-600">
                    {record.id.slice(0, 8)}
                  </span>
                </Card>
              </button>
            </li>
          ))}
        </ul>
      )}

      <LiveRecordCreate
        open={createOpen}
        onOpenChange={setCreateOpen}
        registerType={registerType}
        onSubmit={async (entryData) => {
          await create(entryData);
        }}
      />

      <LiveRecordDetail
        open={selectedRecord !== null}
        onOpenChange={(o) => {
          if (!o) setSelectedRecord(null);
        }}
        record={selectedRecord}
        onArchive={async (recordId) => {
          await archive(recordId);
          setSelectedRecord(null);
        }}
      />
    </div>
  );
}


function FilterTab({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-500 ${
        active
          ? "bg-fulkro-primary-700 text-white"
          : "bg-fulkro-ink-100 text-fulkro-ink-700 hover:bg-fulkro-ink-200"
      }`}
    >
      {label}
    </button>
  );
}


function StatusPill({ status }: { status: LiveRecordStatus }) {
  if (status === "active") {
    return (
      <span className="rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-green-800">
        activa
      </span>
    );
  }
  return (
    <span className="rounded-full bg-fulkro-ink-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-fulkro-ink-600">
      archivada
    </span>
  );
}
