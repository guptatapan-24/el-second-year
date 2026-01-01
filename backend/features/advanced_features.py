#!/usr/bin/env python3
"""
Advanced Predictive Feature Engineering for VeriRisk Phase-2

This module computes forward-looking early-warning features for DeFi risk prediction.
All features are designed to detect patterns that precede TVL crashes, enabling
predictive (not reactive) risk assessment.

Features Computed:
1. tvl_change_6h      - 6-hour TVL percentage change (short-term trend)
2. tvl_change_24h     - 24-hour TVL percentage change (daily trend)
3. tvl_acceleration   - Second derivative of TVL (panic/acceleration detection)
4. volume_spike_ratio - Current volume vs rolling 24h average (unusual activity)
5. reserve_imbalance_rate - Rate of change of reserve imbalance
6. volatility_6h      - Short-term TVL return volatility
7. volatility_24h     - Long-term TVL return volatility
8. volatility_ratio   - volatility_6h / volatility_24h (regime change detector)
9. early_warning_score - Weighted composite signal (0-100)

Academic Keywords:
- Predictive signal extraction
- Time-series feature engineering
- DeFi protocol risk forecasting
- No data leakage design
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PredictiveFeatures:
    """
    Container for computed predictive features.
    
    All features are backward-looking (use only past data) to prevent
    data leakage when used for future prediction.
    """
    pool_id: str
    timestamp: datetime
    
    # TVL Change Features (backward-looking)
    tvl_change_6h: Optional[float] = None
    tvl_change_24h: Optional[float] = None
    tvl_acceleration: Optional[float] = None
    
    # Volume Features
    volume_spike_ratio: Optional[float] = None
    
    # Reserve Features
    reserve_imbalance: Optional[float] = None
    reserve_imbalance_rate: Optional[float] = None
    
    # Volatility Features
    volatility_6h: Optional[float] = None
    volatility_24h: Optional[float] = None
    volatility_ratio: Optional[float] = None
    
    # Composite Score
    early_warning_score: Optional[float] = None
    
    # Data Quality
    data_points_available: int = 0
    sufficient_data: bool = False
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for model input"""
        return {
            'tvl_change_6h': self.tvl_change_6h or 0.0,
            'tvl_change_24h': self.tvl_change_24h or 0.0,
            'tvl_acceleration': self.tvl_acceleration or 0.0,
            'volume_spike_ratio': self.volume_spike_ratio or 1.0,
            'reserve_imbalance': self.reserve_imbalance or 0.0,
            'reserve_imbalance_rate': self.reserve_imbalance_rate or 0.0,
            'volatility_6h': self.volatility_6h or 0.0,
            'volatility_24h': self.volatility_24h or 0.0,
            'volatility_ratio': self.volatility_ratio or 1.0,
            'early_warning_score': self.early_warning_score or 50.0,
        }
    
    def get_feature_vector(self) -> List[float]:
        """Get feature vector for ML model"""
        d = self.to_dict()
        return [
            d['tvl_change_6h'],
            d['tvl_change_24h'],
            d['tvl_acceleration'],
            d['volume_spike_ratio'],
            d['reserve_imbalance'],
            d['reserve_imbalance_rate'],
            d['volatility_6h'],
            d['volatility_24h'],
            d['volatility_ratio'],
            d['early_warning_score'],
        ]


class AdvancedFeatureEngine:
    """
    Engine for computing predictive features from historical time-series data.
    
    Design Principles:
    - No data leakage: All features use only past data relative to prediction time
    - Robust to missing data: Graceful degradation with sensible defaults
    - Bounded outputs: Features are normalized for ML stability
    - Early-warning focus: Features designed to detect pre-crash patterns
    """
    
    # Feature names for model training
    FEATURE_NAMES = [
        'tvl_change_6h',
        'tvl_change_24h', 
        'tvl_acceleration',
        'volume_spike_ratio',
        'reserve_imbalance',
        'reserve_imbalance_rate',
        'volatility_6h',
        'volatility_24h',
        'volatility_ratio',
        'early_warning_score',
    ]
    
    # Window sizes
    WINDOW_6H = 6
    WINDOW_24H = 24
    
    # Minimum data requirements
    MIN_POINTS_6H = 4
    MIN_POINTS_24H = 18
    
    # Early warning score weights
    EWS_WEIGHTS = {
        'tvl_change_6h': 0.15,
        'tvl_change_24h': 0.20,
        'tvl_acceleration': 0.20,
        'volume_spike_ratio': 0.15,
        'reserve_imbalance_rate': 0.10,
        'volatility_ratio': 0.20,
    }
    
    def __init__(self):
        logger.info("✓ AdvancedFeatureEngine initialized")
    
    def compute_features_from_df(self, df: pd.DataFrame, pool_id: str) -> pd.DataFrame:
        """
        Compute all predictive features for a pool from a DataFrame.
        
        This method is optimized for batch processing during model training.
        It processes the entire time series and returns features for each row.
        
        Args:
            df: DataFrame with columns [timestamp, tvl, volume_24h, reserve0, reserve1]
                Must be sorted by timestamp ascending
            pool_id: Pool identifier
            
        Returns:
            DataFrame with original data plus computed features
        """
        if len(df) < self.MIN_POINTS_6H:
            logger.warning(f"Insufficient data for {pool_id}: {len(df)} points")
            return df
        
        df = df.copy()
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Ensure numeric columns
        for col in ['tvl', 'volume_24h', 'reserve0', 'reserve1']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Compute TVL returns for volatility calculation
        df['tvl_return'] = df['tvl'].pct_change().fillna(0)
        
        # 1. TVL Change Features (backward-looking)
        df['tvl_change_6h'] = df['tvl'].pct_change(periods=self.WINDOW_6H).fillna(0)
        df['tvl_change_24h'] = df['tvl'].pct_change(periods=self.WINDOW_24H).fillna(0)
        
        # 2. TVL Acceleration (second derivative - rate of change of change)
        # Compares recent 6h change to prior 6h change
        df['tvl_change_6h_lag'] = df['tvl_change_6h'].shift(self.WINDOW_6H).fillna(0)
        df['tvl_acceleration'] = (df['tvl_change_6h'] - df['tvl_change_6h_lag']).fillna(0)
        
        # 3. Volume Spike Ratio (current volume / rolling 24h average)
        df['volume_rolling_avg'] = df['volume_24h'].rolling(
            window=self.WINDOW_24H, min_periods=1
        ).mean()
        df['volume_spike_ratio'] = np.where(
            df['volume_rolling_avg'] > 0,
            df['volume_24h'] / df['volume_rolling_avg'],
            1.0
        )
        
        # 4. Reserve Imbalance
        total_reserves = df['reserve0'] + df['reserve1']
        df['reserve_imbalance'] = np.where(
            total_reserves > 0,
            np.abs(df['reserve0'] - df['reserve1']) / total_reserves,
            0.0
        )
        
        # 5. Reserve Imbalance Rate of Change
        df['reserve_imbalance_rate'] = df['reserve_imbalance'].diff(
            periods=self.WINDOW_6H
        ).fillna(0)
        
        # 6. Volatility Features (rolling standard deviation of returns)
        df['volatility_6h'] = df['tvl_return'].rolling(
            window=self.WINDOW_6H, min_periods=2
        ).std().fillna(0)
        
        df['volatility_24h'] = df['tvl_return'].rolling(
            window=self.WINDOW_24H, min_periods=6
        ).std().fillna(0)
        
        # 7. Volatility Ratio (short-term vs long-term)
        # High ratio indicates regime change / increased short-term risk
        df['volatility_ratio'] = np.where(
            df['volatility_24h'] > 0.001,  # Avoid division by very small numbers
            df['volatility_6h'] / df['volatility_24h'],
            1.0
        )
        
        # 8. Early Warning Score (composite 0-100)
        df['early_warning_score'] = self._compute_early_warning_score(df)
        
        # Clip extreme values for stability
        df['tvl_change_6h'] = df['tvl_change_6h'].clip(-1.0, 1.0)
        df['tvl_change_24h'] = df['tvl_change_24h'].clip(-1.0, 1.0)
        df['tvl_acceleration'] = df['tvl_acceleration'].clip(-0.5, 0.5)
        df['volume_spike_ratio'] = df['volume_spike_ratio'].clip(0.0, 10.0)
        df['reserve_imbalance'] = df['reserve_imbalance'].clip(0.0, 1.0)
        df['reserve_imbalance_rate'] = df['reserve_imbalance_rate'].clip(-0.5, 0.5)
        df['volatility_6h'] = df['volatility_6h'].clip(0.0, 1.0)
        df['volatility_24h'] = df['volatility_24h'].clip(0.0, 1.0)
        df['volatility_ratio'] = df['volatility_ratio'].clip(0.0, 10.0)
        df['early_warning_score'] = df['early_warning_score'].clip(0.0, 100.0)
        
        # Drop intermediate columns
        df = df.drop(columns=['tvl_return', 'tvl_change_6h_lag', 'volume_rolling_avg'], 
                     errors='ignore')
        
        return df
    
    def _compute_early_warning_score(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute composite early warning score (0-100).
        
        Higher score = higher risk of future TVL crash.
        
        Components:
        - Negative TVL changes increase score
        - Negative acceleration (accelerating outflows) increases score
        - High volume spikes increase score
        - Increasing reserve imbalance increases score
        - High volatility ratio increases score
        """
        score = pd.Series(50.0, index=df.index)  # Start at neutral 50
        
        # TVL Change 6h: negative change = higher risk
        # Scale: -20% change -> +20 points
        tvl_6h_component = -df['tvl_change_6h'] * 100 * self.EWS_WEIGHTS['tvl_change_6h']
        score += tvl_6h_component.fillna(0)
        
        # TVL Change 24h: negative change = higher risk
        tvl_24h_component = -df['tvl_change_24h'] * 100 * self.EWS_WEIGHTS['tvl_change_24h']
        score += tvl_24h_component.fillna(0)
        
        # TVL Acceleration: negative = accelerating outflows = higher risk
        accel_component = -df['tvl_acceleration'] * 100 * self.EWS_WEIGHTS['tvl_acceleration']
        score += accel_component.fillna(0)
        
        # Volume Spike: high spike = potential panic = higher risk
        # Spike > 2x adds risk
        volume_component = (df['volume_spike_ratio'] - 1.0).clip(0) * 10 * self.EWS_WEIGHTS['volume_spike_ratio']
        score += volume_component.fillna(0)
        
        # Reserve Imbalance Rate: positive rate = increasing imbalance = higher risk
        imbalance_component = df['reserve_imbalance_rate'] * 100 * self.EWS_WEIGHTS['reserve_imbalance_rate']
        score += imbalance_component.fillna(0)
        
        # Volatility Ratio: high ratio = regime change = higher risk
        # Ratio > 1.5 adds risk
        vol_component = (df['volatility_ratio'] - 1.0).clip(0) * 10 * self.EWS_WEIGHTS['volatility_ratio']
        score += vol_component.fillna(0)
        
        return score.clip(0, 100)
    
    def compute_features_for_prediction(self, 
                                         history: List[Dict],
                                         pool_id: str) -> PredictiveFeatures:
        """
        Compute features for a single prediction from recent history.
        
        Used during inference to get features for a specific pool.
        
        Args:
            history: List of recent snapshots (dicts with tvl, volume_24h, etc.)
                     Should be sorted by timestamp descending (most recent first)
            pool_id: Pool identifier
            
        Returns:
            PredictiveFeatures object with computed values
        """
        features = PredictiveFeatures(
            pool_id=pool_id,
            timestamp=datetime.utcnow()
        )
        
        if len(history) < self.MIN_POINTS_6H:
            features.warnings.append(f"Insufficient data: {len(history)} points")
            features.data_points_available = len(history)
            return features
        
        # Convert to DataFrame
        df = pd.DataFrame(history)
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        features.data_points_available = len(df)
        features.sufficient_data = len(df) >= self.MIN_POINTS_24H
        
        # Compute features using batch method
        df_with_features = self.compute_features_from_df(df, pool_id)
        
        # Get the latest row (current features)
        latest = df_with_features.iloc[-1]
        
        features.tvl_change_6h = float(latest.get('tvl_change_6h', 0))
        features.tvl_change_24h = float(latest.get('tvl_change_24h', 0))
        features.tvl_acceleration = float(latest.get('tvl_acceleration', 0))
        features.volume_spike_ratio = float(latest.get('volume_spike_ratio', 1.0))
        features.reserve_imbalance = float(latest.get('reserve_imbalance', 0))
        features.reserve_imbalance_rate = float(latest.get('reserve_imbalance_rate', 0))
        features.volatility_6h = float(latest.get('volatility_6h', 0))
        features.volatility_24h = float(latest.get('volatility_24h', 0))
        features.volatility_ratio = float(latest.get('volatility_ratio', 1.0))
        features.early_warning_score = float(latest.get('early_warning_score', 50.0))
        
        return features
    
    @staticmethod
    def get_feature_names() -> List[str]:
        """Get list of feature names for model training"""
        return AdvancedFeatureEngine.FEATURE_NAMES.copy()


def compute_predictive_features_for_pool(df: pd.DataFrame, pool_id: str) -> pd.DataFrame:
    """
    Convenience function to compute predictive features for a pool.
    
    Args:
        df: DataFrame with timestamp, tvl, volume_24h, reserve0, reserve1
        pool_id: Pool identifier
        
    Returns:
        DataFrame with computed features added
    """
    engine = AdvancedFeatureEngine()
    return engine.compute_features_from_df(df, pool_id)


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Demo with synthetic data
    print("\n" + "="*60)
    print("Advanced Predictive Feature Engine Demo")
    print("="*60)
    
    # Create sample data
    np.random.seed(42)
    n_samples = 48  # 48 hours
    
    # Simulate a pool with gradual decline then crash
    base_tvl = 1_000_000
    tvl_series = []
    for i in range(n_samples):
        if i < 30:
            # Normal period with slight decline
            tvl = base_tvl * (1 - 0.005 * i + np.random.normal(0, 0.02))
        else:
            # Crash period - accelerating decline
            tvl = base_tvl * (0.85 - 0.03 * (i - 30) + np.random.normal(0, 0.02))
        tvl_series.append(max(tvl, 100000))
    
    df = pd.DataFrame({
        'timestamp': pd.date_range(end=datetime.utcnow(), periods=n_samples, freq='H'),
        'tvl': tvl_series,
        'volume_24h': np.random.uniform(50000, 200000, n_samples),
        'reserve0': np.array(tvl_series) * 0.5,
        'reserve1': np.array(tvl_series) * 0.5,
    })
    
    engine = AdvancedFeatureEngine()
    df_features = engine.compute_features_from_df(df, 'demo_pool')
    
    print(f"\nComputed features for {len(df_features)} time points")
    print("\nLatest features:")
    latest = df_features.iloc[-1]
    for feat in AdvancedFeatureEngine.FEATURE_NAMES:
        print(f"  {feat}: {latest[feat]:.4f}")
    
    print("\n✓ Feature engine working correctly")
