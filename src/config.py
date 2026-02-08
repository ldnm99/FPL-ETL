"""
Configuration module for FPL ETL pipeline with medallion architecture.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Pipeline configuration with medallion architecture support."""
    
    # Base directories
    DATA_DIR: str = "Data"
    
    # Pipeline mode
    INCREMENTAL_MODE: bool = False  # Always fetch and process all gameweeks
    INCREMENTAL_GAMEWEEKS: int = 2  # Not used when INCREMENTAL_MODE=False
    
    # Medallion Layer Directories
    BRONZE_DIR: Optional[str] = None
    SILVER_DIR: Optional[str] = None
    GOLD_DIR: Optional[str] = None
    
    # Bronze Layer - Raw JSON files
    BRONZE_LEAGUE_RAW: Optional[str] = None
    BRONZE_PLAYERS_RAW: Optional[str] = None
    BRONZE_GAMEWEEKS_DIR: Optional[str] = None
    BRONZE_PICKS_DIR: Optional[str] = None
    
    # Silver Layer - Cleaned CSV/Parquet files
    SILVER_LEAGUE_CSV: Optional[str] = None
    SILVER_PLAYERS_CSV: Optional[str] = None
    SILVER_GAMEWEEKS_DIR: Optional[str] = None
    SILVER_METADATA_DIR: Optional[str] = None
    
    # Gold Layer - Analytics-ready aggregated data
    GOLD_GW_DATA_FULL: Optional[str] = None
    GOLD_PLAYER_SEASON_STATS: Optional[str] = None
    GOLD_MANAGER_PERFORMANCE: Optional[str] = None
    
    # API Configuration
    LEAGUE_ID: str = os.getenv("FPL_LEAGUE_ID", "24636")
    BASE_URL: str = "https://draft.premierleague.com/api"
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 2
    REQUEST_TIMEOUT: int = 10
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET: str = "data"
    
    # Supabase Paths (with layer prefixes)
    SUPABASE_BRONZE_PREFIX: str = "bronze"
    SUPABASE_SILVER_PREFIX: str = "silver"
    SUPABASE_GOLD_PREFIX: str = "gold"
    
    def __post_init__(self):
        """Initialize computed paths after instance creation."""
        # Medallion layer base directories
        self.BRONZE_DIR = os.path.join(self.DATA_DIR, "bronze")
        self.SILVER_DIR = os.path.join(self.DATA_DIR, "silver")
        self.GOLD_DIR = os.path.join(self.DATA_DIR, "gold")
        
        # Bronze layer paths
        self.BRONZE_LEAGUE_RAW = os.path.join(self.BRONZE_DIR, "league_standings_raw.json")
        self.BRONZE_PLAYERS_RAW = os.path.join(self.BRONZE_DIR, "players_raw.json")
        self.BRONZE_GAMEWEEKS_DIR = os.path.join(self.BRONZE_DIR, "gameweeks")
        self.BRONZE_PICKS_DIR = os.path.join(self.BRONZE_DIR, "manager_picks")
        
        # Silver layer paths
        self.SILVER_LEAGUE_CSV = os.path.join(self.SILVER_DIR, "league_standings.csv")
        self.SILVER_PLAYERS_CSV = os.path.join(self.SILVER_DIR, "players_data.csv")
        self.SILVER_GAMEWEEKS_DIR = os.path.join(self.SILVER_DIR, "gameweeks_parquet")
        self.SILVER_METADATA_DIR = os.path.join(self.SILVER_DIR, "metadata")
        
        # Gold layer paths
        self.GOLD_GW_DATA_FULL = os.path.join(self.GOLD_DIR, "gw_data_full.parquet")
        self.GOLD_PLAYER_SEASON_STATS = os.path.join(self.GOLD_DIR, "player_season_stats.parquet")
        self.GOLD_MANAGER_PERFORMANCE = os.path.join(self.GOLD_DIR, "manager_performance.parquet")
        
        # Create directories if they don't exist
        self._create_directories()
    
    def _create_directories(self):
        """Create all required directories for medallion architecture."""
        directories = [
            self.DATA_DIR,
            self.BRONZE_DIR,
            self.BRONZE_GAMEWEEKS_DIR,
            self.BRONZE_PICKS_DIR,
            self.SILVER_DIR,
            self.SILVER_GAMEWEEKS_DIR,
            self.SILVER_METADATA_DIR,
            self.GOLD_DIR,
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def get_bronze_gameweek_path(self, gameweek: int) -> str:
        """Get path for Bronze layer gameweek raw data."""
        return os.path.join(self.BRONZE_GAMEWEEKS_DIR, f"gw_{gameweek}_raw.json")
    
    def get_bronze_picks_path(self, gameweek: int, manager_id: int) -> str:
        """Get path for Bronze layer manager picks raw data."""
        return os.path.join(self.BRONZE_PICKS_DIR, f"gw_{gameweek}_manager_{manager_id}.json")
    
    def get_silver_gameweek_path(self, gameweek: int) -> str:
        """Get path for Silver layer gameweek parquet file."""
        return os.path.join(self.SILVER_GAMEWEEKS_DIR, f"gw_data_gw{gameweek}.parquet")
    
    def get_supabase_path(self, layer: str, filename: str) -> str:
        """
        Get Supabase storage path with layer prefix.
        
        Args:
            layer: One of 'bronze', 'silver', 'gold'
            filename: Name of the file
            
        Returns:
            Full path for Supabase upload (e.g., 'bronze/league_standings_raw.json')
        """
        layer_map = {
            'bronze': self.SUPABASE_BRONZE_PREFIX,
            'silver': self.SUPABASE_SILVER_PREFIX,
            'gold': self.SUPABASE_GOLD_PREFIX,
        }
        
        prefix = layer_map.get(layer, layer)
        return f"{prefix}/{filename}"


# Singleton instance
config = Config()
