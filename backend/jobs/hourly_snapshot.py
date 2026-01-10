#!/usr/bin/env python3
"""
Hourly Snapshot Collector Job

This module implements the hourly data ingestion job for collecting
time-series snapshots from DeFi protocols. It integrates with APScheduler
for automated periodic collection.

Key Features:
- Idempotent writes (no duplicates per hour)
- Graceful failure handling
- Support for live data + synthetic seeding
- Lock-based concurrency protection

Academic Keywords:
- Time-series data engineering
- Realistic DeFi data pipelines
- Data leakage prevention
"""

import logging
from datetime import datetime, timedelta
from threading import Lock
from typing import List, Dict, Optional
import random
import sys
import os
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from db_models.snapshot_history import SnapshotHistory, init_snapshot_history_db
from protocols import MultiProtocolFetcher
from config import config

try:
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(config.ETH_RPC_URL))
except Exception:
    w3 = None

logger = logging.getLogger(__name__)


class HourlySnapshotCollector:
    """
    Collects and stores hourly snapshots for all supported DeFi protocols.
    
    Designed for time-series risk modeling with:
    - Clean temporal data without leakage
    - Idempotent storage (upsert on conflict)
    - Support for seeding historical data
    """
    
    def __init__(self):
        self.fetch_lock = Lock()
        self.multi_protocol = MultiProtocolFetcher(w3) if w3 else None
        
        # Initialize the snapshot_history table
        init_snapshot_history_db()
        logger.info("✓ HourlySnapshotCollector initialized")
    
    def _round_to_hour(self, dt: datetime) -> datetime:
        """Round datetime to the hour (floor)"""
        return dt.replace(minute=0, second=0, microsecond=0)
    
    def collect_hourly_snapshot(self) -> List[str]:
        """
        Collect current snapshot for all protocols and store in history.
        
        This is the main job entry point, called by the scheduler.
        Uses locking to prevent overlapping runs.
        
        Returns:
            List of pool_ids successfully stored
        """
        if not self.fetch_lock.acquire(blocking=False):
            logger.info("⏭️ Hourly snapshot collection already running, skipping")
            return []
        
        try:
            logger.info("="*60)
            logger.info(f"🕐 HOURLY SNAPSHOT COLLECTION @ {datetime.utcnow().isoformat()}")
            logger.info("="*60)
            
            # Get current hour timestamp
            current_hour = self._round_to_hour(datetime.utcnow())
            
            # Fetch all protocol data
            if self.multi_protocol:
                protocols_data = self.multi_protocol.get_all_protocols()
            else:
                logger.warning("⚠️ Web3 not available, using synthetic data")
                protocols_data = self._generate_synthetic_protocols()
            
            stored_pools = []
            db = SessionLocal()
            
            try:
                for proto_data in protocols_data:
                    pool_id = proto_data.get('pool_id', 'unknown')
                    
                    # Create snapshot history record
                    snapshot = SnapshotHistory(
                        pool_id=pool_id,
                        timestamp=current_hour,
                        tvl=proto_data.get('tvl', 0),
                        volume_24h=proto_data.get('volume_24h', 0),
                        reserve0=proto_data.get('reserve0', 0),
                        reserve1=proto_data.get('reserve1', 0),
                        source=proto_data.get('data_source', 'unknown')
                    )
                    
                    # Upsert (insert or update on conflict)
                    try:
                        # Check if exists
                        existing = db.query(SnapshotHistory).filter(
                            and_(
                                SnapshotHistory.pool_id == pool_id,
                                SnapshotHistory.timestamp == current_hour
                            )
                        ).first()
                        
                        if existing:
                            # Update existing
                            existing.tvl = snapshot.tvl
                            existing.volume_24h = snapshot.volume_24h
                            existing.reserve0 = snapshot.reserve0
                            existing.reserve1 = snapshot.reserve1
                            existing.source = snapshot.source
                            logger.debug(f"  ↻ Updated {pool_id} @ {current_hour}")
                        else:
                            # Insert new
                            db.add(snapshot)
                            logger.debug(f"  ✓ Inserted {pool_id} @ {current_hour}")
                        
                        stored_pools.append(pool_id)
                        
                    except IntegrityError:
                        db.rollback()
                        logger.warning(f"  ⚠️ Duplicate entry for {pool_id}, skipped")
                
                db.commit()
                logger.info(f"\n✅ Stored {len(stored_pools)} hourly snapshots")
                
            finally:
                db.close()
            
            return stored_pools
            
        except Exception as e:
            logger.error(f"❌ Hourly snapshot collection failed: {e}")
            return []
        finally:
            self.fetch_lock.release()
    
    def seed_historical_data(self, hours: int = 48) -> int:
        """
        Seed synthetic historical data for feature computation.
        
        This populates the snapshot_history table with realistic
        historical data, enabling immediate feature computation
        for demonstration and testing purposes.
        
        Args:
            hours: Number of hours of historical data to generate
            
        Returns:
            Number of records inserted
        """
        logger.info(f"\n🌱 SEEDING {hours} HOURS OF HISTORICAL DATA")
        logger.info("="*60)
        
        db = SessionLocal()
        records_inserted = 0
        
        try:
            # Get list of all pool IDs
            pool_configs = self._get_pool_configs()
            
            # Generate hourly data for each pool
            for pool_id, config in pool_configs.items():
                base_tvl = config['base_tvl']
                base_volume = config['base_volume']
                volatility = config.get('volatility', 0.05)
                
                # Track previous values for realistic trends
                prev_tvl = base_tvl
                
                for h in range(hours, 0, -1):
                    timestamp = self._round_to_hour(
                        datetime.utcnow() - timedelta(hours=h)
                    )
                    
                    # Generate realistic time-series with trends
                    # Add some autocorrelation for realistic behavior
                    trend = random.gauss(0, volatility)
                    tvl = prev_tvl * (1 + trend)
                    tvl = max(tvl, base_tvl * 0.3)  # Floor at 30% of base
                    prev_tvl = tvl
                    
                    # Volume varies more randomly
                    volume_multiplier = random.uniform(0.5, 2.0)
                    volume_24h = base_volume * volume_multiplier
                    
                    # Reserves based on TVL
                    reserve_ratio = random.uniform(0.4, 0.6)
                    reserve0 = tvl * reserve_ratio
                    reserve1 = tvl * (1 - reserve_ratio)
                    
                    # Check if already exists
                    existing = db.query(SnapshotHistory).filter(
                        and_(
                            SnapshotHistory.pool_id == pool_id,
                            SnapshotHistory.timestamp == timestamp
                        )
                    ).first()
                    
                    if not existing:
                        snapshot = SnapshotHistory(
                            pool_id=pool_id,
                            timestamp=timestamp,
                            tvl=tvl,
                            volume_24h=volume_24h,
                            reserve0=reserve0,
                            reserve1=reserve1,
                            source='synthetic_seed'
                        )
                        db.add(snapshot)
                        records_inserted += 1
                
                logger.info(f"  ✓ Seeded {pool_id}")
            
            db.commit()
            logger.info(f"\n✅ Seeded {records_inserted} historical records")
            
        finally:
            db.close()
        
        return records_inserted
    
    def _get_pool_configs(self) -> Dict:
        """
        Get configuration for all supported pools.
        
        Returns realistic base values for synthetic data generation.
        """
        return {
            # Uniswap V2 pools
            'uniswap_v2_usdc_eth': {'base_tvl': 80_000_000, 'base_volume': 15_000_000, 'volatility': 0.03},
            'uniswap_v2_dai_eth': {'base_tvl': 45_000_000, 'base_volume': 8_000_000, 'volatility': 0.04},
            'uniswap_v2_usdt_eth': {'base_tvl': 50_000_000, 'base_volume': 10_000_000, 'volatility': 0.03},
            'uniswap_v2_wbtc_eth': {'base_tvl': 35_000_000, 'base_volume': 6_000_000, 'volatility': 0.05},
            
            # Uniswap V3 pools
            'uniswap_v3_usdc_eth_0.3pct': {'base_tvl': 120_000_000, 'base_volume': 40_000_000, 'volatility': 0.03},
            'uniswap_v3_usdc_eth_0.05pct': {'base_tvl': 200_000_000, 'base_volume': 80_000_000, 'volatility': 0.02},
            'uniswap_v3_dai_usdc_0.01pct': {'base_tvl': 60_000_000, 'base_volume': 20_000_000, 'volatility': 0.01},
            
            # Aave V3 markets
            'aave_v3_eth': {'base_tvl': 1_500_000_000, 'base_volume': 50_000_000, 'volatility': 0.02},
            'aave_v3_usdc': {'base_tvl': 1_200_000_000, 'base_volume': 40_000_000, 'volatility': 0.01},
            'aave_v3_dai': {'base_tvl': 800_000_000, 'base_volume': 25_000_000, 'volatility': 0.015},
            'aave_v3_wbtc': {'base_tvl': 600_000_000, 'base_volume': 20_000_000, 'volatility': 0.03},
            
            # Compound V2 markets
            'compound_v2_eth': {'base_tvl': 900_000_000, 'base_volume': 30_000_000, 'volatility': 0.025},
            'compound_v2_usdc': {'base_tvl': 1_000_000_000, 'base_volume': 35_000_000, 'volatility': 0.012},
            'compound_v2_dai': {'base_tvl': 600_000_000, 'base_volume': 18_000_000, 'volatility': 0.018},
            'compound_v2_usdt': {'base_tvl': 500_000_000, 'base_volume': 15_000_000, 'volatility': 0.015},
            
            # Curve pools
            'curve_3pool': {'base_tvl': 400_000_000, 'base_volume': 50_000_000, 'volatility': 0.008},
            'curve_steth': {'base_tvl': 500_000_000, 'base_volume': 60_000_000, 'volatility': 0.015},
            'curve_frax': {'base_tvl': 200_000_000, 'base_volume': 25_000_000, 'volatility': 0.012},
        }
    
    def _generate_synthetic_protocols(self) -> List[Dict]:
        """
        Generate synthetic protocol data when live APIs are unavailable.
        """
        pool_configs = self._get_pool_configs()
        results = []
        
        for pool_id, config in pool_configs.items():
            tvl = config['base_tvl'] * random.uniform(0.9, 1.1)
            volume = config['base_volume'] * random.uniform(0.7, 1.3)
            reserve_ratio = random.uniform(0.45, 0.55)
            
            results.append({
                'pool_id': pool_id,
                'tvl': tvl,
                'volume_24h': volume,
                'reserve0': tvl * reserve_ratio,
                'reserve1': tvl * (1 - reserve_ratio),
                'data_source': 'synthetic'
            })
        
        return results
    
    def get_snapshot_count(self, pool_id: Optional[str] = None) -> int:
        """
        Get count of historical snapshots.
        
        Args:
            pool_id: Optional filter by pool
            
        Returns:
            Number of snapshot records
        """
        db = SessionLocal()
        try:
            query = db.query(SnapshotHistory)
            if pool_id:
                query = query.filter(SnapshotHistory.pool_id == pool_id)
            return query.count()
        finally:
            db.close()
    
    def get_latest_snapshots(self, limit: int = 10) -> List[Dict]:
        """
        Get most recent snapshots across all pools.
        
        Returns:
            List of recent snapshot dictionaries
        """
        db = SessionLocal()
        try:
            snapshots = db.query(SnapshotHistory).order_by(
                SnapshotHistory.timestamp.desc()
            ).limit(limit).all()
            
            return [
                {
                    'pool_id': s.pool_id,
                    'timestamp': s.timestamp.isoformat(),
                    'tvl': s.tvl,
                    'volume_24h': s.volume_24h,
                    'source': s.source
                }
                for s in snapshots
            ]
        finally:
            db.close()


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Hourly Snapshot Collector')
    parser.add_argument('--collect', action='store_true', help='Run one collection cycle')
    parser.add_argument('--seed', type=int, default=0, help='Seed N hours of historical data')
    parser.add_argument('--status', action='store_true', help='Show collection status')
    args = parser.parse_args()
    
    collector = HourlySnapshotCollector()
    
    if args.seed > 0:
        records = collector.seed_historical_data(hours=args.seed)
        print(f"\n✓ Seeded {records} historical records")
    
    if args.collect:
        pools = collector.collect_hourly_snapshot()
        print(f"\n✓ Collected snapshots for {len(pools)} pools")
    
    if args.status:
        count = collector.get_snapshot_count()
        latest = collector.get_latest_snapshots(5)
        print(f"\n📊 Snapshot History Status:")
        print(f"   Total records: {count}")
        print(f"   Latest snapshots:")
        for s in latest:
            print(f"     - {s['pool_id']}: ${s['tvl']:,.0f} @ {s['timestamp']}")
