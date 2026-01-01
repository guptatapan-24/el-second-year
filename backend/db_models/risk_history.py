#!/usr/bin/env python3
"""
Risk History Model for VeriRisk Phase 3

Persists risk predictions over time for each protocol to enable:
- Trend analysis
- Escalation detection
- Historical risk auditing
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from datetime import datetime
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, engine

logger = logging.getLogger(__name__)


class RiskHistory(Base):
    """
    Historical risk prediction records.
    
    Stores each risk prediction with:
    - Risk score and level
    - Early warning score
    - SHAP-based explanations (top contributing features)
    - Timestamp for temporal analysis
    """
    __tablename__ = "risk_history"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Protocol identifier
    pool_id = Column(String(100), nullable=False, index=True)
    
    # Risk metrics
    risk_score = Column(Float, nullable=False, comment="Risk score 0-100")
    risk_level = Column(String(20), nullable=False, comment="LOW, MEDIUM, HIGH")
    early_warning_score = Column(Float, nullable=True, comment="Early warning composite 0-100")
    
    # SHAP-based explanations (stored as JSON)
    top_reasons = Column(JSON, nullable=True, comment="Top contributing features with SHAP values")
    
    # Model metadata
    model_version = Column(String(50), nullable=True)
    prediction_horizon = Column(String(20), nullable=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('ix_risk_history_pool_time', 'pool_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<RiskHistory(pool_id='{self.pool_id}', risk_score={self.risk_score}, risk_level='{self.risk_level}', timestamp='{self.timestamp}')>"
    
    def to_dict(self):
        """Convert to dictionary for API response"""
        return {
            'id': self.id,
            'pool_id': self.pool_id,
            'risk_score': self.risk_score,
            'risk_level': self.risk_level,
            'early_warning_score': self.early_warning_score,
            'top_reasons': self.top_reasons,
            'model_version': self.model_version,
            'prediction_horizon': self.prediction_horizon,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


def init_risk_history_db():
    """
    Initialize the risk_history table.
    
    Creates the table if it doesn't exist.
    """
    try:
        RiskHistory.__table__.create(engine, checkfirst=True)
        logger.info("✓ risk_history table initialized")
    except Exception as e:
        logger.error(f"Error initializing risk_history table: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_risk_history_db()
    print("✓ RiskHistory table created successfully")
