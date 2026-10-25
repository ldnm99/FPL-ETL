"""
FPL Draft -> Supabase PostgreSQL ELT Sync Orchestrator.

Main entry point and CLI runner for syncing FPL Draft data to Supabase.
Delegates to modular subpackages under src.etl.sync with Pydantic validation
and dual-ledger run history auditing.
"""
import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path for direct script execution
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import time
import logging
from datetime import datetime, timezone
from src.etl.schemas import PipelineRunAudit
from src.etl.sync import (
    get_supabase_client,
    sync_bootstrap_data,
    sync_fixtures,
    is_fixture_window_active,
    sync_league_managers,
    sync_manager_picks_and_performance,
    update_sync_heartbeat,
    record_pipeline_audit,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fpl_sync.orchestrator")


def main(
    full_sync: bool = False,
    loop_interval: int = 0,
    sync_all_history: bool = False,
    check_active: bool = False,
    is_eod: bool = False
):
    mode_name = "EOD CONSOLIDATION" if is_eod else ("FULL METADATA" if full_sync else "FAST LIVE SYNC")
    logger.info("==================================================")
    logger.info(f"🚀 Modern ELT Sync Orchestrator (Mode: {mode_name})")
    logger.info("==================================================")

    supabase = get_supabase_client()

    while True:
        t0 = time.time()
        current_gw_id = 1
        fixtures_count = 0
        managers_count = 0
        picks_count = 0
        perf_records_count = 0
        status_code = "ok"
        error_msg = None

        try:
            # 1. Sync Static Metadata when requested or in EOD mode
            if full_sync or is_eod:
                logger.info("📌 Syncing static metadata (Clubs, Players, Gameweeks)...")
                current_gw_id = sync_bootstrap_data(supabase) or 1
            else:
                logger.info("⚡ Fast Live Mode: Skipping static club/player tables for sub-second execution...")
                try:
                    res = supabase.table("dim_gameweeks").select("id").eq("is_current", True).limit(1).execute()
                    current_gw_id = res.data[0]["id"] if res.data else 1
                except Exception:
                    current_gw_id = 1

            # 2. Sync Fixtures for Current Gameweek to ensure up-to-date match state
            fixtures_count = sync_fixtures(supabase, current_gw=current_gw_id, refresh_all=(full_sync and not is_eod))

            # 3. If in check_active mode, test if matches are active before doing heavier picks/perf calls
            if check_active and not is_eod:
                active_now = is_fixture_window_active(supabase, current_gw=current_gw_id)
                if not active_now:
                    duration_ms = int((time.time() - t0) * 1000)
                    logger.info("⏸️ Matchday Window Check: No live, provisional, or imminent matches right now.")
                    logger.info("🌙 Exiting early to preserve GitHub Actions free runner quota.")
                    update_sync_heartbeat(supabase, status="idle_standby", current_gw=current_gw_id)
                    record_pipeline_audit(
                        supabase,
                        PipelineRunAudit(
                            run_timestamp=datetime.now(timezone.utc).isoformat(),
                            mode="check_active_idle",
                            gameweek_id=current_gw_id,
                            status="idle_standby",
                            duration_ms=duration_ms,
                            fixtures_count=fixtures_count
                        )
                    )
                    return
                logger.info("🔥 Live match action detected! Proceeding with manager picks and live stats sync...")

            # 4. Sync Managers, Picks & Live Performance Stats
            entries = sync_league_managers(supabase)
            managers_count = len(entries) if entries else 0
            if entries:
                stats_res = sync_manager_picks_and_performance(
                    supabase,
                    entries,
                    current_gw=current_gw_id,
                    sync_all_history=sync_all_history
                )
                picks_count = stats_res.get("picks_count", 0)
                perf_records_count = stats_res.get("perf_records_count", 0)

            # 5. Update Telemetry Heartbeat & Run History Audit Ledger
            duration_ms = int((time.time() - t0) * 1000)
            status_code = "eod_settled" if is_eod else "ok"
            update_sync_heartbeat(supabase, status=status_code, current_gw=current_gw_id)

            record_pipeline_audit(
                supabase,
                PipelineRunAudit(
                    run_timestamp=datetime.now(timezone.utc).isoformat(),
                    mode=mode_name.lower().replace(" ", "_"),
                    gameweek_id=current_gw_id,
                    status=status_code,
                    duration_ms=duration_ms,
                    fixtures_count=fixtures_count,
                    managers_count=managers_count,
                    picks_count=picks_count,
                    perf_records_count=perf_records_count
                )
            )

            logger.info(f"✨ ELT Sync Complete ({mode_name}) in {duration_ms}ms! SQL Views updated automatically.")

            # 6. If in EOD mode, execute Scikit-Learn Performance Clustering & Analytics
            if is_eod:
                logger.info("🧠 Running Nightly Scikit-Learn Gold Analytics & Performance Clustering Pipeline...")
                try:
                    from src.etl.gold_analytics import run_gold_analytics_pipeline
                    analytics_res = run_gold_analytics_pipeline()
                    logger.info(
                        f"✅ Gold Analytics Pipeline complete: {analytics_res.get('total_players_analyzed', 0)} "
                        f"players analyzed in {analytics_res.get('execution_time_seconds', 0)}s."
                    )
                except Exception as e_analytics:
                    logger.warning(f"⚠️ Gold Analytics execution encountered an issue: {e_analytics}")

        except Exception as e:
            duration_ms = int((time.time() - t0) * 1000)
            error_msg = str(e)
            logger.error(f"❌ Error during sync cycle: {e}")
            record_pipeline_audit(
                supabase,
                PipelineRunAudit(
                    run_timestamp=datetime.now(timezone.utc).isoformat(),
                    mode=mode_name.lower().replace(" ", "_"),
                    gameweek_id=current_gw_id,
                    status="error",
                    duration_ms=duration_ms,
                    fixtures_count=fixtures_count,
                    managers_count=managers_count,
                    picks_count=picks_count,
                    perf_records_count=perf_records_count,
                    error_message=error_msg
                )
            )

        if loop_interval <= 0:
            break

        # Adaptive Polling: 60s when matches are live, 30 min (1800s) eco-mode when idle
        active_fixtures = is_fixture_window_active(supabase, current_gw=current_gw_id)
        sleep_duration = loop_interval if active_fixtures else max(loop_interval, 1800)
        mode_label = "⚽ LIVE MATCHES ONGOING (60s loop)" if active_fixtures else "🌙 ECO MODE: No live matches active (30m loop)"
        logger.info(f"⏱️ {mode_label} -> Sleeping for {sleep_duration} seconds...")
        time.sleep(sleep_duration)


if __name__ == "__main__":
    if "--refresh-season-fixtures" in sys.argv:
        logger.info("📅 Initiating Monthly Full Season Fixtures Calendar Sync (380 Matches)...")
        sb_client = get_supabase_client()
        sync_fixtures(sb_client, refresh_all=True)
        logger.info("✅ Full Season Fixtures Calendar Synchronized successfully.")
        sys.exit(0)

    is_full = "--full" in sys.argv
    is_eod = "--eod" in sys.argv
    is_check_active = "--check-active" in sys.argv
    is_history = "--history" in sys.argv
    is_once = "--once" in sys.argv

    interval = 0
    if "--loop" in sys.argv and not is_once:
        try:
            idx = sys.argv.index("--loop")
            interval = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 60
        except Exception:
            interval = 60

    main(
        full_sync=is_full,
        loop_interval=interval,
        sync_all_history=is_history,
        check_active=is_check_active,
        is_eod=is_eod
    )
