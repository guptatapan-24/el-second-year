# VeriRisk Deployment Guide

## Test Account Information

**Address:** `0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048`
**Private Key:** (stored in .env - DO NOT SHARE)

## Getting Sepolia ETH

You need testnet ETH to deploy contracts. Get free Sepolia ETH from these faucets:

### Recommended Faucets:

1. **Alchemy Sepolia Faucet**
   - URL: https://sepoliafaucet.com/
   - Login with Alchemy account
   - Provides 0.5 SepoliaETH per day

2. **Infura Sepolia Faucet**
   - URL: https://www.infura.io/faucet/sepolia
   - Login with Infura account
   - Provides 0.5 SepoliaETH per day

3. **QuickNode Faucet**
   - URL: https://faucet.quicknode.com/ethereum/sepolia
   - Requires Twitter/GitHub verification
   - Provides 0.05 SepoliaETH

4. **Google Cloud Web3 Faucet**
   - URL: https://cloud.google.com/application/web3/faucet/ethereum/sepolia
   - Requires Google login
   - Provides 0.05 SepoliaETH

### Steps to Get Testnet ETH:

1. Visit one of the faucet URLs above
2. Enter the address: `0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048`
3. Complete verification (if required)
4. Wait for transaction confirmation (1-2 minutes)
5. Verify balance: https://sepolia.etherscan.io/address/0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048

## Deployment Steps

Once you have Sepolia ETH:

### 1. Check Balance

```bash
cd /app/contracts
npx hardhat run --network sepolia scripts/check-balance.js
```

### 2. Deploy Contracts

```bash
cd /app/contracts
npx hardhat run scripts/deploy.js --network sepolia
```

This will deploy:
- VeriRiskOracle contract
- ConsumerDemo contract

### 3. Update Backend Configuration

After deployment, update `/app/backend/.env` with the oracle contract address:

```bash
ORACLE_CONTRACT_ADDRESS=<deployed_oracle_address>
```

### 4. Verify Contracts (Optional)

```bash
npx hardhat verify --network sepolia <ORACLE_ADDRESS> "0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048"
npx hardhat verify --network sepolia <CONSUMER_ADDRESS> "<ORACLE_ADDRESS>"
```

## Testing Deployment

### Test Submission

```bash
cd /app/backend
python model_server.py --run-once --pool test_pool_1 > payload.json
python submit_to_chain.py --payload payload.json
```

### View on Explorer

- Sepolia Etherscan: https://sepolia.etherscan.io/
- View transactions: https://sepolia.etherscan.io/address/0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048

## Local Testing (Alternative)

If you want to test without Sepolia ETH:

### 1. Start Local Hardhat Node

```bash
cd /app/contracts
npx hardhat node
```

This creates a local blockchain with test accounts that have 10,000 ETH each.

### 2. Deploy to Local Network

```bash
npx hardhat run scripts/deploy.js --network localhost
```

### 3. Update Backend .env

```bash
ETH_RPC_URL=http://127.0.0.1:8545
```

## Troubleshooting

### Insufficient Funds Error
```
ProviderError: insufficient funds for gas * price + value
```
**Solution:** Get Sepolia ETH from faucets above

### Connection Timeout
```
Error: timeout exceeded
```
**Solution:** Check Infura API key is correct

### Invalid Nonce
```
Error: nonce has already been used
```
**Solution:** Reset account nonce or increment manually

## Next Steps

After successful deployment:

1. Start the backend API server
2. Launch the frontend dashboard
3. Test end-to-end risk submission flow
4. Monitor events on Sepolia explorer
