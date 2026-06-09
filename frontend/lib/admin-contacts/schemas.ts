/**
 * Admin Contacts schemas TypeScript (sub-fase 5.5.E FASE 5.5).
 *
 * Espejo de backend/app/motors/m30_client_contacts/schemas.py.
 * Mantener sincronizado manualmente al cambiar contratos backend.
 */

export const ROLE_CATEGORIES = [
  "sponsor",
  "rseg",
  "ciso",
  "cto",
  "cio",
  "dpo",
  "legal",
  "compras",
  "rrhh",
  "operaciones",
  "tecnico",
  "auditor_interno",
  "consultor_externo",
  "usuario_final",
  "otros",
] as const;
export type RoleCategory = (typeof ROLE_CATEGORIES)[number];

export const ROLE_CATEGORY_LABELS: Record<RoleCategory, string> = {
  sponsor: "Sponsor",
  rseg: "Resp. Seguridad (RSEG)",
  ciso: "CISO",
  cto: "CTO",
  cio: "CIO",
  dpo: "DPO",
  legal: "Legal",
  compras: "Compras",
  rrhh: "RRHH",
  operaciones: "Operaciones",
  tecnico: "Técnico",
  auditor_interno: "Auditor interno",
  consultor_externo: "Consultor externo",
  usuario_final: "Usuario final",
  otros: "Otros",
};

export const PREFERRED_COMMUNICATIONS = [
  "email",
  "phone",
  "whatsapp",
  "linkedin_dm",
  "portal_inbox",
] as const;
export type PreferredCommunication =
  (typeof PREFERRED_COMMUNICATIONS)[number];

export const PREFERRED_COMMUNICATION_LABELS: Record<
  PreferredCommunication,
  string
> = {
  email: "Email",
  phone: "Teléfono",
  whatsapp: "WhatsApp",
  linkedin_dm: "LinkedIn DM",
  portal_inbox: "Bandeja portal",
};

export const INTERACTION_TYPES = [
  "meeting",
  "message",
  "magic_link",
  "contract_signature",
  "email",
  "other",
] as const;
export type InteractionType = (typeof INTERACTION_TYPES)[number];

export const INTERACTION_TYPE_LABELS: Record<InteractionType, string> = {
  meeting: "Reunión",
  message: "Mensaje",
  magic_link: "Magic link",
  contract_signature: "Firma contrato",
  email: "Email",
  other: "Otro",
};

// === Contacts ===

export type ClientContactCreate = {
  full_name: string;
  preferred_name?: string | null;
  email: string;
  phone?: string | null;
  linkedin_url?: string | null;
  role_title: string;
  role_category: RoleCategory;
  is_primary?: boolean;
  is_signatory?: boolean;
  has_portal_access?: boolean;
  notes_marcos?: string | null;
  preferred_communication?: PreferredCommunication | null;
  timezone?: string;
};

export type ClientContactUpdate = Partial<ClientContactCreate>;

export type ClientContactOut = {
  id: string;
  client_id: string;
  full_name: string;
  preferred_name: string | null;
  email: string;
  phone: string | null;
  linkedin_url: string | null;
  role_title: string;
  role_category: string;
  is_primary: boolean;
  is_signatory: boolean;
  has_portal_access: boolean;
  client_user_id: string | null;
  notes_marcos: string | null;
  preferred_communication: string | null;
  timezone: string;
  is_active: boolean;
  inactive_reason: string | null;
  inactive_since: string | null;
  created_at: string;
  updated_at: string | null;
  last_interaction_at: string | null;
  last_interaction_type: string | null;
  interactions_count: number;
};

export type ClientContactListItem = {
  id: string;
  full_name: string;
  preferred_name: string | null;
  email: string;
  phone: string | null;
  role_title: string;
  role_category: string;
  is_primary: boolean;
  is_signatory: boolean;
  has_portal_access: boolean;
  is_active: boolean;
  last_interaction_at: string | null;
  last_interaction_type: string | null;
};

// === Timeline ===

export type TimelineEntryOut = {
  id: string;
  interaction_type: string;
  source_motor: string | null;
  source_id: string | null;
  summary: string | null;
  details: Record<string, unknown> | null;
  occurred_at: string;
};

// === Filters ===

export type ListContactsFilters = {
  role_category?: RoleCategory | null;
  is_active?: boolean | null;
  is_signatory?: boolean | null;
  search?: string | null;
};
