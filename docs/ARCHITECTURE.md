# VeriRisk System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                             │
├─────────────────────────────────────────────────────────────────┤
│  • Ethereum RPC (Infura)  • TheGraph  • CoinGecko  • On-chain   │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   BACKEND / ML SERVICE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Data Fetcher │→│ Preprocessing │→│   Features    │         │
│  └──────────────┘  └──────────────┘  └───────┬──────┘         │
│                                               │                 │
│  ┌──────────────┐  ┌──────────────┐         │                 │
│  │   Database   │←│  ML Inference │←────────┘                 │
│  │   (SQLite)   │  │   (XGBoost)  │                            │
│  └──────────────┘  └───────┬──────┘                            │
│                             │                                    │
│  ┌──────────────┐          │  ┌──────────────┐                │
│  │     SHAP     │←─────────┴─→│    Signer    │                │
│  │ Explainability│             │(eth-account) │                │
│  └──────────────┘             └───────┬──────┘                │
│                                        │                         │
│  ┌──────────────────────────────────┐│                         │
│  │       FastAPI Server             ││                         │
│  │  /health /infer /infer_and_sign  ││                         │
│  │  /push_chain /submissions        ││                         │
│  └──────────────────────────────────┘│                         │
└────────────────────────────────────────┼─────────────────────────┘
                                         │ Signed Payload
                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SMART CONTRACTS (Sepolia)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌───────────────────────────────────────────────────┐         │
│  │          VeriRiskOracle Contract                  │         │
│  │                                                     │         │
│  │  • submitRisk(poolId, score, signature, ...)      │         │
│  │  • getLatestRisk(poolId) → (score, timestamp)     │         │
│  │  • ECDSA signature verification                    │         │
│  │  • Nonce-based replay protection                   │         │
│  │  • Event emission: RiskUpdated                     │         │
│  └────────────────────┬──────────────────────────────┘         │
│                       │                                          │
│                       │ Events                                   │
│                       ▼                                          │
│  ┌───────────────────────────────────────────────────┐         │
│  │         ConsumerDemo Contract                     │         │
│  │                                                     │         │
│  │  • checkAndAct(poolId) - automated actions        │         │
│  │  • Pause pool if risk > 75                         │         │
│  │  • Increase collateral if risk > 60                │         │
│  └───────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                   │
                   │ Read Events via ethers.js
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FRONTEND DASHBOARD                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Dashboard   │  │  Pool Detail │  │  Admin Panel │         │
│  │   (Home)     │  │   (Charts)   │  │   (Testing)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  • Real-time event listening                                     │
│  • Risk visualization (Recharts)                                │
│  • Color-coded risk bands                                        │
│  • Transaction links (Sepolia Explorer)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Backend / ML Service

**Technology Stack:**
- Python 3.11
- FastAPI (API server)
- XGBoost (ML model)
- SHAP (Explainability)
- Web3.py (Blockchain interaction)
- SQLite (Data storage)
- APScheduler (Task scheduling)

**Modules:**

#### data_fetcher.py
- Pulls data from Infura RPC, TheGraph, CoinGecko
- Computes derived features
- Stores snapshots in database
- Generates synthetic data for testing

#### model_trainer.py
- Loads historical snapshots
- Creates risk labels based on heuristics
- Trains XGBoost classifier
- Saves model artifacts with SHA256 hash
- Computes evaluation metrics

#### model_server.py
- Loads trained XGBoost model
- Runs inference on latest snapshot
- Computes SHAP values for top-3 features
- Returns risk score (0-100) with explanations

#### signer.py
- Creates canonical JSON payload
- Signs with Ethereum secp256k1 key
- Verifies signatures
- Manages nonce generation

#### submit_to_chain.py
- Converts payload to contract parameters
- Builds and signs transaction
- Submits to VeriRiskOracle contract
- Waits for confirmation
- Stores submission in database

#### api_server.py
- FastAPI REST endpoints
- Health check, inference, signing, submission
- CORS enabled for frontend
- Error handling and validation

### 2. Smart Contracts

**Technology Stack:**
- Solidity 0.8.20
- Hardhat (Development framework)
- OpenZeppelin (Security libraries)
- Ethers.js (Testing)

**Contracts:**

#### VeriRiskOracle.sol
- Main oracle contract
- Signature verification via ECDSA
- Nonce tracking per signer per pool
- Gas-optimized storage (uint16, uint32)
- Events for frontend indexing

#### ConsumerDemo.sol
- Example consumer contract
- Reads risk from oracle
- Automated actions based on thresholds
- Pause pool if risk > 75
- Increase collateral if risk > 60

### 3. Frontend Dashboard

**Technology Stack:**
- Next.js 14 (React framework)
- TypeScript
- Tailwind CSS (Styling)
- Ethers.js (Blockchain interaction)
- Recharts (Data visualization)
- Axios (HTTP client)

**Pages:**

#### / (Dashboard)
- Grid of monitored pools
- Latest risk scores
- Color-coded risk badges
- Auto-refresh every 10 seconds
- Navigation to pool details

#### /pool/[id] (Pool Detail)
- Current risk assessment
- Historical risk chart (line chart)
- Top-3 risk factors (bar chart)
- Submission history table
- Links to Sepolia explorer

#### /admin (Admin Panel)
- Test inference without signing
- Test inference with signing
- Push risk updates to chain
- View signed payloads
- Useful for testing and demos

## Data Flow

### End-to-End Risk Update Flow

1. **Data Collection** (Every 5 minutes via scheduler)
   ```
   Data Sources → data_fetcher.py → Database
   ```

2. **Risk Computation**
   ```
   Database → model_server.py → Risk Score + SHAP Values
   ```

3. **Signing**
   ```
   Risk Payload → signer.py → Signed Payload (with signature)
   ```

4. **Chain Submission**
   ```
   Signed Payload → submit_to_chain.py → VeriRiskOracle Contract → RiskUpdated Event
   ```

5. **Frontend Update**
   ```
   RiskUpdated Event → Frontend (ethers.js) → Dashboard UI Update
   ```

6. **Consumer Action** (Optional)
   ```
   Consumer Contract → getLatestRisk() → checkAndAct() → Pause/Adjust
   ```

## Security Architecture

### Cryptographic Verification

```
1. Create canonical JSON (sorted keys, no whitespace)
2. Hash with SHA256
3. Sign with Ethereum key (secp256k1)
4. Submit signature + payload to contract
5. Contract verifies:
   - Recover signer from signature
   - Check signer == authorizedSigner
   - Verify nonce not reused
   - Validate timestamp freshness
```

### Replay Protection

```
Mapping: signer → poolId → lastNonce

On submission:
  require(nonce > lastNonce[signer][poolId])
  lastNonce[signer][poolId] = nonce
```

## Scalability Considerations

### Current Limits
- Single backend server
- SQLite database
- Single oracle signer
- Sepolia testnet only

### Production Scaling

1. **Backend:**
   - Horizontal scaling with load balancer
   - PostgreSQL with replication
   - Redis caching
   - Kubernetes deployment

2. **Blockchain:**
   - Multiple oracle nodes
   - Aggregation contract
   - Layer 2 deployment (Arbitrum/Optimism)
   - Multi-chain support

3. **Frontend:**
   - CDN distribution
   - Server-side rendering
   - WebSocket for real-time updates
   - Vercel/Netlify deployment

## Monitoring & Observability

### Metrics to Track

**Backend:**
- API request latency
- Model inference time
- Database query performance
- Data fetch success rate
- Transaction success rate

**Smart Contracts:**
- Gas usage per submission
- Submission frequency
- Failed transactions
- Event emission rate

**Frontend:**
- Page load time
- Error rate
- User interactions

### Logging

**Backend:**
```python
import logging
logging.info(f"Risk computed for {pool_id}: {risk_score}")
logging.error(f"Failed to submit to chain: {error}")
```

**Smart Contracts:**
```solidity
event RiskUpdated(bytes32 indexed poolId, uint16 score, ...);
event SignerUpdated(address indexed oldSigner, address indexed newSigner);
```

### Alerts

- Stale risk data (>1 hour old)
- Transaction failures
- API downtime
- Model inference errors
- High gas prices

## Deployment Architecture

### Development
```
Local machine:
- Backend: localhost:8001
- Frontend: localhost:3000
- Hardhat: localhost:8545
```

### Staging
```
Cloud (AWS/GCP):
- Backend: api-staging.veririsk.io
- Frontend: staging.veririsk.io
- Blockchain: Sepolia testnet
```

### Production
```
Cloud (AWS/GCP):
- Backend: api.veririsk.io (load balanced)
- Frontend: veririsk.io (CDN)
- Blockchain: Ethereum mainnet + L2s
- Database: PostgreSQL (RDS)
- Caching: Redis (ElastiCache)
- Monitoring: Datadog/Prometheus
```

## Technology Decisions

### Why XGBoost?
- Fast inference (<10ms)
- Handles tabular data well
- Built-in feature importance
- Easy to interpret with SHAP
- Production-proven

### Why SHAP?
- Model-agnostic explainability
- Consistent feature attribution
- Fast TreeExplainer for XGBoost
- Research-backed methodology

### Why Solidity 0.8.20?
- Built-in overflow protection
- Latest stable version
- Good tooling support
- OpenZeppelin 5.0 compatibility

### Why Next.js?
- Server-side rendering
- API routes
- Optimized performance
- Great DX
- Vercel deployment

### Why Sepolia?
- Active testnet (Goerli deprecated)
- Good faucet availability
- Infura support
- Similar to mainnet

## Future Enhancements

1. **Multi-Model Ensemble**
   - XGBoost + LSTM + GNN
   - Weighted voting
   - Confidence scoring

2. **Zero-Knowledge Proofs**
   - zk-SNARKs for model execution proof
   - Privacy-preserving risk computation
   - Reduced on-chain verification cost

3. **Decentralized Oracle Network**
   - 7+ independent nodes
   - Median aggregation
   - Economic security via staking

4. **Real-Time Risk Monitoring**
   - Streaming data pipeline
   - Sub-minute latency
   - Anomaly detection

5. **Advanced Explainability**
   - Counterfactual explanations
   - Feature interaction analysis
   - Risk decomposition
