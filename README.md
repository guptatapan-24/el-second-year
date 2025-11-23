# VeriRisk - Verifiable AI Risk Oracle for DeFi

An end-to-end system that ingests on-chain & market data, computes explainable risk scores for DeFi protocols, cryptographically signs and publishes scores on-chain, enables smart contracts to consume them, and provides a user dashboard.

## 🏗️ Architecture

```
Data Sources → Backend/ML → Signed Payload → Smart Contract → Dashboard → Consumer Contracts
```

## 📁 Project Structure

```
/veririsk
  /backend          - Python FastAPI, data fetching, ML inference, signing
  /models           - XGBoost models, training scripts, artifacts
  /contracts        - Solidity smart contracts, Hardhat tests
  /frontend         - Next.js dashboard
  /deployment       - Docker, deployment scripts
  /experiments      - Backtesting, evaluation notebooks
  /docs             - Architecture, paper, threat model
  /tests            - Integration tests
  /.github          - CI/CD workflows
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Yarn
- Docker & Docker Compose
- Infura API key
- Sepolia testnet ETH

### Local Development

1. **Clone and setup:**
```bash
git clone <repo>
cd veririsk
```

2. **Backend setup:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Infura key and private key
python data_fetcher.py --once
python model_server.py
```

3. **Smart contracts:**
```bash
cd contracts
npm install
npx hardhat test
npx hardhat run scripts/deploy.js --network sepolia
```

4. **Frontend:**
```bash
cd frontend
yarn install
yarn dev
```

5. **Docker (all services):**
```bash
docker-compose up
```

## 🔑 Key Features

- **Off-chain ML Risk Computation**: XGBoost model with SHAP explainability
- **Cryptographic Signing**: Ethereum secp256k1 signatures for verification
- **On-chain Verification**: Solidity contracts with ECDSA signature checking
- **Real-time Dashboard**: Monitor risk scores and explanations
- **Automated Actions**: Consumer contracts react to risk thresholds
- **Reproducible Research**: Backtesting, evaluation metrics, IEEE paper

## 🧪 Testing

```bash
# Backend tests
cd backend && pytest

# Contract tests
cd contracts && npx hardhat test

# Frontend tests
cd frontend && yarn test

# E2E tests
cd tests && pytest test_e2e.py
```

## 📊 Demo Workflow

1. Data fetcher pulls on-chain/market data
2. ML model computes risk score (0-100) with top-3 explanations
3. Backend signs payload with private key
4. Submit transaction to VeriRiskOracle on Sepolia
5. Contract verifies signature and emits RiskUpdated event
6. Dashboard listens to events and displays risk
7. Consumer contract reads risk and takes action (pause/alert)

## 🔒 Security

- Signature verification via ECDSA
- Nonce-based replay protection
- Rate limiting on submissions
- Slither static analysis passed
- See [docs/threat_model.md](docs/threat_model.md)

## 📚 Documentation

- [Architecture Diagram](docs/architecture_diagram.png)
- [Threat Model](docs/threat_model.md)
- [API Documentation](docs/api.md)
- [Research Paper](docs/paper_draft.pdf)

## 🎥 Demo

- [Demo Video](docs/demo_video.mp4)
- [Pitch Deck](docs/pitch_deck.pdf)

## 📝 License

MIT License - see LICENSE file
