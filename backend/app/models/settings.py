from pydantic import BaseModel


class EncryptedKeyBlob(BaseModel):
    """An opaque, client-encrypted secret. The backend never sees the plaintext —
    it only stores and returns this blob (Rule 2). Encrypted with AES-GCM; the
    fields below are base64-encoded by the client (Web Crypto)."""

    ciphertext: str
    iv: str
    salt: str
    version: int = 1


class NimKeyGetResponse(BaseModel):
    exists: bool
    blob: EncryptedKeyBlob | None = None


class NimKeyPutResponse(BaseModel):
    saved: bool
