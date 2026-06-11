# Resume Tailor — Project Rules for Claude Code

This file is your ground truth for this project. Read it at the start of every session. Reference it when making architectural decisions. Do not deviate from the rules below without explicit confirmation from the user.

---

## What This Project Is

A web app that tailors a user's LaTeX resume to a specific job posting, with AI-generated critique and outreach messages. Powered by NVIDIA NIM (free LLM API). The user's Google Drive is the database — everything persists there.

**Initial users:** The owner (Sumanth) and 5–10 friends. This is a friends-beta, not a public product (yet).

**Tech stack:**
- Frontend: Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui + CodeMirror 6 + pdf.js
- Backend: FastAPI + Python 3.11 + Pydantic v2 + httpx
- LaTeX: pdflatex + poppler (pdfinfo) in Docker
- LLM: NVIDIA NIM (OpenAI-compatible REST API)
- Storage: User's Google Drive (no database)
- Deployment: Vercel (frontend) + Railway (backend)

---

## Non-Negotiable Architectural Rules

### Rule 1: The backend is stateless

- **No database.** No PostgreSQL, no MongoDB, no SQLite — none.
- **No session storage.** No Redis sessions, no server-side cookies holding state.
- **No file storage owned by us.** Temp files for in-flight PDFs only (10-min TTL).
- All persistent user data lives in the user's own Google Drive.
- If you find yourself wanting to add a database, stop and check with the user first.

**Exception:** An in-memory `inflight_tracker` dict for pipeline deduplication is allowed (see "Option C" in design docs).

### Rule 2: API keys never persist on our infrastructure

- User's NVIDIA NIM key is sent on every request via `X-NIM-Key` header.
- Backend uses it for that request, then it's gone (request-scoped).
- Key is encrypted client-side (Web Crypto API) before being stored in user's Drive.
- Backend never sees the encrypted blob's plaintext.

### Rule 3: Four-layer architecture (strict)

```
ROUTERS (HTTP)  →  ORCHESTRATION  →  AGENTS  →  SERVICES (external I/O)
```

Lower layers never know about higher layers. A router never calls an agent directly — it calls orchestration, which calls agents. A service never calls another service. An agent never calls another agent.

### Rule 4: One LLM call per agent

Each agent module makes exactly one LLM call. If you need multiple LLM calls in sequence, create multiple agents and orchestrate them at the orchestration layer.

### Rule 5: Achievement library is sacred

The tailor agent selects bullets from the user's `profile.json` achievement library. It may lightly reword bullets to surface JD keywords. It **never invents new bullets, fake metrics, or fabricates experience**. Validation enforces that all `selected_ids` returned by the tailor agent exist in the source profile.

### Rule 6: Custom vs auto-generated agents are invisible to the user

The user never sees a difference between built-in agents (AI Engineer, Software Engineer) and auto-generated configs (Data Analyst, anything else). No badges. No "Generating custom agent..." messages. The role resolver picks the right path silently.

Role lookup order:
1. Built-in (`app/builtin_agents/{role_id}.json` in codebase)
2. User's saved auto-generated (`Resume_Tailor/role_configs/{role_id}.json` in their Drive)
3. Generate new via LLM, save to user's Drive, then use

### Rule 7: One-page LaTeX output is guaranteed

The compiler runs `pdflatex` then checks page count with `pdfinfo`. If pages > 1, it walks a "trim ladder" that progressively reduces bullets in older roles. The first version that fits one page wins.

### Rule 8: Failures are explicit, not silent

- Every error returns the standard error schema (`code`, `stage`, `user_message`, `retry_possible`, `trace_id`).
- Error codes come from a fixed enum in `app/models/errors.py`.
- Never raise a raw Python exception to the user. Wrap in a `StageError` or `APIError`.

### Rule 9: SSE for pipeline progress, not WebSocket

The pipeline emits events via Server-Sent Events. Each stage emits `stage_started`, `stage_completed`, or `stage_failed`. The stream ends with `pipeline_complete` or a terminal `stage_failed`.

Do not add WebSocket support unless explicitly requested.

### Rule 10: PDF delivery is streamed, not base64

Compile endpoint returns a `pdf_id` referring to a temp file. Frontend fetches the file from `/api/files/{pdf_id}`. PDFs are never embedded in JSON responses.

---

## What I Want You To Do Before Writing Code

For every feature or component:

1. **Read `docs/`** — the four design sections are the source of truth.
2. **Identify the layer** — is this a router, orchestration, agent, or service?
3. **Identify the dependencies** — what level is it on (see `docs/04-components.md` build order)?
4. **Tell me the plan before writing** — list the file(s) you'll create, the functions/classes, and how they hook into existing code. Wait for my confirmation.
5. **Write tests alongside the code.** Pytest for backend, Vitest for frontend.

---

## What I Want You To Not Do

- **Don't scaffold the whole project at once.** Build one file at a time.
- **Don't add dependencies without asking.** Every new pip/npm package should be justified.
- **Don't over-abstract.** No factory patterns, no dependency injection containers, no premature interfaces. If there's one implementation, use a class directly.
- **Don't add caching, queues, or background workers unless I ask.** This is a friends-beta, not Google.
- **Don't write LLM prompts on your own.** Prompts are the user's responsibility. You may write a placeholder prompt, but mark it clearly with `# TODO: prompt iteration required` so the user can replace it.
- **Don't store secrets in code.** Use `.env` files and `app/config.py` Settings.
- **Don't write code that doesn't compile or pass its tests.** If you're unsure, run the test first.

---

## Coding Conventions

### Python (Backend)

- Python 3.11+ syntax. Use union types (`str | None`, not `Optional[str]`).
- Type hints on every function signature.
- Pydantic v2 for all request/response models.
- `async def` for any function that does I/O.
- Logging via structured logger (see `app/utils/logging.py`). Include `trace_id` in every log line.
- Docstrings on public functions: one-line description, then args/returns if non-obvious.
- Imports sorted: stdlib, third-party, local — separated by blank lines.

### TypeScript (Frontend)

- TypeScript strict mode. No `any` types except in unavoidable third-party gaps.
- Functional React components only (no class components).
- Server state in TanStack Query, client state in Zustand. Don't mix.
- Tailwind for styling. Avoid inline `style={}` except for dynamic values.
- Component file = one default export. Helpers go in same file if small, separate `.helpers.ts` if growing.
- Path imports: `@/components/...`, `@/lib/...` (configure in tsconfig).

### Both

- Small files. If a file exceeds ~300 lines, ask whether to split it.
- Names are descriptive. `compile_with_page_fit` not `compile2` or `do_compile`.
- Comments explain *why*, not *what*. Code shows the what.

---

## Testing Strategy

**Backend:**
- Unit tests for pure functions (latex escape, role resolver logic, etc.) — fast, no I/O.
- Integration tests for routers, with NIM and Drive mocked at the service layer.
- One end-to-end test for the full pipeline using `pytest-asyncio` and a stubbed NIM client.

**Frontend:**
- Vitest for utilities and hooks.
- React Testing Library for components — test behavior, not implementation.
- No e2e tests in Phase 1 (manual testing in browser is fine).

**Coverage target:** No specific number. Test the parts that are most likely to break: agent output parsing, page-fit ladder, role resolver, encryption round-trip.

---

## How to Communicate With Me

- **Show me the plan first.** Before writing 100 lines, write 5 lines describing what you'll do. I'll say "go" or push back.
- **Ask when uncertain.** "Should this be a service or an agent?" is a great question. Don't guess on architecture.
- **Surface tradeoffs.** If you see two ways to do something, list both and recommend one with reasoning.
- **Push back when I'm wrong.** If I ask for something that contradicts these rules, point it out before doing it.

---

## When Things Break

1. Read the actual error message carefully. Don't guess.
2. Check whether the failing component matches the design docs.
3. If a dependency is missing, that's a build-order violation — flag it.
4. If a test is failing, fix the code, not the test (unless the test itself is wrong).
5. Don't add `try/except: pass` to silence errors. Ever.

---

## Files In This Repo You Should Read First

- `docs/01-data-schemas.md` — Drive file structure (what everything looks like)
- `docs/02-api-contract.md` — Every endpoint
- `docs/03-sequence-diagrams.md` — How the flows actually run
- `docs/04-components.md` — File-by-file breakdown
- `docs/IMPLEMENTATION_PLAN.md` — What to build in what order

These five files are the contract. Code that contradicts them is wrong.
