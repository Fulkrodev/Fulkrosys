/**
 * AappBillingPanel · Facturas AAPP Facturae 3.2.x + FACe (SAN-C MB-11.3).
 *
 * Crear invoice draft → generar Facturae XML → firmar XAdES (graceful
 * skip si cert FNMT no disponible · stub honesto) → submit FACe (manual
 * portal) → calc late interest Ley 3/2004.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  FileText,
  Loader2,
  Plus,
} from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { InfoTag } from "@/components/ui/info-tag";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type FaceSubmitResponse,
  type FacturaeGenerationResponse,
  type InvoiceAapp,
  type InvoiceAappCreate,
  createInvoiceAapp,
  generateFacturae,
  getLateInterest,
  listInvoicesAapp,
  submitFace,
} from "@/lib/admin-aapp-billing/api";

interface Props {
  projectId: string;
}

const _emptyForm = (): InvoiceAappCreate => ({
  invoice_number: "",
  amount_eur: "",
  dir3_oficina_contable: "",
  dir3_organo_gestor: "",
  dir3_unidad_tramitadora: "",
});

export function AappBillingPanel({ projectId }: Props) {
  const qc = useQueryClient();
  const [form, setForm] = useState<InvoiceAappCreate>(_emptyForm());

  const invKey = ["invoices-aapp", projectId];
  const { data: invoices } = useQuery<InvoiceAapp[]>({
    queryKey: invKey,
    queryFn: () => listInvoicesAapp(projectId),
  });

  const createMutation = useMutation({
    mutationFn: (body: InvoiceAappCreate) => createInvoiceAapp(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: invKey });
      setForm(_emptyForm());
    },
  });

  const generateMutation = useMutation<
    FacturaeGenerationResponse,
    Error,
    string
  >({
    mutationFn: (id) => generateFacturae(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: invKey }),
  });

  const faceMutation = useMutation<FaceSubmitResponse, Error, string>({
    mutationFn: (id) => submitFace(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: invKey }),
  });

  const interestMutation = useMutation({
    mutationFn: (id: string) => getLateInterest(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: invKey }),
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>
            Facturas AAPP{" "}
            <TooltipENS text="Facturación electrónica obligatoria a Administraciones Públicas · formato Facturae XML firmado XAdES · enviado por portal FACe." />
          </CardTitle>
        </CardHeader>
        <CardContent>
          {!invoices && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando…
            </div>
          )}
          {invoices && invoices.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Sin facturas. Crea la primera abajo.
            </p>
          )}
          {invoices && invoices.length > 0 && (
            <ul className="space-y-3">
              {invoices.map((inv) => (
                <li key={inv.id} className="border rounded p-3 space-y-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <strong>{inv.invoice_number}</strong>
                    <Badge variant="outline">{inv.status}</Badge>
                    <span className="text-sm">{inv.amount_eur} €</span>
                    {inv.interest_owed_eur && (
                      <Badge variant="warning">
                        Mora: {inv.interest_owed_eur} €
                      </Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    DIR3: OC {inv.dir3_oficina_contable} / OG{" "}
                    {inv.dir3_organo_gestor} / UT {inv.dir3_unidad_tramitadora}
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => generateMutation.mutate(inv.id)}
                      disabled={generateMutation.isPending}
                    >
                      <FileText className="h-3 w-3 mr-1" />
                      Generar <InfoTag term="Facturae" display="Facturae" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => faceMutation.mutate(inv.id)}
                      disabled={faceMutation.isPending}
                    >
                      Submit <InfoTag term="FACE" display="FACe" />
                    </Button>
                    {inv.payment_due_date && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => interestMutation.mutate(inv.id)}
                        disabled={interestMutation.isPending}
                      >
                        Calcular mora
                      </Button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {generateMutation.data && (
        <Alert
          variant={generateMutation.data.xades_signed ? "default" : "warning"}
        >
          {generateMutation.data.xades_signed ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <AlertTriangle className="h-4 w-4" />
          )}
          <AlertTitle>
            Facturae XML generado · {generateMutation.data.xml_size_bytes} bytes
          </AlertTitle>
          <AlertDescription className="mt-1 text-sm">
            {generateMutation.data.xades_signed ? (
              <>
                Firmado <InfoTag term="XAdES" display="XAdES" /> con cert FNMT.
              </>
            ) : (
              `XAdES omitido: ${generateMutation.data.xades_skip_reason}`
            )}
          </AlertDescription>
        </Alert>
      )}

      {faceMutation.data && (
        <Alert variant="warning">
          <ExternalLink className="h-4 w-4" />
          <AlertTitle>FACe submission · modo manual</AlertTitle>
          <AlertDescription className="space-y-2 mt-2">
            {faceMutation.data.warning_no_signature && (
              <p className="text-xs text-destructive">
                {faceMutation.data.warning_no_signature}
              </p>
            )}
            <a
              href={faceMutation.data.face_portal_url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline text-sm"
            >
              Abrir portal FACe →
            </a>
            <ol className="list-decimal pl-5 text-xs space-y-0.5">
              {faceMutation.data.manual_steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </AlertDescription>
        </Alert>
      )}

      {interestMutation.data && (
        <Alert>
          <AlertTitle>Cálculo morosidad Ley 3/2004</AlertTitle>
          <AlertDescription className="text-sm space-y-1 mt-1">
            <div>Días retraso: {interestMutation.data.days_late}</div>
            <div>
              Tipo BCE: {interestMutation.data.bce_rate_pct}% + 8 puntos ={" "}
              {interestMutation.data.total_rate_pct}%
            </div>
            <div className="font-bold">
              Intereses adeudados: {interestMutation.data.interest_owed_eur} €
            </div>
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Crear factura AAPP</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="num">Nº factura</Label>
              <Input
                id="num"
                value={form.invoice_number}
                onChange={(e) =>
                  setForm({ ...form, invoice_number: e.target.value })
                }
              />
            </div>
            <div>
              <Label htmlFor="amount">Importe (€)</Label>
              <Input
                id="amount"
                type="number"
                step="0.01"
                value={form.amount_eur}
                onChange={(e) =>
                  setForm({ ...form, amount_eur: e.target.value })
                }
              />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label htmlFor="oc">DIR3 OC</Label>
              <Input
                id="oc"
                value={form.dir3_oficina_contable}
                onChange={(e) =>
                  setForm({ ...form, dir3_oficina_contable: e.target.value })
                }
              />
            </div>
            <div>
              <Label htmlFor="og">DIR3 OG</Label>
              <Input
                id="og"
                value={form.dir3_organo_gestor}
                onChange={(e) =>
                  setForm({ ...form, dir3_organo_gestor: e.target.value })
                }
              />
            </div>
            <div>
              <Label htmlFor="ut">DIR3 UT</Label>
              <Input
                id="ut"
                value={form.dir3_unidad_tramitadora}
                onChange={(e) =>
                  setForm({ ...form, dir3_unidad_tramitadora: e.target.value })
                }
              />
            </div>
          </div>
          <div>
            <Label htmlFor="due">Payment due date (Ley 3/2004 · 30 días)</Label>
            <Input
              id="due"
              type="date"
              value={form.payment_due_date ?? ""}
              onChange={(e) =>
                setForm({ ...form, payment_due_date: e.target.value })
              }
            />
          </div>
          <Button
            onClick={() => createMutation.mutate(form)}
            disabled={
              createMutation.isPending ||
              !form.invoice_number ||
              !form.amount_eur
            }
          >
            {createMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Plus className="h-4 w-4 mr-2" />
            )}
            Crear draft
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
