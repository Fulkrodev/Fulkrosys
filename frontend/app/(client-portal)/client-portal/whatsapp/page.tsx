"use client";

/**
 * /client-portal/whatsapp · MB-8 atom 8.3 Q7.C.
 *
 * 3 estados:
 *  - opt-in: WhatsAppOptInCard
 *  - awaiting OTP: WhatsAppOTPVerifyCard
 *  - active: WhatsAppThreadView con history bidirectional
 */
import { Download, Loader2, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { WhatsAppOptInCard } from "@/components/client-portal/whatsapp/WhatsAppOptInCard";
import { WhatsAppOTPVerifyCard } from "@/components/client-portal/whatsapp/WhatsAppOTPVerifyCard";
import { WhatsAppThreadView } from "@/components/client-portal/whatsapp/WhatsAppThreadView";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TooltipENS } from "@/components/ui/tooltip-ens";
import { useInboundWhatsAppSSE } from "@/hooks/useInboundWhatsAppSSE";
import {
  type WhatsAppMessage,
  type WhatsAppStatus,
  exportRgpd,
  fetchStatus,
  fetchThread,
  fetchThreadMessages,
} from "@/lib/api/whatsapp";


export default function ClientWhatsAppPage() {
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const [messages, setMessages] = useState<WhatsAppMessage[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingPhone, setPendingPhone] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const s = await fetchStatus();
      setStatus(s);
      if (s.opt_in_active) {
        try {
          const tr = await fetchThread();
          setThreadId(tr.thread?.id ?? null);
          const m = await fetchThreadMessages();
          setMessages(m.messages);
        } catch {
          setMessages([]);
        }
      }
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  // SSE realtime inbound · Sprint Polish 2.D (extracted to useInboundWhatsAppSSE).
  const { latestMessage } = useInboundWhatsAppSSE({
    threadId,
    mode: "client",
  });
  useEffect(() => {
    if (!latestMessage) return;
    setMessages((prev) => {
      if (prev.some((p) => p.id === latestMessage.id)) return prev;
      return [...prev, latestMessage];
    });
  }, [latestMessage]);

  const onExport = async () => {
    setExporting(true);
    try {
      const payload = await exportRgpd();
      const blob = new Blob(
        [JSON.stringify(payload, null, 2)], { type: "application/json" },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `whatsapp_export_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="grid place-items-center py-20 text-[color:var(--fulkro-muted)]">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6 md:px-6 md:py-10">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
          WhatsApp · FULKRO
        </h1>
        <p className="text-base text-[color:var(--fulkro-body)]">
          Notificaciones críticas y mensajes 1:1 con Marcos vía WhatsApp.
        </p>
      </header>

      {/* State machine: opt-in → otp → active thread */}
      {!status?.whatsapp_number && pendingPhone === null && (
        <WhatsAppOptInCard onOtpSent={(p) => setPendingPhone(p)} />
      )}

      {status?.whatsapp_number && !status.opt_in_active && (
        <WhatsAppOTPVerifyCard
          phoneE164={pendingPhone ?? status.whatsapp_number}
          onVerified={() => {
            setPendingPhone(null);
            void refresh();
          }}
        />
      )}

      {status?.opt_in_active && (
        <>
          <Card data-testid="whatsapp-active-status">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <ShieldCheck className="h-5 w-5 text-emerald-600" />
                WhatsApp activo · {status.whatsapp_number}
              </CardTitle>
              <Button
                variant="outline"
                size="sm"
                onClick={onExport}
                disabled={exporting}
              >
                {exporting && <Loader2 className="h-4 w-4 animate-spin" />}
                <Download className="h-4 w-4" /> Exportar (RGPD art.15)
              </Button>
            </CardHeader>
            <CardContent className="border-t border-fulkro-surface-glass-border p-0">
              <WhatsAppThreadView messages={messages} />
            </CardContent>
          </Card>

          <p className="text-xs text-[color:var(--fulkro-muted)]">
            Solo Marcos puede responder en este hilo. Conversaciones
            protegidas <TooltipENS term="RGPD" text="Reglamento General de Protección de Datos · normativa europea de privacidad obligatoria si tratas datos personales en la UE." /> · retention 7 años cumplimiento <TooltipENS term="ENS" />.
          </p>
        </>
      )}
    </main>
  );
}
