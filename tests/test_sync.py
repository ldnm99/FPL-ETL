"""
Unit Tests for Modular FPL Sync Engine and Pydantic Ingestion Contracts.
"""
import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock
from src.etl.schemas import (
    ClubIngest,
    PlayerIngest,
    GameweekIngest,
    FixtureIngest,
    ManagerIngest,
    ManagerPickIngest,
    PlayerPerformanceIngest,
    PipelineRunAudit
)
from src.etl.sync.audit import record_pipeline_audit, _init_sqlite_db
from src.etl.sync.fixtures import is_fixture_window_active


class TestPydanticIngestionSchemas:
    """Test Pydantic v2 schemas enforce type validation and default values."""

    def test_club_ingest_valid(self):
        club = ClubIngest(id=1, name="Arsenal", short_name="ARS", code=3)
        assert club.id == 1
        assert club.name == "Arsenal"
        assert club.short_name == "ARS"
        assert club.code == 3

    def test_player_ingest_defaults(self):
        player = PlayerIngest(
            id=101,
            web_name="Saka",
            team=1,
            element_type=3,
            now_cost=100
        )
        assert player.id == 101
        assert player.web_name == "Saka"
        assert player.club_id == 1  # Aliased from 'team'
        assert player.position_name == "MID"
        assert player.element_type == 3

    def test_fixture_ingest_alias_and_flags(self):
        fixture = FixtureIngest(
            id=1,
            event=5,
            team_h=1,
            team_a=2,
            team_h_difficulty=4,
            started=True,
            finished=False
        )
        assert fixture.id == 1
        assert fixture.gameweek_id == 5  # Aliased from 'event'
        assert fixture.fdr_h == 4  # Aliased from 'team_h_difficulty'
        assert fixture.started is True
        assert fixture.finished is False

    def test_manager_pick_ingest(self):
        pick = ManagerPickIngest(
            manager_id=10,
            gameweek_id=8,
            player_id=250,
            position=1
        )
        assert pick.manager_id == 10
        assert pick.gameweek_id == 8
        assert pick.player_id == 250
        assert pick.position == 1

    def test_player_performance_ingest_defcons(self):
        perf = PlayerPerformanceIngest(
            player_id=55,
            gameweek_id=8,
            total_points=8,
            goals_scored=1,
            assists=0,
            defcons=14,
            bonus=2
        )
        assert perf.player_id == 55
        assert perf.total_points == 8
        assert perf.goals_scored == 1
        assert perf.defcons == 14
        assert perf.bonus == 2


class TestAuditLedger:
    """Test Dual-Ledger Run History Logging."""

    def test_sqlite_audit_logging(self, tmp_path):
        db_file = tmp_path / "test_etl_history.sqlite"
        audit = PipelineRunAudit(
            run_timestamp="2026-10-25T02:00:00Z",
            mode="fast_live_sync",
            gameweek_id=8,
            status="ok",
            duration_ms=1250,
            fixtures_count=10,
            managers_count=8,
            picks_count=120,
            perf_records_count=450
        )

        mock_supabase = MagicMock()
        success = record_pipeline_audit(mock_supabase, audit, sqlite_path=db_file)
        assert success is True

        # Verify record exists in SQLite
        with sqlite3.connect(db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT mode, gameweek_id, status, duration_ms FROM pipeline_run_history;")
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "fast_live_sync"
            assert row[1] == 8
            assert row[2] == "ok"
            assert row[3] == 1250


class TestFixtureWindowDetection:
    """Test active match detection and early exit logic."""

    def test_active_match_returns_true(self):
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.execute.return_value.data = [
            {"id": 1, "started": True, "finished": False, "finished_provisional": False}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

        assert is_fixture_window_active(mock_supabase, current_gw=8) is True

    def test_provisional_bps_settlement_returns_true(self):
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.execute.return_value.data = [
            {"id": 1, "started": True, "finished": False, "finished_provisional": True}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

        assert is_fixture_window_active(mock_supabase, current_gw=8) is True

    def test_all_finished_returns_false(self):
        mock_supabase = MagicMock()
        mock_query = MagicMock()
        mock_query.execute.return_value.data = [
            {"id": 1, "started": True, "finished": True, "finished_provisional": True}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value = mock_query

        assert is_fixture_window_active(mock_supabase, current_gw=8) is False


class TestPostGameweekSettlementAndReconciliation:
    """Test gameweek pointer accuracy, 2-GW lookback window, and official standings self-healing."""

    def test_bootstrap_respects_official_events_current(self, monkeypatch):
        from src.etl.sync import bootstrap

        # Simulate post-GW8 state where GW8 is finished=True, but official events.current is still 8
        mock_payload = {
            "teams": [{"id": 1, "name": "Arsenal", "short_name": "ARS", "code": 3}],
            "element_types": [{"id": 3, "singular_name_short": "MID"}],
            "elements": [
                {"id": 10, "web_name": "Saka", "team": 1, "element_type": 3, "code": 223340, "draft_rank": 5}
            ],
            "events": {
                "current": 8,
                "next": 9,
                "data": [
                    {"id": 8, "name": "Gameweek 8", "finished": True, "deadline_time": "2026-10-23T17:30:00Z"},
                    {"id": 9, "name": "Gameweek 9", "finished": False, "deadline_time": "2026-10-31T11:00:00Z"},
                ],
            },
        }
        monkeypatch.setattr(bootstrap, "fetch_json", lambda endpoint: mock_payload)

        mock_supabase = MagicMock()
        detected_gw = bootstrap.sync_bootstrap_data(mock_supabase)
        assert detected_gw == 8

    def test_reconcile_standings_detects_drift_and_heals(self, monkeypatch):
        from src.etl.sync import performance

        # Official API says Manager 199289 has 385 total (0 in current GW9 -> 385 in closed GWs 1..8)
        league_entries = [
            {"id": 199289, "entry_id": 199289, "api_total": 385, "api_event_total": 0},
            {"id": 346616, "entry_id": 346616, "api_total": 383, "api_event_total": 0},
        ]

        # Supabase currently only has 382 for Manager 199289 (missed +3 auto-sub in GW8)
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.lt.return_value.execute.return_value.data = [
            {"manager_id": 199289, "gameweek_id": 8, "points": 382, "is_starter": True},
            {"manager_id": 346616, "gameweek_id": 8, "points": 383, "is_starter": True},
        ]

        heal_called = {}

        def fake_sync(sb, entries, current_gw, sync_all_history=False, **kwargs):
            heal_called["current_gw"] = current_gw
            heal_called["sync_all_history"] = sync_all_history
            return {"picks_count": 105, "perf_records_count": 669}

        monkeypatch.setattr(performance, "sync_manager_picks_and_performance", fake_sync)

        res = performance.reconcile_standings_with_official(mock_supabase, league_entries, current_gw=9)
        assert res["healed"] is True
        assert len(res["drifted_managers"]) == 1
        assert res["drifted_managers"][0]["manager_id"] == 199289
        assert res["drifted_managers"][0]["delta"] == 3
        assert heal_called == {"current_gw": 8, "sync_all_history": True}
