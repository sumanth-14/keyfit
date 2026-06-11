import { decryptNimKey, encryptNimKey } from "@/lib/crypto/keyStore";
import { getNimKeyBlob, putNimKeyBlob } from "@/lib/api/settings";

/** Encrypt the NIM key client-side and persist the blob to the user's Drive. */
export async function saveNimKey(
  accessToken: string,
  email: string,
  plaintext: string,
): Promise<void> {
  const blob = await encryptNimKey(plaintext, email);
  await putNimKeyBlob(accessToken, blob);
}

/** Fetch the stored blob and decrypt it. Returns null if absent or undecryptable. */
export async function loadNimKey(
  accessToken: string,
  email: string,
): Promise<string | null> {
  const res = await getNimKeyBlob(accessToken);
  if (!res.exists || !res.blob) return null;
  try {
    return await decryptNimKey(res.blob, email);
  } catch {
    return null; // wrong email or corrupt blob
  }
}
