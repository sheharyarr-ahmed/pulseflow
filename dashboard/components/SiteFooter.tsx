export default function SiteFooter() {
  return (
    <footer className="footer-glow border-t border-edge">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-10 md:flex-row md:items-center md:justify-between md:px-10">
        <div className="flex items-center gap-2.5">
          {/* eslint-disable-next-line @next/next/no-img-element -- static brand SVG, no optimization needed */}
          <img
            src="/brand/mark-light.svg"
            alt=""
            className="size-4 dark:hidden"
          />
          {/* eslint-disable-next-line @next/next/no-img-element -- static brand SVG, no optimization needed */}
          <img
            src="/brand/mark-dark.svg"
            alt=""
            className="hidden size-4 dark:block"
          />
          <span className="text-sm text-muted">
            Code-first job-hunt automation that ships a daily heartbeat.
          </span>
        </div>
        <p className="font-mono text-[11px] text-muted">
          scored by claude-haiku-4-5 · data refreshes every 5 min ·{" "}
          <a
            href="https://github.com/sheharyarr-ahmed/pulseflow"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-4 transition-colors hover:text-foreground"
          >
            GitHub
          </a>
        </p>
      </div>
    </footer>
  );
}
