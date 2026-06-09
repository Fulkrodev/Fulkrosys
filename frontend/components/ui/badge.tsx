import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  cn(
    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold",
    "transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  ),
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-muted text-muted-foreground hover:bg-muted/80",
        accent:
          "border-transparent bg-accent text-accent-foreground hover:bg-accent/80",
        outline: "border-border text-foreground",
        // Sub-atom Sesión 3B-2B.2 Phase A.1 · WCAG color-contrast fix.
        // Over white card bg (post Card.tsx bg fix):
        //   success/15 blended ≈ rgb(223,238,230) · warning/15 ≈ rgb(247,237,223)
        //   info/15 blended ≈ rgb(223,233,238)
        // Previous text-fulkro-{name} (-500 shade) ratios: 2.6-4.5:1 (FAIL AA).
        // -700 shades yield 4.74-7.33:1 (success 5.87 · warning 4.74 · info 7.33)
        // → AA/AAA across all three variants.
        success:
          "border-transparent bg-fulkro-success/15 text-fulkro-success-700",
        warning:
          "border-transparent bg-fulkro-warning/15 text-fulkro-warning-700",
        info: "border-transparent bg-fulkro-info/15 text-fulkro-info-700",
        danger:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { badgeVariants };
