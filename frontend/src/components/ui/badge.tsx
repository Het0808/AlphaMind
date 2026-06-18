import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/15 text-primary",
        secondary: "border-border bg-muted text-muted-foreground",
        bull: "border-transparent bg-[hsl(var(--bull)/0.15)] text-bull",
        bear: "border-transparent bg-[hsl(var(--bear)/0.15)] text-bear",
        warn: "border-transparent bg-[hsl(var(--warn)/0.15)] text-warn",
        info: "border-transparent bg-[hsl(var(--info)/0.15)] text-info",
        outline: "border-border text-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { badgeVariants };
