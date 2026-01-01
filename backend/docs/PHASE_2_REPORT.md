# VeriRisk Phase-2: Predictive Risk Engine - Technical Report

**Project:** VeriRisk - DeFi Protocol Risk Assessment Platform  
**Phase:** 2 - Predictive Risk Engine  
**Status:** ✅ Complete  
**Date:** January 2026  

---

## 📋 Executive Summary

Phase 2 transformed VeriRisk from a **reactive risk scorer** (Phase 1) into a **predictive early-warning system** that forecasts DeFi protocol risk **6-24 hours ahead** using historical time-series data, machine learning, and explainability.

### Key Achievements
- ✅ Forward-looking crash prediction (not reactive)
- ✅ Time-aware ML training (no data leakage)
- ✅ SHAP-based explainability for every prediction
- ✅ Support for both synthetic and real protocol data
- ✅ CLI-based demo system

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     VeriRisk Phase-2 Architecture               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Data Sources │───▶│   Database   │───▶│  Feature Engine  │  │
│  │              │    │   (SQLite)   │    │                  │  │
│  │ • DeFiLlama  │    │              │    │ • 10 Predictive  │  │
│  │ • Synthetic  │    │ • Snapshots  │    │   Features       │  │
│  └──────────────┘    └──────────────┘    └────────┬─────────┘  │
│                                                    │            │
│                                                    ▼            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │   Output     │◀───│ Model Server │◀───│  Model Trainer   │  │
│  │              │    │              │    │                  │  │
│  │ • Risk Score │    │ • XGBoost    │    │ • Forward Labels │  │
│  │ • SHAP       │    │ • SHAP       │    │ • Time-aware     │  │
│  │ • Top 3      │    │ • Inference  │    │   Split          │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Files Created/Modified

### New Files (Phase 2)

| File | Purpose | Lines |
|------|---------|-------|
| `features/advanced_features.py` | Predictive feature engineering | ~415 |
| `fetch_real_protocols.py` | Real protocol data fetching | ~350 |
| `docs/PHASE_2_REPORT.md` | This report | - |

### Modified Files

| File | Changes |
|------|---------|
| `model_trainer.py` | Complete rewrite for predictive training |
| `model_server.py` | Added SHAP explanations, probability-based scoring |
| `data_fetcher.py` | Added predictive synthetic data generation |

### Unchanged Files

| File | Purpose |
|------|---------|
| `database.py` | SQLAlchemy models (Snapshot table) |
| `config.py` | Configuration management |
| `protocols.py` | DeFiLlama API integration |
| `server.py` | FastAPI server (Phase 1) |

---

## 🔧 Component Details

### 1. Predictive Feature Engine (`features/advanced_features.py`)

**Purpose:** Extract early-warning signals from historical time-series data.

**Features Computed (10 total):**

| Feature | Formula | Purpose |
|---------|---------|---------|
| `tvl_change_6h` | `(TVL_t - TVL_{t-6}) / TVL_{t-6}` | Short-term capital flow |
| `tvl_change_24h` | `(TVL_t - TVL_{t-24}) / TVL_{t-24}` | Daily trend |
| `tvl_acceleration` | `tvl_change_6h_t - tvl_change_6h_{t-6}` | Panic detection (2nd derivative) |
| `volume_spike_ratio` | `volume / rolling_avg_24h(volume)` | Unusual activity |
| `reserve_imbalance` | `\|R0 - R1\| / (R0 + R1)` | Liquidity imbalance |
| `reserve_imbalance_rate` | `imbalance_t - imbalance_{t-6}` | Rate of imbalance change |
| `volatility_6h` | `std(returns, window=6)` | Short-term volatility |
| `volatility_24h` | `std(returns, window=24)` | Long-term volatility |
| `volatility_ratio` | `volatility_6h / volatility_24h` | Regime change detector |
| `early_warning_score` | Weighted composite (0-100) | Combined risk signal |

**Key Classes:**
```python
class PredictiveFeatures:
    """Container for computed features"""
    def to_dict() -> Dict
    def get_feature_vector() -> List[float]

class AdvancedFeatureEngine:
    """Feature computation engine"""
    def compute_features_from_df(df, pool_id) -> DataFrame
    def compute_features_for_prediction(history, pool_id) -> PredictiveFeatures
    @staticmethod
    def get_feature_names() -> List[str]
```

---

### 2. Predictive Model Trainer (`model_trainer.py`)

**Purpose:** Train XGBoost classifier to predict future TVL crashes.

**Key Innovations:**

#### Forward-Looking Labels
```python
# label_24h: 1 if TVL drops >20% in next 24 hours
for i in range(n - horizon):
    forward_return = (tvl[i + horizon] - tvl[i]) / tvl[i]
    if forward_return < -0.20:  # 20% drop
        labels[i] = 1
```

#### Time-Aware Split (No Shuffling)
```python
# Train on past, test on future - simulates real prediction
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
# NO SHUFFLING - critical for time-series
```

#### Class Imbalance Handling
```python
scale_pos_weight = n_negative / n_positive  # ~15x for crash events
model = XGBClassifier(scale_pos_weight=scale_pos_weight, ...)
```

**Model Hyperparameters:**
```python
{
    'n_estimators': 300,
    'max_depth': 6,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'eval_metric': 'logloss'
}
```

**Output Files:**
- `models/xgb_veririsk_v2_predictive.pkl` - Trained model
- `models/xgb_veririsk_v2_predictive_metadata.json` - Metrics & config

---

### 3. Model Inference Server (`model_server.py`)

**Purpose:** Generate predictions with SHAP explanations.

**Output Schema:**
```json
{
    "pool_id": "string",
    "risk_score": 0-100,
    "risk_level": "LOW | MEDIUM | HIGH",
    "prediction_horizon": "24h",
    "prediction_type": "predictive",
    "top_reasons": [
        {
            "feature": "tvl_change_24h",
            "impact": 0.0854,
            "direction": "increases_risk",
            "explanation": "24-hour TVL movement is significantly increasing risk"
        }
    ],
    "early_warning_score": 52.34,
    "features_used": {...},
    "model_version": "v2.0_predictive",
    "timestamp": "ISO string"
}
```

**Risk Level Thresholds:**
```python
def get_risk_level(score):
    if score < 30: return 'LOW'
    elif score < 65: return 'MEDIUM'
    else: return 'HIGH'
```

**SHAP Explanation Logic:**
```python
shap_values = TreeExplainer(model).shap_values(features)
# Sort by absolute impact, return top 3
top_features = sorted(impacts, key=lambda x: abs(x['impact']), reverse=True)[:3]
```

---

### 4. Data Generation (`data_fetcher.py`)

**Synthetic Data Generator:**

Uses state machine model for realistic crash patterns:
```
normal → pre_crash → crash → recovery → normal
```

**Risk Profiles:**
| Profile | Base TVL | Crash Probability | Use Case |
|---------|----------|-------------------|----------|
| `safe` | $2M | 5% | Stable protocols |
| `mixed` | $1M | 15% | Average protocols |
| `risky` | $800K | 25% | Volatile protocols |
| `crash_prone` | $500K | 40% | High-risk testing |

---

### 5. Real Protocol Fetcher (`fetch_real_protocols.py`)

**Data Source:** DeFiLlama API (free, no key required)

**Supported Protocols:**
- Uniswap V2 (USDC-ETH, DAI-ETH, USDT-ETH, WBTC-ETH)
- Uniswap V3 (USDC-ETH 0.3%, 0.05%, DAI-USDC 0.01%)
- Aave V3 (ETH, USDC, DAI, WBTC)
- Compound V2 (ETH, USDC, DAI, USDT)
- Curve (3pool, stETH, frax)

**Historical Data Approach:**
1. Fetch real daily TVL from DeFiLlama (goes back years)
2. Interpolate to hourly with realistic noise
3. Generate pool-level data with weighted TVL splits

---

## 📊 Model Performance

### Training Results (Synthetic Data)

```
============================================================
📈 Model Evaluation Results:
============================================================
   ROC-AUC:   0.6316
   Precision: 0.8125
   Recall:    0.5000
   F1-Score:  0.6190

   Confusion Matrix:
                 Predicted
                 No Crash  Crash
   Actual No Crash    807      3
   Actual Crash        13     13
```

### Feature Importance

```
1. reserve_imbalance         0.3099 ███████████████
2. volatility_24h            0.1256 ██████
3. volume_spike_ratio        0.0891 ████
4. tvl_change_24h            0.0811 ████
5. tvl_change_6h             0.0783 ███
6. tvl_acceleration          0.0751 ███
7. volatility_6h             0.0729 ███
8. early_warning_score       0.0632 ███
9. reserve_imbalance_rate    0.0564 ██
10. volatility_ratio         0.0485 ██
```

### Sample Predictions

```
Risk Rankings (Highest to Lowest)
============================================================
  🔴  98.2%  high_risk_pool
  🟡  37.2%  test_pool_2
  🟢   2.6%  test_pool_1
  🟢   0.3%  curve_3pool
  🟢   0.2%  uniswap_v2_usdc_eth
  🟢   0.1%  aave_v3_eth
```

---

## 🖥️ CLI Commands Reference

### Data Generation

```bash
# Generate synthetic predictive data
python data_fetcher.py --predictive

# Fetch REAL historical data from DeFiLlama
python fetch_real_protocols.py --fetch-history --days 30
```

### Model Training

```bash
# Train predictive model
python model_trainer.py
```

### Inference

```bash
# Single pool prediction
python model_server.py --run-once --pool <pool_id>

# All pools ranking
python model_server.py --all

# JSON output
python model_server.py --run-once --pool <pool_id> --json
```

### Utilities

```bash
# Check database status
python fetch_real_protocols.py --status

# Fetch current real data (single snapshot)
python fetch_real_protocols.py --fetch
```

---

## 🔌 API Contracts (for Phase 3)

### Internal Functions

#### Feature Engine
```python
from features.advanced_features import AdvancedFeatureEngine

engine = AdvancedFeatureEngine()

# For training (batch)
df_features = engine.compute_features_from_df(df, pool_id)

# For inference (single prediction)
features = engine.compute_features_for_prediction(history_list, pool_id)
feature_vector = features.get_feature_vector()  # List[float]
feature_dict = features.to_dict()  # Dict
```

#### Model Server
```python
from model_server import PredictiveModelServer

server = PredictiveModelServer()

# Single prediction
result = server.predict_risk(pool_id)  # Returns dict

# All pools
results = server.predict_all_pools()  # Returns List[dict]
```

### Database Schema

```python
class Snapshot(Base):
    __tablename__ = "snapshots"
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String, unique=True)
    pool_id = Column(String, index=True)
    timestamp = Column(DateTime, index=True)
    tvl = Column(Float)
    reserve0 = Column(Float)
    reserve1 = Column(Float)
    volume_24h = Column(Float)
    oracle_price = Column(Float)
    features = Column(JSON)
    source = Column(String)
```

---

## ⚠️ Known Limitations

1. **Hourly Data Interpolation:** Real historical data is daily; hourly is interpolated
2. **Pool-Level Estimates:** Individual pool TVL is estimated from protocol TVL
3. **Volume Data:** DeFiLlama doesn't provide historical volume; estimated as % of TVL
4. **Model Generalization:** Trained on synthetic crash patterns; may need retraining on real crashes
5. **XGBoost Warning:** Model saves in deprecated binary format (non-breaking)

---

## 🚀 Recommendations for Phase 3

### 1. API Integration
- Expose prediction endpoints via FastAPI
- Add batch prediction endpoint
- Implement caching for frequent requests

### 2. Alerting System
```python
# Suggested endpoint
POST /api/alerts/configure
{
    "pool_id": "aave_v3_eth",
    "threshold": 65,  # risk score
    "webhook_url": "https://...",
    "notification_type": "email|webhook|both"
}
```

### 3. Scheduled Predictions
- Use APScheduler (already in codebase)
- Run predictions every hour
- Store historical predictions for trend analysis

### 4. Model Retraining Pipeline
- Detect model drift
- Automated retraining when performance degrades
- A/B testing between model versions

### 5. Dashboard Integration
- Real-time risk heatmap
- Historical risk trends
- SHAP visualization

---

## 📝 Testing Checklist

- [x] Forward-looking labels created correctly
- [x] No data leakage in train/test split
- [x] Different pools produce different scores
- [x] SHAP explanations present and meaningful
- [x] Model saves and loads correctly
- [x] CLI commands work as expected
- [x] Real protocol data fetching works
- [x] Synthetic data generation works

---

## 📚 Files Quick Reference

```
backend/
├── model_trainer.py          # Training pipeline
├── model_server.py           # Inference with SHAP
├── data_fetcher.py           # Synthetic data generation
├── fetch_real_protocols.py   # Real protocol data
├── features/
│   ├── __init__.py
│   ├── advanced_features.py  # Predictive features
│   └── basic_timeseries.py   # Phase 1 features
├── models/
│   ├── xgb_veririsk_v2_predictive.pkl
│   └── xgb_veririsk_v2_predictive_metadata.json
├── database.py               # SQLAlchemy models
├── protocols.py              # DeFiLlama integration
└── docs/
    └── PHASE_2_REPORT.md     # This report
```

---

## 🎯 Phase 2 Success Criteria - Final Status

| Criterion | Status | Notes |
|-----------|--------|-------|
| Forward-looking labels | ✅ | t+6h and t+24h implemented |
| Predictive features | ✅ | 10 features computed |
| Time-aware training | ✅ | No shuffling, chronological split |
| SHAP explainability | ✅ | Top 3 features per prediction |
| CLI demo | ✅ | All commands working |
| No data leakage | ✅ | Verified in design |
| Different scores per pool | ✅ | Range: 0.1% - 98.2% |

---

**Report Generated:** Phase 2 Complete  
**Next Phase:** Phase 3 (API Integration, Alerting, Dashboard)
