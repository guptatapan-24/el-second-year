#!/usr/bin/env python3
"""
Model Information API Router for VeriRisk Phase 6

Provides model transparency and explainability endpoints:
- GET /api/model/info - Model metadata for transparency
- GET /api/model/features - Feature descriptions with tooltips
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
import json
import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

router = APIRouter(prefix="/model")

# Feature descriptions for tooltip explanations
FEATURE_DESCRIPTIONS = {
    "tvl": {
        "name": "Total Value Locked (TVL)",
        "description": "The total amount of assets deposited in the protocol. A drop in TVL can indicate users withdrawing funds due to concerns.",
        "unit": "USD",
        "risk_direction": "Lower TVL or rapid decrease = Higher Risk"
    },
    "tvl_change_6h": {
        "name": "TVL Change (6h)",
        "description": "Percentage change in TVL over the past 6 hours. Sharp declines often precede larger crashes.",
        "unit": "Percentage",
        "risk_direction": "Negative values = Higher Risk"
    },
    "tvl_change_24h": {
        "name": "TVL Change (24h)",
        "description": "Percentage change in TVL over the past 24 hours. Sustained outflows indicate deteriorating confidence.",
        "unit": "Percentage",
        "risk_direction": "Negative values = Higher Risk"
    },
    "tvl_acceleration": {
        "name": "TVL Acceleration",
        "description": "Rate of change of TVL change (second derivative). Accelerating outflows suggest panic selling.",
        "unit": "Rate",
        "risk_direction": "Negative values = Higher Risk"
    },
    "volume_24h": {
        "name": "24h Trading Volume",
        "description": "Total trading volume in the past 24 hours. Unusual spikes may indicate panic or manipulation.",
        "unit": "USD",
        "risk_direction": "Abnormal spikes = Higher Risk"
    },
    "volume_spike_ratio": {
        "name": "Volume Spike Ratio",
        "description": "Current volume compared to the rolling average. Values >2 indicate unusual trading activity.",
        "unit": "Ratio",
        "risk_direction": "Values >2 = Higher Risk"
    },
    "reserve_imbalance": {
        "name": "Reserve Imbalance",
        "description": "The imbalance between reserve0 and reserve1 in a liquidity pool. High imbalance indicates one-sided pressure.",
        "unit": "Ratio (0-1)",
        "risk_direction": "Higher values = Higher Risk"
    },
    "reserve_imbalance_rate": {
        "name": "Reserve Imbalance Rate",
        "description": "Rate of change of reserve imbalance. Rapidly increasing imbalance suggests impending depeg or liquidity crisis.",
        "unit": "Rate",
        "risk_direction": "Positive values = Higher Risk"
    },
    "volatility_6h": {
        "name": "Short-term Volatility (6h)",
        "description": "Standard deviation of TVL returns over 6 hours. Higher volatility indicates market stress.",
        "unit": "Std Dev",
        "risk_direction": "Higher values = Higher Risk"
    },
    "volatility_24h": {
        "name": "Long-term Volatility (24h)",
        "description": "Standard deviation of TVL returns over 24 hours. Baseline measure of protocol stability.",
        "unit": "Std Dev",
        "risk_direction": "Higher values = Higher Risk"
    },
    "volatility_ratio": {
        "name": "Volatility Ratio",
        "description": "Ratio of short-term to long-term volatility. Values >1.5 indicate regime change or emerging crisis.",
        "unit": "Ratio",
        "risk_direction": "Values >1.5 = Higher Risk"
    },
    "early_warning_score": {
        "name": "Early Warning Score",
        "description": "Composite signal combining all risk factors. Designed to detect patterns that precede crashes.",
        "unit": "Score (0-100)",
        "risk_direction": "Higher values = Higher Risk"
    },
    "reserve0": {
        "name": "Reserve 0",
        "description": "Amount of the first token in the liquidity pool.",
        "unit": "Token Units",
        "risk_direction": "Context-dependent"
    },
    "reserve1": {
        "name": "Reserve 1",
        "description": "Amount of the second token in the liquidity pool.",
        "unit": "Token Units",
        "risk_direction": "Context-dependent"
    }
}

# Response models
class ModelInfoResponse(BaseModel):
    model_name: str
    model_type: str
    training_date: str
    features_used: List[str]
    auc_score: Optional[float]
    training_samples: int
    last_retrained: str
    hyperparameters: Dict
    model_description: str
    shap_explanation: str


class FeatureDescriptionResponse(BaseModel):
    feature: str
    name: str
    description: str
    unit: str
    risk_direction: str


class FeaturesListResponse(BaseModel):
    features: List[FeatureDescriptionResponse]
    total_features: int


def load_model_metadata() -> Dict:
    """Load model metadata from JSON file."""
    metadata_paths = [
        '/app/models/xgb_veririsk_v2_predictive_metadata.json',
        '/app/models/xgb_veririsk_v1_metadata.json',
        '../models/xgb_veririsk_v2_predictive_metadata.json',
        '../models/xgb_veririsk_v1_metadata.json',
    ]
    
    for path in metadata_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    
    # Return default if no metadata found
    return {
        "model_name": "xgb_veririsk_v1",
        "model_type": "XGBClassifier",
        "train_date": datetime.utcnow().isoformat(),
        "feature_names": list(FEATURE_DESCRIPTIONS.keys()),
        "metrics": {
            "auc": None,
            "n_train": 0
        },
        "hyperparameters": {
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.05
        }
    }


@router.get("/info", response_model=ModelInfoResponse)
def get_model_info():
    """
    Get comprehensive model information for transparency.
    
    Returns metadata about the ML model including:
    - Model name and type
    - Training date and sample count
    - Features used with importance
    - AUC score and hyperparameters
    - Human-readable descriptions
    
    This endpoint supports examiner trust by exposing model details.
    """
    metadata = load_model_metadata()
    
    # Extract features used
    features_used = metadata.get('feature_names', [])
    if not features_used:
        # Fallback to feature importance list
        importance = metadata.get('metrics', {}).get('feature_importance', [])
        features_used = [f['feature'] for f in importance] if importance else []
    
    # Get metrics
    metrics = metadata.get('metrics', {})
    
    return ModelInfoResponse(
        model_name=metadata.get('model_name', 'xgb_veririsk_v1'),
        model_type=metadata.get('model_type', 'XGBoost Classifier'),
        training_date=metadata.get('train_date', datetime.utcnow().isoformat()),
        features_used=features_used,
        auc_score=metrics.get('auc'),
        training_samples=metrics.get('n_train', 0) + metrics.get('n_test', 0),
        last_retrained=metadata.get('train_date', datetime.utcnow().isoformat()),
        hyperparameters=metadata.get('hyperparameters', {}),
        model_description="XGBoost gradient boosting classifier trained on historical DeFi protocol metrics to predict TVL crash risk. The model outputs a probability (0-100) representing the likelihood of significant TVL decline in the next 24 hours.",
        shap_explanation="SHAP (SHapley Additive exPlanations) values decompose each prediction into feature contributions. Positive SHAP values increase predicted risk; negative values decrease it. The top contributing features explain why the model assigned a particular risk score."
    )


@router.get("/features", response_model=FeaturesListResponse)
def get_feature_descriptions():
    """
    Get descriptions for all features used by the model.
    
    Returns human-readable explanations for each feature,
    including what it measures and how it affects risk.
    Useful for tooltips and explainability UI.
    """
    features = [
        FeatureDescriptionResponse(
            feature=key,
            name=val['name'],
            description=val['description'],
            unit=val['unit'],
            risk_direction=val['risk_direction']
        )
        for key, val in FEATURE_DESCRIPTIONS.items()
    ]
    
    return FeaturesListResponse(
        features=features,
        total_features=len(features)
    )


@router.get("/architecture")
def get_architecture_info():
    """
    Get system architecture overview for documentation.
    
    Returns a structured description of the VeriRisk pipeline.
    """
    return {
        "system_name": "VeriRisk",
        "version": "1.0.0",
        "description": "Verifiable AI Risk Oracle for DeFi Protocols",
        "pipeline_stages": [
            {
                "stage": 1,
                "name": "Data Ingestion",
                "description": "Fetches real-time data from DeFi protocols via APIs and on-chain sources",
                "components": ["Infura RPC", "TheGraph", "CoinGecko API"],
                "frequency": "Every 5 minutes"
            },
            {
                "stage": 2,
                "name": "Feature Engineering",
                "description": "Computes predictive features from raw protocol data",
                "components": ["TVL Trends", "Volume Analysis", "Reserve Balance", "Volatility Metrics"],
                "output": "10 engineered features per protocol"
            },
            {
                "stage": 3,
                "name": "ML Inference",
                "description": "XGBoost model predicts crash probability from features",
                "components": ["XGBoost Classifier", "SHAP Explainer"],
                "output": "Risk Score (0-100) + Top 3 Contributing Factors"
            },
            {
                "stage": 4,
                "name": "Simulation Engine",
                "description": "What-if analysis by injecting hypothetical stress scenarios",
                "components": ["TVL Shock", "Volume Spike", "Volatility Surge"],
                "output": "Simulated Risk Score + Delta Analysis"
            },
            {
                "stage": 5,
                "name": "Alert System",
                "description": "Generates alerts based on risk thresholds and escalation patterns",
                "components": ["High Risk Alert", "Early Warning Alert", "Risk Spike Alert"],
                "thresholds": "HIGH >= 65, MEDIUM >= 30, LOW < 30"
            },
            {
                "stage": 6,
                "name": "Frontend Visualization",
                "description": "Interactive dashboard for monitoring and exploration",
                "components": ["Risk Gauges", "Timeline Charts", "SHAP Panels", "Alert Feed"]
            }
        ],
        "ml_model": {
            "algorithm": "XGBoost (Gradient Boosting)",
            "task": "Binary Classification (Crash vs No-Crash)",
            "output_interpretation": "Probability * 100 = Risk Score",
            "why_xgboost": [
                "Fast inference (<10ms per prediction)",
                "Handles tabular financial data well",
                "Built-in feature importance",
                "Compatible with SHAP TreeExplainer",
                "Production-proven in finance applications"
            ]
        },
        "explainability": {
            "method": "SHAP (SHapley Additive exPlanations)",
            "output": "Feature-level contribution scores",
            "interpretation": "Positive SHAP = Increases Risk, Negative SHAP = Decreases Risk",
            "why_shap": [
                "Consistent and accurate feature attribution",
                "Model-agnostic methodology",
                "Fast TreeExplainer for gradient boosting",
                "Research-backed (NIPS 2017 paper)"
            ]
        },
        "disclaimers": [
            "This system provides early-warning risk signals, not financial advice.",
            "Predictions are probabilistic and may not capture all risk factors.",
            "Past performance does not guarantee future results.",
            "Built for academic demonstration purposes."
        ]
    }