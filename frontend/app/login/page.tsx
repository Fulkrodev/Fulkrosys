import Image from "next/image";

import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <div className="fulkro-auth-bg flex min-h-dvh flex-col">
      <main className="relative z-10 flex flex-1 items-center justify-center px-4 py-10">
        <div className="grid w-full max-w-6xl items-center gap-10 md:grid-cols-2 md:gap-20">
          <div className="hidden items-center justify-center md:flex">
            <Image
              src="/brand/fulkro-logo-light.svg"
              alt="FULKRO"
              width={1200}
              height={320}
              priority
              className="w-full max-w-[620px] drop-shadow-[0_8px_28px_rgba(46,41,128,0.18)]"
            />
          </div>

          <div className="mx-auto w-full max-w-md space-y-6">
            <div className="flex flex-col items-center gap-5 md:hidden">
              <Image
                src="/brand/fulkro-logo-light.svg"
                alt="FULKRO"
                width={1200}
                height={320}
                priority
                className="w-full max-w-[340px]"
              />
            </div>
            <div className="text-center">
              <h1 className="text-4xl font-extrabold tracking-tight text-fulkro-primary-700">
                Acceso restringido
              </h1>
              <p className="mt-3 text-lg font-semibold text-fulkro-ink-700">
                Plataforma interna de consultoría ENS.
              </p>
            </div>

            <div className="card p-6">
              <LoginForm />
            </div>

            <p className="text-center text-[11px] uppercase tracking-wider text-fulkro-ink-500">
              Sesión registrada en audit_log · RD 311/2022
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
