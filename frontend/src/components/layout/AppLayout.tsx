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
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
        <nav className="container flex h-16 items-center justify-between">
          <NavLink to="/dashboard" className="flex items-center gap-2 font-semibold">
            <Clapperboard className="h-5 w-5 text-violet-600" aria-hidden="true" />
            <span>ClipCreator</span>
          </NavLink>

          <ul className="flex items-center gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-secondary text-secondary-foreground"
                        : "text-muted-foreground hover:text-foreground",
                    )
                  }
                >
                  {({ isActive }) => (
                    <motion.span
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.97 }}
                      className="flex items-center gap-2"
                    >
                      <Icon className="h-4 w-4" aria-hidden="true" />
                      <span className={isActive ? "font-semibold" : undefined}>{label}</span>
                    </motion.span>
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
