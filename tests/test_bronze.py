"""Tests for the Bronze layer extraction module."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock


class TestGetCurrentGameweek:
    def test_returns_current_event(self):
        with patch("src.etl.bronze.fetch_data", return_value={"current_event": 30}):
            from src.etl.bronze import get_current_gameweek
            assert get_current_gameweek() == 30

    def test_falls_back_to_1_on_empty_response(self):
        with patch("src.etl.bronze.fetch_data", return_value=None):
            from src.etl.bronze import get_current_gameweek
            assert get_current_gameweek() == 1

    def test_falls_back_to_1_on_missing_key(self):
        with patch("src.etl.bronze.fetch_data", return_value={"other_key": 5}):
            from src.etl.bronze import get_current_gameweek
            assert get_current_gameweek() == 1


class TestLoadManagerIds:
    def test_parses_manager_ids(self, tmp_path):
        league_file = tmp_path / "league.json"
        league_data = {"league_entries": [{"entry_id": 1}, {"entry_id": 2}, {"entry_id": 3}]}
        league_file.write_text(json.dumps(league_data))

        with patch("src.etl.bronze.config") as mock_config:
            mock_config.BRONZE_LEAGUE_RAW = str(league_file)
            from src.etl.bronze import _load_manager_ids
            ids = _load_manager_ids()

        assert ids == [1, 2, 3]

    def test_returns_empty_list_when_no_entries(self, tmp_path):
        league_file = tmp_path / "league.json"
        league_file.write_text(json.dumps({}))

        with patch("src.etl.bronze.config") as mock_config:
            mock_config.BRONZE_LEAGUE_RAW = str(league_file)
            from src.etl.bronze import _load_manager_ids
            ids = _load_manager_ids()

        assert ids == []


class TestExtractLeagueRaw:
    def test_raises_on_empty_response(self):
        with patch("src.etl.bronze.fetch_data", return_value=None):
            from src.etl.bronze import extract_league_raw
            with pytest.raises(RuntimeError, match="Failed to fetch league data"):
                extract_league_raw()

    def test_saves_json_on_success(self, tmp_path):
        data = {"league_entries": [{"entry_id": 1}]}
        with patch("src.etl.bronze.fetch_data", return_value=data), \
             patch("src.etl.bronze.config") as mock_config:
            mock_config.BASE_URL = "https://example.com/api"
            mock_config.LEAGUE_ID = "12345"
            mock_config.BRONZE_LEAGUE_RAW = str(tmp_path / "league.json")
            from src.etl.bronze import extract_league_raw
            result = extract_league_raw()

        assert result == data
        assert os.path.exists(mock_config.BRONZE_LEAGUE_RAW)


class TestExtractFixturesRaw:
    def test_skips_if_file_exists(self, tmp_path):
        fixtures_path = tmp_path / "fixtures_raw.json"
        fixtures_path.write_text("[]")

        with patch("src.etl.bronze.config") as mock_config:
            mock_config.BRONZE_DIR = str(tmp_path)
            mock_config.BRONZE_PLAYERS_RAW = str(tmp_path / "players.json")
            from src.etl.bronze import extract_fixtures_raw
            result = extract_fixtures_raw(force=False)

        assert result == []

    def test_fetches_when_forced(self, tmp_path):
        fixtures_path = tmp_path / "fixtures_raw.json"
        fixtures_path.write_text("[]")
        players_data = {"fixtures": [{"id": 1}]}
        players_path = tmp_path / "players.json"
        players_path.write_text(json.dumps(players_data))

        with patch("src.etl.bronze.config") as mock_config:
            mock_config.BRONZE_DIR = str(tmp_path)
            mock_config.BRONZE_PLAYERS_RAW = str(players_path)
            from src.etl.bronze import extract_fixtures_raw
            result = extract_fixtures_raw(force=True)

        assert result == [{"id": 1}]
