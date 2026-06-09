/**
 * LegalArticle · shared chrome for legal pages (atom 9.bis.1 PARTE B).
 *
 * Provides the article header (title + subtitle + last updated) and a
 * styled <article> wrapper that applies the legal-prose Tailwind classes
 * uniformly to all 4 legal pages (privacy, cookies, terms, imprint).
 */
import { CalendarDays } from "lucide-react";

interface LegalArticleProps {
  title: string;
  subtitle?: string;
  lastUpdated?: string;
  children: React.ReactNode;
}

export function LegalArticle({
  title,
  subtitle,
  lastUpdated = "2026-05-12",
  children,
}: LegalArticleProps) {
  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-10">
        <h1 className="text-3xl font-semibold tracking-tight text-fulkro-ink-900 sm:text-4xl">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-2 text-base text-fulkro-ink-700">{subtitle}</p>
        ) : null}
        <p className="mt-3 inline-flex items-center gap-1 rounded bg-fulkro-ink-100 px-2 py-1 text-xs text-fulkro-ink-600">
          <CalendarDays className="h-3.5 w-3.5" />
          Última actualización: {lastUpdated}
        </p>
      </header>
      <article className="legal-prose space-y-8 text-fulkro-ink-800">
        {children}
      </article>
      <style
        // eslint-disable-next-line react/no-unknown-property
        dangerouslySetInnerHTML={{
          __html: `
            .legal-prose section { scroll-margin-top: 4rem; }
            .legal-prose h2 {
              font-size: 1.25rem;
              font-weight: 600;
              color: #0f172a;
              margin-bottom: 0.75rem;
              letter-spacing: -0.01em;
            }
            .legal-prose p { margin: 0 0 0.75rem 0; line-height: 1.65; }
            .legal-prose ul {
              margin: 0 0 0.75rem 1.5rem;
              list-style: disc;
            }
            .legal-prose li { margin: 0.25rem 0; line-height: 1.6; }
            .legal-prose a { color: #0f172a; text-decoration: underline; }
            .legal-prose a:hover { color: #000; }
            .legal-prose code {
              background: #f1f5f9;
              padding: 1px 5px;
              border-radius: 3px;
              font-size: 0.875em;
              font-family: ui-monospace, Menlo, Consolas, monospace;
            }
            .legal-prose strong { color: #0f172a; }
          `,
        }}
      />
    </div>
  );
}
