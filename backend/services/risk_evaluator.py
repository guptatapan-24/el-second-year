#!/usr/bin/env python3
"""
Risk Evaluation Service for VeriRisk Phase 3

This service handles:
1. Risk prediction and storage to risk_history
2. Alert evaluation and generation
3. Integration with model_server for predictions
4. SHAP-based explanations for every prediction

Designed for automated pipeline execution.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import desc, and_
from sqlalchemy.orm import Session

import sys
import os
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, Snapshot
from db_models.risk_history import RiskHistory, init_risk_history_db
from db_models.alert import Alert, AlertType, ALERT_THRESHOLDS, init_alerts_db
from model_server import PredictiveModelServer

logger = logging.getLogger(__name__)


class RiskEvaluator:
    """
    Orchestrates risk evaluation, history tracking, and alert generation.
    
    Key responsibilities:
    - Predict risk for all pools
    - Store predictions in risk_history
    - Evaluate alert conditions
    - Generate alerts with SHAP explanations
    """
    
    def __init__(self):
        self.model_server = PredictiveModelServer()
        # Initialize tables
        init_risk_history_db()
        init_alerts_db()
        logger.info("✓ RiskEvaluator initialized")
    
    def predict_and_store_risk(self, pool_id: str) -> Optional[Dict]:
        """
        Predict risk for a single pool and store in risk_history.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Risk prediction result dict or None on error
        """
        try:
            # Get prediction from model server
            result = self.model_server.predict_risk(pool_id)
            
            if 'error' in result:
                logger.warning(f"Prediction error for {pool_id}: {result['error']}")
                return None
            
            # Store in risk_history
            db = SessionLocal()
            try:
                risk_record = RiskHistory(
                    pool_id=pool_id,
                    risk_score=result['risk_score'],
                    risk_level=result['risk_level'],
                    early_warning_score=result.get('early_warning_score'),
                    top_reasons=result.get('top_reasons', []),
                    model_version=result.get('model_version'),
                    prediction_horizon=result.get('prediction_horizon'),
                    timestamp=datetime.utcnow()
                )
                db.add(risk_record)
                db.commit()
                
                logger.info(
                    f"📊 Stored risk: {pool_id} → "
                    f"Score={result['risk_score']:.1f} "
                    f"Level={result['risk_level']}"
                )
                
                return result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error predicting/storing risk for {pool_id}: {e}")
            return None
    
    def predict_all_pools(self) -> List[Dict]:
        """
        Predict and store risk for all pools in the database.
        
        Returns:
            List of prediction results
        """
        db = SessionLocal()
        try:
            # Get all unique pool IDs
            pool_ids = db.query(Snapshot.pool_id).distinct().all()
            pool_ids = [p[0] for p in pool_ids]
            
            logger.info(f"🔄 Predicting risk for {len(pool_ids)} pools...")
            
            results = []
            for pool_id in pool_ids:
                result = self.predict_and_store_risk(pool_id)
                if result:
                    results.append(result)
            
            logger.info(f"✅ Stored {len(results)} risk predictions")
            return results
            
        finally:
            db.close()
    
    def get_previous_risk(self, pool_id: str) -> Optional[RiskHistory]:
        """
        Get the most recent risk_history entry for a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Most recent RiskHistory record or None
        """
        db = SessionLocal()
        try:
            # Get second most recent (skip current if just inserted)
            records = (
                db.query(RiskHistory)
                .filter(RiskHistory.pool_id == pool_id)
                .order_by(desc(RiskHistory.timestamp))
                .limit(2)
                .all()
            )
            
            if len(records) >= 2:
                return records[1]  # Return previous (not current)
            return None
            
        finally:
            db.close()
    
    def has_recent_alert(self, pool_id: str, alert_type: str, hours: int = 1) -> bool:
        """
        Check if a similar alert was recently generated.
        
        Prevents duplicate alerts within the specified time window.
        
        Args:
            pool_id: Pool identifier
            alert_type: Type of alert
            hours: Lookback window in hours
            
        Returns:
            True if a similar active alert exists
        """
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            existing = db.query(Alert).filter(
                and_(
                    Alert.pool_id == pool_id,
                    Alert.alert_type == alert_type,
                    Alert.status == 'active',
                    Alert.created_at >= cutoff
                )
            ).first()
            
            return existing is not None
            
        finally:
            db.close()
    
    def create_alert(
        self,
        pool_id: str,
        alert_type: str,
        risk_score: float,
        risk_level: str,
        message: str,
        top_reasons: List[Dict],
        previous_risk_level: Optional[str] = None,
        previous_risk_score: Optional[float] = None
    ) -> Alert:
        """
        Create and store a new alert.
        
        Args:
            pool_id: Pool identifier
            alert_type: Type of alert
            risk_score: Current risk score
            risk_level: Current risk level
            message: Human-readable alert message
            top_reasons: SHAP-based explanations
            previous_risk_level: Previous risk level (for escalation)
            previous_risk_score: Previous risk score
            
        Returns:
            Created Alert object
        """
        db = SessionLocal()
        try:
            alert = Alert(
                pool_id=pool_id,
                alert_type=alert_type,
                risk_score=risk_score,
                risk_level=risk_level,
                message=message,
                top_reasons=top_reasons,
                status='active',
                previous_risk_level=previous_risk_level,
                previous_risk_score=previous_risk_score,
                created_at=datetime.utcnow()
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            logger.warning(
                f"🚨 ALERT [{alert_type}] {pool_id}: {message} "
                f"(Score: {risk_score:.1f}, Level: {risk_level})"
            )
            
            return alert
            
        finally:
            db.close()
    
    def evaluate_alerts_for_pool(self, pool_id: str, current_risk: Dict) -> List[Alert]:
        """
        Evaluate alert conditions for a single pool.
        
        Checks:
        1. HIGH_RISK_ALERT: risk_score >= 65
        2. EARLY_WARNING_ALERT: early_warning_score >= 40
        3. RISK_ESCALATION_ALERT: risk_level transitions
        
        Args:
            pool_id: Pool identifier
            current_risk: Current risk prediction dict
            
        Returns:
            List of generated alerts
        """
        alerts = []
        
        risk_score = current_risk.get('risk_score', 0)
        risk_level = current_risk.get('risk_level', 'LOW')
        early_warning = current_risk.get('early_warning_score')
        top_reasons = current_risk.get('top_reasons', [])
        
        # Get previous risk for escalation check
        previous = self.get_previous_risk(pool_id)
        
        # 1. HIGH_RISK_ALERT
        if risk_score >= ALERT_THRESHOLDS['high_risk_score']:
            if not self.has_recent_alert(pool_id, AlertType.HIGH_RISK_ALERT.value):
                # Format top reasons for message
                reason_text = ""
                if top_reasons:
                    reason_text = f" Top factor: {top_reasons[0].get('feature', 'unknown')}"
                
                alert = self.create_alert(
                    pool_id=pool_id,
                    alert_type=AlertType.HIGH_RISK_ALERT.value,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    message=f"High risk detected for {pool_id}. Score: {risk_score:.1f}%.{reason_text}",
                    top_reasons=top_reasons
                )
                alerts.append(alert)
        
        # 2. EARLY_WARNING_ALERT
        # Only generate early warning if:
        # - early_warning_score >= threshold (40)
        # - AND risk_score is not LOW (>= 20) to avoid false positives for stable protocols
        # This prevents alerts for protocols that are stable but have neutral EWS baseline
        if early_warning and early_warning >= ALERT_THRESHOLDS['early_warning_score']:
            # Additional check: Don't alert for very low risk scores (stable protocols)
            if risk_score >= 20:  # Only alert if risk_score indicates some concern
                if not self.has_recent_alert(pool_id, AlertType.EARLY_WARNING_ALERT.value):
                    alert = self.create_alert(
                        pool_id=pool_id,
                        alert_type=AlertType.EARLY_WARNING_ALERT.value,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        message=f"Early warning signal for {pool_id}. EWS: {early_warning:.1f}. Potential risk escalation.",
                        top_reasons=top_reasons
                    )
                    alerts.append(alert)
        
        # 3. RISK_ESCALATION_ALERT
        if previous:
            prev_level = previous.risk_level
            transition = (prev_level, risk_level)
            
            if transition in ALERT_THRESHOLDS['escalation_transitions']:
                if not self.has_recent_alert(pool_id, AlertType.RISK_ESCALATION_ALERT.value):
                    alert = self.create_alert(
                        pool_id=pool_id,
                        alert_type=AlertType.RISK_ESCALATION_ALERT.value,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        message=f"Risk level escalated for {pool_id}: {prev_level} → {risk_level}",
                        top_reasons=top_reasons,
                        previous_risk_level=prev_level,
                        previous_risk_score=previous.risk_score
                    )
                    alerts.append(alert)
        
        # 4. RISK_SPIKE (Phase 5) - Detect sudden risk score jumps
        # Independent of risk level - captures sudden instability
        if previous:
            prev_score = previous.risk_score
            score_delta = risk_score - prev_score
            
            if score_delta >= ALERT_THRESHOLDS.get('risk_spike_delta', 30):
                if not self.has_recent_alert(pool_id, AlertType.RISK_SPIKE.value):
                    # Format top reason for spike
                    reason_text = ""
                    if top_reasons:
                        reason_text = f" Key factor: {top_reasons[0].get('feature', 'unknown')}"
                    
                    alert = self.create_alert(
                        pool_id=pool_id,
                        alert_type=AlertType.RISK_SPIKE.value,
                        risk_score=risk_score,
                        risk_level=risk_level,
                        message=f"Sudden risk spike detected for {pool_id}. Score jumped +{score_delta:.1f} points.{reason_text}",
                        top_reasons=top_reasons,
                        previous_risk_level=previous.risk_level,
                        previous_risk_score=prev_score
                    )
                    alerts.append(alert)
        
        return alerts
    
    def evaluate_all_alerts(self) -> List[Alert]:
        """
        Evaluate alerts for all pools based on latest risk_history.
        
        Returns:
            List of all generated alerts
        """
        db = SessionLocal()
        try:
            # Get all pool IDs from risk_history
            pool_ids = db.query(RiskHistory.pool_id).distinct().all()
            pool_ids = [p[0] for p in pool_ids]
            
            logger.info(f"🔍 Evaluating alerts for {len(pool_ids)} pools...")
            
            all_alerts = []
            for pool_id in pool_ids:
                # Get latest risk for this pool
                latest = (
                    db.query(RiskHistory)
                    .filter(RiskHistory.pool_id == pool_id)
                    .order_by(desc(RiskHistory.timestamp))
                    .first()
                )
                
                if latest:
                    current_risk = {
                        'risk_score': latest.risk_score,
                        'risk_level': latest.risk_level,
                        'early_warning_score': latest.early_warning_score,
                        'top_reasons': latest.top_reasons
                    }
                    
                    alerts = self.evaluate_alerts_for_pool(pool_id, current_risk)
                    all_alerts.extend(alerts)
            
            if all_alerts:
                logger.warning(f"🚨 Generated {len(all_alerts)} new alerts")
            else:
                logger.info("✅ No new alerts generated")
            
            return all_alerts
            
        finally:
            db.close()
    
    def get_active_alerts(self) -> List[Dict]:
        """
        Get all active alerts.
        
        Returns:
            List of alert dicts
        """
        db = SessionLocal()
        try:
            alerts = (
                db.query(Alert)
                .filter(Alert.status == 'active')
                .order_by(desc(Alert.created_at))
                .all()
            )
            return [a.to_dict() for a in alerts]
        finally:
            db.close()
    
    def get_latest_risk(self, pool_id: str) -> Optional[Dict]:
        """
        Get latest risk prediction for a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Risk prediction dict or None
        """
        db = SessionLocal()
        try:
            latest = (
                db.query(RiskHistory)
                .filter(RiskHistory.pool_id == pool_id)
                .order_by(desc(RiskHistory.timestamp))
                .first()
            )
            return latest.to_dict() if latest else None
        finally:
            db.close()
    
    def get_risk_history(self, pool_id: str, hours: int = 24) -> List[Dict]:
        """
        Get risk history for a pool.
        
        Args:
            pool_id: Pool identifier
            hours: Number of hours of history
            
        Returns:
            List of risk history dicts, oldest first
        """
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            records = (
                db.query(RiskHistory)
                .filter(
                    and_(
                        RiskHistory.pool_id == pool_id,
                        RiskHistory.timestamp >= cutoff
                    )
                )
                .order_by(RiskHistory.timestamp.asc())
                .all()
            )
            return [r.to_dict() for r in records]
        finally:
            db.close()


# Singleton instance for scheduler use
_risk_evaluator = None


def get_risk_evaluator() -> RiskEvaluator:
    """Get or create singleton RiskEvaluator instance."""
    global _risk_evaluator
    if _risk_evaluator is None:
        _risk_evaluator = RiskEvaluator()
    return _risk_evaluator


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("Risk Evaluator Test")
    print("="*60)
    
    evaluator = RiskEvaluator()
    
    # Test prediction for all pools
    results = evaluator.predict_all_pools()
    print(f"\n✓ Predicted risk for {len(results)} pools")
    
    # Test alert evaluation
    alerts = evaluator.evaluate_all_alerts()
    print(f"✓ Generated {len(alerts)} alerts")
