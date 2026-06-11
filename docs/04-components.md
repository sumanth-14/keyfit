# 04 — Components

The file structure, layer rules, and build order. Read this before opening Claude Code.

## The Four-Layer Rule (Critical)

```
ROUTERS (HTTP)  →  ORCHESTRATION  →  AGENTS  →  SERVICES (external I/O)
```

Lower layers never know about higher layers. **Never skip a layer upward.**

- A router never calls an agent directly — calls orchestration.
- A service never calls another service.
- An agent never calls another agent.

When tempted to violate this, stop and rethink.

---

## Backend File Structure

```
backend/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
│
├── app/
│   ├── main.py                         FastAPI instance, middleware
│   ├── config.py                       env vars (Pydantic Settings)
│   ├── deps.py                         FastAPI dependency injection
│   │
│   ├── routers/                        HTTP layer
│   │   ├── auth.py                     Google OAuth
│   │   ├── setup.py                    Folder creation
│   │   ├── profile.py                  Profile CRUD + parse-from-resume
│   │   ├── keys.py                     Encrypted blob CRUD + validate
│   │   ├── roles.py                    Role listing + selection
│   │   ├── pipeline.py                 Run, stream, retry, retailor
│   │   ├── latex.py                    Compile + save-to-application
│   │   ├── applications.py             Dashboard list + detail + versions
│   │   └── files.py                    PDF streaming
│   │
│   ├── agents/                         One LLM call each
│   │   ├── base.py                     Agent ABC
│   │   ├── jd_analyzer.py
│   │   ├── tailor.py
│   │   ├── critic.py
│   │   ├── outreach.py
│   │   ├── resume_parser.py
│   │   └── role_config_generator.py
│   │
│   ├── services/                       External integrations
│   │   ├── nvidia_nim.py               NIM client (retry, backoff)
│   │   ├── google_drive.py             Drive API wrapper
│   │   ├── google_oauth.py             OAuth token exchange
│   │   ├── latex_compiler.py           pdflatex + pdfinfo + page-fit
│   │   ├── job_scraper.py              URL → JD text
│   │   └── temp_storage.py             Temp PDF file management
│   │
│   ├── orchestration/                  Pipeline coordination
│   │   ├── pipeline_runner.py          Sequences agents
│   │   ├── sse_emitter.py              SSE event broadcaster
│   │   ├── inflight_tracker.py         In-memory dedup
│   │   └── role_resolver.py            built-in > saved > generate
│   │
│   ├── models/                         Pydantic schemas
│   │   ├── profile.py
│   │   ├── role_config.py
│   │   ├── pipeline.py
│   │   ├── critique.py
│   │   ├── outreach.py
│   │   ├── application.py
│   │   └── errors.py
│   │
│   ├── builtin_agents/                 Hand-tuned configs
│   │   ├── ai_engineer.json
│   │   └── software_engineer.json
│   │
│   ├── latex_templates/
│   │   └── one_page_compact.tex        From the Colab notebook
│   │
│   └── utils/
│       ├── logging.py                  Structured logs + trace_id
│       └── latex_escape.py
│
└── tests/
    ├── conftest.py
    ├── unit/
    ├── integration/
    └── fixtures/
```

---

## Frontend File Structure

```
frontend/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
│
├── app/                                Next.js App Router
│   ├── layout.tsx                      Root layout + providers
│   ├── page.tsx                        Landing
│   │
│   ├── (auth)/
│   │   ├── connect/page.tsx            "Connect Drive"
│   │   └── callback/page.tsx           OAuth callback
│   │
│   ├── (app)/                          Authenticated routes
│   │   ├── layout.tsx                  Sidebar + auth guard
│   │   ├── dashboard/page.tsx          Applications list
│   │   ├── onboarding/
│   │   │   ├── api-key/page.tsx        Step 1
│   │   │   └── profile/page.tsx        Step 2
│   │   ├── tailor/page.tsx             New tailor form
│   │   ├── pipeline/[jobId]/page.tsx   Pipeline progress
│   │   ├── application/[id]/
│   │   │   ├── page.tsx                Editor + preview
│   │   │   └── outreach/page.tsx       Outreach tab
│   │   └── settings/
│   │       ├── keys/page.tsx
│   │       ├── profile/page.tsx
│   │       └── devices/page.tsx
│   │
│   └── api/
│       └── auth/callback/route.ts      Code exchange proxy
│
├── components/
│   ├── ui/                             shadcn primitives
│   │
│   ├── editor/
│   │   ├── LatexEditor.tsx             CodeMirror 6 wrapper
│   │   ├── PdfPreview.tsx              <iframe> or pdf.js
│   │   ├── EditorToolbar.tsx
│   │   └── SplitPane.tsx
│   │
│   ├── pipeline/
│   │   ├── PipelineProgress.tsx
│   │   ├── StageCard.tsx
│   │   ├── PipelineErrorView.tsx
│   │   └── useSSEStream.ts             SSE custom hook
│   │
│   ├── critique/
│   │   ├── ScoreBadge.tsx              Color-graded badge
│   │   ├── CritiqueCard.tsx
│   │   └── CritiqueDetails.tsx
│   │
│   ├── dashboard/
│   │   ├── ApplicationsList.tsx
│   │   ├── ApplicationRow.tsx
│   │   ├── EmptyState.tsx
│   │   └── FilterBar.tsx
│   │
│   ├── outreach/
│   │   ├── OutreachCard.tsx
│   │   ├── MessagesList.tsx
│   │   └── CopyButton.tsx
│   │
│   ├── onboarding/
│   │   ├── ApiKeyStep.tsx
│   │   ├── ResumeUpload.tsx
│   │   ├── ProfileReviewForm.tsx
│   │   └── FlagsList.tsx
│   │
│   └── layout/
│       ├── Sidebar.tsx
│       ├── Header.tsx
│       └── UserMenu.tsx
│
├── lib/
│   ├── api/                            API client per domain
│   │   ├── client.ts                   Base with auth headers
│   │   ├── auth.ts
│   │   ├── pipeline.ts
│   │   ├── profile.ts
│   │   ├── applications.ts
│   │   ├── latex.ts
│   │   └── keys.ts
│   │
│   ├── crypto/                         Browser-side encryption
│   │   ├── encryption.ts               AES-GCM
│   │   ├── keyDerivation.ts            PBKDF2
│   │   ├── deviceTrust.ts              Device key handling
│   │   └── secureStorage.ts            IndexedDB wrapper
│   │
│   ├── store/                          Zustand
│   │   ├── auth.ts
│   │   ├── keys.ts                     In-memory only!
│   │   ├── profile.ts
│   │   └── pipeline.ts
│   │
│   └── types/                          Match Pydantic models
│       ├── profile.ts
│       ├── pipeline.ts
│       ├── critique.ts
│       └── application.ts
│
└── public/
```

---

## Component Specs (Key Ones)

### Backend: `app/agents/base.py`

```python
class Agent(ABC):
    """Base class for all LLM agents."""
    
    def __init__(self, nim_client: NimClient, model: str):
        self.nim = nim_client
        self.model = model
    
    @abstractmethod
    def system_prompt(self) -> str: ...
    
    @abstractmethod
    def user_prompt(self, **inputs) -> str: ...
    
    @abstractmethod
    def parse_response(self, raw: str) -> dict: ...
    
    async def run(self, **inputs) -> dict:
        raw = await self.nim.complete(
            model=self.model,
            system=self.system_prompt(),
            user=self.user_prompt(**inputs),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return self.parse_response(raw)
```

Each concrete agent is ~80–150 lines: prompts + validation.

### Backend: `app/agents/tailor.py` — Spec

```python
class TailorAgent(Agent):
    temperature = 0.3
    max_tokens = 4096
    
    def system_prompt(self) -> str:
        # "You select bullets from user's library. Output JSON only.
        #  Never fabricate experience."
        ...
    
    def user_prompt(self, profile, jd_analysis, role_config, prev_critique=None) -> str:
        # Build prompt with profile, analysis, role config
        # If prev_critique: append "Last attempt missed: ... Incorporate
        # ONLY if profile genuinely matches."
        ...
    
    def parse_response(self, raw: str) -> dict:
        # Strip markdown fences
        # json.loads
        # Validate selected_ids ⊆ profile.experience[*].bullets[*].id
        # Raise TailorOutputError if invalid
        ...
```

### Backend: `app/orchestration/pipeline_runner.py` — Spec

~300 lines. Sequences stages, emits SSE events, handles errors.

```python
class PipelineRunner:
    def __init__(self, drive_client, nim_client, sse_emitter):
        ...
    
    async def run(self, job_id: str, request: PipelineRequest):
        try:
            jd_text = await self._stage_scrape(job_id, request)
            jd_analysis = await self._stage_analyze(job_id, jd_text)
            profile = await self._load_profile()
            role_config = await self._resolve_role_config(request.role_config_id)
            tailored = await self._stage_tailor(job_id, profile, jd_analysis, role_config)
            pdf_id, final_latex = await self._stage_compile(job_id, tailored)
            critique = await self._stage_critique(job_id, final_latex, jd_analysis)
            outreach = await self._stage_outreach(...) if request.outreach.enabled else None
            app_id = await self._stage_persist(...)
            await self.sse_emitter.emit(job_id, "pipeline_complete", {"application_id": app_id})
        except StageError as e:
            await self.sse_emitter.emit(job_id, "stage_failed", e.to_dict())
        finally:
            self.inflight_tracker.release(job_id)
    
    async def run_retailor(self, job_id, application_id):
        # Load app, check version count < 3
        # Run tailor with augmented prompt
        # Compile, critique, compare scores
        # Promote or auto-revert
        ...
```

### Backend: `app/orchestration/role_resolver.py` — Spec

```python
class RoleResolver:
    def __init__(self, drive_client, role_generator_agent):
        self.drive = drive_client
        self.generator = role_generator_agent
        self.builtin_dir = Path(__file__).parent.parent / "builtin_agents"
    
    async def resolve(self, role_id: str) -> RoleConfig:
        # 1. Check built-in (codebase)
        builtin_path = self.builtin_dir / f"{role_id}.json"
        if builtin_path.exists():
            return RoleConfig(**json.loads(builtin_path.read_text()))
        
        # 2. Check user's Drive
        config = await self.drive.read_json(f"{role_id}.json", parent_id=...)
        if config:
            return RoleConfig(**config)
        
        # 3. Generate via LLM, save, return
        generated = await self.generator.run(role_id=role_id)
        await self.drive.write_json(f"{role_id}.json", generated.model_dump(), parent_id=...)
        return generated
```

### Backend: `app/services/latex_compiler.py` — Spec

```python
class LatexCompiler:
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
    
    async def compile(self, tex_source: str, filename: str) -> CompileResult:
        # Write .tex, run pdflatex twice, run pdfinfo, return result
        ...
    
    async def compile_one_page(self, tailored, filename, latex_assembler) -> CompileResult:
        # Walk trim ladder:
        # [3,3,2,1] → [3,3,1,1] → [3,2,1,1] → [3,2,1,0] → [2,2,1,0]
        # Return first version that fits one page
        ...
```

### Backend: `app/services/nvidia_nim.py` — Spec

```python
class NimClient:
    def __init__(self, api_key: str, base_url: str):
        ...
    
    async def complete(self, model, system, user, temperature, max_tokens) -> str:
        # POST to NIM with 4-attempt retry
        # 429: wait 15s × attempt
        # 5xx: wait 10s, retry
        # Timeout (90s): one retry
        # Raise NimError on final failure
        ...
```

### Frontend: `components/pipeline/useSSEStream.ts` — Spec

The most important custom hook.

```tsx
function useSSEStream(streamUrl: string | null) {
  const [stages, setStages] = useState<StageStatus[]>([])
  const [error, setError] = useState<PipelineError | null>(null)
  const [result, setResult] = useState<PipelineResult | null>(null)
  
  useEffect(() => {
    if (!streamUrl) return
    
    const source = new EventSource(streamUrl, { withCredentials: true })
    
    source.addEventListener("stage_started", (e) => { ... })
    source.addEventListener("stage_completed", (e) => { ... })
    source.addEventListener("stage_failed", (e) => {
      setError(JSON.parse(e.data).error)
      source.close()
    })
    source.addEventListener("pipeline_complete", (e) => {
      setResult(JSON.parse(e.data))
      source.close()
    })
    
    return () => source.close()
  }, [streamUrl])
  
  return { stages, error, result }
}
```

### Frontend: `lib/crypto/encryption.ts` — Spec

Uses Web Crypto API. ~80 lines, no dependencies.

```ts
export async function encryptApiKey(
  plaintext: string,
  passphrase: string,
  salt: Uint8Array
): Promise<EncryptedBlob>

export async function decryptApiKey(
  blob: EncryptedBlob,
  passphrase: string
): Promise<string>

// Key derivation: PBKDF2-SHA256, 100k iterations
// Encryption: AES-GCM, 256-bit key, random IV per encryption
// Returns { ciphertext, iv, salt } — all base64
```

### Frontend: `lib/crypto/deviceTrust.ts` — Spec

Trust-this-device mechanism.

```ts
// First trust:
//   1. User enters passphrase, decrypts API key
//   2. Generate random device_key (256-bit)
//   3. Store plaintext device_key in IndexedDB
//   4. Encrypt API key with device_key
//   5. Wrap device_key with passphrase-derived key
//   6. Store wrapped device_key in api_keys.enc.json on Drive
//
// Subsequent sessions on same device:
//   1. Read api_keys.enc.json
//   2. Look up device_id in trusted_devices
//   3. Read plaintext device_key from IndexedDB
//   4. Decrypt API key directly (no passphrase)
//
// Untrust:
//   1. Remove device_id from trusted_devices on Drive
//   2. Other devices fall back to passphrase prompt next session
```

---

## Build Order (Dependency Levels)

Build strictly bottom-up. A Level N component should compile and pass tests before any Level N+1 component that depends on it.

```
LEVEL 0 (no dependencies):
  - app/config.py
  - app/utils/logging.py
  - app/utils/latex_escape.py
  - app/models/*  (all Pydantic schemas)
  - lib/types/*   (all TypeScript types)
  - components/ui/* (shadcn primitives)

LEVEL 1 (depend on Level 0):
  - app/services/nvidia_nim.py
  - app/services/google_drive.py
  - app/services/latex_compiler.py
  - app/services/job_scraper.py
  - app/services/temp_storage.py
  - lib/api/client.ts
  - lib/crypto/*

LEVEL 2 (depend on services):
  - app/agents/*
  - app/orchestration/role_resolver.py
  - app/orchestration/inflight_tracker.py
  - app/orchestration/sse_emitter.py
  - lib/store/*
  - lib/api/* (per-domain)

LEVEL 3 (depend on agents + services):
  - app/orchestration/pipeline_runner.py
  - components/editor/*
  - components/pipeline/*
  - components/critique/*
  - components/dashboard/*

LEVEL 4 (depend on everything):
  - app/routers/*
  - app/main.py
  - Next.js pages
```

**The discipline that matters:** never start a Level 3 component if Level 2 isn't done. This prevents the "everything is half-finished" trap.
