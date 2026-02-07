import pandas as pd
import io
import os
import json
import logging
from supabase import create_client, Client
from datetime import datetime, timezone
from typing import Union
from src.config import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --------------------------
# Supabase Client Setup (Lazy Initialization)
# --------------------------
_supabase_client = None

def get_supabase_client() -> Client:
    """Get or create Supabase client. Only initializes when actually needed."""
    global _supabase_client
    
    if _supabase_client is None:
        SUPABASE_URL = config.SUPABASE_URL
        SUPABASE_KEY = config.SUPABASE_KEY
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            logging.error("❌ Missing required environment variables")
            logging.error("   Please set SUPABASE_URL and SUPABASE_SERVICE_KEY")
            logging.error("   Example: export SUPABASE_URL='https://your-project.supabase.co'")
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
        
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logging.info("✅ Supabase client initialized")
    
    return _supabase_client


# --------------------------
# Upload Helpers
# --------------------------
def upload_json(file_path: str, supabase_path: str, bucket: str = "data") -> Union[dict, None]:
    """Upload JSON file to Supabase Storage."""
    try:
        supabase = get_supabase_client()
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()

        res = supabase.storage.from_(bucket).upload(
            path=supabase_path,
            file=data.encode("utf-8"),
            file_options={"content-type": "application/json", "upsert": "true"}
        )

        logging.info(f"✅ Uploaded JSON: {supabase_path}")
        return res
    except Exception as e:
        logging.error(f"❌ Error uploading JSON {file_path}: {e}")
        return None


def upload_csv(file_path: str, supabase_path: str, bucket: str = "data") -> Union[dict, None]:
    """Upload CSV file to Supabase Storage."""
    try:
        supabase = get_supabase_client()
        df = pd.read_csv(file_path)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)

        res = supabase.storage.from_(bucket).upload(
            path=supabase_path,
            file=buffer.getvalue().encode("utf-8"),
            file_options={"content-type": "text/csv", "upsert": "true"}
        )

        logging.info(f"✅ Uploaded CSV: {supabase_path}")
        return res
    except Exception as e:
        logging.error(f"❌ Error uploading CSV {file_path}: {e}")
        return None


def upload_parquet(file_path: str, supabase_path: str, bucket: str = "data") -> Union[dict, None]:
    """Upload Parquet file to Supabase Storage."""
    try:
        supabase = get_supabase_client()
        df = pd.read_parquet(file_path)
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)

        res = supabase.storage.from_(bucket).upload(
            path=supabase_path,
            file=buffer.read(),
            file_options={"content-type": "application/octet-stream", "upsert": "true"}
        )

        logging.info(f"✅ Uploaded Parquet: {supabase_path}")
        return res
    except Exception as e:
        logging.error(f"❌ Error uploading Parquet {file_path}: {e}")
        return None


# --------------------------
# Layer-specific upload functions
# --------------------------
def upload_bronze_layer(recent_gws_only: bool = True, num_gws: int = 2):
    """
    Upload Bronze layer (raw JSON files) to Supabase.
    
    Args:
        recent_gws_only: If True, only upload last N gameweeks
        num_gws: Number of recent gameweeks to upload (default: 2)
    """
    logging.info("🥉 Uploading Bronze layer...")
    
    bucket = config.SUPABASE_BUCKET
    
    # Always upload these core files
    if os.path.exists(config.BRONZE_LEAGUE_RAW):
        upload_json(
            config.BRONZE_LEAGUE_RAW,
            config.get_supabase_path('bronze', 'league_standings_raw.json'),
            bucket
        )
    
    if os.path.exists(config.BRONZE_PLAYERS_RAW):
        upload_json(
            config.BRONZE_PLAYERS_RAW,
            config.get_supabase_path('bronze', 'players_raw.json'),
            bucket
        )
    
    fixtures_raw = os.path.join(config.BRONZE_DIR, 'fixtures_raw.json')
    if os.path.exists(fixtures_raw):
        upload_json(
            fixtures_raw,
            config.get_supabase_path('bronze', 'fixtures_raw.json'),
            bucket
        )
    
    # Determine which gameweeks to upload
    if recent_gws_only:
        from src.etl.bronze import get_current_gameweek
        current_gw = get_current_gameweek()
        start_gw = max(1, current_gw - num_gws + 1)
        logging.info(f"📅 Uploading gameweeks {start_gw} to {current_gw} (last {num_gws} GWs)")
    else:
        start_gw = 1
        current_gw = 38
        logging.info("📅 Uploading ALL gameweeks (full sync)")
    
    # Upload gameweek raw data (only recent GWs)
    if os.path.exists(config.BRONZE_GAMEWEEKS_DIR):
        uploaded_count = 0
        for filename in os.listdir(config.BRONZE_GAMEWEEKS_DIR):
            if filename.endswith('.json'):
                # Extract GW number from filename: gw_25_raw.json -> 25
                try:
                    gw_num = int(filename.split('_')[1])
                    if gw_num >= start_gw and gw_num <= current_gw:
                        file_path = os.path.join(config.BRONZE_GAMEWEEKS_DIR, filename)
                        upload_json(
                            file_path,
                            config.get_supabase_path('bronze', f'gameweeks/{filename}'),
                            bucket
                        )
                        uploaded_count += 1
                except (IndexError, ValueError):
                    # Skip files that don't match expected pattern
                    continue
        logging.info(f"📤 Uploaded {uploaded_count} gameweek files")
    
    # Upload manager picks raw data (only recent GWs)
    if os.path.exists(config.BRONZE_PICKS_DIR):
        uploaded_count = 0
        for filename in os.listdir(config.BRONZE_PICKS_DIR):
            if filename.endswith('.json'):
                # Extract GW number from filename
                try:
                    # Filename format: manager_XXXXX_gw_25.json
                    parts = filename.split('_gw_')
                    if len(parts) == 2:
                        gw_num = int(parts[1].replace('.json', ''))
                        if gw_num >= start_gw and gw_num <= current_gw:
                            file_path = os.path.join(config.BRONZE_PICKS_DIR, filename)
                            upload_json(
                                file_path,
                                config.get_supabase_path('bronze', f'manager_picks/{filename}'),
                                bucket
                            )
                            uploaded_count += 1
                except (IndexError, ValueError):
                    continue
        logging.info(f"📤 Uploaded {uploaded_count} manager pick files")
    
    logging.info("✅ Bronze layer upload complete")


def upload_silver_layer(recent_gws_only: bool = True, num_gws: int = 2):
    """
    Upload Silver layer (cleaned CSV/Parquet files) to Supabase.
    
    Args:
        recent_gws_only: If True, only upload last N gameweeks
        num_gws: Number of recent gameweeks to upload (default: 2)
    """
    logging.info("🥈 Uploading Silver layer...")
    
    bucket = config.SUPABASE_BUCKET
    
    # Always upload these core files
    if os.path.exists(config.SILVER_LEAGUE_CSV):
        upload_csv(
            config.SILVER_LEAGUE_CSV,
            config.get_supabase_path('silver', 'league_standings.csv'),
            bucket
        )
    
    if os.path.exists(config.SILVER_PLAYERS_CSV):
        upload_csv(
            config.SILVER_PLAYERS_CSV,
            config.get_supabase_path('silver', 'players_data.csv'),
            bucket
        )
    
    fixtures_parquet = os.path.join(config.SILVER_DIR, 'fixtures.parquet')
    if os.path.exists(fixtures_parquet):
        upload_parquet(
            fixtures_parquet,
            config.get_supabase_path('silver', 'fixtures.parquet'),
            bucket
        )
    
    # Determine which gameweeks to upload
    if recent_gws_only:
        from src.etl.bronze import get_current_gameweek
        current_gw = get_current_gameweek()
        start_gw = max(1, current_gw - num_gws + 1)
        logging.info(f"📅 Uploading gameweeks {start_gw} to {current_gw} (last {num_gws} GWs)")
    else:
        start_gw = 1
        current_gw = 38
        logging.info("📅 Uploading ALL gameweeks (full sync)")
    
    # Upload gameweek parquet files (only recent GWs)
    if os.path.exists(config.SILVER_GAMEWEEKS_DIR):
        uploaded_count = 0
        for filename in os.listdir(config.SILVER_GAMEWEEKS_DIR):
            if filename.endswith('.parquet'):
                # Extract GW number from filename: gw_data_gw25.parquet -> 25
                try:
                    gw_num = int(filename.replace('gw_data_gw', '').replace('.parquet', ''))
                    if gw_num >= start_gw and gw_num <= current_gw:
                        file_path = os.path.join(config.SILVER_GAMEWEEKS_DIR, filename)
                        upload_parquet(
                            file_path,
                            config.get_supabase_path('silver', f'gameweeks_parquet/{filename}'),
                            bucket
                        )
                        uploaded_count += 1
                except ValueError:
                    continue
        logging.info(f"📤 Uploaded {uploaded_count} gameweek parquet files")
    
    logging.info("✅ Silver layer upload complete")


def upload_gold_layer():
    """
    Upload Gold layer (aggregated Parquet files) to Supabase.
    Gold layer files always contain complete historical data with incremental updates,
    so we always upload all Gold files.
    """
    logging.info("🥇 Uploading Gold layer...")
    
    bucket = config.SUPABASE_BUCKET
    
    # Upload full gameweek dataset
    if os.path.exists(config.GOLD_GW_DATA_FULL):
        upload_parquet(
            config.GOLD_GW_DATA_FULL,
            config.get_supabase_path('gold', 'gw_data_full.parquet'),
            bucket
        )
    
    # Upload player season stats
    if os.path.exists(config.GOLD_PLAYER_SEASON_STATS):
        upload_parquet(
            config.GOLD_PLAYER_SEASON_STATS,
            config.get_supabase_path('gold', 'player_season_stats.parquet'),
            bucket
        )
    
    # Upload manager performance
    if os.path.exists(config.GOLD_MANAGER_PERFORMANCE):
        upload_parquet(
            config.GOLD_MANAGER_PERFORMANCE,
            config.get_supabase_path('gold', 'manager_performance.parquet'),
            bucket
        )
    
    # Upload all dimension tables
    dimensions_dir = os.path.join(config.GOLD_DIR, 'dimensions')
    if os.path.exists(dimensions_dir):
        uploaded_count = 0
        for filename in os.listdir(dimensions_dir):
            if filename.endswith('.parquet'):
                file_path = os.path.join(dimensions_dir, filename)
                upload_parquet(
                    file_path,
                    config.get_supabase_path('gold', f'dimensions/{filename}'),
                    bucket
                )
                uploaded_count += 1
        logging.info(f"📤 Uploaded {uploaded_count} dimension tables")
    
    # Upload all fact tables
    facts_dir = os.path.join(config.GOLD_DIR, 'facts')
    if os.path.exists(facts_dir):
        uploaded_count = 0
        for filename in os.listdir(facts_dir):
            if filename.endswith('.parquet'):
                file_path = os.path.join(facts_dir, filename)
                upload_parquet(
                    file_path,
                    config.get_supabase_path('gold', f'facts/{filename}'),
                    bucket
                )
                uploaded_count += 1
        logging.info(f"📤 Uploaded {uploaded_count} fact tables")
    
    logging.info("✅ Gold layer upload complete")


def update_timestamp(layer: str = "all"):
    """Update last_updated timestamp file."""
    supabase = get_supabase_client()
    timestamp_content = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "layer": layer
    }
    
    timestamp_file = os.path.join(config.DATA_DIR, "last_updated.json")
    with open(timestamp_file, "w") as f:
        json.dump(timestamp_content, f, indent=2)
    
    # Upload timestamp to Supabase
    supabase.storage.from_(config.SUPABASE_BUCKET).upload(
        path="last_updated.json",
        file=json.dumps(timestamp_content).encode("utf-8"),
        file_options={"content-type": "application/json", "upsert": "true"}
    )
    
    logging.info(f"📁 Timestamp updated: {timestamp_content['last_updated']}")


# --------------------------
# Main function for external calls
# --------------------------
def main(recent_gws_only: bool = True, num_gws: int = 2):
    """
    Upload all medallion layers to Supabase.
    
    Args:
        recent_gws_only: If True, only upload last N gameweeks for Bronze/Silver (default: True)
        num_gws: Number of recent gameweeks to upload (default: 2)
    """
    logging.info("⬆️  Starting medallion layer uploads...")
    
    if recent_gws_only:
        logging.info(f"📅 Bronze/Silver: Only uploading last {num_gws} gameweeks")
        logging.info(f"📅 Gold: Uploading ALL files (contains complete historical data)")
    else:
        logging.info("📅 Uploading ALL files (full sync)")
    
    # Upload each layer
    upload_bronze_layer(recent_gws_only=recent_gws_only, num_gws=num_gws)
    upload_silver_layer(recent_gws_only=recent_gws_only, num_gws=num_gws)
    upload_gold_layer()  # Always upload all Gold files
    
    # Update timestamp
    update_timestamp(layer="all")
    
    logging.info("🎉 All medallion layer uploads complete!")


# --------------------------
# Allow standalone execution
# --------------------------
if __name__ == "__main__":
    main()
