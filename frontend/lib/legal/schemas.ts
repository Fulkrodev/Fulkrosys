/**
 * Public-facing legal/trust API types (atom 9.bis.5).
 *
 * Mirror of `backend/app/motors/m_compliance_monitor/public_api.py`.
 */

export type OverallHealth = "green" | "yellow" | "red" | "unknown";

export interface FrameworkStatus {
  name: string;
  status: "active" | "aligned" | "preparedness" | "planned";
  regulatory_basis: string | null;
  since: string | null;
}

export interface ISMSCertification {
  name: string;
  status: "preparedness" | "certified" | "planned";
  expected: string | null;
}

export interface NormaScore {
  norma_key: string;
  norma_name: string;
  score: number | null;
  status: "green" | "yellow" | "red" | "unknown";
  last_report: string | null;
  regulatory_basis_url: string;
}

export interface ComplianceStatusPublic {
  overall_health: OverallHealth;
  last_check: string | null;
  compliance_frameworks: FrameworkStatus[];
  sub_processors_count: number;
  last_breach_reported: string | null;
  isms_certifications: ISMSCertification[];
  monitor_summary: {
    green: number;
    yellow: number;
    red: number;
    unknown: number;
    total: number;
  };
  compliance_scores_per_norma: NormaScore[];
}

export interface SubProcessorSubscribeResult {
  subscribed: boolean;
  email: string;
  message: string;
}

/** Static sub-processor list — kept in sync with docs/06-Sub_Processors */
export interface SubProcessor {
  slug: string;
  name: string;
  service: string;
  service_es: string;
  data_location: string;
  gdpr_mechanism: string;
  dpa_status: "vigente" | "no-aplica" | "pendiente";
  purpose_es: string;
  privacy_url: string | null;
}

export const SUB_PROCESSORS: SubProcessor[] = [
  {
    slug: "hetzner",
    name: "Hetzner Online GmbH",
    service: "Hosting infrastructure",
    service_es: "Infraestructura de hosting",
    data_location: "Falkenstein, Alemania (UE)",
    gdpr_mechanism: "DPA firmado · datos en UE",
    dpa_status: "vigente",
    purpose_es:
      "Servidores dedicados que alojan la plataforma FULKRO (backend, base de datos, almacenamiento objeto).",
    privacy_url: "https://www.hetzner.com/legal/privacy-policy/",
  },
  {
    slug: "postmark",
    name: "Postmark (ActiveCampaign LLC)",
    service: "Transactional email delivery",
    service_es: "Envío de emails transaccionales",
    data_location: "EU Data Region",
    gdpr_mechanism: "DPA firmado · datos en UE",
    dpa_status: "vigente",
    purpose_es:
      "Entrega de emails operacionales: magic links, notificaciones, recordatorios al cliente.",
    privacy_url: "https://postmarkapp.com/eu-privacy",
  },
  {
    slug: "anthropic",
    name: "Anthropic PBC",
    service: "Claude LLM API",
    service_es: "API de modelo de lenguaje Claude",
    data_location: "Estados Unidos (replicación en Frankfurt)",
    gdpr_mechanism: "DPA + Cláusulas Contractuales Tipo (SCC 2021/914)",
    dpa_status: "vigente",
    purpose_es:
      "Procesamiento de lenguaje natural para el copiloto FULKRO y análisis automatizado de documentos del cliente.",
    privacy_url: "https://www.anthropic.com/legal/privacy",
  },
  {
    slug: "360dialog",
    name: "360dialog GmbH",
    service: "WhatsApp Business API gateway",
    service_es: "Gateway de WhatsApp Business API",
    data_location: "Alemania (UE)",
    gdpr_mechanism: "DPA firmado · datos en UE",
    dpa_status: "vigente",
    purpose_es:
      "Canal WhatsApp para comunicaciones operacionales con clientes (cuando han consentido este canal explícitamente).",
    privacy_url: "https://www.360dialog.com/privacy-policy/",
  },
  {
    slug: "minio",
    name: "MinIO (self-hosted)",
    service: "Object storage",
    service_es: "Almacenamiento de objetos",
    data_location: "Co-localizado con Hetzner (Falkenstein, DE)",
    gdpr_mechanism: "Auto-hospedado · sin tercero implicado",
    dpa_status: "no-aplica",
    purpose_es:
      "Almacenamiento de documentos firmados, evidencias y artefactos generados (auto-hospedado, no es un sub-procesador externo).",
    privacy_url: null,
  },
];
