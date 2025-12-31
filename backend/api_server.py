#!/usr/bin/env python3
"""FastAPI server for VeriRisk backend"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
from routers import protocols_router, submissions_router

from model_server import ModelServer
from signer import PayloadSigner
from submit_to_chain import ChainSubmitter
from database import get_db, init_db, Snapshot, RiskSubmission
from config import config
from scheduler import RiskScheduler
scheduler_started = False
# Initialize FastAPI
app = FastAPI(
    title="VeriRisk API",
    description="Verifiable AI Risk Oracle for DeFi",
    version="1.0.0",
    # root_path=\"/api\"  # ADD THIS
)
app.include_router(protocols_router, prefix="/api")
app.include_router(submissions_router, prefix="/api")

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
scheduler = None

@app.on_event("startup")
async def startup_event():
    global model_server, signer, submitter, scheduler, scheduler_started

    if scheduler_started:
        return
    scheduler_started = True
    
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
    
    # Initialize and start scheduler
    try:
        scheduler = RiskScheduler()
        from scheduler import set_global_scheduler
        set_global_scheduler(scheduler)
        scheduler.start()

        print(f"Scheduler started - Auto-fetching every 5 minutes")
    except Exception as e:
        print(f"Warning: Scheduler not started: {e}")

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
    db = next(get_db())
    try:
        # Check data freshness
        latest_snapshot = db.query(Snapshot).order_by(Snapshot.timestamp.desc()).first()
        data_age_seconds = None
        data_status = "no_data"
        
        if latest_snapshot:
            from datetime import timedelta
            age = datetime.utcnow() - latest_snapshot.timestamp
            data_age_seconds = age.total_seconds()
            
            if data_age_seconds < 600:  # < 10 minutes
                data_status = "fresh"
            elif data_age_seconds < 3600:  # < 1 hour
                data_status = "stale"
            else:
                data_status = "very_stale"
        
        # Count live vs synthetic data
        recent_snapshots = db.query(Snapshot).order_by(Snapshot.timestamp.desc()).limit(50).all()
        live_count = sum(1 for s in recent_snapshots if isinstance(s.features, dict) and not s.features.get('synthetic', s.source == 'synthetic'))
        total_count = len(recent_snapshots)
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "model_server": model_server is not None,
                "signer": signer is not None,
                "submitter": submitter is not None,
                "scheduler": scheduler is not None and scheduler.scheduler.running if scheduler else False
            },
            "data_status": {
                "status": data_status,
                "latest_snapshot_age_seconds": data_age_seconds,
                "latest_snapshot_time": latest_snapshot.timestamp.isoformat() if latest_snapshot else None,
                "recent_snapshots": {
                    "total": total_count,
                    "live_data": live_count,
                    "synthetic_data": total_count - live_count,
                    "live_percentage": round(live_count / total_count * 100, 1) if total_count > 0 else 0
                }
            }
        }
    finally:
        db.close()

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



