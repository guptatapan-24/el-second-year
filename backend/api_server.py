#!/usr/bin/env python3
"""FastAPI server for VeriRisk backend"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime

from model_server import ModelServer
from signer import PayloadSigner
from submit_to_chain import ChainSubmitter
from database import get_db, init_db, Snapshot, RiskSubmission
from config import config
from scheduler import RiskScheduler

# Initialize FastAPI
app = FastAPI(
    title="VeriRisk API",
    description="Verifiable AI Risk Oracle for DeFi",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
model_server = None
signer = None
submitter = None

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    global model_server, signer, submitter
    
    # Initialize database
    init_db()
    print("Database initialized")
    
    # Initialize model server
    try:
        model_server = ModelServer()
        print("Model server ready")
    except Exception as e:
        print(f"Warning: Model server not ready: {e}")
    
    # Initialize signer
    try:
        signer = PayloadSigner()
        print(f"Signer ready: {signer.address}")
    except Exception as e:
        print(f"Warning: Signer not ready: {e}")
    
    # Initialize submitter
    try:
        submitter = ChainSubmitter()
        print(f"Chain submitter ready")
    except Exception as e:
        print(f"Warning: Chain submitter not ready: {e}")

# Request/Response models
class InferRequest(BaseModel):
    pool_id: str

class InferResponse(BaseModel):
    pool_id: str
    risk_score: float
    risk_level: str
    top_reasons: List[dict]
    model_version: str
    timestamp: str

class SignedPayloadResponse(BaseModel):
    pool_id: str
    risk_score: float
    top_reasons: List[dict]
    model_version: str
    artifact_cid: str
    timestamp: int
    nonce: int
    signature: str
    signer_address: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "model_server": model_server is not None,
            "signer": signer is not None,
            "submitter": submitter is not None
        }
    }

@app.post("/infer", response_model=InferResponse)
async def infer_risk(request: InferRequest):
    """Run inference for a pool"""
    if model_server is None:
        raise HTTPException(status_code=503, detail="Model server not ready")
    
    try:
        result = model_server.predict_risk(request.pool_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/infer_and_sign", response_model=SignedPayloadResponse)
async def infer_and_sign(request: InferRequest):
    """Run inference and return signed payload"""
    if model_server is None:
        raise HTTPException(status_code=503, detail="Model server not ready")
    if signer is None:
        raise HTTPException(status_code=503, detail="Signer not ready")
    
    try:
        # Predict risk
        result = model_server.predict_risk(request.pool_id)
        
        # Create payload
        payload = signer.create_payload(
            pool_id=result['pool_id'],
            risk_score=result['risk_score'],
            top_reasons=result['top_reasons'],
            model_version=result['model_version'],
            artifact_cid="QmModelArtifact"
        )
        
        # Sign payload
        signed = signer.sign_payload(payload)
        
        return signed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/push_chain")
async def push_to_chain(request: InferRequest):
    """Run inference, sign, and push to blockchain"""
    if model_server is None:
        raise HTTPException(status_code=503, detail="Model server not ready")
    if signer is None:
        raise HTTPException(status_code=503, detail="Signer not ready")
    if submitter is None:
        raise HTTPException(status_code=503, detail="Chain submitter not ready")
    
    try:
        # Predict risk
        result = model_server.predict_risk(request.pool_id)
        
        # Create and sign payload
        payload = signer.create_payload(
            pool_id=result['pool_id'],
            risk_score=result['risk_score'],
            top_reasons=result['top_reasons'],
            model_version=result['model_version'],
            artifact_cid="QmModelArtifact"
        )
        signed = signer.sign_payload(payload)
        
        # Submit to chain
        tx_hash = submitter.submit_risk(signed)
        
        return {
            "success": True,
            "pool_id": request.pool_id,
            "risk_score": result['risk_score'],
            "tx_hash": tx_hash,
            "explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/submissions")
async def get_submissions(pool_id: Optional[str] = None):
    """Get risk submission history"""
    db = next(get_db())
    try:
        query = db.query(RiskSubmission)
        if pool_id:
            query = query.filter(RiskSubmission.pool_id == pool_id)
        
        submissions = query.order_by(RiskSubmission.timestamp.desc()).limit(50).all()
        
        return [
            {
                "pool_id": s.pool_id,
                "risk_score": s.risk_score,
                "timestamp": s.timestamp.isoformat(),
                "tx_hash": s.tx_hash,
                "status": s.status,
                "top_reasons": s.top_reasons
            }
            for s in submissions
        ]
    finally:
        db.close()

@app.get("/snapshots")
async def get_snapshots(pool_id: Optional[str] = None, limit: int = 50):
    """Get data snapshots"""
    db = next(get_db())
    try:
        query = db.query(Snapshot)
        if pool_id:
            query = query.filter(Snapshot.pool_id == pool_id)
        
        snapshots = query.order_by(Snapshot.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "snapshot_id": s.snapshot_id,
                "pool_id": s.pool_id,
                "timestamp": s.timestamp.isoformat(),
                "tvl": s.tvl,
                "volume_24h": s.volume_24h,
                "features": s.features,
                "source": s.source
            }
            for s in snapshots
        ]
    finally:
        db.close()

@app.get("/protocols")
async def get_protocols():
    """Get list of all monitored protocols"""
    db = next(get_db())
    try:
        # Get unique pool_ids with their latest data
        from sqlalchemy import func
        
        subquery = db.query(
            Snapshot.pool_id,
            func.max(Snapshot.timestamp).label('latest_timestamp')
        ).group_by(Snapshot.pool_id).subquery()
        
        snapshots = db.query(Snapshot).join(
            subquery,
            (Snapshot.pool_id == subquery.c.pool_id) & 
            (Snapshot.timestamp == subquery.c.latest_timestamp)
        ).all()
        
        protocols = []
        for s in snapshots:
            # Determine protocol type and display name
            pool_id = s.pool_id
            if 'uniswap_v2' in pool_id:
                protocol_type = 'Uniswap V2'
                category = 'DEX'
            elif 'uniswap_v3' in pool_id:
                protocol_type = 'Uniswap V3'
                category = 'DEX'
            elif 'aave' in pool_id:
                protocol_type = 'Aave V3'
                category = 'Lending'
            elif 'compound' in pool_id:
                protocol_type = 'Compound V2'
                category = 'Lending'
            elif 'curve' in pool_id:
                protocol_type = 'Curve'
                category = 'DEX'
            else:
                protocol_type = s.source or 'Unknown'
                category = 'Other'
            
            # Extract asset name from pool_id for better display
            asset_name = pool_id.split('_')[-1].upper() if '_' in pool_id else pool_id
            if 'uniswap' in pool_id:
                # For uniswap pools, construct pair name
                parts = pool_id.replace('uniswap_v2_', '').replace('uniswap_v3_', '').split('_')
                asset_name = '-'.join([p.upper() for p in parts])
            
            # Check if data is from live source
            features = s.features if isinstance(s.features, dict) else {}
            is_synthetic = features.get('synthetic', s.source == 'synthetic')
            
            protocols.append({
                'pool_id': pool_id,
                'protocol': protocol_type,
                'category': category,
                'asset': asset_name,
                'tvl': s.tvl,
                'volume_24h': s.volume_24h,
                'last_update': s.timestamp.isoformat(),
                'data_source': 'live' if not is_synthetic else 'synthetic'
            })
        
        return protocols
    finally:
        db.close()

@app.post("/fetch_protocols")
async def fetch_protocols():
    """Trigger fetch for all protocols"""
    from data_fetcher import DataFetcher
    try:
        fetcher = DataFetcher()
        snapshot_ids = fetcher.fetch_all_protocols()
        return {
            "success": True,
            "message": f"Fetched data for {len(snapshot_ids)} protocols",
            "snapshot_ids": snapshot_ids
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
