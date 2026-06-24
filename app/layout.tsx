import type { Metadata } from "next";
import Link from "next/link";
import { BriefcaseBusiness, Building2, Database, Heart, LayoutDashboard, ListChecks, Search, Settings, Workflow } from "lucide-react";
import "./globals.css";

export const metadata: Metadata = {
  title: "JobScout AI",
  description: "Job-market intelligence portfolio application.",
};

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/jobs", label: "Job Search", icon: Search },
  { href: "/companies", label: "Companies", icon: Building2 },
  { href: "/scraping", label: "Scraping", icon: Workflow },
  { href: "/review", label: "Review Queue", icon: ListChecks },
  { href: "/saved", label: "Saved Jobs", icon: Heart },
  { href: "/applications", label: "Applications", icon: BriefcaseBusiness },
  { href: "/exports", label: "Exports", icon: Database },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-border bg-white">
            <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8 xl:flex-row xl:items-center xl:justify-between">
              <Link href="/" className="flex items-center gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-md bg-ink text-white">
                  <BriefcaseBusiness className="h-5 w-5" aria-hidden="true" />
                </span>
                <span>
                  <span className="block text-base font-semibold tracking-normal">JobScout AI</span>
                  <span className="block text-xs text-muted">Market intelligence</span>
                </span>
              </Link>
              <nav className="flex flex-wrap items-center gap-1">
                {navItems.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted hover:bg-surface hover:text-ink"
                  >
                    <item.icon className="h-4 w-4" aria-hidden="true" />
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
