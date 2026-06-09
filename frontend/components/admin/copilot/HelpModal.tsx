"use client";

/**
 * HelpModal · contextual FAQ + escalation contact.
 *
 * Sub-atom Sesión 3A Phase B.3 · per-phase FAQ accessible from any admin
 * page via help icon. Complement to CopilotoDock (LLM chat) + CopilotGuidedFlow
 * (structured per-page guidance).
 *
 * Use case: admin needs a quick reference of common questions about the
 * current phase WITHOUT scrolling through chat history · also "Contactar a
 * Marcos" escalation link prominent (mailto + Slack placeholder).
 *
 * R30 admin tutor primer principios sostener.
 */
import { HelpCircle, Mail, MessageSquareWarning, X } from "lucide-react";
import { useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export interface FaqEntry {
  /** Question heading visible. */
  question: string;
  /** Answer body · supports inline markup via React node. */
  answer: React.ReactNode;
}

export interface HelpModalProps {
  /** Trigger button label (defaults to "Ayuda"). */
  triggerLabel?: string;
  /** Phase identifier · used for testid scoping. */
  phaseId: string;
  /** Phase title (e.g. "Categorización · Ayuda"). */
  title: string;
  /** Optional short description below title. */
  description?: string;
  /** FAQ entries · ordered by relevance. */
  faqs: FaqEntry[];
  /** Marcos contact email (defaults to placeholder · should be overridden). */
  contactEmail?: string;
  /** Optional Slack channel URL (placeholder · scope-out post-piloto). */
  slackUrl?: string;
  /** Optional Future video tutorial URL placeholder. */
  videoTutorialUrl?: string;
  /** Custom trigger className (e.g. icon-only · ghost). */
  triggerClassName?: string;
}

export function HelpModal({
  triggerLabel = "Ayuda",
  phaseId,
  title,
  description,
  faqs,
  contactEmail = "marcosmata@fulkro.es",
  slackUrl,
  videoTutorialUrl,
  triggerClassName,
}: HelpModalProps) {
  const [open, setOpen] = useState(false);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          type="button"
          aria-label={`Abrir ayuda contextual: ${title}`}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border border-fulkro-info/30 bg-fulkro-info/5 px-2.5 py-1 text-xs font-medium text-fulkro-info hover:bg-fulkro-info/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-info focus-visible:ring-offset-2",
            triggerClassName,
          )}
          data-testid={`help-modal-trigger-${phaseId}`}
        >
          <HelpCircle className="h-3.5 w-3.5" />
          {triggerLabel}
        </button>
      </DialogTrigger>

      <DialogContent
        className="max-w-2xl"
        data-testid={`help-modal-content-${phaseId}`}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-fulkro-info" />
            {title}
          </DialogTitle>
          {description ? (
            <DialogDescription>{description}</DialogDescription>
          ) : null}
        </DialogHeader>

        <div className="max-h-[60vh] overflow-y-auto pr-2">
          {faqs.length > 0 ? (
            <ul className="space-y-4">
              {faqs.map((faq, i) => (
                <li
                  key={i}
                  className="border-b border-fulkro-ink-300/40 pb-3 last:border-0"
                  data-testid={`help-modal-faq-${phaseId}-${i}`}
                >
                  <h4 className="mb-1.5 text-sm font-bold text-fulkro-primary-700">
                    {faq.question}
                  </h4>
                  <div className="text-sm leading-relaxed text-fulkro-ink-700">
                    {faq.answer}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-fulkro-ink-500">
              Aún no hay FAQ para esta fase. Pregunta al copiloto o contacta
              con Marcos.
            </p>
          )}
        </div>

        {/* Escalation footer */}
        <footer className="mt-4 flex flex-wrap items-center gap-3 border-t border-fulkro-ink-300/40 pt-4">
          <p className="flex-1 min-w-[200px] text-xs text-fulkro-ink-500">
            ¿No encuentras lo que buscas?
          </p>
          <a
            href={`mailto:${contactEmail}?subject=Consulta%20FULKRO%20%C2%B7%20${encodeURIComponent(title)}`}
            className="inline-flex items-center gap-1.5 rounded-md border border-fulkro-info/30 bg-fulkro-info/5 px-3 py-1.5 text-xs font-medium text-fulkro-info hover:bg-fulkro-info/10"
            data-testid={`help-modal-contact-email-${phaseId}`}
          >
            <Mail className="h-3.5 w-3.5" />
            Contactar a Marcos
          </a>
          {slackUrl ? (
            <a
              href={slackUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border border-fulkro-info/30 bg-fulkro-info/5 px-3 py-1.5 text-xs font-medium text-fulkro-info hover:bg-fulkro-info/10"
              data-testid={`help-modal-slack-${phaseId}`}
            >
              <MessageSquareWarning className="h-3.5 w-3.5" />
              Slack
            </a>
          ) : null}
          {videoTutorialUrl ? (
            <a
              href={videoTutorialUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs underline text-fulkro-info hover:text-fulkro-info/80"
              data-testid={`help-modal-video-${phaseId}`}
            >
              Ver tutorial (próximamente)
            </a>
          ) : null}
        </footer>
      </DialogContent>
    </Dialog>
  );
}
