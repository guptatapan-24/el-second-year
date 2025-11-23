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
    
    def compute_derived_features(self, raw_data: Dict) -> Dict:
        """Compute derived risk features from raw data"""
        features = {}
        
        # TVL change percentage
        if 'tvl' in raw_data and 'tvl_prev' in raw_data:
            features['tvl_pct_change_1h'] = (
                (raw_data['tvl'] - raw_data['tvl_prev']) / raw_data['tvl_prev'] * 100
                if raw_data['tvl_prev'] > 0 else 0
            )
        
        # Reserve imbalance
        if 'reserve0' in raw_data and 'reserve1' in raw_data:
            total = raw_data['reserve0'] + raw_data['reserve1']
            features['reserve_imbalance'] = (
                abs(raw_data['reserve0'] - raw_data['reserve1']) / total
                if total > 0 else 0
            )
        
        # Volatility proxy from 24h change
        if 'volume_24h' in raw_data and 'tvl' in raw_data:
            features['volume_tvl_ratio'] = (
                raw_data['volume_24h'] / raw_data['tvl']
                if raw_data['tvl'] > 0 else 0
            )
        
        # Add more features as needed
        features['timestamp'] = datetime.utcnow().isoformat()
        
        return features
    
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
    
    def generate_synthetic_data(self, pool_id: str, num_samples: int = 100):
        """Generate synthetic DeFi data for testing"""
        import random
        import numpy as np
        
        db = SessionLocal()
        try:
            base_time = datetime.utcnow() - timedelta(days=30)
            
            for i in range(num_samples):
                # Simulate realistic DeFi metrics with some risk events
                timestamp = base_time + timedelta(hours=i*6)
                
                # TVL with occasional drops (risk events)
                tvl = 1_000_000 + random.gauss(0, 100_000)
                if random.random() < 0.05:  # 5% chance of drop
                    tvl *= 0.7  # 30% drop
                
                reserve0 = tvl / 2 * (1 + random.gauss(0, 0.1))
                reserve1 = tvl / 2 * (1 + random.gauss(0, 0.1))
                volume_24h = tvl * random.uniform(0.1, 0.5)
                
                features = {
                    'tvl_pct_change_1h': random.gauss(0, 5),
                    'reserve_imbalance': abs(reserve0 - reserve1) / (reserve0 + reserve1),
                    'volume_tvl_ratio': volume_24h / tvl,
                    'volatility_24h': random.uniform(0.02, 0.15),
                    'leverage_ratio': random.uniform(1.0, 3.0),
                }
                
                snapshot = Snapshot(
                    snapshot_id=f"synthetic-{pool_id}-{i}",
                    pool_id=pool_id,
                    timestamp=timestamp,
                    tvl=tvl,
                    reserve0=reserve0,
                    reserve1=reserve1,
                    volume_24h=volume_24h,
                    oracle_price=1.0,
                    features=features,
                    source='synthetic'
                )
                db.add(snapshot)
            
            db.commit()
            print(f"Generated {num_samples} synthetic snapshots for pool {pool_id}")
        finally:
            db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch DeFi data')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--synthetic', action='store_true', help='Generate synthetic data')
    parser.add_argument('--pool', default='0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc',
                        help='Pool address')
    args = parser.parse_args()
    
    # Initialize database
    init_db()
    
    fetcher = DataFetcher()
    
    if args.synthetic:
        print("Generating synthetic data...")
        fetcher.generate_synthetic_data('test_pool_1', 200)
        fetcher.generate_synthetic_data('test_pool_2', 200)
        print("Synthetic data generation complete")
    else:
        pool_id = "uniswap_v2_usdc_eth"
        print(f"Fetching data for pool {pool_id}...")
        snapshot_id = fetcher.fetch_and_store(pool_id, args.pool)
        if snapshot_id:
            print(f"Success! Snapshot ID: {snapshot_id}")
        else:
            print("Failed to fetch data")
