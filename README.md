# Keyfit

**Tailored to the job. Owned by you.**

Keyfit tailors your LaTeX résumé to a specific job posting, then generates an AI critique and outreach messages to go with it. It runs on NVIDIA NIM (a free LLM API) and uses **your own Google Drive as the database** — every résumé, profile, and application lives in your Drive, not on our servers.

> Friends-beta. Built for a small group of users, not a public launch (yet).

---

## How It Works

1. **Connect Google Drive** — OAuth sign-in. Keyfit creates a `Resume_Tailor/` folder in your Drive and stores everything there.
2. **Set up your profile** — Upload your existing `.tex` résumé (auto-parsed into a structured achievement library) or fill the form by hand.
3. **Paste a job** — Drop in a job URL or the raw description, pick a target role.
4. **Watch it run** — A multi-stage pipeline streams live progress over SSE:
   - Analyze the job description
   - Select & lightly reword your best bullets for the role (never invents experience)
   - Assemble and compile a **guaranteed one-page** PDF
   - Score the résumé and list top fixes
   - Draft a cold email + LinkedIn outreach messages
5. **Review & iterate** — View the PDF, read the critique, copy the outreach. Re-tailor anytime; every version is saved to your Drive.

---

## Architecture

Strict four-layer backend. Lower layers never know about higher ones.

```
ROUTERS (HTTP)  →  ORCHESTRATION  →  AGENTS  →  SERVICES (external I/O)
```

**Core principles:**

- **Stateless backend** — no database, no sessions. The only server state is an in-memory dedup tracker for in-flight pipelines. All persistent data lives in the user's Drive.
- **Keys never persist on our infra** — your NVIDIA NIM key rides each request in an `X-NIM-Key` header and is request-scoped. The key is encrypted client-side (Web Crypto) before being saved to your Drive; the backend never sees the plaintext blob.
- **One LLM call per agent** — six single-purpose agents (JD analyzer, tailor, critic, outreach, résumé parser, role-config generator), orchestrated rather than chained inside one module.
- **Guaranteed one-page output** — the compiler runs `pdflatex`, checks the page count with `pdfinfo`, and walks a "trim ladder" that progressively reduces bullets in older roles until the résumé fits one page.
- **Explicit failures** — every error returns a structured schema (`code`, `stage`, `user_message`, `retry_possible`, `trace_id`); no raw exceptions reach the user.

---

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 16 (App Router) · TypeScript · Tailwind v4 · CodeMirror 6 · GSAP |
| Backend | FastAPI · Python 3.11 · Pydantic v2 · httpx |
| LaTeX | `pdflatex` + poppler (`pdfinfo`), in Docker |
| LLM | NVIDIA NIM (OpenAI-compatible REST API) |
| Storage | The user's Google Drive (no database) |
| State | TanStack Query (server) · Zustand (client) |
| Deployment | Vercel (frontend) · Render (backend) |

---

## Repository Layout

```
.
├── backend/          FastAPI app (routers, orchestration, agents, services)
│   ├── app/
│   ├── tests/        pytest (unit + integration)
│   └── Dockerfile    texlive + poppler + Python
├── frontend/         Next.js app (App Router)
├── docs/             Design contract — schemas, API, sequences, components
├── deployment/       Deploy notes
├── render.yaml       Render blueprint (backend)
└── CLAUDE.md         Architectural rules / project ground truth
```

The five files in `docs/` are the source-of-truth contract for how the system is built.

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google OAuth credentials (Client ID + Secret) for Drive access
- A free NVIDIA NIM API key from [build.nvidia.com](https://build.nvidia.com) — or run with mock LLM responses
- **Docker** (recommended) — `pdflatex` is not available on a bare Windows host

### Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate   ·   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET

python run.py          # http://127.0.0.1:8000  (sets the Windows-safe event loop)
```

Run with mock LLM responses (no NIM key, no real LaTeX needed for logic paths):

```bash
USE_MOCK_NIM=true python run.py
```

Full PDF compilation needs the Docker image (bundles texlive + poppler):

```bash
docker build -t keyfit-backend ./backend
docker run -p 8000:8000 --env USE_MOCK_NIM=true keyfit-backend
```

Tests:

```bash
cd backend && pytest
```

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev            # http://localhost:3000
```

---

## Environment Variables

**Backend** (`backend/.env`):

| Var | Purpose |
|-----|---------|
| `ENVIRONMENT` | `development` or `production` |
| `CORS_ORIGINS` | Allowed frontend origins |
| `NIM_BASE_URL` | `https://integrate.api.nvidia.com/v1` |
| `USE_MOCK_NIM` | `true` to use canned LLM responses |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Drive OAuth |
| `GOOGLE_REDIRECT_URI` | e.g. `http://localhost:3000/callback` |
| `TEMP_STORAGE_DIR` / `TEMP_STORAGE_TTL_SECONDS` | In-flight PDF temp files (10-min TTL) |

**Frontend** (`frontend/.env.local`):

| Var | Purpose |
|-----|---------|
| `NEXT_PUBLIC_API_URL` | Backend base URL |

The user's NVIDIA NIM key is **never** an environment variable — it's entered in the app, encrypted client-side, and stored in the user's Drive.

---

## Deployment

- **Frontend → Vercel.** Standard Next.js deploy; set `NEXT_PUBLIC_API_URL` to the backend URL.
- **Backend → Render.** Use the included [`render.yaml`](render.yaml) blueprint (Dashboard → New → Blueprint). Render provisions the Docker service and prompts for the secret env vars (`GOOGLE_*`, `CORS_ORIGINS`).

---

## Design Notes

- **The achievement library is sacred.** The tailor agent only selects and lightly rewords bullets that already exist in your profile to surface job keywords. It never fabricates metrics or experience — validation enforces that every selected bullet ID exists in the source profile.
- **Custom vs. built-in agents are invisible.** Built-in roles (AI Engineer, Software Engineer) and auto-generated ones (any other role) look identical to the user. The role resolver picks built-in → your saved config → freshly generated, silently.
- **Progress is SSE, PDFs are streamed.** Pipeline stages emit Server-Sent Events; compiled PDFs are fetched by `pdf_id`, never base64-embedded in JSON.

---

## Trademark & Affiliation

"Keyfit" here refers solely to this open-source résumé-tailoring project. It is **not affiliated with, endorsed by, or connected to** any other product or company using a similar name — including Chicco/Artsana's "KeyFit"® car seats or "Keyfit Tools." All other trademarks are the property of their respective owners.

---

## License

[MIT](LICENSE) © 2026 Sumanth

