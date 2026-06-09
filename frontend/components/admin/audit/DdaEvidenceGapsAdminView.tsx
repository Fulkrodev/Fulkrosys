"use client";

/**
 * DdaEvidenceGapsAdminView · CLUSTER 3 Phase C3.3 admin twin.
 *
 * Same heatmap structure as auditor view + admin CTA:
 * - Multi-select medidas missing/partial via checkboxes
 * - "Solicitar evidencias al cliente" bulk button → POST request-more-evidence
 *   con medida_codes list + message_to_client opcional
 * - Triggers ClientNotification + audit_log admin.evidence_request.triggered
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Loader2,
  Search,
  Send,
} from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  type DdaEvidenceGapMatrix,
  type GapStatus,
  type MedidaGapRow,
  FAMILY_LABEL,
  SEVERITY_LABEL,
  SEVERITY_VARIANT,
  STATUS_COLOR_CLASS,
  STATUS_LABEL,
  getDdaEvidenceGapsAdmin,
  requestMoreEvidenceAdmin,
} from "@/lib/api/dda-evidence-gaps";

interface Props {
  projectId: string;
}

const STATUS_FILTER_VALUES: { value: GapStatus | "all"; label: string }[] = [
  { value: "all", label: "Todos los estados" },
  { value: "missing", label: "Sin evidencia" },
  { value: "partial", label: "Parciales" },
  { value: "covered", label: "Cubiertas" },
  { value: "not_applicable", label: "No aplican" },
];

const FAMILY_FILTER_VALUES = [
  { value: "all", label: "Todas las familias" },
  { value: "org", label: "Organizativo" },
  { value: "op", label: "Operacional" },
  { value: "mp", label: "Protección" },
];

function MedidaCheckCell({
  medida,
  selected,
  onToggle,
}: {
  medida: MedidaGapRow;
  selected: boolean;
  onToggle: () => void;
}) {
  const selectable =
    medida.status === "missing" || medida.status === "partial";
  return (
    <label
      className={
        "flex cursor-pointer items-start gap-2 rounded-md border-2 px-2 py-1 text-[11px] " +
        (selected
          ? "ring-2 ring-fulkro-primary-700 "
          : "hover:scale-105 transition-all ") +
        STATUS_COLOR_CLASS[medida.status]
      }
      data-testid={`gap-admin-medida-${medida.medida_code}`}
    >
      {selectable ? (
        <input
          type="checkbox"
          checked={selected}
          onChange={onToggle}
          className="mt-1"
          aria-label={`Seleccionar ${medida.medida_code} para solicitar evidencia`}
          data-testid={`gap-admin-checkbox-${medida.medida_code}`}
        />
      ) : (
        <span className="w-3" aria-hidden="true" />
      )}
      <span className="flex-1">
        <span className="block font-mono font-semibold">
          {medida.medida_code}
        </span>
        <span className="block text-[9px] opacity-80">
          {medida.evidence_count}/{medida.min_required}
        </span>
      </span>
    </label>
  );
}

export function DdaEvidenceGapsAdminView({ projectId }: Props) {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = React.useState<GapStatus | "all">(
    "all",
  );
  const [familyFilter, setFamilyFilter] = React.useState<string>("all");
  const [search, setSearch] = React.useState("");
  const [selectedCodes, setSelectedCodes] = React.useState<Set<string>>(
    new Set(),
  );
  const [isRequestOpen, setIsRequestOpen] = React.useState(false);
  const [messageToClient, setMessageToClient] = React.useState("");

  const matrixQ = useQuery<DdaEvidenceGapMatrix>({
    queryKey: ["admin", "audit", "dda-gaps", projectId],
    queryFn: () => getDdaEvidenceGapsAdmin(projectId),
    staleTime: 30_000,
  });

  const requestMut = useMutation({
    mutationFn: async () => {
      return requestMoreEvidenceAdmin(projectId, {
        medida_codes: Array.from(selectedCodes),
        message_to_client: messageToClient.trim() || undefined,
      });
    },
    onSuccess: () => {
      setSelectedCodes(new Set());
      setMessageToClient("");
      setIsRequestOpen(false);
      queryClient.invalidateQueries({
        queryKey: ["admin", "audit", "dda-gaps", projectId],
      });
    },
  });

  const filtered = React.useMemo(() => {
    if (!matrixQ.data) return [];
    return matrixQ.data.medidas.filter((m) => {
      if (statusFilter !== "all" && m.status !== statusFilter) return false;
      if (familyFilter !== "all" && m.family !== familyFilter) return false;
      if (search.trim()) {
        const lower = search.trim().toLowerCase();
        if (
          !m.medida_code.toLowerCase().includes(lower) &&
          !(m.medida_nombre ?? "").toLowerCase().includes(lower)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [matrixQ.data, statusFilter, familyFilter, search]);

  const toggleCode = (code: string) => {
    setSelectedCodes((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  const selectAllGappy = () => {
    if (!matrixQ.data) return;
    const codes = matrixQ.data.medidas
      .filter((m) => m.status === "missing" || m.status === "partial")
      .map((m) => m.medida_code);
    setSelectedCodes(new Set(codes));
  };

  if (matrixQ.isLoading) {
    return (
      <div
        className="flex items-center gap-2 text-sm text-fulkro-ink-500"
        data-testid="gap-admin-loading"
      >
        <Loader2 size={14} className="animate-spin" aria-hidden="true" />
        Calculando análisis…
      </div>
    );
  }

  if (matrixQ.isError || !matrixQ.data) {
    return (
      <Alert variant="danger" data-testid="gap-admin-error">
        <AlertCircle size={14} aria-hidden="true" />
        <AlertTitle>No se pudo cargar el análisis</AlertTitle>
        <AlertDescription>Reintenta más tarde.</AlertDescription>
      </Alert>
    );
  }

  const matrix = matrixQ.data;

  return (
    <div className="space-y-4" data-testid="gap-admin-view">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <HelpCircle
              size={16}
              className="text-fulkro-info-700"
              aria-hidden="true"
            />
            Cobertura DdA · Evidencias (vista admin)
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-4">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Cobertura
            </p>
            <p
              className="text-2xl font-bold text-fulkro-ink-900"
              data-testid="gap-admin-coverage-pct"
            >
              {matrix.coverage_pct.toFixed(1)}%
            </p>
            <p className="text-[11px] text-fulkro-ink-500">
              {matrix.total_covered}/{matrix.total_applicable}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Críticas missing
            </p>
            <p className="text-2xl font-bold text-fulkro-danger-700">
              {matrix.severity_summary.critical_missing}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Recuperables
            </p>
            <p className="text-2xl font-bold text-fulkro-success-700">
              {matrix.severity_summary.recoverable}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Categoría
            </p>
            <p className="text-2xl font-bold text-fulkro-ink-900">
              {matrix.categoria ?? "—"}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Solicitar más evidencias al cliente
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={selectAllGappy}
              data-testid="gap-admin-select-all-gappy"
            >
              Seleccionar todas con gap ({matrix.total_missing + matrix.total_partial})
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSelectedCodes(new Set())}
              data-testid="gap-admin-clear-selection"
              disabled={selectedCodes.size === 0}
            >
              Limpiar
            </Button>
            <Button
              size="sm"
              onClick={() => setIsRequestOpen(true)}
              disabled={selectedCodes.size === 0}
              data-testid="gap-admin-open-request"
              aria-label="Abrir formulario de solicitud"
            >
              <Send size={14} className="mr-1" aria-hidden="true" />
              Solicitar evidencias ({selectedCodes.size})
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Label htmlFor="gap-admin-status-filter">Estado</Label>
            <Select
              value={statusFilter}
              onValueChange={(v) => setStatusFilter(v as GapStatus | "all")}
            >
              <SelectTrigger
                id="gap-admin-status-filter"
                className="w-44"
                aria-label="Estado"
                data-testid="gap-admin-status-filter"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {STATUS_FILTER_VALUES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Label htmlFor="gap-admin-family-filter">Familia</Label>
            <Select
              value={familyFilter}
              onValueChange={setFamilyFilter}
            >
              <SelectTrigger
                id="gap-admin-family-filter"
                className="w-40"
                aria-label="Familia"
                data-testid="gap-admin-family-filter"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FAMILY_FILTER_VALUES.map((f) => (
                  <SelectItem key={f.value} value={f.value}>
                    {f.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Search
              size={14}
              className="text-fulkro-ink-500"
              aria-hidden="true"
            />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por código o nombre"
              aria-label="Buscar medida"
              data-testid="gap-admin-search"
              className="h-9"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Heatmap ({filtered.length} medidas)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-7">
            {filtered.map((m) => (
              <MedidaCheckCell
                key={m.medida_code}
                medida={m}
                selected={selectedCodes.has(m.medida_code)}
                onToggle={() => toggleCode(m.medida_code)}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      <Dialog open={isRequestOpen} onOpenChange={setIsRequestOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Solicitar evidencias al cliente</DialogTitle>
            <DialogDescription>
              {selectedCodes.size} medida{selectedCodes.size > 1 ? "s" : ""}{" "}
              seleccionada{selectedCodes.size > 1 ? "s" : ""}. El cliente
              recibirá una notificación en su portal con la lista y mensaje
              opcional.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="max-h-40 overflow-auto rounded-md border border-fulkro-ink-300 bg-fulkro-ink-50 p-2">
              <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
                Medidas
              </p>
              <p className="font-mono text-[11px] text-fulkro-ink-900">
                {Array.from(selectedCodes).join(" · ")}
              </p>
            </div>
            <div>
              <Label htmlFor="gap-admin-message">Mensaje al cliente (opcional)</Label>
              <Textarea
                id="gap-admin-message"
                rows={4}
                value={messageToClient}
                onChange={(e) => setMessageToClient(e.target.value)}
                placeholder="Explica al cliente qué evidencia se necesita y plazo deseado…"
                aria-label="Mensaje al cliente"
                data-testid="gap-admin-message-textarea"
              />
            </div>
            {requestMut.isError ? (
              <Alert variant="danger">
                <AlertTriangle size={14} aria-hidden="true" />
                <AlertTitle>No se pudo enviar la solicitud</AlertTitle>
                <AlertDescription>
                  {requestMut.error instanceof Error
                    ? requestMut.error.message
                    : "Error desconocido"}
                </AlertDescription>
              </Alert>
            ) : null}
            {requestMut.isSuccess ? (
              <Alert>
                <CheckCircle size={14} aria-hidden="true" />
                <AlertTitle>Solicitud enviada</AlertTitle>
                <AlertDescription>
                  El cliente ha recibido la notificación. Se ha registrado un
                  evento en el audit log inmutable.
                </AlertDescription>
              </Alert>
            ) : null}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsRequestOpen(false)}
              data-testid="gap-admin-cancel"
            >
              Cancelar
            </Button>
            <Button
              onClick={() => requestMut.mutate()}
              disabled={requestMut.isPending || selectedCodes.size === 0}
              data-testid="gap-admin-submit"
            >
              {requestMut.isPending ? "Enviando…" : "Enviar solicitud"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
