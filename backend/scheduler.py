#!/usr/bin/env python3
"""Background scheduler for periodic data fetching and risk updates"""

import time
import asyncio
import requests
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from data_fetcher import DataFetcher
from model_server import ModelServer
from signer import PayloadSigner
from submit_to_chain import ChainSubmitter
from database import SessionLocal, Snapshot
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RiskScheduler:
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.model_server = ModelServer()
        self.signer = PayloadSigner()
        self.submitter = ChainSubmitter()
        self.scheduler = BackgroundScheduler()
        
    def fetch_all_protocols_data(self):
        """Fetch fresh data from all protocols"""
        try:
            logger.info(f"\n🔄 Fetching protocol data...")
            snapshot_ids = self.data_fetcher.fetch_all_protocols()
            logger.info(f"✅ Fetched data for {len(snapshot_ids)} protocols")
            return snapshot_ids
        except Exception as e:
            logger.error(f"❌ Error fetching protocols: {e}")
            return []
    
    def compute_and_submit_risks(self):
        """Compute risk scores for all pools and submit high-risk ones to chain"""
        try:
            print(f"\n[{datetime.utcnow()}] Computing risk scores...")
            
            # Get all unique pool IDs from database
            db = SessionLocal()
            try:
                pool_ids = db.query(Snapshot.pool_id).distinct().all()
                pool_ids = [p[0] for p in pool_ids]
                print(f"Found {len(pool_ids)} pools")
                
                high_risk_count = 0
                for pool_id in pool_ids:
                    try:
                        # Predict risk
                        result = self.model_server.predict_risk(pool_id)
                        risk_score = result['risk_score']
                        
                        # Submit to chain if risk is medium or higher (>30)
                        if risk_score >= 30:
                            # Create and sign payload
                            payload = self.signer.create_payload(
                                pool_id=pool_id,
                                risk_score=risk_score,
                                top_reasons=result['top_reasons'],
                                model_version='xgb_v1',
                                artifact_cid='QmModelArtifact'
                            )
                            signed = self.signer.sign_payload(payload)
                            
                            # Submit to chain
                            tx_hash = self.submitter.submit_risk(signed)
                            print(f"  ✓ {pool_id}: {risk_score:.1f} → {tx_hash[:10]}...")
                            high_risk_count += 1
                            
                            # Rate limit to avoid overwhelming RPC
                            time.sleep(2)
                        
                    except Exception as e:
                        print(f"  ✗ Error processing {pool_id}: {e}")
                        continue
                
                print(f"✓ Submitted {high_risk_count} risk updates to chain")
            finally:
                db.close()
                
        except Exception as e:
            print(f"✗ Error in risk computation: {e}")
    
    def full_update_cycle(self):
        """Complete update cycle: fetch data + compute risks"""
        logger.info("\n" + "="*60)
        logger.info(f"🚀 Starting full update cycle at {datetime.utcnow()}")
        logger.info("="*60)
        
        # Step 1: Fetch fresh data
        self.fetch_all_protocols_data()
        
        # Step 2: Compute and submit risks
        time.sleep(3)  # Brief pause between steps
        self.compute_and_submit_risks()
        
        logger.info("\n" + "="*60)
        logger.info(f"✅ Cycle complete at {datetime.utcnow()}")
        logger.info("="*60 + "\n")
    
    def start(self):
        """Start the scheduler"""
        logger.info("🚀 VeriRisk Risk Scheduler Starting...")
        logger.info(f"   📜 Contract: {config.ORACLE_CONTRACT_ADDRESS}")
        logger.info(f"   🔑 Signer: {self.signer.address}")
        
        # Run immediately on start
        self.full_update_cycle()
        
        # Schedule periodic updates
        # Every 5 minutes: fetch fresh data
        self.scheduler.add_job(
            self.fetch_all_protocols_data,
            'interval',
            minutes=5,
            id='fetch_data',
            replace_existing=True
        )
        
        # Every 10 minutes: compute and submit risks
        self.scheduler.add_job(
            self.compute_and_submit_risks,
            'interval',
            minutes=10,
            id='submit_risks',
            replace_existing=True
        )
        
        # Every 30 minutes: full cycle
        self.scheduler.add_job(
            self.full_update_cycle,
            'interval',
            minutes=30,
            id='full_cycle',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("✅ Scheduler started successfully!")
        logger.info("   ⏰ Data fetch: every 5 minutes")
        logger.info("   📊 Risk computation: every 10 minutes")
        logger.info("   🔄 Full cycle: every 30 minutes")
        
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        print("Scheduler stopped")

if __name__ == "__main__":
    scheduler = RiskScheduler()
    scheduler.start()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
