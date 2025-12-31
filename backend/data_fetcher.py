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
        import random
        from datetime import timedelta

        db = SessionLocal()
        try:
            base_time = datetime.utcnow() - timedelta(days=30)

            for i in range(num_samples):
                timestamp = base_time + timedelta(hours=i)

                # ---- FORCE RISK EVENTS ----
                if random.random() < 0.3:  # 30% risky
                    tvl = random.uniform(200_000, 500_000)
                    tvl_pct_change = random.uniform(-50, -25)
                    volatility = random.uniform(0.12, 0.25)
                    leverage = random.uniform(2.5, 4.0)
                else:  # normal
                    tvl = random.uniform(800_000, 1_200_000)
                    tvl_pct_change = random.uniform(-5, 5)
                    volatility = random.uniform(0.02, 0.05)
                    leverage = random.uniform(1.0, 1.5)

                reserve0 = tvl * random.uniform(0.4, 0.6)
                reserve1 = tvl - reserve0
                volume_24h = tvl * random.uniform(0.2, 0.6)

                features = {
                    "tvl_pct_change_1h": tvl_pct_change,
                    "reserve_imbalance": abs(reserve0 - reserve1) / tvl,
                    "volume_tvl_ratio": volume_24h / tvl,
                    "volatility_24h": volatility,
                    "leverage_ratio": leverage,
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
                    source="synthetic",
                )
                db.add(snapshot)

            db.commit()
            print(f"Generated {num_samples} synthetic snapshots for {pool_id}")
        finally:
            db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch DeFi data')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--all-protocols', action='store_true', help='Fetch all protocols')
    parser.add_argument('--synthetic', action='store_true', help='Generate synthetic data')
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
    elif args.synthetic:
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
