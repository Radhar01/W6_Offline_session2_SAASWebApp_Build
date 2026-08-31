import { motion } from "framer-motion";
import { Clapperboard, LayoutDashboard, Library, Upload } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Upload;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/upload", label: "Upload", icon: Upload },
  { to: "/library", label: "Library", icon: Library },
];

/** Top-level shell: a nav bar plus the routed page content via <Outlet />. */
export function AppLayout() {
  return (
    <div className="relative min-h-screen bg-background text-foreground">
      <div className="bg-mesh pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />

      <header className="sticky top-0 z-10 border-b border-border/60 bg-background/70 backdrop-blur-xl">
        <nav className="container flex h-16 items-center justify-between">
          <NavLink to="/dashboard" className="flex items-center gap-2.5 font-bold tracking-tight">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-500 shadow-glow">
              <Clapperboard className="h-[18px] w-[18px] text-white" aria-hidden="true" />
            </span>
            <span className="text-lg">ClipCreator</span>
          </NavLink>

          <ul className="flex items-center gap-1 rounded-full border border-border/60 bg-card/50 p-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  className="relative flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors"
                >
                  {({ isActive }) => (
                    <>
                      {isActive && (
                        <motion.span
                          layoutId="active-nav-pill"
                          className="absolute inset-0 rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-500 shadow-glow"
                          transition={{ type: "spring", stiffness: 400, damping: 32 }}
                        />
                      )}
                      <motion.span
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.97 }}
                        className={cn(
                          "relative z-10 flex items-center gap-2",
                          isActive ? "text-white" : "text-muted-foreground hover:text-foreground",
                        )}
                      >
                        <Icon className="h-4 w-4" aria-hidden="true" />
                        <span className={isActive ? "font-semibold" : undefined}>{label}</span>
                      </motion.span>
                    </>
                  )}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main className="container py-8">
        <Outlet />
      </main>
    </div>
  );
}
