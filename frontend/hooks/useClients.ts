"use client";

import { useQuery } from "@tanstack/react-query";

import { api, ApiError } from "@/lib/api";
import type { Client } from "@/lib/types";

/** GET /api/v1/clients — falls back to empty list if the backend has no data yet. */
export function useClients() {
  return useQuery({
    queryKey: ["clients"],
    queryFn: async () => {
      try {
        const clients = await api<Client[]>("/api/v1/clients");
        return clients;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return [] as Client[];
        throw err;
      }
    },
  });
}
