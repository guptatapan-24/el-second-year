#!/usr/bin/env python3
"""
Time-Series API Router

Exposes Phase 1 time-series features via REST API endpoints:
- Get snapshot history for a pool
- Compute time-series features
- Get all pool features in batch
- Get system status
- Seed historical data
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel

from features.basic_timeseries import TimeSeriesFeatureEngine, TimeSeriesFeatures
from jobs.hourly_snapshot import HourlySnapshotCollector
from db_models.snapshot_history import SnapshotHistory
from database import SessionLocal
from sqlalchemy import and_, desc, func

router = APIRouter(prefix="/timeseries")


# ----- Pydantic Models -----

class FeatureResponse(BaseModel):
    pool_id: str
    timestamp: str
    features: Dict
    data_quality: Dict
    risk_signals: List[Dict]


class PoolHistoryResponse(BaseModel):
    pool_id: str
    records: List[Dict]
    count: int


class SystemStatusResponse(BaseModel):
    total_records: int
    unique_pools: int
    oldest_record: Optional[str]
    newest_record: Optional[str]
    records_by_source: Dict[str, int]
    pools: List[Dict]


class SeedResponse(BaseModel):
    success: bool
    records_created: int
    message: str


class CollectResponse(BaseModel):
    success: bool
    pools_collected: int
    pool_ids: List[str]


# ----- Global instances -----

feature_engine = TimeSeriesFeatureEngine()
collector = HourlySnapshotCollector()


# ----- Endpoints -----

@router.get("/features/{pool_id}", response_model=FeatureResponse)
def get_pool_features(pool_id: str):
    """
    Compute and return time-series features for a specific pool.
    
    Features computed:
    - tvl_pct_change_6h: 6-hour TVL percentage change
    - tvl_pct_change_24h: 24-hour TVL percentage change  
    - tvl_acceleration: Rate of change of TVL change (panic detection)
    - volume_spike_ratio: Current volume vs 24h average
    - reserve_imbalance: Liquidity skew ratio
    """
    features = feature_engine.compute_features(pool_id)
    
    return FeatureResponse(
        pool_id=features.pool_id,
        timestamp=features.timestamp.isoformat() if features.timestamp else None,
        features={
            'tvl_pct_change_6h': features.tvl_pct_change_6h,
            'tvl_pct_change_24h': features.tvl_pct_change_24h,
            'tvl_acceleration': features.tvl_acceleration,
            'volume_spike_ratio': features.volume_spike_ratio,
            'reserve_imbalance': features.reserve_imbalance,
        },
        data_quality={
            'data_points_available': features.data_points_available,
            'sufficient_data': features.sufficient_data,
            'warnings': features.warnings
        },
        risk_signals=features.get_risk_signals()
    )


@router.get("/features", response_model=Dict[str, FeatureResponse])
def get_all_features():
    """
    Compute and return time-series features for all pools.
    """
    pool_ids = feature_engine.get_all_pool_ids()
    result = {}
    
    for pool_id in pool_ids:
        features = feature_engine.compute_features(pool_id)
        result[pool_id] = FeatureResponse(
            pool_id=features.pool_id,
            timestamp=features.timestamp.isoformat() if features.timestamp else None,
            features={
                'tvl_pct_change_6h': features.tvl_pct_change_6h,
                'tvl_pct_change_24h': features.tvl_pct_change_24h,
                'tvl_acceleration': features.tvl_acceleration,
                'volume_spike_ratio': features.volume_spike_ratio,
                'reserve_imbalance': features.reserve_imbalance,
            },
            data_quality={
                'data_points_available': features.data_points_available,
                'sufficient_data': features.sufficient_data,
                'warnings': features.warnings
            },
            risk_signals=features.get_risk_signals()
        )
    
    return result


@router.get("/history/{pool_id}", response_model=PoolHistoryResponse)
def get_pool_history(
    pool_id: str,
    hours: int = Query(default=24, ge=1, le=168, description="Hours of history to retrieve")
):
    """
    Get historical snapshots for a specific pool.
    """
    from datetime import timedelta
    
    db = SessionLocal()
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        snapshots = db.query(SnapshotHistory).filter(
            and_(
                SnapshotHistory.pool_id == pool_id,
                SnapshotHistory.timestamp >= start_time
            )
        ).order_by(desc(SnapshotHistory.timestamp)).all()
        
        records = [
            {
                'timestamp': s.timestamp.isoformat(),
                'tvl': s.tvl,
                'volume_24h': s.volume_24h,
                'reserve0': s.reserve0,
                'reserve1': s.reserve1,
                'source': s.source
            }
            for s in snapshots
        ]
        
        return PoolHistoryResponse(
            pool_id=pool_id,
            records=records,
            count=len(records)
        )
    finally:
        db.close()


@router.get("/status", response_model=SystemStatusResponse)
def get_timeseries_status():
    """
    Get overall time-series system status.
    """
    db = SessionLocal()
    try:
        # Total records
        total_count = db.query(func.count(SnapshotHistory.id)).scalar()
        
        # Unique pools
        pool_count = db.query(func.count(func.distinct(SnapshotHistory.pool_id))).scalar()
        
        # Time range
        oldest = db.query(func.min(SnapshotHistory.timestamp)).scalar()
        newest = db.query(func.max(SnapshotHistory.timestamp)).scalar()
        
        # Records by source
        source_counts = db.query(
            SnapshotHistory.source,
            func.count(SnapshotHistory.id)
        ).group_by(SnapshotHistory.source).all()
        
        records_by_source = {source or 'unknown': count for source, count in source_counts}
        
        # Per-pool stats
        pool_stats = db.query(
            SnapshotHistory.pool_id,
            func.count(SnapshotHistory.id).label('count'),
            func.min(SnapshotHistory.timestamp).label('oldest'),
            func.max(SnapshotHistory.timestamp).label('newest')
        ).group_by(SnapshotHistory.pool_id).all()
        
        pools = []
        for stat in pool_stats:
            if stat.oldest and stat.newest:
                hours_span = (stat.newest - stat.oldest).total_seconds() / 3600
            else:
                hours_span = 0
            
            pools.append({
                'pool_id': stat.pool_id,
                'record_count': stat.count,
                'hours_span': round(hours_span, 1),
                'ready_for_24h_analysis': stat.count >= 24
            })
        
        return SystemStatusResponse(
            total_records=total_count or 0,
            unique_pools=pool_count or 0,
            oldest_record=oldest.isoformat() if oldest else None,
            newest_record=newest.isoformat() if newest else None,
            records_by_source=records_by_source,
            pools=pools
        )
    finally:
        db.close()


@router.post("/seed", response_model=SeedResponse)
def seed_historical_data(hours: int = Query(default=48, ge=1, le=168)):
    """
    Seed synthetic historical data for testing and immediate feature computation.
    
    This populates the snapshot_history table with realistic historical data,
    enabling immediate feature computation for demonstration purposes.
    """
    try:
        records = collector.seed_historical_data(hours=hours)
        return SeedResponse(
            success=True,
            records_created=records,
            message=f"Successfully seeded {records} historical records for {hours} hours"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collect", response_model=CollectResponse)
def collect_now():
    """
    Trigger immediate hourly snapshot collection from live DeFiLlama APIs.
    """
    try:
        pool_ids = collector.collect_hourly_snapshot()
        return CollectResponse(
            success=True,
            pools_collected=len(pool_ids),
            pool_ids=pool_ids
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pools")
def get_all_pools():
    """
    Get list of all pools with time-series data available.
    """
    pool_ids = feature_engine.get_all_pool_ids()
    return {
        'count': len(pool_ids),
        'pools': pool_ids
    }


@router.get("/risk-signals")
def get_risk_signals():
    """
    Get all current risk signals across all pools.
    
    Returns only pools with active risk conditions.
    """
    pool_ids = feature_engine.get_all_pool_ids()
    all_signals = []
    
    for pool_id in pool_ids:
        features = feature_engine.compute_features(pool_id)
        signals = features.get_risk_signals()
        
        if signals:
            all_signals.append({
                'pool_id': pool_id,
                'timestamp': features.timestamp.isoformat() if features.timestamp else None,
                'signals': signals
            })
    
    return {
        'total_signals': sum(len(s['signals']) for s in all_signals),
        'pools_with_signals': len(all_signals),
        'details': all_signals
    }
