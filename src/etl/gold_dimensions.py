"""
Gold Layer - Dimensional Model: Dimension Tables
Create dimension tables for star schema.
"""
import logging
import pandas as pd
from datetime import datetime
from src.config import config
from src.etl.silver import load_bronze_json

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def create_dim_managers() -> pd.DataFrame:
    """
    Create managers dimension table.
    SCD Type 0 - Static, doesn't change.
    
    Returns:
        DataFrame with manager dimension
    """
    logging.info("🔄 Creating dim_managers...")
    
    # Load from Silver
    df = pd.read_csv(config.SILVER_LEAGUE_CSV)
    
    # Create dimension table
    dim_managers = df[[
        'manager_id', 'first_name', 'last_name', 
        'team_name', 'waiver_pick'
    ]].copy()
    
    # Add metadata
    dim_managers['created_at'] = datetime.now()
    
    # Save to Gold dimensions
    output_path = config.GOLD_DIR + '/dimensions/dim_managers.parquet'
    dim_managers.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ dim_managers created: {len(dim_managers)} managers")
    return dim_managers


def create_dim_clubs() -> pd.DataFrame:
    """
    Create clubs dimension table.
    SCD Type 0 - Static.
    
    Returns:
        DataFrame with clubs dimension
    """
    logging.info("🔄 Creating dim_clubs...")
    
    # Load raw player data to get teams
    raw_data = load_bronze_json(config.BRONZE_PLAYERS_RAW)
    
    if not raw_data or 'teams' not in raw_data:
        logging.error("❌ No teams data found")
        return pd.DataFrame()
    
    teams = raw_data['teams']
    
    # Create dimension table
    dim_clubs = pd.DataFrame(teams)
    
    # Select relevant columns
    dim_clubs = dim_clubs[[
        'id', 'name', 'short_name'
    ]].copy()
    
    # Rename for consistency
    dim_clubs = dim_clubs.rename(columns={
        'id': 'club_id',
        'name': 'club_name'
    })
    
    # Add metadata
    dim_clubs['created_at'] = datetime.now()
    
    # Save to Gold dimensions
    output_path = config.GOLD_DIR + '/dimensions/dim_clubs.parquet'
    dim_clubs.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ dim_clubs created: {len(dim_clubs)} clubs")
    return dim_clubs


def create_dim_players() -> pd.DataFrame:
    """
    Create players dimension table with ALL available columns.
    Includes both profile data and seasonal stats.
    SCD Type 2 - Track club changes.
    
    Returns:
        DataFrame with players dimension
    """
    logging.info("🔄 Creating dim_players (with all columns)...")
    
    # Load from Silver (now has ALL columns)
    df = pd.read_csv(config.SILVER_PLAYERS_CSV)
    
    logging.info(f"📊 Player data has {len(df.columns)} columns")
    
    # Load clubs to get club_id
    dim_clubs = pd.read_parquet(config.GOLD_DIR + '/dimensions/dim_clubs.parquet')
    club_map = dict(zip(dim_clubs['short_name'], dim_clubs['club_id']))
    
    # Map team to club_id
    if 'team' in df.columns:
        df['club_id'] = df['team'].map(club_map)
    
    # Add SCD Type 2 columns
    df['player_key'] = df['player_id']  # Surrogate key (for now same as natural key)
    df['valid_from'] = datetime.now().date()
    df['valid_to'] = None
    df['is_current'] = True
    
    # Save to Gold dimensions (preserve ALL columns)
    output_path = config.GOLD_DIR + '/dimensions/dim_players.parquet'
    df.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ dim_players created: {len(df)} players with {len(df.columns)} columns")
    return df


def create_dim_fixtures() -> pd.DataFrame:
    """
    Create fixtures dimension table.
    Loads from Silver layer fixtures.parquet.
    
    Returns:
        DataFrame with fixtures dimension
    """
    logging.info("🔄 Creating dim_fixtures...")
    
    import os
    
    # Load fixtures from Silver layer
    silver_fixtures_path = os.path.join(config.SILVER_DIR, "fixtures.parquet")
    
    if not os.path.exists(silver_fixtures_path):
        logging.error(f"❌ No fixtures data found in Silver layer: {silver_fixtures_path}")
        empty_df = pd.DataFrame(columns=['fixture_id'])
        output_path = os.path.join(config.GOLD_DIR, 'dimensions', 'dim_fixtures.parquet')
        empty_df.to_parquet(output_path, index=False, engine='pyarrow')
        return empty_df
    
    df = pd.read_parquet(silver_fixtures_path)
    
    if df.empty:
        logging.warning("⚠️ Fixtures data is empty")
        empty_df = pd.DataFrame(columns=['fixture_id'])
        output_path = os.path.join(config.GOLD_DIR, 'dimensions', 'dim_fixtures.parquet')
        empty_df.to_parquet(output_path, index=False, engine='pyarrow')
        return empty_df
    
    # Rename columns to match star schema naming
    rename_map = {
        'gameweek': 'gameweek_id',
        'finished': 'is_finished'
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    
    # Save to Gold dimensions
    output_path = os.path.join(config.GOLD_DIR, 'dimensions', 'dim_fixtures.parquet')
    df.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ dim_fixtures created: {len(df)} fixtures")
    return df


def create_dim_gameweeks() -> pd.DataFrame:
    """
    Create gameweeks dimension table.
    SCD Type 1 - Update status fields.
    
    Returns:
        DataFrame with gameweeks dimension
    """
    logging.info("🔄 Creating dim_gameweeks...")
    
    # Load raw game data
    raw_data = load_bronze_json(config.BRONZE_PLAYERS_RAW)
    
    if not raw_data or 'events' not in raw_data:
        logging.error("❌ No gameweek data found")
        return pd.DataFrame()
    
    events = raw_data['events']
    
    # Create dimension table
    dim_gameweeks = pd.DataFrame(events)
    
    # Select relevant columns
    cols_to_keep = [
        'id', 'name', 'deadline_time', 'finished', 
        'average_entry_score', 'highest_score'
    ]
    
    # Filter to existing columns
    existing_cols = [col for col in cols_to_keep if col in dim_gameweeks.columns]
    dim_gameweeks = dim_gameweeks[existing_cols].copy()
    
    # Rename columns (only if they exist)
    rename_map = {
        'id': 'gameweek_id',
        'name': 'gameweek_name',
        'finished': 'is_finished',
        'average_entry_score': 'avg_score'
    }
    # Only rename columns that exist
    rename_map = {k: v for k, v in rename_map.items() if k in dim_gameweeks.columns}
    dim_gameweeks = dim_gameweeks.rename(columns=rename_map)
    
    # Add gameweek number (use existing ID column or create from index)
    if 'gameweek_id' in dim_gameweeks.columns:
        dim_gameweeks['gameweek_num'] = dim_gameweeks['gameweek_id']
    else:
        # If no ID column, use index + 1 as gameweek number
        dim_gameweeks['gameweek_id'] = range(1, len(dim_gameweeks) + 1)
        dim_gameweeks['gameweek_num'] = dim_gameweeks['gameweek_id']
    
    # Add is_current flag
    if 'is_finished' in dim_gameweeks.columns:
        finished_gws = dim_gameweeks[dim_gameweeks['is_finished'] == True]['gameweek_id'].max()
        current_gw = finished_gws + 1 if pd.notna(finished_gws) else 1
        dim_gameweeks['is_current'] = dim_gameweeks['gameweek_id'] == current_gw
    else:
        dim_gameweeks['is_current'] = False
    
    # Save to Gold dimensions
    output_path = config.GOLD_DIR + '/dimensions/dim_gameweeks.parquet'
    dim_gameweeks.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ dim_gameweeks created: {len(dim_gameweeks)} gameweeks")
    return dim_gameweeks


def main():
    """Create all dimension tables."""
    logging.info("📊 Creating dimensional model - Dimensions...")
    
    import os
    os.makedirs(config.GOLD_DIR + '/dimensions', exist_ok=True)
    
    # Create dimensions in order (clubs before players due to FK)
    create_dim_clubs()
    create_dim_managers()
    create_dim_players()  # Now includes all columns
    create_dim_gameweeks()
    create_dim_fixtures()  # New: fixtures with difficulty ratings
    
    logging.info("🎉 All dimensions created!")


if __name__ == "__main__":
    main()
