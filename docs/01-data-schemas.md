# 01 — Data Schemas (Drive File Structure)

The user's Google Drive is the system's database. Every persistent piece of state lives here. The backend reads/writes these files but doesn't own them — the user does.

## Folder Layout

```
Google Drive/
└── Resume_Tailor/
    ├── _config/
    │   ├── api_keys.enc.json        encrypted NIM key + trusted devices
    │   └── settings.json            user preferences
    │
    ├── profile.json                 achievement library (heart of the system)
    │
    ├── role_configs/
    │   ├── ai_engineer.json         (built-in roles never live here — those
    │   ├── software_engineer.json    live in codebase. Only auto-generated
    │   ├── data_analyst.json         configs are stored in Drive.)
    │   └── product_manager.json
    │
    └── applications/
        └── 2026-05-30_Stripe_SWE_a4f2/
            ├── manifest.json        dashboard reads this (small, fast)
            ├── resume_v1.tex        original tailored
            ├── resume_v1.pdf
            ├── critique_v1.json
            ├── resume_v2.tex        re-tailor attempt
            ├── resume_v2.pdf
            ├── critique_v2.json
            └── outreach.json        outreach generated once, reused
```

---

## File: `_config/api_keys.enc.json`

```json
{
  "version": 1,
  "encryption": {
    "algorithm": "AES-GCM",
    "key_derivation": "PBKDF2-SHA256",
    "iterations": 100000,
    "salt": "base64-encoded-random-salt"
  },
  "encrypted_payload": "base64-ciphertext",
  "trusted_devices": [
    {
      "device_id": "uuid-v4",
      "device_label": "MacBook Pro",
      "added_at": "2026-05-30T10:00:00Z",
      "wrapped_device_key": "device-key-encrypted-by-passphrase-key"
    }
  ]
}
```

The decrypted `encrypted_payload` is:

```json
{
  "nvidia_nim_api_key": "nvapi-...",
  "additional_keys": {}
}
```

---

## File: `_config/settings.json`

```json
{
  "version": 1,
  "default_role": "ai_engineer",
  "preferences": {
    "auto_compile_on_edit": false,
    "show_critique_details_by_default": false,
    "color_theme": "system"
  }
}
```

---

## File: `profile.json`

The user's achievement library. The tailor agent selects from this — never invents new bullets.

```json
{
  "version": 1,
  "personal": {
    "name": "Sai Sumanth Reddy Kachi",
    "email": "saisumanthreddy216@gmail.com",
    "phone": "(667) 445-9499",
    "location": "Baltimore, MD",
    "linkedin": "linkedin.com/in/sumanth14",
    "github": "https://github.com/sumanth-14",
    "github_display": "github.com/sumanth-14",
    "portfolio": "https://sumanth.dev"
  },
  "visa_status": {
    "type": "F-1 OPT",
    "needs_sponsorship": true,
    "stem_extension_eligible": true
  },
  "summary": "AI Engineer with 3+ years of experience building production LLM systems. Skilled in RAG pipelines, multi-agent orchestration, and AI integration across healthcare and enterprise platforms.",
  "education": [
    {
      "id": "EDU_1",
      "degree": "Master of Science, Information Systems",
      "school": "University of Maryland Baltimore County",
      "location": "Baltimore, MD",
      "dates": "Aug 2024 - May 2026",
      "gpa": 3.85,
      "coursework": ["Artificial Intelligence", "Natural Language Processing", "Data Structures & Algorithms", "Cloud Computing", "System Design"]
    }
  ],
  "experience": [
    {
      "id": "R4",
      "title": "Software Engineer Intern",
      "company": "Minnodi LLC",
      "location": "Baltimore, MD",
      "dates": "Nov 2025 - Present",
      "level": "L2",
      "bullets": [
        {
          "id": "R4_AI_01",
          "themes": ["AI", "Healthcare"],
          "text": "Integrated Azure OpenAI service into a healthcare portal...",
          "metrics": ["multiple deployed clinics"],
          "tech_stack": ["Azure OpenAI", "Healthcare APIs"]
        }
      ]
    }
  ],
  "projects": [
    {
      "id": "P_01",
      "name": "Invenio",
      "subtitle": "AI-Powered Job Discovery Platform",
      "stack": ["React.js", "Node.js", "Express.js", "Gemini 3 Flash", "Supabase"],
      "themes": ["FS", "AI"],
      "text": "Architected an end-to-end job discovery pipeline...",
      "metrics": ["15 users", "20 organizations"],
      "url": null
    }
  ],
  "skills": {
    "Programming Languages": ["JavaScript", "TypeScript", "Python", "Java", "SQL"],
    "Frameworks & Libraries": ["React.js", "Node.js", "Express.js", "FastAPI"],
    "Databases & Storage": ["PostgreSQL", "MongoDB", "Supabase", "Azure SQL", "Redis"],
    "Cloud & DevOps": ["Microsoft Azure", "AWS", "Docker", "Git", "CI/CD"],
    "AI & ML": ["Azure OpenAI", "LLMs", "RAG", "Prompt Engineering"],
    "Core Competencies": ["Full-Stack Development", "Microservices", "System Design"]
  }
}
```

**Why the rich structure (themes, metrics, tech_stack on bullets):** Tailor agent reasons about bullets without re-parsing free text. When JD mentions "Kubernetes", agent searches `tech_stack` arrays. When it wants "AI bullets", it filters by `themes`. More reliable than string matching in prompts.

---

## File: `role_configs/{role_id}.json`

```json
{
  "version": 1,
  "role_id": "data_analyst",
  "role_display_name": "Data Analyst",
  "source": "auto_generated",
  "generated_at": "2026-05-30T14:22:00Z",
  "skills_order": [
    "Programming Languages",
    "Databases & Storage",
    "Core Competencies",
    "Frameworks & Libraries",
    "Cloud & DevOps",
    "AI & ML"
  ],
  "bullet_priority_strategy": "Lead with SQL, data analysis, and reporting bullets. Filter `themes` for DB, ANL, REPORT. Quantify with data volume, query performance, dashboard usage.",
  "project_priority_strategy": "Lead with projects involving dashboards, BI tools, or data pipelines.",
  "summary_focus": "Data analyst experience with SQL, BI tools, and statistical analysis.",
  "keywords_emphasis": ["SQL", "Tableau", "Power BI", "A/B testing", "data modeling", "ETL", "dashboards"],
  "preferred_action_verbs": ["Analyzed", "Visualized", "Modeled", "Reported", "Identified", "Quantified"],
  "bullets_per_role_max": {"R4": 3, "R3": 3, "R2": 2, "R1": 1}
}
```

**`source` field values:**
- `"built_in"` — from codebase `app/builtin_agents/`
- `"auto_generated"` — LLM-generated, never edited
- `"user_edited"` — user modified via UI, do not overwrite

---

## File: `applications/{folder}/manifest.json`

Dashboard reads only this — keep it small and fast.

```json
{
  "version": 1,
  "application_id": "app_uuid",
  "created_at": "2026-05-30T15:30:00Z",
  "last_modified": "2026-05-30T16:45:00Z",
  "company": "Stripe",
  "role_title": "Software Engineer",
  "role_config_used": "ai_engineer",
  "job_url": "https://stripe.com/jobs/...",
  "current_version": 2,
  "versions": [
    {
      "version": 1,
      "score": 72,
      "verdict": "NEEDS WORK",
      "color": "yellow",
      "files": {
        "tex": "resume_v1.tex",
        "pdf": "resume_v1.pdf",
        "critique": "critique_v1.json"
      }
    },
    {
      "version": 2,
      "score": 87,
      "verdict": "STRONG MATCH",
      "color": "green",
      "files": {
        "tex": "resume_v2.tex",
        "pdf": "resume_v2.pdf",
        "critique": "critique_v2.json"
      }
    }
  ],
  "outreach_file": "outreach.json",
  "status": "tailored",
  "pipeline_metadata": {
    "model_used": "minimax-m2.7",
    "total_duration_seconds": 92
  }
}
```

**Version handling:**
- Each tailor or re-tailor creates a new version (`v1`, `v2`, `v3`, ...)
- `current_version` points to the version shown by default
- Auto-revert: if new version scores lower than current, `current_version` stays unchanged but new version is still saved as history

---

## File: `applications/{folder}/critique_v{N}.json`

```json
{
  "version": 1,
  "scores": {
    "ats_keyword_match": {"score": 22, "max": 25},
    "impact_metrics": {"score": 23, "max": 25},
    "bullet_quality": {"score": 17, "max": 20},
    "role_alignment": {"score": 14, "max": 15},
    "clarity": {"score": 12, "max": 15}
  },
  "total": 88,
  "verdict": "STRONG MATCH",
  "keywords_found": ["React", "Node.js", "REST", "microservices", "Azure"],
  "keywords_missing": ["Kubernetes", "Kafka"],
  "top_fixes": [
    {"priority": "HIGH", "fix": "Add Kubernetes to skills if you've used it"},
    {"priority": "MEDIUM", "fix": "Mention Kafka in R3 API bullet"}
  ]
}
```

---

## File: `applications/{folder}/outreach.json`

```json
{
  "version": 1,
  "company": "Stripe",
  "role_title": "Software Engineer",
  "generated_at": "2026-05-30T15:31:00Z",
  "messages": {
    "cold_email": {
      "subjects": [
        "SWE | 95% Automation | React/Node",
        "Quick question about the SWE role",
        "3+ yrs full-stack — Stripe SWE intro"
      ],
      "body": "Hi Sarah,\n\nI saw the Software Engineer opening..."
    },
    "linkedin_connection": {
      "text": "Hi Sarah, Full Stack Engineer with 3+ yrs...",
      "char_count": 198
    },
    "linkedin_message": {
      "text": "Thanks for connecting! I wanted to follow up..."
    },
    "followup_email": {
      "subject": "Re: SWE | 95% Automation",
      "body": "Hi Sarah, following up on..."
    }
  },
  "personalization_used": [
    "Referenced Stripe's developer-facing API design philosophy"
  ]
}
```

Outreach is generated once per application and reused across re-tailor attempts. Not regenerated unless user explicitly requests it.

---

## Verdict Tiers (Critique Color Grading)

| Score | Verdict | Color |
|-------|---------|-------|
| 80–100 | STRONG MATCH | green |
| 60–79 | NEEDS WORK | yellow |
| 0–59 | WEAK MATCH | red |

---

## Application Folder Naming

Format: `{YYYY-MM-DD}_{Company}_{Role}_{shortUUID4}`

Examples:
- `2026-05-30_Stripe_SWE_a4f2`
- `2026-06-02_Datadog_SRE_b7c1`

Short UUID4 suffix (4 chars) ensures uniqueness for duplicate (company, role) pairs. Users can rename folders in Drive — the app reads `manifest.json` for display, not folder name.

---

## Versioning

All schemas include `"version": 1`. Future schema changes require bumping the version and writing a migration. Don't write code that breaks on `version > 1` — log a warning and proceed with best effort.
