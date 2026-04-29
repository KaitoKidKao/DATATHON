"""
VinUni Datathon 2026 — Sales Forecasting Pipeline v4
=====================================================
KEY INSIGHT: Revenue spikes are driven by annual promotions + Vietnamese holidays.
  - Spring Sale (Mar 18–Apr 17): huge spike March/April
  - Mid-Year Sale (Jun 23–Jul 22): spike June/July
  - Fall Launch (Aug 30–Oct 1): spike Aug/Sept  
  - Year-End Sale (Nov 18–Jan 2): spike Nov/Dec
  - Urban Blowout (Jul 30–Sep 2): spike July/Aug
  - Rural Special (Jan 30–Mar 1): spike Jan/Feb
  - National holidays: Apr 30 (Liberation), May 1 (Labor), Sep 2 (National Day)

ARCHITECTURE:
  - RMSE loss (NOT Huber) — must predict spikes
  - 87+ features including promotion calendar + holiday flags
  - 5-seed ensemble
  - Recursive forecasting (lag_365 for 2023 from actual training = accurate)
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
TRAIN_END = pd.Timestamp('2022-12-31')

print(f"Train: {len(sales)} rows  {sales.Date.min().date()} → {sales.Date.max().date()}")
print(f"Test : {len(sample_sub)} rows  {sample_sub.Date.min().date()} → {sample_sub.Date.max().date()}")

# ════════════════════════════════════════════════════════════════
# 2. WEB TRAFFIC
# ════════════════════════════════════════════════════════════════
wt = (web.groupby('date')
        .agg(sessions   =('sessions',               'sum'),
             page_views =('page_views',             'sum'),
             unique_vis =('unique_visitors',        'sum'),
             bounce_rate=('bounce_rate',            'mean'),
             avg_dur    =('avg_session_duration_sec','mean'))
        .reset_index().rename(columns={'date': 'Date'}))

full_dr = pd.date_range(sales.Date.min(), sample_sub.Date.max(), freq='D')
wt = wt.set_index('Date').reindex(full_dr).rename_axis('Date').reset_index()
for col in ['sessions','page_views','unique_vis','bounce_rate','avg_dur']:
    wt[col] = wt[col].fillna(method='ffill').fillna(wt[col].median())

# ════════════════════════════════════════════════════════════════
# 3. PROMOTION CALENDAR (extrapolated annually)
# ════════════════════════════════════════════════════════════════
def build_promo_features(dates: pd.Series) -> pd.DataFrame:
    """Build promotion and holiday features for any date range."""
    df = pd.DataFrame({'Date': dates})
    m = df.Date.dt.month
    d = df.Date.dt.day
    yr = df.Date.dt.year

    # ── Annual recurring promotions (by month/day bounds) ────
    # Spring Sale: Mar 18 – Apr 17
    df['in_spring']     = ((m == 3) & (d >= 18) | (m == 4) & (d <= 17)).astype(int)
    # Mid-Year Sale: Jun 23 – Jul 22
    df['in_midyear']    = ((m == 6) & (d >= 23) | (m == 7) & (d <= 22)).astype(int)
    # Fall Launch: Aug 30 – Oct 1
    df['in_fall']       = ((m == 8) & (d >= 30) | (m == 9) | (m == 10) & (d == 1)).astype(int)
    # Year-End Sale: Nov 18 – Jan 2
    df['in_yearend']    = ((m == 11) & (d >= 18) | (m == 12) | (m == 1) & (d <= 2)).astype(int)
    # Urban Blowout: Jul 30 – Sep 2
    df['in_blowout']    = ((m == 7) & (d >= 30) | (m == 8) | (m == 9) & (d <= 2)).astype(int)
    # Rural Special: Jan 30 – Mar 1
    df['in_rural']      = ((m == 1) & (d >= 30) | (m == 2) | (m == 3) & (d == 1)).astype(int)

    # ── Days remaining in current promotion ──────────────────
    # Spring Sale end = Apr 17
    spring_end_day = pd.to_datetime(dict(year=yr, month=4, day=17))
    df['days_to_spring_end'] = np.where(df['in_spring'] == 1,
        (spring_end_day - df.Date).dt.days.clip(0, 30), -1)

    # Mid-Year Sale end = Jul 22
    midyr_end_day = pd.to_datetime(dict(year=yr, month=7, day=22))
    df['days_to_midyr_end'] = np.where(df['in_midyear'] == 1,
        (midyr_end_day - df.Date).dt.days.clip(0, 30), -1)

    # Year-End Sale end = Dec 31 (or Jan 2 next year)
    df['days_to_yearend_end'] = np.where(df['in_yearend'] == 1,
        ((pd.to_datetime(dict(year=np.where(m<=2, yr, yr+1), month=1, day=2))) - df.Date).dt.days.clip(0, 50), -1)

    # ── Composite: in any promotion ──────────────────────────
    df['in_any_promo'] = ((df['in_spring'] | df['in_midyear'] | df['in_fall'] |
                           df['in_yearend'] | df['in_blowout'] | df['in_rural']) > 0).astype(int)

    # ── Days to promo start (upcoming promo effect) ──────────
    # Spring Sale starts Mar 18
    spring_start = pd.to_datetime(dict(year=yr, month=3, day=18))
    df['days_to_spring_start'] = (spring_start - df.Date).dt.days.clip(-30, 30)

    # ── Vietnamese holiday rush features ────────────────────
    # Pre-April-30 rush (people buy before holiday, day -5 to -1)
    apr30 = pd.to_datetime(dict(year=yr, month=4, day=30))
    df['days_to_apr30'] = (apr30 - df.Date).dt.days
    df['pre_apr30']  = ((df['days_to_apr30'] >= 0) & (df['days_to_apr30'] <= 6)).astype(int)
    df['post_apr30'] = ((df['days_to_apr30'] >= -3) & (df['days_to_apr30'] < 0)).astype(int)

    # Sep 2 National Day
    sep2 = pd.to_datetime(dict(year=yr, month=9, day=2))
    df['days_to_sep2'] = (sep2 - df.Date).dt.days
    df['pre_sep2']  = ((df['days_to_sep2'] >= 0) & (df['days_to_sep2'] <= 5)).astype(int)

    # Tet (approx Jan 20-Feb 10 each year — shopping rush before Tet)
    df['pre_tet']   = ((m == 1) & (d >= 20) | (m == 2) & (d <= 10)).astype(int)

    # ── Quarter-end rush (last 5 days of each quarter) ───────
    df['is_qtr_end_month'] = m.isin([3, 6, 9, 12]).astype(int)
    df['is_qtr_end_week']  = (df['is_qtr_end_month'] &
                               ((df.Date.dt.days_in_month - d) <= 5)).astype(int)

    return df

# ════════════════════════════════════════════════════════════════
# 4. CORE FEATURE ENGINEERING
# ════════════════════════════════════════════════════════════════
def make_features(dates: pd.Series, history: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({'Date': dates})

    # ── calendar ─────────────────────────────────────────────
    df['year']         = df.Date.dt.year
    df['month']        = df.Date.dt.month
    df['day']          = df.Date.dt.day
    df['dayofweek']    = df.Date.dt.dayofweek
    df['dayofyear']    = df.Date.dt.dayofyear
    df['quarter']      = df.Date.dt.quarter
    df['is_weekend']   = (df.dayofweek >= 5).astype(int)
    df['weekofyear']   = df.Date.dt.isocalendar().week.astype(int)
    df['days_in_month']= df.Date.dt.days_in_month
    df['days_to_end']  = df['days_in_month'] - df['day']
    df['is_last_1']    = (df.days_to_end == 0).astype(int)
    df['is_last_3']    = (df.days_to_end <= 2).astype(int)
    df['is_last_7']    = (df.days_to_end <= 6).astype(int)
    df['is_first_3']   = (df.day <= 3).astype(int)
    df['dom_norm']     = (df.day - 1) / 30.0
    df['dte_norm']     = df.days_to_end / 30.0
    df['is_month_start']  = df.Date.dt.is_month_start.astype(int)
    df['days_since_train']= (df.Date - TRAIN_END).dt.days

    # ── Fourier seasonality ───────────────────────────────────
    for k in [1, 2]:
        df[f'sin_week_{k}'] = np.sin(2*np.pi*k*df.dayofweek / 7)
        df[f'cos_week_{k}'] = np.cos(2*np.pi*k*df.dayofweek / 7)
    for k in [1, 2, 3, 4]:
        df[f'sin_year_{k}'] = np.sin(2*np.pi*k*df.dayofyear / 365.25)
        df[f'cos_year_{k}'] = np.cos(2*np.pi*k*df.dayofyear / 365.25)
    for k in [1, 2]:
        df[f'sin_month_{k}'] = np.sin(2*np.pi*k*df.day / df.days_in_month)
        df[f'cos_month_{k}'] = np.cos(2*np.pi*k*df.day / df.days_in_month)

    # ── Lag features ──────────────────────────────────────────
    for lag in [1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 30,
                60, 90, 180, 364, 365, 366]:
        df[f'lag_{lag}'] = (df.Date - pd.Timedelta(days=lag)).map(history).values

    for k in [1, 2, 3, 4, 5]:
        df[f'lag_week_{k}'] = (df.Date - pd.Timedelta(weeks=k)).map(history).values

    # YoY
    for delta in [364, 365, 366]:
        df[f'yoy_{delta}'] = (df.Date - pd.Timedelta(days=delta)).map(history).values
    df['yoy_ratio']  = df['lag_365'] / (df['yoy_366'] + 1e-6)
    df['log_lag365'] = np.log1p(df['lag_365'].clip(lower=0))

    # ── Rolling stats (precomputed from history) ──────────────
    h_sorted = history.sort_index()
    for w in [7, 14, 28, 60]:
        vm, vs, vx = [], [], []
        for d in df.Date:
            win = h_sorted.loc[h_sorted.index < d].tail(w)
            if len(win):
                vm.append(win.mean()); vs.append(win.std()); vx.append(win.max())
            else:
                vm.append(np.nan); vs.append(np.nan); vx.append(np.nan)
        df[f'roll_mean_{w}'] = vm
        df[f'roll_std_{w}']  = vs
        df[f'roll_max_{w}']  = vx

    # ── Interaction: days_to_end × log_lag365 ────────────────
    df['dte_x_log365']   = df['days_to_end'] * df['log_lag365']
    df['last3_x_log365'] = df['is_last_3']   * df['log_lag365']
    df['qtrend_x_365']   = df['is_last_7']   * df['log_lag365']

    # ── Web traffic ───────────────────────────────────────────
    df = df.merge(wt, on='Date', how='left')

    # ── Promotion / Holiday features ─────────────────────────
    promo_df = build_promo_features(df['Date'])
    promo_cols = [c for c in promo_df.columns if c != 'Date']
    df = df.merge(promo_df, on='Date', how='left')

    # ── Fill NaN ──────────────────────────────────────────────
    for col in df.columns:
        if col == 'Date': continue
        if df[col].isna().any():
            med = df[col].median()
            df[col] = df[col].fillna(med if not np.isnan(med) else 0)

    return df

# ════════════════════════════════════════════════════════════════
# 5. BUILD TRAINING FEATURES
# ════════════════════════════════════════════════════════════════
history_train = sales.set_index('Date')['Revenue']

print("Building training features ...")
train_feat = make_features(sales['Date'], history_train)
train_feat['Revenue'] = sales['Revenue'].values
train_feat['log_rev'] = np.log1p(train_feat['Revenue'])

DROP = {'Date', 'Revenue', 'log_rev'}
FEATURE_COLS = [c for c in train_feat.columns if c not in DROP]
print(f"Total features: {len(FEATURE_COLS)}")

# ════════════════════════════════════════════════════════════════
# 6. LGB PARAMS + CV
# ════════════════════════════════════════════════════════════════
LGB_PARAMS = dict(
    objective         = 'regression',   # RMSE — must capture spikes!
    metric            = 'rmse',
    learning_rate     = 0.01,
    num_leaves        = 127,
    max_depth         = -1,
    min_child_samples = 15,
    feature_fraction  = 0.75,
    bagging_fraction  = 0.75,
    bagging_freq      = 5,
    lambda_l1         = 0.05,
    lambda_l2         = 0.05,
    n_estimators      = 8000,
    verbose           = -1,
)

splits = [
    ('2020-12-31', '2021-01-01', '2021-12-31'),
    ('2021-12-31', '2022-01-01', '2022-12-31'),
]
print("\n── CV ──")
best_iters_list = []
for tr_end, va_st, va_en in splits:
    tr = train_feat[train_feat['Date'] <= tr_end]
    va = train_feat[(train_feat['Date'] >= va_st) & (train_feat['Date'] <= va_en)]
    m = lgb.LGBMRegressor(**{**LGB_PARAMS, 'random_state': 42})
    m.fit(tr[FEATURE_COLS], tr['log_rev'],
          eval_set=[(va[FEATURE_COLS], va['log_rev'])],
          callbacks=[lgb.early_stopping(200, verbose=False)])
    pred = np.expm1(m.predict(va[FEATURE_COLS]))
    true = np.expm1(va['log_rev'])
    bi = m.best_iteration_
    best_iters_list.append(bi)
    print(f"  {va_st[:4]}: MAE={mean_absolute_error(true,pred):>12,.0f}  "
          f"R²={r2_score(true,pred):.4f}  iters={bi}")

best_iters = int(np.mean(best_iters_list) * 1.1)
print(f"Best iters: {best_iters}")

# ════════════════════════════════════════════════════════════════
# 7. ENSEMBLE — 5 seeds
# ════════════════════════════════════════════════════════════════
SEEDS = [42, 123, 777, 2024, 31415]
Xfull, yfull = train_feat[FEATURE_COLS], train_feat['log_rev']

print(f"\n── Training {len(SEEDS)} models ──")
models = []
for seed in SEEDS:
    m = lgb.LGBMRegressor(**{**LGB_PARAMS, 'n_estimators': best_iters, 'random_state': seed})
    m.fit(Xfull, yfull)
    models.append(m)
    print(f"  seed={seed} done")

# Feature importance
fi = pd.DataFrame({'feature': FEATURE_COLS,
                   'gain': models[0].booster_.feature_importance('gain')}).sort_values('gain', ascending=False)
print("\nTop 25 features:")
print(fi.head(25).to_string(index=False))

# ════════════════════════════════════════════════════════════════
# 8. RECURSIVE FORECASTING
# ════════════════════════════════════════════════════════════════
print("\n── Recursive forecasting ──")
rolling_history = history_train.copy()
test_dates = sample_sub['Date'].sort_values().tolist()
pred_revenue = []

for i, d in enumerate(test_dates):
    row_feat = make_features(pd.Series([d]), rolling_history)
    for fc in FEATURE_COLS:
        if fc not in row_feat.columns:
            row_feat[fc] = 0.0
    log_preds = np.array([m.predict(row_feat[FEATURE_COLS])[0] for m in models])
    pred_rev  = float(np.expm1(log_preds.mean()))
    rolling_history[d] = pred_rev
    pred_revenue.append(pred_rev)
    if (i+1) % 100 == 0 or i < 3:
        print(f"  {i+1:3d}/{len(test_dates)} | {d.date()} | {pred_rev:>12,.0f}")

# ════════════════════════════════════════════════════════════════
# 9. COGS + SAVE
# ════════════════════════════════════════════════════════════════
sales['cogs_ratio'] = sales['COGS'] / sales['Revenue']
monthly_cogs = sales.set_index('Date')['cogs_ratio'].resample('M').mean()

def cogs_ratio_for(d):
    c = monthly_cogs[monthly_cogs.index.month == d.month]
    return float(c.iloc[-1]) if len(c) else cogs_ratio_global

pred_cogs = [rev * cogs_ratio_for(d) for rev, d in zip(pred_revenue, test_dates)]

submission = sample_sub[['Date']].copy()
submission['Revenue'] = pred_revenue
submission['COGS']    = pred_cogs
submission['Date']    = submission['Date'].dt.strftime('%Y-%m-%d')

out = r'c:\Users\ASUS\DATATHON\submission.csv'
submission.to_csv(out, index=False)

sr, pr = sample_sub['Revenue'].values, np.array(pred_revenue)
print(f"\n=== SAVED: {out} ===")
print(f"Sanity vs sample_submission:")
print(f"  MAE={mean_absolute_error(sr,pr):>14,.2f}  R²={r2_score(sr,pr):.6f}")
print(f"Pred stats: mean={pr.mean():,.0f}  max={pr.max():,.0f}  min={pr.min():,.0f}")
print(submission.head(10).to_string(index=False))
