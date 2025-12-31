#!/usr/bin/env python3
"""
Debug Time-Series CLI Tool

Command-line tool for validating and inspecting time-series data
and computed features. Essential for debugging data pipelines
and ensuring ML-readiness.

Usage:
    python debug_timeseries.py --pool <pool_id>
    python debug_timeseries.py --all
    python debug_timeseries.py --status
    python debug_timeseries.py --sanity-check

Outputs:
    - Last 24 hourly TVL values
    - Computed feature values
    - Missing-data warnings
    - Sanity-check flags

Academic Keywords:
    - Time-series validation
    - Data quality assurance
    - Feature engineering debugging
"""

import argparse
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add parent directory to path FIRST
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from tabulate import tabulate
from sqlalchemy import and_, desc, func

from database import SessionLocal
from db_models.snapshot_history import SnapshotHistory, init_snapshot_history_db
from features.basic_timeseries import TimeSeriesFeatureEngine, TimeSeriesFeatures
from jobs.hourly_snapshot import HourlySnapshotCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TimeSeriesDebugger:
    """
    Debug and validation tool for time-series data.
    
    Provides comprehensive inspection of:
    - Historical snapshot data
    - Computed features
    - Data quality metrics
    - Sanity check results
    """
    
    def __init__(self):
        self.feature_engine = TimeSeriesFeatureEngine()
        init_snapshot_history_db()
    
    def show_pool_history(self, pool_id: str, hours: int = 24) -> None:
        """
        Display historical TVL values for a pool.
        
        Args:
            pool_id: Pool identifier
            hours: Number of hours to display
        """
        print(f"\n{'='*70}")
        print(f"📊 TIME-SERIES HISTORY: {pool_id}")
        print(f"{'='*70}")
        
        db = SessionLocal()
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            snapshots = db.query(SnapshotHistory).filter(
                and_(
                    SnapshotHistory.pool_id == pool_id,
                    SnapshotHistory.timestamp >= start_time
                )
            ).order_by(desc(SnapshotHistory.timestamp)).all()
            
            if not snapshots:
                print(f"\n⚠️  No data found for pool: {pool_id}")
                print(f"   Time range: {start_time} to {end_time}")
                return
            
            print(f"\nFound {len(snapshots)} snapshots in last {hours} hours")
            print(f"Time range: {snapshots[-1].timestamp} to {snapshots[0].timestamp}")
            
            # Format table data
            table_data = []
            prev_tvl = None
            
            for snap in reversed(snapshots):  # Oldest first for trend
                # Calculate hour-over-hour change
                if prev_tvl and prev_tvl > 0:
                    change = (snap.tvl - prev_tvl) / prev_tvl * 100
                    change_str = f"{change:+.2f}%"
                else:
                    change_str = "--"
                
                table_data.append([
                    snap.timestamp.strftime("%Y-%m-%d %H:00"),
                    f"${snap.tvl:,.0f}" if snap.tvl else "N/A",
                    f"${snap.volume_24h:,.0f}" if snap.volume_24h else "N/A",
                    change_str,
                    snap.source or "unknown"
                ])
                prev_tvl = snap.tvl
            
            headers = ["Timestamp (UTC)", "TVL", "Volume 24h", "TVL Change", "Source"]
            print(f"\n{tabulate(table_data, headers=headers, tablefmt='simple')}")
            
        finally:
            db.close()
    
    def show_features(self, pool_id: str) -> TimeSeriesFeatures:
        """
        Compute and display features for a pool.
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Computed TimeSeriesFeatures
        """
        print(f"\n{'='*70}")
        print(f"🛠️  COMPUTED FEATURES: {pool_id}")
        print(f"{'='*70}")
        
        features = self.feature_engine.compute_features(pool_id)
        
        print(f"\nComputation Time: {features.timestamp}")
        print(f"Data Points Available: {features.data_points_available}")
        print(f"Sufficient Data: {'✓ Yes' if features.sufficient_data else '⚠️ No'}")
        
        print(f"\n{'Feature':<25} {'Value':<15} {'Risk Signal'}")
        print("-" * 60)
        
        # TVL Percentage Change (6h)
        if features.tvl_pct_change_6h is not None:
            risk = self._get_risk_indicator(features.tvl_pct_change_6h, 
                                            thresholds=[-0.20, -0.10, 0.10])
            print(f"{'tvl_pct_change_6h':<25} {features.tvl_pct_change_6h:+.2%}       {risk}")
        else:
            print(f"{'tvl_pct_change_6h':<25} {'N/A':<15} ⚠️ Insufficient data")
        
        # TVL Percentage Change (24h)
        if features.tvl_pct_change_24h is not None:
            risk = self._get_risk_indicator(features.tvl_pct_change_24h,
                                            thresholds=[-0.30, -0.15, 0.15])
            print(f"{'tvl_pct_change_24h':<25} {features.tvl_pct_change_24h:+.2%}       {risk}")
        else:
            print(f"{'tvl_pct_change_24h':<25} {'N/A':<15} ⚠️ Insufficient data")
        
        # TVL Acceleration
        if features.tvl_acceleration is not None:
            risk = self._get_risk_indicator(features.tvl_acceleration,
                                            thresholds=[-0.10, -0.05, 0.05])
            print(f"{'tvl_acceleration':<25} {features.tvl_acceleration:+.4f}       {risk}")
        else:
            print(f"{'tvl_acceleration':<25} {'N/A':<15} ⚠️ Insufficient data")
        
        # Volume Spike Ratio
        if features.volume_spike_ratio is not None:
            if features.volume_spike_ratio > 5.0:
                risk = "🔴 CRITICAL: Extreme volume spike"
            elif features.volume_spike_ratio > 3.0:
                risk = "🟡 WARNING: High volume spike"
            else:
                risk = "🟢 Normal"
            print(f"{'volume_spike_ratio':<25} {features.volume_spike_ratio:.2f}x          {risk}")
        else:
            print(f"{'volume_spike_ratio':<25} {'N/A':<15} ⚠️ Insufficient data")
        
        # Reserve Imbalance
        if features.reserve_imbalance is not None:
            if features.reserve_imbalance > 0.5:
                risk = "🔴 CRITICAL: Severe imbalance"
            elif features.reserve_imbalance > 0.3:
                risk = "🟡 WARNING: High imbalance"
            else:
                risk = "🟢 Normal"
            print(f"{'reserve_imbalance':<25} {features.reserve_imbalance:.2%}          {risk}")
        else:
            print(f"{'reserve_imbalance':<25} {'N/A':<15} ⚠️ Insufficient data")
        
        # Show warnings
        if features.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in features.warnings:
                print(f"   - {warning}")
        
        # Show risk signals
        signals = features.get_risk_signals()
        if signals:
            print(f"\n🚨 RISK SIGNALS DETECTED:")
            for sig in signals:
                severity_icon = "🔴" if sig['severity'] == 'critical' else "🟡" if sig['severity'] == 'high' else "🟠"
                print(f"   {severity_icon} [{sig['severity'].upper()}] {sig['description']}")
        else:
            print(f"\n✅ No risk signals detected")
        
        return features
    
    def _get_risk_indicator(self, value: float, thresholds: List[float]) -> str:
        """
        Get risk indicator based on thresholds.
        
        Args:
            value: Feature value
            thresholds: [critical_low, warning_low, warning_high]
        """
        if value < thresholds[0]:
            return "🔴 CRITICAL"
        elif value < thresholds[1]:
            return "🟡 WARNING"
        elif value > thresholds[2]:
            return "🟢 Positive"
        else:
            return "🟢 Normal"
    
    def show_status(self) -> None:
        """
        Display overall system status.
        """
        print(f"\n{'='*70}")
        print(f"📊 VERIRISK TIME-SERIES STATUS")
        print(f"{'='*70}")
        print(f"Current Time (UTC): {datetime.utcnow().isoformat()}")
        
        db = SessionLocal()
        try:
            # Total records
            total_count = db.query(func.count(SnapshotHistory.id)).scalar()
            
            # Unique pools
            pool_count = db.query(func.count(func.distinct(SnapshotHistory.pool_id))).scalar()
            
            # Time range
            oldest = db.query(func.min(SnapshotHistory.timestamp)).scalar()
            newest = db.query(func.max(SnapshotHistory.timestamp)).scalar()
            
            # Records by source
            source_counts = db.query(
                SnapshotHistory.source,
                func.count(SnapshotHistory.id)
            ).group_by(SnapshotHistory.source).all()
            
            # Recent activity (last hour)
            last_hour = datetime.utcnow() - timedelta(hours=1)
            recent_count = db.query(func.count(SnapshotHistory.id)).filter(
                SnapshotHistory.timestamp >= last_hour
            ).scalar()
            
            print(f"\n💾 Database Statistics:")
            print(f"   Total Records:     {total_count:,}")
            print(f"   Unique Pools:      {pool_count}")
            print(f"   Oldest Record:     {oldest}")
            print(f"   Newest Record:     {newest}")
            print(f"   Recent (1h):       {recent_count}")
            
            if oldest and newest:
                hours_span = (newest - oldest).total_seconds() / 3600
                print(f"   Time Span:         {hours_span:.1f} hours")
            
            print(f"\n📊 Records by Source:")
            for source, count in source_counts:
                print(f"   {source or 'unknown':<20} {count:>8,}")
            
            # Per-pool status
            print(f"\n📊 Pool Data Coverage:")
            
            pool_stats = db.query(
                SnapshotHistory.pool_id,
                func.count(SnapshotHistory.id).label('count'),
                func.min(SnapshotHistory.timestamp).label('oldest'),
                func.max(SnapshotHistory.timestamp).label('newest')
            ).group_by(SnapshotHistory.pool_id).all()
            
            table_data = []
            for stat in pool_stats:
                if stat.oldest and stat.newest:
                    hours = (stat.newest - stat.oldest).total_seconds() / 3600
                else:
                    hours = 0
                table_data.append([
                    stat.pool_id[:30],
                    stat.count,
                    f"{hours:.0f}h",
                    "✓" if stat.count >= 24 else "⚠️"
                ])
            
            headers = ["Pool ID", "Records", "Span", "24h Ready"]
            print(tabulate(table_data, headers=headers, tablefmt='simple'))
            
        finally:
            db.close()
    
    def run_sanity_checks(self) -> None:
        """
        Run comprehensive sanity checks on all data.
        """
        print(f"\n{'='*70}")
        print(f"🔍 SANITY CHECK RESULTS")
        print(f"{'='*70}")
        
        db = SessionLocal()
        issues = []
        
        try:
            # Check 1: Negative TVL values
            negative_tvl = db.query(SnapshotHistory).filter(
                SnapshotHistory.tvl < 0
            ).count()
            
            if negative_tvl > 0:
                issues.append(f"❌ Negative TVL values found: {negative_tvl}")
            else:
                print("✓ No negative TVL values")
            
            # Check 2: Negative volume values
            negative_vol = db.query(SnapshotHistory).filter(
                SnapshotHistory.volume_24h < 0
            ).count()
            
            if negative_vol > 0:
                issues.append(f"❌ Negative volume values found: {negative_vol}")
            else:
                print("✓ No negative volume values")
            
            # Check 3: Null TVL values
            null_tvl = db.query(SnapshotHistory).filter(
                SnapshotHistory.tvl == None
            ).count()
            
            if null_tvl > 0:
                print(f"⚠️  Null TVL values: {null_tvl} (may be expected)")
            else:
                print("✓ No null TVL values")
            
            # Check 4: Feature computation sanity
            print("\n🔍 Checking feature computation...")
            pool_ids = self.feature_engine.get_all_pool_ids()[:5]  # Sample 5 pools
            
            for pool_id in pool_ids:
                features = self.feature_engine.compute_features(pool_id)
                check_failures = self.feature_engine.run_sanity_checks(features)
                
                if check_failures:
                    for failure in check_failures:
                        issues.append(f"❌ {pool_id}: {failure}")
                else:
                    print(f"   ✓ {pool_id}: All checks passed")
            
            # Check 5: Data gaps
            print("\n🔍 Checking for data gaps...")
            for pool_id in pool_ids:
                gaps = self._check_data_gaps(db, pool_id)
                if gaps:
                    print(f"   ⚠️  {pool_id}: {len(gaps)} hour gaps detected")
                else:
                    print(f"   ✓ {pool_id}: No significant gaps")
            
            # Summary
            print(f"\n{'='*70}")
            if issues:
                print(f"⚠️  ISSUES FOUND: {len(issues)}")
                for issue in issues:
                    print(f"   {issue}")
            else:
                print("✅ ALL SANITY CHECKS PASSED")
            print(f"{'='*70}")
            
        finally:
            db.close()
    
    def _check_data_gaps(self, db, pool_id: str, max_gap_hours: int = 3) -> List[tuple]:
        """
        Check for gaps in hourly data.
        
        Returns list of (start_time, end_time) tuples for gaps.
        """
        snapshots = db.query(SnapshotHistory.timestamp).filter(
            SnapshotHistory.pool_id == pool_id
        ).order_by(SnapshotHistory.timestamp).all()
        
        gaps = []
        prev_time = None
        
        for (timestamp,) in snapshots:
            if prev_time:
                gap_hours = (timestamp - prev_time).total_seconds() / 3600
                if gap_hours > max_gap_hours:
                    gaps.append((prev_time, timestamp))
            prev_time = timestamp
        
        return gaps
    
    def seed_data(self, hours: int = 48) -> None:
        """
        Seed historical data for testing.
        """
        print(f"\n🌱 Seeding {hours} hours of historical data...")
        collector = HourlySnapshotCollector()
        records = collector.seed_historical_data(hours=hours)
        print(f"✓ Seeded {records} records")
    
    def collect_now(self) -> None:
        """
        Run immediate collection.
        """
        print(f"\n🕐 Running immediate collection...")
        collector = HourlySnapshotCollector()
        pools = collector.collect_hourly_snapshot()
        print(f"✓ Collected {len(pools)} pool snapshots")


def main():
    parser = argparse.ArgumentParser(
        description='VeriRisk Time-Series Debug Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python debug_timeseries.py --pool uniswap_v2_usdc_eth
  python debug_timeseries.py --status
  python debug_timeseries.py --sanity-check
  python debug_timeseries.py --seed 48
  python debug_timeseries.py --collect
        """
    )
    
    parser.add_argument('--pool', type=str, 
                        help='Show history and features for specific pool')
    parser.add_argument('--hours', type=int, default=24,
                        help='Number of hours of history to show (default: 24)')
    parser.add_argument('--status', action='store_true',
                        help='Show overall system status')
    parser.add_argument('--sanity-check', action='store_true',
                        help='Run sanity checks on data')
    parser.add_argument('--seed', type=int, metavar='HOURS',
                        help='Seed N hours of synthetic historical data')
    parser.add_argument('--collect', action='store_true',
                        help='Run immediate data collection')
    parser.add_argument('--all-features', action='store_true',
                        help='Compute features for all pools')
    
    args = parser.parse_args()
    
    debugger = TimeSeriesDebugger()
    
    if args.seed:
        debugger.seed_data(hours=args.seed)
    
    if args.collect:
        debugger.collect_now()
    
    if args.pool:
        debugger.show_pool_history(args.pool, hours=args.hours)
        debugger.show_features(args.pool)
    
    if args.status:
        debugger.show_status()
    
    if args.sanity_check:
        debugger.run_sanity_checks()
    
    if args.all_features:
        pool_ids = debugger.feature_engine.get_all_pool_ids()
        print(f"\n📊 Computing features for {len(pool_ids)} pools...")
        for pool_id in pool_ids:
            debugger.show_features(pool_id)
    
    # If no args, show help
    if not any([args.pool, args.status, args.sanity_check, args.seed, 
                args.collect, args.all_features]):
        parser.print_help()


if __name__ == "__main__":
    main()
