# Implementation Plan

What to build in what order so each phase ships something demoable.

## Philosophy

- **Bottom-up within each phase** (Level 0 → 4 from `04-components.md`)
- **Each phase ends with a working thing**, even if ugly
- **Don't start phase N+1 until phase N is demoable**
- **Manual tests count** — automated tests are nice but not blocking

---

## Phase 0 — Repo Setup (You Do This Manually, No Claude Code Yet)

Goal: Project skeleton you understand cold.

### Tasks

```bash
# 1. Create repo
mkdir resume-tailor && cd resume-tailor
git init
mkdir -p frontend backend docs

# 2. Move design docs into place
# Copy CLAUDE.md to repo root
# Copy 01-data-schemas.md, 02-api-contract.md, 03-sequence-diagrams.md,
#       04-components.md, IMPLEMENTATION_PLAN.md into docs/

# 3. Backend skeleton
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install fastapi uvicorn pydantic pydantic-settings httpx python-multipart \
            google-api-python-client google-auth google-auth-oauthlib beautifulsoup4

pip freeze > requirements.txt

# Create folder structure
mkdir -p app/{routers,agents,services,orchestration,models,builtin_agents,latex_templates,utils}
mkdir -p tests/{unit,integration,fixtures}
touch app/main.py app/config.py app/deps.py
touch app/__init__.py
for d in routers agents services orchestration models utils; do
  touch app/$d/__init__.py
done

cd ..

# 4. Frontend skeleton
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*"
cd frontend

# Install dependencies we'll need
npm install @tanstack/react-query zustand
npm install codemirror @codemirror/lang-stex @codemirror/theme-one-dark
npm install lucide-react
npm install -D @types/node

# Create folder structure
mkdir -p components/{ui,editor,pipeline,critique,dashboard,outreach,onboarding,layout}
mkdir -p lib/{api,crypto,store,types}

cd ..

# 5. Initial commit
git add .
git commit -m "Initial project skeleton"
```

### Verification

- [ ] `cd backend && uvicorn app.main:app --reload` starts (will fail because main.py is empty, that's expected — fix in Phase 1)
- [ ] `cd frontend && npm run dev` shows Next.js default page
- [ ] `docs/` contains all five markdown files
- [ ] `CLAUDE.md` is in the repo root

---

## Phase 1 — Backend: One Endpoint End-to-End

Goal: `POST /api/latex/compile` works. Send a `.tex` string, get a PDF back.

This is the smallest possible vertical slice and it validates: FastAPI app, Pydantic models, LaTeX compilation, temp storage, file streaming, Docker.

### Open Claude Code

```bash
cd resume-tailor
claude
```

### Tasks (in order)

**1.1 — Setup core files (Level 0)**

Prompt Claude Code:
> "Read CLAUDE.md and docs/04-components.md. Implement the following Level 0 files: `app/config.py` (env-based Pydantic Settings as described), `app/utils/logging.py` (structured JSON logging with trace_id), `app/main.py` (minimal FastAPI app with a `/health` endpoint and CORS for `http://localhost:3000`). Show me the plan first."

**1.2 — Pydantic models for compile endpoint**

> "Create `app/models/errors.py` with the error code enum and `APIError` exception class from `docs/02-api-contract.md`. Create `app/models/latex.py` with `CompileRequest` and `CompileResponse` models matching the contract."

**1.3 — LaTeX compiler service (Level 1)**

> "Implement `app/services/latex_compiler.py` matching the spec in `docs/04-components.md`. Include `compile` (single pass) and `compile_one_page` (with trim ladder). For now, `compile_one_page` can take just `tex_source` instead of `tailored` — we'll wire the assembler in later. Write unit tests using a hardcoded sample .tex file."

**1.4 — Temp storage service (Level 1)**

> "Implement `app/services/temp_storage.py`. Stores files on local disk under `settings.temp_storage_dir`. Each file gets a UUID-based ID. Files older than `temp_storage_ttl_seconds` are cleaned up by a background task started in `main.py`'s lifespan."

**1.5 — Compile router (Level 4)**

> "Implement `app/routers/latex.py` with the `POST /api/latex/compile` and `GET /api/files/{file_id}` endpoints per `docs/02-api-contract.md`. Hook it into `main.py`. Use FastAPI dependency injection — `compile_endpoint` takes `LatexCompiler` and `TempStorage` as Depends."

**1.6 — Dockerfile**

> "Write a Dockerfile that installs texlive-latex-base + extra + fonts-recommended + fonts-extra + poppler-utils, then layers Python deps and app code per `docs/04-components.md`. Build it locally with `docker build -t resume-tailor-backend .`."

### Manual Verification (no frontend yet)

```bash
# Run locally
cd backend
uvicorn app.main:app --reload

# In another terminal — test compile
curl -X POST http://localhost:8000/api/latex/compile \
  -H "Content-Type: application/json" \
  -d '{
    "tex_source": "\\documentclass{article}\\begin{document}Hello\\end{document}",
    "filename_hint": "test"
  }'

# Should return: { "success": true, "pdf_id": "tmp_...", "pdf_url": "...", "pages": 1 }

# Fetch the PDF
curl http://localhost:8000/api/files/tmp_xxx -o test.pdf
open test.pdf  # or xdg-open / start
```

### Phase 1 Done When

- [ ] `curl` produces a real PDF
- [ ] Docker build succeeds
- [ ] `docker run -p 8000:8000 resume-tailor-backend` works the same way

---

## Phase 2 — Backend: Drive Integration + Auth

Goal: User can OAuth with Google, backend can read/write to their Drive.

### Tasks

**2.1 — Google OAuth service**

> "Implement `app/services/google_oauth.py`. Functions: `get_auth_url(state)`, `exchange_code(code) → tokens`. Set up credentials in `app/config.py`."

**2.2 — Drive client service**

> "Implement `app/services/google_drive.py` per the spec in `docs/04-components.md`. All async methods. Use `google-api-python-client`. Include the high-level `read_json` and `write_json` helpers."

**2.3 — Auth router**

> "Implement `app/routers/auth.py` with `GET /api/auth/google/url` and `POST /api/auth/google/callback`. Returns tokens to the frontend (frontend stores them)."

**2.4 — Setup router**

> "Implement `app/routers/setup.py` with `POST /api/setup/initialize`. Creates Resume_Tailor/ folder + _config/, role_configs/, applications/ subfolders. Idempotent — if folder exists, return existing ID."

**2.5 — Deps for Drive client**

> "Add `get_drive_token` and `get_drive_client` to `app/deps.py` per `docs/04-components.md`."

### Manual Verification

```bash
# Get auth URL
curl http://localhost:8000/api/auth/google/url

# Visit URL in browser, authorize, copy code from redirect URL
# Exchange code
curl -X POST http://localhost:8000/api/auth/google/callback \
  -H "Content-Type: application/json" \
  -d '{"code": "4/0...", "state": "..."}'

# Initialize folder
curl -X POST http://localhost:8000/api/setup/initialize \
  -H "Authorization: Bearer ya29...."

# Check your Drive — Resume_Tailor/ folder should exist
```

### Phase 2 Done When

- [ ] OAuth flow completes
- [ ] `Resume_Tailor/` folder appears in your Drive
- [ ] Subfolders exist

---

## Phase 3 — Backend: Profile & Pipeline (Mocked NIM)

Goal: Full pipeline runs end-to-end with **mocked** LLM responses. Real LLM later.

This lets you build everything without burning NIM calls during dev.

### Tasks

**3.1 — Profile models + router**

> "Implement `app/models/profile.py` matching `docs/01-data-schemas.md`. Implement `app/routers/profile.py` for GET/PUT /api/profile."

**3.2 — NIM client + mock**

> "Implement `app/services/nvidia_nim.py` per the spec. Also create `app/services/nvidia_nim_mock.py` — same interface, returns hardcoded JSON responses keyed by which agent is calling. Toggle via `settings.use_mock_nim = True`."

**3.3 — All agents**

> "Implement `app/agents/base.py`, then concrete agents: `jd_analyzer.py`, `tailor.py`, `critic.py`, `outreach.py`, `resume_parser.py`, `role_config_generator.py`. Each ~80-150 lines. Use placeholder prompts marked `# TODO: prompt iteration required` — I'll write the real prompts later."

**3.4 — Orchestration layer**

> "Implement `app/orchestration/inflight_tracker.py`, `app/orchestration/sse_emitter.py`, `app/orchestration/role_resolver.py`, `app/orchestration/pipeline_runner.py` per `docs/04-components.md`."

**3.5 — Pipeline router**

> "Implement `app/routers/pipeline.py` per `docs/02-api-contract.md`. All endpoints: run, stream, result, retry, retailor."

**3.6 — Built-in role configs**

> "Create `app/builtin_agents/ai_engineer.json` and `app/builtin_agents/software_engineer.json` matching the schema in `docs/01-data-schemas.md`. Use the strategies we documented (AI: lead with AI bullets, AI&ML skills first; SWE: lead with full-stack)."

### Manual Verification

```bash
# Trigger pipeline with mock NIM
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer ya29..." \
  -H "X-NIM-Key: nvapi-mock" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "We are hiring an AI Engineer...",
    "company_name": "Stripe",
    "role_title": "AI Engineer",
    "role_config_id": "ai_engineer",
    "outreach": {"enabled": true}
  }'
# → { "job_id": "...", "stream_url": "..." }

# Subscribe to SSE
curl -N http://localhost:8000/api/pipeline/{job_id}/stream
# Should see all stages stream past
```

### Phase 3 Done When

- [ ] SSE events stream in correct order
- [ ] Pipeline completes
- [ ] Files written to Drive's applications folder
- [ ] Dashboard endpoint `/api/applications` returns the new app

---

## Phase 4 — Frontend: Auth & Dashboard

Goal: User can log in via Google and see their dashboard.

### Tasks

**4.1 — Core libs**

> "Implement `lib/api/client.ts` (fetch wrapper with auth headers), `lib/store/auth.ts` (Zustand for tokens), `lib/types/*` (mirror backend Pydantic models)."

**4.2 — Auth pages**

> "Implement `app/(auth)/connect/page.tsx` (the 'Connect Drive' landing) and `app/(auth)/callback/page.tsx` (handles OAuth redirect, calls backend, stores tokens)."

**4.3 — Layout + sidebar**

> "Implement `app/(app)/layout.tsx` (auth guard — redirect to /connect if no token), `components/layout/Sidebar.tsx`, `components/layout/Header.tsx`."

**4.4 — Dashboard**

> "Implement `app/(app)/dashboard/page.tsx`, `components/dashboard/ApplicationsList.tsx`, `components/dashboard/ApplicationRow.tsx`, `components/dashboard/EmptyState.tsx`. Use TanStack Query to load /api/applications."

### Manual Verification

- [ ] Visit `localhost:3000` → see landing
- [ ] Click "Connect Drive" → Google OAuth flow
- [ ] Redirected back to `/dashboard`
- [ ] Empty state shows (or your test app from Phase 3 shows)

---

## Phase 5 — Frontend: Onboarding (Profile + Keys)

### Tasks

**5.1 — Encryption layer**

> "Implement `lib/crypto/encryption.ts`, `lib/crypto/keyDerivation.ts`, `lib/crypto/deviceTrust.ts`, `lib/crypto/secureStorage.ts` per `docs/04-components.md`. Write a roundtrip test."

**5.2 — API key onboarding step**

> "Implement `components/onboarding/ApiKeyStep.tsx`. User enters NIM key + passphrase. Validates key against backend, encrypts in browser, uploads via PUT /api/keys/encrypted-blob."

**5.3 — Resume upload step**

> "Implement `components/onboarding/ResumeUpload.tsx` and `components/onboarding/ProfileReviewForm.tsx`. Upload existing resume, show extracted profile in editable form with flagged fields highlighted, save via PUT /api/profile."

**5.4 — Onboarding flow router**

> "Implement `app/(app)/onboarding/api-key/page.tsx` and `app/(app)/onboarding/profile/page.tsx`. Auth guard checks if user has key + profile; redirect to onboarding if missing."

### Phase 5 Done When

- [ ] Fresh user goes through onboarding flow start to finish
- [ ] Profile JSON appears in their Drive after save
- [ ] Encrypted blob appears in `_config/` after key entry

---

## Phase 6 — Frontend: Pipeline UI + Editor

Goal: User can tailor a resume end-to-end through the UI.

### Tasks

**6.1 — Tailor form**

> "Implement `app/(app)/tailor/page.tsx`. Form: JD URL / JD text / company / role title / role select dropdown. Submit calls /api/pipeline/run, navigates to /pipeline/{jobId}."

**6.2 — Pipeline progress view**

> "Implement `app/(app)/pipeline/[jobId]/page.tsx`. Uses `useSSEStream` hook to show live stage progress. On complete, navigates to /application/{id}."

**6.3 — SSE hook**

> "Implement `components/pipeline/useSSEStream.ts` and `components/pipeline/PipelineProgress.tsx`, `components/pipeline/StageCard.tsx` per `docs/04-components.md`."

**6.4 — Editor + preview**

> "Implement `app/(app)/application/[id]/page.tsx` with split-pane layout. Left: `components/editor/LatexEditor.tsx` (CodeMirror). Right: `components/editor/PdfPreview.tsx` (`<iframe>` first, pdf.js later). Toolbar with Compile button calling /api/latex/compile, Save button calling /api/latex/save-to-application."

**6.5 — Critique card**

> "Implement `components/critique/ScoreBadge.tsx` (color-graded), `components/critique/CritiqueCard.tsx` with Re-tailor button calling /api/pipeline/retailor."

**6.6 — Outreach view**

> "Implement `app/(app)/application/[id]/outreach/page.tsx`, `components/outreach/MessagesList.tsx`, `components/outreach/OutreachCard.tsx`, `components/outreach/CopyButton.tsx`."

### Phase 6 Done When

- [ ] You can tailor a resume from URL paste to final PDF in the UI
- [ ] PDF preview renders
- [ ] You can edit LaTeX in-browser and recompile
- [ ] Critique score shows with correct color
- [ ] Outreach messages render and copy to clipboard

---

## Phase 7 — Polish + Real NIM

### Tasks

**7.1 — Switch from mock NIM to real**

> "Set `settings.use_mock_nim = False`. Test the full pipeline with a real NIM key."

**7.2 — Write the real prompts**

This is YOUR job, not Claude Code's. Iterate on each agent's prompt manually with real job descriptions. Update the prompts in `app/agents/*.py`. Test each agent in isolation:

```bash
python -m app.agents.tailor --test-with profile.json --jd "..."
```

**7.3 — Error handling polish**

> "Audit all error paths. Make sure every `APIError` has a clear `user_message`. Add error toast component."

**7.4 — Deploy**

> "Write `deployment/README.md`. Deploy backend to Railway (Docker image). Deploy frontend to Vercel. Update CORS origins. Configure env vars."

### Phase 7 Done When

- [ ] App is deployed at a public URL
- [ ] You can run a real tailor end-to-end
- [ ] Hand the URL to a friend

---

## Phase 8 — Friend Beta

### Tasks

- Add 5–10 friends as test users in Google Cloud Console
- Share the URL
- Collect feedback
- Fix bugs in priority order

---

## Estimated Timeline

| Phase | Time (weekend hours) |
|-------|----------------------|
| 0 — Setup | 2-3 hours |
| 1 — One endpoint | 4-6 hours |
| 2 — Drive auth | 4-6 hours |
| 3 — Mocked pipeline | 8-10 hours |
| 4 — Frontend auth | 4-6 hours |
| 5 — Onboarding | 6-8 hours |
| 6 — Pipeline UI + editor | 10-12 hours |
| 7 — Polish + deploy | 6-8 hours |
| **Total** | **~50 hours** |

Realistic if you do 8 hours/weekend: **6 weekends to demo-ready**.

---

## What Makes This Plan Work

1. **You can demo something after every phase.** Even Phase 1 ships a working compile endpoint you can curl.

2. **Backend before frontend.** Frontend depends on real APIs to talk to. Building UI against fake data leads to rework.

3. **Mocked NIM before real NIM.** You build the entire pipeline architecture without burning API quotas or waiting on LLM latency.

4. **Prompts are written manually by you.** This is your moat. Don't outsource prompt iteration to Claude Code.

5. **Layer rules are enforced from day one.** No retrofitting clean architecture later.

## What Makes This Plan Fail

- Trying to build everything at once
- Asking Claude Code to "build the whole pipeline"
- Skipping manual verification at each phase
- Letting Claude Code make architectural decisions without checking the docs
- Adding dependencies "just in case"

Read `CLAUDE.md` before every Claude Code session. Reference the docs. Build one thing at a time.
