"use client";

/**
 * ClientMobileDrawer · CLUSTER 4 Phase 4C (Sesión 3B-2B.8).
 *
 * Mobile drawer cliente portal navigation · Sheet-based slide-in side="left".
 * Reuses ClientSidebar via onNavigate auto-close callback.
 *
 * Visible solo en breakpoints < lg (1024px) · `lg:hidden` trigger button.
 *
 * Filosofía cliente-mínimo:
 * - Cliente NAVEGA portal mobile · NO opera ENS técnico mobile
 * - WCAG 2.4.4 (button-name aria-label) · 2.5.5 (touch target size)
 * - R29 firmísimo aria-label Spanish friendly
 *
 * Focus management + escape key + click-outside close · provistos por Sheet
 * primitive (Radix UI Dialog) built-in.
 */
import { Menu } from "lucide-react";
import * as React from "react";

import { ClientSidebar } from "@/components/layout/ClientSidebar";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export function ClientMobileDrawer() {
  const [open, setOpen] = React.useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Abrir menú de navegación"
          className="lg:hidden text-white hover:bg-white/10"
        >
          <Menu size={22} strokeWidth={2.3} aria-hidden="true" />
        </Button>
      </SheetTrigger>
      <SheetContent
        side="left"
        className="w-72 p-0 border-r-0"
        aria-label="Menú principal"
      >
        <SheetHeader className="sr-only">
          <SheetTitle>Menú principal del portal</SheetTitle>
        </SheetHeader>
        <ClientSidebar
          className="flex w-full h-full"
          onNavigate={() => setOpen(false)}
        />
      </SheetContent>
    </Sheet>
  );
}
