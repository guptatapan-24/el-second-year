#!/usr/bin/env python3
"""Test script for verifying real-time data fetching"""

import sys
from datetime import datetime
from database import SessionLocal, Snapshot, init_db
from data_fetcher import DataFetcher
# os.environ["PYTHONUTF8"] = "1"
# sys.stdout.reconfigure(encoding="utf-8")
# sys.stderr.reconfigure(encoding="utf-8")

def test_data_fetching():
    """Test the complete data fetching pipeline"""
    
    print("=" * 80)
    print(" 🧪 TESTING REAL-TIME DATA FETCHING SYSTEM")
    print("=" * 80)
    
    # Initialize database
    print("\n1️⃣  Initializing database...")
    init_db()
    print("   ✅ Database ready")
    
    # Create fetcher
    print("\n2️⃣  Creating data fetcher...")
    fetcher = DataFetcher()
    print("   ✅ Fetcher initialized")
    
    # Fetch from all protocols
    print("\n3️⃣  Fetching data from DeFi protocols...")
    print("   (This will take ~15-30 seconds)\n")
    
    start_time = datetime.utcnow()
    snapshot_ids = fetcher.fetch_all_protocols()
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n   ✅ Fetch completed in {duration:.1f} seconds")
    print(f"   📊 Created {len(snapshot_ids)} snapshots")
    
    # Verify data in database
    print("\n4️⃣  Verifying data in database...")
    db = SessionLocal()
    try:
        recent_snapshots = db.query(Snapshot).order_by(Snapshot.timestamp.desc()).limit(50).all()
        
        if not recent_snapshots:
            print("   ❌ No snapshots found in database!")
            return False
        
        # Count live vs synthetic data
        live_count = 0
        synthetic_count = 0
        
        for snap in recent_snapshots:
            if isinstance(snap.features, dict):
                is_synthetic = snap.features.get('synthetic', snap.source == 'synthetic')
                if is_synthetic:
                    synthetic_count += 1
                else:
                    live_count += 1
        
        total = len(recent_snapshots)
        live_percentage = (live_count / total * 100) if total > 0 else 0
        
        print(f"   📊 Total recent snapshots: {total}")
        print(f"   🟢 Live data: {live_count} ({live_percentage:.1f}%)")
        print(f"   🟡 Synthetic data: {synthetic_count} ({100-live_percentage:.1f}%)")
        
        if live_percentage >= 80:
            print(f"   ✅ EXCELLENT: {live_percentage:.0f}% real data!")
        elif live_percentage >= 50:
            print(f"   ⚠️  WARNING: Only {live_percentage:.0f}% real data (expected 80%+)")
        else:
            print(f"   ❌ FAIL: Only {live_percentage:.0f}% real data (expected 80%+)")
        
        # Show sample data
        print("\n5️⃣  Sample data (first 5 protocols):")
        print("   " + "-" * 76)
        for i, snap in enumerate(recent_snapshots[:5]):
            age = datetime.utcnow() - snap.timestamp
            is_synthetic = snap.features.get('synthetic', False) if isinstance(snap.features, dict) else 'N/A'
            status = "🟡 SYNTHETIC" if is_synthetic else "🟢 LIVE"
            
            print(f"   {i+1}. {snap.pool_id:<30} TVL: ${snap.tvl:>15,.0f}  {status}")
        
        print("\n" + "=" * 80)
        
        if live_percentage >= 80:
            print("✅ TEST PASSED - Real-time data fetching is working!")
            return True
        else:
            print("⚠️  TEST WARNING - Too much synthetic data, check API connections")
            return False
            
    finally:
        db.close()

if __name__ == "__main__":
    success = test_data_fetching()
    sys.exit(0 if success else 1)
