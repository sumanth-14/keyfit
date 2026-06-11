import asyncio
import json
from io import BytesIO

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from google.auth.exceptions import RefreshError, TransportError

from app.config import settings
from app.models.errors import APIError, ErrorCode
from app.utils.logging import get_logger

logger = get_logger(__name__)

_FOLDER_MIME = "application/vnd.google-apps.folder"


class GoogleDriveClient:
    """Async wrapper around the synchronous google-api-python-client Drive v3 service.

    All methods run the underlying sync SDK calls in a thread-pool executor so
    they don't block the asyncio event loop.
    """

    def __init__(self, access_token: str, refresh_token: str | None = None) -> None:
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        # build() fetches the discovery document (network I/O). The caller is
        # responsible for constructing this object inside run_in_executor when
        # event-loop blocking matters (see deps.py).
        try:
            self._svc = build("drive", "v3", credentials=creds, cache_discovery=False)
        except (RefreshError, TransportError) as exc:
            raise APIError(
                ErrorCode.DRIVE_AUTH_EXPIRED,
                "Your Google session has expired. Please sign out and sign in again.",
                retry_possible=False,
                technical_details=str(exc),
            ) from exc

    # ── Internal helper ────────────────────────────────────────────────────────

    async def _run(self, fn):
        """Run a synchronous Drive API .execute() call in the thread pool."""
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, fn)
        except (RefreshError, TransportError) as exc:
            raise APIError(
                ErrorCode.DRIVE_AUTH_EXPIRED,
                "Your Google session has expired. Please sign out and sign in again.",
                retry_possible=False,
                technical_details=str(exc),
            ) from exc

    # ── Folder operations ──────────────────────────────────────────────────────

    async def find_folder(
        self, name: str, parent_id: str | None = None
    ) -> str | None:
        """Return the Drive folder ID matching name, or None if not found."""
        q = f"name='{name}' and mimeType='{_FOLDER_MIME}' and trashed=false"
        if parent_id:
            q += f" and '{parent_id}' in parents"

        result = await self._run(
            self._svc.files()
            .list(q=q, fields="files(id,name)", spaces="drive")
            .execute
        )
        files = result.get("files", [])
        return files[0]["id"] if files else None

    async def create_folder(
        self, name: str, parent_id: str | None = None
    ) -> str:
        """Create a Drive folder and return its ID."""
        metadata: dict = {"name": name, "mimeType": _FOLDER_MIME}
        if parent_id:
            metadata["parents"] = [parent_id]

        result = await self._run(
            self._svc.files().create(body=metadata, fields="id").execute
        )
        folder_id: str = result["id"]
        logger.info(f"Created Drive folder name={name!r} id={folder_id}")
        return folder_id

    async def ensure_folder(
        self, name: str, parent_id: str | None = None
    ) -> tuple[str, bool]:
        """Return (folder_id, was_created). Idempotent — creates only if missing."""
        existing = await self.find_folder(name, parent_id)
        if existing:
            return existing, False
        new_id = await self.create_folder(name, parent_id)
        return new_id, True

    # ── File operations ────────────────────────────────────────────────────────

    async def find_file(
        self, name: str, parent_id: str | None = None
    ) -> str | None:
        """Return the Drive file ID matching name, or None if not found."""
        q = (
            f"name='{name}' and mimeType!='{_FOLDER_MIME}' and trashed=false"
        )
        if parent_id:
            q += f" and '{parent_id}' in parents"

        result = await self._run(
            self._svc.files()
            .list(q=q, fields="files(id,name)", spaces="drive")
            .execute
        )
        files = result.get("files", [])
        return files[0]["id"] if files else None

    async def upload_bytes(
        self,
        name: str,
        content: bytes,
        mime_type: str,
        parent_id: str | None = None,
        existing_file_id: str | None = None,
    ) -> str:
        """Upload or overwrite a file. Returns the Drive file ID."""
        media = MediaIoBaseUpload(BytesIO(content), mimetype=mime_type, resumable=False)

        if existing_file_id:
            result = await self._run(
                self._svc.files()
                .update(fileId=existing_file_id, media_body=media, fields="id")
                .execute
            )
        else:
            metadata: dict = {"name": name}
            if parent_id:
                metadata["parents"] = [parent_id]
            result = await self._run(
                self._svc.files()
                .create(body=metadata, media_body=media, fields="id")
                .execute
            )

        file_id: str = result["id"]
        logger.info(f"Uploaded file name={name!r} id={file_id} bytes={len(content)}")
        return file_id

    async def download_file(self, file_id: str) -> bytes:
        """Download a file's raw bytes by Drive file ID."""
        request = self._svc.files().get_media(fileId=file_id)
        buf = BytesIO()
        downloader = MediaIoBaseDownload(buf, request)

        def _download() -> bytes:
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buf.getvalue()

        return await self._run(_download)

    async def read_json(
        self, name: str, parent_id: str | None = None
    ) -> dict | None:
        """Read a JSON file from Drive. Returns parsed dict or None if not found."""
        file_id = await self.find_file(name, parent_id)
        if not file_id:
            return None
        content = await self.download_file(file_id)
        return json.loads(content.decode("utf-8"))

    async def write_json(
        self, name: str, data: dict, parent_id: str | None = None
    ) -> str:
        """Write a dict as JSON to Drive, creating or overwriting. Returns file ID."""
        content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        existing_id = await self.find_file(name, parent_id)
        return await self.upload_bytes(
            name=name,
            content=content,
            mime_type="application/json",
            parent_id=parent_id,
            existing_file_id=existing_id,
        )

    async def list_files(
        self,
        parent_id: str,
        mime_type: str | None = None,
        fields: str = "files(id,name,modifiedTime)",
    ) -> list[dict]:
        """List files inside a folder, optionally filtered by mime_type."""
        q = f"'{parent_id}' in parents and trashed=false"
        if mime_type:
            q += f" and mimeType='{mime_type}'"

        result = await self._run(
            self._svc.files()
            .list(q=q, fields=fields, spaces="drive")
            .execute
        )
        return result.get("files", [])

    async def delete_file(self, file_id: str) -> bool:
        """Move a file to the Drive trash. Returns True on success."""
        try:
            await self._run(self._svc.files().delete(fileId=file_id).execute)
            return True
        except Exception as exc:
            logger.warning(f"Drive delete failed file_id={file_id}: {exc}")
            return False


async def make_drive_client(
    access_token: str, refresh_token: str | None = None
) -> GoogleDriveClient:
    """Factory that constructs GoogleDriveClient off the event loop.

    build() fetches the discovery document synchronously, so we run it in a
    thread-pool executor to avoid blocking the asyncio event loop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: GoogleDriveClient(access_token, refresh_token),
    )
