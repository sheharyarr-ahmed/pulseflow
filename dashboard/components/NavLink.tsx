"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  // Job detail pages belong to Overview (their breadcrumb points home).
  const active =
    href === "/"
      ? pathname === "/" || pathname.startsWith("/jobs")
      : pathname.startsWith(href);

  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`relative flex h-14 items-center text-sm transition-colors ${
        active
          ? "text-foreground after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:rounded-full after:bg-pulse"
          : "text-muted hover:text-foreground"
      }`}
    >
      {children}
    </Link>
  );
}
