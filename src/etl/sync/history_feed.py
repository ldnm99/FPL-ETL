"""
History Feed Module (Dual-Writer Engine)
Automatically updates the local SQLite historical database (Data/fpl_draft_history.sqlite)
and appends to the unified multi-season Gold Parquet files whenever the live ETL runs.
"""

import sqlite3
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("fpl_sync.history_feed")


def get_db_path(repo_root: Path) -> Path:
    return repo_root / "Data" / "fpl_draft_history.sqlite"


def get_history_dir(repo_root: Path) -> Path:
    hist_dir = repo_root / "Data" / "history"
    hist_dir.mkdir(parents=True, exist_ok=True)
    return hist_dir


def feed_local_history(
    repo_root: Path,
    season_id: str,
    gameweek_id: int,
    manager_picks: Optional[List[Dict[str, Any]]] = None,
    player_performance: Optional[List[Dict[str, Any]]] = None,
) -> bool:
    """
    Feeds live gameweek picks and performances into the local SQLite historical database
    and updates the unified multi-season Parquet files.
    """
    db_path = get_db_path(repo_root)
    if not db_path.exists():
        logger.warning(f"History database not found at {db_path}. Skipping dual-write.")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 1. Update SQLite Fact Manager Picks
        if manager_picks:
            sqlite_picks = []
            for p in manager_picks:
                sqlite_picks.append({
                    "season_id": season_id,
                    "gameweek_id": gameweek_id,
                    "manager_id": p.get("manager_id"),
                    "player_id": p.get("player_id"),
                    "position": p.get("position", 1),
                    "is_captain": 1 if p.get("is_captain") else 0,
                    "multiplier": p.get("multiplier", 1),
                })
            
            cur.executemany("""
            INSERT OR REPLACE INTO fact_manager_picks 
                (season_id, gameweek_id, manager_id, player_id, position, is_captain, multiplier)
            VALUES 
                (:season_id, :gameweek_id, :manager_id, :player_id, :position, :is_captain, :multiplier);
            """, sqlite_picks)
            logger.info(f"Dual-wrote {len(sqlite_picks)} manager picks into SQLite history.")

        # 2. Update SQLite Fact Player Performance
        if player_performance:
            sqlite_perf = []
            for perf in player_performance:
                sqlite_perf.append({
                    "season_id": season_id,
                    "gameweek_id": gameweek_id,
                    "player_id": perf.get("player_id"),
                    "total_points": perf.get("total_points", 0),
                    "minutes": perf.get("minutes", 0),
                    "goals_scored": perf.get("goals_scored", 0),
                    "assists": perf.get("assists", 0),
                    "clean_sheets": perf.get("clean_sheets", 0),
                    "defensive_contribution": perf.get("defcons", perf.get("defensive_contribution", 0)),
                    "bps": perf.get("bps", 0),
                    "bonus": perf.get("bonus", 0),
                })

            cur.executemany("""
            INSERT OR REPLACE INTO fact_player_performance
                (season_id, gameweek_id, player_id, total_points, minutes, goals_scored, assists, clean_sheets, defensive_contribution, bps, bonus)
            VALUES
                (:season_id, :gameweek_id, :player_id, :total_points, :minutes, :goals_scored, :assists, :clean_sheets, :defensive_contribution, :bps, :bonus);
            """, sqlite_perf)
            logger.info(f"Dual-wrote {len(sqlite_perf)} player performances into SQLite history.")

        conn.commit()
        conn.close()

        # 3. Update Unified Multi-Season Parquet
        hist_dir = get_history_dir(repo_root)
        parquet_picks_path = hist_dir / "fact_manager_picks_all_seasons.parquet"
        if manager_picks and parquet_picks_path.exists():
            try:
                df_existing = pd.read_parquet(parquet_picks_path)
                df_new = pd.DataFrame(sqlite_picks)
                # Filter out old entries for this (season_id, gameweek_id) to avoid duplicates
                mask = (df_existing["season_id"] == season_id) & (df_existing["gameweek_id"] == gameweek_id)
                df_combined = pd.concat([df_existing[~mask], df_new], ignore_index=True)
                df_combined.to_parquet(parquet_picks_path, compression="snappy", index=False)
            except Exception as pe:
                logger.warning(f"Failed to update parquet picks file: {pe}")

        return True

    except Exception as e:
        logger.error(f"Error dual-writing to local history database: {e}")
        return False
