#!/usr/bin/env python3
"""Background scheduler for periodic data fetching and risk updates

Extended for Phase 1 with:
- Hourly snapshot collection for time-series analysis
- Historical data seeding support
- Feature computation integration
"""

import time
import logging
from datetime import datetime
from threading import Lock
from apscheduler.schedulers.background import BackgroundScheduler

from data_fetcher import DataFetcher
from model_server import ModelServer
from signer import PayloadSigner
from submit_to_chain import ChainSubmitter
from database import SessionLocal, Snapshot
from config import config

# Phase 1: Time-series imports
from jobs.hourly_snapshot import HourlySnapshotCollector
from features.basic_timeseries import TimeSeriesFeatureEngine

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scheduler")

# ------------------------------------------------------------------
# Global scheduler reference (for manual trigger)
# ------------------------------------------------------------------
_global_scheduler = None


def set_global_scheduler(scheduler):
    global _global_scheduler
    _global_scheduler = scheduler


def trigger_manual_fetch():
    if _global_scheduler:
        logger.info("📡 Manual fetch requested")
        _global_scheduler.fetch_all_protocols_data()
    else:
        logger.warning("⚠️ Scheduler not initialized yet")


# ------------------------------------------------------------------
# Scheduler Class
# ------------------------------------------------------------------
class RiskScheduler:
    def __init__(self):
        self.data_fetcher = DataFetcher()
        self.model_server = ModelServer()
        self.signer = PayloadSigner()
        self.submitter = ChainSubmitter()

        self.fetch_lock = Lock()
        self.scheduler = BackgroundScheduler()
        
        # Phase 1: Time-series components
        self.hourly_collector = HourlySnapshotCollector()
        self.feature_engine = TimeSeriesFeatureEngine()
        self._history_seeded = False

    # -----------------------------
    # SAFE FETCH (LOCKED)
    # -----------------------------
    def fetch_all_protocols_data(self):
        if not self.fetch_lock.acquire(blocking=False):
            logger.info("⏭️ Fetch already running, skipping")
            return []

        try:
            logger.info("🔄 Fetching protocol data...")
            snapshot_ids = self.data_fetcher.fetch_all_protocols()
            logger.info(f"✅ Fetched {len(snapshot_ids)} protocols")
            return snapshot_ids
        except Exception as e:
            logger.error(f"❌ Fetch failed: {e}")
            return []
        finally:
            self.fetch_lock.release()

    # -----------------------------
    # RISK COMPUTATION
    # -----------------------------
    def compute_and_submit_risks(self):
        logger.info("📊 Computing risk scores...")
        db = SessionLocal()

        try:
            pool_ids = [p[0] for p in db.query(Snapshot.pool_id).distinct().all()]
            logger.info(f"Found {len(pool_ids)} pools")

            submitted = 0
            for pool_id in pool_ids:
                try:
                    result = self.model_server.predict_risk(pool_id)
                    if result["risk_score"] >= 30:
                        payload = self.signer.create_payload(
                            pool_id=pool_id,
                            risk_score=result["risk_score"],
                            top_reasons=result["top_reasons"],
                            model_version="xgb_v1",
                            artifact_cid="QmModelArtifact",
                        )
                        signed = self.signer.sign_payload(payload)
                        tx = self.submitter.submit_risk(signed)
                        logger.info(f"✓ {pool_id}: {result['risk_score']} → {tx[:10]}...")
                        submitted += 1
                        time.sleep(2)
                except Exception as e:
                    logger.warning(f"⚠️ Pool {pool_id} failed: {e}")

            logger.info(f"✅ Submitted {submitted} risk updates")
        finally:
            db.close()

    # -----------------------------
    # PHASE 1: HOURLY SNAPSHOT COLLECTION
    # -----------------------------
    def collect_hourly_snapshots(self):
        """
        Hourly time-series data collection job.
        
        Collects snapshots for all protocols and stores in snapshot_history
        table for rolling window feature computation.
        """
        logger.info("=" * 60)
        logger.info(f"🕐 HOURLY SNAPSHOT COLLECTION @ {datetime.utcnow()}")
        logger.info("=" * 60)
        
        try:
            pools = self.hourly_collector.collect_hourly_snapshot()
            logger.info(f"✅ Collected {len(pools)} hourly snapshots")
            return pools
        except Exception as e:
            logger.error(f"❌ Hourly collection failed: {e}")
            return []
    
    def seed_historical_data(self, hours: int = 48):
        """
        Seed historical data for immediate feature computation.
        
        Call this once on startup to enable time-series features
        without waiting for real data accumulation.
        """
        if self._history_seeded:
            logger.info("📊 Historical data already seeded, skipping")
            return 0
        
        logger.info(f"🌱 Seeding {hours} hours of historical data...")
        try:
            records = self.hourly_collector.seed_historical_data(hours=hours)
            self._history_seeded = True
            logger.info(f"✅ Seeded {records} historical records")
            return records
        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            return 0
    
    def compute_timeseries_features(self):
        """
        Compute time-series features for all pools.
        
        This runs after hourly collection to update derived features.
        """
        logger.info("📊 Computing time-series features...")
        
        try:
            pool_ids = self.feature_engine.get_all_pool_ids()
            features_batch = self.feature_engine.compute_features_batch(pool_ids)
            
            # Log summary
            risk_signals_count = 0
            for pool_id, features in features_batch.items():
                signals = features.get_risk_signals()
                if signals:
                    risk_signals_count += len(signals)
                    for sig in signals:
                        logger.warning(
                            f"🚨 {pool_id}: [{sig['severity'].upper()}] {sig['description']}"
                        )
            
            logger.info(f"✅ Computed features for {len(pool_ids)} pools")
            if risk_signals_count > 0:
                logger.warning(f"⚠️ {risk_signals_count} risk signals detected")
            
            return features_batch
        except Exception as e:
            logger.error(f"❌ Feature computation failed: {e}")
            return {}

    # -----------------------------
    # FULL CYCLE
    # -----------------------------
    def full_update_cycle(self):
        logger.info("=" * 60)
        logger.info(f"🚀 Full cycle start @ {datetime.utcnow()}")
        logger.info("=" * 60)

        self.fetch_all_protocols_data()
        time.sleep(3)
        self.compute_and_submit_risks()

        logger.info("=" * 60)
        logger.info("✅ Full cycle complete")
        logger.info("=" * 60)

    # -----------------------------
    # START (NO IMMEDIATE RUN)
    # -----------------------------
    def start(self):
        logger.info("🚀 VeriRisk Scheduler starting")
        logger.info(f"📜 Contract: {config.ORACLE_CONTRACT_ADDRESS}")
        logger.info(f"🔑 Signer: {self.signer.address}")

        self.scheduler.add_job(
            self.fetch_all_protocols_data,
            "interval",
            minutes=5,
            id="fetch_data",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.compute_and_submit_risks,
            "interval",
            minutes=10,
            id="submit_risks",
            replace_existing=True,
        )

        self.scheduler.add_job(
            self.full_update_cycle,
            "interval",
            minutes=30,
            id="full_cycle",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("✅ Scheduler started")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("🛑 Scheduler stopped")
