#!/usr/bin/env python3
"""
Snapshot History Model for Time-Series Data Storage

This module provides the SQLAlchemy model for storing hourly historical snapshots
of DeFi protocol metrics. It enables time-series analysis and predictive feature
computation without data leakage.

Academic Keywords:
- Time-series risk modeling
- Rolling window analysis
- DeFi protocol monitoring
- Predictive signal extraction
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, Index
from datetime import datetime, timedelta
import logging
import sys
import os
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, engine

logger = logging.getLogger(__name__)


class SnapshotHistory(Base):
    """
    Historical time-series snapshot storage for DeFi protocols.
    
    Stores hourly snapshots enabling:
    - Rolling window feature computation (6h, 24h windows)
    - Trend analysis and acceleration metrics
    - Volume spike detection
    - Reserve imbalance monitoring
    
    Schema designed to prevent data leakage in ML pipelines by
    maintaining strict temporal ordering.
    """
    __tablename__ = "snapshot_history"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Protocol identifier (e.g., 'uniswap_v2_usdc_eth', 'aave_v3_eth')
    pool_id = Column(String(100), nullable=False, index=True)
    
    # Hour-rounded UTC timestamp for deduplication
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Core metrics
    tvl = Column(Float, nullable=True, comment="Total Value Locked in USD")
    volume_24h = Column(Float, nullable=True, comment="24-hour trading volume in USD")
    reserve0 = Column(Float, nullable=True, comment="Reserve of token0")
    reserve1 = Column(Float, nullable=True, comment="Reserve of token1")
    
    # Data source tracking
    source = Column(String(50), nullable=True, comment="Data source: defillama, synthetic, etc.")
    
    # Unique constraint to prevent duplicate hourly entries
    __table_args__ = (
        UniqueConstraint('pool_id', 'timestamp', name='uq_pool_timestamp'),
        Index('ix_snapshot_history_pool_time', 'pool_id', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<SnapshotHistory(pool_id='{self.pool_id}', timestamp='{self.timestamp}', tvl={self.tvl})>"
    
    @staticmethod
    def round_to_hour(dt: datetime) -> datetime:
        """
        Round datetime to the nearest hour (floor).
        
        This ensures consistent hourly bucketing and prevents
        duplicate entries within the same hour.
        
        Args:
            dt: Input datetime
            
        Returns:
            Datetime rounded down to the hour
        """
        return dt.replace(minute=0, second=0, microsecond=0)
    
    @classmethod
    def get_hours_ago(cls, hours: int) -> datetime:
        """
        Get the rounded timestamp for N hours ago.
        
        Useful for window-based queries (6h, 24h lookbacks).
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Hour-rounded timestamp
        """
        return cls.round_to_hour(datetime.utcnow() - timedelta(hours=hours))


def init_snapshot_history_db():
    """
    Initialize the snapshot_history table.
    
    Creates the table if it doesn't exist, preserving
    existing data for incremental updates.
    """
    try:
        SnapshotHistory.__table__.create(engine, checkfirst=True)
        logger.info("✓ snapshot_history table initialized")
    except Exception as e:
        logger.error(f"Error initializing snapshot_history table: {e}")
        raise


if __name__ == "__main__":
    # Initialize table when run directly
    logging.basicConfig(level=logging.INFO)
    init_snapshot_history_db()
    print("✓ SnapshotHistory table created successfully")
