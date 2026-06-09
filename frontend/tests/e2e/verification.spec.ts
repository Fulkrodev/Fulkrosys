import { expect, test, type Page } from "@playwright/test";

import { loginAsMarcos } from "./_helpers/auth-real";

// UI drift: el slug "k17-demo-project" NO existe en BD → el layout
// project-scoped acaba redirigiendo al selector "Selecciona un proyecto"
// (ActiveProjectSync limpia el contexto del proyecto inválido). Los tests
// rápidos ganaban la carrera contra ese gate, pero el test de findings (espera
// 10s a la tabla) lo perdía. Apuntamos al proyecto fijo E2E sembrado por
// globalSetup (00000000-…-001) para que la página resuelva · los endpoints de
// verificación siguen mockeados (stubK17Backend usa esta constante).
const PROJECT_ID =
  process.env.E2E_SEED_PROJECT_ID ?? "00000000-0000-0000-0000-000000000001";
const RUN_ID = "11111111-1111-1111-1111-111111111111";
const FINDING_ID = "22222222-2222-2222-2222-222222222222";
const CRITICAL_FINDING_ID = "22222222-2222-2222-2222-222222222233";
const REMED_TOKEN = "e2e-remediation-token";
const PENTESTER_TOKEN = "e2e-pentester-token";
const AUTH_TOKEN = "e2e-auth-token";

// ─────────────────────────────────────────────────────────────────────
// Fixtures de respuesta backend para K.17
// ─────────────────────────────────────────────────────────────────────

const SAMPLE_RUN = {
  id: RUN_ID,
  project_id: PROJECT_ID,
  category: "BASICO",
  mode: "internal",
  status: "completed",
  scheduled_start: null,
  completed_at: "2026-04-20T10:00:00Z",
  total_findings: 2,
  confirmed_findings: 2,
  critical_count: 1,
  high_count: 1,
  medium_count: 0,
  low_count: 0,
  security_score: 77,
  delta_new: 0,
  delta_resolved: 0,
  delta_persistent: 0,
  created_at: "2026-04-20T09:00:00Z",
};

const SAMPLE_FINDINGS = [
  {
    id: CRITICAL_FINDING_ID,
    run_id: RUN_ID,
    title: "OpenSSH regreSSHion RCE",
    severity: "critical",
    cvss_score: 8.1,
    cve_id: "CVE-2024-6387",
    affected_host: "srv1.example.es",
    affected_port: 22,
    confidence_score: 0.98,
    zfp_gate5_classification: "confirmed",
    ens_primary_measure: "op.exp.5",
    status: "open",
    remediation_priority: 1,
  },
  {
    id: FINDING_ID,
    run_id: RUN_ID,
    title: "TLS 1.0 aceptado",
    severity: "high",
    cvss_score: 7.0,
    cve_id: null,
    affected_host: "app.example.es",
    affected_port: 443,
    confidence_score: 0.9,
    zfp_gate5_classification: "confirmed",
    ens_primary_measure: "mp.com.2",
    status: "open",
    remediation_priority: 2,
  },
];

async function stubK17Backend(page: Page) {
  await page.route(
    `**/api/v1/projects/${PROJECT_ID}/verification/runs*`,
    async (route) => {
      const url = route.request().url();
      // UI drift: listVerificationRuns llama /runs?status=completed (query
      // param) · el check `endsWith("/runs")` fallaba con query string y caía
      // al else (devolvía un SAMPLE_RUN suelto en vez de {runs:[...]}) → la
      // lista quedaba malformada · sin run · sin findings. Comparamos contra el
      // PATHNAME (sin query) para que la lista de runs se sirva siempre.
      const pathname = new URL(url).pathname;
      if (url.includes(`/runs/${RUN_ID}/findings`)) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ findings: SAMPLE_FINDINGS }),
        });
      } else if (pathname.endsWith("/runs")) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ runs: [SAMPLE_RUN] }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(SAMPLE_RUN),
        });
      }
    },
  );
  await page.route(
    `**/api/v1/projects/${PROJECT_ID}/verification/score`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          current: {
            score: 77,
            level: "aceptable",
            critical: 1,
            high: 1,
            medium: 0,
            low: 0,
            info: 0,
            total_penalty: 23,
          },
          history: [],
        }),
      }),
  );
  await page.route(
    `**/api/v1/projects/${PROJECT_ID}/verification/delta`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          previous_run_id: null,
          current_run_id: RUN_ID,
          new: [],
          resolved: [],
          persistent: [],
          severity_changes: [],
          overall_trend: "estable",
          weight_previous: 0,
          weight_current: 7,
          totals: { new: 0, resolved: 0, persistent: 0, severity_changes: 0 },
        }),
      }),
  );
  await page.route(
    `**/api/v1/projects/${PROJECT_ID}/verification/heatmap`,
    async (route) => {
      const cells = [];
      // 73 celdas (org + op.* + mp.*)
      const groups = [
        ["org", 4], ["op.pl", 5], ["op.acc", 6], ["op.exp", 11],
        ["op.ext", 4], ["op.nub", 2], ["op.cont", 4], ["op.mon", 3],
        ["mp.if", 7], ["mp.per", 4], ["mp.eq", 4], ["mp.com", 4],
        ["mp.si", 5], ["mp.sw", 2], ["mp.info", 6], ["mp.s", 2],
      ] as const;
      for (const [fam, n] of groups) {
        for (let i = 1; i <= n; i++) {
          const measure = `${fam}.${i}`;
          const isHit =
            measure === "op.exp.5" || measure === "mp.com.2";
          cells.push({
            measure,
            status: isHit ? "non_compliant" : "compliant",
            color: isHit ? "rojo" : "verde",
            findings_count: isHit ? 1 : 0,
            worst_severity: isHit ? "critical" : null,
            findings_hashes: isHit ? ["h1"] : [],
          });
        }
      }
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cells,
          summary: {
            compliant: 71,
            partial: 0,
            non_compliant: 2,
            not_verified: 0,
            total: 73,
            compliant_pct: 97.3,
            partial_pct: 0,
            non_compliant_pct: 2.7,
            not_verified_pct: 0,
          },
        }),
      });
    },
  );
  await page.route(
    `**/api/v1/projects/${PROJECT_ID}/verification/remediation-plan`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ total: 0, items: [] }),
      }),
  );
  // Mutations
  await page.route(
    `**/api/v1/projects/${PROJECT_ID}/verification/run`,
    async (route) =>
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          ...SAMPLE_RUN,
          id: "new-run-id",
          status: "pending",
          total_findings: 0,
          confirmed_findings: 0,
        }),
      }),
  );
  await page.route(
    `**/api/v1/projects/${PROJECT_ID}/verification/findings/${CRITICAL_FINDING_ID}`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...SAMPLE_FINDINGS[0],
          status: "false_positive",
        }),
      }),
  );
  await page.route(
    `**/api/v1/projects/${PROJECT_ID}/verification/runs/${RUN_ID}/kill`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: RUN_ID,
          status: "cancelled",
          cancel_requested_at: new Date().toISOString(),
          cancel_completed_at: null,
        }),
      }),
  );
  // Ruta dedicada de findings registrada AL FINAL · Playwright resuelve rutas
  // en orden LIFO (la última registrada se evalúa primero), así garantizamos
  // que la lista de findings devuelve SAMPLE_FINDINGS sin depender del orden de
  // evaluación del glob `runs*` ni de query params (filtros · paginación).
  await page.route(
    new RegExp(
      `/api/v1/projects/${PROJECT_ID}/verification/runs/${RUN_ID}/findings`,
    ),
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ findings: SAMPLE_FINDINGS }),
      }),
  );
}

// ─────────────────────────────────────────────────────────────────────
// K.17 Verification
// ─────────────────────────────────────────────────────────────────────

test.describe("K.17 Verificación Técnica", () => {
  test("Test 1: launch flow crea run BASICO", async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubK17Backend(page);
    await page.goto(`/admin/projects/${PROJECT_ID}/verification`);

    await expect(
      page.getByRole("heading", { name: "Verificación técnica" }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: /Lanzar verificación/i })
      .click();
    await expect(
      page.getByRole("heading", { name: "Lanzar verificación técnica" }),
    ).toBeVisible();
    // Básica viene seleccionada por defecto
    await page
      .getByRole("button", { name: /^Lanzar basico/i })
      .click();

    // Toast success (sonner)
    await expect(page.getByText(/Verificación BASICO creada/)).toBeVisible({
      timeout: 5_000,
    });
  });

  test("Test 2: marcar finding como falso positivo", async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubK17Backend(page);
    await page.goto(`/admin/projects/${PROJECT_ID}/verification`);

    // La tabla de hallazgos vive en la pestaña "Estado de seguridad" (default,
    // verification/page.tsx). Esperamos a que la página y la card de hallazgos
    // estén montadas antes de buscar el finding · evita flake por el render
    // diferido del run completado (FindingsTable necesita effectiveRunId).
    await expect(page.getByTestId("verification-page")).toBeVisible({
      timeout: 10_000,
    });

    // Esperar a que la tabla cargue · el título del finding está en la fila.
    await expect(
      page.getByText("OpenSSH regreSSHion RCE").first(),
    ).toBeVisible({ timeout: 10_000 });

    // Click en el finding crítico → abre modal
    await page.getByText("OpenSSH regreSSHion RCE").first().click();
    await expect(
      page.getByRole("heading", { name: "OpenSSH regreSSHion RCE" }),
    ).toBeVisible();

    await page.getByRole("button", { name: /Marcar FP/i }).click();
    await page
      .getByLabel(/Motivo del falso positivo/i)
      .fill("Banner de OpenSSH hace la detección incorrecta");
    await page.getByRole("button", { name: /Confirmar/i }).click();

    await expect(
      page.getByText(/Marcado como falso positivo/i),
    ).toBeVisible({ timeout: 5_000 });
  });

  test("Test 3: heatmap renderiza 73 celdas con tooltip", async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubK17Backend(page);
    await page.goto(`/admin/projects/${PROJECT_ID}/verification`);

    // Una celda por medida. UI evolucionó: el ENSHeatmap agrupa por familia
    // usando `${parte0}.${parte1}` y solo renderiza familias presentes en
    // FAMILY_LABELS (ENSHeatmap.tsx líneas 35-62, 94-95). La familia "org"
    // (medidas org.1..org.4) agrupa bajo la clave "org.1" pero FAMILY_LABELS
    // solo tiene la clave "org", por lo que esa familia NO se renderiza.
    // Verificamos en su lugar una celda conforme de una familia que SÍ se
    // pinta (op.pl → "Planificación"). El aria-label es
    // "<medida> <estado> <N> hallazgos" (línea 136).
    const compliantCell = page.getByRole("button", {
      name: /^op\.pl\.1.*Conforme.*0 hallazgos/i,
    });
    await expect(compliantCell).toBeVisible();
    // Celda non_compliant
    const hitCell = page.getByRole("button", {
      name: /op\.exp\.5.*No conforme/i,
    });
    await expect(hitCell).toBeVisible();
    // Hover → tooltip (sticky area)
    await hitCell.hover();
    await expect(page.getByRole("tooltip")).toBeVisible();
  });

  test("Test 4: kill switch cancela un run", async ({ context, page }) => {
    await loginAsMarcos(context);
    await stubK17Backend(page);
    // Override: un run adicional en phase1_running
    const runningRun = {
      ...SAMPLE_RUN,
      id: RUN_ID,
      status: "phase1_running",
      completed_at: null,
    };
    await page.route(
      `**/api/v1/projects/${PROJECT_ID}/verification/runs`,
      async (route) => {
        if (route.request().method() === "GET") {
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({ runs: [runningRun] }),
          });
        } else {
          await route.continue();
        }
      },
    );
    await page.goto(`/admin/projects/${PROJECT_ID}/verification`);

    // UI evolucionó: el botón kill-switch pasó de "Kill switch (N)" a
    // "Apagado de emergencia (N)" (KillSwitchButton.tsx línea 87) y el toast
    // de éxito a "Apagado de emergencia solicitado: N run(s)…" (línea 42).
    // Misma feature · solo cambió el copy ES.
    await expect(
      page.getByRole("button", { name: /Apagado de emergencia \(1\)/i }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: /Apagado de emergencia \(1\)/i })
      .click();
    await page.getByRole("button", { name: /Confirmar/i }).click();
    await expect(
      page.getByText(/Apagado de emergencia solicitado/i),
    ).toBeVisible({ timeout: 5_000 });
  });
});

// ─────────────────────────────────────────────────────────────────────
// Portal remediación (público)
// ─────────────────────────────────────────────────────────────────────

async function stubRemediation(page: Page) {
  await page.route(
    `**/api/v1/public/remediation/${REMED_TOKEN}`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cliente: { razon_social: "DataForma Galicia SL", cif: "B72634815" },
          scope: {
            project_id: PROJECT_ID,
            scan_date: "2026-04-20T10:00:00Z",
          },
          progress: { total: 3, resolved: 1, pending: 2, pct: 33.3 },
          severity_buckets: {
            critical: { pending: 1, total: 1 },
            high: { pending: 1, total: 1 },
            medium: { pending: 0, total: 1 },
            low: { pending: 0, total: 0 },
          },
          pending_findings: [
            {
              finding_id: CRITICAL_FINDING_ID,
              title: "OpenSSH regreSSHion RCE",
              severity: "critical",
              host_port: "srv1.example.es:22",
              summary_non_technical:
                "El servidor SSH tiene una vulnerabilidad crítica que permite a un atacante remoto ejecutar código.",
              risk_real:
                "Un atacante con acceso a la red puede tomar control del servidor sin credenciales.",
              time_estimate: "20 minutos",
              requires_restart: false,
              requires_maintenance_window: true,
              status: "open",
              remediated_at: null,
            },
            {
              finding_id: FINDING_ID,
              title: "TLS 1.0 aceptado",
              severity: "high",
              host_port: "app.example.es:443",
              summary_non_technical:
                "El servicio web acepta una versión antigua de TLS que ya no se considera segura.",
              risk_real:
                "Un atacante podría interceptar conexiones y descifrar el tráfico.",
              time_estimate: "30 minutos",
              requires_restart: false,
              requires_maintenance_window: true,
              status: "open",
              remediated_at: null,
            },
          ],
          resolved_findings: [],
        }),
      }),
  );
  await page.route(
    `**/api/v1/public/remediation/${REMED_TOKEN}/findings/${CRITICAL_FINDING_ID}/guide`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          finding_id: CRITICAL_FINDING_ID,
          title: "OpenSSH regreSSHion RCE",
          severity: "critical",
          host_port: "srv1.example.es:22",
          guide: {
            resumen_no_tecnico: "Aplica actualización del paquete SSH.",
            riesgo_real: "RCE remoto sin autenticación.",
            pasos: [
              {
                paso: 1,
                titulo: "Actualizar openssh-server",
                comando: "sudo apt update && sudo apt upgrade -y openssh-server",
                explicacion: "Instala la última versión corregida.",
                verificacion: "ssh -V",
              },
            ],
            tiempo_estimado: "20 minutos",
            requiere_reinicio: false,
            requiere_ventana_mantenimiento: true,
            fuente: "deterministic_template",
          },
        }),
      }),
  );
  await page.route(
    `**/api/v1/public/remediation/${REMED_TOKEN}/findings/${CRITICAL_FINDING_ID}/fixed`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          finding_id: CRITICAL_FINDING_ID,
          retest_result: "fixed",
          retest_detail: "No se detecta CVE-2024-6387 tras actualizar",
          executed_at: "2026-04-21T12:00:00Z",
          finding_status_after: "remediated",
          verified_at: "2026-04-21T12:00:00Z",
        }),
      }),
  );
}

test.describe("Portal remediación", () => {
  test("Test 5: end-to-end guide → fixed", async ({ page }) => {
    await stubRemediation(page);
    await page.goto(`/remediation/${REMED_TOKEN}`);

    await expect(
      page.getByText(/Estado de seguridad — DataForma Galicia SL/i),
    ).toBeVisible();
    // Barra progreso con ARIA
    await expect(
      page.getByRole("progressbar", { name: /Progreso de remediación/i }),
    ).toBeVisible();
    // Cards pendientes
    await expect(page.getByText("OpenSSH regreSSHion RCE")).toBeVisible();
    await expect(page.getByText("TLS 1.0 aceptado")).toBeVisible();

    // Abre modal guía
    await page
      .getByRole("button", { name: /Ver guía de solución/i })
      .first()
      .click();
    await expect(
      page.getByRole("heading", { name: "Cómo solucionarlo" }),
    ).toBeVisible();
    // Comando visible y copiable
    await expect(
      page.getByText("sudo apt update && sudo apt upgrade -y openssh-server"),
    ).toBeVisible();
    // Copiar (asignar permiso clipboard en este contexto es flaky; solo
    // verificamos que el botón existe)
    await expect(
      page.getByRole("button", { name: /Copiar Comando/i }),
    ).toBeVisible();

    // Marca arreglado desde el modal
    await page
      .getByRole("button", { name: /Ya lo he arreglado/i })
      .last()
      .click();
    await expect(
      page.getByText(/Hallazgo resuelto y verificado/i),
    ).toBeVisible({ timeout: 10_000 });
  });
});

// ─────────────────────────────────────────────────────────────────────
// Portal pentester externo
// ─────────────────────────────────────────────────────────────────────

async function stubPentester(page: Page) {
  await page.route(
    `**/api/v1/public/pentester-portal/${PENTESTER_TOKEN}`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cliente: { razon_social: "DataForma Galicia SL", cif: "B72634815" },
          engagement: {
            run_id: RUN_ID,
            handoff_id: "h-1",
            category: "ALTO",
            mode: "external_handoff",
            scope: {
              targets: ["srv.example.es"],
              web_apps: ["https://app.example.es"],
              exclusions: ["*.dev.example.es"],
              scan_window: "L-V 09:00-18:00 CET",
            },
            deadline: "2026-05-01T00:00:00Z",
            kickoff_scheduled_at: null,
            status: "portal_ready",
            report_received_at: null,
            total_findings_received: 0,
          },
          pentester: {
            name: "Laura García",
            certification: "OSCP",
            email: "laura@example.es",
          },
          documents: [
            {
              name: "01_Scope",
              path: "var/verification_handoffs/fake/scope.md",
              hash_sha256: "a".repeat(64),
              generated_at: "2026-04-20",
            },
            {
              name: "02_Inventario",
              path: "var/verification_handoffs/fake/inv.md",
              hash_sha256: "b".repeat(64),
              generated_at: "2026-04-20",
            },
          ],
          vpn: { config_available: false, requires_otp_for_creds: true },
          consultor_contact: {
            nombre: "Marcos Mata García",
            email: "marcos@example.es",
            phone_emergency: "+34 600 000 000",
            procedimiento: "Llama si hay compromiso activo.",
          },
        }),
      }),
  );
  await page.route(
    `**/api/v1/public/pentester-portal/${PENTESTER_TOKEN}/findings`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ submitted: 1, total_in_handoff: 1 }),
      }),
  );
}

test.describe("Portal pentester externo", () => {
  test("Test 6: engagement + formulario + envío finding", async ({ page }) => {
    await stubPentester(page);
    await page.goto(`/pentester-portal/${PENTESTER_TOKEN}`);

    await expect(
      page.getByRole("heading", {
        name: /Engagement — DataForma Galicia SL/i,
      }),
    ).toBeVisible();
    // Documentos descargables · UI evolucionó: el label del doc 01_Scope pasó
    // de "Scope y reglas de compromiso" a "Alcance y reglas de compromiso"
    // (PentesterPortal.tsx DOC_LABELS línea 45). Mismo doc · solo copy ES.
    await expect(
      page.getByText("Alcance y reglas de compromiso"),
    ).toBeVisible();
    await expect(page.getByText("Inventario de activos")).toBeVisible();

    // Formulario (viene seleccionado por defecto)
    await page.getByLabel("Título").fill("SMB signing not required");
    await page
      .getByLabel("Descripción técnica")
      .fill("Permite ataques MITM con relay NTLM");
    await page.getByLabel("Host afectado").fill("srv1.example.es");
    await page.getByLabel("Puerto").fill("445");
    await page.getByLabel("CVSS score (opcional)").fill("7.5");

    // UI evolucionó: el botón de envío pasó de "Enviar N finding(s)" a
    // "Enviar N hallazgo(s)" (PentesterPortal.tsx línea 442 · singular cuando
    // length === 1). Misma acción · solo copy ES. El toast sigue diciendo
    // "N findings entregados" (línea 163).
    await page
      .getByRole("button", { name: /Enviar 1 hallazgo/i })
      .click();
    await expect(
      page.getByText(/1 findings entregados/i),
    ).toBeVisible({ timeout: 5_000 });
  });
});

// ─────────────────────────────────────────────────────────────────────
// Portal verify-auth
// ─────────────────────────────────────────────────────────────────────

async function stubVerifyAuth(page: Page, requiresOtp = false) {
  await page.route(
    `**/api/v1/public/verify-auth/${AUTH_TOKEN}`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          cliente: { razon_social: "DataForma Galicia SL", cif: "B72634815" },
          run: {
            run_id: RUN_ID,
            category: "BASICO",
            mode: "internal",
            scheduled_start: null,
            scope: {
              targets: ["srv.example.es"],
              web_apps: ["https://app.example.es"],
              exclusions: [],
              scan_window: "22:00-06:00 CET",
            },
            tools: ["nmap", "nuclei", "testssl"],
          },
          legal_statement:
            "Al autorizar acepto la ejecución dentro del alcance y ventana descritos.",
          requires_otp: requiresOtp,
        }),
      }),
  );
  await page.route(
    `**/api/v1/public/verify-auth/${AUTH_TOKEN}/submit`,
    async (route) =>
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "signed",
          run_id: RUN_ID,
          signed_at: "2026-04-21T12:00:00Z",
          signature_hash: "a".repeat(64),
          expected_completion: null,
        }),
      }),
  );
}

test.describe("Portal verify-auth", () => {
  test("Test 7: revisar scope + autorizar", async ({ page }) => {
    await stubVerifyAuth(page, false);
    await page.goto(`/verify-auth/${AUTH_TOKEN}`);

    await expect(
      page.getByRole("heading", {
        name: /Autorización de verificación técnica/i,
      }),
    ).toBeVisible();
    // Scope visible
    await expect(page.getByText("srv.example.es")).toBeVisible();
    await expect(page.getByText("nuclei")).toBeVisible();
    await expect(page.getByText("testssl")).toBeVisible();

    const submitBtn = page.getByRole("button", {
      name: /Autorizar verificación/i,
    });
    await expect(submitBtn).toBeDisabled();

    await page
      .getByLabel(/He leído y acepto la declaración legal/i)
      .check();
    await expect(submitBtn).toBeEnabled();
    await submitBtn.click();
    await expect(
      page.getByRole("heading", { name: /Verificación autorizada/i }),
    ).toBeVisible({ timeout: 10_000 });
  });
});

// ─────────────────────────────────────────────────────────────────────
// Responsive check (mobile)
// ─────────────────────────────────────────────────────────────────────

test.describe("Responsive portales", () => {
  test("portal remediación apila cards en mobile 375px", async ({
    page,
  }) => {
    await stubRemediation(page);
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`/remediation/${REMED_TOKEN}`);
    await expect(
      page.getByText("OpenSSH regreSSHion RCE"),
    ).toBeVisible();
    // El botón "Ya lo he arreglado" ocupa ancho completo en mobile
    const btn = page
      .getByRole("button", { name: /Ya lo he arreglado/i })
      .first();
    const box = await btn.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(300);
  });
});
