/** Placeholder data for Sprint 2 surfaces whose backend endpoints don't exist yet.
 *
 * Each dataset is documented with the expected endpoint so the frontend can
 * swap mocks for real API calls one-by-one as the backend catches up.
 */
import type {
  ActivityEvent,
  DashboardAlert,
  DashboardKpis,
  Lead,
  MyDayItem,
} from "./types";

export const MOCK_KPIS: DashboardKpis = {
  active_projects: 12,
  leads_count: 8,
  leads_value_eur: 47_500,
  retainers_active: 15,
  mrr_eur: 4_200,
  treasury_30d_eur: 12_300,
  treasury_trend_pct: 8,
  projects_rag: "green",
};

export const MOCK_MY_DAY: MyDayItem[] = [
  {
    id: "md-1",
    type: "review_docs",
    title: "Revisar 3 documentos pendientes",
    count: 3,
    href: "/admin/projects",
  },
  {
    id: "md-2",
    type: "signature",
    title: "Firmar contrato C-004 (Innovatech)",
    count: 1,
    href: "/admin/projects",
  },
  {
    id: "md-3",
    type: "meeting",
    title: "Reunión con Soluciones Digitales Levante",
    scheduledAt: "2026-04-20T11:30:00Z",
    href: "/admin/meeting",
  },
];

export const MOCK_ALERTS: DashboardAlert[] = [
  {
    id: "al-1",
    severity: "red",
    project: "SDL",
    message: "Plazo auditoría ENS en 12 días",
    createdAt: "2026-04-19T09:00:00Z",
  },
  {
    id: "al-2",
    severity: "amber",
    project: "Innovatech",
    message: "MFA parcial detectado — falta cobertura en admins",
    createdAt: "2026-04-18T17:00:00Z",
  },
];

export const MOCK_ACTIVITY: ActivityEvent[] = [
  {
    id: "act-1",
    timestamp: "2026-04-19T14:02:00Z",
    type: "evidence_generated",
    description: "E-101 Política de seguridad generada para SDL",
    project_slug: "sdl",
  },
  {
    id: "act-2",
    timestamp: "2026-04-19T12:45:00Z",
    type: "scan_completed",
    description: "Nuclei scan completado — 2 findings informativos",
    project_slug: "innovatech",
  },
  {
    id: "act-3",
    timestamp: "2026-04-19T10:18:00Z",
    type: "proposal_sent",
    description: "Propuesta P-014 enviada a DataForma Galicia",
    project_slug: "dataforma",
  },
  {
    id: "act-4",
    timestamp: "2026-04-18T16:30:00Z",
    type: "document_signed",
    description: "Contrato C-003 firmado por el RSEG de SDL",
    project_slug: "sdl",
  },
];

const now = new Date("2026-04-20T10:00:00Z").toISOString();

export const MOCK_LEADS: Lead[] = [
  {
    id: "lead-1",
    empresa: "Ayuntamiento de Valencia",
    cif: "P4625200B",
    sector: "Sector público",
    score: 62,
    rag: "amber",
    value_eur: 8_500,
    stage: "new",
    contact_name: "María López",
    contact_email: "secretario@ayto-vlc.es",
    source: "licitación PLACSP",
    pliego_attached: true,
    last_touched_at: "2026-04-17T09:00:00Z",
  },
  {
    id: "lead-2",
    empresa: "DataForma Galicia",
    cif: "B36487129",
    sector: "Tecnología",
    score: 78,
    rag: "green",
    value_eur: 12_000,
    stage: "qualifying",
    contact_name: "Javier Pereira",
    contact_email: "jpereira@dataforma.gal",
    source: "referencia cliente",
    last_touched_at: "2026-04-19T11:00:00Z",
  },
  {
    id: "lead-3",
    empresa: "TechSol Asturias",
    cif: "B33991288",
    sector: "Tecnología",
    score: 85,
    rag: "green",
    value_eur: 15_000,
    stage: "meeting_exploratory",
    contact_name: "Aitor García",
    contact_email: "aitor@techsol.es",
    source: "LinkedIn",
    last_touched_at: now,
  },
  {
    id: "lead-4",
    empresa: "Consultora Moderna SL",
    cif: "B88112233",
    sector: "Servicios",
    score: 71,
    rag: "amber",
    value_eur: 9_500,
    stage: "proposal_sent",
    contact_name: "Lucía Ramos",
    contact_email: "lucia@consultoramoderna.es",
    last_touched_at: "2026-04-15T10:00:00Z",
  },
  {
    id: "lead-5",
    empresa: "Innovatech Burgos",
    cif: "B09234567",
    sector: "Tecnología",
    score: 88,
    rag: "green",
    value_eur: 18_000,
    stage: "negotiation",
    contact_name: "Miguel Ángel Soto",
    contact_email: "msoto@innovatech-burgos.com",
    last_touched_at: "2026-04-18T15:20:00Z",
  },
  {
    id: "lead-6",
    empresa: "Soluciones Digitales Levante",
    cif: "B96758412",
    sector: "Consultoría TI",
    score: 92,
    rag: "green",
    value_eur: 15_000,
    stage: "won",
    contact_name: "Clara Martínez",
    contact_email: "clara@sdlevante.es",
    last_touched_at: "2026-04-12T09:00:00Z",
  },
  {
    id: "lead-7",
    empresa: "Logística Sur SA",
    cif: "A29876543",
    sector: "Logística",
    score: 34,
    rag: "red",
    value_eur: 4_500,
    stage: "lost",
    contact_name: "Ramón Vela",
    lost_reason: "presupuesto insuficiente",
    last_touched_at: "2026-04-10T08:00:00Z",
  },
  {
    id: "lead-8",
    empresa: "Editorial Norte SL",
    cif: "B48772211",
    sector: "Editorial",
    score: 55,
    rag: "amber",
    value_eur: 6_200,
    stage: "paused",
    contact_name: "Alicia Prieto",
    last_touched_at: "2026-04-05T14:00:00Z",
  },
];
