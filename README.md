# 🛡️ VeriRisk - Verifiable AI Risk Oracle for DeFi

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![Node](https://img.shields.io/badge/node-18+-green)
![Solidity](https://img.shields.io/badge/solidity-0.8.20-363636)

**An end-to-end verifiable AI risk oracle system for DeFi protocols**

*XGBoost ML • SHAP Explainability • On-Chain Verification • Real-Time Dashboard*

[Quick Start](#-quick-start) •
[Architecture](#-system-architecture) •
[API Docs](#-api-documentation) •
[Smart Contracts](#-smart-contracts) •
[Contributing](#-contributing)

</div>

---

## 📖 Overview

VeriRisk is a comprehensive, production-ready system that provides **verifiable AI-powered risk scoring** for DeFi protocols. It combines machine learning, cryptographic signing, and blockchain verification to deliver trustworthy, explainable risk assessments.

### Key Capabilities

- 🤖 **Predictive Risk Scoring**: XGBoost model predicting 24-hour crash probability (0-100 scale)
- 🔍 **SHAP Explainability**: Top-3 contributing factors with human-readable explanations
- 🔐 **Cryptographic Verification**: ECDSA signatures with on-chain verification
- ⛓️ **Blockchain Integration**: Solidity smart contracts on Ethereum Sepolia
- 📊 **Real-Time Dashboard**: Next.js dashboard with live monitoring and alerts
- 🤖 **Automated Actions**: Consumer contracts that react to risk thresholds
- 📈 **Time-Series Analytics**: Historical risk trends and protocol health tracking

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            DATA SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  Ethereum RPC (Infura)  •  TheGraph  •  CoinGecko  •  On-Chain Data      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKEND / ML SERVICE (FastAPI)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ Data Fetcher │───▸│ Feature Eng. │───▸│  XGBoost ML  │              │
│  │  (Scheduler) │    │  (Advanced)  │    │  (Inference) │              │
│  └──────────────┘    └──────────────┘    └──────┬───────┘              │
│                                                  │                       │
│  ┌──────────────┐    ┌──────────────┐          │                       │
│  │   SQLite     │◀───│    SHAP      │◀─────────┘                       │
│  │   Database   │    │ Explainer    │                                   │
│  └──────────────┘    └──────────────┘                                   │
│                                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Payload    │───▸│   Signer     │───▸│    Chain     │              │
│  │   Creator    │    │  (ECDSA)     │    │  Submitter   │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                           │
│                    ┌─────────────────────────────────┐                  │
│                    │      FastAPI REST Server        │                  │
│                    │  /api/risk  /api/protocols      │                  │
│                    │  /api/submissions  /api/alerts  │                  │
│                    └─────────────────────────────────┘                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Signed Payload
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SMART CONTRACTS (Ethereum Sepolia)                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │              VeriRiskOracle.sol                          │            │
│  │  • submitRisk(poolId, score, signature, ...)            │            │
│  │  • getLatestRisk(poolId) → (score, timestamp)           │            │
│  │  • ECDSA signature verification                          │            │
│  │  • Nonce-based replay protection                         │            │
│  └───────────────────────────┬─────────────────────────────┘            │
│                               │                                          │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │              ConsumerDemo.sol                            │            │
│  │  • checkAndAct(poolId) - automated risk actions         │            │
│  │  • Pause pool if risk > 75                               │            │
│  │  • Increase collateral if risk > 60                      │            │
│  └─────────────────────────────────────────────────────────┘            │
│                                                                           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Events
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      FRONTEND DASHBOARD (Next.js)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Home       │    │  Protocols   │    │   Alerts     │              │
│  │  Dashboard   │    │   Detail     │    │   Center     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                           │
│  ┌──────────────┐    ┌──────────────┐                                   │
│  │  Simulation  │    │    Admin     │                                   │
│  │    Mode      │    │    Panel     │                                   │
│  └──────────────┘    └──────────────┘                                   │
│                                                                           │
│  • Real-time risk monitoring         • Color-coded risk levels           │
│  • SHAP explanation visualizations   • Historical trend charts           │
│  • Alert management                  • Blockchain explorer links         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
/app
├── 📂 backend/                    # Python FastAPI Backend
│   ├── server.py                  # Main FastAPI application
│   ├── api_server.py              # Alternative API server entry
│   ├── config.py                  # Configuration management
│   ├── database.py                # SQLAlchemy database setup
│   ├── data_fetcher.py            # Multi-source data fetching
│   ├── model_server.py            # ML inference server
│   ├── model_trainer.py           # XGBoost model training
│   ├── signer.py                  # ECDSA payload signing
│   ├── submit_to_chain.py         # Blockchain submission
│   ├── scheduler.py               # APScheduler for auto-updates
│   ├── protocols.py               # Multi-protocol data fetcher
│   ├── 📂 routers/                # API route handlers
│   │   ├── protocols.py           # Protocol endpoints
│   │   ├── risk.py                # Risk scoring endpoints
│   │   ├── submissions.py         # Submission history
│   │   └── timeseries.py          # Time-series data
│   ├── 📂 features/               # Feature engineering
│   │   ├── advanced_features.py   # Predictive features
│   │   └── basic_timeseries.py    # Basic time-series features
│   ├── 📂 services/               # Business logic services
│   │   ├── risk_evaluator.py      # Risk evaluation logic
│   │   └── simulation_service.py  # Crisis simulation
│   ├── 📂 db_models/              # Database models
│   │   ├── alert.py               # Alert model
│   │   ├── risk_history.py        # Risk history model
│   │   └── snapshot_history.py    # Snapshot model
│   ├── 📂 jobs/                   # Scheduled jobs
│   │   └── hourly_snapshot.py     # Hourly data collection
│   ├── requirements.txt           # Python dependencies
│   └── Dockerfile                 # Docker configuration
│
├── 📂 frontend/                   # Next.js Frontend
│   ├── 📂 pages/                  # Next.js pages
│   │   ├── index.tsx              # Home dashboard
│   │   ├── protocols/index.tsx    # Protocol list
│   │   ├── protocols/[pool_id].tsx # Protocol detail
│   │   ├── alerts.tsx             # Alert center
│   │   ├── simulation.tsx         # Simulation mode
│   │   └── admin.tsx              # Admin panel
│   ├── 📂 components/             # React components
│   ├── 📂 styles/                 # CSS styles
│   ├── package.json               # Node.js dependencies
│   ├── tailwind.config.js         # Tailwind CSS config
│   └── Dockerfile                 # Docker configuration
│
├── 📂 contracts/                  # Solidity Smart Contracts
│   ├── 📂 contracts/
│   │   ├── VeriRiskOracle.sol     # Main oracle contract
│   │   └── ConsumerDemo.sol       # Consumer demo contract
│   ├── 📂 scripts/
│   │   └── deploy.js              # Deployment script
│   ├── 📂 test/                   # Contract tests
│   ├── hardhat.config.js          # Hardhat configuration
│   └── package.json               # Node.js dependencies
│
├── 📂 models/                     # Trained ML Models
│   ├── xgb_veririsk_v1.pkl        # V1 reactive model
│   ├── xgb_veririsk_v2_predictive.pkl  # V2 predictive model
│   └── *_metadata.json            # Model metadata
│
├── 📂 docs/                       # Documentation
│   ├── API.md                     # API reference
│   ├── ARCHITECTURE.md            # System architecture
│   ├── DEPLOYMENT_GUIDE.md        # Deployment instructions
│   ├── QUICKSTART.md              # Quick start guide
│   └── threat_model.md            # Security analysis
│
├── 📂 deployment/                 # Deployment utilities
│   └── ipfs_uploader.py           # IPFS artifact upload
│
├── 📂 experiments/                # Research & Experiments
│   └── backtest.py                # Model backtesting
│
├── 📂 tests/                      # Integration tests
│   └── test_e2e.py                # End-to-end tests
│
├── 📂 scripts/                    # Utility scripts
│   ├── setup.sh                   # Setup script
│   └── test-e2e.sh                # E2E test runner
│
├── docker-compose.yml             # Docker Compose config
└── README.md                      # This file
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend & contracts |
| Yarn | 1.22+ | Package management |
| Docker | 20.10+ | Containerization (optional) |
| Git | 2.x | Version control |

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd veririsk

# Start all services
docker-compose up

# Services will be available at:
# - Backend API: http://localhost:8001
# - Frontend: http://localhost:3000
```

### Option 2: Manual Setup

#### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (see Configuration section)

# Initialize database and generate training data
python data_fetcher.py --predictive

# Train ML model
python model_trainer.py

# Start API server (runs on port 8001)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

#### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Configure environment
echo "NEXT_PUBLIC_BACKEND_API=http://localhost:8001" > .env.local

# Start development server (runs on port 3000)
yarn dev
```

#### 3. Smart Contracts (Optional)

```bash
cd contracts

# Install dependencies
yarn install

# Run tests
npx hardhat test

# Deploy to Sepolia (requires testnet ETH)
npx hardhat run scripts/deploy.js --network sepolia
```

---

## ⚙️ Configuration

### Backend Environment Variables

Create `/backend/.env`:

```bash
# Ethereum Configuration
INFURA_PROJECT_ID=your_infura_project_id
ETH_RPC_URL=https://sepolia.infura.io/v3/your_infura_project_id
SIGNER_PRIVATE_KEY=your_private_key_hex
ORACLE_CONTRACT_ADDRESS=deployed_oracle_address

# API Keys (Optional)
COINGECKO_API_KEY=your_coingecko_key
THEGRAPH_API_KEY=your_thegraph_key

# Database
DATABASE_URL=sqlite:///./veririsk.db

# Model Configuration
MODEL_PATH=../models/xgb_veririsk_v2_predictive.pkl
UPDATE_INTERVAL_SECONDS=300  # 5 minutes
```

### Frontend Environment Variables

Create `/frontend/.env.local`:

```bash
NEXT_PUBLIC_BACKEND_API=http://localhost:8001
```

### Getting API Keys

| Service | URL | Purpose |
|---------|-----|---------|
| Infura | https://infura.io | Ethereum RPC access |
| CoinGecko | https://coingecko.com/api | Market data |
| TheGraph | https://thegraph.com | DEX subgraph queries |

---

## 📊 API Documentation

### Base URL
```
http://localhost:8001/api
```

### Core Endpoints

#### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "components": {
    "model_server": true,
    "signer": true,
    "submitter": true,
    "scheduler": true
  },
  "data_status": {
    "status": "fresh",
    "latest_snapshot_age_seconds": 120,
    "recent_snapshots": {
      "total": 50,
      "live_data": 45,
      "synthetic_data": 5,
      "live_percentage": 90.0
    }
  }
}
```

#### Risk Summary
```http
GET /api/risk/summary
```

Response:
```json
{
  "total_pools": 12,
  "high_risk_pools": 2,
  "total_tvl": 15000000,
  "pools": [
    {
      "pool_id": "synthetic_aave_v3",
      "latest_risk_score": 72.5,
      "latest_risk_level": "HIGH",
      "tvl": 1200000,
      "active_alerts": 1
    }
  ]
}
```

#### Get Risk for Pool
```http
POST /infer
Content-Type: application/json

{
  "pool_id": "synthetic_pool_1"
}
```

Response:
```json
{
  "pool_id": "synthetic_pool_1",
  "risk_score": 45.3,
  "risk_level": "MEDIUM",
  "prediction_horizon": "24h",
  "top_reasons": [
    {
      "feature": "tvl_change_6h",
      "impact": -12.5,
      "direction": "increases_risk",
      "explanation": "Recent TVL trend is significantly increasing predicted risk"
    },
    {
      "feature": "reserve_imbalance",
      "impact": 8.3,
      "direction": "increases_risk",
      "explanation": "Liquidity imbalance is slightly increasing manipulation risk"
    }
  ],
  "early_warning_score": 38.5,
  "model_version": "v2.0_predictive",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### Push Risk to Chain
```http
POST /push_chain
Content-Type: application/json

{
  "pool_id": "synthetic_pool_1"
}
```

Response:
```json
{
  "success": true,
  "pool_id": "synthetic_pool_1",
  "risk_score": 45.3,
  "tx_hash": "0xabc123...",
  "explorer_url": "https://sepolia.etherscan.io/tx/0xabc123..."
}
```

### Full API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/api/risk/summary` | GET | All pools risk summary |
| `/api/risk/alerts` | GET | Active risk alerts |
| `/api/protocols` | GET | List all protocols |
| `/api/protocols/status` | GET | System status |
| `/api/protocols/{pool_id}` | GET | Protocol details |
| `/api/protocols/{pool_id}/risk` | POST | Compute risk for pool |
| `/api/protocols/fetch-real-data` | POST | Fetch live data |
| `/api/timeseries/{pool_id}` | GET | Time-series data |
| `/api/submissions` | GET | Submission history |
| `/infer` | POST | Run ML inference |
| `/infer_and_sign` | POST | Inference + signing |
| `/push_chain` | POST | Full blockchain submission |
| `/snapshots` | GET | Data snapshots |

---

## 🔗 Smart Contracts

### VeriRiskOracle.sol

Main oracle contract for storing and verifying risk scores.

```solidity
// Submit signed risk data
function submitRisk(
    bytes32 poolId,      // Pool identifier
    uint16 score,        // Risk score (0-100)
    uint256 timestamp,   // Computation timestamp
    bytes signature,     // ECDSA signature
    bytes32 cidHash,     // Model artifact IPFS hash
    uint256 nonce        // Replay protection nonce
) external;

// Read latest risk
function getLatestRisk(bytes32 poolId) 
    external view 
    returns (uint16 score, uint256 timestamp, bytes32 cidHash);

// Check staleness
function isRiskStale(bytes32 poolId, uint256 maxAge) 
    external view 
    returns (bool);
```

### ConsumerDemo.sol

Example consumer contract demonstrating automated risk responses.

```solidity
// Check risk and take action
function checkAndAct(bytes32 poolId) external;

// Simulate action without executing
function simulateAction(bytes32 poolId) 
    external view 
    returns (string action, uint16 riskScore);
```

### Deployment Addresses

| Network | Contract | Address |
|---------|----------|---------|
| Sepolia | VeriRiskOracle | Deploy with `npx hardhat run scripts/deploy.js --network sepolia` |
| Sepolia | ConsumerDemo | Deployed alongside Oracle |

---

## 🤖 Machine Learning Model

### Model Architecture

- **Algorithm**: XGBoost Classifier
- **Version**: V2 Predictive (24h crash prediction)
- **Features**: 10 engineered time-series features

### Feature Engineering

| Feature | Description | Time Window |
|---------|-------------|-------------|
| `tvl_change_6h` | TVL percentage change | 6 hours |
| `tvl_change_24h` | TVL percentage change | 24 hours |
| `tvl_acceleration` | Rate of TVL change | 6-24h diff |
| `volume_spike_ratio` | Volume vs. moving average | 24 hours |
| `reserve_imbalance` | Token reserve ratio | Current |
| `reserve_imbalance_rate` | Imbalance change rate | 6 hours |
| `volatility_6h` | Price volatility | 6 hours |
| `volatility_24h` | Price volatility | 24 hours |
| `volatility_ratio` | Short/long volatility | 6h/24h |
| `early_warning_score` | Composite risk indicator | Multiple |

### Risk Levels

| Score Range | Level | Color | Action |
|-------------|-------|-------|--------|
| 0-30 | LOW | 🟢 Green | No action needed |
| 31-65 | MEDIUM | 🟡 Yellow | Monitor closely |
| 66-100 | HIGH | 🔴 Red | Immediate attention |

### Training

```bash
# Generate training data with crash patterns
python data_fetcher.py --predictive

# Train model
python model_trainer.py

# Model saved to: ../models/xgb_veririsk_v2_predictive.pkl
```

---

## 🔒 Security

### Cryptographic Security

- **Signature Algorithm**: ECDSA (secp256k1)
- **Message Hashing**: Keccak256 with Ethereum signed message prefix
- **Replay Protection**: Nonce-based (monotonically increasing per signer/pool)
- **Timestamp Validation**: Max 1-hour age, max 5-minute future

### On-Chain Verification

```solidity
// Signature verification in VeriRiskOracle
bytes32 dataHash = keccak256(abi.encodePacked(poolId, score, timestamp, cidHash, nonce));
bytes32 ethSignedMessageHash = dataHash.toEthSignedMessageHash();
address recoveredSigner = ethSignedMessageHash.recover(signature);
require(recoveredSigner == authorizedSigner, "Invalid signature");
```

### Security Measures

| Measure | Implementation |
|---------|----------------|
| Signature Verification | ECDSA with OpenZeppelin libraries |
| Replay Protection | Per-signer, per-pool nonce tracking |
| Timestamp Validation | ±1 hour from block timestamp |
| Access Control | Owner-only signer updates |
| Rate Limiting | Configurable via scheduler |

### Threat Model

See [docs/threat_model.md](docs/threat_model.md) for comprehensive security analysis including:
- Oracle key compromise
- Data poisoning
- Adversarial ML attacks
- Front-running
- Centralization risks

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Test specific module
pytest tests/test_model_server.py -v
```

### Smart Contract Tests

```bash
cd contracts

# Run Hardhat tests
npx hardhat test

# Run with gas reporting
REPORT_GAS=true npx hardhat test

# Run static analysis
slither contracts/
```

### Frontend Tests

```bash
cd frontend

# Run tests
yarn test

# Run with coverage
yarn test --coverage
```

### End-to-End Tests

```bash
# From project root
./scripts/test-e2e.sh

# Or manually
cd tests
pytest test_e2e.py -v
```

---

## 📈 Monitoring & Observability

### Health Endpoints

- Backend: `GET /health`
- Component status, data freshness, scheduler state

### Logs

```bash
# Backend logs
tail -f /var/log/supervisor/backend.*.log

# Frontend logs (development)
yarn dev  # Outputs to console

# Docker logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Metrics to Monitor

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| API Latency | Response time | > 500ms |
| Model Inference | Prediction time | > 100ms |
| Data Freshness | Latest snapshot age | > 10 minutes |
| Transaction Success | Chain submission rate | < 95% |
| Risk Score Drift | Score variance | > 20 points/hour |

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Considerations

1. **Backend Scaling**
   - Horizontal scaling with load balancer
   - PostgreSQL for production database
   - Redis for caching

2. **Blockchain**
   - Deploy to Layer 2 (Arbitrum, Optimism) for lower gas
   - Consider multi-signer oracle network
   - Use Flashbots for MEV protection

3. **Frontend**
   - Deploy to Vercel/Netlify
   - CDN for static assets
   - WebSocket for real-time updates

### Getting Sepolia ETH

1. [Alchemy Faucet](https://sepoliafaucet.com/)
2. [Infura Faucet](https://www.infura.io/faucet/sepolia)
3. [Google Cloud Faucet](https://cloud.google.com/application/web3/faucet/ethereum/sepolia)

---

## 🛠️ Development

### Code Style

- **Python**: Black formatter, isort imports, flake8 linting
- **TypeScript**: ESLint, Prettier
- **Solidity**: Solhint

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install
```

### Git Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit
3. Run tests: `pytest && yarn test`
4. Push and create PR

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/guptatapan-24/el-second-year.git

# Install development dependencies
pip install -r requirements-dev.txt
yarn install

# Run linters
flake8 backend/
yarn lint
```

---

## 📚 Resources

### Documentation

- [Quick Start Guide](docs/QUICKSTART.md)
- [API Documentation](docs/API.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Threat Model](docs/threat_model.md)

### External Links

- [XGBoost Documentation](https://xgboost.readthedocs.io/)
- [SHAP Documentation](https://shap.readthedocs.io/)
- [Hardhat Documentation](https://hardhat.org/docs)
- [Next.js Documentation](https://nextjs.org/docs)
- [Sepolia Explorer](https://sepolia.etherscan.io/)

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OpenZeppelin](https://openzeppelin.com/) - Smart contract security libraries
- [SHAP](https://github.com/slundberg/shap) - ML explainability
- [TheGraph](https://thegraph.com/) - Blockchain data indexing
- [Infura](https://infura.io/) - Ethereum infrastructure

---

<div align="center">

**Built with ❤️ for DeFi Safety**

[Report Bug](https://github.com/guptatapan-24/el-second-year/issues) •
[Request Feature](https://github.com/guptatapan-24/el-second-year/issues)

</div>
