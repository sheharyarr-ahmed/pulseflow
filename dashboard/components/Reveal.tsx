"use client";

import { useEffect, useRef } from "react";

// The only motion JS in the app: an IntersectionObserver that stamps
// data-shown once. Every actual animation lives in CSS (globals.css), and the
// hidden initial state is gated on html.js + prefers-reduced-motion, so no-JS
// and reduced-motion visitors always see content.
export default function Reveal({
  children,
  delay = 0,
  className,
  as: Tag = "div",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
  as?: "div" | "section" | "li";
}) {
  const ref = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.setAttribute("data-shown", "");
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          el.setAttribute("data-shown", "");
          io.disconnect();
        }
      },
      // Fire as soon as the element's top clears the bottom 10% of the
      // viewport — a fixed threshold would never trip on very tall elements.
      { rootMargin: "0px 0px -10% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <Tag
      // eslint-disable-next-line @typescript-eslint/no-explicit-any -- polymorphic ref
      ref={ref as any}
      data-reveal
      className={className}
      style={
        delay ? ({ "--reveal-delay": `${delay}ms` } as React.CSSProperties) : undefined
      }
    >
      {children}
    </Tag>
  );
}
