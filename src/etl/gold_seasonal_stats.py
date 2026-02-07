"""
Create fact table for player seasonal stats.
Separates seasonal (accumulated) stats from gameweek stats.
"""
import logging
import pandas as pd
from src.config import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def create_fact_player_seasonal_stats() -> pd.DataFrame:
    """
    Create fact table for player seasonal statistics.
    This table contains accumulated stats for the season (not per gameweek).
    
    Grain: One row per player (current season snapshot)
    
    Returns:
        DataFrame with seasonal stats
    """
    logging.info("🔄 Creating fact_player_seasonal_stats...")
    
    # Load complete player data from dimensions (has all columns)
    dim_players = pd.read_parquet(config.GOLD_DIR + '/dimensions/dim_players.parquet')
    
    # Filter to current players only
    current_players = dim_players[dim_players['is_current'] == True].copy()
    
    # Identify seasonal stat columns (accumulated totals)
    # These are columns that represent season totals, not per-gameweek
    seasonal_cols = [
        'player_id', 'player_key', 'club_id',
        # Profile data
        'name', 'position', 'code',
        # Seasonal totals
        'total_points', 'minutes', 'goals', 'assists', 'clean_sheets',
        'goals_conceded', 'own_goals', 'penalties_saved', 'penalties_missed',
        'yellow_cards', 'red_cards', 'saves', 'bonus', 'bps',
        'influence', 'creativity', 'threat', 'ict_index',
        # Expected stats (seasonal)
        'xG', 'xA', 'xGi', 'xGc',
        # Averages
        'PpG', 'points_per_game', 'selected_by_percent', 'form',
        # Appearance stats
        'starts', 'appearances',
        # Value
        'now_cost', 'cost_change_start', 'cost_change_event',
        # Status
        'status', 'chance_of_playing_this_round', 'chance_of_playing_next_round',
        'news', 'news_added'
    ]
    
    # Filter to columns that actually exist
    existing_seasonal_cols = [col for col in seasonal_cols if col in current_players.columns]
    
    fact_seasonal = current_players[existing_seasonal_cols].copy()
    
    # Add fact ID
    fact_seasonal['seasonal_stats_id'] = range(1, len(fact_seasonal) + 1)
    
    # Reorder columns (ID first)
    cols = ['seasonal_stats_id'] + [col for col in fact_seasonal.columns if col != 'seasonal_stats_id']
    fact_seasonal = fact_seasonal[cols]
    
    # Save to Gold facts
    output_path = config.GOLD_DIR + '/facts/fact_player_seasonal_stats.parquet'
    fact_seasonal.to_parquet(output_path, index=False, engine='pyarrow')
    
    logging.info(f"✅ fact_player_seasonal_stats created: {len(fact_seasonal)} players with {len(fact_seasonal.columns)} columns")
    return fact_seasonal


def main():
    """Create player seasonal stats fact table."""
    logging.info("📊 Creating player seasonal stats fact...")
    
    import os
    os.makedirs(config.GOLD_DIR + '/facts', exist_ok=True)
    
    create_fact_player_seasonal_stats()
    
    logging.info("🎉 Player seasonal stats fact created!")


if __name__ == "__main__":
    main()
