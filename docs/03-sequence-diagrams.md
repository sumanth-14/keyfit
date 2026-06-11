# 03 — Sequence Diagrams

The order operations happen across browser, backend, NVIDIA NIM, and Google Drive.

## Diagram 1: First-Time Onboarding

```
Browser → FastAPI → Google OAuth → Google Drive → NVIDIA NIM
─────────────────────────────────────────────────────────────

1. Landing page → "Get Started"
   Browser   →   GET  /api/auth/google/url
            ←   { auth_url, state }

2. Browser redirects to Google OAuth consent
   User authorizes Drive scope

3. OAuth redirects back with code
   Browser   →   POST /api/auth/google/callback { code, state }
   Backend   →   Google: exchange code for tokens
            ←   tokens
   Backend   →   Drive: check Resume_Tailor folder exists
            ←   404 not found
            ←   { access_token, tailor_folder_exists: false }

4. Show "Welcome! Let's set up"
   Browser   →   POST /api/setup/initialize
   Backend   →   Drive: create Resume_Tailor/ + subfolders
            ←   folder_ids
            ←   { ready: true }

5. Show "Step 1: Add NVIDIA NIM key"
   User enters API key + passphrase
   
   Browser   →   POST /api/keys/validate { nim_api_key }
   Backend   →   NIM: test call (list models)
            ←   200 OK
            ←   { valid: true }
   
   Browser: encrypt API key locally
     - PBKDF2(passphrase, salt) → derived_key
     - AES-GCM(derived_key, nim_key) → ciphertext
     - Generate device_id, wrap device_key with derived_key
   
   Browser   →   PUT /api/keys/encrypted-blob { ciphertext, salt, devices }
   Backend   →   Drive: save _config/api_keys.enc.json
            ←   saved
            ←   { saved: true }

6. Show "Step 2: Set up your profile"
   User uploads existing resume (.tex or .pdf)
   
   Browser   →   POST /api/profile/parse-from-resume (multipart)
   Backend   →   Extract text
   Backend   →   NIM: parse with LLM ("extract personal, education, experience...")
            ←   structured JSON
   Backend   →   Compute confidence per field
            ←   { profile, extraction_confidence, flagged_fields }

7. Show review form with extracted data + flagged fields highlighted
   User reviews + fills gaps + clicks "Save"
   
   Browser   →   PUT /api/profile { profile }
   Backend   →   Drive: write profile.json
            ←   { saved: true }

8. Redirect to dashboard. Onboarding complete.
```

**Time:** ~2 minutes on happy path (mostly LLM extraction).

**Error branches:**
- Drive folder creation fails → show error, retry button
- NIM key invalid → red error under input
- Resume parsing fails entirely → fallback to empty manual form
- Drive write fails → reauth flow

---

## Diagram 2: Running a Pipeline (Main Flow)

```
Browser → FastAPI → InflightTracker → NVIDIA NIM → Google Drive
───────────────────────────────────────────────────────────────

1. User fills: URL, Company, Role → clicks "Tailor"
   Browser   →   POST /api/pipeline/run
                 Headers: Authorization, X-NIM-Key
                 Body: { job_url, company, role, role_config_id }

2. Backend: compute job_signature = hash(user + role_config + url_or_jd)
   Backend   →   InflightTracker: check signature
            ←   not running
   Backend   →   InflightTracker: register { user, sig: job_id }
   Backend: generate job_id, launch background task
            ←   202 { job_id, stream_url, new: true }

3. Browser opens EventSource(stream_url) — SSE STREAM OPENS

   ┌─ STAGE 1: SCRAPE ──────────────────────────────────────────
   Backend: fetch JD from URL via BeautifulSoup
        emit stage_started { scrape }
        ...
        emit stage_completed { scrape, chars: 3247 }
   
   ┌─ STAGE 2: JD ANALYZER ─────────────────────────────────────
   Backend: emit stage_started { jd_analyzer }
        →   NIM (analyzer model)
        ←   JSON: level, themes, keywords
        emit stage_completed { jd_analyzer, keywords[8] }
   
   ┌─ STAGE 3: LOAD PROFILE + ROLE CONFIG ──────────────────────
   Backend  →   Drive: read profile.json
           ←   profile
   Backend: resolve role_config:
        1. Check built-in (codebase)
        2. If not, check user's role_configs/
        3. If not, LLM-generate, save to Drive
        →   Drive: read role_configs/{role_id}.json
        ←   config
   
   ┌─ STAGE 4: TAILOR ──────────────────────────────────────────
   Backend: emit stage_started { tailor }
        →   NIM (tailor model)
              Inputs: JD analysis + profile + role config
        ←   JSON: selected_ids, tailored_text
   Backend: validate selected_ids ⊆ profile bullets
   Backend: assemble LaTeX from template + tailored content
        emit stage_completed { tailor, bullets_selected: 7 }
   
   ┌─ STAGE 5: COMPILE + PAGE FIT ──────────────────────────────
   Backend: emit stage_started { compile }
   Backend: pdflatex run, check pages via pdfinfo
   Backend: if pages > 1 → walk trim ladder, retry
   Backend: save PDF to temp file → pdf_id
        emit stage_completed { compile, pages: 1, pdf_id }
   
   ┌─ STAGE 6: CRITIC ──────────────────────────────────────────
   Backend: emit stage_started { critique }
        →   NIM (critic model)
        ←   scores + verdict
   Backend: parse, color-grade
        emit stage_completed { critique, score: 88, verdict, color }
   
   ┌─ STAGE 7: OUTREACH (if enabled) ───────────────────────────
   Backend: emit stage_started { outreach }
        →   NIM (outreach model)
        ←   messages
        emit stage_completed { outreach }
   
   ┌─ STAGE 8: PERSIST TO DRIVE ────────────────────────────────
   Backend  →   Drive: create folder
                applications/2026-05-30_Stripe_SWE_a4f2/
            →   Drive: write manifest.json, resume_v1.tex,
                       resume_v1.pdf, critique_v1.json, outreach.json
           ←   saved
   Backend  →   InflightTracker: release slot
   
        emit pipeline_complete { application_id, drive_folder_id }
   
   SSE STREAM CLOSES

4. Browser shows editor view with PDF preview + score badge + outreach tab
```

**Total time:** ~40–60 seconds depending on NIM model speed.

**Critical error paths:**
- `SCRAPE_FAILED` → pipeline continues if user provided JD text instead
- `JD_ANALYZER_FAILED` → emit stage_failed, retry possible
- `TAILOR_FAILED` → emit stage_failed, retry possible
- `PAGE_FIT_FAILED` → still emit stage_completed with warning, user can edit
- `DRIVE_AUTH_EXPIRED` → emit error, frontend triggers reauth
- `NIM_RATE_LIMITED` → backoff and retry internally up to 3 times

**Idempotency (Option C) in action:**

```
User double-clicks "Tailor"

First click:  POST /pipeline/run → not running → starts → job_X (new: true)
Second click: POST /pipeline/run → already running → returns job_X (new: false)

Both browser tabs subscribe to same SSE stream.
Both receive identical events.
Server only does the work once.
```

---

## Diagram 3: Re-Tailor Loop

User sees 72/100 yellow score, clicks "Re-tailor". Critique feedback gets passed to fresh tailor call.

```
Browser → FastAPI → NVIDIA NIM → Google Drive
──────────────────────────────────────────────

1. User sees critique card:
     Score: 72 (yellow)
     Missing: AWS, Kafka
     [Re-tailor] button

2. User clicks "Re-tailor"
   Browser   →   POST /api/pipeline/retailor
                 { application_id, incorporate_feedback: true }

3. Backend  →   Drive: load existing application
              ←   manifest, current critique, latex, JD
   Backend: check retailor_count (from manifest.versions.length)
        if >= 3 → reject 409 TOO_MANY_RETAILORS
   Backend: generate new job_id, open SSE stream
              ←   202 { job_id, stream_url, retailor_attempt: 2 }

4. Browser subscribes to SSE

   ┌─ STAGE: TAILOR (augmented prompt) ─────────────────────────
   Backend: build augmented prompt:
        - Original profile
        - Original JD analysis  
        - Previous critique (what was missing)
        - Instruction: "Last attempt scored 72/100. These keywords
          were missing: AWS, Kafka. Incorporate them ONLY if user's
          profile genuinely contains relevant experience — never
          fabricate."
   
   emit stage_started { tailor, attempt: 2 }
        →   NIM
        ←   new JSON
   assemble LaTeX
   emit stage_completed { tailor }
   
   ┌─ STAGE: COMPILE ───────────────────────────────────────────
   (same as main pipeline)
   emit stage_completed { compile, pages: 1 }
   
   ┌─ STAGE: CRITIC ────────────────────────────────────────────
        →   NIM
        ←   new scores
   emit stage_completed { critique, score: 87 }
   
   ┌─ STAGE: COMPARE + PERSIST ─────────────────────────────────
   
   Did score improve? (87 > 72)
   
   ╭─ YES: Promote new version to current ─╮
   │ Save as resume_v2.tex, resume_v2.pdf  │
   │ Update manifest:                       │
   │   current_version: 2                   │
   │   versions: [v1{72}, v2{87}]           │
   │ DO NOT touch outreach.json             │
   ╰────────────────────────────────────────╯
   
   ╭─ NO (or equal): Keep old as current ──╮
   │ Save new as resume_v2 but DO NOT     │
   │ change current_version                 │
   │ Update manifest:                       │
   │   current_version: 1 (unchanged)       │
   │   versions: [v1{72}, v2{68}]           │
   ╰────────────────────────────────────────╯
   
        →   Drive: write all files
        ←   saved
   
   emit pipeline_complete {
     application_id,
     new_version: 2,
     promoted_to_current: true|false,
     score_change: +15 | -4
   }

5. Browser shows result card based on outcome:
   
   IF promoted:
     "Score improved 72 → 87 🟢"
     "Now includes: AWS"
     "Still missing: Kafka (not in your profile)"
     [Accept] [Re-tailor again (1 left)] [Edit manually]
   
   IF auto-reverted:
     "Re-tailor didn't improve the score — kept your previous version."
     "View attempt 2 →" (link to see what changed)
     [Re-tailor again (1 left)] [Edit manually]
```

**Key design decisions:**

1. **Outreach is not regenerated on re-tailor.** Outreach is based on JD, not resume — still valid. Saves an NIM call.

2. **Hard cap at 3 attempts** (v1 + v2 + v3 = 3 versions total). After v3, button disabled.

3. **All versions kept.** No deletion. User can switch between versions in the editor.

4. **Auto-revert is silent.** Current version doesn't change if new score is worse. New version is still saved as history for transparency.
