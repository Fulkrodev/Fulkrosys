"use client";

/**
 * InesAnnualReportPanel · SAN-C.MB-10.4.
 *
 * Genera reporte INES anual (CCN-STIC 824/844) para la organización del
 * proyecto. El JSON canónico se descarga para subida al portal INES web ·
 * el DOCX legible se imprime para revisión Dirección + auditor.
 *
 * Refs: SAN-C.MB-10.4 · cierra fantasma frontend MB-10.4.
 */
import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { FileDown, FileJson, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";

interface ProjectHeaderClienteOnly {
  cliente: { id: string };
}

async function downloadDocx(orgId: string, year: number): Promise<Blob> {
  const headers = new Headers();
  const csrf = getCsrfToken();
  if (csrf) headers.set(CSRF_HEADER, csrf);
  const res = await fetch(
    `/api/v1/conformity/organizations/${orgId}/ines/${year}/docx`,
    { method: "POST", headers, credentials: "include" },
  );
  if (!res.ok) throw new Error(res.statusText);
  return res.blob();
}

async function downloadJson(orgId: string, year: number): Promise<Blob> {
  const res = await fetch(
    `/api/v1/conformity/organizations/${orgId}/ines/${year}/json`,
    { credentials: "include" },
  );
  if (!res.ok) throw new Error(res.statusText);
  const json = await res.json();
  return new Blob([JSON.stringify(json, null, 2)], {
    type: "application/json",
  });
}

interface InesAnnualReportPanelProps {
  projectId: string;
}

export function InesAnnualReportPanel({ projectId }: InesAnnualReportPanelProps) {
  const headerQuery = useQuery<ProjectHeaderClienteOnly>({
    queryKey: ["project-header-clientid", projectId],
    queryFn: () => api(`/api/v1/projects/${projectId}/header`),
    staleTime: 5 * 60 * 1000,
  });

  const [year, setYear] = React.useState(new Date().getFullYear());
  const [busy, setBusy] = React.useState<"json" | "docx" | null>(null);

  const orgId = headerQuery.data?.cliente.id;

  const handle = async (kind: "json" | "docx") => {
    if (!orgId) return;
    setBusy(kind);
    try {
      const blob =
        kind === "json"
          ? await downloadJson(orgId, year)
          : await downloadDocx(orgId, year);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ines_${year}_${orgId}.${kind}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`INES ${year} (${kind.toUpperCase()}) generado`);
    } catch (e) {
      toast.error("Error generando INES", {
        description: e instanceof Error ? e.message : kind,
      });
    } finally {
      setBusy(null);
    }
  };

  if (!orgId) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Informe INES anual (CCN-STIC 824/844)</CardTitle>
        <p className="text-sm text-muted-foreground">
          Reporte estado seguridad obligatorio sector público · agrega
          sistemas en alcance + incidentes por severidad + madurez procesos +
          inversión + plan año siguiente.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium" htmlFor="ines-year">
            Año fiscal:
          </label>
          <input
            id="ines-year"
            type="number"
            min={2020}
            max={2099}
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="w-24 rounded-md border px-2 py-1 text-sm"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => handle("docx")} disabled={busy !== null}>
            {busy === "docx" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generando…
              </>
            ) : (
              <>
                <FileDown className="mr-2 h-4 w-4" />
                Descargar DOCX (Dirección)
              </>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={() => handle("json")}
            disabled={busy !== null}
          >
            {busy === "json" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Generando…
              </>
            ) : (
              <>
                <FileJson className="mr-2 h-4 w-4" />
                Descargar JSON (portal INES)
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
