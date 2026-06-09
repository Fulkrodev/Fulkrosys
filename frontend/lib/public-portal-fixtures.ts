/**
 * Public portal fixtures · sustituye sprint4-mock.ts post-FASE-9-cleanup (9.A.7).
 *
 * Estos fixtures alimentan paginas publicas de magic-link (sign legacy, upload,
 * survey) hasta que el endpoint backend GET /api/v1/magic-links/{token}/status
 * exponga payloads completos por purpose. La pagina /sign ya consume
 * useMagicLinkStatus real (purpose firma_documento + aprobacion_acta), pero
 * cae al LegacyDocumentSignFlow para sign generico mientras se completa la
 * matriz de purposes.
 *
 * Ver: TODO-FASE-X-MAGIC-LINK-PORTAL-INTEGRATION-001 en progress/backlog_formal.md.
 */
import type {
  MagicLinkContext,
  SignDocumentPayload,
  SurveyPayload,
  UploadPayload,
} from "./sprint4-types";

export function mockSignPayload(token: string): SignDocumentPayload {
  return {
    token,
    purpose: "sign",
    client_name: "Soluciones Digitales Levante",
    project_name: "Implantacion ENS Media",
    expires_at: new Date(Date.now() + 72 * 3_600 * 1_000).toISOString(),
    requires_otp: true,
    document_code: "E-200",
    document_title: "Procedimiento de Gestión de Riesgos",
    preview_snippet:
      "El presente procedimiento establece la metodologia para identificar, evaluar y tratar los riesgos de seguridad de la informacion, alineado con el RD 311/2022 y MAGERIT v3.",
    signatory_role: "Responsable de Seguridad (RSEG)",
  };
}

export function mockSurveyPayload(token: string): SurveyPayload {
  return {
    token,
    purpose: "onboarding_survey",
    client_name: "Cliente FULKRO",
    project_name: "Onboarding ENS",
    expires_at: new Date(Date.now() + 72 * 3_600 * 1_000).toISOString(),
    requires_otp: false,
    sector: "Administracion publica local",
    role: "Secretario general",
    questions: [
      {
        id: "q-1",
        text: "Cuantos empleados tiene la organizacion?",
        type: "choice",
        options: ["<10", "10-50", "51-250", ">250"],
        required: true,
      },
      {
        id: "q-2",
        text: "Que sistemas soportan procesos criticos?",
        type: "long",
        required: true,
      },
      {
        id: "q-3",
        text: "Teneis MFA implantado en sistemas administrativos?",
        type: "choice",
        options: ["Si, en todos", "Parcial (solo admins)", "No", "No lo se"],
        required: true,
      },
      {
        id: "q-4",
        text: "Describa los proveedores TIC principales",
        type: "long",
      },
      {
        id: "q-5",
        text: "Nivel de madurez estimado (1 bajo - 5 alto)",
        type: "scale",
        required: true,
      },
    ],
  };
}

export function mockUploadPayload(token: string): UploadPayload {
  return {
    token,
    purpose: "upload_evidence",
    client_name: "Soluciones Digitales Levante",
    project_name: "Implantacion ENS Media",
    expires_at: new Date(Date.now() + 72 * 3_600 * 1_000).toISOString(),
    requires_otp: false,
    expected_measure: "op.acc.6",
    expected_count: 2,
    instructions:
      "Subir captura de configuracion MFA del IdP (Azure AD) + export CSV con cobertura por usuario.",
  };
}

export function mockGenericMagicContext(token: string): MagicLinkContext {
  return {
    token,
    purpose: "view",
    client_name: "FULKRO",
    project_name: "Magic link",
    expires_at: new Date(Date.now() + 72 * 3_600 * 1_000).toISOString(),
    requires_otp: false,
  };
}
