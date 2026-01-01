# VeriRisk Phase 3: Risk Evaluation, Alerts & Explainability - Technical Report

**Project:** VeriRisk - DeFi Protocol Risk Assessment Platform  
**Phase:** 3 - Risk Evaluation, Alerts & Explainability  
**Status:** ✅ Complete  
**Date:** January 2026  
**Test Verification:** January 1, 2026

---

## 📋 Executive Summary

Phase 3 transformed VeriRisk into a **fully automated, explainable, alert-driven DeFi risk monitoring system**. All required features have been implemented and tested:

### Key Achievements
- ✅ **Risk History Tracking** - Persists risk predictions over time for trend analysis
- ✅ **Alert Engine** - Automatically generates alerts when thresholds are crossed
- ✅ **Explainable AI** - SHAP-based explanations for every prediction and alert
- ✅ **Automated Pipeline** - End-to-end automation via scheduler (10-minute intervals)
- ✅ **Clean API Layer** - RESTful endpoints for demonstration and evaluation
- ✅ **Demo Ready** - System runs autonomously with comprehensive logging

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     VeriRisk Phase 3 Architecture                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │ Data Sources │───▶│   Database   │───▶│    Feature Engine         │   │
│  │              │    │   (SQLite)   │    │                           │   │
│  │ • DeFiLlama  │    │              │    │ • 10 Predictive Features  │   │
│  │ • Synthetic  │    │ • Snapshots  │    │ • Time-series Analysis    │   │
│  └──────────────┘    │ • risk_history│   └───────────┬───────────────┘   │
│                      │ • alerts      │                │                  │
│                      └──────────────┘                ▼                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     Risk Evaluator Service                        │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐   │   │
│  │  │   Model     │  │    SHAP      │  │    Alert Engine        │   │   │
│  │  │   Server    │─▶│  Explainer   │─▶│                        │   │   │
│  │  │             │  │              │  │ • HIGH_RISK_ALERT      │   │   │
│  │  │ • XGBoost   │  │ • Top 3      │  │ • EARLY_WARNING_ALERT  │   │   │
│  │  │ • Predict   │  │   Features   │  │ • RISK_ESCALATION      │   │   │
│  │  └─────────────┘  └──────────────┘  └───────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      API Layer (FastAPI)                          │   │
│  │  GET /api/risk/latest/{pool_id}   │  GET /api/risk/summary       │   │
│  │  GET /api/risk/history/{pool_id}  │  POST /api/risk/predict/*    │   │
│  │  GET /api/risk/alerts             │                               │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      Scheduler (APScheduler)                      │   │
│  │  • fetch_data: every 10 minutes                                   │   │
│  │  • predict_risks: every 10 minutes                                │   │
│  │  • evaluate_alerts: every 10 minutes                              │   │
│  │  • full_cycle: every 30 minutes                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Files Created/Modified for Phase 3

### New Files (Phase 3)

| File | Purpose | Lines |
|------|---------|-------|
| `db_models/risk_history.py` | RiskHistory SQLAlchemy model | ~99 |
| `db_models/alert.py` | Alert SQLAlchemy model with AlertType enum | ~140 |
| `services/risk_evaluator.py` | Risk prediction, storage, and alert generation | ~468 |
| `routers/risk.py` | Phase 3 API endpoints | ~353 |
| `docs/PHASE_3_REPORT.md` | This report | - |

### Modified Files

| File | Changes |
|------|---------|
| `scheduler.py` | Added predict_and_store_risks(), evaluate_alerts() jobs |
| `api_server.py` | Integrated risk_router |
| `routers/__init__.py` | Added risk_router export |

---

## 🔧 Component Details

### 1. Risk History Tracking (`db_models/risk_history.py`)

**Purpose:** Persist risk predictions over time for trend analysis and escalation detection.

**Database Schema:**
```python
class RiskHistory(Base):
    __tablename__ = "risk_history"
    
    id = Column(Integer, primary_key=True)
    pool_id = Column(String(100), index=True)        # Protocol identifier
    risk_score = Column(Float)                        # 0-100 probability
    risk_level = Column(String(20))                   # LOW, MEDIUM, HIGH
    early_warning_score = Column(Float)               # 0-100 composite score
    top_reasons = Column(JSON)                        # SHAP explanations
    model_version = Column(String(50))                # e.g., "v2.0_predictive"
    prediction_horizon = Column(String(20))           # e.g., "24h"
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_risk_history_pool_time', 'pool_id', 'timestamp'),
    )
```

**Key Methods:**
```python
def to_dict() -> Dict    # Convert to API response format
init_risk_history_db()   # Initialize table
```

---

### 2. Alert Engine (`db_models/alert.py` + `services/risk_evaluator.py`)

**Purpose:** Automatically generate alerts when risk thresholds are crossed.

**Alert Types:**
| Type | Condition | Threshold |
|------|-----------|-----------|
| `HIGH_RISK_ALERT` | risk_score >= 65 | 65% |
| `EARLY_WARNING_ALERT` | early_warning_score >= 40 | 40 |
| `RISK_ESCALATION_ALERT` | Risk level increases | LOW→MEDIUM, MEDIUM→HIGH, LOW→HIGH |

**Database Schema:**
```python
class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True)
    pool_id = Column(String(100), index=True)
    alert_type = Column(String(50), index=True)       # AlertType enum value
    risk_score = Column(Float)
    risk_level = Column(String(20))
    message = Column(String(500))                     # Human-readable message
    top_reasons = Column(JSON)                        # SHAP explanations
    status = Column(String(20), default='active')     # active, acknowledged, resolved
    previous_risk_level = Column(String(20))          # For escalation alerts
    previous_risk_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Duplicate Prevention:**
- Alerts are only generated if the same type doesn't exist within 1 hour
- Method: `has_recent_alert(pool_id, alert_type, hours=1)`

---

### 3. Explainable Risk Reports (`model_server.py` + `services/risk_evaluator.py`)

**Purpose:** Attach SHAP-based explanations to every risk prediction.

**Output Format:**
```json
{
    "risk_score": 99.74,
    "risk_level": "HIGH",
    "early_warning_score": 63.07,
    "top_reasons": [
        {
            "feature": "reserve_imbalance",
            "impact": 3.1809,
            "direction": "increases_risk",
            "explanation": "Liquidity imbalance is significantly increasing manipulation risk"
        },
        {
            "feature": "volume_spike_ratio",
            "impact": 0.8625,
            "direction": "increases_risk",
            "explanation": "Trading volume relative to average is significantly increasing risk"
        },
        {
            "feature": "volatility_ratio",
            "impact": 0.7751,
            "direction": "increases_risk",
            "explanation": "Volatility regime indicator is significantly increasing risk"
        }
    ]
}
```

**Features Analyzed:**
| Feature | Purpose |
|---------|---------|
| `tvl_change_6h` | Short-term capital flow |
| `tvl_change_24h` | Daily trend |
| `tvl_acceleration` | Panic detection (2nd derivative) |
| `volume_spike_ratio` | Unusual trading activity |
| `reserve_imbalance` | Liquidity imbalance |
| `reserve_imbalance_rate` | Rate of imbalance change |
| `volatility_6h` | Short-term volatility |
| `volatility_24h` | Long-term volatility |
| `volatility_ratio` | Regime change detector |
| `early_warning_score` | Composite risk signal |

---

### 4. Automated Pipeline (`scheduler.py`)

**Purpose:** End-to-end automation without manual triggers.

**Scheduled Jobs:**
| Job | Interval | Purpose |
|-----|----------|---------|
| `fetch_all_protocols_data` | 10 minutes | Fetch latest protocol snapshots |
| `predict_and_store_risks` | 10 minutes | Run model inference, store in risk_history |
| `evaluate_alerts` | 10 minutes | Check thresholds, generate alerts |
| `compute_and_submit_risks` | 15 minutes | Submit high-risk to blockchain |
| `full_update_cycle` | 30 minutes | Complete pipeline run |
| `collect_hourly_snapshots` | Hourly (at :00) | Time-series data collection |
| `compute_timeseries_features` | Hourly (at :05) | Feature computation |

**Locking Mechanism:**
```python
self.risk_lock = Lock()  # Prevents overlapping risk prediction runs

def predict_and_store_risks(self):
    if not self.risk_lock.acquire(blocking=False):
        logger.info("⏭️ Risk prediction already running, skipping")
        return []
    try:
        # ... prediction logic
    finally:
        self.risk_lock.release()
```

---

### 5. API Layer (`routers/risk.py`)

**Purpose:** Clean, minimal APIs for demonstration and evaluation.

**Endpoints:**

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/risk/latest/{pool_id}` | Latest risk score, level, explanations |
| GET | `/api/risk/history/{pool_id}` | Chronological risk evolution |
| GET | `/api/risk/alerts` | Active alerts across all protocols |
| GET | `/api/risk/summary` | Risk summary across all pools |
| POST | `/api/risk/predict/{pool_id}` | Trigger prediction for single pool |
| POST | `/api/risk/predict-all` | Trigger prediction for all pools |

**Response Examples:**

**GET /api/risk/latest/high_risk_pool:**
```json
{
    "pool_id": "high_risk_pool",
    "risk_score": 99.74,
    "risk_level": "HIGH",
    "early_warning_score": 63.07,
    "top_reasons": [...],
    "model_version": "v2.0_predictive",
    "prediction_horizon": "24h",
    "timestamp": "2026-01-01T10:46:04.652846"
}
```

**GET /api/risk/summary:**
```json
{
    "total_pools": 10,
    "high_risk_pools": 2,
    "medium_risk_pools": 0,
    "low_risk_pools": 8,
    "total_active_alerts": 12,
    "pools": [...],
    "timestamp": "2026-01-01T10:46:12.202887"
}
```

**GET /api/risk/alerts:**
```json
{
    "alerts": [
        {
            "id": 3,
            "pool_id": "high_risk_pool",
            "alert_type": "HIGH_RISK_ALERT",
            "risk_score": 99.74,
            "risk_level": "HIGH",
            "message": "High risk detected for high_risk_pool. Score: 99.7%. Top factor: reserve_imbalance",
            "top_reasons": [...],
            "status": "active",
            "created_at": "2026-01-01T10:46:04.832566"
        },
        ...
    ],
    "count": 12
}
```

---

## 📊 Test Results

### Test Execution Summary

| Test | Status | Details |
|------|--------|---------|
| Backend Startup | ✅ | Scheduler started with all Phase 3 jobs |
| Data Generation | ✅ | 10 pools × 720 samples (30 days hourly) |
| Risk Prediction | ✅ | 10 pools predicted, diverse scores |
| Alert Generation | ✅ | 12 alerts generated (2 HIGH_RISK, 10 EARLY_WARNING) |
| Duplicate Prevention | ✅ | Second prediction cycle: 0 new alerts |
| API Endpoints | ✅ | All 6 endpoints tested and working |
| SHAP Explanations | ✅ | Top 3 features with impact/direction |
| Database Persistence | ✅ | 21 risk_history records, 12 alerts |

### Risk Score Distribution

| Pool | Risk Score | Risk Level | Active Alerts |
|------|------------|------------|---------------|
| high_risk_pool | 99.74% | HIGH | 2 |
| critical_risk_pool | 94.79% | HIGH | 2 |
| late_crash_pool_1 | 6.46% | LOW | 1 |
| synthetic_pool_2 | 1.33% | LOW | 1 |
| synthetic_curve | 0.35% | LOW | 1 |
| late_crash_pool_2 | 0.34% | LOW | 1 |
| synthetic_pool_1 | 0.20% | LOW | 1 |
| synthetic_uniswap_v2 | 0.16% | LOW | 1 |
| late_crash_pool_3 | 0.15% | LOW | 1 |
| synthetic_aave_v3 | 0.13% | LOW | 1 |

### Logs Verification

```log
2026-01-01 10:45:28,688 - scheduler - INFO - 🚀 VeriRisk Scheduler starting (Phase 3)
2026-01-01 10:45:28,691 - scheduler - INFO - ✅ Scheduler started
2026-01-01 10:46:04,808 - services.risk_evaluator - INFO - ✅ Stored 10 risk predictions
2026-01-01 10:46:04,822 - services.risk_evaluator - WARNING - 🚨 ALERT [HIGH_RISK_ALERT] critical_risk_pool: High risk detected for critical_risk_pool. Score: 94.8%.
2026-01-01 10:46:04,840 - services.risk_evaluator - WARNING - 🚨 ALERT [HIGH_RISK_ALERT] high_risk_pool: High risk detected for high_risk_pool. Score: 99.7%.
2026-01-01 10:46:04,928 - services.risk_evaluator - WARNING - 🚨 Generated 12 new alerts
2026-01-01 10:46:35,753 - services.risk_evaluator - INFO - ✅ No new alerts generated  # Duplicate prevention working
```

---

## 🖥️ Demo Guide

### Starting the System

```bash
# 1. Start backend server
sudo supervisorctl restart backend

# 2. Generate test data (optional - for fresh start)
cd /app/backend
python data_fetcher.py --predictive

# 3. Trigger initial predictions
curl -X POST http://localhost:8001/api/risk/predict-all
```

### Demo Flow

1. **Show Snapshot Ingestion:**
   ```bash
   curl http://localhost:8001/health | python3 -m json.tool
   ```
   Shows data_status with snapshot counts.

2. **Show Model Prediction:**
   ```bash
   curl http://localhost:8001/api/risk/latest/high_risk_pool | python3 -m json.tool
   ```
   Displays risk_score, risk_level, prediction_horizon.

3. **Show SHAP Explanation:**
   Same as above - top_reasons array shows feature impacts.

4. **Show Alert Generation:**
   ```bash
   curl "http://localhost:8001/api/risk/alerts?status=active" | python3 -m json.tool
   ```
   Lists all active alerts with types and explanations.

5. **Show Risk Summary:**
   ```bash
   curl http://localhost:8001/api/risk/summary | python3 -m json.tool
   ```
   Overview of all pools with risk distribution.

6. **Show Risk History:**
   ```bash
   curl "http://localhost:8001/api/risk/history/high_risk_pool?hours=24" | python3 -m json.tool
   ```
   Chronological risk evolution.

---

## 🎯 Phase 3 Success Criteria - Final Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Different protocols produce different risk scores | ✅ | Range: 0.13% - 99.74% |
| Risk history shows evolution over time | ✅ | 21 records across 10 pools |
| Alerts trigger only when conditions are met | ✅ | HIGH_RISK >= 65, EARLY_WARNING >= 40 |
| Every alert has explainable reasons | ✅ | top_reasons with SHAP values |
| System runs autonomously | ✅ | Scheduler with 10-minute intervals |
| No duplicate alerts | ✅ | Second cycle: 0 new alerts |
| Clean API for demo | ✅ | 6 endpoints, JSON responses |
| Comprehensive logging | ✅ | Risk scores, alerts, scheduler cycles |

---

## 📚 Quick Reference

### API Endpoints

```bash
# Get latest risk for a pool
GET /api/risk/latest/{pool_id}

# Get risk history for a pool
GET /api/risk/history/{pool_id}?hours=24

# Get all active alerts
GET /api/risk/alerts?status=active

# Get risk summary
GET /api/risk/summary

# Trigger prediction for one pool
POST /api/risk/predict/{pool_id}

# Trigger prediction for all pools
POST /api/risk/predict-all
```

### Database Tables

```
snapshots         - Raw protocol data
snapshot_history  - Time-series snapshots
risk_history      - Risk predictions over time
alerts            - Generated alerts
```

### Scheduler Jobs

```
fetch_data           - 10 min interval
predict_risks        - 10 min interval
evaluate_alerts      - 10 min interval
submit_risks         - 15 min interval
full_cycle           - 30 min interval
hourly_snapshot      - Every hour (:00)
timeseries_features  - Every hour (:05)
```

---

## 🚀 Recommendations for Phase 4

### 1. Frontend Dashboard
- Real-time risk heatmap
- SHAP waterfall visualizations
- Alert management UI
- Historical trend charts

### 2. Notification System
- Email alerts for HIGH_RISK
- Webhook integrations
- Slack/Discord notifications

### 3. Multi-Horizon Predictions
- 6h, 12h, 24h, 48h forecasts
- Ensemble model support
- Model comparison views

### 4. Enhanced Explainability
- Natural language explanations
- Feature interaction analysis
- Counterfactual explanations

### 5. Performance Optimization
- Batch prediction caching
- Database query optimization
- Async alert processing

---

## 📝 Testing Commands

```bash
# Health check
curl http://localhost:8001/health | python3 -m json.tool

# Trigger all predictions
curl -X POST http://localhost:8001/api/risk/predict-all | python3 -m json.tool

# Get risk summary
curl http://localhost:8001/api/risk/summary | python3 -m json.tool

# Get latest risk
curl http://localhost:8001/api/risk/latest/high_risk_pool | python3 -m json.tool

# Get risk history
curl "http://localhost:8001/api/risk/history/high_risk_pool?hours=24" | python3 -m json.tool

# Get active alerts
curl "http://localhost:8001/api/risk/alerts?status=active" | python3 -m json.tool

# Check logs
tail -f /var/log/supervisor/backend.err.log | grep -E "(🚨|✅|📊)"
```

---

**Report Generated:** Phase 3 Complete  
**Test Date:** January 1, 2026  
**Next Phase:** Phase 4 (Frontend Dashboard, Notifications, Multi-Horizon)
