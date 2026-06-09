"use client";

/**
 * ReadinessSection · cliente VE checklist 4-5 items pre-firma conformidad.
 *
 * SAN-E v3.MB-5.6.D · per item: ✅/❌ + detail + link al portal si missing.
 * ALTA tier adds 5th item políticas firmadas (8 mínimo).
 */
import { AlertCircle, CheckCircle2, XCircle } from "lucide-react";
import Link from "next/link";

import type {
  ConformityReadinessView,
  ReadinessItem,
} from "@/lib/api/conformidad";


interface Props {
  readiness: ConformityReadinessView;
}


const ITEM_LINKS: Record<string, string> = {
  DdA: "/client-portal/dda",
  MAGERIT: "/client-portal/magerit",
  Pentest: "/client-portal/pentest-authorization",
};


function getRelatedLink(label: string): string | null {
  for (const [keyword, href] of Object.entries(ITEM_LINKS)) {
    if (label.includes(keyword)) return href;
  }
  return null;
}


function ReadinessItemRow({ item }: { item: ReadinessItem }) {
  const link = !item.ready ? getRelatedLink(item.label) : null;

  return (
    <li className="flex items-start gap-3 rounded-md border bg-background px-3 py-2">
      {item.ready ? (
        <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-fulkro-success" />
      ) : (
        <XCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-fulkro-danger" />
      )}
      <div className="min-w-0 flex-1">
        <p
          className={`text-sm font-medium ${
            item.ready ? "text-[color:var(--fulkro-title)]" : "text-fulkro-danger"
          }`}
        >
          {item.label}
        </p>
        {item.detail && (
          <p className="mt-1 text-xs text-[color:var(--fulkro-muted)]">
            {item.detail}
          </p>
        )}
        {link && (
          <Link
            href={link}
            className="mt-1 inline-block text-xs font-medium text-fulkro-primary-700 hover:underline"
          >
            Ir al portal →
          </Link>
        )}
      </div>
    </li>
  );
}


export function ReadinessSection({ readiness }: Props) {
  return (
    <section className="rounded-lg border bg-card p-5 shadow-sm">
      <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-[color:var(--fulkro-title)]">
        <CheckCircle2 className="h-5 w-5 text-fulkro-primary-700" />
        Estado de preparación pre-firma
      </h2>

      <p className="mb-4 text-sm text-[color:var(--fulkro-muted)]">
        Para firmar la conformidad ENS necesitas tener completos los siguientes
        pasos previos. Si algo está pendiente, te llevamos directamente al
        portal correspondiente.
      </p>

      <ul className="space-y-2">
        {readiness.items.map((item) => (
          <ReadinessItemRow key={item.label} item={item} />
        ))}
      </ul>

      {readiness.blockers.length > 0 && (
        <div className="mt-4 rounded-md border border-fulkro-danger/30 bg-fulkro-danger/10 px-3 py-3">
          <p className="flex items-center gap-2 text-sm font-semibold text-fulkro-danger">
            <AlertCircle className="h-4 w-4" />
            Bloqueos para firmar ({readiness.blockers.length})
          </p>
          <ul className="mt-2 space-y-1">
            {readiness.blockers.map((b, i) => (
              <li
                key={`blocker-${i}`}
                className="text-sm text-[color:var(--fulkro-muted)]"
              >
                <span className="text-fulkro-danger">·</span> {b}
              </li>
            ))}
          </ul>
        </div>
      )}

      {readiness.ready_for_conformity_sign && (
        <div className="mt-4 rounded-md border border-fulkro-success/30 bg-fulkro-success/10 px-3 py-3 text-sm font-medium text-fulkro-success">
          ✓ Todos los pasos previos están completos · puedes firmar la
          conformidad ENS abajo.
        </div>
      )}
    </section>
  );
}
