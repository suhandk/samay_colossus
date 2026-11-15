# Supplied backend integration — 13 November 2026

Located the supplied project at C:/Users/Suhan/OneDrive/文件/ChatGPT/agritech. Original files were read, not modified.

## Reused and verified

- Copied the supplied pure Decimal selling optimizer into backend/selling_engine.py. The new /api/v1/recommendations adapter validates exact crop/market/variety/grade, requires explicitly known selling costs, blocks stale reference prices and writes immutable calculation audit records.
- Farmer-provided buyer quotations can produce an actual immediate-sale feasibility calculation even when mandi references are stale. This result is explicitly scoped to immediate_sale_only; it is not a full sell-or-hold optimization. Future costs and holding scenarios are not silently set to zero.
- Frontend validates backend results, displays actual net cash and quantities, and saves accepted immutable device snapshots. Acceptance does not execute a sale. Editing produces a separate new calculation.
- Verified SHA256 of supplied source archives before importing 1,995 official observations. Excluded secondary records, fixtures and out-of-scope Tomato observations. Reimport produced 0 inserts and 1,995 duplicate detections.
- Verified metadata and model hashes for 322 research artifacts, copied them into models/supplied, and recorded config/model-registry.json. Pickles were not executed. /api/v1/models/availability exposes research availability honestly. The supplied bundle itself describes these as research-only, not validated live recommendations.

## Coverage

| Crop | Mandi | Observations | Dates |
|---|---|---:|---|
| Arecanut | Shivamogga | 1,182 | 2025-11-03 to 2026-11-03 |
| Copra | Tiptur | 299 | 2025-11-01 to 2026-11-03 |
| Onion | Hubballi | 162 | 2026-06-01 to 2026-11-04 |
| Potato | Bengaluru | 352 | 2026-04-01 to 2026-11-04 |

Config uses four initial crops and five authentic mandis (including Kolar without selected-crop observations). The supplied database had no sixth authentic mandi; the other market was explicitly DEMO_DATA and was excluded. All observations are stale as of 13 November. Full machine-readable coverage: supplied-coverage.json.

## Validation

18 backend tests passed; 5 frontend unit tests passed; production build passed. Two mobile tests passed after starting the updated real backend; an additional actual-data market screen check is recorded in final verification. The actual arithmetic test runs only in an isolated test database. No illustrative farmer quote was inserted into production. Backend live catalog/coverage reads returned imported observations. Nonfatal upstream deprecation/annotation warnings remain.

## Still incomplete

Stage 3 is not fully accepted. Live model inference is not connected to the new schema; artifacts are verified and inventoried, not promoted into production forecasts. Full holding-option comparisons, future risk ranges and break-even displays still need current data, evaluated forecast serving, and explicit future cost/loss/settlement assumptions. The provided optimizer supports these but the current adapter intentionally implements only today's sale. A sixth authentic mandi, full account-based saving, native Kannada review and physical Android testing remain outstanding. No fabricated forecasts or forced hold outcomes were introduced.

## Reproduction

Run python -m backend.import_supplied <original-agritech-root> after migrations. Configuration is config/supplied-catalog.json. Original CSV bytes and manifests are retained in PriceImport. The SQLite database is ignored by Git; cloning the repo alone does not reproduce data until this import is run. The existing source bundle must remain available for a fresh restore. Start python -m uvicorn backend.main:app --port 8000 and npm run dev in frontend.


## Continued integration update

Forecast serving is now implemented in backend/forecast_service.py using the supplied feature and prediction mathematics, exact scope/horizon matching, pinned model/metadata/evaluation hashes, source-byte validation and current-data gates. It uses actual decision time rather than end-of-day lookahead. No uncalibrated percentage intervals are fabricated. Compatible artifacts with stale observations return unavailable; research results never become validated advice.

The planner now accepts optional explicit holding assumptions, including future costs, adverse price, realization ratio, market lot/step and storage payment timing. With current model inputs and calibrated intervals, the backend computes conditional holding alternatives using the supplied optimizer. Research scenarios are labeled separately; they cannot force a hold recommendation. The comparison selects the best evaluated option in each feasible strategy category. Price Outlook queries the real forecast endpoint. Current live checks for exact Copra/other/local, Potato/local/medium and Arecanut/rashi/local return stale_market_data.

19 backend tests passed after this integration, including isolated inference, stale gating, exact-series refusal and actual net-cash arithmetic. Three mobile browser tests passed, including authentic dated market records. Latest frontend build/test results are reported in the final response. Prior paragraphs describing inference as unconnected are superseded by this update. Stage acceptance is still constrained by stale actual observations, research-only evidence and the missing sixth authentic mandi.

Final verification: 20 backend tests, 5 frontend tests, 3 mobile browser tests, and the production build passed. The live forecast endpoint returned HTTP 503 with stale_market_data for the exact Copra/other/local series. Holding comparison test confirmed cash constraints and kept research holding candidates ineligible for validated recommendations.
