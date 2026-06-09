/**
 * MensajesTab funcional — embed M29 admin filtered por single cliente.
 *
 * Sustituye MensajesTabPlaceholder (FASE 6 sub-bloque 6.B.2). Reusa
 * AdminInboxList con prop clientIdFilter + AdminMessageThread Sheet
 * + AdminMessageComposer Dialog pre-filled con clientId.
 */
"use client";

import { Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

import { AdminInboxList } from "../../../messages/_components/AdminInboxList";
import { AdminMessageComposer } from "../../../messages/_components/AdminMessageComposer";
import { AdminMessageThread } from "../../../messages/_components/AdminMessageThread";

interface MensajesTabProps {
  clientId: string;
}

export function MensajesTab({ clientId }: MensajesTabProps) {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [composerOpen, setComposerOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  function bumpRefresh() {
    setRefreshKey((k) => k + 1);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-[color:var(--fulkro-title)]">
            Mensajes con este cliente
          </h3>
          <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
            Bandeja filtrada · M29 Client Messaging
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          onClick={() => setComposerOpen(true)}
        >
          <Plus size={14} className="mr-1" />
          Nuevo mensaje
        </Button>
      </div>

      <AdminInboxList
        key={refreshKey}
        clientIdFilter={clientId}
        onSelectThread={(tid) => setActiveThreadId(tid)}
      />

      <Sheet
        open={activeThreadId !== null}
        onOpenChange={(o) => {
          if (!o) {
            setActiveThreadId(null);
            bumpRefresh();
          }
        }}
      >
        <SheetContent
          side="right"
          className="flex w-full flex-col gap-0 p-0 sm:max-w-2xl"
        >
          <SheetHeader className="border-b border-fulkro-ink-200 p-4">
            <SheetTitle>Conversación</SheetTitle>
          </SheetHeader>
          {activeThreadId && (
            <div className="flex-1 overflow-hidden p-4">
              <AdminMessageThread
                threadId={activeThreadId}
                onChanged={bumpRefresh}
              />
            </div>
          )}
        </SheetContent>
      </Sheet>

      <Dialog open={composerOpen} onOpenChange={setComposerOpen}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Nuevo mensaje al cliente</DialogTitle>
          </DialogHeader>
          <AdminMessageComposer
            mode="new"
            presetClientId={clientId}
            onSent={() => {
              setComposerOpen(false);
              bumpRefresh();
            }}
            onCancel={() => setComposerOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}
