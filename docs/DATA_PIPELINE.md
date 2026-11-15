# Authentic data pipeline

## Source investigation, 13 November 2026

The official resource page https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi identifies AGMARKNET daily data. Its page embeds resource identifier `9ef84268-d588-465a-a308-a864a43d0070`, an `api-key` query parameter, and the API host `api.data.gov.in`. A direct API request failed DNS resolution. Consequently authentication validity, actual response fields, pagination semantics, commodity identifiers, coverage and price units were NOT verified. No API adapter is enabled. The AGMARKNET homepage returned HTTP 200 with only 1,003 bytes; this is not a usable historical export. The alternate official variety-wise resource page was reachable, but no authenticated observation payload was obtained.

Official licensing reference: https://data.gov.in/Godl . GODL permits reuse subject to its conditions, attribution and exclusions. Operators must check the specific export's licence and retain the ministry, dataset title, source URL and retrieval date. A reachable catalog page alone is not proof of a valid price record. The captured resource HTML has its public API credential redacted.

## Reviewed CSV workflow

1. Download a real CSV from an official source. Preserve its bytes and source/download URLs. Do not create sample prices.
2. Configure four crops and six mandis with `backend.configure_catalog` only after verifying actual source labels and Kannada names. Register a DataSource with a stable operator ID and the exact official resource URL through an administrative database session. No public source-writing API is exposed.
3. Create a JSON manifest containing source_id, source_url, license_url, retrieved_at (timezone-aware ISO timestamp), verified_by, column_mapping, crop_mapping and market_mapping. Record any manual transformations and the original download hash in additional provenance fields.
4. column_mapping maps canonical keys to actual CSV headers: crop, market, date, minimum, modal, maximum, variety, grade, unit and optional published_at. Omit unit mapping only when manifest.unit has a verified value. Supported units: INR/quintal, INR/kg, INR/tonne. date_format defaults to %Y-%m-%d; explicitly specify the source format. crop_mapping and market_mapping map exact source strings to verified registry IDs. Disambiguate identical market names using state/district before preparing a reviewed export. Optional allowed_pairs restricts accepted crop-market ID pairs.
5. Run `.\.venv\Scripts\python -m backend.ingest path/to/export.csv path/to/manifest.json`. Each import is transactional. Header/manifest failures roll back; row failures are quarantined. Raw CSV and row values remain in the database, including rejected records. Import reports give accepted, duplicate, quarantine, revision and flagged counts.

Missing varieties/grades are quarantined rather than silently mapped to another variety. A changed existing observation requires a newer source publication timestamp; ambiguous changes are quarantined for manual review. Replaying the same latest data adds an audit batch but no observation. Older revisions cannot replace newer values. Prices use Decimal; a change exceeding 50% from the previous same-source/variety/grade observation is flagged and retained. This is a review heuristic, not proof of error. Import in chronological order for spike comparisons; backfills may require retrospective review.

## Refresh and pagination

`python -m backend.refresh manifest.json` downloads a reviewed manifest.download_url from a government HTTPS host, with a 30-second timeout, three bounded attempts and a 20 MB cap. Redirects are rejected for review. Run this one-shot command daily through cron or Windows Task Scheduler; no scheduled job has been installed. It logs structured completion/failure and never substitutes stale data. No verified download URL is shipped. Import large historical exports as separate files. API history supports offset/limit with a maximum page size of 1,000. Upstream API pagination remains blocked until its actual contract is verified.

## Freshness

The official dataset is described as daily, not real-time. SAMAY policy is current at age 0–1 calendar days, delayed at 2–3, stale after 3, unavailable if missing or future-dated. These are conservative product thresholds, not a government publication SLA. They do not assume every mandi trades daily. Retrieval time never refreshes the observation date. Age uses the Asia/Kolkata calendar date.

## API

GET /api/v1/crops and /markets return registry records with source references. /markets/availability and /prices/coverage provide all configured pairs including unavailable cells. /prices/history supports crop, market, variety, grade, start/end ISO dates and offset/limit. /prices/latest requires an exact crop, market, variety and grade to prevent substitution. /data/status reports recent imports and quarantine totals; /data/sources lists reviewed sources. All envelopes include generated_at; price records include source, observation date, retrieval time, publication time, original and normalized units, flags and hashes.

## Recovery

Back up the full database before imports. PostgreSQL: use pg_dump and restore into a separate database with pg_restore. SQLite: stop writers and use SQLite backup API. Validate counts, hashes, revision links and quarantine after restoring. Raw CSV plus stored manifest can reconstruct accepted observations in a clean registry, but does not by itself reconstruct the full audit timeline; preserve full database backups. Isolated tests verify raw-record reimport; deployment backup/restore has not been exercised.
