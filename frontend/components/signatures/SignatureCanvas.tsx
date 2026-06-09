/**
 * SignatureCanvas · Ejecutable 7.7 · TIER 1 cliente firma canvas component.
 *
 * Wrapper react-signature-canvas con:
 *  - Canvas pad responsive (touchscreen móvil + ratón PC)
 *  - Inputs Nombre + Apellido (validación required)
 *  - Clear + Submit buttons R29 cliente friendly
 *  - WCAG 2.2 AA aria-labels
 *
 * NO MFA re-prompt · cliente session ya MFA-authenticated.
 */
"use client";

import { useRef, useState, type CanvasHTMLAttributes } from "react";
import SignaturePad from "react-signature-canvas";

import { Button } from "@/components/ui/button";

export type SignatureSubmitPayload = {
  signature_canvas_dataurl: string;
  signed_name: string;
  signed_surname: string;
};

export type SignatureCanvasProps = {
  /** Etiqueta del documento que se firma (mostrada al cliente). */
  documentLabel?: string;
  /** Callback cuando el cliente envía la firma. */
  onSubmit: (payload: SignatureSubmitPayload) => Promise<void> | void;
  /** Loading state mientras submit en vuelo. */
  isSubmitting?: boolean;
  /** Test id raíz · base del data-testid. */
  testIdPrefix?: string;
};

export function SignatureCanvas({
  documentLabel,
  onSubmit,
  isSubmitting = false,
  testIdPrefix = "signature-canvas",
}: SignatureCanvasProps) {
  const padRef = useRef<SignaturePad | null>(null);
  const [name, setName] = useState("");
  const [surname, setSurname] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleClear = () => {
    padRef.current?.clear();
    setError(null);
  };

  const handleSubmit = async () => {
    setError(null);
    if (!padRef.current || padRef.current.isEmpty()) {
      setError("Por favor, firma con tu dedo (móvil) o ratón (PC).");
      return;
    }
    if (!name.trim()) {
      setError("Introduce tu nombre.");
      return;
    }
    if (!surname.trim()) {
      setError("Introduce tu apellido.");
      return;
    }
    const dataUrl = padRef.current.getCanvas().toDataURL("image/png");
    try {
      await onSubmit({
        signature_canvas_dataurl: dataUrl,
        signed_name: name.trim(),
        signed_surname: surname.trim(),
      });
    } catch (exc) {
      setError(
        exc instanceof Error
          ? exc.message
          : "No se pudo enviar la firma. Inténtalo de nuevo.",
      );
    }
  };

  return (
    <div
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-5"
      data-testid={testIdPrefix}
    >
      {documentLabel ? (
        <p className="text-sm text-slate-600" data-testid={`${testIdPrefix}-label`}>
          Estás firmando: <strong>{documentLabel}</strong>
        </p>
      ) : null}

      <div>
        <label
          htmlFor={`${testIdPrefix}-name`}
          className="mb-1 block text-sm font-medium text-slate-700"
        >
          Nombre
        </label>
        <input
          id={`${testIdPrefix}-name`}
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={120}
          placeholder="p. ej. María"
          aria-label="Nombre del firmante"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
          data-testid={`${testIdPrefix}-name-input`}
        />
      </div>

      <div>
        <label
          htmlFor={`${testIdPrefix}-surname`}
          className="mb-1 block text-sm font-medium text-slate-700"
        >
          Apellido
        </label>
        <input
          id={`${testIdPrefix}-surname`}
          type="text"
          value={surname}
          onChange={(e) => setSurname(e.target.value)}
          maxLength={120}
          placeholder="p. ej. García"
          aria-label="Apellido del firmante"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-violet-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
          data-testid={`${testIdPrefix}-surname-input`}
        />
      </div>

      <div>
        <p className="mb-2 text-sm font-medium text-slate-700">Tu firma</p>
        <p className="mb-2 text-xs text-slate-500">
          Firma con tu dedo (móvil) o con el ratón (ordenador). Si te equivocas,
          pulsa <em>Borrar y volver a empezar</em>.
        </p>
        <div
          className="rounded-md border-2 border-dashed border-slate-300 bg-slate-50"
          role="img"
          aria-label="Lienzo para dibujar tu firma manuscrita"
        >
          <SignaturePad
            ref={padRef}
            canvasProps={{
              className: "h-40 w-full",
              "data-testid": `${testIdPrefix}-pad`,
            } as CanvasHTMLAttributes<HTMLCanvasElement>}
            penColor="#1e293b"
          />
        </div>
      </div>

      {error ? (
        <p
          className="text-sm text-rose-700"
          role="alert"
          data-testid={`${testIdPrefix}-error`}
        >
          {error}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={handleClear}
          disabled={isSubmitting}
          data-testid={`${testIdPrefix}-clear`}
        >
          Borrar y volver a empezar
        </Button>
        <Button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={isSubmitting}
          data-testid={`${testIdPrefix}-submit`}
        >
          {isSubmitting ? "Enviando firma..." : "Firmar documento"}
        </Button>
      </div>
    </div>
  );
}
