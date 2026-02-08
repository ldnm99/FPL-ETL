"""
Main entry point for FPL ETL Pipeline with Medallion Architecture.

This pipeline extracts FPL data and processes it through three layers:
- Bronze: Raw data from API (JSON)
- Silver: Cleaned and validated data (CSV/Parquet)
- Gold: Analytics-ready aggregated data (Parquet)
"""
import os
import logging
import sys

# Add parent directory to path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

from src.config import config
from src.etl import bronze, silver, gold, upload_database

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def download_silver_gameweeks_from_supabase():
    """
    Download all existing Silver gameweek parquet files from Supabase.
    This ensures we have complete historical data when running in incremental mode.
    """
    try:
        from supabase import create_client
        import io
        
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        bucket = config.SUPABASE_BUCKET
        
        # List all files in silver/gameweeks_parquet/ prefix
        result = supabase.storage.from_(bucket).list('silver/gameweeks_parquet')
        
        if not result:
            logging.warning("⚠️ No existing Silver gameweeks found in Supabase")
            return
        
        downloaded = 0
        for file_obj in result:
            filename = file_obj['name']
            if filename.endswith('.parquet'):
                remote_path = f"silver/gameweeks_parquet/{filename}"
                local_path = os.path.join(config.SILVER_GAMEWEEKS_DIR, filename)
                
                # Skip if we just created this file locally
                if os.path.exists(local_path):
                    continue
                
                # Download from Supabase
                data = supabase.storage.from_(bucket).download(remote_path)
                
                # Save locally
                with open(local_path, 'wb') as f:
                    f.write(data)
                
                downloaded += 1
        
        logging.info(f"✅ Downloaded {downloaded} existing gameweek files from Supabase")
        
    except Exception as e:
        logging.warning(f"⚠️ Could not download existing Silver gameweeks: {e}")
        logging.warning("   Continuing with local data only...")


def run_bronze_layer():
    """Execute Bronze layer extraction (raw data from API)."""
    logging.info("=" * 60)
    logging.info("🥉 BRONZE LAYER: Extracting raw data from FPL API")
    logging.info("=" * 60)
    
    # Extract league data
    logging.info("📊 Fetching league standings...")
    bronze.extract_league_raw()
    
    # Extract player data
    logging.info("🧍 Fetching player data...")
    bronze.extract_players_raw()
    
    # Extract fixtures data
    logging.info("📅 Fetching fixtures data...")
    bronze.extract_fixtures_raw()
    
    # Use bronze module's logic which respects INCREMENTAL_MODE
    bronze.main()
    
    logging.info("✅ Bronze layer extraction complete!\n")


def run_silver_layer():
    """Execute Silver layer transformation (cleaned data)."""
    logging.info("=" * 60)
    logging.info("🥈 SILVER LAYER: Transforming to cleaned data")
    logging.info("=" * 60)
    
    # Transform league standings
    logging.info("🔄 Transforming league standings...")
    silver.transform_league_standings()
    
    # Transform player data
    logging.info("🔄 Transforming player data...")
    silver.transform_players_data()
    
    # Transform fixtures data
    logging.info("🔄 Transforming fixtures data...")
    silver.transform_fixtures()
    
    # Get current gameweek
    current_gw = bronze.get_current_gameweek()
    
    # Load manager IDs
    import json
    with open(config.BRONZE_LEAGUE_RAW, 'r') as f:
        league_data = json.load(f)
    manager_ids = [entry['entry_id'] for entry in league_data.get('league_entries', [])]
    
    # Transform gameweeks based on mode
    if config.INCREMENTAL_MODE:
        start_gw = max(1, current_gw - config.INCREMENTAL_GAMEWEEKS + 1)
        logging.info(f"🔄 Transforming gameweeks {start_gw} to {current_gw} (incremental mode)...")
    else:
        start_gw = 1
        logging.info(f"🔄 Transforming ALL gameweek data (GW1 to GW{current_gw})...")
    
    for gw in range(start_gw, current_gw + 1):
        logging.info(f"  Transforming GW{gw}...")
        silver.transform_gameweek_data(gw, manager_ids)
    
    logging.info("✅ Silver layer transformation complete!\n")


def run_gold_layer():
    """Execute Gold layer aggregation (analytics-ready data)."""
    logging.info("=" * 60)
    logging.info("🥇 GOLD LAYER: Creating analytics-ready datasets")
    logging.info("=" * 60)
    
    # Create full gameweek dataset
    logging.info("📊 Creating full gameweek dataset...")
    gold.create_full_gameweek_dataset()
    
    # Create player season statistics
    logging.info("📊 Creating player season statistics...")
    gold.create_player_season_stats()
    
    # Create manager performance metrics
    logging.info("📊 Creating manager performance metrics...")
    gold.create_manager_performance()
    
    # Create dimensional model (dimensions + facts)
    logging.info("📊 Creating dimensional model (star schema)...")
    from src.etl import gold_dimensions, gold_facts
    gold_dimensions.create_all_dimensions()
    gold_facts.create_all_facts()
    
    logging.info("✅ Gold layer aggregation complete!\n")


def run_upload():
    """Upload all layers to Supabase."""
    logging.info("=" * 60)
    logging.info("⬆️  UPLOAD: Uploading to Supabase Storage")
    logging.info("=" * 60)
    
    # Upload ALL gameweeks to ensure complete dataset in Supabase
    # This is critical for GitHub Actions which runs in fresh environments
    upload_database.main(recent_gws_only=False)
    
    logging.info("✅ Upload complete!\n")


def run_pipeline():
    """Run the complete medallion ETL pipeline."""
    logging.info("\n")
    logging.info("🏆" * 30)
    logging.info("🚀 FPL ETL PIPELINE - MEDALLION ARCHITECTURE")
    logging.info("🏆" * 30)
    logging.info(f"📂 Data Directory: {config.DATA_DIR}")
    logging.info(f"🏟️  League ID: {config.LEAGUE_ID}")
    logging.info("\n")
    
    try:
        # Bronze Layer: Extract raw data
        run_bronze_layer()
        
        # Silver Layer: Transform to cleaned data
        run_silver_layer()
        
        # Gold Layer: Create analytics datasets
        run_gold_layer()
        
        # Upload to Supabase
        run_upload()
        
        logging.info("=" * 60)
        logging.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        logging.info("=" * 60)
        logging.info("📊 Data available in three layers:")
        logging.info(f"   🥉 Bronze: {config.BRONZE_DIR} (raw JSON)")
        logging.info(f"   🥈 Silver: {config.SILVER_DIR} (cleaned CSV/Parquet)")
        logging.info(f"   🥇 Gold:   {config.GOLD_DIR} (analytics Parquet)")
        logging.info("=" * 60)
        
    except Exception as e:
        logging.error("\n")
        logging.error("=" * 60)
        logging.error("❌ PIPELINE FAILED!")
        logging.error("=" * 60)
        logging.error(f"Error: {e}")
        logging.error("=" * 60)
        raise


if __name__ == "__main__":
    run_pipeline()
