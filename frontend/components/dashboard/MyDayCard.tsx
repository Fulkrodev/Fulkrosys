"use client";

import {
  Activity,
  ChevronRight,
  FileSignature,
  ListChecks,
  RefreshCw,
  Video,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useMyDay } from "@/hooks/useDashboardData";
import type { MyDayItem } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONS: Record<MyDayItem["type"], LucideIcon> = {
  review_docs: ListChecks,
  signature: FileSignature,
  meeting: Video,
  other: Activity,
};

export function MyDayCard() {
  const { data, isLoading, isError, refetch, isRefetching } = useMyDay();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Activity size={22} strokeWidth={2.2} /> Mi día
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ul className="space-y-3" aria-busy>
            {Array.from({ length: 3 }).map((_, i) => (
              <li
                key={i}
                className="h-9 animate-pulse rounded-md bg-fulkro-ink-100/70"
              />
            ))}
          </ul>
        ) : isError ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-fulkro-danger">
              Error cargando las tareas del día.
            </p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void refetch()}
              disabled={isRefetching}
              className="self-start"
              data-testid="myday-card-retry"
            >
              <RefreshCw
                size={14}
                className={isRefetching ? "animate-spin" : ""}
              />
              Reintentar
            </Button>
          </div>
        ) : data && data.length > 0 ? (
          <ul className="space-y-1.5">
            {data.map((item) => (
              <MyDayRow key={item.id} item={item} />
            ))}
          </ul>
        ) : (
          <p className="text-base font-medium text-[color:var(--fulkro-muted)]">
            Nada urgente para hoy.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function MyDayRow({ item }: { item: MyDayItem }) {
  const Icon = ICONS[item.type];
  const content = (
    <div
      className={cn(
        "group flex items-center gap-3 rounded-md border border-transparent px-3 py-2 text-sm transition",
        "hover:border-[color:var(--fulkro-surface-glass-border)] hover:bg-[color:var(--fulkro-surface-glass)]",
      )}
    >
      <span className="shrink-0 rounded bg-fulkro-ink-100 p-1.5 text-fulkro-primary-700">
        <Icon size={14} />
      </span>
      <span className="flex-1 text-fulkro-ink-700">{item.title}</span>
      {typeof item.count === "number" && item.count > 1 && (
        <span className="rounded bg-fulkro-ink-100 px-1.5 py-0.5 font-mono text-sm font-medium text-[color:var(--fulkro-muted)]">
          {item.count}
        </span>
      )}
      <ChevronRight
        size={14}
        className="text-fulkro-ink-500 opacity-60 transition group-hover:opacity-100"
      />
    </div>
  );

  return (
    <li>
      {item.href ? <Link href={item.href}>{content}</Link> : content}
    </li>
  );
}
