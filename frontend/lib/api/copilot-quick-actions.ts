export interface QuickAction {
  id: string;
  label: string;
  icon: string;
  prefill_query: string;
}

export async function fetchQuickActions(
  context?: string,
  projectId?: string,
  signal?: AbortSignal,
): Promise<QuickAction[]> {
  const params = new URLSearchParams();
  if (context) params.set("context", context);
  if (projectId) params.set("project_id", projectId);
  const qs = params.toString();
  const url = `/api/v1/copilot/quick-actions${qs ? `?${qs}` : ""}`;
  try {
    const r = await fetch(url, { credentials: "include", signal });
    if (!r.ok) return [];
    return (await r.json()) as QuickAction[];
  } catch {
    return [];
  }
}
