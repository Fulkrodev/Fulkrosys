"use client";

/**
 * ClarificationButton · CLUSTER 3 Phase C2.3 · request clarification UI.
 *
 * Reusable button + modal that creates a clarification request via
 * createClarification API. Used in views (Summary · DdA · Evidence · MAGERIT)
 * + standalone "Solicitar aclaración" general entry.
 *
 * Anchor optional: passes targetType + targetId si reusable per item · si
 * standalone usage entrega 'general' anchor-less.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, HelpCircle } from "lucide-react";
import * as React from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
  type ClarificationListResponse,
  type ClarificationPriority,
  type ClarificationTargetType,
  PRIORITY_LABEL,
  createClarification,
  listClarificationsAuditor,
} from "@/lib/api/auditor-clarifications";

interface Props {
  token: string;
  targetType?: ClarificationTargetType;
  targetId?: string;
  targetLabel?: string;
  buttonLabel?: string;
  buttonVariant?: "outline" | "secondary" | "ghost";
  compact?: boolean;
}

const PRIORITY_VALUES: ClarificationPriority[] = [
  "low",
  "normal",
  "high",
  "urgent",
];

export function ClarificationButton({
  token,
  targetType = "general",
  targetId,
  targetLabel,
  buttonLabel,
  buttonVariant = "outline",
  compact = false,
}: Props) {
  const queryClient = useQueryClient();
  const [isOpen, setIsOpen] = React.useState(false);
  const [question, setQuestion] = React.useState("");
  const [priority, setPriority] = React.useState<ClarificationPriority>(
    "normal",
  );

  const listQ = useQuery<ClarificationListResponse>({
    queryKey: ["auditor-portal", "clarifications", token],
    queryFn: () => listClarificationsAuditor(token),
    enabled: Boolean(token) && targetType !== "general",
    staleTime: 15_000,
    retry: false,
  });

  const existingForTarget = React.useMemo(() => {
    if (!listQ.data || targetType === "general") return 0;
    return listQ.data.items.filter(
      (c) =>
        c.linked_target_type === targetType &&
        c.linked_target_id === (targetId ?? null),
    ).length;
  }, [listQ.data, targetType, targetId]);

  const createMut = useMutation({
    mutationFn: async () => {
      return createClarification(token, {
        question_text: question,
        linked_target_type: targetType,
        linked_target_id: targetType === "general" ? null : (targetId ?? null),
        priority,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["auditor-portal", "clarifications", token],
      });
      setQuestion("");
      setPriority("normal");
      setIsOpen(false);
    },
  });

  const label =
    buttonLabel ??
    (existingForTarget > 0
      ? `${existingForTarget} aclaración${existingForTarget > 1 ? "es" : ""}`
      : "Solicitar aclaración");

  return (
    <>
      <Button
        size="sm"
        variant={buttonVariant}
        onClick={() => setIsOpen(true)}
        data-testid={`auditor-clarification-button-${targetType}${
          targetId ? `-${targetId}` : ""
        }`}
        aria-label={`Solicitar aclaración${
          targetLabel ? ` sobre ${targetLabel}` : ""
        }`}
      >
        <HelpCircle size={14} className="mr-1" aria-hidden="true" />
        {label}
      </Button>
      {!compact && targetLabel ? (
        <span className="ml-2 text-[11px] text-fulkro-ink-500">
          {targetLabel}
        </span>
      ) : null}

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Solicitar aclaración</DialogTitle>
            <DialogDescription>
              {targetLabel
                ? `Sobre: ${targetLabel}`
                : "Consulta general al consultor responsable"}
              . El consultor recibirá una notificación en tiempo real y por
              correo electrónico.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label htmlFor="clarification-priority">Prioridad</Label>
              <Select
                value={priority}
                onValueChange={(v) =>
                  setPriority(v as ClarificationPriority)
                }
              >
                <SelectTrigger
                  id="clarification-priority"
                  data-testid="auditor-clarification-priority"
                  aria-label="Prioridad de la solicitud"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITY_VALUES.map((p) => (
                    <SelectItem key={p} value={p}>
                      {PRIORITY_LABEL[p]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="clarification-question">Pregunta</Label>
              <Textarea
                id="clarification-question"
                rows={6}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Formula la pregunta para el consultor responsable. Sé específico para acelerar la respuesta…"
                data-testid="auditor-clarification-textarea"
                aria-label="Texto de la pregunta"
              />
            </div>
            {createMut.isError ? (
              <Alert variant="danger">
                <AlertCircle size={14} aria-hidden="true" />
                <AlertTitle>No se pudo enviar la solicitud</AlertTitle>
                <AlertDescription>
                  Reintenta más tarde.
                </AlertDescription>
              </Alert>
            ) : null}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsOpen(false)}
              data-testid="auditor-clarification-cancel"
            >
              Cancelar
            </Button>
            <Button
              onClick={() => createMut.mutate()}
              disabled={!question.trim() || createMut.isPending}
              data-testid="auditor-clarification-submit"
            >
              {createMut.isPending ? "Enviando…" : "Enviar pregunta"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
