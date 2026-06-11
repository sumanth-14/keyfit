"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Wand2, User, Settings } from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/tailor", label: "Tailor Resume", Icon: Wand2 },
  { href: "/profile", label: "Profile", Icon: User },
  { href: "/settings", label: "Settings", Icon: Settings },
] as const;

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-56 shrink-0 flex-col border-r border-line bg-paper-raised">
      {/* Wordmark */}
      <div className="flex h-14 items-center px-5 border-b border-line">
        <span className="font-serif text-lg font-semibold tracking-tight text-ink">
          Keyfit
        </span>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-0.5 p-2 flex-1">
        {NAV_ITEMS.map(({ href, label, Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={[
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent-soft text-accent"
                  : "text-ink-soft hover:bg-paper hover:text-ink",
              ].join(" ")}
            >
              <Icon size={16} strokeWidth={1.75} />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
