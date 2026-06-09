/**
 * SafeMarkdown — render markdown con sanitización XSS (sub-bloque 6.B.1).
 *
 * react-markdown + remark-gfm (tablas, strikethrough, task lists) +
 * rehype-sanitize con schema permissive curado: links, listas, code
 * blocks, emphasis. NO scripts, NO iframes, NO style attrs, NO data:
 * URLs en href.
 *
 * Uso compartido cliente y admin (fallback render seguro server-side
 * si body_html no presente).
 */
"use client";

import ReactMarkdown from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";

const SAFE_SCHEMA = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    a: [
      ...(defaultSchema.attributes?.a ?? []),
      ["target", "_blank"],
      ["rel", "noopener", "noreferrer"],
    ],
    code: [...(defaultSchema.attributes?.code ?? []), "className"],
    span: [...(defaultSchema.attributes?.span ?? []), "className"],
  },
  // Tag whitelist conservador — bloquea iframe/script/style/object/embed
  tagNames: [
    "a", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "img", "input", "li", "ol", "p", "pre",
    "span", "strong", "table", "tbody", "td", "th", "thead", "tr",
    "ul",
  ],
};

interface SafeMarkdownProps {
  /** Texto markdown a renderizar. */
  body: string;
  /** Clase wrapper opcional (defaults a prose-style mínimo). */
  className?: string;
}

export function SafeMarkdown({ body, className }: SafeMarkdownProps) {
  return (
    <div className={className ?? "text-sm leading-relaxed space-y-2"}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, SAFE_SCHEMA]]}
        components={{
          a: ({ href, children, ...rest }) => (
            <a
              {...rest}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-fulkro-primary-600 underline hover:text-fulkro-primary-700"
            >
              {children}
            </a>
          ),
          code: ({ className: codeClass, children, ...rest }) => (
            <code
              {...rest}
              className={`${codeClass ?? ""} rounded bg-fulkro-ink-100 px-1 py-0.5 text-xs font-mono`}
            >
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="overflow-x-auto rounded-md bg-fulkro-ink-100 p-3 text-xs font-mono">
              {children}
            </pre>
          ),
          ul: ({ children }) => (
            <ul className="ml-5 list-disc space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="ml-5 list-decimal space-y-1">{children}</ol>
          ),
        }}
      >
        {body}
      </ReactMarkdown>
    </div>
  );
}
