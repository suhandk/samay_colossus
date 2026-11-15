# Stage 6 — actual full-stack integration

## Audit and changes

The planner was using an older financial adapter despite a separate Stage 5 service. It lacked capability-backed saved retrieval/recalculation, cancellations, comprehensive OpenAPI contracts and isolated browser tests. The market page derived latest values from history and had no date filter. Reopening a saved plan initially restarted at step one; integration testing found and corrected this to open review directly.

The mobile adapter now converts UI total-charge assumptions into Stage 5 DecisionInput and delegates to its existing compute/persist functions. There is one optimizer, not a second financial implementation. Unknown holding inputs remain unresolved. Crop/mandi/variety/grade selection is exact; no fallback to a different scope occurs. Market-date confirmation and storage evidence are explicit inputs. Future holding options use the existing trusted forecast service. Missing predictions or intervals cannot become supported hold recommendations.

Pydantic request and response models expose planner contracts in OpenAPI. Export with python -m scripts.export_openapi, then npm run contracts in frontend. Generated src/api-contracts.d.ts types the request payload; Zod validates response bodies at runtime. Every UI request passes through src/api.ts, with a 20-second timeout, no-store policy and AbortSignal cancellation. TanStack Query keys isolate scopes, and planner request sequence numbers prevent outdated POST responses from replacing current state. POST requests are not retried automatically.

## Working journeys and screens

Home, language selection, eight-step selling planner, result/alternatives/details, saved drafts and calculations, market prices, price outlook and settings are connected. All financial calculations originate on the backend. Result fields include immediate/future net proceeds, quantities, storage and transaction costs, deterioration, break-even, risk scenarios and difference from immediate sale. Backend English/Kannada explanations accompany the result. Detailed ledgers expand separately.

Editing hides the previous result and marks it outdated. A new recommendation records changed assumptions and its immutable predecessor. Saving is explicit and appends a version; existing saved results are never replaced, so no replacement-confirmation flow is needed. Device-local snapshots preserve original source dates. Saved views verify the server record through its capability token; failed verification shows retry while identifying the saved snapshot as historical. Recalculation is authorized with X-Plan-Token and creates a new ID. Anonymous use needs no account; account-based cross-device history remains unimplemented.

Market Prices now calls both latest/history APIs and supports crop/market, exact variety-grade and start/end dates. Price Outlook requests only registry-supported combinations/horizons; stale or missing forecasts remain unavailable. Dates, money and quantities use locale formatting. Kannada controls/warnings/explanations were exercised and the mobile screenshot inspected. Source-specific variety/grade names remain source labels; their authoritative Kannada translations have not been supplied. Native-speaker terminology and real device TTS still require human/device review.

## Integrated endpoints

- GET /api/catalog and /api/v1/prices/coverage.
- GET /api/v1/prices/latest and /api/v1/prices/history.
- GET /api/v1/models/availability and /api/v1/forecasts.
- POST /api/v1/recommendations, delegating to the same Stage 5 service as POST /api/v1/recommend.
- GET /api/v1/recommendations/{id} with X-Plan-Token.
- POST /api/v1/recommendations/{id}/recalculate-draft with X-Plan-Token, retaining the rich /recalculate API for structured clients.

## Actual validation

52 backend tests passed, including financial mathematics, property-based feasibility/conservation, immutable history and access control. Five frontend unit tests and TypeScript/Vite production build passed. Nonfatal upstream Zod annotation and TestClient deprecation warnings remain.

The new Playwright integration suite launches a real FastAPI process against a new temporary SQLite database and a separate Vite server. It does not mock successful API responses or access farmer production data. Fixture records exist only in that disposable database. Deliberate request abortion is used only for the backend-disconnection fault test.

Sixteen browser checks passed: eight scenarios each at 320×740 and 412×915. Covered full no-storage plan, exact cash response, save/reopen, immutable cash-infeasible recalculation, English/Kannada, explicit unknown buyer/reference scenario, stale-reference blocking, missing forecast/unresolved status, unsupported combination/missing quote, offline indication, API disconnection/retry and horizontal overflow. Both language journeys received the same backend INR 9,850 net under identical isolated inputs. English/Kannada screenshots were generated during the integration run; the Kannada result screenshot was visually inspected. Playwright regenerates test-results on each suite run. These are browser viewport checks, not physical Android device certification.

Commands: python -m pytest backend/tests; python -m scripts.export_openapi; npm run contracts; npm run build; npm test; npm run test:integration. The standard older e2e suite includes historical route-fixture tests; the Stage 6 suite is separately configured and uses the real backend/test database.

## Remaining issues and acceptance boundary

The software journey works for an actual buyer-quote immediate-sale calculation. It correctly refuses unsupported forecast-dependent behavior. Production source observations remain stale; research artifacts and small calibration samples do not support operationally validated holding advice. Only five authentic mandis were supplied; the sixth test-only mandi is never deployed. These inherited data limitations are not resolved by UI integration. Official market calendars and safe-storage conditions are operator assertions, not verified facilities. Local saved-plan capability tokens need the same trusted-device care as financial drafts. No account authentication, physical Android test, native Kannada linguistic sign-off or deployment-wide PostgreSQL test was added. No Prompt 7 work was started. Changes remain uncommitted on sub1.

Final rerun after response-schema integration: all 16 isolated mobile checks passed (22.4s). The three existing browser checks also passed (6.0s). No successful API response is mocked in the isolated integration suite.
