import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { Activity, Database, FileText, ScrollText, Settings, Users, Briefcase } from "lucide-react";

const navItems = [
  { to: "/", labelKey: "nav.dashboard", icon: Activity },
  { to: "/tenants", labelKey: "nav.tenants", icon: Users },
  { to: "/jobs", labelKey: "nav.jobs", icon: Briefcase },
  { to: "/audit", labelKey: "nav.audit", icon: ScrollText },
  { to: "/settings", labelKey: "nav.settings", icon: Settings },
];

export default function Layout() {
  const { t } = useTranslation();
  const location = useLocation();

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-muted/40 border-r border-border flex flex-col">
        <div className="p-6 border-b border-border">
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <Database className="w-5 h-5 text-primary" />
            {t("app.name")}
          </h1>
          <p className="text-xs text-muted-foreground mt-1">{t("app.tagline")}</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              <item.icon className="w-4 h-4" />
              {t(item.labelKey)}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-border">
          <LanguageSwitcher />
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
