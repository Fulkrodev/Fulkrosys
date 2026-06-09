/**
 * /admin/messages — Bandeja admin cross-cliente (sub-bloque 6.B.2).
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

import { AdminInboxList } from "./_components/AdminInboxList";
import { AdminMessageComposer } from "./_components/AdminMessageComposer";
import { AdminMessageThread } from "./_components/AdminMessageThread";

export default function AdminMessagesPage() {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [composerOpen, setComposerOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  function bumpRefresh() {
    setRefreshKey((k) => k + 1);
  }

  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold text-[color:var(--fulkro-title)] tracking-tight">
            Mensajes
          </h1>
          <p className="text-base font-medium text-[color:var(--fulkro-muted)]">
            Bandeja cross-cliente · M29 Client Messaging
          </p>
        </div>
        <Button
          type="button"
          onClick={() => setComposerOpen(true)}
          size="sm"
        >
          <Plus size={14} className="mr-1" />
          Nuevo mensaje
        </Button>
      </div>

      <div className="mt-6">
        <AdminInboxList
          key={refreshKey}
          onSelectThread={(tid) => setActiveThreadId(tid)}
        />
      </div>

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
            <DialogTitle>Nuevo mensaje</DialogTitle>
          </DialogHeader>
          <AdminMessageComposer
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
