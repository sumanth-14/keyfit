# 02 — API Contract

Every endpoint the frontend talks to. Every request shape. Every response shape. Every error code.

## Conventions

- **Base URL:** `https://api.resumetailor.app` (placeholder, set via `NEXT_PUBLIC_API_URL`)
- **Auth:** `Authorization: Bearer {google_oauth_access_token}` on any endpoint touching Drive
- **NIM Key:** `X-NIM-Key: nvapi-...` on any endpoint making LLM calls
- **Idempotency:** Optional `Idempotency-Key: {uuid}` on mutating endpoints
- **Response format:** JSON (except SSE and file streams)
- **HTTP status codes:** Standard — 200 success, 202 accepted (async), 400 bad request, 401 unauthorized, 404 not found, 409 conflict, 500 internal

---

## Standard Error Response

Every error returns this shape, never raw stack traces:

```json
{
  "error": {
    "code": "AGENT_FAILED",
    "stage": "tailor_agent",
    "user_message": "The AI couldn't generate a valid resume. This sometimes happens with very long job descriptions.",
    "technical_details": "Expecting ',' delimiter at line 47 col 12",
    "retry_possible": true,
    "retry_hint": "Try the same input — most retries succeed.",
    "trace_id": "req_a8f7c2"
  }
}
```

---

## Error Code Enum

```
SCRAPE_FAILED            — Job URL couldn't be fetched
SCRAPE_BLOCKED           — Site (LinkedIn) blocks scrapers
JD_ANALYZER_FAILED       — LLM returned invalid JSON
TAILOR_FAILED            — LLM returned invalid output
TAILOR_NO_BULLETS        — User's profile has no relevant bullets
LATEX_COMPILE_FAILED     — pdflatex errored
PAGE_FIT_FAILED          — Even max trim doesn't fit on one page
CRITIC_FAILED            — Critique LLM call failed
OUTREACH_FAILED          — Outreach LLM call failed
DRIVE_AUTH_EXPIRED       — User needs to reconnect Drive
DRIVE_QUOTA_EXCEEDED     — User's Drive is full
NIM_KEY_INVALID          — NVIDIA key rejected
NIM_RATE_LIMITED         — Too many requests, backoff
NIM_MODEL_UNAVAILABLE    — Specified model deprecated/down
PROFILE_NOT_FOUND        — User hasn't done onboarding
PROFILE_INCOMPLETE       — Profile missing required fields
TOO_MANY_RETAILORS       — Hit cap of 3 re-tailors per application
PIPELINE_NOT_FOUND       — job_id doesn't exist or expired
INTERNAL_ERROR           — Catch-all for unexpected failures
```

---

## Group 1: Auth & Setup

### `GET /api/auth/google/url`

Returns Google OAuth URL.

**Response 200:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "state": "random-csrf-token"
}
```

### `POST /api/auth/google/callback`

Frontend posts OAuth code after redirect.

**Request:**
```json
{ "code": "4/0AeanS...", "state": "random-csrf-token" }
```

**Response 200:**
```json
{
  "access_token": "ya29....",
  "refresh_token": "1//0e...",
  "expires_in": 3599,
  "user_email": "user@gmail.com",
  "tailor_folder_exists": false
}
```

### `POST /api/setup/initialize`

Creates `Resume_Tailor/` folder structure in user's Drive. Idempotent.

**Headers:** `Authorization: Bearer ...`  
**Request body:** empty  
**Response 200:**
```json
{
  "folder_id": "1AbCdEf...",
  "subfolders_created": ["_config", "role_configs", "applications"],
  "ready": true
}
```

---

## Group 2: Profile Management

### `POST /api/profile/parse-from-resume`

User uploads existing resume. LLM extracts achievement library.

**Headers:** `Authorization: Bearer ...`, `X-NIM-Key: nvapi-...`  
**Request (multipart):**
- `file`: the resume file
- `format`: `"tex" | "pdf" | "docx"`

**Response 200:**
```json
{
  "profile": { /* full profile.json schema */ },
  "extraction_confidence": {
    "personal": 1.0,
    "education": 0.95,
    "experience": 0.82,
    "projects": 0.70,
    "skills": 0.90
  },
  "flagged_fields": [
    {"path": "experience[2].bullets[0].metrics", "reason": "no_numeric_value_found"},
    {"path": "projects[0].url", "reason": "missing"}
  ],
  "raw_extracted_text": "..."
}
```

### `GET /api/profile`

**Headers:** `Authorization: Bearer ...`  
**Response 200:** Full profile.json  
**Response 404:** `PROFILE_NOT_FOUND` (user hasn't done onboarding)

### `PUT /api/profile`

Replaces profile entirely. No partial updates.

**Headers:** `Authorization: Bearer ...`  
**Request body:** Full profile object  
**Response 200:** `{ "saved": true, "version": 1 }`

---

## Group 3: API Keys (Encrypted Storage)

Backend never sees plaintext keys. Frontend encrypts in browser using Web Crypto API.

### `GET /api/keys/encrypted-blob`

**Headers:** `Authorization: Bearer ...`  
**Response 200:**
```json
{
  "exists": true,
  "encryption": {
    "algorithm": "AES-GCM",
    "key_derivation": "PBKDF2-SHA256",
    "iterations": 100000,
    "salt": "base64..."
  },
  "encrypted_payload": "base64...",
  "trusted_devices": [
    {"device_id": "...", "device_label": "...", "added_at": "..."}
  ]
}
```

**Response 404:** No blob yet (first time)

### `PUT /api/keys/encrypted-blob`

Frontend encrypts, posts ciphertext only.

**Headers:** `Authorization: Bearer ...`  
**Request:** Same shape as GET response (minus `exists`)  
**Response 200:** `{ "saved": true }`

### `POST /api/keys/validate`

Tests whether a NIM key works without storing it.

**Request:** `{ "nim_api_key": "nvapi-..." }`  
**Response 200:** `{ "valid": true, "models_accessible": 47 }`  
**Response 400:** `NIM_KEY_INVALID`

---

## Group 4: Role Configs

### `GET /api/roles/available`

Returns all roles (built-in + user's auto-generated). Frontend doesn't see the distinction.

**Headers:** `Authorization: Bearer ...`  
**Response 200:**
```json
{
  "roles": [
    {"id": "ai_engineer", "display_name": "AI Engineer"},
    {"id": "software_engineer", "display_name": "Software Engineer"},
    {"id": "data_analyst", "display_name": "Data Analyst"}
  ]
}
```

### `POST /api/roles/select`

User picks a role. Backend resolves: built-in > saved auto-gen > generate new.

**Headers:** `Authorization: Bearer ...`, `X-NIM-Key: nvapi-...`  
**Request:** `{ "role_id": "data_analyst" }`  
**Response 200:**
```json
{
  "role_id": "data_analyst",
  "display_name": "Data Analyst",
  "ready": true,
  "generated_now": false
}
```

`generated_now: true` means an LLM call happened (slower). Frontend can show "Setting up..." messaging if true.

---

## Group 5: Pipeline (The Main Event)

### `POST /api/pipeline/run`

Starts a full pipeline. Returns immediately with `job_id`.

**Headers:** `Authorization: Bearer ...`, `X-NIM-Key: nvapi-...`  
**Request:**
```json
{
  "job_url": "https://stripe.com/jobs/abc",
  "job_description": null,
  "company_name": "Stripe",
  "role_title": "Software Engineer",
  "role_config_id": "ai_engineer",
  "outreach": {
    "enabled": true,
    "contact_name": "Sarah Chen",
    "contact_type": "Recruiter"
  }
}
```

Either `job_url` OR `job_description` must be provided. If both, `job_description` wins.

**Response 202:**
```json
{
  "job_id": "job_a8f7c2",
  "status": "running",
  "stream_url": "/api/pipeline/job_a8f7c2/stream",
  "new": true
}
```

**Idempotency (Option C):** If same user submits same `(role_config_id, company, role_title, url_or_jd_hash)` while pipeline still running, returns existing `job_id` with `"new": false`.

### `GET /api/pipeline/{job_id}/stream` (SSE)

Frontend opens `EventSource(stream_url)`. Backend emits events:

```
event: stage_started
data: {"stage": "scrape", "timestamp": "..."}

event: stage_completed
data: {"stage": "scrape", "result": {"chars": 3247}}

event: stage_started
data: {"stage": "jd_analyzer"}

event: stage_progress
data: {"stage": "tailor", "message": "Selecting bullets..."}

event: stage_completed
data: {"stage": "critique", "result": {"score": 88, "verdict": "STRONG MATCH", "color": "green"}}

event: pipeline_complete
data: {"job_id": "...", "application_id": "...", "drive_folder_id": "..."}
```

**Stages (in order):**
1. `scrape` (skipped if `job_description` provided)
2. `jd_analyzer`
3. `tailor`
4. `compile`
5. `critique`
6. `outreach` (skipped if disabled)
7. `persist`

**On failure:**
```
event: stage_failed
data: {
  "stage": "tailor",
  "error": {
    "code": "TAILOR_FAILED",
    "user_message": "...",
    "retry_possible": true,
    "trace_id": "..."
  }
}
```

Stream closes after `pipeline_complete` or terminal `stage_failed`.

### `GET /api/pipeline/{job_id}/result`

Fetches final result if SSE was missed.

**Response 200:**
```json
{
  "job_id": "...",
  "status": "completed",
  "application_id": "app_uuid",
  "drive_folder_id": "1AbCdEf...",
  "current_version": 1,
  "tailored_latex": "\\documentclass...",
  "pdf_url": "/api/files/{pdf_id}",
  "critique": { /* full critique */ },
  "outreach": { /* full outreach or null */ }
}
```

**Response 404:** `PIPELINE_NOT_FOUND` (expired or never existed)

### `POST /api/pipeline/{job_id}/retry`

Retries from a specific failed stage. Earlier results reused.

**Request:** `{ "from_stage": "tailor" }`  
**Response:** Same as `/pipeline/run`

### `POST /api/pipeline/retailor`

The "Re-tailor with critique feedback" button.

**Headers:** `Authorization: Bearer ...`, `X-NIM-Key: nvapi-...`  
**Request:**
```json
{
  "application_id": "app_uuid",
  "incorporate_feedback": true
}
```

**Response 202:** Same shape as `/pipeline/run` + `retailor_attempt: N` field  
**Response 409:** `TOO_MANY_RETAILORS` (cap is 3)

**Behavior:**
- Loads existing application
- Passes previous critique to tailor as additional context
- Generates new version (v2, v3, etc.)
- If new score >= current score: new version becomes `current_version`
- If new score < current score: new version saved as history, `current_version` unchanged

---

## Group 6: LaTeX Editor & Compilation

### `POST /api/latex/compile`

Standalone compile — not tied to a pipeline.

**Request:**
```json
{
  "tex_source": "\\documentclass...",
  "filename_hint": "Resume_Stripe_SWE"
}
```

**Response 200 (success):**
```json
{
  "success": true,
  "pdf_id": "tmp_a8f7c2",
  "pdf_url": "/api/files/tmp/tmp_a8f7c2",
  "pages": 1,
  "warnings": [],
  "expires_at": "2026-05-30T16:00:00Z"
}
```

**Response 200 (compile failure — note status is still 200, not 500):**
```json
{
  "success": false,
  "pdf_id": null,
  "errors": [
    {"line": 47, "type": "undefined_control_sequence", "message": "..."}
  ],
  "compile_log": "... last 50 lines of pdflatex output ..."
}
```

### `POST /api/latex/save-to-application`

Saves edited LaTeX (and re-compiled PDF) as a new version.

**Headers:** `Authorization: Bearer ...`  
**Request:**
```json
{
  "application_id": "app_uuid",
  "tex_source": "...",
  "pdf_id": "tmp_a8f7c2",
  "set_as_current": true
}
```

**Response 200:**
```json
{
  "version": 3,
  "drive_paths": {
    "tex": "resume_v3.tex",
    "pdf": "resume_v3.pdf"
  },
  "is_current": true
}
```

---

## Group 7: Dashboard & Applications

### `GET /api/applications`

Lists all applications. Reads only manifest.json from each folder.

**Headers:** `Authorization: Bearer ...`  
**Query params:** `?limit=50&offset=0&sort=created_at_desc`

**Response 200:**
```json
{
  "applications": [
    {
      "application_id": "app_uuid",
      "folder_name": "2026-05-30_Stripe_SWE_a4f2",
      "company": "Stripe",
      "role_title": "Software Engineer",
      "created_at": "2026-05-30T15:30:00Z",
      "current_version": 2,
      "score": 87,
      "verdict": "STRONG MATCH",
      "color": "green",
      "status": "tailored"
    }
  ],
  "total": 12,
  "offset": 0,
  "limit": 50
}
```

### `GET /api/applications/{application_id}`

Full details — loads all files from folder.

**Response 200:**
```json
{
  "manifest": { /* full manifest.json */ },
  "current_version_data": {
    "tex_source": "\\documentclass...",
    "pdf_url": "/api/files/{drive_file_id}",
    "critique": { /* full critique */ }
  },
  "outreach": { /* full outreach or null */ }
}
```

### `GET /api/applications/{application_id}/version/{N}`

Loads a specific version (for comparison/revert UI).

**Response 200:** Same shape as `current_version_data` above.

### `POST /api/applications/{application_id}/set-current`

Manually change `current_version` (e.g., user prefers older version).

**Request:** `{ "version": 1 }`  
**Response 200:** `{ "current_version": 1 }`

### `DELETE /api/applications/{application_id}`

Removes the folder from Drive.

**Response 200:** `{ "deleted": true }`

---

## Group 8: File Streaming

### `GET /api/files/{file_id}`

Streams a file. Used for PDF previews via pdf.js or `<iframe>`.

**Headers:** `Authorization: Bearer ...`  
**Two cases:**
- `file_id` starts with `tmp_` → reads from temp storage
- `file_id` is a Drive file ID → backend proxies from Drive using user's token

Returns binary with `Content-Type: application/pdf`, `Cache-Control: private, max-age=600`.

---

## Notes on SSE

- Always set `Content-Type: text/event-stream`
- Always set `Cache-Control: no-cache`
- Always set `Connection: keep-alive`
- Events use `event:` (event name) and `data:` (JSON payload) format
- Two newlines (`\n\n`) terminate each event
- Use `id:` field for `Last-Event-ID` resume support (optional)
- Send `:keepalive\n\n` every 15 seconds to prevent proxy timeouts

```python
# Example SSE response in FastAPI
async def event_stream():
    async for event in pipeline_events(job_id):
        yield f"event: {event.type}\ndata: {json.dumps(event.data)}\n\n"

return StreamingResponse(event_stream(), media_type="text/event-stream")
```
