# Deployment Guide

> **Read this before deploying.** Complete local testing first — run both backend and frontend
> locally with a real NIM key and Google OAuth credentials before touching Railway or Vercel.

---

## Prerequisites

- [Railway](https://railway.app) account (backend)
- [Vercel](https://vercel.com) account (frontend)
- [Google Cloud Console](https://console.cloud.google.com) project with OAuth 2.0 credentials
- NVIDIA NIM API key from [build.nvidia.com](https://build.nvidia.com)
- Docker installed locally (to build and test the backend image)

---

## Step 1 — Test locally before deploying

### Backend (Docker)

```bash
cd backend

# Build the image
docker build -t resume-tailor-backend .

# Create a .env file for the container (copy from .env.example)
cp .env.example .env.docker
# Fill in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI=http://localhost:3000/callback

# Run the container
docker run -p 8000:8000 --env-file .env.docker resume-tailor-backend

# Smoke test
curl http://localhost:8000/health
# → {"status": "ok", "environment": "development"}
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# → http://localhost:3000
```

### Switch from mock NIM to real NIM (local)

In `backend/.env` (or `.env.docker`), set:
```
USE_MOCK_NIM=false
```

The backend will now call NVIDIA NIM using the `X-NIM-Key` header sent from the frontend.
The key is never stored — it lives only in the user's Zustand memory store.

---

## Step 2 — Configure Google OAuth for production

1. Go to [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, add your production frontend URL:
   ```
   https://your-app.vercel.app/callback
   ```
4. Keep `http://localhost:3000/callback` for local development
5. Save. Copy the **Client ID** and **Client Secret** for Railway env vars below.

---

## Step 3 — Deploy Backend (choose Render OR Railway)

> The backend needs a **persistent Docker container** (it runs `pdflatex` + `pdfinfo`),
> so it cannot go on Vercel. Pick one host below. **Render** is the default since it has a
> free tier and runs a single persistent instance — which matters because the compile flow
> writes temp PDFs to local `/tmp` and serves them back by `pdf_id`; a single instance keeps
> that filesystem consistent across requests.

### Option A — Render (recommended, free tier)

A `render.yaml` Blueprint lives at the repo root, so this is mostly one-click.

1. Go to [render.com](https://render.com) → **New → Blueprint** → connect GitHub → pick the `keyfit` repo.
2. Render reads `render.yaml`, creates the `keyfit-backend` web service (Docker, from `backend/Dockerfile`),
   and prompts you for the four `sync: false` secret vars:

   | Variable | Value (placeholder until Step 5) |
   |----------|----------------------------------|
   | `CORS_ORIGINS` | `["https://placeholder.vercel.app"]` |
   | `GOOGLE_CLIENT_ID` | `...apps.googleusercontent.com` |
   | `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` |
   | `GOOGLE_REDIRECT_URI` | `https://placeholder.vercel.app/callback` |

   (The non-secret vars — `ENVIRONMENT=production`, `USE_MOCK_NIM=false`, etc. — are baked into `render.yaml`.)
3. Apply → wait for the first build (LaTeX image is large, the first build takes a few minutes).
4. Copy your service URL, e.g. `https://keyfit-backend.onrender.com`. The health check at `/health` must be green.

> **Free-tier note:** the service sleeps after ~15 min idle; the first request after a nap takes
> ~50s to wake. Fine for a 5–10 friend beta. Upgrade to a paid instance to keep it always-on.

### Option B — Railway

### Create project

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select your repo, choose the `backend/` directory as root (or set build context)
3. Railway will auto-detect the `Dockerfile`

### Set environment variables

In Railway → your service → Variables, set:

| Variable | Value | Notes |
|----------|-------|-------|
| `ENVIRONMENT` | `production` | Disables `OAUTHLIB_INSECURE_TRANSPORT`, hides technical_details in errors |
| `CORS_ORIGINS` | `["https://your-app.vercel.app"]` | Your Vercel URL — update after Step 4 |
| `GOOGLE_CLIENT_ID` | `...apps.googleusercontent.com` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | `https://your-app.vercel.app/callback` | Must match OAuth config exactly |
| `USE_MOCK_NIM` | `false` | Real NIM calls |
| `NIM_BASE_URL` | `https://integrate.api.nvidia.com/v1` | Default — only change if using a different NIM endpoint |
| `TEMP_STORAGE_DIR` | `/tmp/resume_tailor` | Default — Railway's `/tmp` is ephemeral but fine for 10-min temp files |
| `TEMP_STORAGE_TTL_SECONDS` | `600` | 10 minutes |

> **Note:** `NIM_MODEL` is not a config var — the model is hardcoded per agent as
> `meta/llama-3.1-70b-instruct`. Change it in the agent files if you want a different model.

### After deploy

Copy your Railway service URL (e.g. `https://resume-tailor-backend.up.railway.app`).
You'll need this for the frontend env var.

---

## Step 4 — Deploy Frontend to Vercel

### Create project

1. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
2. Select your repo
3. Set **Root Directory** to `frontend`
4. Framework preset: **Next.js** (auto-detected)

### Set environment variables

In Vercel → your project → Settings → Environment Variables:

| Variable | Value | Notes |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | `https://resume-tailor-backend.up.railway.app` | Your Railway URL from Step 3 |

### After deploy

Copy your Vercel URL (e.g. `https://your-app.vercel.app`).

---

## Step 5 — Update CORS and OAuth redirect

Go back to your **backend host** (Render or Railway) and update two env vars with your real Vercel URL:

```
CORS_ORIGINS=["https://your-app.vercel.app"]
GOOGLE_REDIRECT_URI=https://your-app.vercel.app/callback
```

And update **Google Cloud Console** → OAuth 2.0 Client → Authorized redirect URIs to add
`https://your-app.vercel.app/callback`.

Railway will redeploy automatically on env var changes.

---

## Step 6 — Smoke test production

```bash
# Health check
curl https://resume-tailor-backend.up.railway.app/health

# Verify CORS header (replace with your Vercel URL)
curl -H "Origin: https://your-app.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     https://resume-tailor-backend.up.railway.app/api/pipeline/run
# → Should return Access-Control-Allow-Origin header
```

Then open `https://your-app.vercel.app` in a browser:
- [ ] Connect Google Drive button works
- [ ] OAuth completes and lands on dashboard
- [ ] NIM key onboarding saves key (memory only)
- [ ] Full pipeline runs with a real job description

---

## Adding friends (beta users)

Google OAuth apps in "Testing" mode only allow users listed in the consent screen's
**Test users** list. For each friend:

1. Google Cloud Console → OAuth consent screen → Test users → Add users
2. Enter their Gmail address
3. They can now OAuth into the app

To remove the testing restriction and allow any Google account, you need to submit for
**Google verification** (required for apps accessing Drive data from external users).
For 5–10 friends, staying in Testing mode is fine.

---

## Rollback

- **Backend**: Railway → Deployments → click any previous deployment → Redeploy
- **Frontend**: Vercel → Deployments → click any previous deployment → Promote to Production
