"""
Gold Layer - Dimensional Model: Fact Tables
Create fact tables for star schema.
"""
import logging
import pandas as pd
import os
from src.config import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def create_fact_player_performance(incremental=True, recent_gws=2) -> pd.DataFrame:
    """
    Create player performance fact table.
    Grain: One row per player per gameweek.
    
    Args:
        incremental: If True, load existing data and only update recent gameweeks
        recent_gws: Number of recent gameweeks to update (default: 2)
    
    Returns:
        DataFrame with player performance facts
    """
    logging.info("🔄 Creating fact_player_performance...")
    
    # Determine which gameweeks to process
    gw_files = sorted([
        f for f in os.listdir(config.SILVER_GAMEWEEKS_DIR)
        if f.endswith('.parquet')
    ])
    
    if not gw_files:
        logging.warning("⚠️ No gameweek files found")
        return pd.DataFrame()
    
    # Load existing Gold data if incremental mode
    existing_df = None
    output_path = config.GOLD_DIR + '/facts/fact_player_performance.parquet'
    
    if incremental and os.path.exists(output_path):
        existing_df = pd.read_parquet(output_path)
        # Get max gameweek to determine which ones to update
        if not existing_df.empty and 'gameweek_id' in existing_df.columns:
            max_gw = existing_df['gameweek_id'].max()
            start_gw = max(1, max_gw - recent_gws + 1)
            logging.info(f"📊 Incremental update: processing GW{start_gw} onwards (updating last {recent_gws} GWs)")
            # Filter files to only recent gameweeks
            # Format: gw_data_gw25.parquet
            gw_files = [f for f in gw_files if int(f.replace('gw_data_gw', '').replace('.parquet', '')) >= start_gw]
            # Remove old data for these gameweeks
            existing_df = existing_df[existing_df['gameweek_id'] < start_gw]
    
    # Load and concatenate new data
    dfs = []
    for filename in gw_files:
        file_path = os.path.join(config.SILVER_GAMEWEEKS_DIR, filename)
        df = pd.read_parquet(file_path)
        dfs.append(df)
    
    if not dfs:
        logging.info("✅ No new gameweeks to process")
        return existing_df if existing_df is not None else pd.DataFrame()
    
    fact_performance = pd.concat(dfs, ignore_index=True)
    
    # Load dim_players to get player_key and club_id
    dim_players = pd.read_parquet(config.GOLD_DIR + '/dimensions/dim_players.parquet')
    player_mapping = dim_players[['player_id', 'player_key', 'club_id']].copy()
    
    # Merge to get player_key and club_id
    fact_performance = fact_performance.merge(
        player_mapping,
        left_on='ID',
        right_on='player_id',
        how='left'
    )
    
    # Select and rename columns for fact table
    fact_cols = {
        'player_key': 'player_key',
        'player_id': 'player_id',
        'club_id': 'club_id',
        'gameweek': 'gameweek_id',
        # Basic performance
        'gw_points': 'gw_points',
        'gw_minutes': 'gw_minutes',
        'gw_goals': 'gw_goals',
        'gw_assists': 'gw_assists',
        'gw_clean_sheets': 'gw_clean_sheets',
        'gw_goals_conceded': 'gw_goals_conceded',
        'gw_bonus': 'gw_bonus',
        'gw_bps': 'gw_bps',
        # Defensive stats
        'gw_saves': 'gw_saves',
        'gw_penalties_saved': 'gw_penalties_saved',
        'gw_yellow_cards': 'gw_yellow_cards',
        'gw_red_cards': 'gw_red_cards',
        'gw_own_goals': 'gw_own_goals',
        'gw_penalties_missed': 'gw_penalties_missed',
        # Advanced stats (ICT)
        'gw_influence': 'gw_influence',
        'gw_creativity': 'gw_creativity',
        'gw_threat': 'gw_threat',
        'gw_ict_index': 'gw_ict_index',
        # Expected stats (xG, xA)
        'gw_expected_goals': 'gw_xG',
        'gw_expected_assists': 'gw_xA',
        'gw_expected_goal_involvements': 'gw_xGi',
        'gw_expected_goals_conceded': 'gw_xGc',
        # Defensive contribution
        'gw_clearances_blocks_interceptions': 'gw_clearances_blocks_interceptions',
        'gw_recoveries': 'gw_recoveries',
        'gw_tackles': 'gw_tackles',
        'gw_defensive_contribution': 'gw_defensive_contribution',
        # Other
        'gw_starts': 'gw_starts',
        'gw_in_dreamteam': 'gw_in_dreamteam',
    }
    
    # Filter to existing columns
    existing_fact_cols = {k: v for k, v in fact_cols.items() if k in fact_performance.columns}
    fact_performance = fact_performance.rename(columns=existing_fact_cols)
    
    # Select only fact columns
    final_cols = list(existing_fact_cols.values())
    fact_performance = fact_performance[final_cols].copy()
    
    # Combine with existing data if in incremental mode
    if existing_df is not None and not existing_df.empty:
        logging.info(f"📊 Combining {len(existing_df)} existing + {len(fact_performance)} new records")
        fact_performance = pd.concat([existing_df, fact_performance], ignore_index=True)
    
    # Add surrogate key
    fact_performance['performance_id'] = range(1, len(fact_performance) + 1)
    
    # Reorder columns (surrogate key first)
    cols = ['performance_id'] + [col for col in fact_performance.columns if col != 'performance_id']
    fact_performance = fact_performance[cols]
    
    # Save to Gold facts
    output_path = config.GOLD_DIR + '/facts/fact_player_performance.parquet'
    fact_performance.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ fact_player_performance created: {len(fact_performance)} records")
    return fact_performance


def create_fact_manager_picks() -> pd.DataFrame:
    """
    Create manager picks fact table.
    Grain: One row per manager per player per gameweek.
    
    Returns:
        DataFrame with manager picks facts
    """
    logging.info("🔄 Creating fact_manager_picks...")
    
    # Load all Silver gameweek parquet files
    gw_files = sorted([
        f for f in os.listdir(config.SILVER_GAMEWEEKS_DIR)
        if f.endswith('.parquet')
    ])
    
    if not gw_files:
        logging.warning("⚠️ No gameweek files found")
        return pd.DataFrame()
    
    # Load and concatenate
    dfs = []
    for filename in gw_files:
        file_path = os.path.join(config.SILVER_GAMEWEEKS_DIR, filename)
        df = pd.read_parquet(file_path)
        dfs.append(df)
    
    fact_picks = pd.concat(dfs, ignore_index=True)
    
    # Filter only rows where manager_id is not null (actual picks)
    fact_picks = fact_picks[fact_picks['manager_id'].notna()].copy()
    
    # Select relevant columns
    cols_to_keep = ['manager_id', 'ID', 'gameweek', 'position']
    existing_cols = [col for col in cols_to_keep if col in fact_picks.columns]
    fact_picks = fact_picks[existing_cols].copy()
    
    # Rename columns
    fact_picks = fact_picks.rename(columns={
        'ID': 'player_id',
        'gameweek': 'gameweek_id'
    })
    
    # Add surrogate key
    fact_picks['pick_id'] = range(1, len(fact_picks) + 1)
    
    # Reorder columns (surrogate key first)
    cols = ['pick_id'] + [col for col in fact_picks.columns if col != 'pick_id']
    fact_picks = fact_picks[cols]
    
    # Save to Gold facts
    output_path = config.GOLD_DIR + '/facts/fact_manager_picks.parquet'
    fact_picks.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ fact_manager_picks created: {len(fact_picks)} picks")
    return fact_picks


def create_manager_gameweek_performance() -> pd.DataFrame:
    """
    Create denormalized table: Manager's picks with performance per gameweek.
    This is a WIDE table for easy querying - shows each manager's full team
    performance for each gameweek.
    
    Grain: One row per manager per player per gameweek
    
    Returns:
        DataFrame with manager gameweek performance
    """
    logging.info("🔄 Creating manager_gameweek_performance (denormalized)...")
    
    # Load fact tables
    fact_picks = pd.read_parquet(config.GOLD_DIR + '/facts/fact_manager_picks.parquet')
    fact_performance = pd.read_parquet(config.GOLD_DIR + '/facts/fact_player_performance.parquet')
    
    # Load dimensions
    dim_managers = pd.read_parquet(config.GOLD_DIR + '/dimensions/dim_managers.parquet')
    dim_players = pd.read_parquet(config.GOLD_DIR + '/dimensions/dim_players.parquet')
    dim_clubs = pd.read_parquet(config.GOLD_DIR + '/dimensions/dim_clubs.parquet')
    dim_gameweeks = pd.read_parquet(config.GOLD_DIR + '/dimensions/dim_gameweeks.parquet')
    
    # Start with manager picks
    mgr_performance = fact_picks.copy()
    
    # Join with player performance
    mgr_performance = mgr_performance.merge(
        fact_performance[['player_id', 'gameweek_id', 'gw_points', 'gw_minutes', 
                         'gw_goals', 'gw_assists', 'gw_clean_sheets', 'gw_bonus']],
        on=['player_id', 'gameweek_id'],
        how='left'
    )
    
    # Join with manager info
    mgr_performance = mgr_performance.merge(
        dim_managers[['manager_id', 'first_name', 'last_name', 'team_name']],
        on='manager_id',
        how='left'
    )
    
    # Join with player info
    mgr_performance = mgr_performance.merge(
        dim_players[['player_id', 'name', 'club_id', 'position']],
        on='player_id',
        how='left',
        suffixes=('', '_player')
    )
    
    # Join with club info
    mgr_performance = mgr_performance.merge(
        dim_clubs[['club_id', 'club_name', 'short_name']],
        on='club_id',
        how='left'
    )
    
    # Join with gameweek info (using available columns)
    gw_cols = ['gameweek_id', 'gameweek_num']
    # Add optional columns if they exist
    if 'is_finished' in dim_gameweeks.columns:
        gw_cols.append('is_finished')
    if 'is_current' in dim_gameweeks.columns:
        gw_cols.append('is_current')
    
    mgr_performance = mgr_performance.merge(
        dim_gameweeks[gw_cols],
        on='gameweek_id',
        how='left'
    )
    
    # Rename columns for clarity
    mgr_performance = mgr_performance.rename(columns={
        'name': 'player_name',
        'position_player': 'player_position',
        'position': 'team_position',
        'team_name': 'manager_team_name'
    })
    
    # Select final columns in logical order
    final_cols = [
        'gameweek_num',
        'manager_id',
        'first_name',
        'last_name',
        'manager_team_name',
        'player_id',
        'player_name',
        'player_position',
        'club_name',
        'short_name',
        'team_position',
        'gw_points',
        'gw_minutes',
        'gw_goals',
        'gw_assists',
        'gw_clean_sheets',
        'gw_bonus',
        'is_finished'
    ]
    
    # Filter to existing columns
    existing_final_cols = [col for col in final_cols if col in mgr_performance.columns]
    mgr_performance = mgr_performance[existing_final_cols]
    
    # Sort by gameweek, manager, team position
    sort_cols = ['gameweek_num', 'manager_id']
    if 'team_position' in mgr_performance.columns:
        sort_cols.append('team_position')
    
    mgr_performance = mgr_performance.sort_values(sort_cols)
    
    # Save to Gold facts
    output_path = config.GOLD_DIR + '/facts/manager_gameweek_performance.parquet'
    mgr_performance.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ manager_gameweek_performance created: {len(mgr_performance)} records")
    return mgr_performance


def main():
    """Create all fact tables."""
    logging.info("📊 Creating dimensional model - Facts...")
    
    import os
    os.makedirs(config.GOLD_DIR + '/facts', exist_ok=True)
    
    # Create fact tables
    create_fact_player_performance()  # Gameweek-level stats
    create_fact_manager_picks()
    
    # Create player seasonal stats (new)
    from src.etl import gold_seasonal_stats
    gold_seasonal_stats.create_fact_player_seasonal_stats()
    
    # Create denormalized manager performance table
    create_manager_gameweek_performance()
    
    logging.info("🎉 All facts created!")


if __name__ == "__main__":
    main()
