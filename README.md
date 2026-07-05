# Stock Volatility Platform

A real-time stock volatility prediction platform: ingests OHLCV market data,
engineers volatility features, trains ML models, and serves predictions via
a FastAPI REST API with a Next.js dashboard.

> Status: under active development. This README is updated as each layer is built.

## Architecture

Layered / hexagonal architecture — dependencies point inward, toward the domain:

```
src/volatility_platform/
├── domain/           # Pure data models, no I/O
├── features/         # Feature engineering (shared by training & inference)
├── ml/                # Training, inference, model registry
├── data_providers/   # Adapters for external market data (yfinance, ...)
├── repositories/      # MongoDB adapters, one per collection
├── services/          # Orchestration / use cases (the DI seam)
├── api/               # FastAPI delivery layer
└── config/            # Typed settings (pydantic-settings)
```

See commit history / project notes for the reasoning behind this structure.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env              # then fill in real values
```

## Populating data

There's no HTTP endpoint for ingestion by design (see `services/ingestion_service.py`
— ingestion runs on its own schedule, separate from the request/response API).
Run it manually or as a scheduled job:

```bash
python pipelines/ingest_daily.py
```

Then train the shared pooled model. `POST /train` works for local dev, but
training cross-validates four deliberately different candidate models
(HAR-RV, ridge, random forest, XGBoost — see `ml/train.py` for why each one
is in the set rather than a longer list of near-duplicates) and can be too
slow/memory-heavy for a free-tier hosting instance (it hit Render's proxy
timeout in practice). The more reliable path — and the better MLOps pattern
generally, since training shouldn't run inside a resource-constrained API
request — is training locally (or in CI) against the same production
database:

```bash
MODEL_REGISTRY_BACKEND=mongodb python pipelines/train_model.py
```

This writes the trained model straight to MongoDB, where the deployed API
(which also uses the `mongodb` backend in production) picks it up immediately
via `GET /model-info` / `POST /predict` — no redeploy needed.

## Running tests

```bash
pytest
```

## Frontend (Next.js dashboard)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at the local API by default
npm run dev
```

Runs at `http://localhost:3000`. The backend needs `CORS_ORIGINS` (in `.env`)
to include the frontend's origin — `http://localhost:3000` is the default.

## Running with Docker

Requires `.env` to exist (`cp .env.example .env`) before building, since
`docker-compose.yml` loads it via `env_file`.

```bash
docker compose up --build
```

This starts MongoDB and the API together. The API container overrides
`MONGODB_URI` to reach MongoDB via the Compose network, and sets
`MODEL_REGISTRY_BACKEND=mongodb` — the production backend, since trained
models stored on a container's local disk don't survive a restart/redeploy.
The API is available at `http://localhost:8000` (`/docs` for the OpenAPI UI).

The API image is a multi-stage build (`docker/Dockerfile.api`): a `builder`
stage installs the package into a venv, and the `runtime` stage copies just
that venv into a slim, non-root final image with a Python-based `HEALTHCHECK`
(`docker/healthcheck.py`) — no `curl` needed in the image.

## Deployment

Three pieces, each on the free/hobby tier of its platform: **MongoDB Atlas**
(database), **Render** (API), **Vercel** (frontend).

### 1. MongoDB Atlas

1. Create a free account at mongodb.com/cloud/atlas, create a free (M0) cluster.
2. Database Access → add a database user (username/password).
3. Network Access → add `0.0.0.0/0` (allow from anywhere) — Render's outbound
   IPs aren't static on the free plan, so IP allowlisting isn't practical here;
   the database user's password is what actually gates access. This is a real
   tradeoff (any IP can *attempt* a connection) but the standard one for this
   setup: authentication still applies, and a strong random password mitigates
   most of the exposure. Atlas VPC Peering / Private Endpoints avoid this
   entirely but require a paid (M10+) tier.
4. Get the connection string (Connect → Drivers → Python), it looks like
   `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/`. This becomes
   `MONGODB_URI` in Render.

### 2. Push this repo to GitHub

Nothing has been pushed yet — this repo currently only exists locally. Create
the GitHub repo (via github.com's "New repository" button, or `gh repo create`
if you have the GitHub CLI installed), then:

```bash
git remote add origin <your-repo-url>
git add .
git commit -m "Initial commit"
git push -u origin master
```

### 3. Render (API)

1. New → Blueprint, connect the GitHub repo. Render reads `render.yaml` at
   the repo root and creates the `volatility-platform-api` web service.
2. Set the two secrets `render.yaml` marks `sync: false`:
   - `MONGODB_URI` — from Atlas, step 1.
   - `CORS_ORIGINS` — leave as `http://localhost:3000` for now; update once
     step 4 gives you the Vercel URL.
3. In the service's Settings, turn off "Auto-Deploy" if it's on — deploys are
   meant to happen via the CI-gated hook (step 5), not on every push.
4. After the first manual deploy succeeds, copy Settings → Deploy Hook URL —
   you'll need it in step 5.
5. Once live: run `python pipelines/ingest_daily.py` (pointed at the Atlas
   `MONGODB_URI` via a local `.env`) to populate data, then call `POST /train`
   against the deployed API to train the first model.

### 4. Vercel (frontend)

1. Import the GitHub repo as a new Vercel project; set **Root Directory** to
   `frontend`.
2. Add environment variable `NEXT_PUBLIC_API_URL` = the Render service's URL
   (e.g. `https://volatility-platform-api.onrender.com`).
3. Deploy. Then go back to Render and update `CORS_ORIGINS` to this Vercel
   URL (comma-separate if you need both prod and preview URLs), so the
   browser-side fetches from the dashboard aren't blocked by CORS.

### 5. Wire up CI-gated deploys

`.github/workflows/deploy.yml` only deploys after `ci.yml` passes on `main`.
Add the Render deploy hook URL (from step 3.4) as a GitHub Actions secret:

```bash
gh secret set RENDER_DEPLOY_HOOK_URL --body "<the deploy hook URL>"
```

(Or: repo Settings → Secrets and variables → Actions → New repository secret,
via the GitHub web UI.)

## Project layout rationale

- **`src/` layout**: keeps the package installable and prevents accidental
  imports of code that isn't actually packaged.
- **`domain/` vs `ml/` vs `models_store/`**: separates "what is a prediction"
  (data shape) from "how we train/predict" (code) from "the trained artifact
  file" (binary) — three different things that are easy to conflate under a
  single `models/` folder.
- **`services/` as the DI seam**: services depend on repository *interfaces*,
  not concrete MongoDB classes, so business logic can be unit-tested without
  a database and swapped to a different backing store later.
