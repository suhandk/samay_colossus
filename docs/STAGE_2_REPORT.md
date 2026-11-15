# Stage 2 — partial implementation; live-data acceptance blocked

## Verified sources and access

The official data.gov.in daily AGMARKNET catalog and GODL licensing reference were inspected. The resource page embeds the API URL and api-key parameter. The API host failed DNS resolution; actual API payload, credential validity and commodity/market identifiers remain unverified. No invented API adapter was added. See DATA_PIPELINE.md for evidence, CSV procedure and limitations.

## Actual data and coverage

Authentic observations imported: **0**. Configured crops: **0**; markets: **0**. Date ranges: unavailable. No 4-by-6 coverage can truthfully be populated without verified registry selections. The configurable registry is preserved. Coverage API returns an empty matrix until configured; thereafter each missing pair explicitly reports unavailable. There are no synthetic production records.

## Implementation

Added migration 0002 with price imports, versioned price records and quarantine tables. CSV ingestion retains raw data, hashes, source provenance, units and timestamps; validates prices, dates, mappings and quality; detects duplicates; quarantines ambiguous revisions; preserves valid timestamped revisions and flags large changes. Added a bounded government-CSV refresh CLI suitable for external scheduling. No actual schedule or verified CSV download URL has been configured.

All eight requested API routes are present. Exact variety/grade are mandatory for latest-price requests. History is paginated. Market UI supports selection, min/modal/max, source/date/retrieval/freshness and a trend when authentic data exists, with bilingual explanations and explicit unavailable/error states.

## Actual verification

- Alembic upgrade to 0002 succeeded on the local SQLite database.
- Pytest: 15 passed (one upstream TestClient deprecation warning).
- Vitest: 2 passed.
- TypeScript/Vite production build passed; dependency annotation and bundle-size warnings remain.
- Live server started on 8001. GET history, coverage and data status returned real empty-state responses, captured in source-investigation/local-api-results.json.
- Tests cover CSV import, duplicate prevention, unit conversion, invalid and missing fields, revisions, stale dates, unknown mappings, API responses and reconstruction from retained raw CSV.
- Full PostgreSQL backup restoration, authenticated API imports, upstream pagination and populated-price browser rendering remain unverified.

## Remaining blockers

Need an authentic official CSV export with provenance or functioning API access, then verify four crop and six mandi identities and import available history. Actual-price display and 24-cell coverage acceptance cannot pass yet. Operator registration of reviewed sources and mappings is intentionally explicit. Catalog configuration and source review do not establish that every combination exists. CSV spike checks currently compare earlier stored rows, so backfills need retrospective quality review. Concurrent import conflicts fail transactionally rather than being retried. Prompt 3 was not started. Changes remain uncommitted.
