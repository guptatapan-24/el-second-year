# VeriRisk API Documentation

## Base URL

```
http://localhost:8001
```

## Authentication

No authentication required for MVP.

In production, add API key authentication.

## Endpoints

### Health Check

**GET** `/health`

Check API server status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "components": {
    "model_server": true,
    "signer": true,
    "submitter": true
  }
}
```

---

### Run Inference

**POST** `/infer`

Compute risk score with SHAP explanations.

**Request Body:**
```json
{
  "pool_id": "test_pool_1"
}
```

**Response:**
```json
{
  "pool_id": "test_pool_1",
  "risk_score": 45.3,
  "risk_level": "MEDIUM",
  "top_reasons": [
    {"feature": "tvl_pct_change_1h", "impact": -12.5},
    {"feature": "reserve_imbalance", "impact": 8.3},
    {"feature": "volatility_24h", "impact": 5.1}
  ],
  "model_version": "xgb_v1",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "features": {
    "tvl": 1000000,
    "reserve0": 500000,
    "reserve1": 500000,
    "volume_24h": 200000,
    "tvl_pct_change_1h": -5.2,
    "reserve_imbalance": 0.15,
    "volume_tvl_ratio": 0.2,
    "volatility_24h": 0.08,
    "leverage_ratio": 2.5
  }
}
```

---

### Infer and Sign

**POST** `/infer_and_sign`

Compute risk score and create signed payload.

**Request Body:**
```json
{
  "pool_id": "test_pool_1"
}
```

**Response:**
```json
{
  "pool_id": "test_pool_1",
  "risk_score": 45.3,
  "top_reasons": [...],
  "model_version": "xgb_v1",
  "artifact_cid": "QmModelArtifact",
  "timestamp": 1705318200,
  "nonce": 1705318200,
  "signature": "0xabc123...",
  "signer_address": "0xE6791Fb925cD110c5Be24aCe1d6837d0D0c1A048"
}
```

---

### Push to Chain

**POST** `/push_chain`

Complete workflow: infer, sign, and submit to blockchain.

**Request Body:**
```json
{
  "pool_id": "test_pool_1"
}
```

**Response:**
```json
{
  "success": true,
  "pool_id": "test_pool_1",
  "risk_score": 45.3,
  "tx_hash": "0xdef456...",
  "explorer_url": "https://sepolia.etherscan.io/tx/0xdef456..."
}
```

**Error Response:**
```json
{
  "detail": "Chain submitter not ready"
}
```

---

### Get Submissions

**GET** `/submissions?pool_id=test_pool_1`

Retrieve risk submission history.

**Query Parameters:**
- `pool_id` (optional): Filter by specific pool

**Response:**
```json
[
  {
    "pool_id": "test_pool_1",
    "risk_score": 45.3,
    "timestamp": "2024-01-15T10:30:00.000Z",
    "tx_hash": "0xdef456...",
    "status": "confirmed",
    "top_reasons": [...]
  },
  ...
]
```

---

### Get Snapshots

**GET** `/snapshots?pool_id=test_pool_1&limit=50`

Retrieve data snapshots.

**Query Parameters:**
- `pool_id` (optional): Filter by specific pool
- `limit` (optional, default=50): Max number of results

**Response:**
```json
[
  {
    "snapshot_id": "abc123",
    "pool_id": "test_pool_1",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "tvl": 1000000,
    "volume_24h": 200000,
    "features": {...}
  },
  ...
]
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 200  | Success |
| 500  | Internal server error |
| 503  | Service unavailable (component not ready) |

## Rate Limits

No rate limits in MVP.

In production, implement:
- 10 requests/minute per IP
- 100 requests/hour per IP

## Data Models

### Risk Score
- Range: 0-100
- 0-30: Low risk (green)
- 31-65: Medium risk (yellow)
- 66-100: High risk (red)

### Features Used

1. **tvl**: Total Value Locked (USD)
2. **reserve0**: Token 0 reserves
3. **reserve1**: Token 1 reserves  
4. **volume_24h**: 24-hour trading volume (USD)
5. **tvl_pct_change_1h**: TVL % change in last hour
6. **reserve_imbalance**: Ratio of reserve imbalance
7. **volume_tvl_ratio**: Volume to TVL ratio
8. **volatility_24h**: 24-hour price volatility
9. **leverage_ratio**: Effective leverage

### SHAP Impact Values

- Positive impact: Increases risk
- Negative impact: Decreases risk
- Magnitude: Contribution to final score

## Examples

### cURL Examples

```bash
# Health check
curl http://localhost:8001/health

# Run inference
curl -X POST http://localhost:8001/infer \
  -H "Content-Type: application/json" \
  -d '{"pool_id": "test_pool_1"}'

# Infer and sign
curl -X POST http://localhost:8001/infer_and_sign \
  -H "Content-Type: application/json" \
  -d '{"pool_id": "test_pool_1"}'

# Push to chain
curl -X POST http://localhost:8001/push_chain \
  -H "Content-Type: application/json" \
  -d '{"pool_id": "test_pool_1"}'

# Get submissions
curl http://localhost:8001/submissions?pool_id=test_pool_1

# Get snapshots
curl http://localhost:8001/snapshots?limit=10
```

### Python Examples

```python
import requests

API_URL = "http://localhost:8001"

# Run inference
response = requests.post(
    f"{API_URL}/infer",
    json={"pool_id": "test_pool_1"}
)
result = response.json()
print(f"Risk Score: {result['risk_score']}")

# Push to chain
response = requests.post(
    f"{API_URL}/push_chain",
    json={"pool_id": "test_pool_1"}
)
result = response.json()
print(f"TX Hash: {result['tx_hash']}")
```

### JavaScript Examples

```javascript
// Using fetch
const response = await fetch('http://localhost:8001/infer', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({pool_id: 'test_pool_1'})
});
const result = await response.json();
console.log('Risk Score:', result.risk_score);

// Using axios
import axios from 'axios';

const result = await axios.post('http://localhost:8001/push_chain', {
  pool_id: 'test_pool_1'
});
console.log('TX Hash:', result.data.tx_hash);
```
