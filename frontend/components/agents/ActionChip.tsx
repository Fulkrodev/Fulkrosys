"use client";

import {
  FileText,
  Link as LinkIcon,
  Navigation,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import type { SuggestedAction } from "@/lib/sprint4-types";

const ICONS: Record<SuggestedAction["kind"], LucideIcon> = {
  invoke_agent: Sparkles,
  open_magic_link: LinkIcon,
  generate_doc: FileText,
  navigate: Navigation,
};

export function ActionChip({ action }: { action: SuggestedAction }) {
  const Icon = ICONS[action.kind];
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() =>
        toast.success(
          `${action.label} (acción de Agente 14 — wiring con backend real en siguiente sprint)`,
        )
      }
    >
      <Icon size={12} />
      {action.label}
    </Button>
  );
}
