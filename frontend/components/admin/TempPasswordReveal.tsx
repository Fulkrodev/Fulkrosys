"use client";

/**
 * TempPasswordReveal · diálogo persistente para mostrar una contraseña
 * temporal generada por el backend (reset / invitación de usuario portal).
 *
 * Reemplaza el patrón inseguro de mostrar la contraseña en un toast
 * auto-desechable (§1.8): el toast desaparece solo y no se puede recuperar,
 * así que la credencial podía perderse antes de copiarse. Este diálogo
 * persiste hasta que el admin lo cierra explícitamente y ofrece un botón
 * "Copiar" (navigator.clipboard) — patrón ya probado en
 * projects/[id]/equipo/_components/PortalUserPanel.tsx (OPS-026 DRY).
 *
 * Uso (controlado por el componente padre):
 *   const [tempPwd, setTempPwd] = React.useState<string | null>(null);
 *   ...onSuccess: (data) => setTempPwd(data.temp_password) ...
 *   <TempPasswordReveal
 *     tempPassword={tempPwd}
 *     onClose={() => setTempPwd(null)}
 *     title="Contraseña temporal generada"
 *   />
 */
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface TempPasswordRevealProps {
  /** La contraseña temporal a mostrar. `null` mantiene el diálogo cerrado. */
  tempPassword: string | null;
  /** Se invoca cuando el admin cierra el diálogo (debe poner tempPassword a null). */
  onClose: () => void;
  /** Título del diálogo. */
  title?: string;
  /** Texto descriptivo bajo el título. */
  description?: string;
}

export function TempPasswordReveal({
  tempPassword,
  onClose,
  title = "Contraseña temporal generada",
  description = "Cópiala y entrégasela al usuario por un canal seguro. El usuario deberá cambiarla en su primer acceso.",
}: TempPasswordRevealProps) {
  const open = tempPassword !== null;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
    >
      <DialogContent
        className="sm:max-w-md"
        data-testid="temp-password-reveal"
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <code
          className="block break-all rounded-md border border-fulkro-ink-100 bg-fulkro-ink-50 px-3 py-2 font-mono text-sm"
          data-testid="temp-password-value"
        >
          {tempPassword}
        </code>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              if (tempPassword) {
                void navigator.clipboard.writeText(tempPassword);
                toast.success("Contraseña copiada");
              }
            }}
            data-testid="temp-password-copy"
          >
            Copiar
          </Button>
          <Button type="button" onClick={onClose}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
