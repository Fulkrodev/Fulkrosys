import * as React from "react";

import { cn } from "@/lib/utils";

export const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, style, ...props }, ref) => (
  <div
    ref={ref}
    style={{
      // Sub-atom Sesión 3B-2B.2 Phase A.1 · WCAG color-contrast fix.
      // Previous bg `rgba(108, 99, 255, 0.07)` (surface-glass) blended with
      // body bg-fulkro-ink-50 (#fafafa) → effective bg ~rgb(240,239,250).
      // text-fulkro-ink-500 (rgb 110,110,122) on this bg = 4.22:1 → fails
      // AA (needs ≥4.5). Same text on solid white = 4.75:1 → passes AA.
      // Glass visual was nearly invisible anyway (alpha 0.07 over near-white)
      // · solid white preserves card distinction via border + shadow.
      // backdrop-filter removed (no-op on opaque bg · saves GPU layer).
      backgroundColor: "#ffffff",
      borderColor: "var(--fulkro-surface-glass-border)",
      ...style,
    }}
    className={cn(
      "rounded-xl border text-card-foreground shadow-sm",
      className,
    )}
    {...props}
  />
));
Card.displayName = "Card";

export const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col gap-2 p-6", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-bold leading-tight tracking-tight text-[color:var(--fulkro-title)]",
      className,
    )}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-base font-medium text-[color:var(--fulkro-muted)]", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0 text-[15px] text-[color:var(--fulkro-body)]", className)} {...props} />
));
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";
