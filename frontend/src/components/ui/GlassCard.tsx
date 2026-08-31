import { motion } from "framer-motion";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

import { cn } from "@/lib/utils";

type DivPropsWithoutMotionConflicts = Omit<
  ComponentPropsWithoutRef<"div">,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart" | "onAnimationEnd"
>;

interface GlassCardProps extends DivPropsWithoutMotionConflicts {
  children: ReactNode;
}

/** A frosted-glass card with a subtle entrance animation and hover elevation. */
export function GlassCard({ children, className, ...props }: GlassCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01, y: -4 }}
      transition={{ duration: 0.2 }}
      className={cn(
        "rounded-2xl border border-border bg-card/60 p-6 text-card-foreground shadow-sm backdrop-blur-lg",
        className,
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
}
