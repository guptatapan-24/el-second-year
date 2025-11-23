from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import config

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Snapshot(Base):
    """DeFi protocol snapshot with features"""
    __tablename__ = "snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(String, unique=True, index=True)
    pool_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Raw metrics
    tvl = Column(Float)
    reserve0 = Column(Float)
    reserve1 = Column(Float)
    volume_24h = Column(Float)
    oracle_price = Column(Float)
    
    # Derived features (JSON for flexibility)
    features = Column(JSON)
    
    # Metadata
    source = Column(String)  # 'uniswap_v2', 'uniswap_v3', etc.
    
class RiskSubmission(Base):
    """Record of risk submissions to chain"""
    __tablename__ = "risk_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    pool_id = Column(String, index=True)
    risk_score = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Explainability
    top_reasons = Column(JSON)
    model_version = Column(String)
    artifact_cid = Column(String)
    
    # Signing & submission
    signature = Column(String)
    tx_hash = Column(String)
    nonce = Column(Integer)
    status = Column(String)  # 'pending', 'confirmed', 'failed'

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
