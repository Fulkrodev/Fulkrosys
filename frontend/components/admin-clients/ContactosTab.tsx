"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

import { ContactCreateWizard } from "./contacts/ContactCreateWizard";
import { ContactDetail } from "./contacts/ContactDetail";
import { ContactImporter } from "./contacts/ContactImporter";
import { ContactsList } from "./contacts/ContactsList";

type Props = {
  clientId: string;
};

/**
 * Tab Contactos (FASE 5.5 — sub-bloque 5.5.E).
 *
 * Reemplaza ``ContactosTabPlaceholder`` con UI funcional completa:
 *   - DataTable con filtros (activo / categoría / búsqueda)
 *   - Wizard 3 pasos creación
 *   - Sheet detalle con form editable + timeline DESC
 *   - Importer/Exporter CSV
 *
 * Selección de fila en lista abre Sheet detalle. Cambios desde Sheet
 * (update / deactivate / activate / delete) o Wizard (create) /
 * Importer (bulk) refrescan la lista vía ``reloadKey`` bump.
 */
export function ContactosTab({ clientId }: Props) {
  const [reloadKey, setReloadKey] = useState(0);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [importerOpen, setImporterOpen] = useState(false);
  const [detailContactId, setDetailContactId] = useState<string | null>(null);

  const reload = () => setReloadKey((k) => k + 1);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold text-[color:var(--fulkro-title)]">
            Contactos
          </h2>
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Agenda profesional cliente. Usados por A18 (interlocutor),
            M14 (signatario contrato), M29 (mensajería) y A14
            (contexto copilot).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setImporterOpen(true)}
          >
            Importar / Exportar
          </Button>
          <Button type="button" onClick={() => setWizardOpen(true)}>
            + Nuevo contacto
          </Button>
        </div>
      </div>

      <ContactsList
        clientId={clientId}
        reloadKey={reloadKey}
        onRowSelect={(cid) => setDetailContactId(cid)}
      />

      <ContactCreateWizard
        clientId={clientId}
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        onCreated={reload}
      />

      <ContactImporter
        clientId={clientId}
        open={importerOpen}
        onOpenChange={setImporterOpen}
        onImported={reload}
      />

      <ContactDetail
        clientId={clientId}
        contactId={detailContactId}
        open={detailContactId !== null}
        onOpenChange={(next) => {
          if (!next) setDetailContactId(null);
        }}
        onChanged={reload}
      />
    </div>
  );
}
