/**
 * CLUSTER 6 Phase 6A · TOTP enrollment helper.
 *
 * Provides formatting helpers for displaying the TOTP secret in a way
 * suitable for manual entry into authenticator apps (Google Authenticator,
 * Authy, 1Password). QR rendering is intentionally NOT implemented locally
 * to keep the bundle small and avoid a custom QR encoder edge cases (see
 * `Future-1.E.mfa.qr-render-package` for the npm route).
 *
 * Manual entry is supported by all modern authenticator apps and is the
 * canonical fallback path when QR scanning isn't available.
 */

/**
 * Splits the TOTP secret into groups of 4 chars uppercase for legible
 * manual entry (e.g. ``ABCD EFGH IJKL MNOP``).
 */
export function formatSecretForManualEntry(secret: string): string {
  const upper = secret.toUpperCase().replace(/\s+/g, "");
  return upper.match(/.{1,4}/g)?.join(" ") ?? upper;
}

/**
 * Returns a public QR image URL for the otpauth:// URI · uses qrserver.com
 * (free public service · no auth · stable). Caller can render via
 * <img src={qrImageUrl(uri)} />.
 *
 * Note: otpauth URIs contain the secret in plaintext · the same applies
 * to manual entry · this is by design (the secret is shared with the user).
 * Network egress to qrserver.com is acceptable in cliente browser context.
 */
export function qrImageUrl(otpauthUri: string, size = 220): string {
  const params = new URLSearchParams({
    size: `${size}x${size}`,
    data: otpauthUri,
    ecc: "M",
  });
  return `https://api.qrserver.com/v1/create-qr-code/?${params.toString()}`;
}
