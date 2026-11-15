from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from contextlib import nullcontext
import os
import numpy as np
import pandas as pd
IST=ZoneInfo("Asia/Kolkata")
LAGS=(1,2,3,7,14,30)
WINDOWS=(7,14,30)
FEATURES=[f"lag_{n}_obs_inr_per_quintal" for n in LAGS]+[f"rolling_{stat}_{n}_obs_inr_per_quintal" for n in WINDOWS for stat in ("mean","median","std")]+["origin_weekday","origin_month","target_weekday","target_month","days_since_latest_report","history_30_obs_span_days"]


def midnight(value: date) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(value, datetime.min.time(), IST)).tz_convert("UTC")

def asof(vintages: pd.DataFrame, cutoff: pd.Timestamp, before: date | None = None, inclusive: bool = True) -> pd.DataFrame:
    if vintages.empty:
        return empty_vintages()
    mask = vintages.available_at <= cutoff if inclusive else vintages.available_at < cutoff
    if before is not None:
        mask &= vintages.report_date < before
    frame = vintages.loc[mask].copy()
    if frame.empty:
        return frame
    # The common immutable snapshot has one vintage per report date. Avoid a
    # repeated groupby over its entire history; the result is exactly identical.
    if frame.report_date.is_unique:
        return frame.sort_values("report_date")
    # Do not silently resolve ambiguous simultaneous source vintages.
    if (frame.groupby(["report_date", "available_at"]).price.nunique() > 1).any():
        raise ValueError("Conflicting prices at identical report/availability timestamp")
    return frame.sort_values(["report_date", "available_at", "row_id"]).drop_duplicates("report_date", keep="last").sort_values("report_date")

def features_at(vintages: pd.DataFrame, origin: date, horizon: int, *, decision_at=None) -> tuple[dict, dict]:
    if type(horizon) is not int or not 1 <= horizon <= 730:
        raise ValueError("Horizon must be an integer from 1 to 730 calendar days")
    cutoff = midnight(origin) if decision_at is None else pd.Timestamp(decision_at)
    if cutoff.tzinfo is None or not midnight(origin) <= cutoff < midnight(origin+timedelta(days=1)):
        raise ValueError("Decision timestamp must be timezone-aware and inside the selected origin date")
    history = asof(vintages, cutoff, before=origin)
    values = history.price.to_numpy(dtype=float)
    features = {f"lag_{n}_obs_inr_per_quintal": float(values[-n]) if len(values) >= n else np.nan for n in LAGS}
    for n in WINDOWS:
        chunk = values[-n:]
        for stat, fn in (("mean", np.mean), ("median", np.median), ("std", lambda x: np.std(x, ddof=1))):
            features[f"rolling_{stat}_{n}_obs_inr_per_quintal"] = float(fn(chunk)) if len(values) >= n else np.nan
    target = origin + timedelta(days=horizon)
    age = (origin - history.iloc[-1].report_date).days if len(history) else np.nan
    features.update(origin_weekday=origin.weekday(), origin_month=origin.month, target_weekday=target.weekday(), target_month=target.month, days_since_latest_report=age,
                    history_30_obs_span_days=(history.iloc[-1].report_date - history.iloc[-30].report_date).days if len(history) >= 30 else np.nan)
    used = history.tail(30)
    audit = {"decision_at": cutoff.isoformat(), "history_count": len(history),
             "max_feature_report_date": used.report_date.max().isoformat() if len(used) else None,
             "max_feature_available_at": used.available_at.max().isoformat() if len(used) else None,
             "source_row_ids": used.row_id.tolist()}
    return features, audit

def thread_context():
    if os.name == "nt":
        return nullcontext()
    from threadpoolctl import threadpool_limits
    return threadpool_limits(limits=1)

def seasonal_value(vintages, origin, horizon):
    previous = origin + timedelta(days=horizon) - timedelta(days=7)
    while previous >= origin:
        previous -= timedelta(days=7)
    history = asof(vintages, midnight(origin), before=origin)
    match = history[history.report_date == previous]
    return float(match.iloc[-1].price) if len(match) else np.nan

def relative_inputs(frame):
    """Only existing causal inputs; normalize price levels and encode known calendars."""
    inputs=frame[FEATURES].copy()
    base=np.maximum(frame.lag_1_obs_inr_per_quintal.to_numpy(dtype=float),.01)
    for column in inputs:
        if column.endswith("inr_per_quintal"):
            inputs[column]=inputs[column]/base-(0 if "std_" in column else 1)
    for column,period in (("origin_weekday",7),("target_weekday",7),("origin_month",12),("target_month",12)):
        angle=2*np.pi*inputs[column]/period
        inputs[column+"_sin"]=np.sin(angle)
        inputs[column+"_cos"]=np.cos(angle)
    return inputs

def predict_rows(name, model, frame):
    if name == "naive":
        result = frame["lag_1_obs_inr_per_quintal"].to_numpy()
    elif name in {"mean_14", "median_14"}:
        stat = name.split("_")[0]
        result = frame[f"rolling_{stat}_14_obs_inr_per_quintal"].to_numpy()
    elif name == "seasonal_naive":
        # Registered fallback is part of this candidate, identical in all partitions.
        result = frame.seasonal_price.fillna(frame.lag_1_obs_inr_per_quintal).to_numpy()
    elif name.startswith("blend_naive_mean14_"):
        weight=float(name.rsplit("_",1)[1])/100
        result=(1-weight)*frame.lag_1_obs_inr_per_quintal.to_numpy()+weight*frame.rolling_mean_14_obs_inr_per_quintal.to_numpy()
    elif "_return" in name:
        with thread_context():
            result=frame.lag_1_obs_inr_per_quintal.to_numpy()*(1+model.predict(relative_inputs(frame)))
    else:
        with thread_context():
            result = model.predict(frame[FEATURES])
    result = np.asarray(result, dtype=float)
    if not np.isfinite(result).all():
        raise ValueError("Model produced nonfinite predictions")
    return np.maximum(result, 0)
def empty_vintages():
    return pd.DataFrame(columns=["report_date","available_at","price","batch_id","row_id","file_sha256"])
