import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import { GlobalFulkroFooter } from "@/components/layout/GlobalFulkroFooter";

import { Providers } from "./providers";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FULKRO",
  description:
    "Plataforma de implantación ENS (RD 311/2022) — consultoría automatizada",
  robots: { index: false, follow: false },
  manifest: "/site.webmanifest",
  icons: {
    apple: "/brand/favicon-192.png",
    other: [
      { rel: "icon", type: "image/png", sizes: "192x192", url: "/brand/favicon-192.png" },
      { rel: "icon", type: "image/png", sizes: "512x512", url: "/brand/favicon-512.png" },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="es"
      className={`${inter.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        {/* Skip-link a11y · keyboard users · WCAG 2.4.1 Bypass Blocks */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-fulkro-primary-700 focus:px-4 focus:py-2 focus:text-white focus:font-semibold focus:outline-none focus:ring-2 focus:ring-fulkro-primary-300"
        >
          Saltar al contenido principal
        </a>
        <Providers>{children}</Providers>
        <GlobalFulkroFooter />
      </body>
    </html>
  );
}
