"use client";

/**
 * McpToolFormModal · Sub-atom 1.D.E.B v3.11.
 *
 * Modal form parametrizado per tool. Render dinámico desde
 * `MCPToolSchema.params[]` con validación required local + soporte tipos
 * string / integer / enum.
 *
 * Submit · POST /api/v1/projects/{id}/mcps/{mcp}/tools/{tool}/execute →
 * devuelve execution_id que el padre usa para abrir McpExecutionProgress.
 *
 * R23 sostener · project-scoped · auth require_owner backend.
 */
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { mcpsApi, type MCPToolSchema } from "@/lib/api/mcps";

import { mcpsKeys } from "@/hooks/useMCPs";

interface McpToolFormModalProps {
  projectId: string;
  tool: MCPToolSchema | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onExecutionStarted: (executionId: string) => void;
}

export function McpToolFormModal({
  projectId,
  tool,
  open,
  onOpenChange,
  onExecutionStarted,
}: McpToolFormModalProps) {
  const qc = useQueryClient();
  const [values, setValues] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (open && tool) {
      const defaults: Record<string, unknown> = {};
      for (const p of tool.params) {
        if (p.default !== null && p.default !== undefined) {
          defaults[p.name] = p.default;
        }
      }
      setValues(defaults);
    } else if (!open) {
      setValues({});
    }
  }, [open, tool]);

  const executeMutation = useMutation({
    mutationFn: () => {
      if (!tool) throw new Error("No hay tool seleccionado");
      return mcpsApi.execute(projectId, tool.mcp_name, tool.tool_name, values);
    },
    onSuccess: (execution) => {
      toast.success("MCP ejecutándose", {
        description: `${tool?.label} · execution ${execution.execution_id.slice(
          0,
          8,
        )}`,
      });
      qc.invalidateQueries({ queryKey: mcpsKeys.executions(projectId) });
      onExecutionStarted(execution.execution_id);
      onOpenChange(false);
    },
    onError: (err) => {
      toast.error("No se pudo ejecutar el MCP", {
        description: err instanceof Error ? err.message : undefined,
      });
    },
  });

  const missingRequired = useMemo(() => {
    if (!tool) return [] as string[];
    return tool.params
      .filter((p) => {
        if (!p.required) return false;
        const v = values[p.name];
        return v === undefined || v === null || v === "";
      })
      .map((p) => p.name);
  }, [tool, values]);

  if (!tool) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-xl"
        data-testid={`mcp-tool-form-${tool.tool_name}`}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Play size={16} />
            {tool.label}
          </DialogTitle>
          <DialogDescription>
            {tool.description} · Risk:{" "}
            <span className="font-semibold">{tool.risk_level}</span> · ETA{" "}
            ~{Math.round(tool.estimated_duration_s / 60)} min.
          </DialogDescription>
        </DialogHeader>

        <Alert variant="info">
          <AlertTitle>Ejecución project-scoped</AlertTitle>
          <AlertDescription>
            El reporte se adjuntará automáticamente al IDMS (folder{" "}
            <code>13_Informes_Tecnicos</code> · clasificación{" "}
            <code>informe</code>) tras completar.
          </AlertDescription>
        </Alert>

        <div className="space-y-3" data-testid="mcp-tool-form-fields">
          {tool.params.map((param) => (
            <ParamField
              key={param.name}
              param={param}
              value={values[param.name]}
              onChange={(v) =>
                setValues((prev) => ({ ...prev, [param.name]: v }))
              }
            />
          ))}
        </div>

        <DialogFooter className="flex justify-between gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={executeMutation.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={() => executeMutation.mutate()}
            disabled={
              executeMutation.isPending || missingRequired.length > 0
            }
            data-testid="mcp-tool-form-submit"
          >
            {executeMutation.isPending ? (
              <Loader2 size={14} className="mr-1 animate-spin" />
            ) : (
              <Play size={14} className="mr-1" />
            )}
            Iniciar escaneo
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ParamFieldProps {
  param: MCPToolSchema["params"][number];
  value: unknown;
  onChange: (value: unknown) => void;
}

function ParamField({ param, value, onChange }: ParamFieldProps) {
  const id = `mcp-param-${param.name}`;
  const label = (
    <Label htmlFor={id} className="flex items-center gap-1">
      <span>{param.name}</span>
      {param.required && (
        <span className="text-fulkro-warning" aria-label="requerido">
          *
        </span>
      )}
    </Label>
  );
  const help = param.description ? (
    <p className="text-[11px] text-muted-foreground">{param.description}</p>
  ) : null;

  if (param.type === "enum" && param.enum) {
    return (
      <div className="space-y-1" data-testid={`param-${param.name}`}>
        {label}
        <Select
          value={String(value ?? param.default ?? "")}
          onValueChange={onChange}
        >
          <SelectTrigger id={id}>
            <SelectValue placeholder={param.placeholder ?? "Selecciona…"} />
          </SelectTrigger>
          <SelectContent>
            {param.enum.map((opt) => (
              <SelectItem key={opt} value={opt}>
                {opt}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {help}
      </div>
    );
  }

  if (param.type === "integer") {
    return (
      <div className="space-y-1" data-testid={`param-${param.name}`}>
        {label}
        <Input
          id={id}
          type="number"
          value={
            value === undefined || value === null
              ? ""
              : String(value as number | string)
          }
          placeholder={param.placeholder ?? ""}
          onChange={(e) => {
            const n = e.target.value === "" ? "" : Number(e.target.value);
            onChange(n);
          }}
        />
        {help}
      </div>
    );
  }

  return (
    <div className="space-y-1" data-testid={`param-${param.name}`}>
      {label}
      <Input
        id={id}
        type="text"
        value={
          value === undefined || value === null ? "" : String(value as string)
        }
        placeholder={param.placeholder ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
      {help}
    </div>
  );
}
