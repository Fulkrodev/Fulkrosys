"use client";

import { Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * SectionPlaceholder · Sesión 3B-2B.6 CLUSTER 2 Phase 4 scaffold.
 *
 * Las 9 sections empiezan como placeholder informativo · contenidos read-only
 * reales se wiren en Phase 5 (commits siguientes). Phase 4 = entry gate +
 * navigation + branding · Phase 5 = views.
 */
export function SectionPlaceholder({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles size={16} className="text-fulkro-info-700" aria-hidden="true" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p>{description}</p>
        <p className="rounded-md border border-fulkro-info-700/30 bg-fulkro-info-700/5 px-3 py-2 text-[12px] text-fulkro-info-700">
          {/* #19 · sin referencias internas a "fase del despliegue" ante el
              auditor ENAC. Copy neutro y profesional. */}
          Esta sección se mostrará cuando el consultor publique los datos
          correspondientes del proyecto · todo acceso queda registrado en el
          audit log inmutable.
        </p>
      </CardContent>
    </Card>
  );
}
