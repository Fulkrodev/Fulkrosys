"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { clientApi } from "@/lib/client-portal-api";

export default function ClientPortalRoot() {
  const router = useRouter();
  useEffect(() => {
    let cancelled = false;
    clientApi("/client-portal/me")
      .then(() => {
        if (!cancelled) router.replace("/client-portal/dashboard");
      })
      .catch(() => {
        if (!cancelled) router.replace("/client-portal/login");
      });
    return () => {
      cancelled = true;
    };
  }, [router]);
  return null;
}
