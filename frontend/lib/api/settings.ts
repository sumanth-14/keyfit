import { apiFetch } from "./client";
import type { EncryptedKeyBlob } from "@/lib/crypto/keyStore";

export interface NimKeyGetResponse {
  exists: boolean;
  blob: EncryptedKeyBlob | null;
}

export async function getNimKeyBlob(
  accessToken: string,
): Promise<NimKeyGetResponse> {
  return apiFetch<NimKeyGetResponse>("/api/settings/nim-key", { accessToken });
}

export async function putNimKeyBlob(
  accessToken: string,
  blob: EncryptedKeyBlob,
): Promise<{ saved: boolean }> {
  return apiFetch<{ saved: boolean }>("/api/settings/nim-key", {
    accessToken,
    method: "PUT",
    body: blob,
  });
}
