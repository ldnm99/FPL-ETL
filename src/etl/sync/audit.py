"""
Pipeline Run History and Audit Ledger Module.
Provides dual logging (Supabase PostgreSQL + local SQLite) for tracking execution telemetry,
catching ingestion mistakes, and recording historical point updates.
"""
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import sqlite3
import logging
from typing import Optional, List, Dict, Any
from src.etl.schemas import PipelineRunAudit

logger = logging.getLogger("fpl_sync.audit")

# Default local SQLite audit DB path in Data/ directory
DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[3] / "Data" / "etl_history.sqlite"


def _init_sqlite_db(db_path: Path):
    """Ensures SQLite audit database and table exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_timestamp TEXT NOT NULL,
                mode TEXT NOT NULL,
                gameweek_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                fixtures_count INTEGER DEFAULT 0,
                managers_count INTEGER DEFAULT 0,
                picks_count INTEGER DEFAULT 0,
                perf_records_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sqlite_run_timestamp ON pipeline_run_history(run_timestamp DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sqlite_run_gw ON pipeline_run_history(gameweek_id);")
        conn.commit()


def record_pipeline_audit(
    supabase,
    audit: PipelineRunAudit,
    sqlite_path: Path = DEFAULT_SQLITE_PATH
) -> bool:
    """
    Records an execution entry into both Supabase Postgres and local SQLite.
    Guarantees no crashes even if network or DB connection is transiently unavailable.
    """
    record_dict = audit.model_dump()
    success = True

    # 1. Supabase PostgreSQL Ledger
    try:
        if supabase:
            supabase.table("pipeline_run_history").insert(record_dict).execute()
            logger.info(f"📜 Audit record #{audit.mode} (status: {audit.status}, {audit.duration_ms}ms) saved to Supabase.")
    except Exception as err:
        logger.warning(f"⚠️ Notice logging audit to Supabase (table may need DDL migration): {err}")
        success = False

    # 2. Local SQLite Ledger
    try:
        _init_sqlite_db(sqlite_path)
        with sqlite3.connect(sqlite_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pipeline_run_history (
                    run_timestamp, mode, gameweek_id, status, duration_ms,
                    fixtures_count, managers_count, picks_count, perf_records_count, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit.run_timestamp,
                audit.mode,
                audit.gameweek_id,
                audit.status,
                audit.duration_ms,
                audit.fixtures_count,
                audit.managers_count,
                audit.picks_count,
                audit.perf_records_count,
                audit.error_message
            ))
            conn.commit()
    except Exception as err:
        logger.warning(f"⚠️ Notice logging audit to local SQLite: {err}")

    return success
