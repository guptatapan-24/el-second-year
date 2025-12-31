#!/usr/bin/env python3
"""
Basic Time-Series Feature Engineering Module

This module computes derived time-series features for DeFi risk assessment.
All features are computed using rolling windows WITHOUT machine learning,
ensuring clean feature derivation without data leakage.

Features Computed:
1. tvl_pct_change_6h  - 6-hour TVL percentage change (capital outflow trend)
2. tvl_pct_change_24h - 24-hour TVL percentage change (daily liquidity movement)
3. tvl_acceleration   - Rate of change of TVL change (panic detection)
4. volume_spike_ratio - Current volume vs 24h average (unusual activity)
5. reserve_imbalance  - Liquidity skew ratio (manipulation risk)

Academic Keywords:
- Rolling window analysis
- Predictive signal extraction
- Data leakage prevention
- DeFi protocol monitoring
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import and_, desc

from database import SessionLocal
from db_models.snapshot_history import SnapshotHistory

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesFeatures:
    """
    Container for computed time-series features.
    
    All features are designed to be ML-ready without leakage:
    - Only uses past data (no future information)
    - Normalized/bounded values for model stability
    - Clear risk signal interpretation
    """
    pool_id: str
    timestamp: datetime
    
    # TVL Change Features
    tvl_pct_change_6h: Optional[float] = None   # Capital outflow trend
    tvl_pct_change_24h: Optional[float] = None  # Daily liquidity movement
    tvl_acceleration: Optional[float] = None    # Panic indicator (Δ of ΔTVL)
    
    # Volume Features
    volume_spike_ratio: Optional[float] = None  # Unusual trading activity
    
    # Reserve Features
    reserve_imbalance: Optional[float] = None   # Liquidity skew / manipulation risk
    
    # Data Quality Flags
    data_points_available: int = 0
    sufficient_data: bool = False
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'pool_id': self.pool_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'features': {
                'tvl_pct_change_6h': self.tvl_pct_change_6h,
                'tvl_pct_change_24h': self.tvl_pct_change_24h,
                'tvl_acceleration': self.tvl_acceleration,
                'volume_spike_ratio': self.volume_spike_ratio,
                'reserve_imbalance': self.reserve_imbalance,
            },
            'data_quality': {
                'data_points_available': self.data_points_available,
                'sufficient_data': self.sufficient_data,
                'warnings': self.warnings
            }
        }
    
    def get_risk_signals(self) -> List[Dict]:
        """
        Interpret features as risk signals.
        
        Returns list of detected risk conditions with severity.
        """
        signals = []
        
        # TVL drop signals
        if self.tvl_pct_change_6h is not None and self.tvl_pct_change_6h < -0.10:
            signals.append({
                'signal': 'tvl_drop_6h',
                'severity': 'high' if self.tvl_pct_change_6h < -0.20 else 'medium',
                'value': self.tvl_pct_change_6h,
                'description': f'TVL dropped {abs(self.tvl_pct_change_6h)*100:.1f}% in 6 hours'
            })
        
        if self.tvl_pct_change_24h is not None and self.tvl_pct_change_24h < -0.15:
            signals.append({
                'signal': 'tvl_drop_24h',
                'severity': 'high' if self.tvl_pct_change_24h < -0.30 else 'medium',
                'value': self.tvl_pct_change_24h,
                'description': f'TVL dropped {abs(self.tvl_pct_change_24h)*100:.1f}% in 24 hours'
            })
        
        # Acceleration signal (panic)
        if self.tvl_acceleration is not None and self.tvl_acceleration < -0.05:
            signals.append({
                'signal': 'accelerating_outflow',
                'severity': 'critical' if self.tvl_acceleration < -0.10 else 'high',
                'value': self.tvl_acceleration,
                'description': 'Accelerating capital outflow detected (potential panic)'
            })
        
        # Volume spike
        if self.volume_spike_ratio is not None and self.volume_spike_ratio > 3.0:
            signals.append({
                'signal': 'volume_spike',
                'severity': 'high' if self.volume_spike_ratio > 5.0 else 'medium',
                'value': self.volume_spike_ratio,
                'description': f'Volume is {self.volume_spike_ratio:.1f}x higher than 24h average'
            })
        
        # Reserve imbalance
        if self.reserve_imbalance is not None and self.reserve_imbalance > 0.3:
            signals.append({
                'signal': 'reserve_imbalance',
                'severity': 'high' if self.reserve_imbalance > 0.5 else 'medium',
                'value': self.reserve_imbalance,
                'description': f'Reserve imbalance of {self.reserve_imbalance*100:.1f}% detected'
            })
        
        return signals


class TimeSeriesFeatureEngine:
    """
    Engine for computing time-series features from historical snapshots.
    
    Design Principles:
    - No data leakage: Only uses past data relative to computation time
    - Robust to missing data: Graceful degradation with warnings
    - Bounded outputs: Features are normalized for ML readiness
    """
    
    # Window sizes for rolling computations
    WINDOW_6H = 6
    WINDOW_24H = 24
    
    # Minimum data points required
    MIN_POINTS_6H = 4   # At least 4 of 6 hours
    MIN_POINTS_24H = 18 # At least 18 of 24 hours
    
    def __init__(self):
        logger.info("✓ TimeSeriesFeatureEngine initialized")
    
    def compute_features(self, pool_id: str, 
                         as_of: Optional[datetime] = None) -> TimeSeriesFeatures:
        """
        Compute all time-series features for a pool.
        
        Args:
            pool_id: Protocol pool identifier
            as_of: Compute features as of this time (default: now)
            
        Returns:
            TimeSeriesFeatures with computed values and quality flags
        """
        if as_of is None:
            as_of = datetime.utcnow()
        
        # Round to hour for consistency
        as_of = self._round_to_hour(as_of)
        
        # Initialize result
        features = TimeSeriesFeatures(
            pool_id=pool_id,
            timestamp=as_of
        )
        
        # Fetch historical data
        history = self._get_history(pool_id, hours=self.WINDOW_24H, as_of=as_of)
        features.data_points_available = len(history)
        
        if len(history) < self.MIN_POINTS_6H:
            features.warnings.append(
                f"Insufficient data: {len(history)} points (need {self.MIN_POINTS_6H})"
            )
            features.sufficient_data = False
            return features
        
        features.sufficient_data = len(history) >= self.MIN_POINTS_24H
        
        # Compute TVL change features
        features.tvl_pct_change_6h = self._compute_tvl_pct_change(
            history, hours=self.WINDOW_6H
        )
        features.tvl_pct_change_24h = self._compute_tvl_pct_change(
            history, hours=self.WINDOW_24H
        )
        
        # Compute acceleration
        features.tvl_acceleration = self._compute_tvl_acceleration(history)
        
        # Compute volume spike ratio
        features.volume_spike_ratio = self._compute_volume_spike_ratio(history)
        
        # Compute reserve imbalance (from latest snapshot)
        if history:
            latest = history[0]  # Most recent
            features.reserve_imbalance = self._compute_reserve_imbalance(
                latest.reserve0, latest.reserve1
            )
        
        # Add data quality warnings
        if features.tvl_pct_change_6h is None:
            features.warnings.append("Could not compute 6h TVL change")
        if features.tvl_pct_change_24h is None:
            features.warnings.append("Could not compute 24h TVL change")
        if features.volume_spike_ratio is None:
            features.warnings.append("Could not compute volume spike ratio")
        
        return features
    
    def compute_features_batch(self, pool_ids: List[str],
                               as_of: Optional[datetime] = None) -> Dict[str, TimeSeriesFeatures]:
        """
        Compute features for multiple pools.
        
        Args:
            pool_ids: List of pool identifiers
            as_of: Compute features as of this time
            
        Returns:
            Dictionary mapping pool_id to TimeSeriesFeatures
        """
        results = {}
        for pool_id in pool_ids:
            try:
                results[pool_id] = self.compute_features(pool_id, as_of)
            except Exception as e:
                logger.error(f"Error computing features for {pool_id}: {e}")
                results[pool_id] = TimeSeriesFeatures(
                    pool_id=pool_id,
                    timestamp=as_of or datetime.utcnow(),
                    warnings=[f"Computation error: {str(e)}"]
                )
        return results
    
    def get_all_pool_ids(self) -> List[str]:
        """
        Get all unique pool IDs in the history table.
        """
        db = SessionLocal()
        try:
            result = db.query(SnapshotHistory.pool_id).distinct().all()
            return [r[0] for r in result]
        finally:
            db.close()
    
    def _get_history(self, pool_id: str, hours: int, 
                     as_of: datetime) -> List[SnapshotHistory]:
        """
        Fetch historical snapshots for a pool.
        
        Args:
            pool_id: Pool identifier
            hours: Number of hours of history to fetch
            as_of: End time for the window
            
        Returns:
            List of SnapshotHistory records, most recent first
        """
        db = SessionLocal()
        try:
            start_time = as_of - timedelta(hours=hours)
            
            snapshots = db.query(SnapshotHistory).filter(
                and_(
                    SnapshotHistory.pool_id == pool_id,
                    SnapshotHistory.timestamp >= start_time,
                    SnapshotHistory.timestamp <= as_of
                )
            ).order_by(desc(SnapshotHistory.timestamp)).all()
            
            return snapshots
        finally:
            db.close()
    
    def _round_to_hour(self, dt: datetime) -> datetime:
        """Round datetime to the hour (floor)"""
        return dt.replace(minute=0, second=0, microsecond=0)
    
    def _compute_tvl_pct_change(self, history: List[SnapshotHistory], 
                                 hours: int) -> Optional[float]:
        """
        Compute percentage change in TVL over N hours.
        
        Formula: (TVL_now - TVL_N_hours_ago) / TVL_N_hours_ago
        
        Args:
            history: List of snapshots (most recent first)
            hours: Lookback period
            
        Returns:
            Percentage change as decimal (e.g., -0.15 = -15%)
        """
        if len(history) < 2:
            return None
        
        current_tvl = history[0].tvl
        
        # Find snapshot closest to N hours ago
        target_time = history[0].timestamp - timedelta(hours=hours)
        past_snapshot = None
        
        for snap in history:
            if snap.timestamp <= target_time:
                past_snapshot = snap
                break
        
        if past_snapshot is None or past_snapshot.tvl is None or past_snapshot.tvl == 0:
            # Use oldest available if exact match not found
            past_snapshot = history[-1]
            if past_snapshot.tvl is None or past_snapshot.tvl == 0:
                return None
        
        past_tvl = past_snapshot.tvl
        
        if past_tvl == 0:
            return None
        
        pct_change = (current_tvl - past_tvl) / past_tvl
        
        # Clamp extreme values
        return max(min(pct_change, 10.0), -1.0)
    
    def _compute_tvl_acceleration(self, history: List[SnapshotHistory]) -> Optional[float]:
        """
        Compute TVL acceleration (rate of change of rate of change).
        
        Formula: Δ(ΔTVL) = (change_recent - change_older)
        
        This detects accelerating withdrawals (panic behavior).
        
        Returns:
            Acceleration value (negative = accelerating outflow)
        """
        if len(history) < 7:  # Need at least 7 points for 2 windows
            return None
        
        # Recent 3-hour change
        recent_tvl = history[0].tvl if history[0].tvl else 0
        mid_tvl = history[3].tvl if len(history) > 3 and history[3].tvl else recent_tvl
        older_tvl = history[6].tvl if len(history) > 6 and history[6].tvl else mid_tvl
        
        if mid_tvl == 0 or older_tvl == 0:
            return None
        
        # Rate of change in each period
        recent_change = (recent_tvl - mid_tvl) / mid_tvl if mid_tvl else 0
        older_change = (mid_tvl - older_tvl) / older_tvl if older_tvl else 0
        
        # Acceleration = change in rate of change
        acceleration = recent_change - older_change
        
        # Clamp extreme values
        return max(min(acceleration, 1.0), -1.0)
    
    def _compute_volume_spike_ratio(self, history: List[SnapshotHistory]) -> Optional[float]:
        """
        Compute ratio of current volume to 24h average.
        
        Formula: current_volume / avg(volume_24h over last 24h)
        
        High values indicate unusual trading activity.
        
        Returns:
            Spike ratio (1.0 = normal, >3.0 = spike)
        """
        if len(history) < 2:
            return None
        
        current_volume = history[0].volume_24h
        
        if current_volume is None:
            return None
        
        # Compute average volume over available history
        volumes = [s.volume_24h for s in history if s.volume_24h is not None and s.volume_24h > 0]
        
        if not volumes:
            return None
        
        avg_volume = sum(volumes) / len(volumes)
        
        if avg_volume == 0:
            return None
        
        ratio = current_volume / avg_volume
        
        # Clamp extreme values
        return max(min(ratio, 100.0), 0.0)
    
    def _compute_reserve_imbalance(self, reserve0: Optional[float], 
                                    reserve1: Optional[float]) -> Optional[float]:
        """
        Compute reserve imbalance ratio.
        
        Formula: |reserve0 - reserve1| / (reserve0 + reserve1)
        
        High imbalance indicates liquidity skew or potential manipulation.
        
        Returns:
            Imbalance ratio between 0 and 1
        """
        if reserve0 is None or reserve1 is None:
            return None
        
        total = reserve0 + reserve1
        
        if total == 0:
            return None
        
        imbalance = abs(reserve0 - reserve1) / total
        
        # Already bounded 0-1 by formula
        return imbalance
    
    def run_sanity_checks(self, features: TimeSeriesFeatures) -> List[str]:
        """
        Run sanity checks on computed features.
        
        Returns list of failed checks.
        """
        failures = []
        
        # TVL should never be negative (but change can be)
        # This is checked at data level
        
        # Volume spike ratio >= 0
        if features.volume_spike_ratio is not None and features.volume_spike_ratio < 0:
            failures.append(f"Volume spike ratio negative: {features.volume_spike_ratio}")
        
        # Reserve imbalance between 0 and 1
        if features.reserve_imbalance is not None:
            if features.reserve_imbalance < 0 or features.reserve_imbalance > 1:
                failures.append(
                    f"Reserve imbalance out of bounds: {features.reserve_imbalance}"
                )
        
        return failures


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Time-Series Feature Engine')
    parser.add_argument('--pool', type=str, help='Compute features for specific pool')
    parser.add_argument('--all', action='store_true', help='Compute features for all pools')
    args = parser.parse_args()
    
    engine = TimeSeriesFeatureEngine()
    
    if args.pool:
        features = engine.compute_features(args.pool)
        print(f"\n📊 Features for {args.pool}:")
        print(f"   TVL Change (6h):  {features.tvl_pct_change_6h:.2%}" if features.tvl_pct_change_6h else "   TVL Change (6h):  N/A")
        print(f"   TVL Change (24h): {features.tvl_pct_change_24h:.2%}" if features.tvl_pct_change_24h else "   TVL Change (24h): N/A")
        print(f"   TVL Acceleration: {features.tvl_acceleration:.4f}" if features.tvl_acceleration else "   TVL Acceleration: N/A")
        print(f"   Volume Spike:     {features.volume_spike_ratio:.2f}x" if features.volume_spike_ratio else "   Volume Spike:     N/A")
        print(f"   Reserve Imbalance: {features.reserve_imbalance:.2%}" if features.reserve_imbalance else "   Reserve Imbalance: N/A")
        
        signals = features.get_risk_signals()
        if signals:
            print(f"\n⚠️  Risk Signals Detected:")
            for sig in signals:
                print(f"   [{sig['severity'].upper()}] {sig['description']}")
    
    elif args.all:
        pool_ids = engine.get_all_pool_ids()
        print(f"\n📊 Computing features for {len(pool_ids)} pools...")
        
        all_features = engine.compute_features_batch(pool_ids)
        
        for pool_id, features in all_features.items():
            status = "✓" if features.sufficient_data else "⚠"
            print(f"\n{status} {pool_id}:")
            if features.tvl_pct_change_6h is not None:
                print(f"   6h: {features.tvl_pct_change_6h:+.2%}")
            if features.tvl_pct_change_24h is not None:
                print(f"   24h: {features.tvl_pct_change_24h:+.2%}")
    else:
        print("Use --pool <pool_id> or --all to compute features")
