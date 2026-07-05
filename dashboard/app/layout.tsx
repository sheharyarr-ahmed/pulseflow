import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://pulseflow.vercel.app",
  ),
  title: "PulseFlow — Daily Freelance-Market Job Hunt",
  description:
    "Code-first workflow automation that runs an unattended daily job hunt: fetch, dedupe, LLM-score, and Slack-notify — with a daily heartbeat so silence means breakage.",
  applicationName: "PulseFlow",
  openGraph: {
    title: "PulseFlow — Daily Freelance-Market Job Hunt",
    description:
      "Code-first job-hunt automation that ships a daily heartbeat.",
    siteName: "PulseFlow",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "PulseFlow — Daily Freelance-Market Job Hunt",
    description:
      "Code-first job-hunt automation that ships a daily heartbeat.",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
};

// Runs before paint: applies the stored/system theme (no flash) and marks JS as
// available so scroll-reveal styles only ever hide content when they can also
// unhide it. Static first-party string — not feed data (Decision 20 untouched).
const themeInit = `(function(){var c=document.documentElement.classList;c.add("js");try{var t=localStorage.getItem("theme");if(t==="dark"||(!t&&matchMedia("(prefers-color-scheme: dark)").matches))c.add("dark")}catch(e){}})()`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className="flex min-h-full flex-col bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
