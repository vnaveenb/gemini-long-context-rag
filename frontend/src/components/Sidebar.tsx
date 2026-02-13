"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ApiKeyDropdown } from "@/components/ApiKeyDropdown";

const NAV = [
  { href: "/", label: "Dashboard", icon: "📊" },
  { href: "/upload", label: "Upload & Analyse", icon: "📤" },
  { href: "/reports", label: "Reports", icon: "📋" },
  { href: "/audit", label: "Audit Log", icon: "🔍" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:w-64 flex-col bg-[var(--sidebar)] text-[var(--sidebar-fg)]">
      {/* Logo / Brand */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
        <span className="text-2xl">📋</span>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-white">LRA</h1>
          <p className="text-xs text-[var(--muted)]">Compliance Intelligence</p>
        </div>
      </div>

      {/* Nav Links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-[var(--accent)] text-white"
                  : "text-[var(--sidebar-fg)] hover:bg-white/10"
              }`}
            >
              <span className="text-lg">{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>

      {/* BYOK API Key */}
      <div className="border-t border-white/10 pt-3">
        <ApiKeyDropdown />
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-white/10 text-xs text-[var(--muted)]">
        LRA v0.2.0
      </div>
    </aside>
  );
}
