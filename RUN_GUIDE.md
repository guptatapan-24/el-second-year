# 🚀 VeriRisk - Complete Run Guide

## Prerequisites Check
```bash
# Check Python version (need 3.10+)
python3 --version

# Check Node.js version (need 18+)
node --version

# Check if yarn is installed
yarn --version
```

---

## 📦 STEP 1: Backend Setup & Run

### 1.1 Install Backend Dependencies
```bash
# Navigate to backend directory
cd /app/backend

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi, web3, xgboost; print('✓ Dependencies OK')"
```

### 1.2 Initialize Database & Generate Training Data
```bash
# Still in /app/backend directory

# Generate synthetic training data (for ML model)
python data_fetcher.py --synthetic

# Train the ML model
python model_trainer.py

# Verify model was created
ls -lh ../models/xgb_veririsk_v1.pkl
```

### 1.3 Test Real-Time Data Fetching
```bash
# Test that live data fetching works
python test_data_fetching.py

# Expected output: "✅ TEST PASSED - Real-time data fetching is working!"
```

### 1.4 Start Backend Server
```bash
# Option A: Run directly (foreground)
python server.py

# Option B: Run with supervisor (background)
sudo supervisorctl restart backend

# Option C: Run with uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### 1.5 Verify Backend is Running
Open a new terminal and run:
```bash
# Test health endpoint
curl http://localhost:8001/health | jq

# Expected response should include:
# - "status": "healthy"
# - "scheduler": true
# - "live_percentage": should be high (80%+)

# Test protocols endpoint
curl http://localhost:8001/protocols | jq '.[0]'

# Should show protocol data with TVL values
```

---

## 🎨 STEP 2: Frontend Setup & Run

### 2.1 Install Frontend Dependencies
```bash
# Navigate to frontend directory
cd /app/frontend

# Install Node.js dependencies with yarn
yarn install

# This will take 2-3 minutes
# Wait for "✨ Done" message
```

### 2.2 Verify Environment Variables
```bash
# Check that .env file exists and has correct backend URL
cat .env

# Should show:
# NEXT_PUBLIC_BACKEND_API=/api

# If file doesn't exist, create it:
echo "NEXT_PUBLIC_BACKEND_API=/api" > .env
```

### 2.3 Start Frontend Development Server
```bash
# Still in /app/frontend directory

# Option A: Run with yarn (recommended)
yarn dev

# Option B: Run with supervisor
sudo supervisorctl restart frontend

# Option C: Run with npm
npm run dev
```

### 2.4 Verify Frontend is Running
```bash
# In a new terminal, test the frontend
curl http://localhost:3000

# Should return HTML content

# Or open in browser:
# http://localhost:3000
```

---

## ✅ STEP 3: Verify Everything is Working

### 3.1 Check All Services
```bash
# Check if both services are running
sudo supervisorctl status

# Expected output:
# backend    RUNNING
# frontend   RUNNING
```

### 3.2 Test Data Flow
```bash
# Test backend health with data status
curl http://localhost:8001/health | jq '.data_status'

# Should show:
# - "status": "fresh" (if data < 10 min old)
# - "live_percentage": 80-100%

# Manually trigger a data fetch (optional)
curl -X POST http://localhost:8001/fetch_protocols

# Check protocols are available
curl http://localhost:8001/protocols | jq 'length'
# Should return: 18 (number of protocols)
```

### 3.3 Access the Dashboard
Open your browser and navigate to:
```
http://localhost:3000
```

You should see:
- Dashboard with protocol cards
- Risk scores for each protocol
- TVL values
- Color-coded risk levels (green/yellow/red)

---

## 🔄 QUICK START (All-in-One)

If you want to start everything quickly:

```bash
# Terminal 1 - Backend
cd /app/backend && python server.py

# Terminal 2 - Frontend
cd /app/frontend && yarn dev

# Terminal 3 - Monitor logs
tail -f /var/log/supervisor/backend.*.log
```

---

## 📊 STEP 4: Monitor & Verify Real-Time Data

### 4.1 Watch Backend Logs
```bash
# View backend logs in real-time
tail -f /var/log/supervisor/backend.*.log

# You should see periodic messages like:
# "🔄 STARTING MULTI-PROTOCOL DATA FETCH"
# "✅ FETCH COMPLETE!"
# "🟢 Live data: 18 (100.0%)"
```

### 4.2 Check Database Content
```bash
cd /app/backend

# View recent snapshots
python -c "
from database import SessionLocal, Snapshot
from datetime import datetime

db = SessionLocal()
snapshots = db.query(Snapshot).order_by(Snapshot.timestamp.desc()).limit(10).all()

print('Recent Snapshots:')
print('-' * 80)
for s in snapshots:
    age = (datetime.utcnow() - s.timestamp).total_seconds()
    is_live = not s.features.get('synthetic', False) if isinstance(s.features, dict) else False
    status = '🟢 LIVE' if is_live else '🟡 SYNTHETIC'
    print(f'{s.pool_id:<35} \${s.tvl:>15,.0f}  {status}  ({int(age)}s ago)')
db.close()
"
```

### 4.3 Test API Endpoints
```bash
# Get all protocols
curl http://localhost:8001/protocols

# Get snapshots for specific pool
curl http://localhost:8001/snapshots?pool_id=uniswap_v2_usdc_eth

# Get submission history
curl http://localhost:8001/submissions
```

---

## 🐛 Troubleshooting

### Backend Won't Start

**Error: "Model not loaded"**
```bash
cd /app/backend
python data_fetcher.py --synthetic
python model_trainer.py
python server.py
```

**Error: "No module named 'X'"**
```bash
cd /app/backend
pip install -r requirements.txt --force-reinstall
```

**Error: Port 8001 already in use**
```bash
# Find and kill the process
lsof -ti:8001 | xargs kill -9
# Then restart
python server.py
```

### Frontend Won't Start

**Error: "EADDRINUSE: address already in use :::3000"**
```bash
# Find and kill the process
lsof -ti:3000 | xargs kill -9
# Then restart
cd /app/frontend && yarn dev
```

**Error: "node_modules not found"**
```bash
cd /app/frontend
rm -rf node_modules yarn.lock
yarn install
yarn dev
```

**Error: Can't connect to backend**
```bash
# Check backend is running
curl http://localhost:8001/health

# Check .env file
cat /app/frontend/.env

# Should be: NEXT_PUBLIC_BACKEND_API=/api
```

### Data Issues

**Problem: No live data (100% synthetic)**
```bash
# Test API connectivity
cd /app/backend
python -c "
from protocols import DeFiLlamaFetcher
llama = DeFiLlamaFetcher()
data = llama.get_protocol_tvl('uniswap-v2')
print('✓ API working' if data else '✗ API failed')
"

# If API failed, check internet connection
ping -c 3 api.llama.fi
```

**Problem: Stale data**
```bash
# Manually trigger fetch
curl -X POST http://localhost:8001/fetch_protocols

# Restart scheduler
sudo supervisorctl restart backend
```

---

## 📱 Access Points

Once everything is running:

- **Frontend Dashboard**: http://localhost:3000
- **API Health Check**: http://localhost:8001/health
- **API Docs**: http://localhost:8001/docs (Swagger UI)
- **Protocols List**: http://localhost:3000/protocols
- **Admin Panel**: http://localhost:3000/admin

---

## 🛑 Stopping Services

### Stop All Services
```bash
sudo supervisorctl stop all
```

### Stop Individual Services
```bash
# Stop backend only
sudo supervisorctl stop backend

# Stop frontend only
sudo supervisorctl stop frontend
```

### Stop Manual Processes
```bash
# If you ran services manually (Ctrl+C in the terminal)
# Or find and kill:
pkill -f "python server.py"
pkill -f "yarn dev"
```

---

## 🔄 Restart Services

```bash
# Restart all services
sudo supervisorctl restart all

# Restart individual services
sudo supervisorctl restart backend
sudo supervisorctl restart frontend

# Check status
sudo supervisorctl status
```

---

## 📝 Quick Reference

### Backend Commands
```bash
cd /app/backend

# Test data fetching
python test_data_fetching.py

# Generate training data
python data_fetcher.py --synthetic

# Train model
python model_trainer.py

# Run server
python server.py

# Test API
curl http://localhost:8001/health
```

### Frontend Commands
```bash
cd /app/frontend

# Install dependencies
yarn install

# Run development server
yarn dev

# Build for production
yarn build

# Run production build
yarn start
```

---

## ✅ Success Checklist

After running everything, verify:

- [ ] Backend server running on port 8001
- [ ] Frontend server running on port 3000
- [ ] `/health` endpoint returns "healthy"
- [ ] Live data percentage > 80%
- [ ] Dashboard loads at http://localhost:3000
- [ ] Protocol cards show TVL values
- [ ] Data updates every 5 minutes (check logs)
- [ ] No errors in logs

---

## 🎓 For Demo/Presentation

### Recommended Demo Flow

1. **Start services** (in separate terminals for visibility):
   ```bash
   # Terminal 1
   cd /app/backend && python server.py
   
   # Terminal 2
   cd /app/frontend && yarn dev
   ```

2. **Show live data fetching**:
   ```bash
   # Terminal 3
   cd /app/backend && python test_data_fetching.py
   ```

3. **Open browser**: http://localhost:3000
   - Show dashboard
   - Click on a protocol to see details
   - Point out TVL values from real protocols

4. **Show API health**:
   ```bash
   curl http://localhost:8001/health | jq
   ```

5. **Highlight**:
   - "Data is fetching from real DeFi protocols via DeFiLlama API"
   - "System updates automatically every 5 minutes"
   - "100% live data, no simulation"
   - "Production-ready error handling and retry logic"

---

**Need help? Check logs:**
```bash
# Backend logs
tail -f /var/log/supervisor/backend.*.log

# Frontend logs
tail -f /var/log/supervisor/frontend.*.log
```
