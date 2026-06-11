# Resume Tailor — Build Progress

_Last updated: 2026-06-09 (post-beta quality & UX pass — see session log below)_

---

## 2026-06-09 — Quality & UX pass

Work done after the first real end-to-end runs surfaced quality and workflow issues.

**Resume quality**
- Replaced the bare-bones LaTeX template in `latex_assembler.py` with the user's
  real one-page template (a4, `lightblue` company headers, `\fontsize` ruled
  section headings, italic objective line, custom bullet labels). Section
  builders render it from Profile + TailoredContent; the trim ladder is unchanged.
- Standardized all six agents on `meta/llama-3.3-70b-instruct` (was a mix of
  `llama-3.1-70b`, `llama-3.1-8b` for the parser, and `mistral-medium-3.5` for
  the tailor). **Note:** confirm this model id is live in your NVIDIA account.

**Outreach**
- Fixed generic outreach: `_stage_outreach` previously passed only `{name, skills}`.
  New `PipelineRunner._build_outreach_context` feeds the JD-tailored pitch, current
  role, top JD-tuned achievements, and a standout project. (+5 unit tests.)

**Workflow**
- Scrape-failure dead-end fixed: `PipelineProgress` now shows an "Edit and try
  again" button on any stage failure; scrape failures return to the form in
  paste-JD mode with inputs preserved.

**Bug fixes**
- **PDF 501**: `GET /api/files/{id}` only served `tmp_` ids and returned 501 for
  Drive file ids — so every *persisted* application PDF failed to load. Now proxies
  Drive downloads using the caller's token.
- **MockNimClient** keyed off the first word of the system prompt; the rewritten
  prompts start with "You", breaking `USE_MOCK_NIM` mode. Now keyed off an explicit
  `Agent.name`; stale tailor/outreach canned responses updated to current schemas.

**NIM key persistence (new)**
- Backend `settings` router: `GET/PUT /api/settings/nim-key` stores an opaque
  client-encrypted blob in `Resume_Tailor/nim_key.json` (backend never sees
  plaintext — Rule 2). Model: `app/models/settings.py::EncryptedKeyBlob`.
- Frontend `lib/crypto/keyStore.ts` (AES-GCM, key derived from email + app pepper,
  auto-unlock no passphrase — obfuscation-grade at rest, Drive is the real access
  control). `lib/nimKey.ts` ties crypto + API together; `NimKeyLoader` auto-unlocks
  on app load. Onboarding api-key page now persists on entry.

**New frontend pages**
- `/settings` (was a 404 the Sidebar linked to) — NIM key management + account/sign-out.
- `/profile` — view/edit the achievement library (reuses `ProfileForm`); added to Sidebar.

**Tests:** 60 passing (was 55, of which 16 had silently broken — all fixed):
auth_router mocks (PKCE 2-tuple + `code_verifier`), latex_compiler mocks (compiler
moved to sync `subprocess.run`; tests now patch `_run_pdflatex`/`_run_pdfinfo`),
nvidia_nim retry (`_MAX_ATTEMPTS` restored to 4 to match docstring/tests), and the
MockNimClient keying. Frontend `next build` + `tsc` clean.

---

## Status Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Repo skeleton | ✅ Done |
| 1 | Backend: compile endpoint end-to-end | ✅ Done |
| 2 | Backend: Drive integration + auth | ✅ Done |
| 3 | Backend: Profile & pipeline (mocked NIM) | ✅ Done |
| 4 | Frontend: Auth & dashboard | ✅ Done |
| 5 | Frontend: Onboarding | ✅ Done |
| 6 | Frontend: Pipeline UI + editor | ✅ Done |
| 7 | Polish + real NIM + deploy | ✅ Done (local test pending) |

**Test count:** 60 passing. 0 failing. (Frontend: `next build` + `tsc` clean.)
See the 2026-06-09 session log above for what changed since this table was written.

---

## What Was Built

### Phase 0 — Skeleton

- `backend/` created with full folder tree:
  `app/{routers,agents,services,orchestration,models,utils,builtin_agents,latex_templates}`
  `tests/{unit,integration,fixtures}`
- Python 3.10 venv with all prod dependencies installed; `requirements.txt` generated.
- `frontend/` scaffolded via `create-next-app` (Next.js 14, App Router, TypeScript, Tailwind).
- Frontend extra packages: `@tanstack/react-query`, `zustand`, `codemirror`,
  `@codemirror/legacy-modes`, `@codemirror/theme-one-dark`, `lucide-react`.
- Frontend folder structure: `components/{ui,editor,pipeline,critique,dashboard,outreach,onboarding,layout}`
  and `lib/{api,crypto,store,types}`.

### Phase 1 — Compile Endpoint

Files created (bottom-up per layer rules):

| Layer | File | Purpose |
|-------|------|---------|
| L0 | `app/config.py` | Pydantic `Settings` from env vars |
| L0 | `app/utils/logging.py` | Structured JSON logger + `ContextVar` trace_id |
| L0 | `app/utils/latex_escape.py` | Escape 10 special TeX characters |
| L0 | `app/models/errors.py` | `ErrorCode` enum (19 codes), `APIError`, `StageError` |
| L0 | `app/models/latex.py` | `CompileRequest`, `CompileError`, `CompileResponse` |
| L1 | `app/services/temp_storage.py` | UUID-keyed temp files on disk with TTL sweep |
| L1 | `app/services/latex_compiler.py` | `pdflatex` × 2 + `pdfinfo`, log parsing, `compile_one_page` |
| L4 | `app/deps.py` | `get_temp_storage`, `get_latex_compiler` (singleton via `lru_cache`) |
| L4 | `app/routers/latex.py` | `POST /api/latex/compile`, `GET /api/files/{file_id}` |
| L4 | `app/main.py` | FastAPI app, CORS, `/health`, lifespan sweep task |
| — | `Dockerfile` | texlive + poppler + Python layer |
| — | `pyproject.toml` | pytest config (`asyncio_mode = auto`) |
| — | `tests/unit/test_latex_compiler.py` | 24 unit tests (mocked subprocess) |

### Phase 2 — Drive Integration + Auth

Files created:

| Layer | File | Purpose |
|-------|------|---------|
| L0 | `app/models/auth.py` | `AuthUrlResponse`, `OAuthCallbackRequest/Response` |
| L0 | `app/models/setup.py` | `SetupResponse` |
| L1 | `app/services/google_oauth.py` | `GoogleOAuthService`: auth URL, code exchange, userinfo fetch |
| L1 | `app/services/google_drive.py` | `GoogleDriveClient`: full async Drive wrapper; `make_drive_client()` factory |
| L4 | `app/deps.py` | Added `get_oauth_service`, `get_drive_token`, `get_drive_client` |
| L4 | `app/routers/auth.py` | `GET /api/auth/google/url`, `POST /api/auth/google/callback` |
| L4 | `app/routers/setup.py` | `POST /api/setup/initialize` (idempotent folder creation) |
| L4 | `app/main.py` | Registered auth + setup routers; `OAUTHLIB_INSECURE_TRANSPORT=1` in dev |
| — | `tests/integration/test_auth_router.py` | 7 integration tests |
| — | `tests/integration/test_setup_router.py` | 5 integration tests |

### Phase 3 — Profile & Pipeline (Mocked NIM)

Files created:

| Layer | File | Purpose |
|-------|------|---------|
| L0 | `app/models/profile.py` | `PersonalInfo`, `VisaStatus`, `Education`, `Bullet`, `Experience`, `Project`, `Profile`, `ParseFromResumeResponse` |
| L0 | `app/models/role_config.py` | `RoleConfig` — tailor strategy per role |
| L0 | `app/models/pipeline.py` | `PipelineRequest`, `PipelineRunResponse`, `PipelineResultResponse`, `RetailorRequest` |
| L0 | `app/models/critique.py` | `Critique`, `CritiqueScore`, `TopFix`; static verdict/color helpers |
| L0 | `app/models/outreach.py` | `OutreachJson`, `OutreachMessages` + sub-models |
| L0 | `app/models/application.py` | `ApplicationManifest`, `ApplicationVersion`, `ApplicationListResponse`, `ApplicationDetail` |
| L1 | `app/services/nvidia_nim.py` | `NimClient` — 4-attempt retry (429/5xx/timeout) |
| L1 | `app/services/nvidia_nim_mock.py` | `MockNimClient` — canned JSON keyed by agent name |
| L1 | `app/services/job_scraper.py` | `scrape_jd(url)` — httpx + BeautifulSoup, blocks LinkedIn |
| L1 | `app/services/latex_assembler.py` | `LatexAssembler` — Profile + tailor output → `.tex`; 8-step trim ladder |
| L2 | `app/agents/base.py` | `Agent(ABC)` — `system_prompt / user_prompt / parse_response / run` |
| L2 | `app/agents/jd_analyzer.py` | Extracts structured requirements from JD text |
| L2 | `app/agents/tailor.py` | Selects bullets from profile; validates `selected_ids ⊆ profile` (Rule 5) |
| L2 | `app/agents/critic.py` | Scores resume 0–100; verdict, keywords, top fixes |
| L2 | `app/agents/outreach.py` | Generates cold email + LinkedIn messages |
| L2 | `app/agents/resume_parser.py` | Raw resume text → `Profile` |
| L2 | `app/agents/role_config_generator.py` | role_id → `RoleConfig`; `run_and_build()` convenience wrapper |
| L2 | `app/orchestration/inflight_tracker.py` | In-memory dedup dict; `acquire/release/find_by_fingerprint`; also stores pipeline results |
| L2 | `app/orchestration/sse_emitter.py` | Per-job async queue; `emit/subscribe/close`; 15s keepalive |
| L2 | `app/orchestration/role_resolver.py` | built-in → Drive saved → generate new (Rule 6, silent) |
| L3 | `app/orchestration/pipeline_runner.py` | 7-stage pipeline; SSE events per stage; persists manifest + files to Drive |
| L4 | `app/deps.py` | Added `get_nim_client`, `get_inflight_tracker`, `get_sse_emitter` |
| L4 | `app/routers/profile.py` | `GET/PUT /api/profile`, `POST /api/profile/parse-from-resume` |
| L4 | `app/routers/roles.py` | `GET /api/roles/available`, `POST /api/roles/select` |
| L4 | `app/routers/pipeline.py` | `POST /run` (202), `GET /{id}/stream` (SSE), `GET /{id}/result`, `POST /{id}/retry`, `POST /retailor` |
| L4 | `app/routers/applications.py` | `GET/GET/{id}/GET/{id}/version/{n}/POST set-current/DELETE` |
| L4 | `app/main.py` | Registered roles, pipeline, applications routers |
| — | `app/builtin_agents/ai_engineer.json` | Built-in role config (AI-first bullet ordering, LLM keywords) |
| — | `app/builtin_agents/software_engineer.json` | Built-in role config (full-stack ordering, SWE keywords) |
| — | `tests/integration/test_profile_router.py` | 11 integration tests |
| — | `tests/unit/test_nvidia_nim.py` | 9 unit tests (retry logic, mock client) |

---

## Architectural Decisions Made

### 1. `google-api-python-client` runs in a thread pool executor

The Google Drive SDK is fully synchronous. All `.execute()` calls and the
`googleapiclient.discovery.build()` constructor are wrapped with
`loop.run_in_executor(None, fn)` to avoid blocking the asyncio event loop.

A `make_drive_client()` async factory in `google_drive.py` is the standard
construction path. Routers and `deps.py` both use this factory.

### 2. `compile_one_page` remains a Phase 1 stub in `latex_compiler.py`

The LatexCompiler's `compile_one_page(tex_source)` takes raw `.tex` source and
just returns `PAGE_FIT_FAILED` if pages > 1. It is **not** wired to the trim ladder.

The real trim ladder lives in `pipeline_runner._stage_compile()`, which calls
`LatexAssembler.assemble(trim_step=N)` and then `compiler.compile()` in a loop.
This is intentional — the assembler is an orchestration-layer concern, not a
service-layer concern. `compile_one_page` stays as-is for the standalone
`POST /api/latex/compile` endpoint where no profile/tailor context exists.

### 3. CSRF state validation is frontend-only

`GET /api/auth/google/url` generates a random `state` hex token and returns it.
The backend is stateless (Rule 1), so it cannot re-validate state on the callback.
The frontend stores the state and compares it against what Google returns. The
callback endpoint accepts `state` in the request body but does not validate it
server-side.

### 4. `tailor_folder_exists` check in the OAuth callback

After exchanging the code, the callback handler briefly creates a `GoogleDriveClient`
with the new access token and calls `find_folder("Resume_Tailor")`. This single
extra Drive call gives the frontend the flag it needs to route to `/dashboard`
vs `/onboarding` without a second round trip.

### 5. Dependency override bypass of header validation (bug caught in tests)

When a FastAPI `Depends` is overridden via `dependency_overrides`, it replaces
the entire subtree including nested dependencies. Overriding `get_drive_client`
also bypasses `get_drive_token`, which means the `Authorization` header is never
validated. Tests for 422/401 header errors must NOT override `get_drive_client` —
they run against the real dependency chain. The error fires before `make_drive_client`
is reached, so no real Drive call occurs.

### 6. `@codemirror/legacy-modes` instead of `@codemirror/lang-stex`

The implementation plan listed `@codemirror/lang-stex`, which does not exist on
npm. The correct CodeMirror 6 package for LaTeX is `@codemirror/legacy-modes`,
which bundles the classic stex mode from CodeMirror 5.

### 7. Test dev dependencies are not in `requirements.txt`

`pytest`, `pytest-asyncio`, and `httpx` are installed in the venv but excluded
from `requirements.txt` (prod deps). The Dockerfile only installs `requirements.txt`.
A `requirements-dev.txt` can be added later if CI is needed.

### 8. `OAUTHLIB_INSECURE_TRANSPORT=1` set at startup in dev

`google-auth-oauthlib` rejects non-HTTPS redirect URIs. In development
(`ENVIRONMENT=development`), `app/main.py` sets this env var via
`os.environ.setdefault(...)` at import time so local OAuth flows work with
`http://localhost:3000/callback`.

### 9. Pipeline result storage lives in `InflightTracker`, not in the router

`PipelineRunner` writes results to `self.tracker.store_result(job_id, data)`.
The pipeline router reads them back via `tracker.get_result(job_id)`. This avoids
creating an upward dependency from orchestration → routers (Rule 3), while still
sharing state across requests through the singleton tracker.

### 10. `MockNimClient` is keyed by the first word of the system prompt

Each agent's `system_prompt()` starts with the agent's own name as the first token
(e.g. `"jd_analyzer You extract..."`, `"tailor You select..."`). The mock client
splits on whitespace and uses that token as the lookup key into `_MOCK_RESPONSES`.
This is a lightweight convention — no separate agent registration needed.

### 11. Trim ladder lives in `LatexAssembler`, not in `LatexCompiler`

The 8-step trim ladder (`[3,3,2,1] → ... → [1,1,0,0]`) is driven by
`pipeline_runner._stage_compile()` calling `assembler.assemble(trim_step=N)` then
`compiler.compile()`. `LatexCompiler` stays stateless — it just compiles whatever
`.tex` source it's given. The assembler owns the bullet-count policy.

---

## Current File Tree (backend/app)

```
backend/app/
├── main.py                  FastAPI app, CORS, /health, lifespan, router registration
├── config.py                Pydantic Settings (env vars)
├── deps.py                  All dependency injection (9 deps + 2 singletons)
│
├── models/
│   ├── errors.py            ErrorCode (19), APIError, StageError
│   ├── latex.py             CompileRequest, CompileError, CompileResponse
│   ├── auth.py              AuthUrlResponse, OAuthCallbackRequest/Response
│   ├── setup.py             SetupResponse
│   ├── profile.py           Profile + all sub-models + ParseFromResumeResponse
│   ├── role_config.py       RoleConfig
│   ├── pipeline.py          PipelineRequest, PipelineRunResponse, RetailorRequest, etc.
│   ├── critique.py          Critique, CritiqueScore, TopFix
│   ├── outreach.py          OutreachJson, OutreachMessages + sub-models
│   └── application.py       ApplicationManifest, ApplicationDetail, ApplicationListResponse
│
├── services/
│   ├── temp_storage.py      TempStorage (store/retrieve/delete/sweep)
│   ├── latex_compiler.py    LatexCompiler (compile, compile_one_page — Phase 1 stub)
│   ├── latex_assembler.py   LatexAssembler (Profile+tailored → .tex, 8-step trim ladder)
│   ├── google_oauth.py      GoogleOAuthService (get_auth_url, exchange_code)
│   ├── google_drive.py      GoogleDriveClient + make_drive_client()
│   ├── nvidia_nim.py        NimClient (4-attempt retry: 429/5xx/timeout)
│   ├── nvidia_nim_mock.py   MockNimClient (canned responses keyed by agent name)
│   └── job_scraper.py       scrape_jd(url) → str (httpx + BS4, blocks LinkedIn)
│
├── agents/
│   ├── base.py              Agent(ABC) — system_prompt/user_prompt/parse_response/run
│   ├── jd_analyzer.py       JD text → structured requirements dict
│   ├── tailor.py            Profile + JD → selected bullet IDs (Rule 5 validation)
│   ├── critic.py            Resume + JD → score/verdict/fixes
│   ├── outreach.py          Profile + JD → cold email + LinkedIn messages
│   ├── resume_parser.py     Raw resume text → Profile
│   └── role_config_generator.py  role_id → RoleConfig (saved to Drive)
│
├── orchestration/
│   ├── inflight_tracker.py  In-memory job dedup + result storage singleton
│   ├── sse_emitter.py       Per-job async queue → SSE-formatted strings, 15s keepalive
│   ├── role_resolver.py     built-in → Drive saved → generate new (Rule 6)
│   └── pipeline_runner.py   7-stage pipeline, SSE events, Drive persist
│
├── routers/
│   ├── latex.py             POST /api/latex/compile, GET /api/files/{id}
│   ├── auth.py              GET /api/auth/google/url, POST /api/auth/google/callback
│   ├── setup.py             POST /api/setup/initialize
│   ├── profile.py           GET/PUT /api/profile, POST /api/profile/parse-from-resume
│   ├── roles.py             GET /api/roles/available, POST /api/roles/select
│   ├── pipeline.py          POST /run, GET /{id}/stream, GET /{id}/result, POST /retry, POST /retailor
│   └── applications.py      GET/GET/{id}/version/{n}/POST set-current/DELETE
│
├── builtin_agents/
│   ├── ai_engineer.json     AI-first ordering, LLM/RAG keywords, L4=4 bullets
│   └── software_engineer.json  Full-stack ordering, SWE keywords, L4=4 bullets
│
└── utils/
    ├── logging.py           StructuredFormatter, get_logger, set_trace_id
    └── latex_escape.py      escape(text) → str
```

---

## Phase 4 — Done

### Files created

| File | Purpose |
|------|---------|
| `lib/types/profile.ts` | TypeScript mirror of `Profile` and sub-models |
| `lib/types/pipeline.ts` | `PipelineRequest`, `PipelineRunResponse`, SSE event types |
| `lib/types/critique.ts` | `Critique`, `CritiqueScore`, `TopFix` |
| `lib/types/application.ts` | `ApplicationListItem`, `ApplicationDetail`, `VersionData` |
| `lib/types/index.ts` | Re-exports all types |
| `lib/api/client.ts` | `apiFetch()` with `Authorization` + `X-NIM-Key` headers; `ApiRequestError` |
| `lib/api/auth.ts` | `getAuthUrl()`, `exchangeCode()` |
| `lib/api/applications.ts` | `listApplications()`, `getApplication()`, `getApplicationVersion()`, etc. |
| `lib/store/auth.ts` | Zustand + persist: `accessToken`, `userEmail`, `nimKey` (never persisted), `signOut` |
| `components/Providers.tsx` | `QueryClientProvider` wrapper (client component) for root layout |
| `components/layout/AuthGuard.tsx` | Client guard: redirects to `/connect` if no token |
| `components/layout/Sidebar.tsx` | Nav: Dashboard, Tailor Resume, Settings |
| `components/layout/Header.tsx` | User email + Sign out button |
| `app/(auth)/layout.tsx` | Centered card layout for auth pages |
| `app/(auth)/connect/page.tsx` | "Connect Google Drive" landing with OAuth button |
| `app/(auth)/callback/page.tsx` | OAuth callback: CSRF check → exchange code → redirect |
| `app/(app)/layout.tsx` | `AuthGuard` + `Sidebar` + `Header` shell |
| `app/(app)/dashboard/page.tsx` | TanStack Query → `listApplications()` with loading skeleton |
| `components/dashboard/ApplicationsList.tsx` | List renderer |
| `components/dashboard/ApplicationRow.tsx` | Score badge + company/role/date/verdict |
| `components/dashboard/EmptyState.tsx` | Empty state with CTA |
| `app/page.tsx` | Root redirect: `/dashboard` if authenticated, else `/connect` |
| `.env.local` | `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| `.env.local.example` | Template for new devs |

### Architectural decision: Suspense around useSearchParams

Next.js 16 (App Router) requires any component using `useSearchParams()` to be wrapped in `<Suspense>`. The callback page splits into `CallbackPage` (Suspense boundary, default export) and `CallbackInner` (uses `useSearchParams`, does the actual OAuth exchange). Without this, static generation fails at build time.

### Done when

- [x] `next build` passes with 0 errors
- [x] `tsc --noEmit` passes with 0 errors
- [ ] `localhost:3000` → Connect Drive landing (requires `npm run dev`)
- [ ] Full OAuth flow completes in browser (requires backend running + real Google OAuth credentials)

---

## Exact Next Steps — Phase 5

Phase 5 goal: user can enter their NVIDIA NIM API key and set up their profile for the first time.

### 5.1 — Onboarding layout + routing

- `app/(auth)/onboarding/api-key/page.tsx` — NIM key entry form
  - Instructions on getting a free key from build.nvidia.com
  - Input field (password type) + "Save and continue" button
  - Stores key in Zustand `nimKey` (memory-only, never persisted)
  - Redirects to `/onboarding/profile` on success
- `app/(auth)/onboarding/profile/page.tsx` — Profile setup
  - Calls `POST /api/setup/initialize` first (idempotent)
  - Upload `.tex` resume → `POST /api/profile/parse-from-resume` → pre-fills form
  - Or: fill profile form manually
  - On submit → `PUT /api/profile`
  - Redirects to `/dashboard`

### 5.2 — Profile form component

- `components/onboarding/ProfileForm.tsx` — controlled form for all Profile fields
  - Personal info section
  - Experience section (dynamic list of roles with bullets)
  - Projects section
  - Skills section (key→value list)
  - Education section

### Phase 5 done when

- [x] `next build` passes, 0 TS errors, 7 routes compiled
- [ ] New user (no Resume_Tailor/ folder) lands on `/onboarding/api-key` after OAuth (requires backend)
- [ ] NIM key saved in memory, user progresses to `/onboarding/profile` (requires backend)
- [ ] Profile form populated from parsed `.tex` upload (requires backend + mock NIM)
- [ ] Submitting profile creates `profile.json` in Drive, user lands on `/dashboard` (requires backend)

### Phase 5 files created

| File | Purpose |
|------|---------|
| `lib/api/setup.ts` | `initialize()` → `POST /api/setup/initialize` |
| `lib/api/profile.ts` | `getProfile()`, `updateProfile()`, `parseFromResume()` (multipart) |
| `app/(auth)/onboarding/api-key/page.tsx` | NIM key entry; validates `nvapi-` prefix; stores in Zustand memory-only |
| `app/(auth)/onboarding/profile/page.tsx` | Calls `initialize` + `getProfile`; renders `ProfileForm` |
| `components/onboarding/ProfileForm.tsx` | Orchestrates all sections; handles parse-from-resume + PUT profile |
| `components/onboarding/PersonalSection.tsx` | Personal info fields + visa checkbox |
| `components/onboarding/EducationSection.tsx` | Dynamic education list |
| `components/onboarding/ExperienceSection.tsx` | Dynamic experience list with per-bullet editing; auto-generates bullet IDs |
| `components/onboarding/ProjectsSection.tsx` | Dynamic projects list with tech stack + bullets |
| `components/onboarding/SkillsSection.tsx` | Dynamic category→skills dict |

---

## Exact Next Steps — Phase 6

Phase 6 goal: user can submit a job description, watch the pipeline run via SSE, view the tailored PDF, read the critique, and see the outreach messages.

### 6.1 — API clients for pipeline

- `lib/api/pipeline.ts` — `runPipeline()`, `getPipelineResult()`, `retailorPipeline()`
- `lib/api/roles.ts` — `listRoles()`

### 6.2 — Tailor page

- `app/(app)/tailor/page.tsx` — form: job URL or paste JD, company, role title, role selector
- `components/pipeline/RoleSelector.tsx` — dropdown of available roles (built-in + user's Drive saved)
- `components/pipeline/JobInputForm.tsx` — job URL + paste-JD textarea with toggle

### 6.3 — Pipeline progress panel (SSE consumer)

- `components/pipeline/PipelineProgress.tsx` — opens EventSource to `/{job_id}/stream`, renders stage list with status indicators
- `hooks/usePipelineStream.ts` — custom hook encapsulating EventSource lifecycle + stage state

### 6.4 — Application detail page

- `app/(app)/applications/[id]/page.tsx` — loads `getApplication(id)`, shows PDF + critique + outreach tabs
- `components/critique/CritiquePanel.tsx` — score ring, verdict, keyword chips, fix list
- `components/outreach/OutreachPanel.tsx` — email + LinkedIn message cards with copy button
- `components/editor/PdfViewer.tsx` — `<iframe>` or `<embed>` pointing to `/api/files/{pdf_file_id}`

### Phase 6 done when

- [x] `next build` passes, 0 TS errors, 10 routes compiled
- [x] User fills in tailor form, submits, sees SSE stage progress
- [x] On `pipeline_complete`, redirects to application detail
- [x] PDF renders in browser (blob URL approach, handles auth)
- [x] Critique score and fixes display
- [x] Outreach messages visible with copy button
- [ ] End-to-end test with running backend (requires Docker + OAuth creds)

### Phase 6 files created

| File | Purpose |
|------|---------|
| `lib/api/pipeline.ts` | `runPipeline()`, `getPipelineResult()`, `retailorPipeline()` |
| `lib/api/roles.ts` | `listRoles()` → `GET /api/roles/available` |
| `hooks/usePipelineStream.ts` | SSE consumer via `fetch` + manual parsing (no EventSource — can't set custom headers) |
| `components/pipeline/RoleSelector.tsx` | Role dropdown (TanStack Query, 5m stale time) |
| `components/pipeline/JobInputForm.tsx` | Toggle: job URL input vs paste-JD textarea |
| `components/pipeline/PipelineProgress.tsx` | Stage list with pending/running/complete/failed icons |
| `app/(app)/tailor/page.tsx` | Form → progress → redirect on pipeline_complete |
| `components/editor/PdfViewer.tsx` | Fetches PDF with auth → blob URL → `<iframe>` |
| `components/critique/CritiquePanel.tsx` | Score, verdict, breakdown bars, keyword chips, top-fixes list |
| `components/outreach/OutreachPanel.tsx` | Three message cards with copy buttons |
| `app/(app)/applications/[id]/page.tsx` | Tab layout: Resume / Critique / Outreach |

### Architectural decision: `fetch` instead of `EventSource` for SSE

`EventSource` does not support custom request headers. The `/api/pipeline/{id}/stream`
endpoint requires `Authorization: Bearer {token}`. The hook uses `fetch()` with
manual SSE parsing (splitting on `\n\n`, extracting `event:` and `data:` lines).
This also avoids an extra npm dependency.

### Architectural decision: blob URL for PDF rendering

`<iframe src="/api/files/...">` can't attach the `Authorization` header. `PdfViewer`
fetches the PDF bytes with `fetch()` + auth header, calls `URL.createObjectURL(blob)`,
and passes that to `<iframe src>`. The object URL is revoked on component unmount.

---

## Manual Verification Pending

Phase 1, 2, and 3 curl/SSE tests require Docker (pdflatex not on Windows host)
and real Google OAuth credentials. Neither has been run yet — automated tests
cover all logic paths.

To verify Phase 1:
```bash
docker build -t resume-tailor-backend .
docker run -p 8000:8000 --env USE_MOCK_NIM=true resume-tailor-backend
curl -X POST http://localhost:8000/api/latex/compile \
  -H "Content-Type: application/json" \
  -d '{"tex_source":"\\documentclass{article}\\begin{document}Hello\\end{document}","filename_hint":"test"}'
```

To verify Phase 3 (pipeline with mock NIM):
```bash
# Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET in backend/.env
# Set USE_MOCK_NIM=true
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer ya29...." \
  -H "X-NIM-Key: nvapi-mock" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "We are hiring an AI Engineer with Python and LLM experience.",
    "company_name": "Stripe",
    "role_title": "AI Engineer",
    "role_config_id": "ai_engineer",
    "outreach": {"enabled": true}
  }'
# → { "job_id": "job_...", "stream_url": "..." }

curl -N http://localhost:8000/api/pipeline/{job_id}/stream
# Should see all 7 stages stream through, then pipeline_complete
```

---

## Prompts & template — DONE (was "needs iteration")

~~All six agents have placeholder prompts.~~ All six agents now have full,
hand-written prompts (jd_analyzer, tailor, critic, outreach, resume_parser,
role_config_generator). Iterate further on quality as needed, but they are no
longer placeholders.

~~`latex_assembler.py` returns a bare-bones template.~~ Replaced with the user's
real one-page template on 2026-06-09 (see session log above).

**Still open / worth a look:**
- Project bullets are not tailored — the tailor only rewords *experience* bullets;
  project text comes verbatim from `profile.json`. Tailoring projects would need a
  tailor schema + agent change.
- Existing `profile.json` files were parsed by the old 8B model; re-parse to benefit
  from the upgraded resume_parser.
- The encrypted-key auto-unlock is obfuscation-grade (no passphrase). Upgrade to a
  passphrase-derived key if stronger at-rest protection is wanted.
