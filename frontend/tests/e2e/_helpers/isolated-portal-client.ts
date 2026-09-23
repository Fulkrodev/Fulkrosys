/**
 * Helper E2E Playwright · cliente de portal AISLADO creado por las APIs admin
 * reales (no por endpoints `_dev`).
 *
 * POR QUÉ: el portal cliente resuelve el proyecto MÁS RECIENTE del cliente
 * (R27 · LIMIT 1 por created_at). El cliente compartido (`B00000000`) estrena
 * proyectos en cuanto otros specs firman contratos, y los clientes dedicados de
 * `_dev` (`_DEDICATED_KEYS`) ya tienen dueño: sembrar ahí categorizaciones o
 * congelar su MAGERIT cambiaría lo que ven esos otros specs. Un spec que depende
 * de QUÉ proyecto ve el cliente necesita su propio cliente.
 *
 * Todo sale del flujo normal de Marcos:
 *   POST /clients                         (get-or-create por CIF)
 *   POST /clients/{id}/projects           (get-or-create por nombre)
 *   POST /projects/{pid}/portal-user      (alta idempotente · contraseña temporal)
 *   POST /client-auth/change-password     (primer acceso · must_change_password)
 *   POST /clients/{id}/users/{uid}/reset-password  (solo si la fija no vale)
 * Idempotente: las re-ejecuciones reutilizan cliente/proyecto/usuario y entran
 * con la contraseña fija que dejó la primera.
 */
import {
  request as pwRequest,
  type APIRequestContext,
  type BrowserContext,
} from "@playwright/test";

const BACKEND_BASE =
  process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";

/** Cumple la política de contraseñas cliente (8-16 · mayús · minús · núm · símbolo). */
const ISOLATED_PASSWORD = "Aislad0-E2e!";

export interface IsolatedPortalClientSpec {
  /** CIF estable (identifica al cliente entre ejecuciones). */
  cif: string;
  nombre: string;
  /** Dominio `.example`: el login cliente valida EmailStr y rechaza `.test`. */
  email: string;
  projectNombre: string;
  categoria: "BASICA" | "MEDIA" | "ALTA";
}

export interface IsolatedPortalClient {
  clientId: string;
  projectId: string;
  email: string;
  password: string;
}

/** Cabecera CSRF de la sesión admin (cookie `fulkro_csrf` no httpOnly). */
export async function adminCsrfHeaders(
  context: BrowserContext,
): Promise<Record<string, string>> {
  const csrf = (await context.cookies()).find(
    (c) => c.name === "fulkro_csrf",
  )?.value;
  if (!csrf) throw new Error("fulkro_csrf ausente · ¿loginAsMarcos ejecutado?");
  return { "x-csrf-token": csrf };
}

async function ok<T>(
  res: Awaited<ReturnType<APIRequestContext["get"]>>,
  what: string,
): Promise<T> {
  if (!res.ok()) {
    throw new Error(`${what} devolvió ${res.status()} :: ${await res.text()}`);
  }
  return (await res.json()) as T;
}

/**
 * Asegura cliente + proyecto + usuario de portal aislados y deja la contraseña
 * del usuario en un valor conocido. `adminContext` debe venir de loginAsMarcos.
 */
export async function ensureIsolatedPortalClient(
  adminContext: BrowserContext,
  spec: IsolatedPortalClientSpec,
): Promise<IsolatedPortalClient> {
  const api = adminContext.request;
  const headers = await adminCsrfHeaders(adminContext);
  const base = `${BACKEND_BASE}/api/v1`;

  // 1 · Cliente (get-or-create por CIF · el POST da 409 si ya existe).
  const clients = await ok<Array<{ id: string; cif: string }>>(
    await api.get(`${base}/clients`),
    "GET /clients",
  );
  let clientId = clients.find((c) => c.cif === spec.cif)?.id;
  if (!clientId) {
    clientId = (
      await ok<{ id: string }>(
        await api.post(`${base}/clients`, {
          headers,
          data: { nombre: spec.nombre, cif: spec.cif },
        }),
        "POST /clients",
      )
    ).id;
  }

  // 2 · Proyecto (get-or-create por nombre · el único del cliente).
  const projects = await ok<
    Array<{ id: string; nombre: string; deleted_at: string | null }>
  >(await api.get(`${base}/clients/${clientId}/projects`), "GET projects");
  let projectId = projects.find(
    (p) => p.nombre === spec.projectNombre && !p.deleted_at,
  )?.id;
  if (!projectId) {
    projectId = (
      await ok<{ id: string }>(
        await api.post(`${base}/clients/${clientId}/projects`, {
          headers,
          data: { nombre: spec.projectNombre, categoria_objetivo: spec.categoria },
        }),
        "POST project",
      )
    ).id;
  }

  // 3 · Usuario de portal: el "asegurar usuario" del proyecto (m30, lo que usa
  //     la ficha de contactos) es idempotente y devuelve la contraseña
  //     temporal SOLO si lo acaba de crear.
  const ensured = await ok<{ client_user_id: string; temp_password: string | null }>(
    await api.post(`${base}/projects/${projectId}/portal-user`, {
      headers,
      data: { email: spec.email, full_name: `${spec.nombre} User` },
    }),
    "POST portal-user",
  );

  const clientApi = await pwRequest.newContext();
  try {
    let temp = ensured.temp_password;
    if (!temp) {
      // Ya existía: una ejecución anterior le dejó la contraseña fija.
      const again = await clientApi.post(`${base}/client-auth/login`, {
        data: { email: spec.email, password: ISOLATED_PASSWORD },
      });
      if (again.ok()) {
        return { clientId, projectId, email: spec.email, password: ISOLATED_PASSWORD };
      }
      // Contraseña desconocida (alguien la cambió): Marcos la resetea.
      temp = (
        await ok<{ temp_password: string }>(
          await api.post(
            `${base}/clients/${clientId}/users/${ensured.client_user_id}/reset-password`,
            { headers },
          ),
          "POST reset-password",
        )
      ).temp_password;
    }

    // 4 · Primer acceso: login con la temporal y cambio a la fija
    //     (must_change_password bloquea el portal hasta hacerlo).
    await ok(
      await clientApi.post(`${base}/client-auth/login`, {
        data: { email: spec.email, password: temp },
      }),
      "POST client-auth/login (temporal)",
    );
    const csrf = (await clientApi.storageState()).cookies.find(
      (c) => c.name === "fulkro_csrf",
    )?.value;
    if (!csrf) throw new Error("login cliente sin cookie fulkro_csrf");
    await ok(
      await clientApi.post(`${base}/client-auth/change-password`, {
        headers: { "x-csrf-token": csrf },
        data: { old_password: temp, new_password: ISOLATED_PASSWORD },
      }),
      "POST client-auth/change-password",
    );
  } finally {
    await clientApi.dispose();
  }

  return {
    clientId,
    projectId,
    email: spec.email,
    password: ISOLATED_PASSWORD,
  };
}
