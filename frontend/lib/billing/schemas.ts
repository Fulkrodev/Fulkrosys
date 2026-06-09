/**
 * Schemas TypeScript MB-18 auto-billing + retainer churn (ADR-040).
 *
 * Mirror exacto Pydantic schemas de backend/app/billing/api.py +
 * backend/app/retainer/api.py.
 */

export interface FinanceKpis {
  billed_this_month_eur: string;
  paid_this_month_eur: string;
  pending_total_eur: string;
  overdue_count: number;
}

export interface PendingPaymentRow {
  milestone_id: string;
  milestone_name: string;
  milestone_index: number;
  project_id: string;
  project_name: string;
  invoice_id: string | null;
  invoice_number: string | null;
  amount_eur: string;
  billed_at: string | null;
  days_pending: number;
}

export interface MarkPaidRequest {
  payment_reference?: string;
  payment_notes?: string;
  paid_at?: string;
}

export interface MarkPaidResponse {
  milestone_id: string;
  status: string;
  paid_at: string | null;
  payment_reference: string | null;
  workflow_advanced_to_phase: number | null;
}

export interface RegenerateMilestonesResponse {
  contract_id: string;
  created: number;
  skipped: number;
}

export interface ClientInvoiceRow {
  invoice_id: string;
  invoice_number: string | null;
  concepto: string | null;
  base_imponible: string | null;
  iva_importe: string | null;
  total: string | null;
  fecha_emision: string | null;
  fecha_vencimiento: string | null;
  estado_pago: string | null;
  bank_instructions_html: string;
  bank_instructions_text: string;
}

// ──────────── #45 · vista implementación × pagos ────────────

export type PaymentState = "paid" | "due" | "upcoming";

export interface ImplementationPaymentRow {
  milestone_id: string;
  milestone_index: number;
  milestone_name: string;
  description: string | null;
  workflow_phase_index: number;
  phase_label: string;
  amount_eur: string;
  vat_percent: string;
  amount_with_vat_eur: string;
  percent_of_total: string | null;
  scheduled_date: string | null;
  status: string;
  payment_state: PaymentState;
  phase_reached: boolean;
  is_overdue: boolean;
  paid_at: string | null;
  billed_at: string | null;
}

export interface ImplementationPaymentsTotals {
  total_eur: string;
  paid_eur: string;
  pending_eur: string;
  overdue_count: number;
  next_due_date: string | null;
}

export interface ImplementationPaymentsView {
  project_id: string;
  project_name: string;
  categoria: string | null;
  current_phase: string | null;
  current_phase_index: number;
  current_phase_label: string;
  found: boolean;
  milestones: ImplementationPaymentRow[];
  totals: ImplementationPaymentsTotals;
}

// Resumen amable (R29) que devuelve el endpoint del portal cliente.
export interface ClientImplementationHito {
  concepto: string;
  fase: string;
  importe_eur: string;
  estado: string;
  payment_state: PaymentState;
  fecha_prevista: string | null;
  vencido: boolean;
  pagado_el: string | null;
}

export interface ClientImplementationPayments {
  project_name: string;
  fase_actual: string | null;
  total_eur: string;
  pagado_eur: string;
  pendiente_eur: string;
  proximo_pago_previsto: string | null;
  hitos: ClientImplementationHito[];
}

export type RetainerRiskLevel = "low" | "medium" | "high" | "critical";

export const RETAINER_RISK_LEVELS: RetainerRiskLevel[] = [
  "low",
  "medium",
  "high",
  "critical",
];

export interface ChurnRiskRow {
  signal_id: string;
  retainer_id: string;
  project_id: string;
  // Opcional · el endpoint de churn-risk puede no resolver el nombre del cliente
  // (la lista canónica /finance no lo usa). El widget cae a un label de retainer.
  client_name?: string | null;
  computed_at: string;
  churn_risk_score: string;
  risk_level: RetainerRiskLevel;
  days_since_portal_login: number | null;
  days_since_chat_msg_client: number | null;
  tasks_overdue_count: number;
  invoices_overdue_count: number;
  primary_risk_factors: string[];
  recommended_action: string | null;
}

export type RetainerState =
  | "active"
  | "paused"
  | "expired"
  | "cancelled"
  | "upgraded"
  | "downgraded"
  | "churned";

export const RETAINER_STATES: RetainerState[] = [
  "active",
  "paused",
  "expired",
  "cancelled",
  "upgraded",
  "downgraded",
  "churned",
];

export interface RetainerTransitionRequest {
  target_state: RetainerState;
  reason?: string;
}

export interface RetainerTransitionResponse {
  retainer_id: string;
  previous_state: string;
  new_state: string;
  reason: string | null;
}

export interface ScanChurnResponse {
  total_scanned: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  alerts_created: number;
}
