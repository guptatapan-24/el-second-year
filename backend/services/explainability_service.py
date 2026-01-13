#!/usr/bin/env python3
"""
Explainability Service for VeriRisk Phase 6

Provides:
1. Natural language explanations from SHAP output
2. Risk confidence scoring based on feature stability
3. Human-readable summaries for non-technical users
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# Feature name mappings for human-readable output
FEATURE_NAMES_READABLE = {
    'tvl': 'Total Value Locked',
    'tvl_change_6h': 'Short-term TVL decline',
    'tvl_change_24h': 'Daily TVL decline',
    'tvl_acceleration': 'Accelerating outflows',
    'volume_24h': 'Trading volume',
    'volume_spike_ratio': 'Unusual trading activity',
    'reserve_imbalance': 'Liquidity imbalance',
    'reserve_imbalance_rate': 'Increasing imbalance',
    'reserve0': 'Reserve balance',
    'reserve1': 'Reserve balance',
    'volatility_6h': 'Short-term volatility',
    'volatility_24h': 'Long-term volatility',
    'volatility_ratio': 'Volatility surge',
    'early_warning_score': 'Early warning signals',
}

# Impact direction descriptions
IMPACT_DESCRIPTIONS = {
    'tvl': {
        'positive': 'Low TVL is increasing risk',
        'negative': 'Healthy TVL is reducing risk'
    },
    'tvl_change_6h': {
        'positive': 'Sharp recent TVL decline is increasing risk',
        'negative': 'Stable TVL is reducing risk'
    },
    'tvl_change_24h': {
        'positive': 'Sustained TVL outflows are increasing risk',
        'negative': 'TVL stability is reducing risk'
    },
    'tvl_acceleration': {
        'positive': 'Accelerating outflows are increasing risk',
        'negative': 'Decelerating outflows are reducing risk'
    },
    'volume_spike_ratio': {
        'positive': 'Unusual trading activity is increasing risk',
        'negative': 'Normal trading volume is reducing risk'
    },
    'reserve_imbalance': {
        'positive': 'Liquidity imbalance is increasing risk',
        'negative': 'Balanced reserves are reducing risk'
    },
    'reserve_imbalance_rate': {
        'positive': 'Increasing imbalance is increasing risk',
        'negative': 'Stable reserves are reducing risk'
    },
    'volatility_6h': {
        'positive': 'High short-term volatility is increasing risk',
        'negative': 'Low volatility is reducing risk'
    },
    'volatility_24h': {
        'positive': 'Elevated volatility is increasing risk',
        'negative': 'Market stability is reducing risk'
    },
    'volatility_ratio': {
        'positive': 'Volatility surge is increasing risk',
        'negative': 'Consistent volatility is reducing risk'
    },
    'early_warning_score': {
        'positive': 'Multiple warning signals detected',
        'negative': 'No significant warning signals'
    }
}


@dataclass
class ExplainabilitySummary:
    """Container for natural language risk explanation."""
    summary: str
    top_factors: List[str]
    confidence: str  # HIGH, MEDIUM, LOW
    confidence_reason: str
    risk_direction_hint: str


def generate_natural_language_summary(
    top_reasons: List[Dict],
    risk_score: float,
    risk_level: str,
    features_used: Optional[Dict] = None
) -> ExplainabilitySummary:
    """
    Generate human-readable explanation from SHAP output.
    
    Args:
        top_reasons: List of SHAP-based top contributing features
        risk_score: The overall risk score (0-100)
        risk_level: LOW, MEDIUM, or HIGH
        features_used: Optional dict of feature values
        
    Returns:
        ExplainabilitySummary with natural language explanation
    """
    if not top_reasons:
        return ExplainabilitySummary(
            summary="Insufficient data to generate detailed explanation.",
            top_factors=[],
            confidence="LOW",
            confidence_reason="Missing SHAP analysis data",
            risk_direction_hint="Monitor this protocol for more data"
        )
    
    # Build natural language factors
    factor_sentences = []
    positive_factors = []  # Increase risk
    negative_factors = []  # Decrease risk
    
    for reason in top_reasons[:3]:
        feature = reason.get('feature', 'unknown')
        impact = reason.get('impact', 0)
        direction = reason.get('direction', 'unknown')
        
        readable_name = FEATURE_NAMES_READABLE.get(feature, feature.replace('_', ' '))
        
        # Get impact description
        if feature in IMPACT_DESCRIPTIONS:
            if impact > 0 or direction == 'increases_risk':
                desc = IMPACT_DESCRIPTIONS[feature]['positive']
                positive_factors.append(readable_name)
            else:
                desc = IMPACT_DESCRIPTIONS[feature]['negative']
                negative_factors.append(readable_name)
        else:
            if impact > 0 or direction == 'increases_risk':
                desc = f"{readable_name} is contributing to higher risk"
                positive_factors.append(readable_name)
            else:
                desc = f"{readable_name} is reducing risk"
                negative_factors.append(readable_name)
        
        factor_sentences.append(desc)
    
    # Build summary sentence
    if risk_level == 'HIGH':
        if positive_factors:
            summary = f"Risk is elevated primarily due to {', '.join(positive_factors[:2])}. "
            if len(positive_factors) > 2:
                summary += f"Additional concern from {positive_factors[2]}. "
            summary += "Consider this protocol high-risk for potential TVL decline."
        else:
            summary = "Risk is elevated based on multiple factors in the model analysis."
    
    elif risk_level == 'MEDIUM':
        summary = "Risk is moderate. "
        if positive_factors:
            summary += f"Key factors: {', '.join(positive_factors[:2])}. "
        if negative_factors:
            summary += f"Some stability from {negative_factors[0]}. "
        summary += "Monitor closely for changes."
    
    else:  # LOW
        summary = "Risk is low. "
        if negative_factors:
            summary += f"Stability indicators: {', '.join(negative_factors[:2])}. "
        if positive_factors:
            summary += f"Minor concern: {positive_factors[0]}. "
        else:
            summary += "No significant risk factors detected."
    
    # Calculate confidence
    confidence, confidence_reason = calculate_confidence_from_features(
        top_reasons, features_used
    )
    
    # Risk direction hint
    if len(positive_factors) > len(negative_factors):
        hint = "Risk factors outweigh stabilizers - exercise caution"
    elif len(negative_factors) > len(positive_factors):
        hint = "Stabilizing factors present - relatively safe position"
    else:
        hint = "Mixed signals - continue monitoring"
    
    return ExplainabilitySummary(
        summary=summary,
        top_factors=factor_sentences,
        confidence=confidence,
        confidence_reason=confidence_reason,
        risk_direction_hint=hint
    )


def calculate_confidence_from_features(
    top_reasons: List[Dict],
    features_used: Optional[Dict] = None
) -> Tuple[str, str]:
    """
    Calculate prediction confidence based on feature stability.
    
    Confidence levels:
    - HIGH: Low feature variance, strong SHAP signals
    - MEDIUM: Moderate variance or mixed signals
    - LOW: High variance, extreme values, or sparse data
    
    Args:
        top_reasons: SHAP-based top features
        features_used: Feature values dict
        
    Returns:
        Tuple of (confidence_level, reason)
    """
    if not top_reasons:
        return ("LOW", "Insufficient SHAP data for confidence assessment")
    
    # Check SHAP impact magnitudes
    impacts = [abs(r.get('impact', 0)) for r in top_reasons]
    max_impact = max(impacts) if impacts else 0
    avg_impact = sum(impacts) / len(impacts) if impacts else 0
    
    # Check feature values if available
    extreme_features = 0
    if features_used:
        # Detect extreme values that reduce confidence
        thresholds = {
            'tvl_change_6h': (-0.3, 0.3),
            'tvl_change_24h': (-0.5, 0.5),
            'tvl_acceleration': (-0.2, 0.2),
            'volume_spike_ratio': (0.3, 5.0),
            'volatility_ratio': (0.5, 3.0),
            'reserve_imbalance': (0, 0.5),
        }
        
        for feature, (low, high) in thresholds.items():
            val = features_used.get(feature)
            if val is not None:
                if val < low or val > high:
                    extreme_features += 1
    
    # Determine confidence level
    if extreme_features >= 3:
        return ("LOW", "Extreme feature values indicate unusual market conditions")
    elif extreme_features >= 1 or avg_impact > 0.3:
        return ("MEDIUM", "Some volatility in key metrics")
    elif max_impact > 0.1 and avg_impact > 0.05:
        return ("HIGH", "Consistent feature patterns with clear signals")
    else:
        return ("MEDIUM", "Moderate signal strength in feature analysis")


def enhance_risk_response_with_explainability(
    risk_result: Dict
) -> Dict:
    """
    Enhance a risk prediction response with explainability data.
    
    Adds:
    - natural_language_summary: Human-readable explanation
    - confidence: HIGH/MEDIUM/LOW
    - confidence_reason: Why this confidence level
    - enhanced_top_reasons: Top reasons with readable descriptions
    
    Args:
        risk_result: Original risk prediction dict
        
    Returns:
        Enhanced dict with explainability fields
    """
    top_reasons = risk_result.get('top_reasons', [])
    risk_score = risk_result.get('risk_score', 0)
    risk_level = risk_result.get('risk_level', 'LOW')
    features_used = risk_result.get('features_used', {})
    
    # Generate natural language summary
    explainability = generate_natural_language_summary(
        top_reasons=top_reasons,
        risk_score=risk_score,
        risk_level=risk_level,
        features_used=features_used
    )
    
    # Enhance top reasons with readable descriptions
    enhanced_reasons = []
    for reason in top_reasons:
        feature = reason.get('feature', 'unknown')
        impact = reason.get('impact', 0)
        direction = reason.get('direction', 'unknown')
        
        readable_name = FEATURE_NAMES_READABLE.get(feature, feature.replace('_', ' '))
        
        # Get contextual description
        if feature in IMPACT_DESCRIPTIONS:
            key = 'positive' if (impact > 0 or direction == 'increases_risk') else 'negative'
            description = IMPACT_DESCRIPTIONS[feature][key]
        else:
            description = reason.get('explanation', f'{readable_name} affecting risk score')
        
        enhanced_reasons.append({
            **reason,
            'readable_name': readable_name,
            'description': description
        })
    
    # Add explainability fields to result
    enhanced_result = {
        **risk_result,
        'explainability': {
            'summary': explainability.summary,
            'top_factors': explainability.top_factors,
            'risk_direction_hint': explainability.risk_direction_hint
        },
        'confidence': explainability.confidence,
        'confidence_reason': explainability.confidence_reason,
        'enhanced_top_reasons': enhanced_reasons
    }
    
    return enhanced_result


if __name__ == "__main__":
    # Demo test
    sample_result = {
        'pool_id': 'test_pool',
        'risk_score': 72.5,
        'risk_level': 'HIGH',
        'top_reasons': [
            {'feature': 'tvl_change_6h', 'impact': 0.25, 'direction': 'increases_risk'},
            {'feature': 'volatility_ratio', 'impact': 0.18, 'direction': 'increases_risk'},
            {'feature': 'reserve_imbalance', 'impact': -0.05, 'direction': 'decreases_risk'}
        ],
        'features_used': {
            'tvl_change_6h': -0.35,
            'volatility_ratio': 2.1,
            'reserve_imbalance': 0.15
        }
    }
    
    enhanced = enhance_risk_response_with_explainability(sample_result)
    
    print("\n" + "="*60)
    print("Explainability Service Demo")
    print("="*60)
    print(f"\nRisk Score: {enhanced['risk_score']}")
    print(f"Risk Level: {enhanced['risk_level']}")
    print(f"Confidence: {enhanced['confidence']}")
    print(f"Confidence Reason: {enhanced['confidence_reason']}")
    print(f"\nSummary: {enhanced['explainability']['summary']}")
    print(f"\nTop Factors:")
    for factor in enhanced['explainability']['top_factors']:
        print(f"  - {factor}")
    print(f"\nDirection Hint: {enhanced['explainability']['risk_direction_hint']}")