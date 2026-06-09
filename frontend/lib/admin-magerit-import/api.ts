/**
 * Admin MAGERIT XML import API client (SAN-C MB-11.4).
 *
 * Endpoints backend (api/v1 m02_magerit.pilar_import_api):
 *   POST /api/v1/magerit/analysis/{id}/import-xml         · persist
 *   POST /api/v1/magerit/analysis/{id}/import-xml/preview · dry-run
 */
"use client";

import { api } from "@/lib/api";

export interface ImportXmlResponse {
  detected_format: string;
  assets_created: number;
  threat_assessments_created: number;
  safeguards_created: number;
}

export interface ImportXmlPreviewResponse {
  detected_format: string;
  assets_count: number;
  threat_assessments_count: number;
  safeguards_count: number;
  sample_asset_codes: string[];
}

const BASE = "/api/v1/magerit";

async function _uploadXml<T>(path: string, file: File): Promise<T> {
  const fd = new FormData();
  fd.append("file", file);
  return api<T>(path, { method: "POST", body: fd });
}

export async function previewMageritXml(
  analysisId: string,
  file: File,
): Promise<ImportXmlPreviewResponse> {
  return _uploadXml<ImportXmlPreviewResponse>(
    `${BASE}/analysis/${analysisId}/import-xml/preview`,
    file,
  );
}

export async function importMageritXml(
  analysisId: string,
  file: File,
): Promise<ImportXmlResponse> {
  return _uploadXml<ImportXmlResponse>(
    `${BASE}/analysis/${analysisId}/import-xml`,
    file,
  );
}
