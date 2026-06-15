/**
 * /client-portal/inbox — Bandeja entrada cliente (sub-bloque 6.B.1).
 *
 * Layout:
 *   - Layout chrome (Sidebar + Header) viene del layout client-portal
 *   - Header h1 + button "Nuevo mensaje" (Dialog MessageComposer mode=new)
 *   - ClientInboxList (default view) o Sheet ClientMessageThread on row click
 */
"use client";

import { Plus } from "lucide-react";
import { useState } from "react";


import { NotificationsInboxPanel } from "@/components/client-portal/NotificationsInboxPanel";
import { PageContainer } from "@/components/layout/PageContainer";
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

import { ClientInboxList } from "./_components/ClientInboxList";
import { ClientMessageThread } from "./_components/ClientMessageThread";
import { MessageComposer } from "./_components/MessageComposer";

export default function ClientPortalInboxPage() {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [composerOpen, setComposerOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  function bumpRefresh() {
    setRefreshKey((k) => k + 1);
  }

  return (
    <>
      <PageContainer variant="reading">
        <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1>Bandeja de entrada</h1>
          <Button
            type="button"
            onClick={() => setComposerOpen(true)}
            size="md"
            className="text-base"
          >
            <Plus size={18} strokeWidth={2.4} className="mr-1" />
            Nuevo mensaje
          </Button>
        </div>

        <NotificationsInboxPanel />

        <div className="space-y-3">
          <h2 className="text-base font-semibold text-fulkro-primary-700">
            Mensajes
          </h2>
          <ClientInboxList
            key={refreshKey}
            onSelectThread={(tid) => setActiveThreadId(tid)}
          />
        </div>
        </div>
      </PageContainer>

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
              <ClientMessageThread
                threadId={activeThreadId}
                onSent={bumpRefresh}
              />
            </div>
          )}
        </SheetContent>
      </Sheet>

      <Dialog
        open={composerOpen}
        onOpenChange={setComposerOpen}
      >
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Nuevo mensaje</DialogTitle>
          </DialogHeader>
          <MessageComposer
            mode="new"
            onSent={() => {
              setComposerOpen(false);
              bumpRefresh();
            }}
            onCancel={() => setComposerOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </>
  );
}
