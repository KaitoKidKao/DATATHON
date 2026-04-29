"""
VinUni Datathon 2026 - Sales Forecasting Pipeline
Full LightGBM training + submission generation
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

# ─── 1. Load Data ──────────────────────────────────────────────────
base = r'c:\Users\ASUS\DATATHON\datathon-2026-round-1'

sales = pd.read_csv(f'{base}/sales.csv', parse_dates=['Date'])
web_traffic = pd.read_csv(f'{base}/web_traffic.csv', parse_dates=['date'])
sample_sub = pd.read_csv(f'{base}/sample_submission.csv', parse_dates=['Date'])

print(f"Sales train: {sales.shape} | {sales['Date'].min()} ~ {sales['Date'].max()}")
print(f"Test period: {sample_sub['Date'].min()} ~ {sample_sub['Date'].max()}")

# ─── 2. Aggregate web traffic (multiple rows per day) ──────────────
wt_agg = web_traffic.groupby('date').agg(
    sessions=('sessions', 'sum'),
    page_views=('page_views', 'sum'),
    unique_visitors=('unique_visitors', 'sum'),
    bounce_rate=('bounce_rate', 'mean'),
    avg_session_dur=('avg_session_duration_sec', 'mean')
).reset_index()
wt_agg.rename(columns={'date': 'Date'}, inplace=True)

# ─── 3. Build feature dataframe ────────────────────────────────────
df = sales.copy().sort_values('Date').reset_index(drop=True)
df = df.merge(wt_agg, on='Date', how='left')

# Time features
df['year']      = df['Date'].dt.year
df['month']     = df['Date'].dt.month
df['day']       = df['Date'].dt.day
df['dayofweek'] = df['Date'].dt.dayofweek
df['dayofyear'] = df['Date'].dt.dayofyear
df['quarter']   = df['Date'].dt.quarter
df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)
df['week_of_year'] = df['Date'].dt.isocalendar().week.astype(int)

# Month-end / Month-start indicators
df['is_month_start'] = df['Date'].dt.is_month_start.astype(int)
df['is_month_end']   = df['Date'].dt.is_month_end.astype(int)

# Holiday season flag (Q4: Black Friday, Christmas, Tet is Jan-Feb)
df['is_holiday_season'] = ((df['month'] >= 10) | (df['month'] <= 2)).astype(int)

# Lag features (strictly shifted to avoid leakage)
for lag in [1, 7, 14, 21, 30, 60, 90, 365]:
    df[f'rev_lag_{lag}'] = df['Revenue'].shift(lag)

# Rolling statistics (start from lag=1 to avoid leakage)
for window in [7, 14, 30]:
    df[f'rev_roll_mean_{window}'] = df['Revenue'].shift(1).rolling(window).mean()
    df[f'rev_roll_std_{window}']  = df['Revenue'].shift(1).rolling(window).std()
    df[f'rev_roll_max_{window}']  = df['Revenue'].shift(1).rolling(window).max()
    df[f'rev_roll_min_{window}']  = df['Revenue'].shift(1).rolling(window).min()

# COGS ratio (historical) as exogenous feature
df['cogs_ratio'] = df['COGS'] / df['Revenue'].replace(0, np.nan)
for lag in [1, 7, 30]:
    df[f'cogs_ratio_lag_{lag}'] = df['cogs_ratio'].shift(lag)

# Backfill remaining NaNs
df = df.bfill()

# ─── 4. Define features ────────────────────────────────────────────
FEATURES = [
    'year', 'month', 'day', 'dayofweek', 'dayofyear', 'quarter',
    'is_weekend', 'week_of_year', 'is_month_start', 'is_month_end', 'is_holiday_season',
    'sessions', 'page_views', 'unique_visitors', 'bounce_rate', 'avg_session_dur',
    'rev_lag_1', 'rev_lag_7', 'rev_lag_14', 'rev_lag_21', 'rev_lag_30',
    'rev_lag_60', 'rev_lag_90', 'rev_lag_365',
    'rev_roll_mean_7', 'rev_roll_mean_14', 'rev_roll_mean_30',
    'rev_roll_std_7', 'rev_roll_std_14', 'rev_roll_std_30',
    'rev_roll_max_7', 'rev_roll_min_7',
    'cogs_ratio_lag_1', 'cogs_ratio_lag_7', 'cogs_ratio_lag_30',
]
TARGET = 'Revenue'

# ─── 5. Train / Validation split (time-based) ─────────────────────
TRAIN_END = '2021-12-31'
VAL_START = '2022-01-01'

train_df = df[df['Date'] <= TRAIN_END]
val_df   = df[df['Date'] >= VAL_START]

X_train, y_train = train_df[FEATURES], train_df[TARGET]
X_val,   y_val   = val_df[FEATURES],   val_df[TARGET]

# Log-transform to stabilize variance
y_train_log = np.log1p(y_train)
y_val_log   = np.log1p(y_val)

print(f"\nTrain: {len(X_train)} | Val: {len(X_val)}")

# ─── 6. Train LightGBM ─────────────────────────────────────────────
params = {
    'objective': 'regression',
    'metric': 'rmse',
    'learning_rate': 0.02,
    'max_depth': 7,
    'num_leaves': 63,
    'min_data_in_leaf': 20,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'lambda_l1': 0.1,
    'lambda_l2': 0.1,
    'n_estimators': 2000,
    'random_state': 42,
    'verbose': -1,
}

model = lgb.LGBMRegressor(**params)
model.fit(
    X_train, y_train_log,
    eval_set=[(X_val, y_val_log)],
    callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(200)]
)

# Validation metrics
y_pred_log = model.predict(X_val)
y_pred     = np.expm1(y_pred_log)

mae  = mean_absolute_error(y_val, y_pred)
rmse = np.sqrt(mean_squared_error(y_val, y_pred))
r2   = r2_score(y_val, y_pred)

print('\n=== VALIDATION METRICS ===')
print(f'MAE:  {mae:,.2f}')
print(f'RMSE: {rmse:,.2f}')
print(f'R2:   {r2:.6f}')

# ─── 7. Retrain on ALL data ────────────────────────────────────────
print('\nRetraining final model on ALL training data...')
X_full    = df[FEATURES]
y_full_log = np.log1p(df[TARGET])

final_model = lgb.LGBMRegressor(**{**params, 'n_estimators': model.best_iteration_ + 50})
final_model.fit(X_full, y_full_log)

# Feature importance
feat_imp = pd.DataFrame({
    'feature': FEATURES,
    'importance': final_model.feature_importances_
}).sort_values('importance', ascending=False)
print('\n=== TOP 15 FEATURE IMPORTANCES ===')
print(feat_imp.head(15).to_string(index=False))

# ─── 8. Build test features ────────────────────────────────────────
test_df = sample_sub[['Date']].copy()
test_df = test_df.merge(wt_agg, on='Date', how='left')

# For missing web traffic in test, use trailing mean
for col in ['sessions', 'page_views', 'unique_visitors', 'bounce_rate', 'avg_session_dur']:
    test_df[col] = test_df[col].fillna(wt_agg[col].tail(90).mean())

test_df['year']      = test_df['Date'].dt.year
test_df['month']     = test_df['Date'].dt.month
test_df['day']       = test_df['Date'].dt.day
test_df['dayofweek'] = test_df['Date'].dt.dayofweek
test_df['dayofyear'] = test_df['Date'].dt.dayofyear
test_df['quarter']   = test_df['Date'].dt.quarter
test_df['is_weekend'] = (test_df['dayofweek'] >= 5).astype(int)
test_df['week_of_year'] = test_df['Date'].dt.isocalendar().week.astype(int)
test_df['is_month_start'] = test_df['Date'].dt.is_month_start.astype(int)
test_df['is_month_end']   = test_df['Date'].dt.is_month_end.astype(int)
test_df['is_holiday_season'] = ((test_df['month'] >= 10) | (test_df['month'] <= 2)).astype(int)

# For lag/rolling: extend df with test rows so we can compute lags
# We use the last known values from training
all_rev = df.set_index('Date')['Revenue']
mean_rev = all_rev.tail(90).mean()
cogs_ratio_mean = (df['COGS'] / df['Revenue'].replace(0, np.nan)).tail(90).mean()

for lag in [1, 7, 14, 21, 30, 60, 90, 365]:
    # Try to get real lag from training data if available
    test_df[f'rev_lag_{lag}'] = test_df['Date'].apply(
        lambda d: all_rev.get(d - pd.Timedelta(days=lag), mean_rev)
    )

for window in [7, 14, 30]:
    # rolling: use trailing window from training
    test_df[f'rev_roll_mean_{window}'] = test_df['Date'].apply(
        lambda d: all_rev[all_rev.index < d].tail(window).mean() if len(all_rev[all_rev.index < d]) > 0 else mean_rev
    )
    test_df[f'rev_roll_std_{window}'] = test_df['Date'].apply(
        lambda d: all_rev[all_rev.index < d].tail(window).std() if len(all_rev[all_rev.index < d]) > 0 else 0
    )
    test_df[f'rev_roll_max_{window}'] = test_df['Date'].apply(
        lambda d: all_rev[all_rev.index < d].tail(window).max() if len(all_rev[all_rev.index < d]) > 0 else mean_rev
    )
    test_df[f'rev_roll_min_{window}'] = test_df['Date'].apply(
        lambda d: all_rev[all_rev.index < d].tail(window).min() if len(all_rev[all_rev.index < d]) > 0 else mean_rev
    )

for lag in [1, 7, 30]:
    test_df[f'cogs_ratio_lag_{lag}'] = cogs_ratio_mean

# ─── 9. Predict & submission ───────────────────────────────────────
preds_log = final_model.predict(test_df[FEATURES])
test_df['Revenue_pred'] = np.expm1(preds_log)

# COGS: use trailing mean COGS/Revenue ratio
cogs_margin = df['COGS'].sum() / df['Revenue'].sum()
test_df['COGS_pred'] = test_df['Revenue_pred'] * cogs_margin

# Finalize submission
submission = sample_sub.copy()
submission['Revenue'] = test_df['Revenue_pred'].values
submission['COGS']    = test_df['COGS_pred'].values
submission['Date']    = pd.to_datetime(submission['Date']).dt.strftime('%Y-%m-%d')

submission.to_csv(r'c:\Users\ASUS\DATATHON\submission.csv', index=False)
print('\n=== SUBMISSION GENERATED ===')
print(submission.head(10).to_string(index=False))
print(f'\nTotal rows: {len(submission)}')
print('Saved: c:/Users/ASUS/DATATHON/submission.csv')
