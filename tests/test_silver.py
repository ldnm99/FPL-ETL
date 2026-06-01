"""Tests for the Silver layer transformation module."""
import json
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock


class TestLoadBronzeJson:
    def test_returns_dict_on_valid_file(self, tmp_path):
        data = {"key": "value"}
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data))

        from src.etl.silver import load_bronze_json
        result = load_bronze_json(str(f))
        assert result == data

    def test_returns_empty_dict_on_missing_file(self):
        from src.etl.silver import load_bronze_json
        result = load_bronze_json("/nonexistent/path.json")
        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not valid json {{{")
        from src.etl.silver import load_bronze_json
        result = load_bronze_json(str(f))
        assert result == {}


class TestTransformLeagueStandings:
    def test_transforms_valid_data(self, tmp_path):
        raw_data = {
            "league_entries": [
                {
                    "entry_id": 100,
                    "id": 1,
                    "player_first_name": "Alice",
                    "player_last_name": "Smith",
                    "short_name": "ALS",
                    "entry_name": "Alice FC",
                    "waiver_pick": 1
                }
            ]
        }
        league_raw = tmp_path / "league.json"
        league_raw.write_text(json.dumps(raw_data))
        league_csv = tmp_path / "league.csv"

        with patch("src.etl.silver.config") as mock_config:
            mock_config.BRONZE_LEAGUE_RAW = str(league_raw)
            mock_config.SILVER_LEAGUE_CSV = str(league_csv)
            from src.etl.silver import transform_league_standings
            df = transform_league_standings()

        assert not df.empty
        assert "manager_id" in df.columns
        assert "team_name" in df.columns
        assert df.iloc[0]["manager_id"] == 100
        assert df.iloc[0]["team_name"] == "Alice FC"

    def test_returns_empty_on_invalid_structure(self, tmp_path):
        raw_data = {"wrong_key": []}
        league_raw = tmp_path / "league.json"
        league_raw.write_text(json.dumps(raw_data))

        with patch("src.etl.silver.config") as mock_config:
            mock_config.BRONZE_LEAGUE_RAW = str(league_raw)
            from src.etl.silver import transform_league_standings
            df = transform_league_standings()

        assert df.empty
