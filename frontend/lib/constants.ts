/** Route paths used across the app. */
export const ROUTES = {
  login: "/login",
  dashboard: "/admin/dashboard",
  pipeline: "/admin/pipeline",
  projects: "/admin/projects",
  meeting: "/admin/meeting",
  meetings: "/admin/meetings",
  retainer: "/admin/retainers",
  clients: "/admin/clients",
  copilot: "/admin/copilot",
  operations: "/admin/operations",
  siem: "/admin/siem",
  messages: "/admin/messages",
  // Sub-atom 1.D.E v3.11 · /admin/mcps SIDEBAR GLOBAL eliminado · R23
  // sostener firmísimo (directiva Marcos 20 May 2026). MCPs accionables
  // SOLO project-scoped via /admin/projects/[id]/mcps/. ProjectTabs
  // entry "Pentest MCPs" Shield icon SUB_TABS.
  settings: "/admin/settings",
  notifications: "/admin/notifications",
  finance: "/admin/finance",
  retainersChurnRisk: "/admin/retainers/churn-risk",
  // Sub-atom Sesión 3B-1 Phase B.3 · compliance landing dashboard
  // (consolidation Option B · sub-portales bajo /admin/compliance/*).
  // MB-9.bis self-compliance dashboards (voluntary access · NO-BLOCKER pattern).
  compliance: "/admin/compliance",
  complianceMonitor: "/admin/compliance/monitor",
  complianceProjects: "/admin/compliance/projects",
  complianceNormaReports: "/admin/compliance/norma-reports",
} as const;

export const CSRF_HEADER = "X-CSRF-Token";
export const CSRF_COOKIE = "fulkro_csrf";
export const SESSION_COOKIE = "fulkro_session";
