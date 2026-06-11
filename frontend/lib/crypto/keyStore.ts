// Client-side encryption for the user's NVIDIA NIM key (Rule 2).
//
// The key is encrypted with AES-GCM before it ever leaves the browser; the
// backend only ever stores/returns the opaque blob. We auto-unlock with no
// passphrase by deriving the AES key from the user's email + a static app
// pepper. That makes this obfuscation-grade at rest — the real access control
// is the user's own Google Drive (drive.file scope), not the passphrase.

const PEPPER = "resume-tailor::nim-key::v1";
const PBKDF2_ITERATIONS = 100_000;

export interface EncryptedKeyBlob {
  ciphertext: string;
  iv: string;
  salt: string;
  version: number;
}

function toB64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
}

function fromB64(s: string): ArrayBuffer {
  return Uint8Array.from(atob(s), (c) => c.charCodeAt(0)).buffer;
}

function randomBuffer(byteLength: number): ArrayBuffer {
  const buf = new ArrayBuffer(byteLength);
  crypto.getRandomValues(new Uint8Array(buf));
  return buf;
}

async function deriveKey(email: string, salt: ArrayBuffer): Promise<CryptoKey> {
  const baseKey = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(`${email.toLowerCase()}::${PEPPER}`),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations: PBKDF2_ITERATIONS, hash: "SHA-256" },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

export async function encryptNimKey(
  plaintext: string,
  email: string,
): Promise<EncryptedKeyBlob> {
  const salt = randomBuffer(16);
  const iv = randomBuffer(12);
  const key = await deriveKey(email, salt);
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    new TextEncoder().encode(plaintext),
  );
  return {
    ciphertext: toB64(ciphertext),
    iv: toB64(iv),
    salt: toB64(salt),
    version: 1,
  };
}

export async function decryptNimKey(
  blob: EncryptedKeyBlob,
  email: string,
): Promise<string> {
  const key = await deriveKey(email, fromB64(blob.salt));
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: fromB64(blob.iv) },
    key,
    fromB64(blob.ciphertext),
  );
  return new TextDecoder().decode(plaintext);
}
