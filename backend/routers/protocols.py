from fastapi import APIRouter
from sqlalchemy import func
from database import SessionLocal, Snapshot
from scheduler import trigger_manual_fetch

router = APIRouter(prefix="/protocols")


@router.get("")
def get_protocols():
    """
    Return ONLY the latest snapshot per pool_id
    """
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

        return [
            {
                "pool_id": r.pool_id,
                "protocol": r.features.get("protocol"),
                "category": r.features.get("category"),
                "tvl": r.tvl,
                "volume_24h": r.volume_24h,
                "last_update": r.timestamp.isoformat(),
                "data_source": r.source,
            }
            for r in rows
        ]
    finally:
        db.close()


@router.post("/fetch")
def fetch_protocols():
    trigger_manual_fetch()
    return {"status": "queued"}
