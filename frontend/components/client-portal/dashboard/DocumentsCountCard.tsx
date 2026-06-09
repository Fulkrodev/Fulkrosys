"use client";

/**
 * DocumentsCountCard · zone 3 dashboard.
 */
import Link from "next/link";
import { FileText } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  count: number;
}

export function DocumentsCountCard({ count }: Props) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Documentos</CardTitle>
        <Link
          href="/client-portal/files"
          className="text-sm font-bold text-[color:var(--fulkro-accent)] hover:underline"
        >
          Ver todos →
        </Link>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4">
          <FileText className="h-8 w-8 text-[color:var(--fulkro-subtitle)]" />
          <div>
            <p className="text-4xl font-bold tracking-tight text-[color:var(--fulkro-title)]">
              {count}
            </p>
            <p className="text-sm font-medium text-[color:var(--fulkro-muted)]">
              nuevos en los últimos 7 días
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
