"use client";

/**
 * SearchBar · debounced input + clear button + ESC keyboard.
 * SAN-E v3.MB-6 atom 7 · Q2 D hybrid ILIKE backend.
 */
import { Search, X } from "lucide-react";

import { cn } from "@/lib/utils";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchBar({
  value,
  onChange,
  placeholder = "Buscar por nombre, contenido o tipo…",
  className,
}: Props) {
  return (
    <div
      data-testid="files-search-bar"
      className={cn(
        "relative flex items-center gap-2 rounded-lg border border-fulkro-ink-200 bg-white px-3 py-1.5 focus-within:ring-2 focus-within:ring-fulkro-primary-700/30",
        className,
      )}
    >
      <Search
        className="h-4 w-4 text-fulkro-ink-500 flex-shrink-0"
        aria-hidden
      />
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") onChange("");
        }}
        placeholder={placeholder}
        className="flex-1 bg-transparent text-sm outline-none placeholder:text-fulkro-ink-400"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          aria-label="Limpiar búsqueda"
          className="text-fulkro-ink-500 hover:text-fulkro-ink-800"
        >
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      )}
    </div>
  );
}
