#!/usr/bin/env python3
"""Data fetcher for DeFi protocol metrics from multiple sources"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from web3 import Web3
from config import config
from database import SessionLocal, Snapshot, init_db
from protocols import MultiProtocolFetcher
import hashlib
import random

class DataFetcher:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(config.ETH_RPC_URL))
        self.session = requests.Session()
        self.multi_protocol = MultiProtocolFetcher(self.w3)
        
    def fetch_coingecko_data(self, token_ids: List[str]) -> Dict:
        """Fetch market data from CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': ','.join(token_ids),
                'vs_currencies': 'usd',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true'
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"CoinGecko API error: {e}")
            return {}
    
    def fetch_thegraph_uniswap(self, pool_address: str) -> Dict:
        """Fetch Uniswap pool data from TheGraph"""
        # Uniswap V2 subgraph query
        query = """
        query($pool: String!) {
          pair(id: $pool) {
            id
            token0 { symbol }
            token1 { symbol }
            reserve0
            reserve1
            reserveUSD
            volumeUSD
            txCount
          }
        }
        """
        
        url = "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
        try:
            response = self.session.post(
                url,
                json={'query': query, 'variables': {'pool': pool_address.lower()}},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', {}).get('pair', {})
        except Exception as e:
            print(f"TheGraph API error: {e}")
            return {}
    
    def fetch_onchain_data(self, pool_address: str) -> Dict:
        """Fetch on-chain data directly via RPC"""
        try:
            # Get block number and timestamp
            block = self.w3.eth.get_block('latest')
            
            # For demo: return mock on-chain data structure
            # In production: call actual pool contract methods
            return {
                'block_number': block['number'],
                'timestamp': block['timestamp'],
                'gas_price': self.w3.eth.gas_price,
            }
        except Exception as e:
            print(f"On-chain fetch error: {e}")
            return {}
    
    def compute_derived_features(self, raw: dict) -> dict:
        tvl = float(raw.get("tvl", 0))
        r0 = float(raw.get("reserve0", 0))
        r1 = float(raw.get("reserve1", 0))
        vol = float(raw.get("volume_24h", 0))

        return {
            "tvl_pct_change_1h": 0.0,
            "reserve_imbalance": abs(r0 - r1) / max(r0 + r1, 1),
            "volume_tvl_ratio": vol / max(tvl, 1),
            "volatility_24h": 0.02,
            "leverage_ratio": 1.0,
        }

    
    def fetch_and_store(self, pool_id: str, pool_address: str) -> Optional[str]:
        """Fetch data for a pool and store in database"""
        try:
            # Fetch from multiple sources
            graph_data = self.fetch_thegraph_uniswap(pool_address)
            onchain_data = self.fetch_onchain_data(pool_address)
            market_data = self.fetch_coingecko_data(['ethereum', 'usd-coin'])
            
            # Combine and structure data
            raw_data = {
                'tvl': float(graph_data.get('reserveUSD', 1000000)),
                'reserve0': float(graph_data.get('reserve0', 500000)),
                'reserve1': float(graph_data.get('reserve1', 500000)),
                'volume_24h': float(graph_data.get('volumeUSD', 100000)),
                'oracle_price': 1.0,  # Simplified
                'block_number': onchain_data.get('block_number', 0),
            }
            
            # Compute derived features
            features = self.compute_derived_features(raw_data)
            
            # Create snapshot
            snapshot_id = hashlib.sha256(
                f"{pool_id}-{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]
            
            db = SessionLocal()
            try:
                snapshot = Snapshot(
                    snapshot_id=snapshot_id,
                    pool_id=pool_id,
                    timestamp=datetime.utcnow(),
                    tvl=raw_data['tvl'],
                    reserve0=raw_data['reserve0'],
                    reserve1=raw_data['reserve1'],
                    volume_24h=raw_data['volume_24h'],
                    oracle_price=raw_data['oracle_price'],
                    features=features,
                    source='uniswap_v2'
                )
                db.add(snapshot)
                db.commit()
                db.refresh(snapshot)
                print(f"Stored snapshot {snapshot_id} for pool {pool_id}")
                return snapshot_id
            finally:
                db.close()
                
        except Exception as e:
            print(f"Error fetching/storing data for {pool_id}: {e}")
            return None
    
    def fetch_all_protocols(self) -> List[str]:
        """Fetch data from all supported DeFi protocols and store in database"""
        protocols_data = self.multi_protocol.get_all_protocols()
        snapshot_ids = []
        
        db = SessionLocal()
        try:
            for proto_data in protocols_data:
                # Compute derived features
                features = self.compute_derived_features(proto_data)
                
                # Add protocol-specific features
                if proto_data['protocol'] in ['Aave V3', 'Compound V2']:
                    features['utilization_rate'] = proto_data.get('utilization_rate', 0)
                    features['supply_apy'] = proto_data.get('supply_apy', 0)
                    features['borrow_apy'] = proto_data.get('borrow_apy', 0)
                
                # Create snapshot
                snapshot_id = hashlib.sha256(
                    f"{proto_data['pool_id']}-{datetime.utcnow().isoformat()}".encode()
                ).hexdigest()[:16]
                
                snapshot = Snapshot(
                    snapshot_id=snapshot_id,
                    pool_id=proto_data['pool_id'],
                    timestamp=datetime.utcnow(),
                    tvl=proto_data.get('tvl', 0),
                    reserve0=proto_data.get('reserve0', 0),
                    reserve1=proto_data.get('reserve1', 0),
                    volume_24h=proto_data.get('volume_24h', 0),
                    oracle_price=proto_data.get('price', 1.0),
                    features=features,
                    source=proto_data['protocol']
                )
                db.add(snapshot)
                snapshot_ids.append(snapshot_id)
                print(f"Stored snapshot for {proto_data['display_name']}")
            
            db.commit()
            print(f"\n✓ Successfully fetched and stored data for {len(protocols_data)} protocols")
            return snapshot_ids
        finally:
            db.close()
    
    def generate_synthetic_data(self, pool_id: str, num_samples: int = 300):
        """Legacy method - use generate_predictive_synthetic_data instead"""
        return self.generate_predictive_synthetic_data(pool_id, num_samples)
    
    def generate_predictive_synthetic_data(self, pool_id: str, num_samples: int = 720, 
                                            risk_profile: str = 'mixed',
                                            force_current_risk_state: bool = False):
        """
        Generate synthetic time-series data with realistic crash patterns for predictive modeling.
        
        This method creates data with:
        - Continuous time-series (hourly snapshots)
        - Realistic crash scenarios (gradual decline, sudden crash, recovery patterns)
        - Multiple risk regimes for diverse training data
        - Option to force current high-risk state for testing
        
        Args:
            pool_id: Pool identifier
            num_samples: Number of hourly snapshots (default 720 = 30 days)
            risk_profile: 'safe', 'risky', 'mixed', 'crash_prone'
            force_current_risk_state: If True, ensures pool ends in pre_crash/crash state
        """
        import numpy as np
        
        db = SessionLocal()
        try:
            # Clear existing data for this pool
            db.query(Snapshot).filter(Snapshot.pool_id == pool_id).delete()
            db.commit()
            
            base_time = datetime.utcnow() - timedelta(hours=num_samples)
            
            # Initialize TVL trajectory based on risk profile
            # crash_probability is the per-hour probability (as decimal)
            if risk_profile == 'safe':
                base_tvl = 2_000_000
                crash_probability = 0.0005  # 0.05% per hour (~3.5% per month)
            elif risk_profile == 'risky':
                base_tvl = 800_000
                crash_probability = 0.003   # 0.3% per hour (~20% per month)
            elif risk_profile == 'crash_prone':
                base_tvl = 500_000
                crash_probability = 0.008   # 0.8% per hour (~45% per month)
            else:  # mixed
                base_tvl = 1_000_000
                crash_probability = 0.0015  # 0.15% per hour (~10% per month)
            
            current_tvl = base_tvl
            regime = 'normal'  # normal, pre_crash, crash, recovery
            regime_duration = 0
            crash_counter = 0
            
            # For crash_prone profile with force_current_risk_state, 
            # ensure we end in a high-risk state (pre_crash or crash)
            if force_current_risk_state and risk_profile == 'crash_prone':
                # Schedule a crash to START at the end of the time series
                # The pre_crash phase will begin 12-24 hours before end and extend to the end
                forced_crash_start = num_samples - random.randint(12, 24)
                # Prevent transition from pre_crash to crash until very end
                forced_crash_end_protection = num_samples - random.randint(3, 8)
            else:
                forced_crash_start = None
                forced_crash_end_protection = None
            
            snapshots = []
            
            for i in range(num_samples):
                timestamp = base_time + timedelta(hours=i)
                
                # Force crash state near the end for crash_prone pools
                if forced_crash_start and i >= forced_crash_start:
                    if regime == 'normal':
                        regime = 'pre_crash'
                        # Set duration to extend past the end of data
                        regime_duration = num_samples - i + 10  # Will never reach 0 before data ends
                    elif regime == 'pre_crash' and i >= forced_crash_end_protection:
                        # Optionally transition to crash in the last few hours
                        regime = 'crash'
                        regime_duration = num_samples - i + 5
                
                # State machine for realistic price dynamics
                if regime == 'normal':
                    # Small random walk
                    change = np.random.normal(0, 0.01)  # 1% std dev
                    current_tvl *= (1 + change)
                    
                    # Check for crash trigger (fixed: no extra /100)
                    if random.random() < crash_probability:
                        regime = 'pre_crash'
                        regime_duration = random.randint(6, 24)  # 6-24 hours warning
                        
                elif regime == 'pre_crash':
                    # Gradual decline with increasing volatility
                    decline_rate = 0.008 + 0.005 * (1 - regime_duration / 24)  # Accelerating decline
                    noise = np.random.normal(0, 0.02)
                    current_tvl *= (1 - decline_rate + noise)
                    
                    regime_duration -= 1
                    if regime_duration <= 0:
                        regime = 'crash'
                        regime_duration = random.randint(6, 18)  # Crash duration
                        crash_counter += 1
                        
                elif regime == 'crash':
                    # Sharp decline
                    crash_rate = random.uniform(0.04, 0.10)  # 4-10% per hour (more severe)
                    noise = np.random.normal(0, 0.015)
                    current_tvl *= (1 - crash_rate + noise)
                    
                    regime_duration -= 1
                    if regime_duration <= 0:
                        regime = 'recovery'
                        regime_duration = random.randint(24, 72)  # Recovery period
                        
                elif regime == 'recovery':
                    # Slow recovery
                    recovery_rate = random.uniform(0.002, 0.008)
                    noise = np.random.normal(0, 0.01)
                    current_tvl *= (1 + recovery_rate + noise)
                    
                    regime_duration -= 1
                    if regime_duration <= 0:
                        regime = 'normal'
                
                # Ensure TVL doesn't go negative or too low
                current_tvl = max(current_tvl, base_tvl * 0.05)  # Allow lower floor for crash_prone
                # Cap TVL growth
                current_tvl = min(current_tvl, base_tvl * 2.0)
                
                # Generate correlated features based on regime
                if regime == 'crash':
                    # High volume during crash (panic selling)
                    volume_multiplier = random.uniform(3.0, 7.0)
                    reserve_imbalance = random.uniform(0.20, 0.50)
                    volatility = random.uniform(0.10, 0.20)
                elif regime == 'pre_crash':
                    # Increasing volume before crash
                    volume_multiplier = random.uniform(1.5, 3.5)
                    reserve_imbalance = random.uniform(0.10, 0.30)
                    volatility = random.uniform(0.05, 0.12)
                elif regime == 'recovery':
                    volume_multiplier = random.uniform(1.0, 2.0)
                    reserve_imbalance = random.uniform(0.05, 0.15)
                    volatility = random.uniform(0.03, 0.06)
                else:  # normal
                    volume_multiplier = random.uniform(0.8, 1.5)
                    reserve_imbalance = random.uniform(0.02, 0.08)
                    volatility = random.uniform(0.01, 0.03)
                
                # Generate reserves with imbalance
                total_reserve = current_tvl
                imbalance_direction = 1 if random.random() > 0.5 else -1
                reserve0 = total_reserve * (0.5 + imbalance_direction * reserve_imbalance / 2)
                reserve1 = total_reserve - reserve0
                
                # Volume correlated with TVL and regime
                volume_24h = current_tvl * 0.3 * volume_multiplier
                
                features = {
                    "tvl_pct_change_1h": 0.0,  # Will be computed by feature engine
                    "reserve_imbalance": abs(reserve0 - reserve1) / max(total_reserve, 1),
                    "volume_tvl_ratio": volume_24h / max(current_tvl, 1),
                    "volatility_24h": volatility,
                    "leverage_ratio": 1.0,
                    "regime": regime,  # For debugging
                }
                
                snapshot = Snapshot(
                    snapshot_id=f"synthetic-{pool_id}-{i}",
                    pool_id=pool_id,
                    timestamp=timestamp,
                    tvl=current_tvl,
                    reserve0=reserve0,
                    reserve1=reserve1,
                    volume_24h=volume_24h,
                    oracle_price=1.0,
                    features=features,
                    source="synthetic_predictive",
                )
                snapshots.append(snapshot)
            
            # Bulk insert
            db.bulk_save_objects(snapshots)
            db.commit()
            
            # Determine final state
            final_regime = snapshots[-1].features.get('regime', 'unknown')
            
            print(f"✓ Generated {num_samples} predictive synthetic snapshots for {pool_id}")
            print(f"  Risk profile: {risk_profile}")
            print(f"  Crash events: {crash_counter}")
            print(f"  Final regime: {final_regime}")
            print(f"  TVL range: ${min(s.tvl for s in snapshots):,.0f} - ${max(s.tvl for s in snapshots):,.0f}")
            
        finally:
            db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch DeFi data')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--all-protocols', action='store_true', help='Fetch all protocols')
    parser.add_argument('--synthetic', action='store_true', help='Generate synthetic data')
    parser.add_argument('--predictive', action='store_true', help='Generate predictive synthetic data')
    parser.add_argument('--pool', default='0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',
                        help='Pool address')
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    fetcher = DataFetcher()
    
    if args.all_protocols:
        print("Fetching data from all DeFi protocols...")
        snapshot_ids = fetcher.fetch_all_protocols()
        print(f"\n✓ Successfully created {len(snapshot_ids)} snapshots")
    elif args.predictive:
        print("Generating predictive synthetic data with crash patterns...")
        print("\n📊 Creating diverse pool profiles for training:")
        
        # Create pools with different risk profiles
        fetcher.generate_predictive_synthetic_data('test_pool_1', 720, 'mixed')
        fetcher.generate_predictive_synthetic_data('test_pool_2', 720, 'safe')
        fetcher.generate_predictive_synthetic_data('uniswap_v2_usdc_eth', 720, 'mixed')
        fetcher.generate_predictive_synthetic_data('aave_v3_eth', 720, 'risky')
        fetcher.generate_predictive_synthetic_data('curve_3pool', 720, 'safe')
        # High risk pool with forced current risk state for testing
        fetcher.generate_predictive_synthetic_data('high_risk_pool', 720, 'crash_prone', force_current_risk_state=True)
        # Add an additional pool that's currently in crash
        fetcher.generate_predictive_synthetic_data('critical_risk_pool', 720, 'crash_prone', force_current_risk_state=True)
        
        print("\n✓ Predictive synthetic data generation complete")
        print("  Run: python model_trainer.py to train the predictive model")
        print("  Note: high_risk_pool and critical_risk_pool are forced to end in crash/pre_crash state")
    elif args.synthetic:
        print("Generating synthetic data...")
        fetcher.generate_predictive_synthetic_data('test_pool_1', 720, 'mixed')
        fetcher.generate_predictive_synthetic_data('test_pool_2', 720, 'safe')
        print("Synthetic data generation complete")
    else:
        pool_id = "uniswap_v2_usdc_eth"
        print(f"Fetching data for pool {pool_id}...")
        snapshot_id = fetcher.fetch_and_store(pool_id, args.pool)
        if snapshot_id:
            print(f"Success! Snapshot ID: {snapshot_id}")
        else:
            print("Failed to fetch data")
