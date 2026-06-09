"use client";

/**
 * ContactDepartmentAssignSelect · sub-atom 1.C.F.3.2.
 *
 * Dropdown inline para asignar/des-asignar un empleado a un área. Renderiza
 * la lista de departments del proyecto + opción "Sin asignar" (NULL FK).
 *
 * Optimistic: muestra el nuevo valor inmediatamente y revierte si la API
 * falla. Llama `onChanged` al cierre exitoso para refrescar la tabla.
 */
import { useState } from "react";
import { toast } from "sonner";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { ApiError } from "@/lib/api";
import {
  assignContactToDepartment,
  type Department,
} from "@/lib/api/departments";

const UNASSIGNED_VALUE = "__unassigned__";

type Props = {
  projectId: string;
  contactId: string;
  currentDepartmentId: string | null;
  departments: Department[];
  onChanged?: (nextDepartmentId: string | null) => void;
  disabled?: boolean;
};

export function ContactDepartmentAssignSelect({
  projectId,
  contactId,
  currentDepartmentId,
  departments,
  onChanged,
  disabled,
}: Props) {
  const [value, setValue] = useState<string>(
    currentDepartmentId ?? UNASSIGNED_VALUE,
  );
  const [submitting, setSubmitting] = useState(false);

  const handleChange = async (next: string) => {
    const previous = value;
    setValue(next);
    setSubmitting(true);
    try {
      const nextDeptId = next === UNASSIGNED_VALUE ? null : next;
      await assignContactToDepartment(projectId, contactId, nextDeptId);
      onChanged?.(nextDeptId);
    } catch (err) {
      setValue(previous);
      const msg =
        err instanceof ApiError
          ? `Error ${err.status}: ${err.message}`
          : "Error asignando área";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Select
      value={value}
      onValueChange={(next) => void handleChange(next)}
      disabled={disabled || submitting}
    >
      <SelectTrigger className="h-8 w-[180px]">
        <SelectValue placeholder="Sin asignar" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={UNASSIGNED_VALUE}>
          <span className="text-fulkro-ink-500">Sin asignar</span>
        </SelectItem>
        {departments.map((d) => (
          <SelectItem key={d.id} value={d.id}>
            {d.code} — {d.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
