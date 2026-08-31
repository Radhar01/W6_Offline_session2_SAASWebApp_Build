import { motion } from "framer-motion";
import { forwardRef } from "react";
import type { ComponentPropsWithoutRef } from "react";

import { cn } from "@/lib/utils";

type InputPropsWithoutMotionConflicts = Omit<
  ComponentPropsWithoutRef<"input">,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart" | "onAnimationEnd"
>;

interface AnimatedInputProps extends InputPropsWithoutMotionConflicts {
  label?: string;
  error?: string;
}

/** Text input with a focus-scale animation and inline validation message. */
export const AnimatedInput = forwardRef<HTMLInputElement, AnimatedInputProps>(
  ({ label, error, className, id, ...props }, ref) => {
    const inputId = id ?? props.name;

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-foreground">
            {label}
          </label>
        )}
        <motion.input
          ref={ref}
          id={inputId}
          whileFocus={{ scale: 1.01 }}
          transition={{ duration: 0.15 }}
          className={cn(
            "w-full rounded-xl border-2 border-input bg-background px-4 py-3 text-foreground outline-none transition-colors focus:border-ring",
            error && "border-destructive focus:border-destructive",
            className,
          )}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-destructive">{error}</p>}
      </div>
    );
  },
);

AnimatedInput.displayName = "AnimatedInput";
