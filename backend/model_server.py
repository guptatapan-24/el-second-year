#!/usr/bin/env python3
"""
VeriRisk Phase-2: Predictive Model Inference Server with SHAP Explainability

This module provides:
1. Predictive risk scoring (forecasts future crashes)
2. SHAP-based explanations for every prediction
3. Top contributing features with impact magnitude and direction
4. CLI interface for demo/testing

Output Schema:
{
    "pool_id": "string",
    "risk_score": 0-100 (probability × 100),
    "risk_level": "LOW" | "MEDIUM" | "HIGH",
    "top_reasons": [
        {"feature": "name", "impact": float, "direction": "positive|negative"}
    ],
    "early_warning_score": 0-100,
    "features_used": {...},
    "model_version": "v2.0",
    "prediction_horizon": "24h",
    "timestamp": "ISO string"
}
"""

import joblib
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import shap
import sys
import os
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Snapshot
from config import config
from features.advanced_features import AdvancedFeatureEngine, PredictiveFeatures


class PredictiveModelServer:
    """
    Inference server for predictive risk model.
    
    Key capabilities:
    - Load trained predictive model
    - Compute features from recent history
    - Generate probability-based risk scores
    - Provide SHAP-based explanations
    """
    
    # Model paths (try v2 first, fallback to v1)
    MODEL_PATH_V2 = '../models/xgb_veririsk_v2_predictive.pkl'
    MODEL_PATH_V1 = '../models/xgb_veririsk_v1.pkl'
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.model = None
        self.explainer = None
        self.model_version = 'unknown'
        self.feature_engine = AdvancedFeatureEngine()
        self.feature_names = AdvancedFeatureEngine.get_feature_names()
        
        self.load_model()
    
    def load_model(self):
        """Load trained model and initialize SHAP explainer."""
        # Try v2 model first
        paths_to_try = []
        if self.model_path:
            paths_to_try.append(self.model_path)
        paths_to_try.extend([self.MODEL_PATH_V2, self.MODEL_PATH_V1])
        
        for path in paths_to_try:
            try:
                # Handle relative paths
                if not os.path.isabs(path):
                    path = os.path.join(os.path.dirname(__file__), path)
                
                if os.path.exists(path):
                    self.model = joblib.load(path)
                    self.model_path = path
                    
                    # Determine version
                    if 'v2_predictive' in path:
                        self.model_version = 'v2.0_predictive'
                        # Use v2 feature names
                        self.feature_names = AdvancedFeatureEngine.get_feature_names()
                    else:
                        self.model_version = 'v1.0_reactive'
                        # Use v1 feature names
                        self.feature_names = [
                            'tvl', 'reserve0', 'reserve1', 'volume_24h',
                            'tvl_pct_change_1h', 'reserve_imbalance',
                            'volume_tvl_ratio', 'volatility_24h', 'leverage_ratio'
                        ]
                    
                    print(f"✓ Model loaded: {os.path.basename(path)}")
                    print(f"  Version: {self.model_version}")
                    
                    # Initialize SHAP explainer
                    self.explainer = shap.TreeExplainer(self.model)
                    print("✓ SHAP explainer initialized")
                    
                    return
                    
            except Exception as e:
                print(f"⚠ Could not load {path}: {e}")
                continue
        
        print("\n⚠ No trained model found. Train a model first:")
        print("   python data_fetcher.py --predictive")
        print("   python model_trainer.py")
    
    def get_pool_history(self, pool_id: str, hours: int = 48) -> List[Dict]:
        """
        Fetch recent history for a pool from database.
        
        Args:
            pool_id: Pool identifier
            hours: Number of hours of history to fetch
            
        Returns:
            List of snapshot dictionaries, sorted by timestamp ascending
        """
        db = SessionLocal()
        try:
            from sqlalchemy import desc
            from datetime import timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            snapshots = (
                db.query(Snapshot)
                .filter(Snapshot.pool_id == pool_id)
                .filter(Snapshot.timestamp >= cutoff)
                .order_by(Snapshot.timestamp.asc())
                .all()
            )
            
            history = []
            for snap in snapshots:
                history.append({
                    'timestamp': snap.timestamp,
                    'tvl': float(snap.tvl or 0),
                    'volume_24h': float(snap.volume_24h or 0),
                    'reserve0': float(snap.reserve0 or 0),
                    'reserve1': float(snap.reserve1 or 0),
                })
            
            return history
            
        finally:
            db.close()
    
    def get_latest_snapshot_features(self, pool_id: str) -> Dict:
        """
        Get features from the latest snapshot (for v1 compatibility).
        """
        db = SessionLocal()
        try:
            from sqlalchemy import desc
            
            snap = (
                db.query(Snapshot)
                .filter(Snapshot.pool_id == pool_id)
                .order_by(desc(Snapshot.timestamp))
                .first()
            )
            
            if not snap:
                raise ValueError(f"No snapshot found for pool: {pool_id}")
            
            tvl = float(snap.tvl or 0)
            r0 = float(snap.reserve0 or 0)
            r1 = float(snap.reserve1 or 0)
            vol = float(snap.volume_24h or 0)
            f = snap.features or {}
            
            return {
                'tvl': tvl,
                'reserve0': r0,
                'reserve1': r1,
                'volume_24h': vol,
                'tvl_pct_change_1h': float(f.get('tvl_pct_change_1h', 0)),
                'reserve_imbalance': float(
                    f.get('reserve_imbalance', abs(r0 - r1) / max(r0 + r1, 1))
                ),
                'volume_tvl_ratio': float(
                    f.get('volume_tvl_ratio', vol / max(tvl, 1))
                ),
                'volatility_24h': float(f.get('volatility_24h', 0.02)),
                'leverage_ratio': float(f.get('leverage_ratio', 1.0)),
            }
            
        finally:
            db.close()
    
    def compute_predictive_features(self, pool_id: str) -> Tuple[np.ndarray, Dict]:
        """
        Compute predictive features from pool history.
        
        Returns:
            Tuple of (feature_vector, feature_dict)
        """
        if 'v2' in self.model_version:
            # V2: Use advanced feature engine
            history = self.get_pool_history(pool_id, hours=48)
            
            if len(history) < 6:
                raise ValueError(f"Insufficient history for {pool_id}: {len(history)} hours (need 6+)")
            
            features = self.feature_engine.compute_features_for_prediction(history, pool_id)
            feature_dict = features.to_dict()
            feature_vector = np.array([features.get_feature_vector()])
            
            return feature_vector, feature_dict
        else:
            # V1: Use latest snapshot features
            feature_dict = self.get_latest_snapshot_features(pool_id)
            feature_vector = np.array([[feature_dict[f] for f in self.feature_names]])
            
            return feature_vector, feature_dict
    
    def compute_shap_explanations(self, features: np.ndarray) -> List[Dict]:
        """
        Compute SHAP explanations for a prediction.
        
        Returns top 3 contributing features with:
        - feature name
        - impact magnitude
        - direction (positive = increases risk, negative = decreases risk)
        """
        if self.explainer is None:
            return [{"feature": "model_not_loaded", "impact": 0, "direction": "unknown"}]
        
        try:
            # Compute SHAP values
            shap_values = self.explainer.shap_values(features)
            
            # Handle different SHAP output formats
            if isinstance(shap_values, list):
                # Binary classification: use positive class
                shap_values = shap_values[1]
            
            # Get feature impacts
            feature_impacts = []
            for i, feature_name in enumerate(self.feature_names):
                impact = float(shap_values[0][i])
                feature_impacts.append({
                    'feature': feature_name,
                    'impact': round(impact, 4),
                    'abs_impact': abs(impact),
                    'direction': 'increases_risk' if impact > 0 else 'decreases_risk'
                })
            
            # Sort by absolute impact
            feature_impacts.sort(key=lambda x: x['abs_impact'], reverse=True)
            
            # Return top 3 with direction
            top_3 = []
            for f in feature_impacts[:3]:
                top_3.append({
                    'feature': f['feature'],
                    'impact': f['impact'],
                    'direction': f['direction'],
                    'explanation': self._get_feature_explanation(f['feature'], f['impact'])
                })
            
            return top_3
            
        except Exception as e:
            print(f"⚠ SHAP computation error: {e}")
            return [{"feature": "error", "impact": 0, "direction": "unknown"}]
    
    def _get_feature_explanation(self, feature: str, impact: float) -> str:
        """Generate human-readable explanation for a feature's contribution."""
        direction = "increasing" if impact > 0 else "decreasing"
        magnitude = "significantly" if abs(impact) > 0.1 else "slightly"
        
        explanations = {
            'tvl_change_6h': f"Recent TVL trend is {magnitude} {direction} predicted risk",
            'tvl_change_24h': f"24-hour TVL movement is {magnitude} {direction} risk score",
            'tvl_acceleration': f"TVL change acceleration is {magnitude} {direction} crash likelihood",
            'volume_spike_ratio': f"Trading volume relative to average is {magnitude} {direction} risk",
            'reserve_imbalance': f"Liquidity imbalance is {magnitude} {direction} manipulation risk",
            'reserve_imbalance_rate': f"Rate of imbalance change is {magnitude} {direction} risk",
            'volatility_6h': f"Short-term volatility is {magnitude} {direction} risk assessment",
            'volatility_24h': f"Long-term volatility is {magnitude} {direction} risk assessment",
            'volatility_ratio': f"Volatility regime indicator is {magnitude} {direction} risk",
            'early_warning_score': f"Composite early warning signal is {magnitude} {direction} risk",
        }
        
        return explanations.get(feature, f"Feature is {magnitude} {direction} risk")
    
    def get_risk_level(self, score: float) -> str:
        """Categorize risk score into risk level."""
        if score < 30:
            return 'LOW'
        elif score < 65:
            return 'MEDIUM'
        else:
            return 'HIGH'
    
    def predict_risk(self, pool_id: str) -> Dict:
        """
        Generate predictive risk assessment for a pool.
        
        Returns:
            Risk assessment dictionary with score, level, and explanations
        """
        if self.model is None:
            return {
                "error": "Model not loaded",
                "pool_id": pool_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            # Compute features
            feature_vector, feature_dict = self.compute_predictive_features(pool_id)
            
            # Get probability prediction
            prob = float(self.model.predict_proba(feature_vector)[0][1])
            risk_score = round(prob * 100, 2)
            
            # Compute SHAP explanations
            top_reasons = self.compute_shap_explanations(feature_vector)
            
            # Get early warning score if available
            early_warning_score = feature_dict.get('early_warning_score', None)
            
            # Build response
            result = {
                "pool_id": pool_id,
                "risk_score": risk_score,
                "risk_level": self.get_risk_level(risk_score),
                "prediction_horizon": "24h" if 'v2' in self.model_version else "current",
                "prediction_type": "predictive" if 'v2' in self.model_version else "reactive",
                "top_reasons": top_reasons,
                "early_warning_score": round(early_warning_score, 2) if early_warning_score else None,
                "features_used": feature_dict,
                "model_version": self.model_version,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "pool_id": pool_id,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def predict_all_pools(self) -> List[Dict]:
        """Generate risk predictions for all pools in database."""
        db = SessionLocal()
        try:
            pool_ids = db.query(Snapshot.pool_id).distinct().all()
            pool_ids = [p[0] for p in pool_ids]
            
            results = []
            for pool_id in pool_ids:
                result = self.predict_risk(pool_id)
                results.append(result)
            
            # Sort by risk score descending
            results.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
            
            return results
            
        finally:
            db.close()


def print_prediction_result(result: Dict):
    """Pretty print a prediction result."""
    print("\n" + "="*60)
    print(f"🎯 Risk Prediction: {result['pool_id']}")
    print("="*60)
    
    if 'error' in result:
        print(f"❌ Error: {result['error']}")
        return
    
    # Risk score with visual bar
    score = result['risk_score']
    level = result['risk_level']
    level_emoji = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🔴'}[level]
    
    bar_length = int(score / 2)
    bar = '█' * bar_length + '░' * (50 - bar_length)
    
    print(f"\n   Risk Score: {score}% {level_emoji} {level}")
    print(f"   [{bar}]")
    
    print(f"\n   Prediction Type: {result.get('prediction_type', 'unknown')}")
    print(f"   Prediction Horizon: {result.get('prediction_horizon', 'unknown')}")
    print(f"   Model Version: {result.get('model_version', 'unknown')}")
    
    if result.get('early_warning_score') is not None:
        print(f"   Early Warning Score: {result['early_warning_score']}")
    
    print("\n   🔍 Top Risk Factors (SHAP Explanations):")
    for i, reason in enumerate(result.get('top_reasons', []), 1):
        direction = '⬆️' if reason.get('direction') == 'increases_risk' else '⬇️'
        print(f"      {i}. {reason['feature']}: {reason['impact']:+.4f} {direction}")
        if reason.get('explanation'):
            print(f"         → {reason['explanation']}")
    
    print(f"\n   Timestamp: {result['timestamp']}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='VeriRisk Predictive Model Inference Server'
    )
    parser.add_argument('--pool', default='test_pool_1', 
                        help='Pool ID to analyze')
    parser.add_argument('--run-once', action='store_true', 
                        help='Run single prediction and exit')
    parser.add_argument('--all', action='store_true',
                        help='Predict risk for all pools')
    parser.add_argument('--model', type=str, default=None,
                        help='Path to model file')
    parser.add_argument('--json', action='store_true',
                        help='Output raw JSON instead of formatted')
    
    args = parser.parse_args()
    
    server = PredictiveModelServer(model_path=args.model)
    
    if server.model is None:
        print("\n⚠ Cannot run predictions without a trained model.")
        return
    
    if args.all:
        print("\n📊 Predicting risk for all pools...")
        results = server.predict_all_pools()
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"Risk Rankings (Highest to Lowest)")
            print(f"{'='*60}")
            for result in results:
                level_emoji = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🔴'}.get(
                    result.get('risk_level', ''), '⚪'
                )
                print(f"  {level_emoji} {result.get('risk_score', 0):5.1f}%  {result['pool_id']}")
            
            print(f"\n✓ Analyzed {len(results)} pools")
    
    elif args.run_once:
        result = server.predict_risk(args.pool)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_prediction_result(result)
    
    else:
        print("\nModel server ready.")
        print("Usage:")
        print("  python model_server.py --run-once --pool <pool_id>")
        print("  python model_server.py --all")
        print("  python model_server.py --run-once --pool test_pool_1 --json")


if __name__ == "__main__":
    main()
