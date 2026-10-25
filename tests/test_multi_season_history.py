"""
Tests for Multi-Season Historical Database, 8 Canonical Manager Identities,
and Dual-Feed Local History Sync.
"""

import sqlite3
import pytest
from pathlib import Path
from src.etl.sync.history_feed import feed_local_history, get_db_path, get_history_dir

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_sqlite_db_exists():
    """Verify that the unified multi-season SQLite database exists."""
    db_path = get_db_path(REPO_ROOT)
    assert db_path.exists(), f"SQLite database not found at {db_path}"
    assert db_path.stat().st_size > 0, "SQLite database is empty"


def test_seasons_metadata():
    """Verify all 3 seasons exist with correct IDs, league IDs, and metadata."""
    db_path = get_db_path(REPO_ROOT)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id, league_id, name, champion_name, is_current FROM dim_seasons ORDER BY id")
    seasons = cur.fetchall()
    conn.close()

    assert len(seasons) == 3, f"Expected 3 seasons, got {len(seasons)}"
    season_dict = {s[0]: s for s in seasons}

    # 2024/2025
    assert "2024_2025" in season_dict
    assert season_dict["2024_2025"][1] == 70113
    assert season_dict["2024_2025"][3] == "Clev Clevinson Rodriguez"
    assert season_dict["2024_2025"][4] == 0

    # 2025/2026
    assert "2025_2026" in season_dict
    assert season_dict["2025_2026"][1] == 24636
    assert season_dict["2025_2026"][3] == "Lourenço Marvão"
    assert season_dict["2025_2026"][4] == 0

    # 2026/2027
    assert "2026_2027" in season_dict
    assert season_dict["2026_2027"][1] == 38279
    assert season_dict["2026_2027"][4] == 1


def test_eight_canonical_managers():
    """Verify the 8 canonical manager identities and specifically Luis Costa != João Pedro."""
    db_path = get_db_path(REPO_ROOT)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT canonical_id, manager_name, is_active_current_season FROM dim_manager_identity")
    managers = cur.fetchall()
    conn.close()

    assert len(managers) == 8, f"Expected exactly 8 canonical managers, found {len(managers)}"
    mgr_map = {m[0]: m[1] for m in managers}

    # Verify key managers
    assert 199289 in mgr_map  # Lourenço Marvão
    assert 204604 in mgr_map  # Clev Clevinson Rodriguez
    assert 202383 in mgr_map  # Tiago Duarte
    assert 210387 in mgr_map  # Diogo Santana
    assert 346616 in mgr_map  # Bernardo Moura
    assert 244074 in mgr_map  # Vasco Carvalho
    assert 144396 in mgr_map  # Luis Costa (25/26 only)
    assert 210890 in mgr_map  # João Pedro / Gordinho Chill (26/27 only)

    # Validate separation
    assert mgr_map[144396] == "Luis Costa"
    assert "João Pedro" in mgr_map[210890]


def test_manager_seasons_participation():
    """Verify historical participation across seasons."""
    db_path = get_db_path(REPO_ROOT)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 2024/2025: exactly 5 managers
    cur.execute("SELECT canonical_id FROM dim_manager_seasons WHERE season_id = '2024_2025'")
    m24 = [row[0] for row in cur.fetchall()]
    assert len(m24) == 5
    assert 144396 not in m24  # Luis Costa was not in 24/25
    assert 210890 not in m24  # João Pedro was not in 24/25

    # 2025/2026: exactly 7 managers, including Luis Costa
    cur.execute("SELECT canonical_id FROM dim_manager_seasons WHERE season_id = '2025_2026'")
    m25 = [row[0] for row in cur.fetchall()]
    assert len(m25) == 7
    assert 144396 in m25  # Luis Costa was in 25/26
    assert 210890 not in m25  # João Pedro was not in 25/26

    # 2026/2027: exactly 7 managers, including João Pedro
    cur.execute("SELECT canonical_id FROM dim_manager_seasons WHERE season_id = '2026_2027'")
    m26 = [row[0] for row in cur.fetchall()]
    assert len(m26) == 7
    assert 210890 in m26  # João Pedro in 26/27
    assert 144396 not in m26  # Luis Costa not in 26/27

    conn.close()


def test_fact_manager_picks_records():
    """Verify that manager picks are recorded across past seasons."""
    db_path = get_db_path(REPO_ROOT)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT season_id, COUNT(*) FROM fact_manager_picks GROUP BY season_id")
    picks_per_season = dict(cur.fetchall())
    conn.close()

    assert "2024_2025" in picks_per_season and picks_per_season["2024_2025"] > 0
    assert "2025_2026" in picks_per_season and picks_per_season["2025_2026"] > 0


def test_fact_player_performance_records():
    """Verify player performances exist for historical seasons."""
    db_path = get_db_path(REPO_ROOT)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT season_id, COUNT(*) FROM fact_player_performance GROUP BY season_id")
    perf_per_season = dict(cur.fetchall())
    conn.close()

    assert "2025_2026" in perf_per_season and perf_per_season["2025_2026"] > 10000


def test_gold_parquet_history_files():
    """Verify unified multi-season parquet files exist in Data/history/."""
    hist_dir = get_history_dir(REPO_ROOT)
    assert (hist_dir / "fact_manager_picks_all_seasons.parquet").exists()
    assert (hist_dir / "fact_player_performance_all_seasons.parquet").exists()
    assert (hist_dir / "fact_manager_picks_all_seasons.parquet").stat().st_size > 0
    assert (hist_dir / "fact_player_performance_all_seasons.parquet").stat().st_size > 0


def test_dual_feed_local_history():
    """Verify feed_local_history executes cleanly without breaking."""
    sample_picks = [{
        "manager_id": 199289,
        "player_id": 99999,
        "position": 1,
        "is_captain": False,
        "multiplier": 1
    }]
    sample_perf = [{
        "player_id": 99999,
        "total_points": 12,
        "minutes": 90,
        "goals_scored": 1,
        "assists": 1,
        "clean_sheets": 0,
        "defensive_contribution": 2,
        "bps": 34,
        "bonus": 3
    }]

    success = feed_local_history(
        repo_root=REPO_ROOT,
        season_id="2026_2027",
        gameweek_id=99,
        manager_picks=sample_picks,
        player_performance=sample_perf
    )
    assert success is True

    # Check cleanup
    db_path = get_db_path(REPO_ROOT)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM fact_manager_picks WHERE gameweek_id = 99")
    cur.execute("DELETE FROM fact_player_performance WHERE gameweek_id = 99")
    conn.commit()
    conn.close()
