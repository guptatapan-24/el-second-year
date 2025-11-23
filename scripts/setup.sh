#!/bin/bash
set -e

echo "=== VeriRisk Setup Script ==="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}1. Setting up Python backend...${NC}"
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
cd ..

echo -e "${GREEN}✓ Backend setup complete${NC}"

echo -e "${YELLOW}2. Setting up smart contracts...${NC}"
cd contracts
yarn install
cd ..

echo -e "${GREEN}✓ Contracts setup complete${NC}"

echo -e "${YELLOW}3. Setting up frontend...${NC}"
cd frontend
yarn install
cd ..

echo -e "${GREEN}✓ Frontend setup complete${NC}"

echo -e "${YELLOW}4. Generating synthetic data...${NC}"
cd backend
source venv/bin/activate
python data_fetcher.py --synthetic
cd ..

echo -e "${GREEN}✓ Synthetic data generated${NC}"

echo -e "${YELLOW}5. Training ML model...${NC}"
cd backend
source venv/bin/activate
python model_trainer.py
cd ..

echo -e "${GREEN}✓ Model training complete${NC}"

echo ""
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo ""
echo "Next steps:"
echo "1. Get Sepolia ETH for test address: 0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048"
echo "2. Deploy contracts: cd contracts && npx hardhat run scripts/deploy.js --network sepolia"
echo "3. Update ORACLE_CONTRACT_ADDRESS in backend/.env"
echo "4. Start backend: cd backend && uvicorn api_server:app --reload"
echo "5. Start frontend: cd frontend && yarn dev"
echo ""
