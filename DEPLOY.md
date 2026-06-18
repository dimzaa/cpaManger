# Deploy to Render + Neon + Vercel — Free Tier

Total cost: ₪0. Time required: ~45 min if it's your first time, ~15 min after.

> **Reality check.** Render's free web service spins down after 15 min of
> inactivity. The first request after a sleep takes ~30 sec to wake.
> This is fine for showing the tool to one CPA friend, putting it on
> your portfolio, or testing — it is **not** fine for a paying client
> who expects snappy uploads. For real production, you'll need to
> upgrade to Render's $7/month plan (no spin-down) or move to Fly.io.

---

## Step 0 — Prerequisites

1. A GitHub account
2. Your repo pushed to GitHub (private repo is fine)
3. About 45 minutes

If your repo isn't on GitHub yet:
```bash
cd C:\Users\zahal\OneDrive\מסמכים\שולחן העבודה\uncatagorized\github\cpa
git init   # if not already a repo
git add .
git commit -m "Pre-deploy snapshot"
gh repo create cpa --private --source=. --remote=origin --push
# Or do it via github.com manually if you don't have gh CLI
```

---

## Step 1 — Database on Neon (10 min)

Why Neon, not Render's Postgres: Render's free Postgres **expires after
90 days** and gets deleted. Neon's free tier is permanent.

1. Go to https://neon.tech → Sign up with GitHub
2. Create a new project, region: **Frankfurt (eu-central-1)** for lowest
   latency to Israel
3. Pick database name `cpa` (or whatever)
4. Once created, copy the connection string. It looks like:
   ```
   postgresql://user:password@ep-xxx-xxx.eu-central-1.aws.neon.tech/cpa?sslmode=require
   ```
5. **Save that string somewhere safe** — you'll paste it into Render in
   Step 2.

---

## Step 2 — Backend on Render (15 min)

1. Go to https://render.com → Sign up with GitHub → grant repo access
2. Click **New +** → **Web Service** → pick your `cpa` repo
3. Fill in:
   - **Name:** `cpa-backend` (becomes `cpa-backend.onrender.com`)
   - **Region:** Frankfurt
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build command:**
     ```
     pip install -r requirements.txt
     ```
   - **Start command:**
     ```
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan:** Free
4. Click **Advanced** → **Environment Variables** → add these:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Neon string from Step 1 |
   | `SECRET_KEY` | generate one with `python -c "import secrets;print(secrets.token_urlsafe(64))"` |
   | `DEBUG` | `False` |
   | `CORS_ORIGINS` | leave blank for now — you'll fill it in Step 3 |
   | `PYTHON_VERSION` | `3.11.9` |
5. Click **Create Web Service**. Render starts building. First build
   takes 5–10 minutes (installing pandas + sqlalchemy is slow).
6. When it says **Live**, hit `https://cpa-backend.onrender.com/health`
   in your browser. Should return `{"status":"ok"}` or similar. If it
   does, the API is up. Database tables get auto-created on first boot
   via the `lifespan` in `backend/main.py`.

If you see errors in the Render log, the most common ones are:
- **`ModuleNotFoundError`** → a dependency is missing from
  `requirements.txt`. Add it, push to GitHub, Render auto-redeploys.
- **`sqlalchemy.exc.OperationalError: could not connect`** → your
  Neon connection string is wrong or has typos. Re-copy from Neon.
- **`psycopg2.OperationalError: SSL connection required`** → ensure
  the Neon URL ends in `?sslmode=require`.

---

## Step 3 — Frontend on Vercel (10 min)

1. Go to https://vercel.com → Sign up with GitHub
2. Click **Add New** → **Project** → pick your `cpa` repo
3. Fill in:
   - **Framework Preset:** Vite (should auto-detect)
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build` (auto-detected)
   - **Output Directory:** `dist` (auto-detected)
4. **Environment Variables** → add:
   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://cpa-backend.onrender.com` (from Step 2) |
5. Click **Deploy**. ~2 minutes for first build.
6. When done, Vercel gives you a URL like `https://cpa-xyz.vercel.app`.
   Open it — you should see your React app.

---

## Step 4 — Wire CORS so frontend can talk to backend (5 min)

The backend currently allows requests from any origin (`allow_origins=["*"]`)
which is fine for testing. For production, lock it down:

1. Open `backend/main.py`. Find this block (around line 115):
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       ...
   )
   ```
2. Replace with the version below (already in this commit if you applied
   the deployment patch):
   ```python
   import os
   _cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
   app.add_middleware(
       CORSMiddleware,
       allow_origins=_cors_origins,
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
3. Push to GitHub. Render auto-redeploys.
4. Back in Render → your service → Environment → set
   `CORS_ORIGINS` = `https://cpa-xyz.vercel.app` (your real Vercel URL).
   Save — Render restarts automatically.

---

## Step 5 — Seed an admin user (5 min)

Render free plan has no shell, so seed via a one-shot API call. Or
easier: temporarily add a `/api/bootstrap-admin` endpoint, hit it once,
remove it. Quickest path:

1. From your local machine (with `DATABASE_URL` pointing at Neon):
   ```bash
   set DATABASE_URL=postgresql://... (the Neon string)
   cd C:\Users\zahal\OneDrive\מסמכים\שולחן העבודה\uncatagorized\github\cpa
   python -c "
   import sys; sys.path.insert(0, '.')
   from backend.database import SessionLocal
   from backend.models.user import User
   import bcrypt
   db = SessionLocal()
   admin = User(email='you@example.com',
                hashed_password=bcrypt.hashpw(b'CHANGE_ME', bcrypt.gensalt()).decode(),
                role='admin')
   db.add(admin); db.commit()
   print(f'Admin created: id={admin.id}')
   "
   ```
2. Log in via the Vercel URL with `you@example.com` / `CHANGE_ME`.
3. Change the password immediately.

---

## Step 6 — Upload a HORADA and verify

1. Open the Vercel frontend
2. Log in as admin
3. Create a municipality (UI or via API)
4. Upload one of the ZIPs from `uploads/` in your repo (e.g.
   `20260402_162642_Horada.zip`)
5. Should land successfully. Check the budget view — should show
   ~4,951 lines, ₪4,702,530.10 total, **balanced ✅**

If it does → you're deployed. Congrats.

---

## Common gotchas

| Problem | Fix |
|---|---|
| First request takes 30 sec | Render free spin-down. Wait or upgrade to $7/mo. |
| Vercel build fails on `frontend/` | Make sure `package-lock.json` is committed. |
| CORS error in browser console | `CORS_ORIGINS` on Render doesn't include your exact Vercel URL (https, no trailing slash). |
| Upload returns 413 | Render free has a 100MB body limit. HORADA ZIPs are <1MB so this only bites you on weird files. |
| Database fills up | Neon free tier = 0.5 GB. Each HORADA is <1 MB, so you get ~500 uploads before hitting the limit. Upgrade to Neon Launch ($19/mo) for 10 GB if you scale. |
| `bidi` / `arabic-reshaper` missing on Render | Already in requirements.txt after the audit. If not, add them. |

---

## What you still don't have on the free tier

- **No always-on backend.** First request after 15 min idle is slow.
- **No automatic backups.** Neon free has 7-day point-in-time recovery,
  but no scheduled exports. Run a weekly `pg_dump` manually if the data
  matters.
- **No custom domain on Render free.** You're stuck with
  `*.onrender.com` until you upgrade.
- **No staging environment.** Push-to-deploy means every commit hits
  production. Use a `staging` branch + a second Render service for safety
  (still free, just doubles your free hours usage).
- **Real client data → real legal risk.** Free hosting is fine for
  learning and demos. The moment you put real CPA-firm data on it, you
  inherit data-protection obligations the free tier isn't built for.
