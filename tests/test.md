# VeriRisk Complete Testing Guide for Windows 11 PowerShell

## Table of Contents
1. [Prerequisites Installation](#1-prerequisites-installation)
2. [Project Setup](#2-project-setup)
3. [Backend Setup & Testing](#3-backend-setup--testing)
4. [Frontend Setup & Testing](#4-frontend-setup--testing)
5. [Full Workflow Testing](#5-full-workflow-testing)
6. [API Endpoint Testing](#6-api-endpoint-testing)
7. [Simulation Testing](#7-simulation-testing)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites Installation

### 1.1 Install Node.js (v18+)
```powershell
# Download and install from: https://nodejs.org/
# Verify installation:
node --version
# Expected: v18.x.x or higher

npm --version
# Expected: 9.x.x or higher
```

### 1.2 Install Yarn Package Manager
```powershell
npm install -g yarn
yarn --version
# Expected: 1.22.x
```

### 1.3 Install Python (v3.10+)
```powershell
# Download and install from: https://www.python.org/downloads/
# IMPORTANT: Check "Add Python to PATH" during installation

# Verify installation:
python --version
# Expected: Python 3.10.x or higher

pip --version
# Expected: pip 23.x.x
```

### 1.4 Install MongoDB (v6+)
```powershell
# Download and install from: https://www.mongodb.com/try/download/community
# Choose "Complete" installation
# Check "Install MongoDB as a Service"

# Verify MongoDB is running:
Get-Service MongoDB
# Expected: Status = Running

# If not running:
net start MongoDB
```

### 1.5 Install Git
```powershell
# Download from: https://git-scm.com/downloads
git --version
# Expected: git version 2.x.x
```

---

## 2. Project Setup

### 2.1 Clone Repository
```powershell
# Navigate to your projects folder
cd C:\Projects

# Clone the repository
git clone <your-repo-url> veririsk
cd veririsk

# Verify structure
Get-ChildItem
# Expected: backend/, frontend/, contracts/, docs/, models/, etc.
```

### 2.2 Verify Project Structure
```powershell
Get-ChildItem -Recurse -Depth 1 | Select-Object Name, PSIsContainer
```
**Expected Output:**
```
Name        PSIsContainer
----        -------------
backend     True
frontend    True
contracts   True
docs        True
models      True
scripts     True
tests       True
```

---

## 3. Backend Setup & Testing

### 3.1 Create Python Virtual Environment
```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Verify activation (should see (venv) in prompt)
# Expected: (venv) PS C:\Projects\veririsk\backend>
```

### 3.2 Install Python Dependencies
```powershell
# Upgrade pip first
python -m pip install --upgrade pip

# Install setuptools (required for some packages)
pip install setuptools

# Install all requirements
pip install -r requirements.txt

# Verify key packages
pip show fastapi uvicorn xgboost shap scikit-learn
```
**Expected Output:** Package details for each listed package

### 3.3 Configure Backend Environment
```powershell
# Create .env file
@"
MONGO_URL=mongodb://localhost:27017/veririsk
PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000001
RPC_URL=https://sepolia.infura.io/v3/dummy_key
"@ | Out-File -FilePath .env -Encoding utf8

# Verify .env created
Get-Content .env
```

### 3.4 Start Backend Server
```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Start the server
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```
**Expected Output:**
```
INFO:     Database initialized
INFO:     Model server ready
INFO:     Signer ready: 0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf
INFO:     Chain submitter ready
INFO:     Scheduler started - Auto-fetching every 5 minutes
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

### 3.5 Test Backend Health (New PowerShell Window)
```powershell
# Test health endpoint
$response = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get
$response | ConvertTo-Json -Depth 5
```
**Expected Output:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-08T14:30:00.000000",
  "components": {
    "model_server": true,
    "signer": true,
    "submitter": true,
    "scheduler": true
  },
  "data_status": {
    "status": "no_data",
    "latest_snapshot_age_seconds": null,
    "latest_snapshot_time": null,
    "recent_snapshots": {
      "total": 0,
      "live_data": 0,
      "synthetic_data": 0,
      "live_percentage": 0
    }
  }
}
```

---

## 4. Frontend Setup & Testing

### 4.1 Install Frontend Dependencies (New PowerShell Window)
```powershell
cd C:\Projects\veririsk\frontend

# Install dependencies with yarn
yarn install
```
**Expected Output:**
```
yarn install v1.22.22
[1/4] Resolving packages...
[2/4] Fetching packages...
[3/4] Linking dependencies...
[4/4] Building fresh packages...
Done in XX.XXs.
```

### 4.2 Configure Frontend Environment
```powershell
# Create .env file
@"
NEXT_PUBLIC_BACKEND_API=http://localhost:8001
"@ | Out-File -FilePath .env -Encoding utf8

# Verify
Get-Content .env
```

### 4.3 Start Frontend Development Server
```powershell
yarn dev
```
**Expected Output:**
```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
event - compiled client and server successfully in XXX ms
```

### 4.4 Test Frontend Access
```powershell
# In another PowerShell window
$response = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing
$response.StatusCode
# Expected: 200

# Check content contains VeriRisk
$response.Content -match "VeriRisk"
# Expected: True
```

---

## 5. Full Workflow Testing

### 5.1 Check Initial System Status
```powershell
$status = Invoke-RestMethod -Uri "http://localhost:8001/api/protocols/status"
$status | ConvertTo-Json -Depth 3
```
**Expected Output (Initial State):**
```json
{
  "total_snapshots": 0,
  "pool_count": 0,
  "hours_of_history": 0,
  "latest_snapshot": null,
  "oldest_snapshot": null,
  "model_trained": true,
  "data_ready": false,
  "init_status": {
    "running": false,
    "phase": "",
    "progress": 0,
    "error": null,
    "completed": false
  }
}
```

### 5.2 Initialize System with Real DeFiLlama Data
```powershell
# This fetches 30 days of real DeFi protocol data and trains the ML model
$init = Invoke-RestMethod -Uri "http://localhost:8001/api/protocols/initialize?days=30" -Method Post
$init | ConvertTo-Json -Depth 3
```
**Expected Output:**
```json
{
  "status": "started",
  "message": "Initializing VeriRisk with 30 days of historical data",
  "steps": [
    "1. Fetching real historical TVL from DeFiLlama",
    "2. Training XGBoost ML model",
    "3. Running risk predictions for all pools",
    "4. Generating alerts"
  ],
  "note": "Use GET /api/protocols/status to check progress"
}
```

### 5.3 Monitor Initialization Progress
```powershell
# Poll status every 10 seconds until complete
do {
    Start-Sleep -Seconds 10
    $status = Invoke-RestMethod -Uri "http://localhost:8001/api/protocols/status"
    Write-Host "Phase: $($status.init_status.phase) | Progress: $($status.init_status.progress)%"
} while ($status.init_status.running -eq $true)

Write-Host "Initialization complete!"
$status | ConvertTo-Json -Depth 3
```
**Expected Progress:**
```
Phase: Fetching 30-day historical data from DeFiLlama... | Progress: 10%
Phase: Historical data fetched. Training ML model... | Progress: 40%
Phase: Model trained. Running risk predictions... | Progress: 70%
Phase: Initialization complete! | Progress: 100%
Initialization complete!
```

**Final Expected Output:**
```json
{
  "total_snapshots": 150,
  "pool_count": 5,
  "hours_of_history": 720,
  "latest_snapshot": "2026-01-08T14:35:00.000000",
  "oldest_snapshot": "2025-12-09T14:35:00.000000",
  "model_trained": true,
  "data_ready": true,
  "init_status": {
    "running": false,
    "phase": "Initialization complete!",
    "progress": 100,
    "error": null,
    "completed": true
  }
}
```

---

## 6. API Endpoint Testing

### 6.1 Test Protocols List
```powershell
$protocols = Invoke-RestMethod -Uri "http://localhost:8001/api/protocols"
$protocols | ConvertTo-Json -Depth 3
Write-Host "Total protocols: $($protocols.Count)"
```
**Expected Output:**
```json
[
  {
    "pool_id": "uniswap_v3_eth-usdc",
    "protocol": "Uniswap V3",
    "category": "DEX",
    "tvl": 500000000,
    "volume_24h": 150000000,
    "last_update": "2026-01-08T14:35:00",
    "data_source": "live"
  },
  ...
]
```

### 6.2 Test Risk Summary
```powershell
$summary = Invoke-RestMethod -Uri "http://localhost:8001/api/risk/summary"
$summary | ConvertTo-Json -Depth 3
```
**Expected Output:**
```json
{
  "total_pools": 5,
  "high_risk_pools": 1,
  "medium_risk_pools": 2,
  "low_risk_pools": 2,
  "total_active_alerts": 3,
  "pools": [
    {
      "pool_id": "aave_v3_eth",
      "latest_risk_score": 72.5,
      "latest_risk_level": "HIGH",
      "active_alerts": 2
    },
    ...
  ],
  "timestamp": "2026-01-08T14:40:00.000000"
}
```

### 6.3 Test Individual Pool Risk
```powershell
# Replace with actual pool_id from protocols list
$poolId = "uniswap_v3_eth-usdc"
$risk = Invoke-RestMethod -Uri "http://localhost:8001/api/risk/latest/$poolId"
$risk | ConvertTo-Json -Depth 3
```
**Expected Output:**
```json
{
  "pool_id": "uniswap_v3_eth-usdc",
  "risk_score": 35.2,
  "risk_level": "MEDIUM",
  "early_warning_score": 22.5,
  "top_reasons": [
    {
      "feature": "tvl_change_1h",
      "impact": 0.15,
      "direction": "increasing",
      "explanation": "TVL volatility contributing to risk"
    },
    {
      "feature": "volume_volatility",
      "impact": 0.12,
      "direction": "increasing",
      "explanation": "High trading volume volatility"
    }
  ],
  "model_version": "xgb_veririsk_v2_predictive",
  "prediction_horizon": "1h",
  "timestamp": "2026-01-08T14:40:00.000000"
}
```

### 6.4 Test Risk History
```powershell
$poolId = "uniswap_v3_eth-usdc"
$history = Invoke-RestMethod -Uri "http://localhost:8001/api/risk/history/$poolId`?hours=48"
$history | ConvertTo-Json -Depth 3
Write-Host "History records: $($history.count)"
```
**Expected Output:**
```json
{
  "pool_id": "uniswap_v3_eth-usdc",
  "records": [
    {
      "risk_score": 32.1,
      "risk_level": "MEDIUM",
      "early_warning_score": 20.5,
      "top_reasons": [...],
      "timestamp": "2026-01-06T14:40:00"
    },
    ...
  ],
  "count": 48,
  "oldest": "2026-01-06T14:40:00",
  "newest": "2026-01-08T14:40:00"
}
```

### 6.5 Test Alerts
```powershell
# Get all active alerts
$alerts = Invoke-RestMethod -Uri "http://localhost:8001/api/risk/alerts?status=active"
$alerts | ConvertTo-Json -Depth 4
Write-Host "Active alerts: $($alerts.count)"
```
**Expected Output:**
```json
{
  "alerts": [
    {
      "id": 1,
      "pool_id": "aave_v3_eth",
      "alert_type": "HIGH_RISK_ALERT",
      "risk_score": 72.5,
      "risk_level": "HIGH",
      "message": "Risk score exceeded HIGH threshold (65)",
      "top_reasons": [...],
      "status": "active",
      "previous_risk_level": "MEDIUM",
      "previous_risk_score": 58.3,
      "created_at": "2026-01-08T14:35:00"
    }
  ],
  "count": 3
}
```

### 6.6 Trigger Manual Prediction
```powershell
$poolId = "uniswap_v3_eth-usdc"
$prediction = Invoke-RestMethod -Uri "http://localhost:8001/api/risk/predict/$poolId" -Method Post
$prediction | ConvertTo-Json -Depth 2
```
**Expected Output:**
```json
{
  "status": "success",
  "pool_id": "uniswap_v3_eth-usdc",
  "risk_score": 35.8,
  "risk_level": "MEDIUM",
  "alerts_generated": 0,
  "timestamp": "2026-01-08T14:45:00.000000"
}
```

### 6.7 Trigger All Predictions
```powershell
$allPredictions = Invoke-RestMethod -Uri "http://localhost:8001/api/risk/predict-all" -Method Post
$allPredictions | ConvertTo-Json -Depth 2
```
**Expected Output:**
```json
{
  "status": "success",
  "pools_predicted": 5,
  "alerts_generated": 1,
  "timestamp": "2026-01-08T14:45:00.000000"
}
```

---

## 7. Simulation Testing

### 7.1 Browser-Based Simulation Test
1. Open browser: `http://localhost:3000/simulation`
2. Select a protocol from dropdown
3. Click "TVL Crash" event card
4. Click "Run Simulation"
5. Observe:
   - Before/After risk score comparison
   - SHAP explanation panel
   - Alert triggered indicator
   - ML vs Rule-Based comparison

### 7.2 Manual Simulation via API
```powershell
# Note: Simulation endpoint is frontend-based simulation
# The ML prediction can be triggered via:

# Step 1: Get current risk
$poolId = "uniswap_v3_eth-usdc"
$before = Invoke-RestMethod -Uri "http://localhost:8001/api/risk/latest/$poolId"
Write-Host "Before - Risk Score: $($before.risk_score) | Level: $($before.risk_level)"

# Step 2: Trigger new prediction (simulates data change)
$after = Invoke-RestMethod -Uri "http://localhost:8001/api/risk/predict/$poolId" -Method Post
Write-Host "After - Risk Score: $($after.risk_score) | Level: $($after.risk_level)"
```

---

## 8. Troubleshooting

### 8.1 Backend Won't Start

**Error: `ModuleNotFoundError: No module named 'pkg_resources'`**
```powershell
pip install setuptools
```

**Error: `ModuleNotFoundError: No module named 'xxx'`**
```powershell
pip install -r requirements.txt --force-reinstall
```

**Error: MongoDB Connection Failed**
```powershell
# Check if MongoDB is running
Get-Service MongoDB

# Start MongoDB
net start MongoDB

# Or run manually
mongod --dbpath "C:\data\db"
```

### 8.2 Frontend Won't Start

**Error: `yarn: command not found`**
```powershell
npm install -g yarn
```

**Error: Build failures**
```powershell
# Clear cache and reinstall
Remove-Item -Recurse -Force node_modules
Remove-Item yarn.lock
yarn cache clean
yarn install
```

### 8.3 API Connection Errors

**CORS Errors in Browser**
- Backend already has CORS configured for all origins
- If still failing, check browser console for specific error

**Connection Refused**
```powershell
# Verify backend is running
Test-NetConnection -ComputerName localhost -Port 8001

# Expected: TcpTestSucceeded : True
```

### 8.4 Database Issues

**Reset Database**
```powershell
# Connect to MongoDB
mongo

# In mongo shell:
use veririsk
db.dropDatabase()
exit
```

**Check Database Content**
```powershell
mongo veririsk --eval "db.snapshots.count()"
mongo veririsk --eval "db.risk_history.count()"
mongo veririsk --eval "db.alerts.count()"
```

---

## Quick Reference: All API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| GET | `/api/protocols` | List all protocols |
| GET | `/api/protocols/status` | Data & init status |
| POST | `/api/protocols/initialize?days=30` | Initialize with real data |
| POST | `/api/protocols/fetch` | Fetch latest data |
| POST | `/api/protocols/train-model` | Retrain ML model |
| GET | `/api/risk/summary` | Risk overview |
| GET | `/api/risk/latest/{pool_id}` | Latest risk for pool |
| GET | `/api/risk/history/{pool_id}?hours=48` | Risk history |
| GET | `/api/risk/alerts?status=active` | List alerts |
| POST | `/api/risk/predict/{pool_id}` | Predict single pool |
| POST | `/api/risk/predict-all` | Predict all pools |

---

## Quick Reference: Frontend Pages

| URL | Page | Features |
|-----|------|----------|
| `http://localhost:3000` | Dashboard | Stats, overview, alerts |
| `http://localhost:3000/protocols` | Protocols | Protocol cards, filters |
| `http://localhost:3000/protocols/{pool_id}` | Detail | Gauge, SHAP, timeline |
| `http://localhost:3000/alerts` | Alerts | Alert feed, filters |
| `http://localhost:3000/simulation` | Simulation | Event simulation |

---

## Success Checklist

- [ ] Backend starts without errors
- [ ] Frontend compiles successfully
- [ ] Health endpoint returns "healthy"
- [ ] Protocols list returns data after initialization
- [ ] Risk summary shows pool statistics
- [ ] Individual pool risk shows SHAP explanations
- [ ] Risk history shows timeline data
- [ ] Alerts endpoint returns alert list
- [ ] Simulation page loads and functions
- [ ] All frontend pages render correctly
