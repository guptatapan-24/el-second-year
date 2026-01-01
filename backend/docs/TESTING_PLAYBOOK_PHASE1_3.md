# VeriRisk Backend Testing Playbook (Phases 1 → 3)

This file contains **copy/paste commands** to test the backend MVP end-to-end using:
- **Synthetic generated data** (fast, deterministic-ish)
- **Real-protocol data** (DeFiLlama historical + simulated-from-real)

You selected:
- Location: `backend/docs/TESTING_PLAYBOOK_PHASE1_3.md`
- Commands style: **local container** using `http://localhost:8001`
- Real protocol mode: **both** DeFiLlama historical **and** simulated-from-real

---

## 0) Quick mental model (tables + pipelines)

### Phase 1 (Historical time-series foundation)
- Table: `snapshot_history` (SQLAlchemy model: `backend/db_models/snapshot_history.py`)
- Job: `backend/jobs/hourly_snapshot.py` (hour-rounded inserts)
- API: `backend/routers/timeseries.py` (prefixed at runtime as `/api/timeseries/...`)

### Phase 2 (Predictive ML + SHAP)
- Table: `snapshots` (SQLAlchemy model: `backend/database.py::Snapshot`)
- Synthetic generator (30 days hourly): `python data_fetcher.py --predictive`
- Trainer: `python model_trainer.py` (writes model artifacts to `models/`)
- Inference: `python model_server.py --run-once --pool <pool_id>`
- Real protocol 30-day history: `python fetch_real_protocols.py --fetch-history --days 30`

### Phase 3 (Risk history + alerts + automation)
- Table: `risk_history` (model: `backend/db_models/risk_history.py`)
- Table: `alerts` (model: `backend/db_models/alert.py`)
- Service: `backend/services/risk_evaluator.py` (predict → store → evaluate alerts)
- API: `backend/routers/risk.py` (prefixed at runtime as `/api/risk/...`)

---

## 1) Start/Restart backend (Supervisor)

> Use supervisor (do not run uvicorn manually).

```bash
sudo supervisorctl status
sudo supervisorctl restart backend

# If something fails to start:
tail -n 200 /var/log/supervisor/backend.err.log
tail -n 200 /var/log/supervisor/backend.out.log
```

### (Optional) Check server is responding

Note: some endpoints are not `/api`-prefixed (e.g., `/health`). For local testing this is fine.

```bash
curl -sS http://localhost:8001/health | python -m json.tool
```

---

## 2) (Optional but recommended) Reset database for a clean run

This project uses SQLite via `DATABASE_URL` (default: `sqlite:///./veririsk.db`).

⚠ **This deletes local dev data.** Do this only if you want a clean test.

```bash
# Stop backend so the sqlite file is not locked
sudo supervisorctl stop backend

# Delete sqlite DB (default location)
rm -f /app/backend/veririsk.db

# Start backend again
sudo supervisorctl start backend

# Verify
curl -sS http://localhost:8001/health | python -m json.tool
```

---

## 3) Phase 1 tests — time-series snapshots + feature derivation

### 3.1 Seed synthetic historical snapshots into `snapshot_history`

This seeds **Phase-1 hourly history** (NOT the ML table).

```bash
# Seed 72 hours (good for quick testing)
curl -sS -X POST "http://localhost:8001/api/timeseries/seed?hours=72" | python -m json.tool

# Or seed 168 hours (7 days)
curl -sS -X POST "http://localhost:8001/api/timeseries/seed?hours=168" | python -m json.tool
```

### 3.2 Check time-series system status

```bash
curl -sS http://localhost:8001/api/timeseries/status | python -m json.tool
curl -sS http://localhost:8001/api/timeseries/pools | python -m json.tool
```

### 3.3 Pull last N hours of history for one pool

Pick a pool ID from `/api/timeseries/pools`, for example `uniswap_v2_usdc_eth`.

```bash
POOL_ID="uniswap_v2_usdc_eth"

# Last 24 hours
curl -sS "http://localhost:8001/api/timeseries/history/${POOL_ID}?hours=24" | python -m json.tool

# Last 168 hours (7 days)
curl -sS "http://localhost:8001/api/timeseries/history/${POOL_ID}?hours=168" | python -m json.tool
```

### 3.4 Compute Phase-1 time-series features for a pool

```bash
POOL_ID="uniswap_v2_usdc_eth"

curl -sS "http://localhost:8001/api/timeseries/features/${POOL_ID}" | python -m json.tool
```

### 3.5 List risk signals across all pools (Phase 1)

```bash
curl -sS http://localhost:8001/api/timeseries/risk-signals | python -m json.tool
```

### 3.6 CLI-based Phase-1 validation (recommended for viva/demo)

```bash
cd /app/backend

# Show system status
python scripts/debug_timeseries.py --status

# Run sanity checks
python scripts/debug_timeseries.py --sanity-check

# Inspect a pool deeply
python scripts/debug_timeseries.py --pool uniswap_v2_usdc_eth --hours 48
```

---

## 4) Phase 2 tests — predictive synthetic data (30 days) + train + SHAP inference

Phase-2 ML uses the `snapshots` table (NOT `snapshot_history`).

### 4.1 Generate predictive synthetic data (30 days hourly) into `snapshots`

This generates multiple pools:
- Mixed/safe/risky profiles
- `high_risk_pool` and `critical_risk_pool` forced to end in a crash/pre-crash state
- `late_crash_pool_*` to ensure the **test split** has crash events

```bash
cd /app/backend
python data_fetcher.py --predictive
```

### 4.2 Train the predictive model (XGBoost)

```bash
cd /app/backend
python model_trainer.py

# Expected artifacts (paths in repo):
#   /app/models/xgb_veririsk_v2_predictive.pkl
#   /app/models/xgb_veririsk_v2_predictive_metadata.json
```

### 4.3 Run predictive inference (SHAP explanations)

```bash
cd /app/backend

# High-risk synthetic pool (should often be MEDIUM/HIGH)
python model_server.py --run-once --pool high_risk_pool

# Another forced-risk pool
python model_server.py --run-once --pool critical_risk_pool

# A "normal" pool
python model_server.py --run-once --pool synthetic_pool_2

# Rank all pools by risk
python model_server.py --all

# Raw JSON (useful for saving evidence)
python model_server.py --run-once --pool high_risk_pool --json
```

---

## 5) Phase 2 tests — REAL protocol data (DeFiLlama 30-day history) + predictions

This uses REAL historical TVL from DeFiLlama (daily) and interpolates to hourly.

### 5.1 Fetch REAL 30-day history into `snapshots`

⚠ This script clears existing `snapshots` for those pools before inserting.

```bash
cd /app/backend
python fetch_real_protocols.py --fetch-history --days 30

# Check DB status summary
python fetch_real_protocols.py --status
```

### 5.2 Run predictions on real-protocol pools

This requires a trained model present (you can train on synthetic or on real).

```bash
cd /app/backend

# NOTE: This script prints a lot; avoid piping to `head` because it can raise BrokenPipeError.
python fetch_real_protocols.py --predict
```

### 5.3 (Optional) Train model specifically on REAL history

If you want to claim “trained on real data”, do:

```bash
cd /app/backend
python model_trainer.py

# Then re-run real predictions
python fetch_real_protocols.py --predict
```

---

## 6) Phase 2 tests — simulated history from REAL current TVL (fallback path)

This uses current protocol TVLs and simulates hourly history around them.

```bash
cd /app/backend

# NOTE: this prints a lot; avoid piping to `head` because it can raise BrokenPipeError.

# Build 30 days of simulated history (720 hours)
python fetch_real_protocols.py --build-history --hours 720

# Check status
python fetch_real_protocols.py --status

# Predict
python fetch_real_protocols.py --predict
```

---

## 7) Phase 3 tests — risk history persistence + alert engine + APIs

### 7.1 Trigger Phase-3 prediction pipeline for one pool (API)

Pick a pool that exists in `snapshots`.

```bash
POOL_ID="high_risk_pool"

curl -sS -X POST "http://localhost:8001/api/risk/predict/${POOL_ID}" | python -m json.tool

# Check latest stored risk
curl -sS "http://localhost:8001/api/risk/latest/${POOL_ID}" | python -m json.tool

# Risk history (default 24h; max 168h)
curl -sS "http://localhost:8001/api/risk/history/${POOL_ID}?hours=24" | python -m json.tool
```

### 7.2 Trigger Phase-3 prediction pipeline for ALL pools (API)

```bash
curl -sS -X POST "http://localhost:8001/api/risk/predict-all" | python -m json.tool

# Summary across pools
curl -sS http://localhost:8001/api/risk/summary | python -m json.tool
```

### 7.3 Alerts

Note: Alerts API is implemented as `/api/risk/alerts` (router prefix `/risk`).

```bash
# Active alerts across all pools
curl -sS "http://localhost:8001/api/risk/alerts?status=active" | python -m json.tool

# Alerts for a single pool
POOL_ID="high_risk_pool"
curl -sS "http://localhost:8001/api/risk/alerts?status=active&pool_id=${POOL_ID}" | python -m json.tool
```

### 7.4 Force alerts to trigger (if you need deterministic demo)

If alerts are not firing, generate predictions repeatedly; Phase-3 prevents duplicates in a short window, so you may need to:
- Change pools
- Wait for the duplicate window to expire
- Reset DB and rerun with `high_risk_pool`

```bash
POOL_ID="high_risk_pool"

# Run multiple times (may or may not create new alerts due to dedupe)
for i in 1 2 3; do
  echo "Run $i";
  curl -sS -X POST "http://localhost:8001/api/risk/predict/${POOL_ID}" | python -m json.tool;
  sleep 1;
done

# Then inspect alerts
curl -sS "http://localhost:8001/api/risk/alerts?status=active&pool_id=${POOL_ID}" | python -m json.tool
```

---

## 8) (Optional) Validate DB contents quickly (no sqlite CLI needed)

```bash
cd /app/backend
python - <<'PY'
from database import SessionLocal, Snapshot
from db_models.snapshot_history import SnapshotHistory
from db_models.risk_history import RiskHistory
from db_models.alert import Alert
from sqlalchemy import func

db = SessionLocal()
try:
    print('snapshots:', db.query(func.count(Snapshot.id)).scalar())
    print('snapshot_history:', db.query(func.count(SnapshotHistory.id)).scalar())
    print('risk_history:', db.query(func.count(RiskHistory.id)).scalar())
    print('alerts:', db.query(func.count(Alert.id)).scalar())

    # Show a few pools
    pools = db.query(Snapshot.pool_id).distinct().limit(10).all()
    print('example pools:', [p[0] for p in pools])
finally:
    db.close()
PY
```

---

## 9) Expected “evidence” outputs for viva/demo

- Phase 1:
  - `/api/timeseries/status` shows `total_records` and pools with `ready_for_24h_analysis: true`
  - `python scripts/debug_timeseries.py --pool ...` prints last 24h table + computed features + risk signals

- Phase 2:
  - `python model_trainer.py` prints label distributions, metrics (ROC-AUC if possible), and feature importance
  - `python model_server.py --run-once --pool high_risk_pool` returns:
    - `risk_score` (0–100)
    - `risk_level`
    - `top_reasons` (SHAP top 3)

- Phase 3:
  - `/api/risk/latest/{pool_id}` returns persisted prediction
  - `/api/risk/history/{pool_id}` shows evolution (default 24h)
  - `/api/risk/alerts` returns active alerts with `top_reasons`

---

## 10) One-command “happy path” (synthetic-only demo)

```bash
sudo supervisorctl restart backend

# Phase 1 seed + verify
curl -sS -X POST "http://localhost:8001/api/timeseries/seed?hours=72" | python -m json.tool
curl -sS http://localhost:8001/api/timeseries/status | python -m json.tool

# Phase 2 generate + train + inference
cd /app/backend
python data_fetcher.py --predictive
python model_trainer.py
python model_server.py --run-once --pool high_risk_pool

# Phase 3 store risk + alerts via API
curl -sS -X POST "http://localhost:8001/api/risk/predict/high_risk_pool" | python -m json.tool
curl -sS "http://localhost:8001/api/risk/latest/high_risk_pool" | python -m json.tool
curl -sS "http://localhost:8001/api/risk/alerts?status=active" | python -m json.tool
```
