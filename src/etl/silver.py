"""
Silver Layer: Transform Bronze (raw) data into cleaned, validated datasets.
This module reads raw JSON from Bronze layer and produces CSV/Parquet files.
"""
import json
import logging
import pandas as pd
from typing import Dict, Any, List
from src.config import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def load_bronze_json(file_path: str) -> Dict[Any, Any]:
    """Load JSON data from Bronze layer."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        logging.error(f"❌ Bronze file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"❌ Invalid JSON in {file_path}: {e}")
        return {}


def transform_league_standings() -> pd.DataFrame:
    """
    Transform raw league data into cleaned CSV.
    
    Returns:
        DataFrame with league standings
    """
    logging.info("🔄 Transforming league standings (Bronze → Silver)")
    
    # Load raw data from Bronze
    raw_data = load_bronze_json(config.BRONZE_LEAGUE_RAW)
    
    if not raw_data or 'league_entries' not in raw_data:
        logging.error("❌ Invalid league data structure")
        return pd.DataFrame()
    
    # Extract league entries
    league_entries = raw_data['league_entries']
    
    # Transform to DataFrame
    df = pd.DataFrame(league_entries)
    
    # Select and rename columns
    columns_to_keep = [
        'entry_id', 'id', 'player_first_name', 'player_last_name',
        'short_name', 'waiver_pick', 'entry_name'
    ]
    
    # Filter columns that exist
    existing_cols = [col for col in columns_to_keep if col in df.columns]
    df = df[existing_cols]
    
    # Rename for consistency with current schema
    df = df.rename(columns={
        'entry_id': 'manager_id',
        'player_first_name': 'first_name',
        'player_last_name': 'last_name',
        'entry_name': 'team_name'
    })
    
    # Save to Silver layer
    df.to_csv(config.SILVER_LEAGUE_CSV, index=False)
    logging.info(f"✅ Silver: League standings saved to {config.SILVER_LEAGUE_CSV}")
    
    return df


def transform_players_data() -> pd.DataFrame:
    """
    Transform raw player data into cleaned CSV.
    Includes ALL available columns from API.
    
    Returns:
        DataFrame with player statistics
    """
    logging.info("🔄 Transforming player data (Bronze → Silver)")
    
    # Load raw data from Bronze
    raw_data = load_bronze_json(config.BRONZE_PLAYERS_RAW)
    
    if not raw_data or 'elements' not in raw_data:
        logging.error("❌ Invalid player data structure")
        return pd.DataFrame()
    
    # Extract elements (players) and teams
    players = raw_data['elements']
    teams = {team['id']: team['short_name'] for team in raw_data.get('teams', [])}
    
    # Transform to DataFrame (KEEP ALL COLUMNS)
    df = pd.DataFrame(players)
    
    # Add team name
    if 'team' in df.columns:
        df['team_name'] = df['team'].map(teams)
    
    # Map position codes to names
    position_map = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    if 'element_type' in df.columns:
        df['position'] = df['element_type'].map(position_map)
    
    # Rename key columns for consistency (but keep all other columns)
    rename_map = {
        'id': 'player_id',
        'web_name': 'name',
        'first_name': 'first_name',
        'second_name': 'last_name',
        'team': 'team_id',
        'team_name': 'team',
        'expected_assists': 'xA',
        'clean_sheets': 'CS',
        'goals_conceded': 'Gc',
        'goals_scored': 'goals',
        'expected_goals': 'xG',
        'expected_goal_involvements': 'xGi',
        'expected_goals_conceded': 'xGc',
        'points_per_game': 'PpG'
    }
    
    # Only rename columns that exist
    existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=existing_renames)
    
    # Save to Silver layer (with ALL columns preserved)
    df.to_csv(config.SILVER_PLAYERS_CSV, index=False)
    logging.info(f"✅ Silver: Player data saved with {len(df.columns)} columns to {config.SILVER_PLAYERS_CSV}")
    
    return df


def transform_gameweek_data(gameweek: int, manager_ids: List[int]) -> pd.DataFrame:
    """
    Transform raw gameweek data into cleaned Parquet.
    
    Args:
        gameweek: Gameweek number
        manager_ids: List of manager IDs
        
    Returns:
        DataFrame with gameweek player stats and manager picks
    """
    logging.info(f"🔄 Transforming gameweek {gameweek} data (Bronze → Silver)")
    
    # Load raw gameweek stats
    gw_raw_path = config.get_bronze_gameweek_path(gameweek)
    gw_data = load_bronze_json(gw_raw_path)
    
    if not gw_data or 'elements' not in gw_data:
        logging.warning(f"⚠️ No gameweek data for GW{gameweek}")
        return pd.DataFrame()
    
    # Transform gameweek stats
    # Note: 'elements' is a dictionary keyed by player ID (string keys)
    gw_stats = []
    elements = gw_data['elements']
    
    # Handle both dict and list formats
    if isinstance(elements, dict):
        # Dict format: {player_id: player_data}
        for player_id, player_data in elements.items():
            # Get stats object (has ALL the gameweek stats)
            stats = player_data.get('stats', {})
            
            # Extract ALL available stats
            gw_stats.append({
                'ID': int(player_id),
                'gameweek': gameweek,
                # Basic performance
                'gw_points': stats.get('total_points', 0),
                'gw_minutes': stats.get('minutes', 0),
                'gw_goals': stats.get('goals_scored', 0),
                'gw_assists': stats.get('assists', 0),
                'gw_clean_sheets': stats.get('clean_sheets', 0),
                'gw_goals_conceded': stats.get('goals_conceded', 0),
                'gw_bonus': stats.get('bonus', 0),
                'gw_bps': stats.get('bps', 0),
                # Defensive stats
                'gw_saves': stats.get('saves', 0),
                'gw_penalties_saved': stats.get('penalties_saved', 0),
                'gw_yellow_cards': stats.get('yellow_cards', 0),
                'gw_red_cards': stats.get('red_cards', 0),
                'gw_own_goals': stats.get('own_goals', 0),
                'gw_penalties_missed': stats.get('penalties_missed', 0),
                # Advanced stats (ICT)
                'gw_influence': stats.get('influence', 0.0),
                'gw_creativity': stats.get('creativity', 0.0),
                'gw_threat': stats.get('threat', 0.0),
                'gw_ict_index': stats.get('ict_index', 0.0),
                # Expected stats (xG, xA)
                'gw_expected_goals': stats.get('expected_goals', 0.0),
                'gw_expected_assists': stats.get('expected_assists', 0.0),
                'gw_expected_goal_involvements': stats.get('expected_goal_involvements', 0.0),
                'gw_expected_goals_conceded': stats.get('expected_goals_conceded', 0.0),
                # Defensive contribution
                'gw_clearances_blocks_interceptions': stats.get('clearances_blocks_interceptions', 0),
                'gw_recoveries': stats.get('recoveries', 0),
                'gw_tackles': stats.get('tackles', 0),
                'gw_defensive_contribution': stats.get('defensive_contribution', 0),
                # Other
                'gw_starts': stats.get('starts', 0),
                'gw_in_dreamteam': stats.get('in_dreamteam', False),
            })
    else:
        # List format (legacy - shouldn't happen but keep for safety)
        for player in elements:
            stats = player.get('stats', {})
            gw_stats.append({
                'ID': player['id'],
                'gameweek': gameweek,
                'gw_points': stats.get('total_points', 0),
                'gw_minutes': stats.get('minutes', 0),
                'gw_goals': stats.get('goals_scored', 0),
                'gw_assists': stats.get('assists', 0),
                'gw_clean_sheets': stats.get('clean_sheets', 0),
                'gw_goals_conceded': stats.get('goals_conceded', 0),
                'gw_bonus': stats.get('bonus', 0),
                'gw_saves': stats.get('saves', 0),
                'gw_yellow_cards': stats.get('yellow_cards', 0),
                'gw_red_cards': stats.get('red_cards', 0),
            })
    
    df_stats = pd.DataFrame(gw_stats)
    
    # Load and transform manager picks
    picks_list = []
    for manager_id in manager_ids:
        picks_path = config.get_bronze_picks_path(gameweek, manager_id)
        picks_data = load_bronze_json(picks_path)
        
        if picks_data and 'picks' in picks_data:
            for pick in picks_data['picks']:
                picks_list.append({
                    'ID': pick['element'],
                    'gameweek': gameweek,
                    'manager_id': manager_id,
                    'position': pick.get('position')
                })
    
    df_picks = pd.DataFrame(picks_list)
    
    # Merge stats with picks
    if not df_picks.empty:
        df_merged = df_stats.merge(df_picks, on=['ID', 'gameweek'], how='left')
    else:
        df_merged = df_stats
        df_merged['manager_id'] = None
        df_merged['position'] = None
    
    # Save to Silver layer
    output_path = config.get_silver_gameweek_path(gameweek)
    df_merged.to_parquet(output_path, index=False, engine='pyarrow')
    logging.info(f"✅ Silver: Gameweek {gameweek} saved to {output_path}")
    
    return df_merged


def merge_all_gameweeks() -> pd.DataFrame:
    """
    Merge all Silver layer gameweek files into one dataset.
    This creates an intermediate Silver file for Gold layer to consume.
    
    Returns:
        Merged DataFrame with all gameweeks
    """
    logging.info("🔄 Merging all Silver gameweek files")
    
    import os
    
    # Find all gameweek parquet files
    gw_files = sorted([
        f for f in os.listdir(config.SILVER_GAMEWEEKS_DIR)
        if f.endswith('.parquet')
    ])
    
    if not gw_files:
        logging.warning("⚠️ No gameweek files found in Silver layer")
        return pd.DataFrame()
    
    # Load and concatenate
    dfs = []
    for filename in gw_files:
        file_path = os.path.join(config.SILVER_GAMEWEEKS_DIR, filename)
        df = pd.read_parquet(file_path)
        dfs.append(df)
    
    merged_df = pd.concat(dfs, ignore_index=True)
    
    logging.info(f"✅ Silver: Merged {len(gw_files)} gameweeks into {len(merged_df)} records")
    
    return merged_df


def main():
    """Run Silver layer transformations."""
    logging.info("🥈 Starting Silver Layer transformations...")
    
    # Transform league standings
    transform_league_standings()
    
    # Transform player data
    transform_players_data()
    
    logging.info("🎉 Silver Layer transformations complete!")


if __name__ == "__main__":
    main()
