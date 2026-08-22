"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { BarChart3, Inbox, LayoutGrid, Megaphone, UserRound } from "lucide-react";

import { fadeSlideUp } from "@/lib/motion";
import { CurrentUser } from "@/lib/types";
import { HOME_FOR_ROLE } from "@/lib/session";
import ProfileDropdown from "./profile-dropdown";

/**
 * Navigation for each role.
 *
 * Previously the navbar carried a single "Dashboard" link, so Profile and
 * Analytics were only reachable through the avatar dropdown. The theme toggle
 * was also here but the app is dark-only in practice, so it has been removed
 * rather than left offering a half-broken light mode.
 */
const NAV: Record<CurrentUser["role"], { href: string; label: string; icon: typeof LayoutGrid }[]> = {
  INFLUENCER: [
    { href: "/dashboard/influencer", label: "Studio", icon: LayoutGrid },
    { href: "/dashboard/analytics/influencer", label: "Analytics", icon: BarChart3 },
    { href: "/dashboard/profile", label: "Profile", icon: UserRound },
  ],
  BRAND: [
    { href: "/dashboard/brand", label: "Studio", icon: LayoutGrid },
    { href: "/dashboard/brand/campaigns", label: "Campaigns", icon: Megaphone },
    { href: "/dashboard/brand/interested", label: "Responses", icon: Inbox },
    { href: "/dashboard/analytics/brand", label: "Dashboard", icon: BarChart3 },
    { href: "/dashboard/brand-profile", label: "Profile", icon: UserRound },
  ],
  ADMIN: [
    { href: "/dashboard/admin", label: "Overview", icon: LayoutGrid },
    { href: "/dashboard/admin/users", label: "Users", icon: UserRound },
  ],
};

export default function DashboardNavbar({ user }: { user: CurrentUser }) {
  const router = useRouter();
  const pathname = usePathname();
  const items = NAV[user.role] ?? [];

  // The most specific matching link wins. A plain `startsWith` lit up both
  // "Studio" (/dashboard/brand) and "Campaigns" (/dashboard/brand/campaigns) at
  // once, because the studio's href is a prefix of every page under it.
  const activeHref = items
    .filter((i) => pathname === i.href || pathname.startsWith(i.href + "/"))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <motion.header
      variants={fadeSlideUp}
      initial="hidden"
      animate="visible"
      // Matches the shell surface. This used to be `bg-background` — white by
      // default — bolted onto black pages.
      className="sticky top-0 z-50 border-b border-white/10 bg-[#06070C]/85 backdrop-blur-md"
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <button
          onClick={() => router.push(HOME_FOR_ROLE[user.role])}
          className="rounded-md text-xl font-semibold tracking-tight text-white transition hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
        >
          Crewaa
        </button>

        <nav className="flex items-center gap-1" aria-label="Main">
          {items.map(({ href, label, icon: Icon }) => {
            const active = href === activeHref;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40 ${
                  active
                    ? "bg-white/10 text-white"
                    : "text-gray-400 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}

          <div className="ml-2">
            <ProfileDropdown user={user} />
          </div>
        </nav>
      </div>
    </motion.header>
  );
}
