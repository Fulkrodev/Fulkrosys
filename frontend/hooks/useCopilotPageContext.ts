"use client";

import { useParams, usePathname } from "next/navigation";
import * as React from "react";

import { useCopilotStore } from "@/lib/stores/copilot-store";

const MOTOR_KEYWORDS: Array<{ key: string; motor: string }> = [
  { key: "magerit", motor: "magerit" },
  { key: "obligations", motor: "obligations" },
  { key: "obligaciones", motor: "obligations" },
  { key: "conformity", motor: "conformity" },
  { key: "conformidad", motor: "conformity" },
  { key: "diagnosis", motor: "diagnosis" },
  { key: "diagnostico", motor: "diagnosis" },
  { key: "evidence", motor: "evidence" },
  { key: "evidencias", motor: "evidence" },
];

function deriveActiveMotor(pathname: string | null): string | undefined {
  if (!pathname) return undefined;
  const lower = pathname.toLowerCase();
  for (const { key, motor } of MOTOR_KEYWORDS) {
    if (lower.includes(`/${key}`)) return motor;
  }
  return undefined;
}

function pickFirst(value: string | string[] | undefined): string | undefined {
  if (!value) return undefined;
  return Array.isArray(value) ? value[0] : value;
}

export function useCopilotPageContext() {
  const pathname = usePathname();
  const params = useParams<Record<string, string | string[]>>();
  const setPanelContext = useCopilotStore((s) => s.setPanelContext);

  React.useEffect(() => {
    const projectId = pickFirst(params?.projectId) ?? pickFirst(params?.id);
    const clientId = pickFirst(params?.clientId);
    const activeMotor = deriveActiveMotor(pathname);
    setPanelContext({
      url: pathname ?? undefined,
      projectId,
      clientId,
      activeMotor,
    });
  }, [pathname, params, setPanelContext]);
}
