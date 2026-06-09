"use client";

/**
 * Root global error boundary · Next.js 14 App Router convention.
 *
 * Sub-atom Sesión 3B-2B.2 Path B fix · OPS-052 16ª manifestación resolved.
 *
 * MUST include <html> and <body> tags (replaces root layout when crash propagates).
 * Per Next.js docs: global-error.tsx handles errors thrown in the root layout itself.
 *
 * Distinct from app/error.tsx (handles errors within child routes preserving layout).
 *
 * R30 admin tutor + R29 cliente sin presión · friendly fallback.
 */
import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.error("[global-error] root crash", error);
  }, [error]);

  return (
    <html lang="es">
      <body
        style={{
          margin: 0,
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
          background: "rgb(250, 250, 250)",
          color: "rgb(44, 44, 56)",
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "1.5rem",
        }}
      >
        <div
          style={{
            maxWidth: "32rem",
            width: "100%",
            background: "white",
            border: "1px solid rgb(232, 232, 236)",
            borderRadius: "0.75rem",
            padding: "1.5rem",
            boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
          }}
        >
          <h1
            style={{
              fontSize: "1.25rem",
              fontWeight: 700,
              color: "rgb(80, 72, 204)",
              marginBottom: "0.5rem",
              marginTop: 0,
            }}
          >
            ⚠ Algo no funcionó como esperábamos
          </h1>
          <p
            style={{
              fontSize: "0.875rem",
              color: "rgb(77, 77, 89)",
              marginBottom: "1rem",
            }}
          >
            Hubo un error inesperado en la aplicación. Puedes intentar
            recargarla o volver al inicio.
          </p>
          {error.digest ? (
            <p
              style={{
                fontSize: "0.75rem",
                color: "rgb(110, 110, 122)",
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
                marginBottom: "1rem",
              }}
            >
              Reference: <code>{error.digest}</code>
            </p>
          ) : null}
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              type="button"
              onClick={() => reset()}
              style={{
                background: "rgb(108, 99, 255)",
                color: "white",
                border: "none",
                borderRadius: "0.375rem",
                padding: "0.5rem 1rem",
                fontSize: "0.875rem",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Reintentar
            </button>
            <a
              href="/"
              style={{
                background: "white",
                color: "rgb(80, 72, 204)",
                border: "1px solid rgb(184, 184, 196)",
                borderRadius: "0.375rem",
                padding: "0.5rem 1rem",
                fontSize: "0.875rem",
                fontWeight: 600,
                textDecoration: "none",
                display: "inline-block",
              }}
            >
              Ir al inicio
            </a>
          </div>
        </div>
      </body>
    </html>
  );
}
