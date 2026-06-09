"use client";

/**
 * AnnotationPanel · CLUSTER 3 Phase C1.3 · auditor portal annotation widget.
 *
 * Reusable widget embeddable cross views (Evidence · MAGERIT · Plan · DdA).
 * Per-target "Anotar" button → opens AnnotationModal · creates annotation via
 * createAnnotation API · invalidates query cache.
 *
 * Usage:
 *   <AnnotationPanel
 *     token={token}
 *     targetType="evidence"
 *     targetId={evidenceId}
 *     targetLabel="Evidencia: documento.pdf"
 *   />
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, MessageSquarePlus, Trash2 } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  type AnnotationListResponse,
  type AnnotationOut,
  type AnnotationSeverity,
  type AnnotationTargetType,
  SEVERITY_LABEL,
  SEVERITY_VARIANT,
  STATUS_LABEL,
  STATUS_VARIANT,
  createAnnotation,
  deleteAnnotationAuditor,
  listAnnotationsAuditor,
} from "@/lib/api/auditor-annotations";

interface Props {
  token: string;
  targetType: AnnotationTargetType;
  targetId: string;
  targetLabel: string;
  compact?: boolean;
}

const SEVERITY_VALUES: AnnotationSeverity[] = [
  "info",
  "warning",
  "concern",
  "critical",
];

export function AnnotationPanel({
  token,
  targetType,
  targetId,
  targetLabel,
  compact = false,
}: Props) {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [annotationText, setAnnotationText] = React.useState("");
  const [flagSeverity, setFlagSeverity] = React.useState<AnnotationSeverity>(
    "info",
  );

  const listQ = useQuery<AnnotationListResponse>({
    queryKey: ["auditor-portal", "annotations", token],
    queryFn: () => listAnnotationsAuditor(token),
    enabled: Boolean(token),
    staleTime: 15_000,
    retry: false,
  });

  const targetAnnotations = React.useMemo(() => {
    if (!listQ.data) return [];
    return listQ.data.items.filter(
      (a) => a.target_type === targetType && a.target_id === targetId,
    );
  }, [listQ.data, targetType, targetId]);

  const createMut = useMutation({
    mutationFn: async () => {
      return createAnnotation(token, {
        target_type: targetType,
        target_id: targetId,
        annotation_text: annotationText,
        flag_severity: flagSeverity,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["auditor-portal", "annotations", token],
      });
      setAnnotationText("");
      setFlagSeverity("info");
      setIsCreateOpen(false);
    },
  });

  const deleteMut = useMutation({
    mutationFn: async (annotationId: string) => {
      await deleteAnnotationAuditor(token, annotationId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["auditor-portal", "annotations", token],
      });
    },
  });

  const button = (
    <Button
      size="sm"
      variant="outline"
      onClick={() => setIsCreateOpen(true)}
      data-testid={`auditor-annotate-${targetType}-${targetId}`}
      aria-label={`Anotar ${targetLabel}`}
    >
      <MessageSquarePlus size={14} className="mr-1" aria-hidden="true" />
      {targetAnnotations.length > 0
        ? `${targetAnnotations.length} anotación${targetAnnotations.length > 1 ? "es" : ""}`
        : "Anotar"}
    </Button>
  );

  return (
    <div className="space-y-2" data-testid="auditor-annotation-panel">
      <div className="flex items-center gap-2">
        {button}
        {compact ? null : (
          <span className="text-[11px] text-fulkro-ink-500">
            {targetLabel}
          </span>
        )}
      </div>

      {targetAnnotations.length > 0 && !compact ? (
        <div className="space-y-1">
          {targetAnnotations.map((a) => (
            <AnnotationRow
              key={a.id}
              annotation={a}
              onDelete={() => deleteMut.mutate(a.id)}
              deleting={deleteMut.isPending}
            />
          ))}
        </div>
      ) : null}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nueva anotación</DialogTitle>
            <DialogDescription>
              {targetLabel} · esta anotación queda registrada en el audit log
              inmutable y será revisada por el consultor responsable.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="auditor-annotation-severity">Severidad</Label>
              <Select
                value={flagSeverity}
                onValueChange={(v) => setFlagSeverity(v as AnnotationSeverity)}
              >
                <SelectTrigger
                  id="auditor-annotation-severity"
                  data-testid="auditor-annotation-severity"
                  aria-label="Severidad de la anotación"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SEVERITY_VALUES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {SEVERITY_LABEL[s]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="auditor-annotation-text">Anotación</Label>
              <Textarea
                id="auditor-annotation-text"
                rows={5}
                value={annotationText}
                onChange={(e) => setAnnotationText(e.target.value)}
                placeholder="Describe el hallazgo, la observación o la solicitud de aclaración…"
                data-testid="auditor-annotation-textarea"
                aria-label="Texto de la anotación"
              />
            </div>
            {createMut.isError ? (
              <Alert variant="danger">
                <AlertCircle size={14} aria-hidden="true" />
                <AlertTitle>No se pudo crear la anotación</AlertTitle>
                <AlertDescription>
                  Reintenta más tarde. Si el problema persiste, contacta con el
                  consultor responsable.
                </AlertDescription>
              </Alert>
            ) : null}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateOpen(false)}
              data-testid="auditor-annotation-cancel"
            >
              Cancelar
            </Button>
            <Button
              onClick={() => createMut.mutate()}
              disabled={!annotationText.trim() || createMut.isPending}
              data-testid="auditor-annotation-submit"
            >
              {createMut.isPending ? "Guardando…" : "Guardar anotación"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function AnnotationRow({
  annotation,
  onDelete,
  deleting,
}: {
  annotation: AnnotationOut;
  onDelete: () => void;
  deleting: boolean;
}) {
  const canDelete =
    annotation.status === "open" &&
    Date.now() - new Date(annotation.created_at).getTime() <
      24 * 60 * 60 * 1000;

  return (
    <div
      className="rounded-md border border-fulkro-ink-300/60 bg-white p-2 text-[13px]"
      data-testid={`auditor-annotation-row-${annotation.id}`}
    >
      <div className="mb-1 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <Badge variant={SEVERITY_VARIANT[annotation.flag_severity]}>
            {SEVERITY_LABEL[annotation.flag_severity]}
          </Badge>
          <Badge variant={STATUS_VARIANT[annotation.status]}>
            {STATUS_LABEL[annotation.status]}
          </Badge>
          <span className="text-[10px] text-fulkro-ink-500">
            {new Date(annotation.created_at).toLocaleString()}
          </span>
        </div>
        {canDelete ? (
          <Button
            size="sm"
            variant="ghost"
            onClick={onDelete}
            disabled={deleting}
            aria-label="Eliminar anotación"
            data-testid={`auditor-annotation-delete-${annotation.id}`}
          >
            <Trash2 size={12} aria-hidden="true" />
          </Button>
        ) : null}
      </div>
      <p className="whitespace-pre-wrap text-fulkro-ink-900">
        {annotation.annotation_text}
      </p>
      {annotation.admin_response ? (
        <div className="mt-2 rounded bg-fulkro-info-700/5 p-2">
          <p className="text-[10px] uppercase tracking-wider text-fulkro-info-700">
            Respuesta del consultor
            {annotation.admin_responded_at
              ? ` · ${new Date(annotation.admin_responded_at).toLocaleString()}`
              : ""}
          </p>
          <p className="text-[12px] text-fulkro-ink-900">
            {annotation.admin_response}
          </p>
        </div>
      ) : null}
    </div>
  );
}
