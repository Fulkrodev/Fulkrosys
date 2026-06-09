/**
 * BackupPolicy321Panel · Política copias 3-2-1 (SAN-C MB-11.5).
 *
 * POST /api/v1/backup-policy/3-2-1/evaluate · stateless evaluation
 */
"use client";

import { useMutation } from "@tanstack/react-query";
import { CheckCircle2, Loader2, Plus, Trash2, XCircle } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type BackupCopyInput,
  type Compliance321Response,
  evaluate321,
} from "@/lib/admin-backup-policy/api";

export function BackupPolicy321Panel() {
  const [copies, setCopies] = useState<BackupCopyInput[]>([
    { label: "Copia producción", media_type: "disk", is_offsite: false },
  ]);

  const mutation = useMutation<Compliance321Response, Error, BackupCopyInput[]>({
    mutationFn: (input) => evaluate321(input),
  });

  const updateCopy = (idx: number, patch: Partial<BackupCopyInput>) => {
    setCopies(
      copies.map((c, i) => (i === idx ? { ...c, ...patch } : c)),
    );
  };

  const removeCopy = (idx: number) => {
    setCopies(copies.filter((_, i) => i !== idx));
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Política 3-2-1 · Configuración copias</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {copies.map((c, idx) => (
            <div key={idx} className="grid grid-cols-12 gap-2 items-end">
              <div className="col-span-5">
                <Label htmlFor={`label-${idx}`}>Label</Label>
                <Input
                  id={`label-${idx}`}
                  value={c.label}
                  onChange={(e) => updateCopy(idx, { label: e.target.value })}
                />
              </div>
              <div className="col-span-3">
                <Label htmlFor={`media-${idx}`}>Medio</Label>
                <Input
                  id={`media-${idx}`}
                  value={c.media_type}
                  onChange={(e) =>
                    updateCopy(idx, { media_type: e.target.value })
                  }
                  placeholder="disk · cloud · tape"
                />
              </div>
              <div className="col-span-3 flex items-center gap-2 pb-2">
                <input
                  id={`offsite-${idx}`}
                  type="checkbox"
                  checked={c.is_offsite}
                  onChange={(e) =>
                    updateCopy(idx, { is_offsite: e.target.checked })
                  }
                />
                <Label htmlFor={`offsite-${idx}`}>Offsite</Label>
              </div>
              <Button
                size="icon"
                variant="ghost"
                onClick={() => removeCopy(idx)}
                aria-label="Eliminar copia"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                setCopies([
                  ...copies,
                  { label: "", media_type: "", is_offsite: false },
                ])
              }
            >
              <Plus className="h-4 w-4 mr-1" />
              Añadir copia
            </Button>
            <Button
              size="sm"
              onClick={() => mutation.mutate(copies)}
              disabled={mutation.isPending}
            >
              {mutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              )}
              Evaluar 3-2-1
            </Button>
          </div>
        </CardContent>
      </Card>

      {mutation.data && (
        <Alert variant={mutation.data.compliant ? "default" : "danger"}>
          {mutation.data.compliant ? (
            <CheckCircle2 className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          <AlertTitle>
            {mutation.data.compliant ? "Compliant 3-2-1" : "No compliant"}
          </AlertTitle>
          <AlertDescription className="space-y-2 mt-2">
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge variant="secondary">
                Copias: {mutation.data.copies_count}
              </Badge>
              <Badge variant="secondary">
                Medios: {mutation.data.media_types.join(", ") || "—"}
              </Badge>
              <Badge variant="secondary">
                Offsite: {mutation.data.offsite_count}
              </Badge>
            </div>
            {mutation.data.gaps.length > 0 && (
              <ul className="list-disc pl-5 text-sm">
                {mutation.data.gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            )}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
