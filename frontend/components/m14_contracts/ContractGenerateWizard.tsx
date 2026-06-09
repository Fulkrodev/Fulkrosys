"use client";

/**
 * ContractGenerateWizard · Sub-atom 1.D.D.A v3.11.
 *
 * Wizard 3 pasos generación de contrato desde Proposal won:
 *   1) Tipo plantilla (C-001..C-005) selector
 *   2) Parámetros (proposal won · firmante · cargo · vigencia)
 *   3) Preview + generar (POST /contracts/generate)
 *
 * Reuse pattern ContactCreateWizard (m30 1.C.F.1) · Stepper UI · zod
 * por paso opcional · backend production-grade existing zero touch.
 */
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, FileSignature, Loader2 } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Stepper } from "@/components/ui/stepper";
import {
  type Contract,
  type ContractTemplate,
  type ProposalSummary,
  contractsApi,
} from "@/lib/api/contracts";

interface ContractGenerateWizardProps {
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onGenerated?: (contract: Contract) => void;
}

const STEPS = [
  { id: "tipo", label: "Tipo de contrato" },
  { id: "params", label: "Parámetros" },
  { id: "preview", label: "Previsualizar y generar" },
];

export function ContractGenerateWizard({
  projectId,
  open,
  onOpenChange,
  onGenerated,
}: ContractGenerateWizardProps) {
  const qc = useQueryClient();
  const [stepIndex, setStepIndex] = useState(0);
  const [plantillaId, setPlantillaId] = useState<string>("C-001");
  const [proposalId, setProposalId] = useState<string>("");
  const [firmanteNombre, setFirmanteNombre] = useState("");
  const [firmanteCargo, setFirmanteCargo] = useState("");
  const [vigenciaMeses, setVigenciaMeses] = useState(12);
  const [prefillSeeded, setPrefillSeeded] = useState(false);

  const templatesQuery = useQuery({
    queryKey: ["m14", "contract-templates"],
    queryFn: () => contractsApi.listTemplates(),
    staleTime: 60 * 60 * 1000,
    enabled: open,
  });

  const proposalsQuery = useQuery({
    queryKey: ["m13", "proposals", projectId],
    queryFn: () => contractsApi.listProposals(projectId),
    enabled: open && Boolean(projectId),
    staleTime: 30_000,
  });

  // #9 · datos del cliente para pre-rellenar el firmante (editable).
  const prefillQuery = useQuery({
    queryKey: ["m14", "contract-prefill", projectId],
    queryFn: () => contractsApi.clientPrefill(projectId),
    enabled: open && Boolean(projectId),
    staleTime: 30_000,
  });

  const proposals: ProposalSummary[] = (() => {
    const data = proposalsQuery.data;
    if (!data) return [];
    if (Array.isArray(data)) return data;
    return data.proposals ?? [];
  })();
  const wonProposals = proposals.filter((p) => p.estado === "won");

  // Reset on close
  useEffect(() => {
    if (!open) {
      setStepIndex(0);
      setPlantillaId("C-001");
      setProposalId("");
      setFirmanteNombre("");
      setFirmanteCargo("");
      setVigenciaMeses(12);
      setPrefillSeeded(false);
    }
  }, [open]);

  // #9 · siembra el firmante con persona_contacto del cliente (una vez · no
  // pisa lo que el usuario haya tecleado · siempre editable / override).
  useEffect(() => {
    if (!open || prefillSeeded) return;
    const pc = prefillQuery.data?.persona_contacto;
    if (pc) {
      setFirmanteNombre((prev) => (prev ? prev : pc));
      setPrefillSeeded(true);
    }
  }, [open, prefillSeeded, prefillQuery.data]);

  const generateMutation = useMutation({
    mutationFn: () =>
      contractsApi.generate(projectId, {
        proposal_id: proposalId,
        plantilla_id: plantillaId,
        cliente_firmante_nombre: firmanteNombre.trim(),
        cliente_firmante_cargo: firmanteCargo.trim(),
        vigencia_meses: vigenciaMeses,
      }),
    onSuccess: (contract) => {
      toast.success(`Contrato ${plantillaId} generado`, {
        description: `Estado: ${contract.estado} · Firmar Marcos para continuar.`,
      });
      qc.invalidateQueries({ queryKey: ["m14", "contracts", projectId] });
      onGenerated?.(contract);
    },
    onError: (err) => {
      toast.error("No se pudo generar el contrato", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const canNextFromTipo = Boolean(plantillaId);
  const canNextFromParams =
    Boolean(proposalId) &&
    firmanteNombre.trim().length >= 2 &&
    firmanteCargo.trim().length >= 2 &&
    vigenciaMeses >= 1 &&
    vigenciaMeses <= 120;

  const selectedTemplate: ContractTemplate | undefined =
    templatesQuery.data?.templates.find((t) => t.plantilla_id === plantillaId);
  const selectedProposal = wonProposals.find((p) => p.id === proposalId);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl"
        data-testid="contract-generate-wizard"
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSignature size={18} /> Generar contrato
          </DialogTitle>
          <DialogDescription>
            Wizard 3 pasos · plantilla C-001..C-005 · requiere propuesta en
            estado <code>won</code>.
          </DialogDescription>
        </DialogHeader>

        <Stepper steps={STEPS} currentIndex={stepIndex} className="my-2" />

        {stepIndex === 0 && (
          <StepTipo
            templatesLoading={templatesQuery.isLoading}
            templatesError={templatesQuery.isError}
            templates={templatesQuery.data?.templates ?? []}
            plantillaId={plantillaId}
            onChange={setPlantillaId}
          />
        )}

        {stepIndex === 1 && (
          <StepParams
            proposalsLoading={proposalsQuery.isLoading}
            proposalsError={proposalsQuery.isError}
            wonProposals={wonProposals}
            proposalId={proposalId}
            setProposalId={setProposalId}
            firmanteNombre={firmanteNombre}
            setFirmanteNombre={setFirmanteNombre}
            firmanteCargo={firmanteCargo}
            setFirmanteCargo={setFirmanteCargo}
            vigenciaMeses={vigenciaMeses}
            setVigenciaMeses={setVigenciaMeses}
          />
        )}

        {stepIndex === 2 && (
          <StepPreview
            plantillaId={plantillaId}
            template={selectedTemplate}
            proposal={selectedProposal}
            firmanteNombre={firmanteNombre}
            firmanteCargo={firmanteCargo}
            vigenciaMeses={vigenciaMeses}
          />
        )}

        <DialogFooter className="flex justify-between gap-2">
          <Button
            variant="outline"
            onClick={() =>
              stepIndex === 0
                ? onOpenChange(false)
                : setStepIndex((s) => s - 1)
            }
            disabled={generateMutation.isPending}
            data-testid="contracts-wizard-back"
          >
            <ChevronLeft size={14} className="mr-1" />
            {stepIndex === 0 ? "Cancelar" : "Atrás"}
          </Button>
          {stepIndex < 2 ? (
            <Button
              onClick={() => setStepIndex((s) => s + 1)}
              disabled={
                (stepIndex === 0 && !canNextFromTipo) ||
                (stepIndex === 1 && !canNextFromParams)
              }
              data-testid="contracts-wizard-next"
            >
              Siguiente
              <ChevronRight size={14} className="ml-1" />
            </Button>
          ) : (
            <Button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending}
              data-testid="contracts-wizard-submit"
            >
              {generateMutation.isPending ? (
                <Loader2 size={14} className="mr-1 animate-spin" />
              ) : (
                <FileSignature size={14} className="mr-1" />
              )}
              Generar contrato
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function StepTipo({
  templatesLoading,
  templatesError,
  templates,
  plantillaId,
  onChange,
}: {
  templatesLoading: boolean;
  templatesError: boolean;
  templates: ContractTemplate[];
  plantillaId: string;
  onChange: (id: string) => void;
}) {
  if (templatesLoading) {
    return (
      <div className="space-y-2" data-testid="wizard-step-tipo">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }
  if (templatesError || templates.length === 0) {
    return (
      <Alert variant="danger" data-testid="wizard-step-tipo">
        <AlertTitle>No se pudieron cargar las plantillas</AlertTitle>
        <AlertDescription>
          Intenta de nuevo. Si persiste, contacta a Marcos.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-2" data-testid="wizard-step-tipo">
      <p className="text-sm text-muted-foreground">
        Selecciona el tipo de contrato a generar.
      </p>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        {templates.map((t) => {
          const active = plantillaId === t.plantilla_id;
          return (
            <button
              key={t.plantilla_id}
              type="button"
              onClick={() => onChange(t.plantilla_id)}
              className={`flex flex-col items-start gap-1 rounded-md border p-3 text-left transition-colors ${
                active
                  ? "border-fulkro-primary-700 bg-fulkro-primary-50"
                  : "border-fulkro-ink-300/40 hover:bg-fulkro-surface-glass"
              }`}
              data-testid={`wizard-template-${t.plantilla_id}`}
            >
              <div className="flex w-full items-start justify-between gap-2">
                <span className="font-semibold">{t.nombre}</span>
                <Badge variant={active ? "default" : "outline"}>
                  {t.plantilla_id}
                </Badge>
              </div>
              <span className="text-xs text-muted-foreground">
                Tipo: {t.tipo}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function StepParams({
  proposalsLoading,
  proposalsError,
  wonProposals,
  proposalId,
  setProposalId,
  firmanteNombre,
  setFirmanteNombre,
  firmanteCargo,
  setFirmanteCargo,
  vigenciaMeses,
  setVigenciaMeses,
}: {
  proposalsLoading: boolean;
  proposalsError: boolean;
  wonProposals: ProposalSummary[];
  proposalId: string;
  setProposalId: (s: string) => void;
  firmanteNombre: string;
  setFirmanteNombre: (s: string) => void;
  firmanteCargo: string;
  setFirmanteCargo: (s: string) => void;
  vigenciaMeses: number;
  setVigenciaMeses: (n: number) => void;
}) {
  if (proposalsLoading) {
    return (
      <div className="space-y-2" data-testid="wizard-step-params">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }
  if (proposalsError) {
    return (
      <Alert variant="danger" data-testid="wizard-step-params">
        <AlertTitle>No se pudieron cargar las propuestas</AlertTitle>
        <AlertDescription>Intenta de nuevo más tarde.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-3" data-testid="wizard-step-params">
      <div className="space-y-1">
        <Label htmlFor="proposal-select">
          Propuesta won origen <span className="text-fulkro-warning">*</span>
        </Label>
        {wonProposals.length === 0 ? (
          <Alert variant="warning">
            <AlertTitle>Sin propuestas en estado won</AlertTitle>
            <AlertDescription>
              Genera y cierra una propuesta antes de crear un contrato.
            </AlertDescription>
          </Alert>
        ) : (
          <Select value={proposalId} onValueChange={setProposalId}>
            <SelectTrigger
              id="proposal-select"
              data-testid="wizard-proposal-select"
            >
              <SelectValue placeholder="Selecciona una propuesta won…" />
            </SelectTrigger>
            <SelectContent>
              {wonProposals.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.numero ?? p.id.slice(0, 8)}
                  {p.total_eur ? ` · ${p.total_eur.toLocaleString("es-ES")} €` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <div className="space-y-1">
        <Label htmlFor="firmante-nombre">
          Nombre del firmante (cliente){" "}
          <span className="text-fulkro-warning">*</span>
        </Label>
        <Input
          id="firmante-nombre"
          value={firmanteNombre}
          onChange={(e) => setFirmanteNombre(e.target.value)}
          placeholder="Ana García López"
          data-testid="wizard-firmante-nombre"
        />
      </div>

      <div className="space-y-1">
        <Label htmlFor="firmante-cargo">
          Cargo del firmante <span className="text-fulkro-warning">*</span>
        </Label>
        <Input
          id="firmante-cargo"
          value={firmanteCargo}
          onChange={(e) => setFirmanteCargo(e.target.value)}
          placeholder="CEO · Director General · etc"
          data-testid="wizard-firmante-cargo"
        />
      </div>

      <Alert variant="warning" data-testid="wizard-firmante-poder-note">
        <AlertTitle>Confirma el poder de firma</AlertTitle>
        <AlertDescription>
          El firmante debe tener capacidad legal para obligar a la empresa
          (apoderado o administrador). Lo pre-rellenamos con la persona de
          contacto por comodidad, pero asegúrate de que sea quien debe firmar.
        </AlertDescription>
      </Alert>

      <div className="space-y-1">
        <Label htmlFor="vigencia-meses">
          Vigencia (meses) · entre 1 y 120
        </Label>
        <Input
          id="vigencia-meses"
          type="number"
          min={1}
          max={120}
          value={vigenciaMeses}
          onChange={(e) => setVigenciaMeses(Number(e.target.value) || 12)}
          data-testid="wizard-vigencia-meses"
        />
      </div>
    </div>
  );
}

function StepPreview({
  plantillaId,
  template,
  proposal,
  firmanteNombre,
  firmanteCargo,
  vigenciaMeses,
}: {
  plantillaId: string;
  template?: ContractTemplate;
  proposal?: ProposalSummary;
  firmanteNombre: string;
  firmanteCargo: string;
  vigenciaMeses: number;
}) {
  return (
    <div className="space-y-3" data-testid="wizard-step-preview">
      <p className="text-sm text-muted-foreground">
        Revisa los parámetros. Al confirmar se generará el contrato en estado{" "}
        <code>draft</code>; tendrás que firmarlo (Marcos) y enviarlo al cliente
        desde la vista detalle.
      </p>
      <div className="rounded-md border p-4 text-sm">
        <dl className="grid grid-cols-2 gap-3">
          <PreviewItem label="Plantilla">
            <code className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 text-xs font-mono">
              {plantillaId}
            </code>
            {template ? ` · ${template.nombre}` : null}
          </PreviewItem>
          <PreviewItem label="Tipo">
            {template?.tipo ?? "—"}
          </PreviewItem>
          <PreviewItem label="Propuesta origen">
            {proposal
              ? `${proposal.numero ?? proposal.id.slice(0, 8)}${
                  proposal.total_eur
                    ? ` · ${proposal.total_eur.toLocaleString("es-ES")} €`
                    : ""
                }`
              : "—"}
          </PreviewItem>
          <PreviewItem label="Vigencia">
            {vigenciaMeses} meses
          </PreviewItem>
          <PreviewItem label="Firmante nombre">{firmanteNombre}</PreviewItem>
          <PreviewItem label="Firmante cargo">{firmanteCargo}</PreviewItem>
        </dl>
      </div>
      <Alert variant="info">
        <AlertTitle>Estado inicial: borrador</AlertTitle>
        <AlertDescription>
          Tras generar, el contrato queda en <code>draft</code>. Firma como
          Marcos y luego envíalo al cliente vía magic link para completar la
          firma.
        </AlertDescription>
      </Alert>
    </div>
  );
}

function PreviewItem({
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
