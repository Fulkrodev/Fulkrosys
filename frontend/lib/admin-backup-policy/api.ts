/**
 * Admin 3-2-1 backup policy API client (SAN-C MB-11.5).
 *
 * Endpoint backend stateless (sin project_id):
 *   POST /api/v1/backup-policy/3-2-1/evaluate
 */
"use client";

import { api } from "@/lib/api";

export interface BackupCopyInput {
  label: string;
  media_type: string;
  is_offsite: boolean;
}

export interface Compliance321Response {
  compliant: boolean;
  copies_count: number;
  media_types: string[];
  offsite_count: number;
  gaps: string[];
}

export async function evaluate321(
  copies: BackupCopyInput[],
): Promise<Compliance321Response> {
  return api<Compliance321Response>(
    "/api/v1/backup-policy/3-2-1/evaluate",
    {
      method: "POST",
      body: JSON.stringify({ copies }),
    },
  );
}
