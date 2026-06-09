import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-all disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fulkro-primary-700/40 focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        // Primary · gradient morado guay (azul-índigo→violeta) para CTAs principales
        primary: "btn-action",
        // Secondary · glass-strong con texto morado oscuro · acción importante pero no principal
        secondary:
          "bg-[color:var(--fulkro-surface-glass-strong)] text-[color:var(--fulkro-title)] hover:bg-[color:var(--fulkro-surface-glass-border)] border border-[color:var(--fulkro-surface-glass-border)]",
        // Accent · morado vivo (mantiene compat con código antiguo)
        accent:
          "bg-fulkro-accent-500 text-white hover:bg-fulkro-accent-300 shadow-md",
        // Outline · tinte morado sutil · acción terciaria sobre superficies claras
        outline: "btn-outline-fulkro",
        // Ghost · sin fondo · acciones en chrome o links
        ghost:
          "text-[color:var(--fulkro-body)] hover:bg-[color:var(--fulkro-surface-glass-strong)] hover:text-[color:var(--fulkro-title)]",
        // Link · texto morado oscuro
        link: "text-[color:var(--fulkro-title)] underline-offset-4 hover:underline",
        // Danger · rojo
        danger:
          "bg-fulkro-danger text-white hover:bg-fulkro-danger/90 shadow-md",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { buttonVariants };
