import { motion } from "framer-motion";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { cn } from "@/lib/utils";

type ButtonPropsWithoutMotionConflicts = Omit<
  ComponentPropsWithoutRef<"button">,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart" | "onAnimationEnd"
>;

interface GradientButtonProps extends ButtonPropsWithoutMotionConflicts {
  children: ReactNode;
}

/** Primary call-to-action button with a gradient fill and hover/tap feedback. */
export function GradientButton({ children, className, disabled, ...props }: GradientButtonProps) {
  return (
    <motion.button
      whileHover={disabled ? undefined : { scale: 1.02, y: -2 }}
      whileTap={disabled ? undefined : { scale: 0.98 }}
      className={cn(
        "inline-flex items-center justify-center rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-500 px-6 py-3 font-semibold text-white shadow-glow transition-shadow duration-300 hover:shadow-glow-lg disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none",
        className,
      )}
      disabled={disabled}
      {...props}
    >
      {children}
    </motion.button>
  );
}
