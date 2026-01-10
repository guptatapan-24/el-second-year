from fastapi import APIRouter, BackgroundTasks, Query
from sqlalchemy import func
from database import SessionLocal, Snapshot, init_db
from scheduler import trigger_manual_fetch
from datetime import datetime
import subprocess
import sys
import os
import logging
import threading
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/protocols")

# Track background task status
_init_status = {"running": False, "phase": "", "progress": 0, "error": None, "completed": False}
_status_lock = threading.Lock()


def update_status(phase: str, progress: int, error: str = None, completed: bool = False):
    global _init_status
    with _status_lock:
        _init_status["phase"] = phase
        _init_status["progress"] = progress
        _init_status["error"] = error
        _init_status["completed"] = completed
        if error:
            _init_status["running"] = False


@router.get("")
def get_protocols():
    """
    Return ONLY the latest snapshot per pool_id.
    Filters to show only the 28 expected protocols:
    - 18 real DeFi protocol pools (from fetch_real_protocols.py)
    - 10 synthetic pools for ML training (from data_fetcher.py --predictive)
    """
    # Expected pool_id prefixes for the 28 protocols
    EXPECTED_POOL_PREFIXES = [
        # Real DeFi protocols (18 pools)
        'uniswap_v2_',    # 4 pools
        'uniswap_v3_',    # 3 pools
        'aave_v3_',       # 4 pools
        'compound_v2_',   # 4 pools
        'curve_',         # 3 pools
        # Synthetic pools for training (10 pools)
        'synthetic_',     # 5 pools
        'high_risk_pool',
        'critical_risk_pool',
        'late_crash_pool_',  # 3 pools
    ]
    
    db = SessionLocal()
    try:
        # Subquery: latest timestamp per pool
        subq = (
            db.query(
                Snapshot.pool_id,
                func.max(Snapshot.timestamp).label("latest_ts")
            )
            .group_by(Snapshot.pool_id)
            .subquery()
        )

        # Join snapshots with subquery
        rows = (
            db.query(Snapshot)
            .join(
                subq,
                (Snapshot.pool_id == subq.c.pool_id)
                & (Snapshot.timestamp == subq.c.latest_ts)
            )
            .order_by(Snapshot.timestamp.desc())
            .all()
        )

        # Filter to only expected protocols
        def is_expected_pool(pool_id: str) -> bool:
            for prefix in EXPECTED_POOL_PREFIXES:
                if pool_id.startswith(prefix) or pool_id == prefix.rstrip('_'):
                    return True
            return False

        filtered_rows = [r for r in rows if is_expected_pool(r.pool_id)]

        return [
            {
                "pool_id": r.pool_id,
                "protocol": r.features.get("protocol") if r.features else None,
                "category": r.features.get("category") if r.features else "DeFi",
                "tvl": r.tvl,
                "volume_24h": r.volume_24h,
                "last_update": r.timestamp.isoformat(),
                "data_source": r.source,
            }
            for r in filtered_rows
        ]
    finally:
        db.close()


@router.post("/fetch")
def fetch_protocols():
    trigger_manual_fetch()
    return {"status": "queued"}


@router.get("/status")
def get_data_status():
    """Get current database and initialization status"""
    db = SessionLocal()
    try:
        # Count snapshots
        total_snapshots = db.query(Snapshot).count()
        
        # Count unique pools
        pool_count = db.query(func.count(func.distinct(Snapshot.pool_id))).scalar() or 0
        
        # Get latest timestamp
        latest = db.query(func.max(Snapshot.timestamp)).scalar()
        
        # Get oldest timestamp
        oldest = db.query(func.min(Snapshot.timestamp)).scalar()
        
        # Calculate hours of history
        hours_of_history = 0
        if latest and oldest:
            hours_of_history = int((latest - oldest).total_seconds() / 3600)
        
        # Check if model exists - use cross-platform path
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(os.path.dirname(backend_dir), "models", "xgb_veririsk_v2_predictive.pkl")
        model_exists = os.path.exists(model_path)
        
        # Get init status
        with _status_lock:
            init_status = _init_status.copy()
        
        return {
            "total_snapshots": total_snapshots,
            "pool_count": pool_count,
            "hours_of_history": hours_of_history,
            "latest_snapshot": latest.isoformat() if latest else None,
            "oldest_snapshot": oldest.isoformat() if oldest else None,
            "model_trained": model_exists,
            "data_ready": total_snapshots > 0 and hours_of_history >= 24,
            "init_status": init_status
        }
    finally:
        db.close()


def run_full_initialization(days: int = 30):
    """
    Background task to initialize the system with data and train model.
    
    Sequence (per user requirement):
    1. First run data_fetcher.py --predictive (generates synthetic training data)
    2. Then run fetch_real_protocols.py --fetch-history --days 30 (fetches real DeFi data)
    3. Then train the model with model_trainer.py
    4. Run predictions and generate alerts
    """
    global _init_status
    
    with _status_lock:
        _init_status["running"] = True
        _init_status["error"] = None
        _init_status["completed"] = False
    
    # Use cross-platform path detection
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Phase 1: Generate predictive synthetic data for model training
        update_status("Generating predictive synthetic data...", 5)
        logger.info("📊 Phase 1: Generating predictive synthetic data...")
        
        result = subprocess.run(
            [sys.executable, "data_fetcher.py", "--predictive"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"Synthetic data generation failed: {result.stderr}")
            update_status("Synthetic data generation failed", 5, error=result.stderr[:500])
            return
        
        logger.info("✅ Predictive synthetic data generated")
        update_status("Fetching real historical data from DeFiLlama...", 20)
        
        # Phase 2: Fetch real historical data from DeFiLlama
        logger.info("🌐 Phase 2: Fetching real historical data...")
        
        result = subprocess.run(
            [sys.executable, "fetch_real_protocols.py", "--fetch-history", "--days", str(days)],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"Fetch failed: {result.stderr}")
            update_status("Data fetch failed", 20, error=result.stderr[:500])
            return
        
        logger.info("✅ Historical data fetched successfully")
        update_status("Training ML model...", 50)
        
        # Phase 3: Train the model
        logger.info("🧠 Phase 3: Training ML model...")
        
        result = subprocess.run(
            [sys.executable, "model_trainer.py"],
            cwd=backend_dir,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            logger.error(f"Training failed: {result.stderr}")
            update_status("Model training failed", 50, error=result.stderr[:500])
            return
        
        logger.info("✅ Model trained successfully")
        update_status("Running risk predictions...", 75)
        
        # Phase 4: Run predictions for all pools
        logger.info("📊 Phase 4: Running predictions for all pools...")
        
        # Import risk evaluator to run predictions
        from services.risk_evaluator import get_risk_evaluator
        evaluator = get_risk_evaluator()
        
        # Predict all pools
        results = evaluator.predict_all_pools()
        logger.info(f"✅ Predicted risk for {len(results)} pools")
        
        update_status("Generating alerts...", 90)
        
        # Phase 5: Evaluate alerts
        alerts = evaluator.evaluate_all_alerts()
        logger.info(f"✅ Generated {len(alerts)} alerts")
        
        update_status("Initialization complete!", 100, completed=True)
        logger.info("🎉 Full initialization complete!")
        
    except subprocess.TimeoutExpired:
        logger.error("Process timed out")
        update_status("Process timed out", _init_status["progress"], error="Operation timed out after 5 minutes")
    except Exception as e:
        logger.error(f"Initialization failed: {str(e)}")
        update_status("Initialization failed", _init_status["progress"], error=str(e)[:500])
    finally:
        with _status_lock:
            _init_status["running"] = False


@router.post("/initialize")
def initialize_system(background_tasks: BackgroundTasks, days: int = Query(default=30, ge=7, le=90)):
    """
    Initialize the VeriRisk system with real DeFiLlama data.
    
    This endpoint:
    1. Fetches 30 days of REAL historical TVL from DeFiLlama
    2. Trains the XGBoost ML model on this data
    3. Runs predictions for all pools
    4. Generates initial alerts
    
    This is a background task - use GET /api/protocols/status to check progress.
    """
    with _status_lock:
        if _init_status["running"]:
            return {
                "status": "already_running",
                "message": "Initialization is already in progress",
                "current_phase": _init_status["phase"],
                "progress": _init_status["progress"]
            }
    
    # Start background task
    background_tasks.add_task(run_full_initialization, days)
    
    return {
        "status": "started",
        "message": f"Initializing VeriRisk with {days} days of historical data",
        "steps": [
            "1. Fetching real historical TVL from DeFiLlama",
            "2. Training XGBoost ML model",
            "3. Running risk predictions for all pools",
            "4. Generating alerts"
        ],
        "note": "Use GET /api/protocols/status to check progress"
    }


@router.post("/train-model")
def train_model_endpoint(background_tasks: BackgroundTasks):
    """
    Train or retrain the ML model on existing data.
    """
    def train_task():
        try:
            # Use cross-platform path detection
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            update_status("Training ML model...", 50)
            result = subprocess.run(
                [sys.executable, "model_trainer.py"],
                cwd=backend_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                update_status("Model training complete!", 100, completed=True)
            else:
                update_status("Training failed", 50, error=result.stderr[:500])
        except Exception as e:
            update_status("Training error", 50, error=str(e)[:500])
        finally:
            with _status_lock:
                _init_status["running"] = False
    
    with _status_lock:
        if _init_status["running"]:
            return {"status": "busy", "message": "Another operation is in progress"}
        _init_status["running"] = True
    
    background_tasks.add_task(train_task)
    return {"status": "started", "message": "Model training started"}


@router.post("/predict-all")
def predict_all_endpoint():
    """
    Run predictions for all pools and update risk history.
    """
    from services.risk_evaluator import get_risk_evaluator
    
    evaluator = get_risk_evaluator()
    results = evaluator.predict_all_pools()
    alerts = evaluator.evaluate_all_alerts()
    
    return {
        "status": "success",
        "pools_predicted": len(results),
        "alerts_generated": len(alerts),
        "timestamp": datetime.utcnow().isoformat()
    }