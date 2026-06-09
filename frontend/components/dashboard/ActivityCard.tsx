"use client";

import { Activity, RefreshCw } from "lucide-react";

import { ActivityFeed } from "@/components/data/ActivityFeed";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useActivity } from "@/hooks/useDashboardData";

export function ActivityCard() {
  const { data, isLoading, isError, refetch, isRefetching } = useActivity();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2.5">
          <Activity size={22} strokeWidth={2.2} /> Actividad reciente
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ul className="space-y-3" aria-busy>
            {Array.from({ length: 3 }).map((_, i) => (
              <li
                key={i}
                className="h-10 animate-pulse rounded-md bg-fulkro-ink-100/70"
              />
            ))}
          </ul>
        ) : isError ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-fulkro-danger">
              No pude obtener la actividad reciente.
            </p>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void refetch()}
              disabled={isRefetching}
              className="self-start"
              data-testid="activity-card-retry"
            >
              <RefreshCw
                size={14}
                className={isRefetching ? "animate-spin" : ""}
              />
              Reintentar
            </Button>
          </div>
        ) : (
          <ActivityFeed events={data ?? []} max={6} />
        )}
      </CardContent>
    </Card>
  );
}
