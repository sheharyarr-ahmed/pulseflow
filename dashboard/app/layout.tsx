import type { Metadata } from "next";
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
