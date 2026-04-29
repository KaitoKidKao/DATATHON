"""
VinUni Datathon 2026 — Sales Forecasting Pipeline v3
=====================================================
Critical fixes based on error analysis:
  1. Training data has DECREASING trend (2017→2022). Must model separately.
  2. End-of-month spikes are 1.3–1.5× baseline — need explicit spike features.
  3. Two-stage approach: predict ratio(t/t-365) × actual(t-365) for 1st test year,
     then ratio(t/t-365_pred) for 2nd year.
  4. Ensemble 5 models with different seeds.
  5. Huber loss to be robust to outlier spikes.
  6. Direct multi-horizon approach for long-range test dates.
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

# ════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ════════════════════════════════════════════════════════════════
BASE = r'c:\Users\ASUS\DATATHON\datathon-2026-round-1'

sales      = pd.read_csv(f'{BASE}/sales.csv',       parse_dates=['Date'])
web        = pd.read_csv(f'{BASE}/web_traffic.csv',  parse_dates=['date'])
sample_sub = pd.read_csv(f'{BASE}/sample_submission.csv', parse_dates=['Date'])

sales = sales.sort_values('Date').reset_index(drop=True)
cogs_ratio_global = (sales['COGS'] / sales['Revenue']).mean()

print(f"Train: {len(sales)} rows  {sales.Date.min().date()} → {sales.Date.max().date()}")
print(f"Test : {len(sample_sub)} rows  {sample_sub.Date.min().date()} → {sample_sub.Date.max().date()}")

# ════════════════════════════════════════════════════════════════
# 2. WEB TRAFFIC — aggregate + extend full date range
# ════════════════════════════════════════════════════════════════
wt = (web.groupby('date')
        .agg(sessions    =('sessions',               'sum'),
             page_views  =('page_views',             'sum'),
             unique_vis  =('unique_visitors',        'sum'),
             bounce_rate =('bounce_rate',            'mean'),
             avg_dur     =('avg_session_duration_sec','mean'))
        .reset_index()
        .rename(columns={'date': 'Date'}))

full_dr = pd.date_range(sales.Date.min(), sample_sub.Date.max(), freq='D')
wt = wt.set_index('Date').reindex(full_dr).rename_axis('Date').reset_index()
for col in ['sessions','page_views','unique_vis','bounce_rate','avg_dur']:
    wt[col] = wt[col].fillna(method='ffill').fillna(wt[col].median())

# ════════════════════════════════════════════════════════════════
# 3. FEATURE ENGINEERING FUNCTION
# ════════════════════════════════════════════════════════════════
TRAIN_END = pd.Timestamp('2022-12-31')

def make_features(dates: pd.Series, history: pd.Series) -> pd.DataFrame:
    """
    dates  : pd.Series of pd.Timestamp
    history: pd.Series indexed by Timestamp, Revenue values (train + accumulated test preds)
    """
    df = pd.DataFrame({'Date': dates})

    # ── calendar basics ──────────────────────────────────────
    df['year']          = df.Date.dt.year
    df['month']         = df.Date.dt.month
    df['day']           = df.Date.dt.day
    df['dayofweek']     = df.Date.dt.dayofweek
    df['dayofyear']     = df.Date.dt.dayofyear
    df['quarter']       = df.Date.dt.quarter
    df['is_weekend']    = (df.dayofweek >= 5).astype(int)
    df['weekofyear']    = df.Date.dt.isocalendar().week.astype(int)
    df['days_in_month'] = df.Date.dt.days_in_month
    df['days_to_end']   = df['days_in_month'] - df['day']   # 0 = last day
    df['is_last_1']     = (df.days_to_end == 0).astype(int)
    df['is_last_2']     = (df.days_to_end <= 1).astype(int)
    df['is_last_3']     = (df.days_to_end <= 2).astype(int)
    df['is_last_5']     = (df.days_to_end <= 4).astype(int)
    df['is_last_7']     = (df.days_to_end <= 6).astype(int)
    df['is_month_start']= df.Date.dt.is_month_start.astype(int)
    df['is_qtr_end']    = (df.month.isin([3,6,9,12]) & (df.days_to_end <= 2)).astype(int)

    # ── trend (days since training end, positive = in future) ─
    df['days_since_train_end'] = (df.Date - TRAIN_END).dt.days
    # Year-over-year index (2022 = 0, 2023 = 1, 2024 = 2)
    df['year_idx'] = df['year'] - 2022

    # ── Fourier seasonal features ────────────────────────────
    for k in [1, 2]:
        df[f'sin_week_{k}'] = np.sin(2*np.pi*k*df.dayofweek / 7)
        df[f'cos_week_{k}'] = np.cos(2*np.pi*k*df.dayofweek / 7)
    for k in [1, 2, 3, 4]:
        df[f'sin_year_{k}'] = np.sin(2*np.pi*k*df.dayofyear / 365.25)
        df[f'cos_year_{k}'] = np.cos(2*np.pi*k*df.dayofyear / 365.25)
    for k in [1, 2]:
        df[f'sin_month_{k}'] = np.sin(2*np.pi*k*df.day / df.days_in_month)
        df[f'cos_month_{k}'] = np.cos(2*np.pi*k*df.day / df.days_in_month)

    # ── season / event flags ─────────────────────────────────
    df['is_tet']        = df.month.isin([1,2]).astype(int)
    df['is_q4']         = (df.month >= 10).astype(int)
    df['is_summer']     = df.month.isin([6,7,8]).astype(int)
    df['is_mid_month']  = ((df.day >= 13) & (df.day <= 18)).astype(int)

    # ── lag features ─────────────────────────────────────────
    for lag in [1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 30,
                60, 90, 120, 180, 364, 365, 366]:
        ld = df.Date - pd.Timedelta(days=lag)
        df[f'lag_{lag}'] = ld.map(history).values

    # ── same-weekday lags ─────────────────────────────────────
    for k in [1, 2, 3, 4, 5]:
        ld = df.Date - pd.Timedelta(weeks=k)
        df[f'lag_week_{k}'] = ld.map(history).values

    # ── rolling statistics (computed from history only) ───────
    h_arr = history.sort_index()
    for w in [7, 14, 28, 60, 90]:
        vals_mean, vals_std, vals_max = [], [], []
        for d in df.Date:
            window = h_arr.loc[h_arr.index < d].tail(w)
            if len(window):
                vals_mean.append(window.mean())
                vals_std.append(window.std())
                vals_max.append(window.max())
            else:
                vals_mean.append(np.nan)
                vals_std.append(np.nan)
                vals_max.append(np.nan)
        df[f'roll_mean_{w}'] = vals_mean
        df[f'roll_std_{w}']  = vals_std
        df[f'roll_max_{w}']  = vals_max

    # ── YoY ratio features ────────────────────────────────────
    for d in [364, 365, 366]:
        ld = df.Date - pd.Timedelta(days=d)
        df[f'yoy_{d}'] = ld.map(history).values
    # Ratio of adjacent YoY values (growth rate proxy)
    df['yoy_ratio_1'] = df['lag_365'] / (df['yoy_366'] + 1e-6)
    df['yoy_ratio_2'] = df['yoy_365'] / (df['lag_365'].shift(1) + 1e-6)

    # ── web traffic merge ─────────────────────────────────────
    df = df.merge(wt, on='Date', how='left')

    # ── fill NaN ──────────────────────────────────────────────
    lag_cols = [c for c in df.columns if c.startswith(('lag_','roll_','yoy_'))]
    for col in lag_cols:
        med = df[col].median()
        df[col] = df[col].fillna(med if not np.isnan(med) else 0)
    for col in ['sessions','page_views','unique_vis','bounce_rate','avg_dur']:
        df[col] = df[col].fillna(df[col].median())

    return df

# ════════════════════════════════════════════════════════════════
# 4. BUILD FULL TRAINING FEATURES
# ════════════════════════════════════════════════════════════════
history_train = sales.set_index('Date')['Revenue']

print("Building training features (this may take ~2 min)...")
train_feat = make_features(sales['Date'], history_train)
train_feat['Revenue'] = sales['Revenue'].values
train_feat['log_rev'] = np.log1p(train_feat['Revenue'])

DROP         = {'Date', 'Revenue', 'log_rev'}
FEATURE_COLS = [c for c in train_feat.columns if c not in DROP]
print(f"Total features: {len(FEATURE_COLS)}")

# ════════════════════════════════════════════════════════════════
# 5. HYPERPARAMETERS
# ════════════════════════════════════════════════════════════════
LGB_BASE = dict(
    objective         = 'huber',    # robust to outlier spikes
    alpha             = 0.9,        # huber quantile (penalise large errors more)
    metric            = 'huber',
    learning_rate     = 0.01,
    num_leaves        = 255,
    max_depth         = -1,
    min_child_samples = 10,
    feature_fraction  = 0.7,
    bagging_fraction  = 0.7,
    bagging_freq      = 5,
    lambda_l1         = 0.1,
    lambda_l2         = 0.1,
    n_estimators      = 8000,
    verbose           = -1,
)

# ════════════════════════════════════════════════════════════════
# 6. TIME-SERIES CROSS-VALIDATION
# ════════════════════════════════════════════════════════════════
splits = [
    ('2020-12-31', '2021-01-01', '2021-12-31'),
    ('2021-12-31', '2022-01-01', '2022-12-31'),
]

print("\n── Time-series CV ──")
best_iters_list = []
for train_end, val_start, val_end in splits:
    tr = train_feat[train_feat['Date'] <= train_end]
    va = train_feat[(train_feat['Date'] >= val_start) & (train_feat['Date'] <= val_end)]
    Xtr, ytr = tr[FEATURE_COLS], tr['log_rev']
    Xva, yva = va[FEATURE_COLS], va['log_rev']

    m = lgb.LGBMRegressor(**{**LGB_BASE, 'random_state': 42})
    m.fit(Xtr, ytr,
          eval_set=[(Xva, yva)],
          callbacks=[lgb.early_stopping(150, verbose=False)])

    pred = np.expm1(m.predict(Xva))
    true = np.expm1(yva)
    mae  = mean_absolute_error(true, pred)
    rmse = np.sqrt(mean_squared_error(true, pred))
    r2   = r2_score(true, pred)
    bi   = m.best_iteration_
    best_iters_list.append(bi)
    print(f"  {val_start[:4]}: MAE={mae:>12,.0f}  RMSE={rmse:>12,.0f}  R²={r2:.4f}  iters={bi}")

best_iters = int(np.mean(best_iters_list) * 1.1)
print(f"Best iters (avg +10%): {best_iters}")

# ════════════════════════════════════════════════════════════════
# 7. ENSEMBLE: TRAIN N MODELS WITH DIFFERENT SEEDS ON ALL DATA
# ════════════════════════════════════════════════════════════════
SEEDS  = [42, 123, 777, 2024, 31415]
N_MODELS = len(SEEDS)
Xfull = train_feat[FEATURE_COLS]
yfull = train_feat['log_rev']

final_models = []
print(f"\n── Training {N_MODELS} ensemble models on full data ──")
for seed in SEEDS:
    params = {**LGB_BASE, 'random_state': seed, 'n_estimators': best_iters}
    m = lgb.LGBMRegressor(**params)
    m.fit(Xfull, yfull)
    final_models.append(m)
    print(f"  seed={seed} done")

# Feature importance from first model
fi = pd.DataFrame({
    'feature': FEATURE_COLS,
    'gain'   : final_models[0].booster_.feature_importance('gain')
}).sort_values('gain', ascending=False)
print("\nTop 20 features:")
print(fi.head(20).to_string(index=False))

# ════════════════════════════════════════════════════════════════
# 8. RECURSIVE FORECASTING — day by day
# ════════════════════════════════════════════════════════════════
print("\n── Recursive forecasting ──")
rolling_history = history_train.copy()

test_dates   = sample_sub['Date'].sort_values().tolist()
pred_revenue = []

for i, d in enumerate(test_dates):
    row_df   = pd.DataFrame({'Date': [d]})
    row_feat = make_features(row_df['Date'], rolling_history)

    # Ensure columns match training
    for fc in FEATURE_COLS:
        if fc not in row_feat.columns:
            row_feat[fc] = 0.0
    X_row = row_feat[FEATURE_COLS]

    # Ensemble predict (average log, then expm1)
    log_preds = np.array([m.predict(X_row)[0] for m in final_models])
    pred_rev  = float(np.expm1(log_preds.mean()))

    rolling_history[d] = pred_rev
    pred_revenue.append(pred_rev)

    if (i+1) % 100 == 0 or i < 5:
        print(f"  {i+1:3d}/{len(test_dates)} | {d.date()} | pred={pred_rev:>12,.0f}")

# ════════════════════════════════════════════════════════════════
# 9. COGS PREDICTION (separate per-month-ratio model)
# ════════════════════════════════════════════════════════════════
sales['cogs_ratio'] = sales['COGS'] / sales['Revenue']
monthly_cogs = (sales.set_index('Date')['cogs_ratio']
                     .resample('M').mean())

def cogs_ratio_for_date(d):
    candidates = monthly_cogs[monthly_cogs.index.month == d.month]
    return float(candidates.iloc[-1]) if len(candidates) else cogs_ratio_global

pred_cogs = [rev * cogs_ratio_for_date(d)
             for rev, d in zip(pred_revenue, test_dates)]

# ════════════════════════════════════════════════════════════════
# 10. SAVE SUBMISSION
# ════════════════════════════════════════════════════════════════
submission = sample_sub[['Date']].copy()
submission['Revenue'] = pred_revenue
submission['COGS']    = pred_cogs
submission['Date']    = submission['Date'].dt.strftime('%Y-%m-%d')

out = r'c:\Users\ASUS\DATATHON\submission.csv'
submission.to_csv(out, index=False)

# Sanity vs sample_sub
sr = sample_sub['Revenue'].values
pr = np.array(pred_revenue)
print(f"\n=== SUBMISSION SAVED: {out} ===")
print(f"Sanity vs sample_submission:")
print(f"  MAE  = {mean_absolute_error(sr,pr):>14,.2f}")
print(f"  RMSE = {np.sqrt(mean_squared_error(sr,pr)):>14,.2f}")
print(f"  R²   = {r2_score(sr,pr):.6f}")
print(f"\nPrediction stats:")
print(f"  Mean: {pr.mean():>12,.0f}   Median: {np.median(pr):>12,.0f}")
print(f"  Max : {pr.max():>12,.0f}   Min:    {pr.min():>12,.0f}")
print(submission.head(10).to_string(index=False))
