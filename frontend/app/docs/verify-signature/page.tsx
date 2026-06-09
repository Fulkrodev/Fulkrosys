/**
 * /docs/verify-signature · página doc cómo verificar firmas FULKRO Ed25519.
 *
 * SAN-B.MB-7.5 · acompaña PublicKeyVerifier · explicación auditor externo
 * sin acceso al sistema. 3 caminos: openssl CLI · python · API
 * /verify-signature endpoint.
 */
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Verificar firma FULKRO Ed25519 · Documentación",
  description:
    "Cómo verificar las firmas Ed25519 que FULKRO aplica a documentos, evidence y backups. Tres caminos: openssl, python, API verify-signature.",
};

export default function VerifySignatureDocsPage() {
  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-8">
      <header className="mb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-fulkro-title">
          Verificar firmas FULKRO Ed25519
        </h1>
        <p className="mt-2 text-sm text-fulkro-muted">
          FULKRO firma documentos legales (M14 contracts), archivos de
          evidence (M07), dossiers de cierre (M25) y backups (M26) con
          Ed25519. Esta página describe tres formas de verificar una firma
          sin acceso al sistema FULKRO.
        </p>
      </header>

      <section className="space-y-6 text-sm leading-relaxed text-fulkro-ink-700">
        <article>
          <h2 className="mb-2 text-lg font-semibold">1. Descargar la clave pública</h2>
          <p>
            Antes de verificar, descarga la clave pública FULKRO desde el portal
            cliente <code>/client-portal/firma</code> (botón &quot;Descargar .pem&quot;)
            o vía API pública sin autenticación:
          </p>
          <pre className="mt-2 overflow-x-auto rounded-md border bg-fulkro-ink-100/40 p-3 text-xs">
{`curl https://app.fulkro.es/api/v1/auth/public-key \\
  -o fulkro-public-key.json
# Extrae el campo "public_key" como fulkro-public-key.pem`}
          </pre>
        </article>

        <article>
          <h2 className="mb-2 text-lg font-semibold">2. Verificar con openssl (recomendado auditor)</h2>
          <pre className="mt-2 overflow-x-auto rounded-md border bg-fulkro-ink-100/40 p-3 text-xs">
{`# payload.bin = el documento original (PDF, ZIP, etc)
# signature.bin = bytes binarios de la firma Ed25519 (decodificada de base64)
openssl pkeyutl -verify \\
  -pubin -inkey fulkro-public-key.pem \\
  -rawin -in payload.bin \\
  -sigfile signature.bin
# Output esperado: "Signature Verified Successfully"`}
          </pre>
        </article>

        <article>
          <h2 className="mb-2 text-lg font-semibold">3. Verificar con Python (cryptography)</h2>
          <pre className="mt-2 overflow-x-auto rounded-md border bg-fulkro-ink-100/40 p-3 text-xs">
{`from cryptography.hazmat.primitives import serialization

with open("fulkro-public-key.pem", "rb") as f:
    public_key = serialization.load_pem_public_key(f.read())

with open("payload.bin", "rb") as f:
    payload = f.read()
with open("signature.bin", "rb") as f:
    signature = f.read()

try:
    public_key.verify(signature, payload)
    print("Firma válida")
except Exception as exc:
    print(f"Firma inválida: {exc}")`}
          </pre>
        </article>

        <article>
          <h2 className="mb-2 text-lg font-semibold">4. Verificar vía API (alternativa sin libs)</h2>
          <p>
            Si no tienes <code>openssl</code> ni Python con <code>cryptography</code>,
            FULKRO ofrece un endpoint público (sin auth) que verifica la firma
            directamente:
          </p>
          <pre className="mt-2 overflow-x-auto rounded-md border bg-fulkro-ink-100/40 p-3 text-xs">
{`curl -X POST https://app.fulkro.es/api/v1/auth/verify-signature \\
  -H "Content-Type: application/json" \\
  -d '{
    "payload_b64": "<base64 del documento original>",
    "signature_b64": "<base64 de la firma>"
  }'
# Respuesta: { "valid": true } o { "valid": false }`}
          </pre>
        </article>

        <article className="rounded-md border border-fulkro-ink-300/60 bg-fulkro-ink-100/40 p-4">
          <h3 className="mb-1 text-base font-semibold">Notas</h3>
          <ul className="ml-4 list-disc space-y-1 text-xs text-fulkro-ink-600">
            <li>
              El <strong>algoritmo es Ed25519</strong> (firma digital de curva
              elíptica · estándar IETF RFC 8032).
            </li>
            <li>
              El <strong>formato de la clave es PEM</strong> (texto base64 con
              cabeceras <code>BEGIN PUBLIC KEY</code> / <code>END PUBLIC KEY</code>).
            </li>
            <li>
              El <strong>key_id</strong> mostrado en el portal es un hash SHA-256
              truncado de la clave pública · sirve para confirmar que estás
              usando la misma clave que verificó FULKRO al firmar.
            </li>
            <li>
              Si FULKRO rota la clave en el futuro, el portal cliente actualizará
              la clave pública mostrada y publicará un nuevo key_id.
            </li>
          </ul>
        </article>
      </section>
    </div>
  );
}
