/**
 * Admin Archetype API client (SAN-C MB-11.6).
 *
 * Reusa frontend/lib/api.ts (admin context · CSRF + cookies admin).
 *
 * Endpoints backend (api/v1 archetype_router montado main.py):
 *   POST /api/v1/projects/{project_id}/classify-archetype
 *   GET  /api/v1/projects/{project_id}/archetype
 *
 * RBAC backend: require_owner (Marcos admin only) heredado del get_db.
 */
"use client";

import { api } from "@/lib/api";
import type {
  ArchetypeResponse,
  ClassifyArchetypeRequest,
} from "./schemas";

const BASE = "/api/v1/projects";

export async function classifyArchetype(
  projectId: string,
  body: ClassifyArchetypeRequest,
): Promise<ArchetypeResponse> {
  return api<ArchetypeResponse>(
    `${BASE}/${projectId}/classify-archetype`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
}

export async function getArchetype(projectId: string): Promise<ArchetypeResponse> {
  return api<ArchetypeResponse>(`${BASE}/${projectId}/archetype`);
}
