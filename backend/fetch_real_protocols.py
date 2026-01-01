#!/usr/bin/env python3
"""
VeriRisk Phase-2: Real Protocol Data Fetcher

This script fetches LIVE data from real DeFi protocols using DeFiLlama API.
It can:
1. Fetch current snapshots from real protocols
2. Build historical data over time (run hourly via cron)
3. Test the predictive model on real protocol data

Usage:
    python fetch_real_protocols.py --fetch          # Fetch current data once
    python fetch_real_protocols.py --fetch-all      # Fetch all protocols
    python fetch_real_protocols.py --build-history  # Simulate history for testing
    python fetch_real_protocols.py --predict        # Run predictions on real data
    python fetch_real_protocols.py --status         # Check data status
"""

import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, Snapshot, init_db
from protocols import MultiProtocolFetcher, DeFiLlamaFetcher
from web3 import Web3
from config import config
import hashlib
import numpy as np


def fetch_real_protocols_once():
    """Fetch current data from all real DeFi protocols"""
    print("\n" + "="*70)
    print("🌐 FETCHING LIVE DATA FROM REAL DEFI PROTOCOLS")
    print("="*70)
    
    w3 = Web3(Web3.HTTPProvider(config.ETH_RPC_URL))
    fetcher = MultiProtocolFetcher(w3)
    
    protocols_data = fetcher.get_all_protocols()
    
    db = SessionLocal()
    try:
        stored_count = 0
        for proto_data in protocols_data:
            # Create snapshot
            snapshot_id = hashlib.sha256(
                f"{proto_data['pool_id']}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]
            
            # Compute features
            tvl = float(proto_data.get('tvl', 0))
            r0 = float(proto_data.get('reserve0', 0))
            r1 = float(proto_data.get('reserve1', 0))
            vol = float(proto_data.get('volume_24h', 0))
            
            features = {
                "tvl_pct_change_1h": 0.0,
                "reserve_imbalance": abs(r0 - r1) / max(r0 + r1, 1),
                "volume_tvl_ratio": vol / max(tvl, 1),
                "volatility_24h": 0.02,
                "leverage_ratio": 1.0,
                "data_source": proto_data.get('data_source', 'unknown'),
                "synthetic": proto_data.get('synthetic', False),
            }
            
            snapshot = Snapshot(
                snapshot_id=snapshot_id,
                pool_id=proto_data['pool_id'],
                timestamp=datetime.utcnow(),
                tvl=tvl,
                reserve0=r0,
                reserve1=r1,
                volume_24h=vol,
                oracle_price=proto_data.get('price', 1.0),
                features=features,
                source=proto_data.get('protocol', 'unknown')
            )
            db.add(snapshot)
            stored_count += 1
        
        db.commit()
        print(f"\n✅ Stored {stored_count} real protocol snapshots")
        
    finally:
        db.close()
    
    return protocols_data


def build_simulated_history(hours: int = 168):
    """
    Build simulated historical data based on REAL current TVL values.
    
    This creates realistic history by:
    1. Fetching current REAL TVL from DeFiLlama
    2. Simulating realistic historical fluctuations around that TVL
    3. Preserving real protocol characteristics
    
    This allows testing the predictive model on pools with real TVL magnitudes.
    """
    print("\n" + "="*70)
    print("🔧 BUILDING SIMULATED HISTORY FROM REAL PROTOCOL DATA")
    print(f"   Duration: {hours} hours ({hours/24:.1f} days)")
    print("="*70)
    
    w3 = Web3(Web3.HTTPProvider(config.ETH_RPC_URL))
    fetcher = MultiProtocolFetcher(w3)
    
    # First, fetch real current data
    print("\n📡 Fetching current real protocol data...")
    real_data = fetcher.get_all_protocols()
    
    db = SessionLocal()
    try:
        for proto in real_data:
            pool_id = proto['pool_id']
            real_tvl = float(proto.get('tvl', 0))
            real_volume = float(proto.get('volume_24h', 0))
            real_r0 = float(proto.get('reserve0', 0))
            real_r1 = float(proto.get('reserve1', 0))
            is_synthetic = proto.get('synthetic', True)
            
            if real_tvl == 0:
                print(f"⚠ Skipping {pool_id}: No TVL data")
                continue
            
            # Clear existing data for this pool
            db.query(Snapshot).filter(Snapshot.pool_id == pool_id).delete()
            
            print(f"\n📊 {proto.get('display_name', pool_id)}")
            print(f"   Current TVL: ${real_tvl:,.0f}")
            print(f"   Data Source: {'🟢 LIVE' if not is_synthetic else '🟡 Fallback'}")
            
            # Generate historical data with realistic fluctuations
            base_time = datetime.utcnow() - timedelta(hours=hours)
            snapshots = []
            
            # Use different volatility profiles based on protocol type
            if 'curve' in pool_id or 'steth' in pool_id:
                volatility = 0.005  # Stableswap: low volatility
            elif 'aave' in pool_id or 'compound' in pool_id:
                volatility = 0.01   # Lending: medium-low volatility
            elif 'uniswap_v3' in pool_id:
                volatility = 0.02   # V3: medium volatility
            else:
                volatility = 0.015  # Default: medium volatility
            
            current_tvl = real_tvl * np.random.uniform(0.95, 1.05)  # Start near current
            
            for i in range(hours):
                timestamp = base_time + timedelta(hours=i)
                
                # Random walk with mean reversion to real TVL
                mean_reversion = 0.01 * (real_tvl - current_tvl) / real_tvl
                change = np.random.normal(mean_reversion, volatility)
                current_tvl *= (1 + change)
                
                # Keep TVL bounded
                current_tvl = max(current_tvl, real_tvl * 0.7)
                current_tvl = min(current_tvl, real_tvl * 1.3)
                
                # Scale reserves proportionally
                scale = current_tvl / real_tvl if real_tvl > 0 else 1
                reserve0 = real_r0 * scale * np.random.uniform(0.98, 1.02)
                reserve1 = real_r1 * scale * np.random.uniform(0.98, 1.02)
                
                # Volume with some randomness
                volume = real_volume * np.random.uniform(0.5, 1.5)
                
                features = {
                    "tvl_pct_change_1h": 0.0,
                    "reserve_imbalance": abs(reserve0 - reserve1) / max(reserve0 + reserve1, 1),
                    "volume_tvl_ratio": volume / max(current_tvl, 1),
                    "volatility_24h": volatility,
                    "leverage_ratio": 1.0,
                    "data_source": "simulated_from_real",
                    "base_real_tvl": real_tvl,
                }
                
                snapshot = Snapshot(
                    snapshot_id=f"real-hist-{pool_id}-{i}",
                    pool_id=pool_id,
                    timestamp=timestamp,
                    tvl=current_tvl,
                    reserve0=reserve0,
                    reserve1=reserve1,
                    volume_24h=volume,
                    oracle_price=proto.get('price', 1.0),
                    features=features,
                    source=f"{proto.get('protocol', 'unknown')}_simulated"
                )
                snapshots.append(snapshot)
            
            db.bulk_save_objects(snapshots)
            print(f"   ✓ Generated {hours} historical snapshots")
        
        db.commit()
        print(f"\n✅ Historical data built for {len(real_data)} protocols")
        
    finally:
        db.close()


def predict_real_protocols():
    """Run predictions on real protocol data"""
    print("\n" + "="*70)
    print("🎯 PREDICTIVE RISK ANALYSIS ON REAL PROTOCOLS")
    print("="*70)
    
    # Import model server
    from model_server import PredictiveModelServer, print_prediction_result
    
    server = PredictiveModelServer()
    
    if server.model is None:
        print("\n⚠ No trained model found. Please train first:")
        print("   python model_trainer.py")
        return
    
    # Get all pools with sufficient data
    db = SessionLocal()
    try:
        from sqlalchemy import func
        
        pool_counts = (
            db.query(Snapshot.pool_id, func.count(Snapshot.id))
            .group_by(Snapshot.pool_id)
            .all()
        )
        
        eligible_pools = [p[0] for p in pool_counts if p[1] >= 48]
        
        if not eligible_pools:
            print("\n⚠ No pools with sufficient history (48+ hours)")
            print("   Run: python fetch_real_protocols.py --build-history")
            return
        
        print(f"\n📊 Found {len(eligible_pools)} pools with sufficient data")
        
        # Run predictions
        results = []
        for pool_id in eligible_pools:
            result = server.predict_risk(pool_id)
            if 'error' not in result:
                results.append(result)
        
        # Sort by risk score
        results.sort(key=lambda x: x.get('risk_score', 0), reverse=True)
        
        # Print rankings
        print("\n" + "="*70)
        print("REAL PROTOCOL RISK RANKINGS (Highest to Lowest)")
        print("="*70)
        
        for result in results:
            level_emoji = {'LOW': '🟢', 'MEDIUM': '🟡', 'HIGH': '🔴'}.get(
                result.get('risk_level', ''), '⚪'
            )
            pool_id = result['pool_id']
            score = result.get('risk_score', 0)
            
            # Format pool name nicely
            display_name = pool_id.replace('_', ' ').title()
            print(f"  {level_emoji}  {score:5.1f}%  {display_name}")
        
        print(f"\n✓ Analyzed {len(results)} real protocols")
        
        # Show detailed view for top 3 risky
        print("\n" + "="*70)
        print("TOP 3 HIGHEST RISK PROTOCOLS (DETAILED)")
        print("="*70)
        
        for result in results[:3]:
            print_prediction_result(result)
        
    finally:
        db.close()


def check_data_status():
    """Check current data status in database"""
    print("\n" + "="*70)
    print("📊 DATABASE STATUS")
    print("="*70)
    
    db = SessionLocal()
    try:
        from sqlalchemy import func
        
        # Total snapshots
        total = db.query(Snapshot).count()
        print(f"\nTotal snapshots: {total}")
        
        # Per-pool breakdown
        pool_stats = (
            db.query(
                Snapshot.pool_id,
                func.count(Snapshot.id).label('count'),
                func.min(Snapshot.timestamp).label('oldest'),
                func.max(Snapshot.timestamp).label('newest'),
                func.avg(Snapshot.tvl).label('avg_tvl')
            )
            .group_by(Snapshot.pool_id)
            .all()
        )
        
        if not pool_stats:
            print("\n⚠ No data in database")
            print("   Run: python fetch_real_protocols.py --build-history")
            return
        
        print(f"\nPools in database: {len(pool_stats)}")
        print("\n" + "-"*90)
        print(f"{'Pool ID':<40} {'Count':>8} {'Avg TVL':>15} {'Hours':>8}")
        print("-"*90)
        
        for stat in sorted(pool_stats, key=lambda x: x.count, reverse=True):
            hours = 0
            if stat.oldest and stat.newest:
                hours = int((stat.newest - stat.oldest).total_seconds() / 3600)
            
            avg_tvl = stat.avg_tvl or 0
            tvl_str = f"${avg_tvl/1e6:.1f}M" if avg_tvl > 1e6 else f"${avg_tvl:,.0f}"
            
            print(f"{stat.pool_id:<40} {stat.count:>8} {tvl_str:>15} {hours:>8}h")
        
        print("-"*90)
        
        # Data freshness
        latest = db.query(func.max(Snapshot.timestamp)).scalar()
        if latest:
            age = datetime.utcnow() - latest
            print(f"\nLatest data: {latest.isoformat()} ({age.total_seconds()/3600:.1f}h ago)")
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='VeriRisk Real Protocol Data Fetcher',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_real_protocols.py --fetch           # Fetch current snapshot
  python fetch_real_protocols.py --build-history   # Build 7 days of history
  python fetch_real_protocols.py --predict         # Run predictions
  python fetch_real_protocols.py --status          # Check database status
  
For continuous monitoring:
  # Add to crontab to run every hour:
  # 0 * * * * cd /path/to/backend && python fetch_real_protocols.py --fetch
        """
    )
    
    parser.add_argument('--fetch', action='store_true',
                        help='Fetch current data from real protocols')
    parser.add_argument('--build-history', action='store_true',
                        help='Build simulated history from real TVL values')
    parser.add_argument('--hours', type=int, default=168,
                        help='Hours of history to build (default: 168 = 7 days)')
    parser.add_argument('--predict', action='store_true',
                        help='Run predictions on real protocol data')
    parser.add_argument('--status', action='store_true',
                        help='Check current data status')
    
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    if args.fetch:
        fetch_real_protocols_once()
    elif args.build_history:
        build_simulated_history(hours=args.hours)
    elif args.predict:
        predict_real_protocols()
    elif args.status:
        check_data_status()
    else:
        # Default: show status and usage
        check_data_status()
        print("\n" + "="*70)
        print("QUICK START GUIDE")
        print("="*70)
        print("""
1. Build history from real protocol TVL values:
   python fetch_real_protocols.py --build-history --hours 720

2. Train model on real data:
   python model_trainer.py

3. Run predictions on real protocols:
   python fetch_real_protocols.py --predict
        """)


if __name__ == "__main__":
    main()
