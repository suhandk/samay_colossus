# Stage 5 — actual cash-first optimization results

## Implemented

The deterministic Python Decimal optimizer enumerates sell-now quantities for each supplied feasible holding date, capped at 10,000 evaluations. Each strategy enforces total harvest, storage capacity, safe duration, immediate net cash, market steps and minimum lots. Sell-all remains eligible. A liquidity tie break was corrected to prefer more sold today before shorter holding duration.

Added a strict financial API with explicitly required cost fields (unknown values cannot silently become zero), risk preference, buyer-quote versus reference scenario, safe-storage evidence, cash deadline and exact variety/grade. Future market-date availability must be explicitly confirmed by the operator/farmer; it is recorded as an assertion, not independently verified mandi calendar data. Forecast scenarios are fetched by the backend. User future quotes are supported only as labeled conditional exploration. Client-supplied trusted scenario/model/reliability fields are rejected.

POST /api/v1/recommend and POST /api/v1/recommendations/compare compute and record results. GET /api/v1/recommendations/{id} and POST /api/v1/recommendations/{id}/recalculate require X-Plan-Token. The random capability is returned only at creation; only its hash is stored. Recalculation creates a new record linked to the old one. Anonymous farmer financial inputs are not exposed through a public list. Evidence stores the exact engine input, source metadata, model output and immutable arithmetic ledger. Financial Decimals in the new API serialize as strings.

The existing mobile API adapter also requires explicit market quantity constraints, validates deadlines, and supports risk selection in its request schema. Its frontend now collects lot/step/increment during quantity entry and warns when cash calculations use a market reference. The rich financial API has a separate schema; frontend migration to every rich cost/schedule field is not complete.

## Equations and timing

Gross = sold quantity × buyer price. Net = gross − percentage commission/fees − fixed and variable transport − handling − fixed transaction charges. Monetary settlements round half-up to paise. Fixed sale costs apply only to nonzero sales. Today and future transactions each incur their specified fixed costs.

Remaining quantity compounds daily by multiplying by (1 − daily quantity-loss fraction). Each day's storage charge applies to its opening quantity, plus the explicit fixed storage charge. Marketable future quantity rounds down to the market step; deterioration and rounding loss have zero salvage value. Upfront storage reduces today's net cash; later storage reduces future proceeds. No complete production-cost estimate exists, so outputs are net realization, not farm profit.

Conservative score = adverse total net. Balanced = 0.5 × central + 0.5 × adverse. Aggressive = 0.8 × central + 0.2 × adverse. These are utility weights, not probabilities. Central proceeds are a scenario, not a statistically estimated expectation.

Break-even is the smallest paise-grid future price at which combined net proceeds equal selling all immediately, with exact transaction rounding. Binary search accounts for loss, storage, variable and fixed costs. It is a whole-harvest incremental comparison, not an isolated held-lot comparison when fixed charges are shared.

Cash is required today even if the entered deadline is later. This conservative implementation never relies on uncertain future proceeds to meet the deadline. Past deadlines are rejected. It does not optimize multi-date borrowing or deferred cash obligations.

## Actual tests

52 backend tests passed, including reused supplied optimizer mathematical tests and Hypothesis feasibility/conservation checks (80 generated examples). Cases cover split/hold/sell-all, rising/falling prices, absent forecasts, severe losses, upfront/fixed/variable costs, cash shortfalls, lot rounding, risk preferences and paise break-even. Token authorization, immutable recalculation, unknown-cost rejection, client scenario forgery and exact engine-input replay are checked in isolated test databases. No fixtures are inserted into farmer data.

An illustrative isolated test sells 10 quintals at INR 1,000 with zero explicitly declared charges, producing INR 10,000 net. Another test from the supplied suite sells 11 of 20 quintals and nets INR 10,240 after test charges, satisfying INR 10,000 cash while holding 9. These are test arithmetic examples, not actual transactions or improvement claims.

## Historical research run

Command: python -m backend.backtest_decisions --protocol reports/decision-protocol.json. The predeclared protocol is labeled RESEARCH_ONLY. It assumes 10 quintals, INR 5,000 cash, 10-quintal storage, 0.2% daily quantity loss, INR 1/quintal/day storage, INR 100 transport plus INR 50 transaction charges per nonzero sale, a 3-day horizon and conservative risk. Buyer realization equals dated modal by assumption. Forecast scenarios use prior observed-price persistence and a prior-30-observation minimum stress assumption, not the newly trained champions. Origins are chronological, weekly subsampled and require exact target observations; no interpolation or future information enters the scenario.

145 feasible-origin samples across 15 exact series:

- Mean net difference versus sell-all-now: INR 1,912.28.
- Median net difference: INR 0.00.
- Periods with strictly positive difference: 2.07%.
- Worst difference: −INR 12,999.48.
- Immediate cash success among feasible evaluated samples: 100%.
- Strict as-of eligible origins: 0.

The mean is dominated by rare large gains and is not a farmer-income claim. These are retrospective snapshot scenarios with assumed buyer prices/costs/storage. No-feasible-plan periods are excluded from the feasible-origin success statistic. Strict historical performance is unavailable because source publication vintages and historical buyer quotes are absent. Full per-origin dates and results: reports/decision-backtest.json.

## Limits and status

Fresh observations and operationally validated prediction intervals remain unavailable. Research holding scenarios cannot become validated recommendations. Missing forecasts produce explicit unresolved assumptions and retain only evaluable immediate-sale options. Missing costs are validation failures rather than invented zeros. Market-date availability is an explicit assertion. Crop-specific storage limits/loss rates are user-provided, not verified agronomic advice. No guaranteed buyer, future cash, profit, weather adjustment or forced hold result is introduced. Stage 5 mathematics/API checks pass; operational acceptance remains constrained by those data/evidence limits. Prompt 6 was not started.

Backtest accounting: 145 attempted origins, 0 infeasible origins excluded, 145 feasible samples. Frontend verification: production build, 5 unit tests and 3 mobile browser tests passed.
