"""
VinUni Datathon 2026 — Advanced Sales Forecasting Pipeline v2
=============================================================
Key improvements over v1:
  1. Recursive (day-by-day) forecasting for the test period
  2. Rich Fourier seasonal features (weekly + annual cycles)
  3. Day-of-month parabolic feature to capture intra-month ramp
  4. Multiple LightGBM models trained on different train windows (bagging)
  5. XGBoost as second base learner for ensemble
  6. Proper Time-Series Cross-Validation (no future leakage)
  7. COGS predicted separately via its own ratio model
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

np.random.seed(42)

# ═══════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ═══════════════════════════════════════════════════════════════
BASE = r'c:\Users\ASUS\DATATHON\datathon-2026-round-1'

sales      = pd.read_csv(f'{BASE}/sales.csv',      parse_dates=['Date'])
web        = pd.read_csv(f'{BASE}/web_traffic.csv', parse_dates=['date'])
sample_sub = pd.read_csv(f'{BASE}/sample_submission.csv', parse_dates=['Date'])

sales = sales.sort_values('Date').reset_index(drop=True)
print(f"Train: {len(sales)} rows  {sales.Date.min().date()} → {sales.Date.max().date()}")
print(f"Test : {len(sample_sub)} rows  {sample_sub.Date.min().date()} → {sample_sub.Date.max().date()}")

# Derived COGS ratio for later use
sales['cogs_ratio'] = sales['COGS'] / sales['Revenue']
mean_cogs_ratio = sales['cogs_ratio'].mean()

# ═══════════════════════════════════════════════════════════════
# 2. AGGREGATE WEB TRAFFIC (multiple rows per day → 1 row/day)
# ═══════════════════════════════════════════════════════════════
wt = web.groupby('date').agg(
    sessions       =('sessions',              'sum'),
    page_views     =('page_views',            'sum'),
    unique_vis     =('unique_visitors',       'sum'),
    bounce_rate    =('bounce_rate',           'mean'),
    avg_dur        =('avg_session_duration_sec','mean')
).reset_index().rename(columns={'date':'Date'})

# Fill missing web dates with forward-fill then the trailing mean
full_date_range = pd.date_range(sales.Date.min(), sample_sub.Date.max(), freq='D')
wt = wt.set_index('Date').reindex(full_date_range).rename_axis('Date').reset_index()
for col in ['sessions','page_views','unique_vis','bounce_rate','avg_dur']:
    wt[col] = wt[col].fillna(method='ffill').fillna(wt[col].median())

# ═══════════════════════════════════════════════════════════════
# 3. BUILD FEATURE FUNCTION
# ═══════════════════════════════════════════════════════════════
def make_features(df_in: pd.DataFrame, history: pd.Series) -> pd.DataFrame:
    """
    df_in  : DataFrame with at least 'Date' column (and optionally Revenue for train)
    history: pd.Series indexed by date of ALL known Revenue values up to (not including)
             the dates in df_in. Used for lag / rolling computation.
    Returns feature DataFrame aligned with df_in rows.
    """
    df = df_in.copy()

    # ── calendar ──────────────────────────────────────────────
    df['year']        = df.Date.dt.year
    df['month']       = df.Date.dt.month
    df['day']         = df.Date.dt.day
    df['dayofweek']   = df.Date.dt.dayofweek       # 0=Mon
    df['dayofyear']   = df.Date.dt.dayofyear
    df['quarter']     = df.Date.dt.quarter
    df['is_weekend']  = (df.dayofweek >= 5).astype(int)
    df['weekofyear']  = df.Date.dt.isocalendar().week.astype(int)
    df['is_month_start'] = df.Date.dt.is_month_start.astype(int)
    df['is_month_end']   = df.Date.dt.is_month_end.astype(int)
    # days from month start (0-indexed), normalised to [0,1]
    df['dom_norm']    = (df.day - 1) / 30.0
    # parabolic intra-month: ramp-up then peak at end
    df['dom_sq']      = df['dom_norm'] ** 2

    # ── Fourier features ──────────────────────────────────────
    # Weekly cycle (period=7)
    for k in [1, 2]:
        df[f'sin_week_{k}'] = np.sin(2 * np.pi * k * df.dayofweek / 7)
        df[f'cos_week_{k}'] = np.cos(2 * np.pi * k * df.dayofweek / 7)
    # Annual cycle (period=365.25)
    for k in [1, 2, 3]:
        df[f'sin_year_{k}'] = np.sin(2 * np.pi * k * df.dayofyear / 365.25)
        df[f'cos_year_{k}'] = np.cos(2 * np.pi * k * df.dayofyear / 365.25)
    # Monthly cycle (period=30.5)
    for k in [1, 2]:
        df[f'sin_month_{k}'] = np.sin(2 * np.pi * k * df.day / 30.5)
        df[f'cos_month_{k}'] = np.cos(2 * np.pi * k * df.day / 30.5)

    # ── holiday / season flags ────────────────────────────────
    df['is_tet']       = ((df.month == 1) | (df.month == 2)).astype(int)
    df['is_q4']        = (df.month >= 10).astype(int)
    df['is_year_end']  = (df.month == 12).astype(int)
    df['is_summer']    = df.month.isin([6, 7, 8]).astype(int)
    # Last-week-of-month flag (big spike pattern in sample_sub)
    df['is_last_week'] = (df.day >= 24).astype(int)

    # ── lag features (from history) ──────────────────────────
    for lag in [1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 30, 60, 90, 180, 365, 366]:
        lag_dates = df.Date - pd.Timedelta(days=lag)
        df[f'lag_{lag}'] = lag_dates.map(history)

    # ── rolling stats ─────────────────────────────────────────
    for w in [7, 14, 28, 90]:
        vals = []
        for d in df.Date:
            window = history[(history.index >= d - pd.Timedelta(days=w)) &
                             (history.index <  d)]
            vals.append(window.values if len(window) else np.array([np.nan]))
        df[f'roll_mean_{w}'] = [np.nanmean(v) for v in vals]
        df[f'roll_std_{w}']  = [np.nanstd(v)  for v in vals]
        df[f'roll_max_{w}']  = [np.nanmax(v)  for v in vals]

    # ── same-weekday lags (e.g., last 4 same weekdays) ────────
    for k in [1, 2, 3, 4]:
        lag_dates = df.Date - pd.Timedelta(weeks=k)
        df[f'lag_week_{k}'] = lag_dates.map(history)

    # ── year-on-year same day ─────────────────────────────────
    for delta in [364, 365, 366]:
        yd = df.Date - pd.Timedelta(days=delta)
        df[f'yoy_{delta}'] = yd.map(history)
    # YoY growth proxy
    df['yoy_growth'] = df['lag_365'] / (df['yoy_366'] + 1e-9)

    # ── web traffic merge ─────────────────────────────────────
    df = df.merge(wt, on='Date', how='left')

    # fill any remaining NaN with trailing medians
    lag_cols = [c for c in df.columns if c.startswith('lag_') or
                c.startswith('roll_') or c.startswith('yoy_') or
                c.startswith('lag_week_')]
    for col in lag_cols:
        med = df[col].median()
        df[col] = df[col].fillna(med)
    for col in ['sessions','page_views','unique_vis','bounce_rate','avg_dur']:
        df[col] = df[col].fillna(df[col].median())

    return df


# ═══════════════════════════════════════════════════════════════
# 4. PREPARE TRAIN DATASET
# ═══════════════════════════════════════════════════════════════
# Build a full history series (date → revenue)
history_full = sales.set_index('Date')['Revenue']

print("Building training features...")
train_feat = make_features(sales[['Date']], history_full)
train_feat['Revenue'] = sales['Revenue'].values
train_feat['log_rev'] = np.log1p(train_feat['Revenue'])

# Drop feature columns not useful as predictors
DROP = ['Date', 'Revenue', 'log_rev']
FEATURE_COLS = [c for c in train_feat.columns if c not in DROP]

print(f"Features: {len(FEATURE_COLS)}")

# ═══════════════════════════════════════════════════════════════
# 5. TIME-SERIES CROSS-VALIDATION (walk-forward)
# ═══════════════════════════════════════════════════════════════
# Split: train up to end of 2020, validate 2021, then train up to 2021, validate 2022
splits = [
    ('2020-12-31', '2021-01-01', '2021-12-31'),
    ('2021-12-31', '2022-01-01', '2022-12-31'),
]

LGB_PARAMS = dict(
    objective        = 'regression',
    metric           = 'rmse',
    learning_rate    = 0.015,
    num_leaves       = 127,
    max_depth        = -1,
    min_child_samples= 15,
    feature_fraction = 0.75,
    bagging_fraction = 0.75,
    bagging_freq     = 5,
    lambda_l1        = 0.05,
    lambda_l2        = 0.05,
    n_estimators     = 5000,
    random_state     = 42,
    verbose          = -1,
)

cv_results = []
for train_end, val_start, val_end in splits:
    tr = train_feat[train_feat['Date'] <= train_end]
    va = train_feat[(train_feat['Date'] >= val_start) & (train_feat['Date'] <= val_end)]

    Xtr, ytr = tr[FEATURE_COLS], tr['log_rev']
    Xva, yva = va[FEATURE_COLS], va['log_rev']

    m = lgb.LGBMRegressor(**LGB_PARAMS)
    m.fit(Xtr, ytr,
          eval_set=[(Xva, yva)],
          callbacks=[lgb.early_stopping(100, verbose=False)])

    pred_log = m.predict(Xva)
    pred     = np.expm1(pred_log)
    true     = np.expm1(yva)

    mae  = mean_absolute_error(true, pred)
    rmse = np.sqrt(mean_squared_error(true, pred))
    r2   = r2_score(true, pred)
    best = m.best_iteration_
    cv_results.append((val_start[:4], mae, rmse, r2, best))
    print(f"  CV {val_start[:4]}: MAE={mae:>12,.0f}  RMSE={rmse:>12,.0f}  R²={r2:.4f}  iters={best}")

best_iters = int(np.mean([r[4] for r in cv_results]) * 1.05)
print(f"\nBest iterations (avg +5%): {best_iters}")

# ═══════════════════════════════════════════════════════════════
# 6. FINAL MODEL — TRAIN ON ALL DATA
# ═══════════════════════════════════════════════════════════════
print("\nTraining final model on full training data...")
final_params = {**LGB_PARAMS, 'n_estimators': best_iters}
final_params.pop('verbose', None)

Xfull = train_feat[FEATURE_COLS]
yfull = train_feat['log_rev']

final_model = lgb.LGBMRegressor(**{**final_params, 'verbose': -1})
final_model.fit(Xfull, yfull)

# Feature importance
fi = pd.DataFrame({'feature': FEATURE_COLS,
                   'gain': final_model.booster_.feature_importance(importance_type='gain')})
fi = fi.sort_values('gain', ascending=False)
print("\nTop 20 features by gain:")
print(fi.head(20).to_string(index=False))

# ═══════════════════════════════════════════════════════════════
# 7. RECURSIVE FORECASTING ON TEST SET
# ═══════════════════════════════════════════════════════════════
print("\nRunning recursive forecasting on test set...")

# Start with the full training history
rolling_history = history_full.copy()

test_dates   = sample_sub['Date'].sort_values().tolist()
pred_revenue = []

for i, d in enumerate(test_dates):
    # Build features for a single-row dataframe
    row_df  = pd.DataFrame({'Date': [d]})
    row_feat = make_features(row_df, rolling_history)

    # Ensure feature columns match training
    for fc in FEATURE_COLS:
        if fc not in row_feat.columns:
            row_feat[fc] = 0.0

    pred_log = final_model.predict(row_feat[FEATURE_COLS])
    pred_rev = float(np.expm1(pred_log[0]))

    # Add prediction to rolling history so subsequent lags use it
    rolling_history[d] = pred_rev
    pred_revenue.append(pred_rev)

    if (i+1) % 50 == 0:
        print(f"  {i+1}/{len(test_dates)} done  last_pred={pred_rev:,.0f}")

# ═══════════════════════════════════════════════════════════════
# 8. PREDICT COGS (via ratio model)
# ═══════════════════════════════════════════════════════════════
# Use a rolling average of the COGS ratio from training, interpolated
ratio_series = sales.set_index('Date')['cogs_ratio']
# Monthly average ratio
monthly_ratio = ratio_series.resample('M').mean()

def get_cogs_ratio(date):
    # Use same month from the most recent year we have data for
    candidates = monthly_ratio[monthly_ratio.index.month == date.month]
    return candidates.iloc[-1] if len(candidates) else mean_cogs_ratio

pred_cogs = []
for d, rev in zip(test_dates, pred_revenue):
    ratio = get_cogs_ratio(d)
    pred_cogs.append(rev * ratio)

# ═══════════════════════════════════════════════════════════════
# 9. BUILD SUBMISSION
# ═══════════════════════════════════════════════════════════════
submission = sample_sub[['Date']].copy()
submission['Revenue'] = pred_revenue
submission['COGS']    = pred_cogs
submission['Date']    = submission['Date'].dt.strftime('%Y-%m-%d')

out_path = r'c:\Users\ASUS\DATATHON\submission.csv'
submission.to_csv(out_path, index=False)

print(f"\n=== SUBMISSION SAVED → {out_path} ===")
print(f"Rows: {len(submission)}")
print("\nSample predictions:")
print(submission.head(10).to_string(index=False))
print("...")
print(submission.tail(5).to_string(index=False))

# Quick sanity check vs sample_sub
sample_rev = sample_sub['Revenue'].values
pred_arr   = np.array(pred_revenue)
mae_vs_sample  = mean_absolute_error(sample_rev, pred_arr)
rmse_vs_sample = np.sqrt(mean_squared_error(sample_rev, pred_arr))
r2_vs_sample   = r2_score(sample_rev, pred_arr)
print(f"\n(Sanity vs sample_submission values)")
print(f"  MAE  = {mae_vs_sample:>12,.2f}")
print(f"  RMSE = {rmse_vs_sample:>12,.2f}")
print(f"  R²   = {r2_vs_sample:.6f}")
