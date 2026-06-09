/**
 * Helper E2E Playwright · captured emails mock backend.
 *
 * SAN-E v3.MB-5.3.D · primer fixture reusable atoms 5.4-5.10 + MB-15.
 *
 * Usage:
 *
 *     import { test, expect } from "@playwright/test";
 *     import { resetCapturedEmails, waitForOtp } from "./_helpers/email-mock";
 *
 *     test.beforeEach(async ({ request }) => {
 *       await resetCapturedEmails(request);
 *     });
 *
 *     test("firma con OTP", async ({ page, request }) => {
 *       // ... trigger flow que envía OTP ...
 *       const otp = await waitForOtp(request, "user@test.es");
 *       await page.getByLabel(/codigo/i).fill(otp);
 *     });
 *
 * Backend endpoints requeridos (env-gated NO production):
 *   - DELETE /api/v1/_dev/captured-emails
 *   - GET    /api/v1/_dev/captured-emails?to=&subject_pattern=
 *   - GET    /api/v1/_dev/captured-emails/wait-for-otp?to=&timeout_seconds=
 */
import type { APIRequestContext } from "@playwright/test";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";


export interface CapturedEmail {
  to: string;
  subject: string;
  html_body: string;
  message_id: string;
  captured_at: string;
}


export async function resetCapturedEmails(
  request: APIRequestContext,
): Promise<void> {
  const res = await request.delete(`${BACKEND_BASE}/api/v1/_dev/captured-emails`);
  if (!res.ok()) {
    throw new Error(
      `_dev/captured-emails DELETE devolvio ${res.status()}. Backend running?`,
    );
  }
}


export async function getCapturedEmails(
  request: APIRequestContext,
  filters: { to?: string; subjectPattern?: string } = {},
): Promise<CapturedEmail[]> {
  const params = new URLSearchParams();
  if (filters.to) params.append("to", filters.to);
  if (filters.subjectPattern) params.append("subject_pattern", filters.subjectPattern);
  const qs = params.toString();
  const path = `${BACKEND_BASE}/api/v1/_dev/captured-emails${qs ? `?${qs}` : ""}`;
  const res = await request.get(path);
  if (!res.ok()) {
    throw new Error(
      `_dev/captured-emails GET devolvio ${res.status()}. Backend running?`,
    );
  }
  const body = (await res.json()) as { captured: CapturedEmail[] };
  return body.captured;
}


export async function waitForOtp(
  request: APIRequestContext,
  toEmail: string,
  timeoutSeconds = 10,
): Promise<string> {
  const path =
    `${BACKEND_BASE}/api/v1/_dev/captured-emails/wait-for-otp` +
    `?to=${encodeURIComponent(toEmail)}` +
    `&timeout_seconds=${timeoutSeconds}`;
  const res = await request.get(path);
  if (!res.ok()) {
    throw new Error(
      `OTP no recibido para ${toEmail} en ${timeoutSeconds}s ` +
        `(${res.status()})`,
    );
  }
  const body = (await res.json()) as { otp_code: string };
  return body.otp_code;
}
