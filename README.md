# Resume Tailor — Handoff Package

This bundle contains everything Claude Code needs to build the project.

## What's Inside

```
.
├── README.md                      ← You are here
├── CLAUDE.md                      ← Master rules for Claude Code (goes in repo root)
└── docs/
    ├── 01-data-schemas.md         ← Drive file structure
    ├── 02-api-contract.md         ← Every endpoint
    ├── 03-sequence-diagrams.md    ← How flows actually run
    ├── 04-components.md           ← File-by-file breakdown + build order
    └── IMPLEMENTATION_PLAN.md     ← Phase-by-phase build order
```

## How to Use This

### Step 1: Set up your repo

```bash
mkdir resume-tailor && cd resume-tailor
git init

# Copy this entire handoff bundle into your repo
cp /path/to/handoff/CLAUDE.md ./CLAUDE.md
mkdir docs && cp /path/to/handoff/docs/*.md ./docs/

# Commit
git add .
git commit -m "Add design docs and project rules"
```

### Step 2: Follow Phase 0 of the Implementation Plan

Open `docs/IMPLEMENTATION_PLAN.md` and do Phase 0 manually (creating backend/frontend skeletons). **Don't use Claude Code yet** — you want to know the structure yourself.

### Step 3: Install Claude Code

```bash
npm install -g @anthropic-ai/claude-code
cd resume-tailor
claude
```

### Step 4: Start Phase 1

In Claude Code, type:

> Read `CLAUDE.md` and `docs/IMPLEMENTATION_PLAN.md`. I'm starting Phase 1. Show me your plan for task 1.1.

Claude Code will read the files, understand the architecture, and propose a plan before writing code. You approve, it builds, you verify, you move to task 1.2.

### Step 5: Repeat for each phase

Each phase has clear tasks, clear verification steps, and a clear "done when" checklist.

---

## The Most Important Rules (Repeated for Emphasis)

1. **Read the docs before building.** Every Claude Code session should start with the docs.

2. **Build one thing at a time.** Resist the urge to ask Claude Code to "build the whole thing."

3. **Verify after every task.** Run the code. Read what it wrote. Don't just accept.

4. **Push back when Claude Code suggests architecture changes.** The docs are the contract. Deviations need your explicit approval.

5. **You write the LLM prompts.** Claude Code can plumb them into code, but the prompts themselves are your work.

---

## When You Hit Trouble

- **Build error in Phase N?** Re-read the task's spec in `04-components.md`. Often the issue is a missing Level N-1 dependency.

- **Claude Code suggests adding Redis/Postgres/etc?** Refer to Rule 1 in `CLAUDE.md`. Don't do it.

- **Architecture question that isn't in the docs?** Come back, we'll work through it.

- **Phase taking 2x longer than estimated?** That's normal for first-timers. Don't skip phases to catch up.

---

## Final Note

You spent ~5 hours designing this with me across multiple sessions. Most projects skip this step and pay for it during build. You won't.

Go ship it.
