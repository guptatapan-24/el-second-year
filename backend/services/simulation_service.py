#!/usr/bin/env python3
"""
Simulation Service for VeriRisk Phase 5

This module provides what-if risk simulation capabilities:
1. Fetch latest snapshot for a protocol
2. Apply user-defined overrides (TVL change, volume change, volatility)
3. Recompute derived features
4. Run ML inference with modified features
5. Generate SHAP explanations
6. Compare simulated vs actual risk

IMPORTANT: Simulations are stateless - no data is persisted.
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

import sys
import os
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, Snapshot
from model_server import PredictiveModelServer
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class SimulationService:
    """
    Service for running what-if risk simulations.
    
    Enables users to:
    - Test impact of TVL drops on risk score
    - Simulate volume spikes
    - Override volatility and reserve imbalance
    - Compare simulated vs actual risk with explanations
    """
    
    def __init__(self):
        self.model_server = PredictiveModelServer()
        logger.info("✓ SimulationService initialized")
    
    def get_latest_features(self, pool_id: str) -> Optional[Dict]:
        """
        Get the latest feature snapshot for a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Dictionary with current features or None
        """
        db = SessionLocal()
        try:
            snap = (
                db.query(Snapshot)
                .filter(Snapshot.pool_id == pool_id)
                .order_by(desc(Snapshot.timestamp))
                .first()
            )
            
            if not snap:
                return None
            
            # Extract base metrics
            tvl = float(snap.tvl or 0)
            volume_24h = float(snap.volume_24h or 0)
            reserve0 = float(snap.reserve0 or 0)
            reserve1 = float(snap.reserve1 or 0)
            
            # Extract computed features from snapshot
            features = snap.features or {}
            
            return {
                'pool_id': pool_id,
                'timestamp': snap.timestamp.isoformat(),
                'base_metrics': {
                    'tvl': tvl,
                    'volume_24h': volume_24h,
                    'reserve0': reserve0,
                    'reserve1': reserve1,
                },
                'features': {
                    'tvl_change_6h': float(features.get('tvl_change_6h', 0)),
                    'tvl_change_24h': float(features.get('tvl_change_24h', 0)),
                    'tvl_acceleration': float(features.get('tvl_acceleration', 0)),
                    'volume_spike_ratio': float(features.get('volume_spike_ratio', 1.0)),
                    'reserve_imbalance': float(features.get('reserve_imbalance', 0)),
                    'reserve_imbalance_rate': float(features.get('reserve_imbalance_rate', 0)),
                    'volatility_6h': float(features.get('volatility_6h', 0.02)),
                    'volatility_24h': float(features.get('volatility_24h', 0.02)),
                    'volatility_ratio': float(features.get('volatility_ratio', 1.0)),
                    'early_warning_score': float(features.get('early_warning_score', 20)),
                }
            }
            
        finally:
            db.close()
    
    def apply_overrides(
        self,
        base_features: Dict,
        tvl_change_pct: float = 0,
        volume_change_pct: float = 0,
        volatility_override: Optional[float] = None,
        reserve_imbalance_override: Optional[float] = None
    ) -> Dict:
        """
        Apply user-defined overrides to base features.
        
        Args:
            base_features: Original feature dictionary
            tvl_change_pct: Percentage change to TVL (-100 to +100)
            volume_change_pct: Percentage change to volume (-100 to +500)
            volatility_override: Direct override for volatility (0.01 to 0.5)
            reserve_imbalance_override: Direct override for imbalance (0 to 1)
            
        Returns:
            Modified feature dictionary for simulation
        """
        # Deep copy features
        simulated = {
            'base_metrics': dict(base_features['base_metrics']),
            'features': dict(base_features['features'])
        }
        
        # Apply TVL change
        if tvl_change_pct != 0:
            # Modify base TVL
            original_tvl = simulated['base_metrics']['tvl']
            new_tvl = original_tvl * (1 + tvl_change_pct / 100)
            simulated['base_metrics']['tvl'] = max(0, new_tvl)
            
            # Update TVL change features
            # Simulate as if this change happened in 6h
            simulated['features']['tvl_change_6h'] = tvl_change_pct / 100
            
            # If significant drop, increase 24h change and acceleration
            if tvl_change_pct < -20:
                simulated['features']['tvl_change_24h'] = min(
                    simulated['features']['tvl_change_24h'],
                    tvl_change_pct / 100 * 0.8  # 80% impact on 24h
                )
                # Accelerating decline
                simulated['features']['tvl_acceleration'] = tvl_change_pct / 100 * 0.5
                
                # Increase early warning score for drops
                drop_severity = abs(tvl_change_pct) / 100
                ews_boost = min(50, drop_severity * 100)
                simulated['features']['early_warning_score'] = min(
                    100,
                    simulated['features']['early_warning_score'] + ews_boost
                )
        
        # Apply volume change
        if volume_change_pct != 0:
            original_volume = simulated['base_metrics']['volume_24h']
            new_volume = original_volume * (1 + volume_change_pct / 100)
            simulated['base_metrics']['volume_24h'] = max(0, new_volume)
            
            # Update volume spike ratio
            # Spike ratio = current / average, so % change directly affects it
            original_spike_ratio = simulated['features']['volume_spike_ratio']
            simulated['features']['volume_spike_ratio'] = original_spike_ratio * (1 + volume_change_pct / 100)
            
            # Cap spike ratio
            simulated['features']['volume_spike_ratio'] = min(10.0, max(0.1, 
                simulated['features']['volume_spike_ratio']))
            
            # Volume spikes increase early warning
            if volume_change_pct > 100:
                ews_boost = min(30, volume_change_pct / 10)
                simulated['features']['early_warning_score'] = min(
                    100,
                    simulated['features']['early_warning_score'] + ews_boost
                )
        
        # Apply volatility override
        if volatility_override is not None:
            volatility_override = max(0.01, min(0.5, volatility_override))
            simulated['features']['volatility_6h'] = volatility_override
            simulated['features']['volatility_24h'] = volatility_override * 0.8  # Slightly lower 24h
            
            # Recalculate volatility ratio
            if simulated['features']['volatility_24h'] > 0.001:
                simulated['features']['volatility_ratio'] = (
                    simulated['features']['volatility_6h'] / 
                    simulated['features']['volatility_24h']
                )
            
            # High volatility increases early warning
            if volatility_override > 0.15:
                ews_boost = min(25, (volatility_override - 0.15) * 200)
                simulated['features']['early_warning_score'] = min(
                    100,
                    simulated['features']['early_warning_score'] + ews_boost
                )
        
        # Apply reserve imbalance override
        if reserve_imbalance_override is not None:
            reserve_imbalance_override = max(0, min(1, reserve_imbalance_override))
            original_imbalance = simulated['features']['reserve_imbalance']
            simulated['features']['reserve_imbalance'] = reserve_imbalance_override
            
            # Calculate rate of change
            imbalance_delta = reserve_imbalance_override - original_imbalance
            simulated['features']['reserve_imbalance_rate'] = imbalance_delta
            
            # High imbalance increases early warning
            if reserve_imbalance_override > 0.3:
                ews_boost = min(20, (reserve_imbalance_override - 0.3) * 50)
                simulated['features']['early_warning_score'] = min(
                    100,
                    simulated['features']['early_warning_score'] + ews_boost
                )
        
        # Ensure all features are bounded
        simulated['features']['tvl_change_6h'] = max(-1.0, min(1.0, simulated['features']['tvl_change_6h']))
        simulated['features']['tvl_change_24h'] = max(-1.0, min(1.0, simulated['features']['tvl_change_24h']))
        simulated['features']['tvl_acceleration'] = max(-0.5, min(0.5, simulated['features']['tvl_acceleration']))
        simulated['features']['reserve_imbalance'] = max(0, min(1, simulated['features']['reserve_imbalance']))
        simulated['features']['early_warning_score'] = max(0, min(100, simulated['features']['early_warning_score']))
        
        return simulated
    
    def predict_with_features(self, features: Dict) -> Dict:
        """
        Run ML prediction with provided features.
        
        Args:
            features: Feature dictionary
            
        Returns:
            Prediction result with score, level, and explanations
        """
        if self.model_server.model is None:
            return {"error": "Model not loaded"}
        
        try:
            # Build feature vector in correct order
            feature_names = self.model_server.feature_names
            feature_dict = features['features']
            
            feature_vector = np.array([[
                feature_dict.get('tvl_change_6h', 0),
                feature_dict.get('tvl_change_24h', 0),
                feature_dict.get('tvl_acceleration', 0),
                feature_dict.get('volume_spike_ratio', 1.0),
                feature_dict.get('reserve_imbalance', 0),
                feature_dict.get('reserve_imbalance_rate', 0),
                feature_dict.get('volatility_6h', 0.02),
                feature_dict.get('volatility_24h', 0.02),
                feature_dict.get('volatility_ratio', 1.0),
                feature_dict.get('early_warning_score', 20),
            ]])
            
            # Get ML probability
            prob = float(self.model_server.model.predict_proba(feature_vector)[0][1])
            ml_risk_score = prob * 100
            
            # Apply feature-based boosters (same logic as model_server)
            risk_score = ml_risk_score
            
            tvl_change_6h = feature_dict.get('tvl_change_6h', 0)
            tvl_change_24h = feature_dict.get('tvl_change_24h', 0)
            tvl_acceleration = feature_dict.get('tvl_acceleration', 0)
            early_warning_score = feature_dict.get('early_warning_score', 20)
            
            # Boost for severe TVL decline
            if tvl_change_6h < -0.20 or tvl_change_24h < -0.50:
                decline_boost = min(30, abs(min(tvl_change_6h, tvl_change_24h)) * 40)
                risk_score = max(risk_score, 65 + decline_boost)
            
            # Boost for accelerating decline
            if tvl_acceleration < -0.05 and (tvl_change_6h < -0.10 or tvl_change_24h < -0.20):
                accel_boost = min(20, abs(tvl_acceleration) * 200)
                risk_score = min(100, risk_score + accel_boost)
            
            # Boost for high early warning score
            if early_warning_score > 70:
                ews_boost = (early_warning_score - 70) * 0.8
                risk_score = max(risk_score, 65 + ews_boost)
            
            risk_score = round(max(0, min(100, risk_score)), 2)
            
            # Compute SHAP explanations
            top_reasons = self.model_server.compute_shap_explanations(feature_vector)
            
            # Determine risk level
            if risk_score < 30:
                risk_level = 'LOW'
            elif risk_score < 65:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'HIGH'
            
            return {
                'risk_score': risk_score,
                'risk_level': risk_level,
                'ml_probability': round(ml_risk_score, 2),
                'top_reasons': top_reasons,
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"error": str(e)}
    
    def run_simulation(
        self,
        pool_id: str,
        tvl_change_pct: float = 0,
        volume_change_pct: float = 0,
        volatility_override: Optional[float] = None,
        reserve_imbalance_override: Optional[float] = None
    ) -> Dict:
        """
        Run a complete what-if simulation.
        
        Args:
            pool_id: Pool to simulate
            tvl_change_pct: % change to TVL (-80 to +80)
            volume_change_pct: % change to volume (-100 to +200)
            volatility_override: Override volatility (0.01 to 0.5)
            reserve_imbalance_override: Override imbalance (0 to 1)
            
        Returns:
            Complete simulation result with actual vs simulated comparison
        """
        # Step 1: Get current state
        base_features = self.get_latest_features(pool_id)
        
        if not base_features:
            return {
                "error": f"No data found for pool: {pool_id}",
                "pool_id": pool_id
            }
        
        # Step 2: Get actual current risk
        actual_prediction = self.model_server.predict_risk(pool_id)
        
        if 'error' in actual_prediction:
            return {
                "error": f"Failed to get actual risk: {actual_prediction['error']}",
                "pool_id": pool_id
            }
        
        # Step 3: Apply overrides
        simulated_features = self.apply_overrides(
            base_features,
            tvl_change_pct=tvl_change_pct,
            volume_change_pct=volume_change_pct,
            volatility_override=volatility_override,
            reserve_imbalance_override=reserve_imbalance_override
        )
        
        # Step 4: Run simulation prediction
        simulated_prediction = self.predict_with_features(simulated_features)
        
        if 'error' in simulated_prediction:
            return {
                "error": f"Simulation failed: {simulated_prediction['error']}",
                "pool_id": pool_id
            }
        
        # Step 5: Calculate delta
        actual_score = actual_prediction.get('risk_score', 0)
        simulated_score = simulated_prediction.get('risk_score', 0)
        delta = round(simulated_score - actual_score, 2)
        
        # Step 6: Build response
        return {
            "pool_id": pool_id,
            "timestamp": datetime.utcnow().isoformat(),
            "simulation_params": {
                "tvl_change_pct": tvl_change_pct,
                "volume_change_pct": volume_change_pct,
                "volatility_override": volatility_override,
                "reserve_imbalance_override": reserve_imbalance_override
            },
            "actual_risk": {
                "score": actual_score,
                "level": actual_prediction.get('risk_level', 'UNKNOWN'),
                "early_warning_score": actual_prediction.get('early_warning_score')
            },
            "simulated_risk": {
                "score": simulated_score,
                "level": simulated_prediction.get('risk_level', 'UNKNOWN'),
                "early_warning_score": simulated_features['features'].get('early_warning_score')
            },
            "delta": delta,
            "risk_increased": delta > 0,
            "alert_would_trigger": simulated_score >= 65 or abs(delta) >= 30,
            "top_risk_factors": simulated_prediction.get('top_reasons', []),
            "feature_changes": {
                "tvl_change_6h": {
                    "before": base_features['features'].get('tvl_change_6h', 0),
                    "after": simulated_features['features'].get('tvl_change_6h', 0)
                },
                "volume_spike_ratio": {
                    "before": base_features['features'].get('volume_spike_ratio', 1),
                    "after": simulated_features['features'].get('volume_spike_ratio', 1)
                },
                "volatility_6h": {
                    "before": base_features['features'].get('volatility_6h', 0.02),
                    "after": simulated_features['features'].get('volatility_6h', 0.02)
                },
                "reserve_imbalance": {
                    "before": base_features['features'].get('reserve_imbalance', 0),
                    "after": simulated_features['features'].get('reserve_imbalance', 0)
                }
            }
        }


# Singleton instance
_simulation_service = None


def get_simulation_service() -> SimulationService:
    """Get or create singleton SimulationService instance."""
    global _simulation_service
    if _simulation_service is None:
        _simulation_service = SimulationService()
    return _simulation_service


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "="*60)
    print("Simulation Service Test")
    print("="*60)
    
    service = get_simulation_service()
    
    # Test simulation with TVL crash
    result = service.run_simulation(
        pool_id="uniswap_v2_usdc_eth",
        tvl_change_pct=-50,
        volume_change_pct=100
    )
    
    import json
    print(json.dumps(result, indent=2))