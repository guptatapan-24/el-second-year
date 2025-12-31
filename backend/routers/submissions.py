from fastapi import APIRouter
# from database import SessionLocal, Submission
from database import SessionLocal, RiskSubmission


router = APIRouter()

@router.get("/submissions")
# @router.get("/submissions")
def get_submissions():
    db = SessionLocal()
    try:
        return [
            {
                "pool_id": r.pool_id,
                "risk_score": r.risk_score,
                "timestamp": r.timestamp.isoformat(),
                "model_version": r.model_version,
            }
            for r in db.query(RiskSubmission).all()
        ]
    finally:
        db.close()
