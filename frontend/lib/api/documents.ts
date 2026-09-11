/**
 * Motor 6 — Document Factory API client (subset rectores · MB-9.bis.3).
 *
 * Endpoints expuestos:
 *  - POST /api/v1/projects/{id}/manual-sgsi/generate (DOCX blob)
 *  - POST /api/v1/projects/{id}/plan-director/generate (DOCX blob)
 *
 * Usa fetch directo (api() wrapper solo JSON). Para artefactos
 * documentales completos del Motor 6 (templates · render · catalog),
 * consultar otros módulos en `/api/v1/document-factory`.
 */
import { api } from "@/lib/api";
import { CSRF_HEADER } from "@/lib/constants";
import { getCsrfToken } from "@/lib/csrf";

const BASE = "/api/v1";

async function _downloadDocxPost(path: string): Promise<Blob> {
  const headers = new Headers();
  const csrf = getCsrfToken();
  if (csrf) headers.set(CSRF_HEADER, csrf);

  const response = await fetch(path, {
    method: "POST",
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      if (payload && typeof payload === "object" && "detail" in payload) {
        detail = String((payload as { detail: unknown }).detail);
      }
    } catch {
      // not JSON · use statusText
    }
    throw new Error(detail);
  }

  return response.blob();
}

/** POST /api/v1/projects/{id}/manual-sgsi/generate · DOCX E-160. */
export function generateManualSgsiDocx(projectId: string): Promise<Blob> {
  return _downloadDocxPost(`${BASE}/projects/${projectId}/manual-sgsi/generate`);
}

/** POST /api/v1/projects/{id}/plan-director/generate · DOCX E-170. */
export function generatePlanDirectorDocx(projectId: string): Promise<Blob> {
  return _downloadDocxPost(
    `${BASE}/projects/${projectId}/plan-director/generate`,
  );
}

// ===================================================================
// P2 · el cable que faltaba
//
// El generador generico existe y funciona desde el primer dia:
//   POST /api/v1/projects/{id}/documents/generate  {template_codigo, context}
// Saca 63 de los 65 entregables del catalogo en una pasada. Y no lo llamaba
// NADIE: `grep -rn "documents/generate" frontend/` devolvia cero resultados.
// El motor estaba entero y le faltaba el cable hasta la pantalla.
// ===================================================================


export interface EntregablesRequeridos {
  categoria: string;
  requeridos: string[];
  presentes: string[];
  /** Faltan Y tienen plantilla en el catalogo: generables hoy. */
  faltan: string[];
  /** Faltan y NO tienen plantilla: no se pueden generar todavia. */
  faltan_sin_plantilla: string[];
  total: number;
  presentes_count: number;
}

/** Que entregables exige el checklist para la categoria, y cuales faltan. */
export function getEntregablesRequeridos(
  projectId: string,
): Promise<EntregablesRequeridos> {
  // Sin `categoria`: la deriva el backend del proyecto. La pantalla no tiene
  // por que saberla para preguntar que le falta.
  return api<EntregablesRequeridos>(
    `${BASE}/audit-prep/projects/${projectId}/entregables-requeridos`,
  );
}

export interface DocumentoGenerado {
  document_id: string;
  template_codigo: string;
  nombre: string;
  rendered_hash: string | null;
  pdf_warning?: string | null;
}

/** Genera UN entregable por su codigo de plantilla y lo registra. */
export function generateDocumentoPorCodigo(
  projectId: string,
  templateCodigo: string,
): Promise<DocumentoGenerado> {
  return api<DocumentoGenerado>(
    `${BASE}/projects/${projectId}/documents/generate`,
    {
      method: "POST",
      json: {
        template_codigo: templateCodigo,
        context: {},
        generate_pdf: true,
        sign: true,
        generated_by: "admin.documentos",
      },
    },
  );
}
