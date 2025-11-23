#!/bin/bash
set -e

echo "=== VeriRisk End-to-End Test ==="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cd backend

echo -e "${YELLOW}1. Testing model inference...${NC}"
python model_server.py --run-once --pool test_pool_1 > /tmp/inference_result.json
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Inference successful${NC}"
    cat /tmp/inference_result.json
else
    echo -e "${RED}✗ Inference failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}2. Testing signing...${NC}"
python signer.py --test-sign
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Signing successful${NC}"
else
    echo -e "${RED}✗ Signing failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}3. Testing API server...${NC}"
echo "Start the API server with: uvicorn api_server:app --reload"
echo "Then test with: curl http://localhost:8001/health"

echo ""
echo -e "${GREEN}=== Tests Complete ===${NC}"
