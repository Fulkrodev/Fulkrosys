import Link from "next/link";

import { Logo } from "@/components/brand/Logo";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-fulkro-ink-50">
      <header className="flex items-center justify-between border-b border-fulkro-ink-300/60 bg-white px-6 py-3">
        <Link href="/login" className="inline-flex">
          <Logo variant="light" size="md" priority />
        </Link>
        <p className="text-[11px] uppercase tracking-wider text-fulkro-ink-500">
          Enlace seguro FULKRO · firmado Ed25519
        </p>
      </header>
      <main
        id="main-content"
        tabIndex={-1}
        className="flex flex-1 flex-col items-center px-4 py-10 focus:outline-none"
      >
        <div className="w-full max-w-lg">{children}</div>
      </main>
      <footer className="border-t border-fulkro-ink-300/60 bg-white px-6 py-3 text-center text-[11px] text-fulkro-ink-500">
        Este enlace caduca 72 horas tras su emisión · RD 311/2022
      </footer>
    </div>
  );
}
