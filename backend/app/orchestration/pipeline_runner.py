import asyncio
import uuid
from datetime import datetime, timezone

from app.agents.critic import CriticAgent
from app.agents.jd_analyzer import JdAnalyzerAgent
from app.agents.outreach import OutreachAgent
from app.agents.role_config_generator import RoleConfigGeneratorAgent
from app.agents.tailor import TailorAgent
from app.models.application import (
    ApplicationManifest,
    ApplicationVersion,
    ApplicationVersionFiles,
    PipelineMetadata,
)
from app.models.critique import Critique
from app.models.errors import APIError, ErrorCode, StageError
from app.models.outreach import OutreachJson, OutreachMessages
from app.models.pipeline import PipelineRequest, TailoredContent
from app.models.profile import Profile
from app.models.role_config import RoleConfig
from app.orchestration.inflight_tracker import InflightTracker
from app.orchestration.role_resolver import RoleResolver
from app.orchestration.sse_emitter import SseEmitter
from app.services.google_drive import GoogleDriveClient
from app.services.job_scraper import scrape_jd
from app.services.latex_assembler import LatexAssembler
from app.services.latex_compiler import LatexCompiler
from app.services.nvidia_nim import NimClient
from app.services.nvidia_nim_mock import MockNimClient
from app.utils.logging import get_logger, set_trace_id

logger = get_logger(__name__)

_ROOT_FOLDER = "Resume_Tailor"
AnyNimClient = NimClient | MockNimClient


class PipelineRunner:
    """Sequences all pipeline stages, emits SSE events, persists results to Drive."""

    def __init__(
        self,
        drive_client: GoogleDriveClient,
        nim_client: AnyNimClient,
        sse_emitter: SseEmitter,
        inflight_tracker: InflightTracker,
        latex_compiler: LatexCompiler,
    ) -> None:
        self.drive = drive_client
        self.nim = nim_client
        self.sse = sse_emitter
        self.tracker = inflight_tracker
        self.compiler = latex_compiler
        self.assembler = LatexAssembler()

    async def run(self, job_id: str, request: PipelineRequest) -> None:
        """Execute the full pipeline in a background task."""
        trace_id = set_trace_id()
        started_at = datetime.now(timezone.utc)
        logger.info(f"Pipeline start job_id={job_id} trace_id={trace_id}")

        try:
            # Load shared resources
            root_id = await self.drive.find_folder(_ROOT_FOLDER)
            if not root_id:
                raise StageError(
                    "setup",
                    ErrorCode.PROFILE_NOT_FOUND,
                    "Drive folder not found. Please complete setup.",
                )

            profile = await self._load_profile(root_id)
            role_configs_id = await self.drive.find_folder("role_configs", parent_id=root_id)

            role_config = await self._stage_resolve_role(
                job_id, request.role_config_id, root_id, role_configs_id
            )
            jd_text = await self._stage_scrape(job_id, request)
            jd_analysis = await self._stage_analyze(job_id, jd_text)
            tailored = await self._stage_tailor(
                job_id, profile, jd_analysis, role_config
            )
            pdf_bytes, final_latex, pdf_id = await self._stage_compile(
                job_id, profile, tailored, role_config
            )
            critique = await self._stage_critique(job_id, final_latex, jd_analysis)

            outreach: OutreachJson | None = None
            if request.outreach.enabled:
                outreach = await self._stage_outreach(
                    job_id, profile, tailored, jd_analysis, request
                )

            app_id, folder_id = await self._stage_persist(
                job_id,
                request,
                root_id,
                final_latex,
                pdf_bytes,
                critique,
                outreach,
                role_config,
                started_at,
            )

            elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
            self.tracker.store_result(job_id, {
                "job_id": job_id,
                "status": "completed",
                "application_id": app_id,
                "drive_folder_id": folder_id,
                "current_version": 1,
                "tailored_latex": final_latex,
                "pdf_url": f"/api/files/{pdf_id}",
                "critique": critique.model_dump(),
                "outreach": outreach.model_dump() if outreach else None,
            })

            await self.sse.emit(
                job_id,
                "pipeline_complete",
                {
                    "job_id": job_id,
                    "application_id": app_id,
                    "drive_folder_id": folder_id,
                    "duration_seconds": elapsed,
                },
            )
            logger.info(f"Pipeline complete job_id={job_id} elapsed={elapsed:.1f}s")

        except StageError as exc:
            detail = exc.to_detail()
            self.tracker.store_result(job_id, {"job_id": job_id, "status": "failed", "error": detail.model_dump()})
            await self.sse.emit(
                job_id,
                "stage_failed",
                {"stage": exc.stage, "error": detail.model_dump()},
            )
            logger.error(f"Pipeline failed at stage={exc.stage} job_id={job_id}")

        except APIError as exc:
            detail = exc.to_detail()
            self.tracker.store_result(job_id, {"job_id": job_id, "status": "failed", "error": detail.model_dump()})
            await self.sse.emit(
                job_id,
                "stage_failed",
                {"stage": "unknown", "error": detail.model_dump()},
            )

        finally:
            await self.tracker.release(job_id)
            await self.sse.close(job_id)

    # ── Stages ─────────────────────────────────────────────────────────────────

    async def _load_profile(self, root_id: str) -> Profile:
        data = await self.drive.read_json("profile.json", parent_id=root_id)
        if not data:
            raise StageError(
                "setup",
                ErrorCode.PROFILE_NOT_FOUND,
                "Profile not found. Please complete onboarding first.",
            )
        return Profile.model_validate(data)

    async def _stage_resolve_role(
        self,
        job_id: str,
        role_config_id: str,
        root_id: str,
        role_configs_id: str | None,
    ) -> RoleConfig:
        if not role_configs_id:
            role_configs_id = await self.drive.find_folder("role_configs", parent_id=root_id)
        generator = RoleConfigGeneratorAgent(nim_client=self.nim)
        resolver = RoleResolver(
            drive_client=self.drive,
            generator_agent=generator,
            role_configs_folder_id=role_configs_id or root_id,
        )
        return await resolver.resolve(role_config_id)

    async def _stage_scrape(self, job_id: str, request: PipelineRequest) -> str:
        if request.job_description:
            return request.job_description

        await self.sse.emit(job_id, "stage_started", {"stage": "scrape"})
        try:
            text = await scrape_jd(request.job_url)  # type: ignore[arg-type]
        except APIError as exc:
            raise StageError(
                "scrape", exc.code, exc.user_message,
                retry_possible=exc.retry_possible,
            ) from exc
        await self.sse.emit(job_id, "stage_completed", {"stage": "scrape", "result": {"chars": len(text)}})
        return text

    async def _stage_analyze(self, job_id: str, jd_text: str) -> dict:
        await self.sse.emit(job_id, "stage_started", {"stage": "jd_analyzer"})
        try:
            agent = JdAnalyzerAgent(nim_client=self.nim)
            result = await agent.run(jd_text=jd_text)
        except APIError as exc:
            raise StageError("jd_analyzer", exc.code, exc.user_message) from exc
        await self.sse.emit(job_id, "stage_completed", {"stage": "jd_analyzer"})
        return result

    async def _stage_tailor(
        self,
        job_id: str,
        profile: Profile,
        jd_analysis: dict,
        role_config: RoleConfig,
        prev_critique: dict | None = None,
    ) -> TailoredContent:
        await self.sse.emit(job_id, "stage_started", {"stage": "tailor"})
        agent = TailorAgent(nim_client=self.nim)
        role_config_dict = role_config.model_dump()

        async def _run_and_validate(validation_error: str | None = None) -> TailoredContent:
            try:
                raw = await agent.run(
                    profile=profile,
                    jd_analysis=jd_analysis,
                    role_config=role_config_dict,
                    prev_critique=prev_critique,
                    validation_error=validation_error,
                )
                content = TailoredContent.model_validate(raw)
                agent.validate_tailored_output(content, profile)
                return content
            except APIError:
                raise

        try:
            content = await _run_and_validate()
        except APIError as exc:
            if exc.code != ErrorCode.TAILOR_VALIDATION_FAILED:
                raise StageError("tailor", exc.code, exc.user_message) from exc
            # One retry with the validation error injected into the prompt
            logger.warning(
                f"Tailor validation failed job_id={job_id}, retrying. "
                f"details={exc.technical_details}"
            )
            try:
                content = await _run_and_validate(validation_error=exc.technical_details)
            except APIError as exc2:
                raise StageError(
                    "tailor",
                    exc2.code,
                    "The AI couldn't preserve all your resume content after two attempts. "
                    "Try again or check your profile for inconsistencies.",
                    technical_details=exc2.technical_details,
                    retry_possible=True,
                ) from exc2

        await self.sse.emit(job_id, "stage_completed", {"stage": "tailor"})
        return content

    async def _stage_compile(
        self,
        job_id: str,
        profile: Profile,
        tailored: TailoredContent,
        role_config: RoleConfig,
    ) -> tuple[bytes, str, str]:
        await self.sse.emit(job_id, "stage_started", {"stage": "compile"})
        try:
            last_result = None
            last_tex = None

            for step in range(self.assembler.trim_steps_count()):
                tex = self.assembler.assemble(
                    profile=profile,
                    tailored=tailored,
                    trim_step=step,
                )
                result = await self.compiler.compile(tex, filename="resume")
                if not result.success:
                    logger.error(
                        f"pdflatex failed job_id={job_id} step={step} "
                        f"errors={result.errors} log_tail={result.compile_log[-500:]!r}"
                    )
                    raise StageError(
                        "compile",
                        ErrorCode.LATEX_COMPILE_FAILED,
                        "LaTeX compilation failed. Check the backend log for the pdflatex error.",
                        technical_details=result.compile_log[-500:],
                        retry_possible=True,
                    )
                last_result, last_tex = result, tex
                if result.pages == 1:
                    from app.deps import get_temp_storage
                    pdf_id = get_temp_storage().store(result.pdf_bytes, ext="pdf")
                    await self.sse.emit(
                        job_id, "stage_completed",
                        {"stage": "compile", "result": {"pages": 1}},
                    )
                    return result.pdf_bytes, tex, pdf_id

            # Ladder exhausted — still > 1 page.  Warn and return closest fit.
            pages = last_result.pages if last_result else "?"
            logger.warning(
                f"Page-fit ladder exhausted job_id={job_id} pages={pages}; "
                "returning closest fit with warning"
            )
            await self.sse.emit(
                job_id,
                "page_overflow_warning",
                {
                    "pages": pages,
                    "message": (
                        f"Your resume is {pages} pages. It couldn't fit on one page even "
                        "after trimming older content. The closest version is shown — "
                        "consider shortening some bullet points."
                    ),
                },
            )
            from app.deps import get_temp_storage
            pdf_id = get_temp_storage().store(last_result.pdf_bytes, ext="pdf")
            await self.sse.emit(
                job_id, "stage_completed",
                {"stage": "compile", "result": {"pages": pages, "overflow": True}},
            )
            return last_result.pdf_bytes, last_tex, pdf_id

        except StageError:
            raise
        except APIError as exc:
            raise StageError("compile", exc.code, exc.user_message) from exc
        except Exception as exc:
            logger.error(f"compile exception job_id={job_id} type={type(exc).__name__} detail={exc}")
            raise StageError(
                "compile",
                ErrorCode.LATEX_COMPILE_FAILED,
                "LaTeX compilation failed. Check your template syntax.",
                technical_details=str(exc),
                retry_possible=True,
            ) from exc

    async def _stage_critique(
        self, job_id: str, latex_source: str, jd_analysis: dict
    ) -> Critique:
        await self.sse.emit(job_id, "stage_started", {"stage": "critique"})
        try:
            agent = CriticAgent(nim_client=self.nim)
            result = await agent.run(latex_source=latex_source, jd_analysis=jd_analysis)
            critique = Critique.model_validate(result)
        except APIError as exc:
            raise StageError("critique", exc.code, exc.user_message) from exc

        await self.sse.emit(
            job_id,
            "stage_completed",
            {"stage": "critique", "result": {"score": critique.total, "verdict": critique.verdict, "color": Critique.color_for_score(critique.total)}},
        )
        return critique

    @staticmethod
    def _build_outreach_context(
        profile: Profile, tailored: TailoredContent
    ) -> dict:
        """Assemble a rich, specific candidate snapshot for the outreach agent.

        The old payload was just name + skills, which forced the agent to write
        generically. We surface the JD-tailored summary, the candidate's current
        role, their strongest (already JD-tuned) achievements, and a standout
        project so the agent can lead with something concrete.
        """
        exp_meta = {e.id: e for e in profile.experience}
        proj_meta = {p.id: p for p in profile.projects}

        current_role: str | None = None
        if tailored.experience:
            meta = exp_meta.get(tailored.experience[0].role_id)
            if meta:
                current_role = f"{meta.title}, {meta.company}"

        # Top achievements come from the tailored bullets (already reworded toward
        # the JD and ordered by relevance) — the best material to lead with.
        top_achievements: list[str] = []
        for te in tailored.experience[:2]:
            top_achievements.extend(te.bullets[:2])

        standout_project: dict | None = None
        if tailored.projects:
            meta = proj_meta.get(tailored.projects[0].project_id)
            if meta:
                standout_project = {
                    "name": meta.name,
                    "what": meta.text,
                    "stack": meta.stack,
                    "metrics": meta.metrics,
                }

        return {
            "name": profile.personal.name,
            "pitch": tailored.summary,
            "current_role": current_role,
            "top_achievements": top_achievements[:4],
            "standout_project": standout_project,
            "skills": profile.skills,
        }

    async def _stage_outreach(
        self,
        job_id: str,
        profile: Profile,
        tailored: TailoredContent,
        jd_analysis: dict,
        request: PipelineRequest,
    ) -> OutreachJson:
        await self.sse.emit(job_id, "stage_started", {"stage": "outreach"})
        try:
            agent = OutreachAgent(nim_client=self.nim)
            result = await agent.run(
                profile_summary=self._build_outreach_context(profile, tailored),
                jd_analysis=jd_analysis,
                company_name=request.company_name,
                role_title=request.role_title,
                contact_name=request.outreach.contact_name,
                contact_type=request.outreach.contact_type,
            )
            messages = OutreachMessages.model_validate(result.get("messages", {}))
            outreach = OutreachJson(
                company=request.company_name,
                role_title=request.role_title,
                generated_at=datetime.now(timezone.utc).isoformat(),
                messages=messages,
                personalization_used=result.get("personalization_used", []),
            )
        except APIError as exc:
            raise StageError("outreach", exc.code, exc.user_message) from exc

        await self.sse.emit(job_id, "stage_completed", {"stage": "outreach"})
        return outreach

    async def _stage_persist(
        self,
        job_id: str,
        request: PipelineRequest,
        root_id: str,
        latex_source: str,
        pdf_bytes: bytes,
        critique: Critique,
        outreach: OutreachJson | None,
        role_config: RoleConfig,
        started_at: datetime,
    ) -> tuple[str, str]:
        await self.sse.emit(job_id, "stage_started", {"stage": "persist"})
        try:
            app_id = f"app_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc)
            short_uuid = uuid.uuid4().hex[:4]
            safe_company = "".join(c if c.isalnum() else "" for c in request.company_name)[:20]
            safe_role = "".join(c if c.isalnum() else "" for c in request.role_title)[:10]
            folder_name = f"{now.date()}_{safe_company}_{safe_role}_{short_uuid}"

            apps_folder_id = await self.drive.find_folder("applications", parent_id=root_id)
            if not apps_folder_id:
                apps_folder_id, _ = await self.drive.ensure_folder("applications", parent_id=root_id)

            app_folder_id, _ = await self.drive.ensure_folder(folder_name, parent_id=apps_folder_id)

            # Write resume_v1.tex
            await self.drive.upload_bytes(
                "resume_v1.tex",
                latex_source.encode("utf-8"),
                "text/plain",
                parent_id=app_folder_id,
            )
            # Write resume_v1.pdf
            await self.drive.upload_bytes(
                "resume_v1.pdf",
                pdf_bytes,
                "application/pdf",
                parent_id=app_folder_id,
            )
            # Write critique_v1.json
            await self.drive.write_json("critique_v1.json", critique.model_dump(), parent_id=app_folder_id)

            # Write outreach.json
            outreach_file = None
            if outreach:
                await self.drive.write_json("outreach.json", outreach.model_dump(), parent_id=app_folder_id)
                outreach_file = "outreach.json"

            elapsed = (now - started_at).total_seconds()
            manifest = ApplicationManifest(
                application_id=app_id,
                created_at=started_at.isoformat(),
                last_modified=now.isoformat(),
                company=request.company_name,
                role_title=request.role_title,
                role_config_used=request.role_config_id,
                job_url=request.job_url,
                current_version=1,
                versions=[
                    ApplicationVersion(
                        version=1,
                        score=critique.total,
                        verdict=critique.verdict,
                        color=Critique.color_for_score(critique.total),
                        files=ApplicationVersionFiles(
                            tex="resume_v1.tex",
                            pdf="resume_v1.pdf",
                            critique="critique_v1.json",
                        ),
                    )
                ],
                outreach_file=outreach_file,
                status="tailored",
                pipeline_metadata=PipelineMetadata(
                    model_used=getattr(self.nim, "_api_key", "mock")[:4] + "...",
                    total_duration_seconds=elapsed,
                ),
            )
            await self.drive.write_json("manifest.json", manifest.model_dump(), parent_id=app_folder_id)

        except APIError as exc:
            raise StageError("persist", exc.code, exc.user_message) from exc
        except Exception as exc:
            raise StageError(
                "persist",
                ErrorCode.INTERNAL_ERROR,
                "Failed to save your application to Drive.",
                retry_possible=True,
            ) from exc

        await self.sse.emit(job_id, "stage_completed", {"stage": "persist"})
        return app_id, app_folder_id
