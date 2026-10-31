"""
Modular FPL Sync Package.
High-efficiency, zero-cost ELT synchronizer connecting Premier League APIs to Supabase PostgreSQL.
"""
from src.etl.sync.client import (
    create_resilient_session,
    get_supabase_client,
    fetch_json,
    HTTP_SESSION,
    DEFAULT_LEAGUE_ID
)
from src.etl.sync.audit import record_pipeline_audit
from src.etl.sync.bootstrap import sync_bootstrap_data
from src.etl.sync.fixtures import sync_fixtures, is_fixture_window_active
from src.etl.sync.managers import sync_league_managers
from src.etl.sync.performance import (
    sync_manager_picks_and_performance,
    reconcile_standings_with_official,
)
from src.etl.sync.heartbeat import update_sync_heartbeat
from src.etl.sync.history_feed import feed_local_history

__all__ = [
    "create_resilient_session",
    "get_supabase_client",
    "fetch_json",
    "HTTP_SESSION",
    "DEFAULT_LEAGUE_ID",
    "record_pipeline_audit",
    "sync_bootstrap_data",
    "sync_fixtures",
    "is_fixture_window_active",
    "sync_league_managers",
    "sync_manager_picks_and_performance",
    "reconcile_standings_with_official",
    "update_sync_heartbeat",
    "feed_local_history",
]
