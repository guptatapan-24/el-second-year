#!/usr/bin/env python3
"""
Risk API Router for VeriRisk Phase 3 & 5

Clean, minimal APIs for demonstration and evaluation:
- GET /api/risk/latest/{pool_id} - Latest risk score, level, explanations
- GET /api/risk/history/{pool_id} - Chronological risk evolution
- GET /api/alerts - Active alerts across all protocols
- GET /api/alerts/{pool_id} - Alerts for specific pool
- GET /api/risk/summary - Risk summary across all pools
- POST /api/simulate - Run what-if risk simulation (Phase 5)

No authentication required. JSON responses only.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.risk_evaluator import RiskEvaluator, get_risk_evaluator
from services.simulation_service import get_simulation_service
from services.explainability_service import enhance_risk_response_with_explainability
from database import SessionLocal
from db_models.risk_history import RiskHistory
from db_models.alert import Alert
from sqlalchemy import desc, func

router = APIRouter(prefix="/risk")
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


# ----- Pydantic Response Models -----

class ReasonResponse(BaseModel):
    feature: str
    impact: float
    direction: str
    explanation: Optional[str] = None
    readable_name: Optional[str] = None
    description: Optional[str] = None


class ExplainabilityResponse(BaseModel):
    summary: str
    top_factors: List[str]
    risk_direction_hint: str


class LatestRiskResponse(BaseModel):
    pool_id: str
    risk_score: float
    risk_level: str
    early_warning_score: Optional[float]
    top_reasons: List[Dict]
    model_version: Optional[str]
    prediction_horizon: Optional[str]
    timestamp: str
    # Phase 6: Explainability additions
    confidence: Optional[str] = None
    confidence_reason: Optional[str] = None
    explainability: Optional[ExplainabilityResponse] = None
    enhanced_top_reasons: Optional[List[Dict]] = None


class RiskHistoryItemResponse(BaseModel):
    risk_score: float
    risk_level: str
    early_warning_score: Optional[float]
    top_reasons: List[Dict]
    timestamp: str


class RiskHistoryResponse(BaseModel):
    pool_id: str
    records: List[RiskHistoryItemResponse]
    count: int
    oldest: Optional[str]
    newest: Optional[str]


class AlertResponse(BaseModel):
    id: int
    pool_id: str
    alert_type: str
    risk_score: float
    risk_level: str
    message: str
    top_reasons: Optional[List[Dict]]
    status: str
    previous_risk_level: Optional[str]
    previous_risk_score: Optional[float]
    created_at: str


class AlertsListResponse(BaseModel):
    alerts: List[AlertResponse]
    count: int


class PoolRiskSummary(BaseModel):
    pool_id: str
    latest_risk_score: float
    latest_risk_level: str
    active_alerts: int
    tvl: float = 0  # Added TVL field


class RiskSummaryResponse(BaseModel):
    total_pools: int
    high_risk_pools: int
    medium_risk_pools: int
    low_risk_pools: int
    total_active_alerts: int
    total_tvl: float = 0  # Added total TVL
    pools: List[PoolRiskSummary]
    timestamp: str


# ----- Endpoints -----

@router.get("/latest/{pool_id}", response_model=LatestRiskResponse)
def get_latest_risk(pool_id: str):
    """
    Get the latest risk score, level, and SHAP explanations for a pool.
    
    Returns:
    - risk_score: 0-100 probability of future risk
    - risk_level: LOW (<30), MEDIUM (30-65), HIGH (>65)
    - early_warning_score: Composite early warning signal
    - top_reasons: Top 3 SHAP-based contributing features
    - confidence: HIGH/MEDIUM/LOW prediction confidence
    - explainability: Natural language explanation of risk factors
    """
    evaluator = get_risk_evaluator()
    result = evaluator.get_latest_risk(pool_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No risk data found for pool: {pool_id}"
        )
    
    # Enhance with explainability (Phase 6)
    enhanced_result = enhance_risk_response_with_explainability(result)
    
    # Build explainability response
    explainability_data = enhanced_result.get('explainability', {})
    explainability_response = ExplainabilityResponse(
        summary=explainability_data.get('summary', ''),
        top_factors=explainability_data.get('top_factors', []),
        risk_direction_hint=explainability_data.get('risk_direction_hint', '')
    ) if explainability_data else None
    
    return LatestRiskResponse(
        pool_id=enhanced_result['pool_id'],
        risk_score=enhanced_result['risk_score'],
        risk_level=enhanced_result['risk_level'],
        early_warning_score=enhanced_result.get('early_warning_score'),
        top_reasons=enhanced_result.get('top_reasons') or [],
        model_version=enhanced_result.get('model_version'),
        prediction_horizon=enhanced_result.get('prediction_horizon'),
        timestamp=enhanced_result['timestamp'],
        confidence=enhanced_result.get('confidence'),
        confidence_reason=enhanced_result.get('confidence_reason'),
        explainability=explainability_response,
        enhanced_top_reasons=enhanced_result.get('enhanced_top_reasons')
    )


@router.get("/history/{pool_id}", response_model=RiskHistoryResponse)
def get_risk_history(
    pool_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history")
):
    """
    Get chronological risk evolution for a pool.
    
    Shows how risk score and level have changed over time,
    enabling trend analysis and escalation detection.
    """
    evaluator = get_risk_evaluator()
    records = evaluator.get_risk_history(pool_id, hours=hours)
    
    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"No risk history found for pool: {pool_id}"
        )
    
    items = [
        RiskHistoryItemResponse(
            risk_score=r['risk_score'],
            risk_level=r['risk_level'],
            early_warning_score=r['early_warning_score'],
            top_reasons=r['top_reasons'] or [],
            timestamp=r['timestamp']
        )
        for r in records
    ]
    
    return RiskHistoryResponse(
        pool_id=pool_id,
        records=items,
        count=len(items),
        oldest=items[0].timestamp if items else None,
        newest=items[-1].timestamp if items else None
    )


@router.get("/alerts", response_model=AlertsListResponse)
def get_alerts(
    status: str = Query(default="active", description="Filter by status"),
    pool_id: Optional[str] = Query(default=None, description="Filter by pool")
):
    """
    Get alerts across all protocols.
    
    Alert Types:
    - HIGH_RISK_ALERT: Risk score >= 65
    - EARLY_WARNING_ALERT: Early warning score >= 40
    - RISK_ESCALATION_ALERT: Risk level increased
    """
    db = SessionLocal()
    try:
        query = db.query(Alert)
        
        if status:
            query = query.filter(Alert.status == status)
        if pool_id:
            query = query.filter(Alert.pool_id == pool_id)
        
        alerts = query.order_by(desc(Alert.created_at)).all()
        
        items = [
            AlertResponse(
                id=a.id,
                pool_id=a.pool_id,
                alert_type=a.alert_type,
                risk_score=a.risk_score,
                risk_level=a.risk_level,
                message=a.message,
                top_reasons=a.top_reasons,
                status=a.status,
                previous_risk_level=a.previous_risk_level,
                previous_risk_score=a.previous_risk_score,
                created_at=a.created_at.isoformat()
            )
            for a in alerts
        ]
        
        return AlertsListResponse(alerts=items, count=len(items))
        
    finally:
        db.close()


@router.get("/summary", response_model=RiskSummaryResponse)
def get_risk_summary():
    """
    Get risk summary across all monitored pools.
    
    Provides overview for demo presentation:
    - Count of pools by risk level
    - Total active alerts
    - Per-pool summary with TVL
    
    Filters to only show the 28 expected protocols.
    """
    # Exact pool IDs expected (28 total)
    EXPECTED_POOL_IDS = {
        # Real DeFi protocols (18 pools)
        # Uniswap V2 (4)
        'uniswap_v2_usdc_eth',
        'uniswap_v2_dai_eth',
        'uniswap_v2_usdt_eth',
        'uniswap_v2_wbtc_eth',
        # Uniswap V3 (3)
        'uniswap_v3_usdc_eth_0.3pct',
        'uniswap_v3_usdc_eth_0.05pct',
        'uniswap_v3_dai_usdc_0.01pct',
        # Aave V3 (4)
        'aave_v3_eth',
        'aave_v3_usdc',
        'aave_v3_dai',
        'aave_v3_wbtc',
        # Compound V2 (4)
        'compound_v2_eth',
        'compound_v2_usdc',
        'compound_v2_dai',
        'compound_v2_usdt',
        # Curve (3)
        'curve_3pool',
        'curve_steth',
        'curve_frax',
        # Synthetic pools for training (10 pools)
        'synthetic_pool_1',
        'synthetic_pool_2',
        'synthetic_uniswap_v2',
        'synthetic_aave_v3',
        'synthetic_curve',
        'high_risk_pool',
        'critical_risk_pool',
        'late_crash_pool_1',
        'late_crash_pool_2',
        'late_crash_pool_3',
    }
    
    def is_expected_pool(pool_id: str) -> bool:
        return pool_id in EXPECTED_POOL_IDS
    
    db = SessionLocal()
    try:
        # Get latest risk for each pool using subquery
        from sqlalchemy import func
        from database import Snapshot
        
        subq = (
            db.query(
                RiskHistory.pool_id,
                func.max(RiskHistory.timestamp).label('max_ts')
            )
            .group_by(RiskHistory.pool_id)
            .subquery()
        )
        
        latest_risks = (
            db.query(RiskHistory)
            .join(
                subq,
                (RiskHistory.pool_id == subq.c.pool_id) &
                (RiskHistory.timestamp == subq.c.max_ts)
            )
            .all()
        )
        
        # Filter to expected pools
        latest_risks = [r for r in latest_risks if is_expected_pool(r.pool_id)]
        
        # Get latest TVL for each pool from Snapshot table
        tvl_subq = (
            db.query(
                Snapshot.pool_id,
                func.max(Snapshot.timestamp).label('max_ts')
            )
            .group_by(Snapshot.pool_id)
            .subquery()
        )
        
        latest_snapshots = (
            db.query(Snapshot.pool_id, Snapshot.tvl)
            .join(
                tvl_subq,
                (Snapshot.pool_id == tvl_subq.c.pool_id) &
                (Snapshot.timestamp == tvl_subq.c.max_ts)
            )
            .all()
        )
        
        # Create TVL lookup map (filtered)
        tvl_by_pool = {s.pool_id: s.tvl or 0 for s in latest_snapshots if is_expected_pool(s.pool_id)}
        
        # Count by risk level
        high_count = sum(1 for r in latest_risks if r.risk_level == 'HIGH')
        medium_count = sum(1 for r in latest_risks if r.risk_level == 'MEDIUM')
        low_count = sum(1 for r in latest_risks if r.risk_level == 'LOW')
        
        # Count active alerts per pool
        alert_counts = (
            db.query(Alert.pool_id, func.count(Alert.id).label('count'))
            .filter(Alert.status == 'active')
            .group_by(Alert.pool_id)
            .all()
        )
        alert_by_pool = {p: c for p, c in alert_counts if is_expected_pool(p)}
        
        total_alerts = sum(alert_by_pool.values())
        
        # Calculate total TVL
        total_tvl = sum(tvl_by_pool.values())
        
        # Build pool summaries with TVL
        pools = [
            PoolRiskSummary(
                pool_id=r.pool_id,
                latest_risk_score=r.risk_score,
                latest_risk_level=r.risk_level,
                active_alerts=alert_by_pool.get(r.pool_id, 0),
                tvl=tvl_by_pool.get(r.pool_id, 0)
            )
            for r in sorted(latest_risks, key=lambda x: x.risk_score, reverse=True)
        ]
        
        return RiskSummaryResponse(
            total_pools=len(latest_risks),
            high_risk_pools=high_count,
            medium_risk_pools=medium_count,
            low_risk_pools=low_count,
            total_active_alerts=total_alerts,
            total_tvl=total_tvl,
            pools=pools,
            timestamp=datetime.utcnow().isoformat()
        )
        
    finally:
        db.close()


@router.post("/predict/{pool_id}")
def trigger_prediction(pool_id: str):
    """
    Manually trigger risk prediction for a pool.
    
    Useful for demo: forces immediate prediction and alert evaluation.
    """
    evaluator = get_risk_evaluator()
    
    # Predict and store
    result = evaluator.predict_and_store_risk(pool_id)
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to predict risk for pool: {pool_id}"
        )
    
    # Evaluate alerts
    alerts = evaluator.evaluate_alerts_for_pool(pool_id, result)
    
    return {
        "status": "success",
        "pool_id": pool_id,
        "risk_score": result['risk_score'],
        "risk_level": result['risk_level'],
        "alerts_generated": len(alerts),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/predict-all")
def trigger_all_predictions():
    """
    Manually trigger risk prediction for all pools.
    
    Useful for demo: forces immediate full pipeline run.
    """
    evaluator = get_risk_evaluator()
    
    # Predict all
    results = evaluator.predict_all_pools()
    
    # Evaluate all alerts
    alerts = evaluator.evaluate_all_alerts()
    
    return {
        "status": "success",
        "pools_predicted": len(results),
        "alerts_generated": len(alerts),
        "timestamp": datetime.utcnow().isoformat()
    }



# ----- Phase 5: Simulation Endpoints -----

class SimulationRequest(BaseModel):
    """Request body for risk simulation"""
    pool_id: str = Field(..., description="Pool identifier to simulate")
    tvl_change_pct: float = Field(default=0, ge=-80, le=80, description="TVL change percentage (-80 to +80)")
    volume_change_pct: float = Field(default=0, ge=-100, le=200, description="Volume change percentage (-100 to +200)")
    volatility_override: Optional[float] = Field(default=None, ge=0.01, le=0.5, description="Override volatility (0.01-0.5)")
    reserve_imbalance_override: Optional[float] = Field(default=None, ge=0, le=1, description="Override reserve imbalance (0-1)")


class RiskDetail(BaseModel):
    """Risk score details"""
    score: float
    level: str
    early_warning_score: Optional[float] = None


class FeatureChange(BaseModel):
    """Feature value before and after simulation"""
    before: float
    after: float


class SimulationResponse(BaseModel):
    """Response from risk simulation"""
    pool_id: str
    timestamp: str
    simulation_params: Dict
    actual_risk: RiskDetail
    simulated_risk: RiskDetail
    delta: float
    risk_increased: bool
    alert_would_trigger: bool
    top_risk_factors: List[Dict]
    feature_changes: Dict[str, FeatureChange]


@router.post("/simulate", response_model=SimulationResponse)
def run_simulation(request: SimulationRequest):
    """
    Run what-if risk simulation for a protocol.
    
    Phase 5 Feature: Allows injecting hypothetical shocks into protocol features
    and re-running ML inference to see predicted impact.
    
    **Simulation Parameters:**
    - `tvl_change_pct`: Simulate TVL increase/decrease (-80% to +80%)
    - `volume_change_pct`: Simulate volume spike/drop (-100% to +200%)
    - `volatility_override`: Override current volatility (0.01 to 0.5)
    - `reserve_imbalance_override`: Override reserve imbalance (0 to 1)
    
    **Processing Steps:**
    1. Fetch latest snapshot for pool
    2. Apply simulated deltas to feature values
    3. Re-run ML risk prediction
    4. Compare simulated vs actual risk
    
    **Note:** Simulation is stateless - no data is persisted.
    
    **Example Use Cases:**
    - "What if TVL drops 50%?" → tvl_change_pct=-50
    - "What if volume spikes 150%?" → volume_change_pct=150
    - "What if volatility increases to 0.3?" → volatility_override=0.3
    """
    simulation_service = get_simulation_service()
    
    result = simulation_service.run_simulation(
        pool_id=request.pool_id,
        tvl_change_pct=request.tvl_change_pct,
        volume_change_pct=request.volume_change_pct,
        volatility_override=request.volatility_override,
        reserve_imbalance_override=request.reserve_imbalance_override
    )
    
    if 'error' in result:
        raise HTTPException(
            status_code=404 if "No data found" in result['error'] else 500,
            detail=result['error']
        )
    
    return result


@router.get("/simulate/presets")
def get_simulation_presets():
    """
    Get predefined simulation scenarios for demo purposes.
    
    Returns common DeFi crisis scenarios that can be tested.
    """
    return {
        "presets": [
            {
                "id": "tvl_crash",
                "name": "TVL Crash",
                "description": "Simulate a 50% sudden drop in Total Value Locked",
                "params": {
                    "tvl_change_pct": -50,
                    "volume_change_pct": 50
                },
                "severity": "HIGH",
                "real_world_example": "Terra/Luna collapse"
            },
            {
                "id": "bank_run",
                "name": "Bank Run",
                "description": "Simulate mass withdrawal scenario",
                "params": {
                    "tvl_change_pct": -70,
                    "volume_change_pct": 200
                },
                "severity": "CRITICAL",
                "real_world_example": "FTX withdrawal panic"
            },
            {
                "id": "volume_spike",
                "name": "Volume Spike",
                "description": "Simulate unusual trading activity surge",
                "params": {
                    "tvl_change_pct": -10,
                    "volume_change_pct": 150
                },
                "severity": "MEDIUM",
                "real_world_example": "Pre-crash trading activity"
            },
            {
                "id": "liquidity_imbalance",
                "name": "Liquidity Imbalance",
                "description": "Simulate severe pool imbalance",
                "params": {
                    "tvl_change_pct": -20,
                    "reserve_imbalance_override": 0.6
                },
                "severity": "HIGH",
                "real_world_example": "Curve pool depeg"
            },
            {
                "id": "volatility_surge",
                "name": "Volatility Surge",
                "description": "Simulate market volatility spike",
                "params": {
                    "tvl_change_pct": -15,
                    "volatility_override": 0.35
                },
                "severity": "MEDIUM",
                "real_world_example": "Black swan event"
            },
            {
                "id": "healthy_growth",
                "name": "Healthy Growth",
                "description": "Simulate positive protocol growth",
                "params": {
                    "tvl_change_pct": 30,
                    "volume_change_pct": 20
                },
                "severity": "LOW",
                "real_world_example": "Bull market inflow"
            }
        ],
        "timestamp": datetime.utcnow().isoformat()
    }