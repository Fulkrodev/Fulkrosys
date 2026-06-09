import Image from "next/image";
import Link from "next/link";

export default function NotFound() {
  return (
    <div
      // Architectural fix · gradient via ::before pseudo-element so axe-core
      // computes contrast against solid #0a1a5c (see Sidebar.tsx).
      className="sidebar-chrome flex min-h-dvh flex-col text-white"
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(circle at 30% 20%, rgba(255,255,255,0.08) 0%, transparent 60%)",
        }}
      />

      <div className="relative z-10 px-6 py-6">
        <Link href="/admin/dashboard" className="inline-flex">
          <Image
            src="/brand/fulkro-logo-mono-white.svg"
            alt="FULKRO"
            width={240}
            height={64}
            priority
          />
        </Link>
      </div>

      <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 pb-16 text-center">
        <p className="text-[140px] font-black leading-none tracking-tighter text-white md:text-[200px]">
          404
        </p>

        <h1 className="mt-6 text-4xl font-bold tracking-tight text-white md:text-5xl">
          Página no encontrada
        </h1>

        <p className="mt-5 max-w-2xl text-lg font-medium text-white/80 md:text-xl">
          La ruta que buscas no existe o aún no está disponible.
        </p>

        <Link
          href="/admin/dashboard"
          style={{
            backgroundColor: "rgba(255, 255, 255, 0.95)",
            color: "var(--fulkro-title)",
          }}
          className="mt-12 inline-flex items-center justify-center rounded-xl px-8 py-4 text-lg font-bold shadow-lg ring-1 ring-white/30 transition-all hover:scale-[1.03] hover:bg-white"
        >
          ← Volver al panel
        </Link>

        <Link
          href="/admin/dashboard"
          className="mt-6 text-sm font-semibold uppercase tracking-wider text-white/60 transition-colors hover:text-white"
        >
          o ir al dashboard principal
        </Link>
      </div>
    </div>
  );
}
