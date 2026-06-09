"use client";

import { Command } from "cmdk";
import {
  Briefcase,
  FolderOpen,
  Home,
  LifeBuoy,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  TrendingUp,
  Video,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";

import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface PaletteAction {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
  run: () => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();

  React.useEffect(() => {
    function handler(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
      if (event.key === "Escape" && open) {
        event.preventDefault();
        onOpenChange(false);
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onOpenChange]);

  const navigate = (href: string) => {
    router.push(href);
    onOpenChange(false);
  };

  const actions: PaletteAction[] = [
    {
      id: "goto-dashboard",
      label: "Ir al dashboard",
      group: "Navegación",
      icon: Home,
      run: () => navigate(ROUTES.dashboard),
    },
    {
      id: "goto-pipeline",
      label: "Ir al pipeline comercial",
      group: "Navegación",
      icon: TrendingUp,
      run: () => navigate(ROUTES.pipeline),
    },
    {
      id: "goto-projects",
      label: "Ir a proyectos",
      group: "Navegación",
      icon: FolderOpen,
      run: () => navigate(ROUTES.projects),
    },
    {
      id: "goto-retainer",
      label: "Ir a retainer",
      group: "Navegación",
      icon: Briefcase,
      run: () => navigate(ROUTES.retainer),
    },
    {
      id: "goto-copilot",
      label: "Abrir copiloto",
      group: "Navegación",
      icon: LifeBuoy,
      run: () => navigate(ROUTES.copilot),
    },
    {
      id: "goto-operations",
      label: "Consola de operaciones",
      group: "Navegación",
      icon: ShieldCheck,
      run: () => navigate(ROUTES.operations),
    },
    {
      id: "goto-settings",
      label: "Ajustes",
      group: "Navegación",
      icon: Settings2,
      run: () => navigate(ROUTES.settings),
    },
    {
      id: "new-lead",
      label: "Nuevo lead",
      group: "Acciones",
      icon: Plus,
      run: () => navigate(`${ROUTES.pipeline}?new=1`),
    },
    {
      id: "new-meeting",
      label: "Nueva reunión exploratoria",
      group: "Acciones",
      icon: Video,
      run: () => navigate(`${ROUTES.meetings}/new`),
    },
  ];

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-fulkro-ink-900/40 p-4 pt-[10vh] animate-fade-in">
      <div
        role="dialog"
        aria-label="Buscar o ejecutar"
        className={cn(
          "w-full max-w-lg overflow-hidden rounded-lg border border-fulkro-ink-300/60 bg-white shadow-ink",
        )}
      >
        <Command label="Ir a…">
          <div className="flex items-center gap-3 border-b border-fulkro-ink-300/60 px-4">
            <Search size={16} className="text-fulkro-ink-500" />
            <Command.Input
              autoFocus
              placeholder="Ir a… o acción rápida"
              className="h-12 flex-1 bg-transparent py-3 text-sm outline-none placeholder:text-fulkro-ink-500"
            />
            <kbd className="rounded bg-fulkro-ink-100 px-2 py-0.5 font-mono text-[10px] text-fulkro-ink-500">
              Esc
            </kbd>
          </div>
          <Command.List className="max-h-[60vh] overflow-y-auto p-2">
            <Command.Empty className="px-4 py-6 text-sm text-fulkro-ink-500">
              Sin resultados.
            </Command.Empty>
            {groupActions(actions).map(({ group, items }) => (
              <Command.Group
                heading={group}
                key={group}
                className="pb-2 text-[11px] font-semibold uppercase tracking-wider text-fulkro-ink-500"
              >
                {items.map((action) => {
                  const Icon = action.icon;
                  return (
                    <Command.Item
                      key={action.id}
                      value={`${action.group} ${action.label}`}
                      onSelect={action.run}
                      className="flex cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-sm text-fulkro-ink-700 data-[selected=true]:bg-fulkro-ink-100"
                    >
                      <Icon size={14} />
                      <span>{action.label}</span>
                    </Command.Item>
                  );
                })}
              </Command.Group>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}

function groupActions(actions: PaletteAction[]) {
  const map = new Map<string, PaletteAction[]>();
  actions.forEach((a) => {
    const bucket = map.get(a.group) ?? [];
    bucket.push(a);
    map.set(a.group, bucket);
  });
  return Array.from(map.entries()).map(([group, items]) => ({ group, items }));
}
