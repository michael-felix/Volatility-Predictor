import type { Metadata } from "next";
import Link from "next/link";
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
  title: "Volatility Platform",
  description: "Real-time stock volatility predictions.",
};

const NAV_LINK_CLASS =
  "relative transition-colors hover:text-[var(--foreground)] " +
  "after:absolute after:-bottom-1 after:left-0 after:h-px after:w-full " +
  "after:origin-left after:scale-x-0 after:bg-[var(--brand)] " +
  "after:transition-transform after:duration-200 hover:after:scale-x-100";

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
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-10 border-b border-[var(--border-hairline)] bg-[var(--background)]/90 px-6 py-4 backdrop-blur">
          <div className="mx-auto flex max-w-4xl items-center justify-between">
            <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: "var(--brand)" }}
              />
              Volatility Platform
            </Link>
            <nav className="flex items-center gap-5 text-sm text-[var(--text-secondary)]">
              <Link href="/" className={NAV_LINK_CLASS}>
                Dashboard
              </Link>
              <Link href="/models" className={NAV_LINK_CLASS}>
                Models
              </Link>
              <Link href="/guide" className={NAV_LINK_CLASS}>
                Guide
              </Link>
            </nav>
          </div>
        </header>

        <main className="flex-1 px-6 py-6">{children}</main>

        <footer className="border-t border-[var(--border-hairline)] px-6 py-4 text-center text-xs text-[var(--text-muted)]">
          <p>
            Educational demo only — not financial advice. Predictions are
            estimates based on historical patterns.{" "}
            <Link href="/guide" className="underline hover:text-[var(--text-secondary)]">
              Read the guide
            </Link>
            .
          </p>
          <p className="mt-1 opacity-60">Built by Michael Lim</p>
        </footer>
      </body>
    </html>
  );
}
