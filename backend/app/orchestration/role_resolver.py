import json
from pathlib import Path

from app.agents.role_config_generator import RoleConfigGeneratorAgent
from app.models.role_config import RoleConfig
from app.services.google_drive import GoogleDriveClient
from app.utils.logging import get_logger

logger = get_logger(__name__)

_BUILTIN_DIR = Path(__file__).parent.parent / "builtin_agents"
_ROLE_CONFIGS_SUBFOLDER = "role_configs"


class RoleResolver:
    """Resolves a role_id to a RoleConfig via three-step lookup (Rule 6).

    1. Built-in codebase configs (`app/builtin_agents/{role_id}.json`)
    2. User's saved auto-generated configs on Drive (`role_configs/{role_id}.json`)
    3. Generate via LLM, save to Drive, return

    The user never sees which path was taken.
    """

    def __init__(
        self,
        drive_client: GoogleDriveClient,
        generator_agent: RoleConfigGeneratorAgent,
        role_configs_folder_id: str,
    ) -> None:
        self.drive = drive_client
        self.generator = generator_agent
        self.role_configs_folder_id = role_configs_folder_id

    async def resolve(self, role_id: str) -> RoleConfig:
        # Step 1: built-in
        builtin_path = _BUILTIN_DIR / f"{role_id}.json"
        if builtin_path.exists():
            data = json.loads(builtin_path.read_text(encoding="utf-8"))
            logger.info(f"RoleResolver: built-in config role_id={role_id}")
            return RoleConfig.model_validate(data)

        # Step 2: user's Drive
        filename = f"{role_id}.json"
        data = await self.drive.read_json(filename, parent_id=self.role_configs_folder_id)
        if data is not None:
            logger.info(f"RoleResolver: Drive config role_id={role_id}")
            return RoleConfig.model_validate(data)

        # Step 3: generate, save, return
        logger.info(f"RoleResolver: generating config role_id={role_id}")
        config = await self.generator.run_and_build(role_id=role_id)
        await self.drive.write_json(
            filename,
            config.model_dump(),
            parent_id=self.role_configs_folder_id,
        )
        return config

    async def list_available(self) -> list[dict]:
        """Return all role IDs and display names visible to the user.

        Combines built-in roles with user's saved auto-generated configs.
        Deduplicates by role_id (built-in wins).
        """
        roles: dict[str, str] = {}

        # Built-in (highest priority)
        for path in sorted(_BUILTIN_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                roles[data["role_id"]] = data["role_display_name"]
            except Exception:
                pass

        # Drive-saved auto-generated
        try:
            files = await self.drive.list_files(
                parent_id=self.role_configs_folder_id,
                mime_type="application/json",
            )
            for f in files:
                if f["name"].endswith(".json"):
                    role_id = f["name"].removesuffix(".json")
                    if role_id not in roles:
                        # Fetch to get display name
                        data = await self.drive.read_json(
                            f["name"], parent_id=self.role_configs_folder_id
                        )
                        if data and "role_display_name" in data:
                            roles[role_id] = data["role_display_name"]
        except Exception as exc:
            logger.warning(f"Could not load Drive role configs: {exc}")

        return [{"id": rid, "display_name": name} for rid, name in roles.items()]
