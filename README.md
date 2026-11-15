# SAMAY foundation

Repository: https://github.com/suhandk/samay_colossus

Installable app: https://samay-colossus-app.vercel.app/

The `main` and `sub1` branches contain this project. Local databases, credentials and installed dependencies are excluded; use the documented setup and source-data import procedures.

Cash requirement first. Financial feasibility second. Future selling opportunity third.
SAMAY recommends; the farmer decides.

## Local development (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to port 8000. API documentation: http://localhost:8000/docs.

## Verification

```powershell
.\.venv\Scripts\python -m pytest backend/tests
cd frontend
npm run build
npx playwright install chromium
npm run test:e2e
```

The browser test requires the backend running with an empty migrated development database. Test fixtures use an isolated in-memory database. No agricultural records ship with this repository.

## Catalog configuration

Obtain four verified crop records and six verified mandi records. Create a JSON object with `crops` and `markets` arrays. Every record requires a stable `id`, `names` object containing `en` and `kn`, and `source_reference`. Run `python -m backend.configure_catalog path/to/catalog.json` using the virtual environment. Names are never interpreted by application logic. Operator verification is required: a source-reference string alone does not prove authenticity. This stage has no observation importer; crop-market choices require actual observation rows, and historical presence does not prove current price availability.

## PostgreSQL and Docker

Set `POSTGRES_PASSWORD`, run `docker compose up -d db`, then `docker compose run --rm api python -m alembic upgrade head`, then `docker compose up -d api`. Use a URL-safe password or URL-encode it in the connection URL. Frontend production hosting must serve `frontend/dist`, support SPA fallback, and proxy `/api` to the API. Restrict CORS to the real frontend origin and terminate TLS at the deployment gateway. Docker/PostgreSQL deployment requires separate verification.

See docs/ARCHITECTURE.md and docs/ENGINEERING_CONTRACT.md. This release is the foundation, not an operational recommendation service.

## Data pipeline

See [CSV ingestion and source verification](docs/DATA_PIPELINE.md) and [Stage 2 actual results](docs/STAGE_2_REPORT.md). Run Alembic upgrade head before starting the updated API. Live-data acceptance is blocked pending an authentic source export.

## Farmer frontend

See [Stage 3 report](docs/STAGE_3_REPORT.md). Build with npm run build; serve dist with HTTPS and SPA routing. The generated service worker caches only shell assets, never API results. Local drafts are opt-in and are not financial recommendations.

## Forecast training and evaluation

Run `python -m backend.train_forecasts` from the project root using the virtual environment. Read [Stage 4 actual metrics](docs/forecasting/STAGE_4_REPORT.md) before deploying an artifact. Training is always offline and promotion is explicit.

## Cash-first decisions

See [Stage 5 equations, APIs and actual backtest](docs/STAGE_5_REPORT.md). Rich calculations use POST /api/v1/recommend. Retain the returned access token securely for retrieval/recalculation. The mobile adapter remains POST /api/v1/recommendations.

## Integrated browser tests

From frontend run `npm run test:integration`. This starts isolated test servers on ports 8005 and 5179, with a disposable test database; no existing farmer database is used. See [Stage 6 verification](docs/STAGE_6_REPORT.md). Update generated contracts with `python -m scripts.export_openapi` from the repository root followed by `npm run contracts` from frontend.
