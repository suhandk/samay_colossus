# Stage 4 actual evaluation report

Authentic official observations only. Exact crop/market/variety/grade scope. No random split or imputation.

| Crop | Variety / grade | Horizon | Winner | Holdout n | MAE INR/q | WAPE % | Baseline MAE INR/q |
|---|---|---:|---|---:|---:|---:|---:|
| arecanut | bette / local | 7 | hist_gradient_boosting | 21 | 3711.41 | 6.63 | 2355.52 |
| arecanut | gorabalu / local | 7 | ridge | 21 | 4100.66 | 11.38 | 1225.67 |
| arecanut | other / local | 7 | ridge | 18 | 9498.91 | 27.71 | 7693.94 |
| arecanut | rashi / local | 7 | last | 22 | 1294.18 | 2.73 | 1294.18 |
| arecanut | saraku / local | 7 | hist_gradient_boosting | 20 | 5869.91 | 7.65 | 10382.65 |
| copra | other / local | 1 | hist_gradient_boosting | 24 | 1264.14 | 7.09 | 995.83 |
| copra | other / local | 3 | hist_gradient_boosting | 24 | 1568.22 | 8.76 | 808.33 |
| copra | other / local | 7 | ridge | 28 | 917.82 | 5.10 | 1057.14 |

45 evaluations across 15 series; 8 passed sample requirements and 37 were insufficient. Calibration partitions contain only 15–22 samples in eligible evaluations; all newly evaluated intervals are unavailable under the predeclared minimum of 30. Seasonal naive was eligible only when its exact historical weekly references existed for every evaluated row; no weekly fallback was invented. LightGBM requires at least 500 training examples and was not eligible for these small series. Ridge scaling was fitted only on each training fold. Rolling-origin checks use training prefixes.

Model choice is frozen after validation; calibration supplies residual radii only and final holdout never selects the winner. Targets crossing partition boundaries are purged. The selected model remains fit on the initial training partition; there is no silent full-history refit.

A second independent run reproduced selected candidates, metrics, radii, versions and pickled model hashes exactly. Full partition dates, all metrics, comparisons, anomaly/missing-date inspection and limitations are in models/evaluated/report.json.

Historical source publication and revision timestamps are unknown. This is retrospective snapshot evaluation, not a reconstruction of prices actually available at each historical forecast time. Reporting gaps do not establish market closures. Monthly patterns are descriptive and do not establish seasonality. Current source observations remain stale; current operational forecasts are withheld. No artifact was automatically promoted.

Commands: python -m backend.train_forecasts; python -m backend.train_forecasts --output models/repro-check; python -m pytest backend/tests. Explicit research deployment: python -m backend.promote_forecast VERSION. This requires an evaluated version and pinned model hash and still returns limited evidence, never validated.

API: POST /api/v1/predict, GET /api/v1/forecasts, GET /api/v1/models/status. Unsupported scopes/horizons, missing source history, integrity failures and stale data do not return replacement predictions. Valid successful payloads contain provenance, model/training timestamps, target date, last observed date and limitations. No training occurs during requests.

Remaining: fresh authenticated observations; actual publication/revision vintages; more calibration and multiple-year series; operational acceptance criteria established with agronomic/market review. Prompt 5 was not started.