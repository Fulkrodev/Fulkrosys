import { Clock3 } from "lucide-react";

import type { MagicLinkContext } from "@/lib/sprint4-types";

export function MagicLinkMeta({ context }: { context: MagicLinkContext }) {
  const remaining = Math.max(
    0,
    Math.round((new Date(context.expires_at).getTime() - Date.now()) / 3_600_000),
  );
  return (
    <div className="mb-5 flex items-center justify-between gap-4 rounded-md border border-fulkro-ink-300/60 bg-white px-4 py-3 text-xs">
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-fulkro-ink-500">
          Cliente
        </p>
        <p className="text-sm font-medium text-fulkro-ink-700">
          {context.client_name}
        </p>
        <p className="text-[11px] text-fulkro-ink-500">
          {context.project_name}
        </p>
      </div>
      <span className="inline-flex items-center gap-1 rounded-full border border-fulkro-warning/40 bg-fulkro-warning/5 px-2 py-0.5 text-[11px] font-medium text-fulkro-warning">
        <Clock3 size={12} /> caduca en {remaining} h
      </span>
    </div>
  );
}
