"""
Pipeline Heartbeat and Status Telemetry Module.
Writes real-time heartbeat timestamps and active status into Supabase sync_status table.
"""
import logging
from datetime import datetime, timezone
from src.etl.sync.fixtures import is_fixture_window_active

logger = logging.getLogger("fpl_sync.heartbeat")


def update_sync_heartbeat(supabase, status: str = "ok", current_gw: int = 1) -> bool:
    """
    Writes a heartbeat timestamp into 'sync_status' in Supabase.
    Provides instant pipeline freshness telemetry to the web frontend.
    """
    try:
        record = {
            "id": 1,
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "current_gameweek": current_gw,
            "is_fixture_active": is_fixture_window_active(supabase, current_gw=current_gw),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("sync_status").upsert(record).execute()
        logger.info(f"💓 Pipeline heartbeat updated in 'sync_status' (status={status}, GW={current_gw})")
        return True
    except Exception as err:
        logger.warning(f"⚠️ Heartbeat write notice (sync_status table may be pending): {err}")
        return False
