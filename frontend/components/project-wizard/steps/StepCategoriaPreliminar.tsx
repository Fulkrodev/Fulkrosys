"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import {
  CATEGORIA_LABELS,
  ENS_DIM_LABELS,
  IMPACT_LABELS,
  type Categoria,
  type EnsDimsValoracion,
  type ImpactLevel,
  type Step2ContextoENS,
  type Step3CategoriaPreliminar,
} from "@/lib/api/project-diagnostico";

interface StepCategoriaPreliminarProps {
  initialValue: Step3CategoriaPreliminar | null;
  contextEns: Step2ContextoENS;
  onSubmit: (data: Step3CategoriaPreliminar) => void;
  onBack: () => void;
}

const DIM_TOOLTIP_KEYS: Record<keyof typeof ENS_DIM_LABELS, string> = {
  confidencialidad: "DICAT",
  integridad: "DICAT",
  disponibilidad: "DICAT",
  autenticidad: "DICAT",
  trazabilidad: "DICAT",
};

const DIM_INLINE_HELP: Record<keyof typeof ENS_DIM_LABELS, string> = {
  confidencialidad: "Solo lo ve quien debe (sin filtraciones)",
  integridad: "Los datos no cambian sin permiso",
  disponibilidad: "Funciona cuando se necesita",
  autenticidad: "Sabes quién hizo qué (identidad probada)",
  trazabilidad: "Queda registro auditable de todo",
};

/**
 * Lógica DETERMINISTA · regla simple ENS Anexo I:
 *   - Cualquier dim ALTO → ALTA
 *   - Cualquier dim MEDIO (y ningún ALTO) → MEDIA
 *   - Todas BAJO → BÁSICA
 *
 * R1 sostener · NO LLM · trazabilidad ENAC.
 */
function suggestCategoria(dims: EnsDimsValoracion): Categoria | null {
  // N1 · la regla del maximo del Anexo I opera SOLO sobre las dimensiones
  // AFECTADAS. Una dimension no afectada no se adscribe a ningun nivel
  // (Anexo I punto 3), asi que no puede determinar la categoria. Antes no
  // existia "no afectada" y todo arrancaba en BAJO, que devolvia BASICA
  // incluso para un sistema que nadie habia valorado todavia.
  const afectadas = Object.values(dims).filter((v) => v !== "NO_AFECTADA");
  if (afectadas.length === 0) return null; // nada que categorizar
  if (afectadas.includes("ALTO")) return "ALTA";
  if (afectadas.includes("MEDIO")) return "MEDIA";
  return "BASICA";
}

// #5 · rango ordinal para el suelo heredado de la AAPP (piso · solo eleva).
const CAT_RANK: Record<Categoria, number> = { BASICA: 1, MEDIA: 2, ALTA: 3 };

/**
 * Heurística suggestion inicial dims según contexto ENS Step 2.
 * Determinista · pure function.
 */
function initialDimsFromContext(ctx: Step2ContextoENS): EnsDimsValoracion {
  const isAapp =
    ctx.sector_ens === "aapp" || ctx.tipo_organizacion === "sector_publico";
  const isLargeOrg =
    ctx.tamano_empleados === "grande" || ctx.tamano_empleados === "enterprise";
  if (isAapp && isLargeOrg) {
    return {
      confidencialidad: "ALTO",
      integridad: "ALTO",
      disponibilidad: "ALTO",
      autenticidad: "ALTO",
      trazabilidad: "ALTO",
    };
  }
  if (isAapp || ctx.sector_ens === "privado_licita_aapp") {
    return {
      confidencialidad: "MEDIO",
      integridad: "MEDIO",
      disponibilidad: "MEDIO",
      autenticidad: "BAJO",
      trazabilidad: "BAJO",
    };
  }
  return {
    confidencialidad: "BAJO",
    integridad: "BAJO",
    disponibilidad: "BAJO",
    autenticidad: "BAJO",
    trazabilidad: "BAJO",
  };
}

export function StepCategoriaPreliminar({
  initialValue,
  contextEns,
  onSubmit,
  onBack,
}: StepCategoriaPreliminarProps) {
  const [dims, setDims] = useState<EnsDimsValoracion>(
    initialValue?.dims_anexo_i ?? initialDimsFromContext(contextEns),
  );
  const [categoria, setCategoria] = useState<Categoria>(
    initialValue?.categoria_preliminar ?? "BASICA",
  );
  const [justificacion, setJustificacion] = useState(
    initialValue?.justificacion ?? "",
  );
  // #5 · suelo heredado de la AAPP (decisión A · "NINGUNO" = sin herencia).
  const [heredada, setHeredada] = useState<Categoria | "NINGUNO">(
    initialValue?.categoria_heredada_aapp ?? "NINGUNO",
  );

  // Categoría sugerida actualiza cuando dims cambian (a menos que admin override manual)
  const [overrideCategoria, setOverrideCategoria] = useState(
    initialValue?.categoria_preliminar !== undefined,
  );
  const suggested = useMemo(() => suggestCategoria(dims), [dims]);

  useEffect(() => {
    if (!overrideCategoria && suggested !== null) {
      setCategoria(suggested);
    }
  }, [suggested, overrideCategoria]);

  const handleSubmit = () => {
    const floor = heredada === "NINGUNO" ? null : heredada;
    // El suelo es un piso: la categoría enviada nunca queda por debajo (el
    // backend lo refuerza vía elevate_to_floor; mantenemos el payload coherente).
    const categoriaFinal =
      floor && CAT_RANK[floor] > CAT_RANK[categoria] ? floor : categoria;
    onSubmit({
      categoria_preliminar: categoriaFinal,
      dims_anexo_i: dims,
      justificacion: justificacion.trim() || null,
      categoria_heredada_aapp: floor,
    });
  };

  const updateDim = (
    key: keyof EnsDimsValoracion,
    value: ImpactLevel,
  ) => {
    setDims((d) => ({ ...d, [key]: value }));
  };

  return (
    <div className="space-y-4" data-testid="step-categoria">
      <div className="space-y-1">
        <h2 className="text-lg font-semibold">
          Paso 3 · Categoría preliminar <TooltipENS term="ENS" />
        </h2>
        <p className="text-sm text-muted-foreground">
          Valora cada dimensión <TooltipENS term="DICAT" /> de{" "}
          <TooltipENS term="Anexo_I" /> · sugerimos categoría por la regla
          ENS (cualquier <strong>ALTO</strong> → ALTA · cualquier{" "}
          <strong>MEDIO</strong> → MEDIA · todas <strong>BAJO</strong> →
          BÁSICA). Marcos puede sobrescribir.
        </p>
      </div>

      <div className="space-y-2 rounded-md border p-4">
        <p className="text-xs font-semibold uppercase text-muted-foreground">
          5 Dimensiones ENS Anexo I
        </p>
        <div className="grid gap-2">
          {(Object.keys(ENS_DIM_LABELS) as Array<keyof typeof ENS_DIM_LABELS>).map(
            (key) => (
              <DimRow
                key={key}
                dimKey={key}
                value={dims[key]}
                onChange={(v) => updateDim(key, v)}
              />
            ),
          )}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          <Label htmlFor="categoria-suggested">Categoría sugerida</Label>
          <Badge
            variant={
              suggested === null
                ? "warning"
                : suggested === "ALTA"
                  ? "danger"
                  : suggested === "MEDIA"
                    ? "warning"
                    : "success"
            }
            className="w-fit text-sm"
          >
            {suggested === null
              ? "Sin categorizar"
              : CATEGORIA_LABELS[suggested]}
          </Badge>
          <p className="text-[11px] text-muted-foreground">
            {suggested === null
              ? "Las cinco dimensiones están marcadas como no afectadas: no hay nada que categorizar (Anexo I, punto 3)."
              : "Calculada por regla ENS · determinista. Las dimensiones no afectadas no entran en la regla del máximo."}
          </p>
        </div>

        <div className="flex flex-col gap-1">
          <Label htmlFor="categoria-override">
            Categoría final (Marcos puede sobrescribir)
          </Label>
          <Select
            value={categoria}
            onValueChange={(v) => {
              setCategoria(v as Categoria);
              setOverrideCategoria(true);
            }}
          >
            <SelectTrigger
              id="categoria-override"
              data-testid="field-categoria-override"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(CATEGORIA_LABELS) as Categoria[]).map((c) => (
                <SelectItem key={c} value={c}>
                  <TooltipENS term={`categoria_${c.toLowerCase()}` as never} text="" />
                  {CATEGORIA_LABELS[c]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {overrideCategoria && categoria !== suggested && (
            <Alert variant="warning">
              <AlertTitle>Override manual</AlertTitle>
              <AlertDescription>
                Justificación obligatoria · auditor ENAC pedirá razón si
                difiere de la regla ENS.
              </AlertDescription>
            </Alert>
          )}
        </div>
      </div>

      {/* #5 · suelo de categoría heredado de la AAPP contratante (decisión A) */}
      <div className="space-y-2 rounded-md border border-dashed p-4">
        <Label htmlFor="categoria-heredada">
          ¿La AAPP ya categorizó este servicio? <TooltipENS term="ENS" />
        </Label>
        <p className="text-[11px] text-muted-foreground">
          Si el pliego/contrato de la licitación indica la categoría que la
          Administración asignó, fíjala aquí. Es un <strong>suelo</strong>: la
          categoría no puede declararse por debajo (solo puede subir).
        </p>
        <Select
          value={heredada}
          onValueChange={(v) => setHeredada(v as Categoria | "NINGUNO")}
        >
          <SelectTrigger
            id="categoria-heredada"
            data-testid="field-categoria-heredada"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="NINGUNO">Sin herencia / no consta</SelectItem>
            <SelectItem value="MEDIA">{CATEGORIA_LABELS.MEDIA}</SelectItem>
            <SelectItem value="ALTA">{CATEGORIA_LABELS.ALTA}</SelectItem>
          </SelectContent>
        </Select>
        {heredada !== "NINGUNO" && CAT_RANK[heredada] > CAT_RANK[categoria] && (
          <Alert variant="warning" data-testid="floor-elevates-alert">
            <AlertTitle>Suelo heredado eleva la categoría</AlertTitle>
            <AlertDescription>
              La AAPP categorizó <strong>{CATEGORIA_LABELS[heredada]}</strong>: la
              categoría del proyecto se elevará a {CATEGORIA_LABELS[heredada]} (no
              puede declararse por debajo de lo que categorizó la Administración).
            </AlertDescription>
          </Alert>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <Label htmlFor="justificacion">
          Justificación de categoría {overrideCategoria && categoria !== suggested && (
            <span className="text-fulkro-warning">*</span>
          )}
        </Label>
        <Textarea
          id="justificacion"
          rows={3}
          value={justificacion}
          onChange={(e) => setJustificacion(e.target.value)}
          placeholder="Ej: Sistema con datos personales clientes AAPP · alcance ENS MEDIA"
          data-testid="field-justificacion"
        />
      </div>

      <div className="flex items-center justify-between gap-2 pt-2">
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          data-testid="step3-back"
        >
          <ChevronLeft size={14} className="mr-1" />
          Atrás
        </Button>
        <Button onClick={handleSubmit} data-testid="step3-next">
          Siguiente
          <ChevronRight size={14} className="ml-1" />
        </Button>
      </div>
    </div>
  );
}

function DimRow({
  dimKey,
  value,
  onChange,
}: {
  dimKey: keyof typeof ENS_DIM_LABELS;
  value: ImpactLevel;
  onChange: (v: ImpactLevel) => void;
}) {
  return (
    <div
      className="flex items-center justify-between gap-3 rounded-md border p-2"
      data-testid={`dim-row-${dimKey}`}
    >
      <div className="flex flex-1 flex-col gap-0.5 min-w-0">
        <span className="flex items-center gap-1.5 text-sm font-medium">
          {ENS_DIM_LABELS[dimKey]}
          <TooltipENS term={DIM_TOOLTIP_KEYS[dimKey] as never} text="" />
        </span>
        <span className="text-[11px] text-muted-foreground">
          {DIM_INLINE_HELP[dimKey]}
        </span>
      </div>
      <div className="flex gap-1">
        {/* N1 · "No afectada" es una opcion explicita, no la ausencia de
            click: el Anexo I punto 3 distingue una dimension en BAJO de una
            que no se ve afectada, y son conjuntos de medidas distintos. */}
        {(["NO_AFECTADA", "BAJO", "MEDIO", "ALTO"] as ImpactLevel[]).map((level) => (
          <Button
            key={level}
            size="sm"
            variant={value === level ? "primary" : "outline"}
            onClick={() => onChange(level)}
            data-testid={`dim-${dimKey}-${level}`}
          >
            {IMPACT_LABELS[level]}
          </Button>
        ))}
      </div>
    </div>
  );
}
