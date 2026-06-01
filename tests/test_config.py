"""Tests for Config class."""
import pytest
from unittest.mock import patch


class TestConfigValidate:
    def test_raises_when_supabase_url_missing(self):
        from src.config import Config
        cfg = Config.__new__(Config)
        cfg.SUPABASE_URL = ""
        cfg.SUPABASE_KEY = "some-key"
        with pytest.raises(EnvironmentError, match="SUPABASE_URL"):
            cfg.validate()

    def test_raises_when_supabase_key_missing(self):
        from src.config import Config
        cfg = Config.__new__(Config)
        cfg.SUPABASE_URL = "https://example.supabase.co"
        cfg.SUPABASE_KEY = ""
        with pytest.raises(EnvironmentError, match="SUPABASE_SERVICE_KEY"):
            cfg.validate()

    def test_passes_when_both_set(self):
        from src.config import Config
        cfg = Config.__new__(Config)
        cfg.SUPABASE_URL = "https://example.supabase.co"
        cfg.SUPABASE_KEY = "some-key"
        cfg.validate()  # Should not raise


class TestConfigPaths:
    def test_bronze_gameweek_path(self):
        from src.config import config
        path = config.get_bronze_gameweek_path(5)
        assert path.endswith("gw_5_raw.json")
        assert "gameweeks" in path

    def test_silver_gameweek_path(self):
        from src.config import config
        path = config.get_silver_gameweek_path(12)
        assert path.endswith("gw_data_gw12.parquet")

    def test_supabase_path(self):
        from src.config import config
        path = config.get_supabase_path("bronze", "test.json")
        assert path == "bronze/test.json"

    def test_incremental_mode_comment_matches_behavior(self):
        """INCREMENTAL_MODE=False should mean full load, not incremental."""
        from src.config import Config
        cfg = Config()
        # Default is False = full load
        assert cfg.INCREMENTAL_MODE is False
