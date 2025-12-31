"""Database models package for VeriRisk time-series extension"""

from db_models.snapshot_history import SnapshotHistory, init_snapshot_history_db

__all__ = ['SnapshotHistory', 'init_snapshot_history_db']
