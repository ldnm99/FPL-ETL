"""
Gold Layer: Create analytics-ready aggregated datasets.
This module reads Silver layer data and produces business-ready aggregations.
"""
import logging
import pandas as pd
from typing import Optional
from src.config import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def create_full_gameweek_dataset() -> pd.DataFrame:
    """
    Create full merged gameweek dataset with player and manager info.
    This is the main analytics dataset.
    
    Returns:
        Complete gameweek dataset with all enrichments
    """
    logging.info("🔄 Creating Gold: Full gameweek dataset")
    
    # Load Silver layer data
    from src.etl.silver import merge_all_gameweeks
    df_gameweeks = merge_all_gameweeks()
    
    if df_gameweeks.empty:
        logging.warning("⚠️ No gameweek data available")
        return pd.DataFrame()
    
    # Load player data for enrichment
    df_players = pd.read_csv(config.SILVER_PLAYERS_CSV)
    
    # Load league standings for manager info
    df_league = pd.read_csv(config.SILVER_LEAGUE_CSV)
    
    # Merge with player info
    df_enriched = df_gameweeks.merge(
        df_players[['player_id', 'name', 'team', 'position', 'total_points']],
        left_on='ID',
        right_on='player_id',
        how='left',
        suffixes=('', '_season')
    )
    
    # Merge with manager info
    df_enriched = df_enriched.merge(
        df_league[['manager_id', 'first_name', 'last_name', 'team_name']],
        on='manager_id',
        how='left'
    )
    
    # Rename columns for clarity
    df_enriched = df_enriched.rename(columns={
        'total_points': 'season_points',
        'team_name': 'manager_team_name'
    })
    
    # Sort by gameweek and points
    df_enriched = df_enriched.sort_values(['gameweek', 'gw_points'], ascending=[True, False])
    
    # Save to Gold layer
    df_enriched.to_parquet(config.GOLD_GW_DATA_FULL, index=False, engine='pyarrow')
    logging.info(f"✅ Gold: Full gameweek dataset saved ({len(df_enriched)} records)")
    
    return df_enriched


def create_player_season_stats() -> pd.DataFrame:
    """
    Create aggregated player season statistics.
    
    Returns:
        Player-level season aggregations
    """
    logging.info("🔄 Creating Gold: Player season statistics")
    
    # Load full gameweek data
    try:
        df = pd.read_parquet(config.GOLD_GW_DATA_FULL)
    except FileNotFoundError:
        logging.warning("⚠️ Full gameweek dataset not found, creating it first")
        df = create_full_gameweek_dataset()
    
    if df.empty:
        return pd.DataFrame()
    
    # Aggregate by player
    player_stats = df.groupby(['ID', 'name', 'team', 'position']).agg({
        'gw_points': ['sum', 'mean', 'max', 'min', 'std'],
        'gw_minutes': 'sum',
        'gw_goals': 'sum',
        'gw_assists': 'sum',
        'gw_clean_sheets': 'sum',
        'gw_bonus': 'sum',
        'gameweek': 'count'  # Number of gameweeks played
    }).reset_index()
    
    # Flatten column names
    player_stats.columns = [
        'ID', 'name', 'team', 'position',
        'total_points', 'avg_points', 'max_points', 'min_points', 'std_points',
        'total_minutes', 'total_goals', 'total_assists',
        'total_clean_sheets', 'total_bonus', 'gameweeks_played'
    ]
    
    # Calculate additional metrics
    player_stats['points_per_game'] = (
        player_stats['total_points'] / player_stats['gameweeks_played']
    ).round(2)
    
    player_stats['minutes_per_game'] = (
        player_stats['total_minutes'] / player_stats['gameweeks_played']
    ).round(2)
    
    # Sort by total points
    player_stats = player_stats.sort_values('total_points', ascending=False)
    
    # Save to Gold layer
    player_stats.to_parquet(config.GOLD_PLAYER_SEASON_STATS, index=False, engine='pyarrow')
    logging.info(f"✅ Gold: Player season stats saved ({len(player_stats)} players)")
    
    return player_stats


def create_manager_performance() -> pd.DataFrame:
    """
    Create manager performance metrics over time.
    
    Returns:
        Manager-level performance aggregations
    """
    logging.info("🔄 Creating Gold: Manager performance")
    
    # Load full gameweek data
    try:
        df = pd.read_parquet(config.GOLD_GW_DATA_FULL)
    except FileNotFoundError:
        logging.warning("⚠️ Full gameweek dataset not found, creating it first")
        df = create_full_gameweek_dataset()
    
    if df.empty:
        return pd.DataFrame()
    
    # Filter only picked players (have manager_id)
    df_picks = df[df['manager_id'].notna()].copy()
    
    # Aggregate by manager and gameweek
    manager_gw_stats = df_picks.groupby(['manager_id', 'gameweek', 'manager_team_name']).agg({
        'gw_points': 'sum',
        'ID': 'count'  # Number of players
    }).reset_index()
    
    manager_gw_stats = manager_gw_stats.rename(columns={
        'gw_points': 'total_gw_points',
        'ID': 'players_count'
    })
    
    # Calculate cumulative points
    manager_gw_stats = manager_gw_stats.sort_values(['manager_id', 'gameweek'])
    manager_gw_stats['cumulative_points'] = manager_gw_stats.groupby('manager_id')['total_gw_points'].cumsum()
    
    # Calculate rolling average (last 3 gameweeks)
    manager_gw_stats['rolling_avg_3gw'] = (
        manager_gw_stats.groupby('manager_id')['total_gw_points']
        .transform(lambda x: x.rolling(window=3, min_periods=1).mean())
        .round(2)
    )
    
    # Add rank per gameweek
    manager_gw_stats['gw_rank'] = (
        manager_gw_stats.groupby('gameweek')['total_gw_points']
        .rank(ascending=False, method='min')
    )
    
    # Save to Gold layer
    manager_gw_stats.to_parquet(config.GOLD_MANAGER_PERFORMANCE, index=False, engine='pyarrow')
    logging.info(f"✅ Gold: Manager performance saved ({len(manager_gw_stats)} records)")
    
    return manager_gw_stats


def main():
    """Run Gold layer aggregations."""
    logging.info("🥇 Starting Gold Layer aggregations...")
    
    # Create full gameweek dataset
    create_full_gameweek_dataset()
    
    # Create player season stats
    create_player_season_stats()
    
    # Create manager performance
    create_manager_performance()
    
    # Create dimensional model (star schema)
    logging.info("📊 Creating dimensional model (star schema)...")
    from src.etl import gold_dimensions, gold_facts
    
    gold_dimensions.main()  # Create dimension tables
    gold_facts.main()       # Create fact tables
    
    logging.info("🎉 Gold Layer aggregations complete!")


if __name__ == "__main__":
    main()
