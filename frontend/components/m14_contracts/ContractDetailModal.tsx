"use client";

/**
 * ContractDetailModal · Sub-atom 1.D.D.A v3.11.
 *
 * Vista detalle de un contrato: metadata + estado firma · acciones
 * (firmar Marcos · enviar a cliente · descargar DOCX) + commitments
 * tracking. Reuse Dialog · TanStack Query · sonner toast.
 *
 * Backend reuse:
 *  GET  /api/v1/contracts/projects/{pid}/contracts/{cid}
 *  POST /api/v1/contracts/projects/{pid}/contracts/{cid}/sign-marcos
 *  POST /api/v1/contracts/projects/{pid}/contracts/{cid}/send-client
 *  GET  /api/v1/contracts/projects/{pid}/contracts/{cid}/docx
 *  GET  /api/v1/contracts/projects/{pid}/contracts/{cid}/commitments
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileCheck2, Loader2, Send } from "lucide-react";
import { toast } from "sonner";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CONTRACT_ESTADO_LABELS,
  CONTRACT_ESTADO_VARIANTS,
  contractsApi,
} from "@/lib/api/contracts";

interface ContractDetailModalProps {
  projectId: string;
  contractId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ContractDetailModal({
  projectId,
  contractId,
  open,
  onOpenChange,
}: ContractDetailModalProps) {
  const qc = useQueryClient();
  const [recipientEmail, setRecipientEmail] = useState("");
  const [downloading, setDownloading] = useState(false);

  const contractQuery = useQuery({
    queryKey: ["m14", "contract", projectId, contractId],
    queryFn: () => contractsApi.get(projectId, contractId),
    enabled: open && Boolean(contractId),
  });

  const commitmentsQuery = useQuery({
    queryKey: ["m14", "contract", projectId, contractId, "commitments"],
    queryFn: () => contractsApi.listCommitments(projectId, contractId),
    enabled: open && Boolean(contractId),
    staleTime: 60_000,
  });

  const signMutation = useMutation({
    mutationFn: () => contractsApi.signMarcos(projectId, contractId),
    onSuccess: () => {
      toast.success("Contrato firmado por Marcos", {
        description: "Hash SHA-256 actualizado · ready para envío al cliente.",
      });
      qc.invalidateQueries({
        queryKey: ["m14", "contract", projectId, contractId],
      });
      qc.invalidateQueries({ queryKey: ["m14", "contracts", projectId] });
    },
    onError: (err) => {
      toast.error("No se pudo firmar el contrato", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const sendMutation = useMutation({
    mutationFn: (email: string) =>
      contractsApi.sendClient(projectId, contractId, {
        recipient_email: email,
      }),
    onSuccess: () => {
      toast.success("Contrato enviado al cliente", {
        description: "Magic link generado · contrato pendiente firma cliente.",
      });
      qc.invalidateQueries({
        queryKey: ["m14", "contract", projectId, contractId],
      });
      qc.invalidateQueries({ queryKey: ["m14", "contracts", projectId] });
      setRecipientEmail("");
    },
    onError: (err) => {
      toast.error("No se pudo enviar el contrato", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const blob = await contractsApi.downloadDocx(projectId, contractId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `contrato_${contractId}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("DOCX descargado");
    } catch (err) {
      toast.error("Error descargando DOCX", {
        description: err instanceof Error ? err.message : undefined,
      });
    } finally {
      setDownloading(false);
    }
  };

  const c = contractQuery.data;
  const canSignMarcos = Boolean(c && c.estado === "draft");
  const showSendSection = Boolean(
    c && (c.estado === "firmado_marcos" || c.estado === "sent"),
  );
  const canSendClient = showSendSection && recipientEmail.includes("@");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl"
        data-testid="contract-detail-modal"
      >
        <DialogHeader>
          <DialogTitle>
            {c
              ? `Contrato ${c.plantilla_id} · ${c.tipo}`
              : "Cargando contrato…"}
          </DialogTitle>
          <DialogDescription>
            Estado actual + acciones de firma · descarga DOCX + commitments.
          </DialogDescription>
        </DialogHeader>

        {contractQuery.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-6 w-full" />
          </div>
        ) : contractQuery.isError || !c ? (
          <Alert variant="danger">
            <AlertTitle>No se pudo cargar el contrato</AlertTitle>
            <AlertDescription>
              {contractQuery.error instanceof Error
                ? contractQuery.error.message
                : "Error desconocido"}
            </AlertDescription>
          </Alert>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <FieldRow label="Estado">
                <Badge variant={CONTRACT_ESTADO_VARIANTS[c.estado]}>
                  {CONTRACT_ESTADO_LABELS[c.estado]}
                </Badge>
              </FieldRow>
              <FieldRow label="Plantilla">
                <code className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 text-xs font-mono">
                  {c.plantilla_id}
                </code>
              </FieldRow>
              <FieldRow label="Firmante cliente">
                {c.cliente_firmante_nombre}
              </FieldRow>
              <FieldRow label="Cargo">{c.cliente_firmante_cargo}</FieldRow>
              <FieldRow label="Firmado Marcos">
                {c.firmado_marcos_at ? formatDateTime(c.firmado_marcos_at) : "—"}
              </FieldRow>
              <FieldRow label="Firmado cliente">
                {c.firmado_cliente_at
                  ? formatDateTime(c.firmado_cliente_at)
                  : "—"}
              </FieldRow>
              <FieldRow label="Vigente desde">
                {c.vigente_desde ?? "—"}
              </FieldRow>
              <FieldRow label="Vigente hasta">
                {c.vigente_hasta ?? "—"}
              </FieldRow>
            </div>

            {c.hash_sha256 && (
              <div
                className="rounded-md border border-fulkro-ink-300/40 bg-fulkro-ink-50 p-2 text-xs"
                data-testid="contract-hash"
              >
                <span className="font-semibold">Hash SHA-256: </span>
                <code className="break-all font-mono text-[10px]">
                  {c.hash_sha256}
                </code>
              </div>
            )}

            {commitmentsQuery.data?.commitments &&
              commitmentsQuery.data.commitments.length > 0 && (
                <div
                  className="rounded-md border p-3"
                  data-testid="contract-commitments"
                >
                  <p className="mb-2 text-xs font-semibold uppercase text-muted-foreground">
                    Compromisos (XYZPR)
                  </p>
                  <ul className="space-y-1 text-sm">
                    {commitmentsQuery.data.commitments.map((cm) => (
                      <li
                        key={cm.id}
                        className="flex items-center justify-between gap-2"
                      >
                        <span>
                          <strong>{cm.tipo}</strong>
                          {cm.parametro ? ` · ${cm.parametro}` : ""}
                          {cm.valor_esperado ? ` = ${cm.valor_esperado}` : ""}
                        </span>
                        <Badge
                          variant={cm.cumplido ? "success" : "warning"}
                        >
                          {cm.cumplido ? "Cumplido" : "Pendiente"}
                        </Badge>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {showSendSection && (
              <div
                className="space-y-2 rounded-md border p-3"
                data-testid="contract-send-section"
              >
                <Label htmlFor="recipient-email">
                  Email del destinatario (cliente)
                </Label>
                <Input
                  id="recipient-email"
                  type="email"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  placeholder="firmante@cliente.es"
                  data-testid="contract-recipient-email-input"
                />
              </div>
            )}
          </div>
        )}

        <DialogFooter className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={handleDownload}
            disabled={!c || downloading}
            data-testid="contract-download-button"
          >
            {downloading ? (
              <Loader2 size={14} className="mr-1 animate-spin" />
            ) : (
              <Download size={14} className="mr-1" />
            )}
            Descargar DOCX
          </Button>
          {canSignMarcos && (
            <Button
              onClick={() => signMutation.mutate()}
              disabled={signMutation.isPending}
              data-testid="contract-sign-marcos-button"
            >
              {signMutation.isPending ? (
                <Loader2 size={14} className="mr-1 animate-spin" />
              ) : (
                <FileCheck2 size={14} className="mr-1" />
              )}
              Firmar (Marcos)
            </Button>
          )}
          {canSendClient && (
            <Button
              onClick={() => sendMutation.mutate(recipientEmail.trim())}
              disabled={sendMutation.isPending}
              data-testid="contract-send-client-button"
            >
              {sendMutation.isPending ? (
                <Loader2 size={14} className="mr-1 animate-spin" />
              ) : (
                <Send size={14} className="mr-1" />
              )}
              Enviar a cliente
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function FieldRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-semibold uppercase text-muted-foreground">
        {label}
      </span>
      <span>{children}</span>
    </div>
  );
}

function formatDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
