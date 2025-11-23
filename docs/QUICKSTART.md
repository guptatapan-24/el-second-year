# VeriRisk Quick Start Guide

## Overview

VeriRisk is a complete Verifiable AI Risk Oracle system for DeFi protocols with:
- ✅ ML risk prediction (XGBoost + SHAP)
- ✅ Cryptographic signing with Ethereum keys  
- ✅ Smart contracts for on-chain verification (Sepolia)
- ✅ Real-time dashboard
- ✅ Consumer contract demo
- ✅ Full test suite

## Test Account

**Address:** `0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048`

**Important:** This address needs Sepolia ETH to deploy contracts.

## Quick Start (5 minutes)

### 1. Generate Data & Train Model

```bash
cd /app/backend
python data_fetcher.py --synthetic  # Generate 400 synthetic snapshots
python model_trainer.py             # Train XGBoost model
```

### 2. Test ML Inference

```bash
python model_server.py --run-once --pool test_pool_1
```

You should see risk score output with SHAP explanations.

### 3. Test Signing

```bash
python signer.py --test-sign
```

Verifies cryptographic signing workflow.

### 4. Start Backend API

```bash
cd /app/backend
python api_server.py
```

API runs on `http://localhost:8001`

Test health endpoint:
```bash
curl http://localhost:8001/health
```

### 5. Get Sepolia ETH

Before deploying contracts, get testnet ETH:

1. Visit: https://sepoliafaucet.com/
2. Enter address: `0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048`
3. Wait 1-2 minutes for confirmation

### 6. Deploy Contracts

```bash
cd /app/contracts
npx hardhat test                                    # Run tests first
npx hardhat run scripts/deploy.js --network sepolia # Deploy to Sepolia
```

**Copy the Oracle contract address from output!**

### 7. Update Backend Config

Edit `/app/backend/.env`:

```bash
ORACLE_CONTRACT_ADDRESS=<your_deployed_oracle_address>
```

Restart backend API.

### 8. Test End-to-End

```bash
cd /app/backend

# Run inference and push to chain
curl -X POST http://localhost:8001/push_chain \
  -H "Content-Type: application/json" \
  -d '{"pool_id": "test_pool_1"}'
```

Check Sepolia explorer: https://sepolia.etherscan.io/address/0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048

### 9. Start Frontend

```bash
cd /app/frontend
yarn dev
```

Open http://localhost:3000

## What You'll See

### Dashboard (http://localhost:3000)
- Grid of monitored pools
- Real-time risk scores
- Color-coded risk levels (green/yellow/red)
- Auto-refresh every 10 seconds

### Pool Detail Page
- Current risk assessment
- Risk score history chart
- Top 3 risk factors with SHAP values
- Submission history
- Links to Sepolia explorer

### Admin Panel (http://localhost:3000/admin)
- Test inference without signing
- Test inference with signing
- Push risk updates to blockchain
- View signed payloads

## API Endpoints

```
GET  /health              - Health check
POST /infer               - Run inference only
POST /infer_and_sign      - Inference + signing
POST /push_chain          - Full workflow (infer, sign, submit)
GET  /submissions         - Get submission history
GET  /snapshots           - Get data snapshots
```

## Smart Contract Functions

### VeriRiskOracle

```solidity
// Submit signed risk data
function submitRisk(
    bytes32 poolId,
    uint16 score,
    uint256 timestamp,
    bytes signature,
    bytes32 cidHash,
    uint256 nonce
)

// Get latest risk
function getLatestRisk(bytes32 poolId) 
    returns (uint16 score, uint256 timestamp, bytes32 cidHash)

// Check if data is stale
function isRiskStale(bytes32 poolId, uint256 maxAge) 
    returns (bool)
```

### ConsumerDemo

```solidity
// Take automated action based on risk
function checkAndAct(bytes32 poolId)

// Simulate action without executing
function simulateAction(bytes32 poolId) 
    returns (string action, uint16 riskScore)
```

## Troubleshooting

### "Model not loaded" error
```bash
cd /app/backend
python model_trainer.py
```

### "Insufficient funds" on deployment
Get Sepolia ETH from faucets listed in DEPLOYMENT_GUIDE.md

### "Invalid signer" error
Ensure Oracle contract was deployed with correct signer address.

### Backend connection error in frontend
Check NEXT_PUBLIC_BACKEND_API in `/app/frontend/.env.local`

## Next Steps

1. **Add Real Data Sources**: Integrate with real DEX/lending protocols
2. **Improve Model**: Train on historical failure data
3. **Add More Pools**: Monitor multiple protocols
4. **Implement Scheduler**: Auto-update risk scores every 5 minutes
5. **Add Notifications**: Alert on high risk
6. **Deploy to Production**: Use mainnet, professional key management

## Docker Quick Start

```bash
cd /app
docker-compose up
```

Services:
- Backend API: http://localhost:8001
- Frontend: http://localhost:3000

## Testing

```bash
# Backend tests
cd /app/backend
pytest

# Contract tests  
cd /app/contracts
npx hardhat test

# E2E test script
/app/scripts/test-e2e.sh
```

## Resources

- Sepolia Faucet: https://sepoliafaucet.com/
- Sepolia Explorer: https://sepolia.etherscan.io/
- XGBoost Docs: https://xgboost.readthedocs.io/
- SHAP Docs: https://shap.readthedocs.io/
- Hardhat Docs: https://hardhat.org/
- Next.js Docs: https://nextjs.org/
