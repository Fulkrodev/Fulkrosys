"use client";

/**
 * ClientUnblockedBanner · real-time banner cuando step_unblocked SSE event (1.D.G.E v3.11).
 *
 * Format R29: "✨ Marcos terminó · te toca a ti: {step_title}"
 * Click → navigate cta_url cliente
 * Auto-dismiss after view (manual dismiss button también).
 *
 * Sostiene R29 friendly · NO coercitive · congrats tone.
 */
import * as React from "react";
import Link from "next/link";
import { ArrowRight, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

import { useClientProjectEvents } from "@/hooks/useClientProjectEvents";

interface UnblockedNotification {
  templateId: string;
  stepTitle: string;
  ctaUrl?: string;
  timestamp: string;
}

export interface ClientUnblockedBannerProps {
  projectId: string | null;
  ctaUrlResolver?: (templateId: string) => string | undefined;
}

export function ClientUnblockedBanner({
  projectId,
  ctaUrlResolver,
}: ClientUnblockedBannerProps) {
  const [notifications, setNotifications] = React.useState<
    UnblockedNotification[]
  >([]);

  useClientProjectEvents(projectId, {
    enabled: Boolean(projectId),
    onStepUnblocked: (event) => {
      const templateId = event.data.template_id ?? "";
      const stepTitle = event.data.step_title ?? "Hay algo nuevo para ti";
      const ctaUrl = ctaUrlResolver?.(templateId);
      setNotifications((prev) => {
        if (prev.some((n) => n.templateId === templateId)) return prev;
        return [
          ...prev,
          {
            templateId,
            stepTitle,
            ctaUrl,
            timestamp: event.data._timestamp ?? new Date().toISOString(),
          },
        ];
      });
    },
    invalidateQueries: [
      ["client-tasks"],
      ["client-workflow-guide", projectId ?? ""],
    ],
  });

  if (notifications.length === 0) return null;

  return (
    <div
      className="space-y-2"
      data-testid="client-unblocked-banner-container"
    >
      {notifications.map((notification) => (
        <Card
          key={notification.templateId}
          className="border-l-4 border-l-amber-500 bg-amber-50/60 dark:bg-amber-950/30"
          data-testid={`unblocked-banner-${notification.templateId}`}
        >
          <CardContent className="py-3 px-4 flex items-start gap-3">
            <Sparkles className="size-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium leading-snug">
                Marcos terminó · te toca a ti
              </p>
              <p className="text-sm text-foreground/75 mt-0.5">
                {notification.stepTitle}
              </p>
            </div>
            {notification.ctaUrl && (
              <Link
                href={notification.ctaUrl}
                className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition hover:opacity-90"
              >
                Ver
                <ArrowRight className="size-3" />
              </Link>
            )}
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() =>
                setNotifications((prev) =>
                  prev.filter(
                    (n) => n.templateId !== notification.templateId,
                  ),
                )
              }
              aria-label="Cerrar notificación"
              data-testid={`unblocked-dismiss-${notification.templateId}`}
            >
              <X className="size-4" />
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
