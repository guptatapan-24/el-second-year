#!/usr/bin/env python3
"""ML model inference server with SHAP explainability"""

import joblib
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
import shap
from database import SessionLocal, Snapshot
from config import config

class ModelServer:
    def __init__(self, model_path: str = None):
        self.model_path = model_path or config.MODEL_PATH
        self.model = None
        self.explainer = None
        self.feature_names = [
            'tvl', 'reserve0', 'reserve1', 'volume_24h',
            'tvl_pct_change_1h', 'reserve_imbalance',
            'volume_tvl_ratio', 'volatility_24h', 'leverage_ratio'
        ]
        self.load_model()
    
    def load_model(self):
        """Load trained model and setup explainer"""
        try:
            self.model = joblib.load(self.model_path)
            print(f"Model loaded from {self.model_path}")
            
            # Initialize SHAP explainer
            self.explainer = shap.TreeExplainer(self.model)
            print("SHAP explainer initialized")
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Run model_trainer.py first to train the model")
    
    def get_latest_snapshot(self, pool_id: str) -> Dict:
        """Get latest snapshot for a pool"""
        db = SessionLocal()
        try:
            snapshot = db.query(Snapshot).filter(
                Snapshot.pool_id == pool_id
            ).order_by(Snapshot.timestamp.desc()).first()
            
            if not snapshot:
                raise ValueError(f"No snapshot found for pool {pool_id}")
            
            # Prepare feature dict
            features = {
                'tvl': snapshot.tvl or 0,
                'reserve0': snapshot.reserve0 or 0,
                'reserve1': snapshot.reserve1 or 0,
                'volume_24h': snapshot.volume_24h or 0,
            }
            
            # Add derived features from JSON
            if snapshot.features:
                for key in ['tvl_pct_change_1h', 'reserve_imbalance',
                           'volume_tvl_ratio', 'volatility_24h', 'leverage_ratio']:
                    features[key] = snapshot.features.get(key, 0)
            
            return features
        finally:
            db.close()
    
    def compute_shap_explanations(self, features: np.ndarray) -> List[Dict]:
        """Compute SHAP values and return top contributing features"""
        if self.explainer is None:
            return [{"feature": "model_not_loaded", "impact": 0}]
        
        # Compute SHAP values
        shap_values = self.explainer.shap_values(features)
        
        # Get base value (expected model output)
        base_value = self.explainer.expected_value
        
        # For binary classification, use positive class SHAP values
        if isinstance(shap_values, list):
            shap_values = shap_values[1]  # Positive class
        
        # Get absolute SHAP values and rank
        feature_impacts = []
        for i, feature_name in enumerate(self.feature_names):
            impact = float(shap_values[0][i])
            feature_impacts.append({
                'feature': feature_name,
                'impact': impact,
                'abs_impact': abs(impact)
            })
        
        # Sort by absolute impact
        feature_impacts.sort(key=lambda x: x['abs_impact'], reverse=True)
        
        # Return top 3
        return feature_impacts[:3]
    
    def predict_risk(self, pool_id: str) -> Dict:
        """Predict risk score for a pool with explanations"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Get latest snapshot
        features_dict = self.get_latest_snapshot(pool_id)
        
        # Prepare features array
        X = np.array([[features_dict.get(f, 0) for f in self.feature_names]])
        
        # Predict probability
        risk_proba = self.model.predict_proba(X)[0][1]  # Probability of risk
        risk_score = float(risk_proba * 100)  # Scale to 0-100
        
        # Get SHAP explanations
        top_reasons = self.compute_shap_explanations(X)
        
        # Prepare result
        result = {
            'pool_id': pool_id,
            'risk_score': round(risk_score, 2),
            'risk_level': self.get_risk_level(risk_score),
            'top_reasons': [
                {
                    'feature': r['feature'],
                    'impact': round(r['impact'], 3)
                }
                for r in top_reasons
            ],
            'model_version': 'xgb_v1',
            'timestamp': datetime.utcnow().isoformat(),
            'features': features_dict
        }
        
        return result
    
    def get_risk_level(self, score: float) -> str:
        """Categorize risk score"""
        if score < 30:
            return 'LOW'
        elif score < 65:
            return 'MEDIUM'
        else:
            return 'HIGH'

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Model inference server')
    parser.add_argument('--pool', default='test_pool_1', help='Pool ID to analyze')
    parser.add_argument('--run-once', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    server = ModelServer()
    
    if args.run_once:
        try:
            result = server.predict_risk(args.pool)
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Model server ready. Use --run-once to test inference.")
