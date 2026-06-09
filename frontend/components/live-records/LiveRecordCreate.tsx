"use client";

/**
 * LiveRecordCreate · dialog modal crear entrada registro vivo.
 *
 * Sub-atom 1.C.B fase 4c. Form dinamico generado desde FIELD_CONFIGS +
 * validacion Zod (front-end UX) · backend re-valida con HTTP 422 fallback.
 *
 * Soporta los 26 register_types E-300..E-325 sin component-per-type
 * (drive 100% por metadata FIELD_CONFIGS).
 */
import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm, type FieldValues } from "react-hook-form";

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
import { Textarea } from "@/components/ui/textarea";
import {
  type FieldConfig,
  getFieldConfig,
  getZodSchema,
} from "@/lib/schemas/live-records";
import {
  REGISTER_TYPE_LABELS,
  type RegisterType,
} from "@/lib/types/live-records";


interface LiveRecordCreateProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  registerType: RegisterType;
  onSubmit: (entryData: Record<string, unknown>) => Promise<void>;
}


function defaultValuesFor(fields: readonly FieldConfig[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    if (f.kind === "boolean") out[f.key] = false;
    else if (f.kind === "number") out[f.key] = undefined;
    else out[f.key] = "";
  }
  return out;
}


function normalizeForSubmit(
  fields: readonly FieldConfig[],
  values: FieldValues,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    const raw = values[f.key];
    if (f.kind === "number") {
      if (raw === "" || raw === null || raw === undefined) continue;
      const num = typeof raw === "number" ? raw : Number(raw);
      if (!Number.isNaN(num)) out[f.key] = num;
    } else if (f.kind === "boolean") {
      out[f.key] = Boolean(raw);
    } else if (raw === "" || raw === null || raw === undefined) {
      if (f.required) out[f.key] = raw;
    } else {
      out[f.key] = raw;
    }
  }
  return out;
}


export function LiveRecordCreate({
  open,
  onOpenChange,
  registerType,
  onSubmit,
}: LiveRecordCreateProps) {
  const fields = getFieldConfig(registerType);
  const schema = getZodSchema(registerType);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
    setError,
  } = useForm<FieldValues>({
    resolver: zodResolver(schema),
    defaultValues: defaultValuesFor(fields),
  });

  useEffect(() => {
    if (!open) reset(defaultValuesFor(fields));
  }, [open, fields, reset]);

  async function submitHandler(values: FieldValues) {
    try {
      const payload = normalizeForSubmit(fields, values);
      await onSubmit(payload);
      reset(defaultValuesFor(fields));
      onOpenChange(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error al crear entrada";
      setError("root", { message: msg });
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-fulkro-ink-800">
            Nueva entrada · {registerType}
          </DialogTitle>
          <DialogDescription className="text-sm text-fulkro-ink-600">
            {REGISTER_TYPE_LABELS[registerType]}
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={handleSubmit(submitHandler)}
          className="space-y-4 max-h-[60vh] overflow-y-auto pr-2"
        >
          {fields.map((field) => (
            <FieldRenderer
              key={field.key}
              field={field}
              register={register}
              error={errors[field.key]?.message as string | undefined}
            />
          ))}

          {errors.root?.message && (
            <p className="text-sm text-red-700">{String(errors.root.message)}</p>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creando..." : "Crear entrada"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}


function FieldRenderer({
  field,
  register,
  error,
}: {
  field: FieldConfig;
  register: ReturnType<typeof useForm>["register"];
  error?: string;
}) {
  const id = `lr-field-${field.key}`;
  const required = field.required;

  let control: React.ReactNode;
  if (field.kind === "textarea") {
    control = (
      <Textarea
        id={id}
        {...register(field.key)}
        rows={3}
        placeholder={field.placeholder}
      />
    );
  } else if (field.kind === "select") {
    control = (
      <select
        id={id}
        {...register(field.key)}
        className="flex h-10 w-full rounded-md border border-fulkro-ink-300 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-500"
      >
        <option value="">— seleccionar —</option>
        {field.options?.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  } else if (field.kind === "boolean") {
    control = (
      <label className="inline-flex items-center gap-2 text-sm text-fulkro-ink-700">
        <input
          id={id}
          type="checkbox"
          {...register(field.key)}
          className="h-4 w-4 rounded border-fulkro-ink-300 text-fulkro-primary-700 focus:ring-fulkro-primary-500"
        />
        <span>{field.label}</span>
      </label>
    );
  } else if (field.kind === "number") {
    control = (
      <Input
        id={id}
        type="number"
        step="any"
        {...register(field.key, { valueAsNumber: true })}
        placeholder={field.placeholder}
      />
    );
  } else if (field.kind === "date") {
    control = <Input id={id} type="date" {...register(field.key)} />;
  } else if (field.kind === "datetime") {
    control = <Input id={id} type="datetime-local" {...register(field.key)} />;
  } else {
    control = (
      <Input
        id={id}
        type="text"
        {...register(field.key)}
        placeholder={field.placeholder}
      />
    );
  }

  return (
    <div className="space-y-1.5">
      {field.kind !== "boolean" && (
        <Label htmlFor={id} className="text-xs font-semibold text-fulkro-ink-700">
          {field.label}
          {required && <span className="ml-1 text-red-600">*</span>}
        </Label>
      )}
      {control}
      {field.helpText && (
        <p className="text-[11px] text-fulkro-ink-500">{field.helpText}</p>
      )}
      {error && <p className="text-xs text-red-700">{error}</p>}
    </div>
  );
}
