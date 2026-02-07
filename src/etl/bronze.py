"""
Bronze Layer: Extract and store raw data from FPL API.
This module saves API responses exactly as received (no transformations).
"""
import json
import logging
import os
from typing import Dict, Any, List
from src.utils import fetch_data
from src.config import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def save_raw_json(data: Dict[Any, Any], file_path: str) -> None:
    """Save raw JSON data to file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logging.info(f"✅ Saved raw JSON: {file_path}")


def extract_league_raw() -> Dict[Any, Any]:
    """
    Extract raw league standings data from FPL API.
    
    Returns:
        Raw JSON response from API
    """
    url = f"{config.BASE_URL}/league/{config.LEAGUE_ID}/details"
    logging.info(f"📊 Fetching raw league data from: {url}")
    
    data = fetch_data(url)
    
    if not data:
        logging.error(f"❌ No league data found for league ID {config.LEAGUE_ID}")
        return {}
    
    # Save raw JSON to Bronze layer
    save_raw_json(data, config.BRONZE_LEAGUE_RAW)
    logging.info(f"✅ Bronze: League raw data saved")
    
    return data


def extract_players_raw() -> Dict[Any, Any]:
    """
    Extract raw player data from FPL API.
    
    Returns:
        Raw JSON response from API
    """
    url = f"{config.BASE_URL}/bootstrap-static"
    logging.info(f"🧍 Fetching raw player data from: {url}")
    
    data = fetch_data(url)
    
    if not data:
        logging.error("❌ No player data found")
        return {}
    
    # Save raw JSON to Bronze layer
    save_raw_json(data, config.BRONZE_PLAYERS_RAW)
    logging.info(f"✅ Bronze: Player raw data saved")
    
    return data


def extract_fixtures_raw() -> List[Dict[Any, Any]]:
    """
    Extract raw fixtures data from bootstrap-static endpoint.
    The Draft API includes fixtures in the bootstrap-static response.
    
    Returns:
        List of fixture dicts
    """
    import os
    import json
    logging.info("🏟️ Extracting fixtures from bootstrap-static...")
    
    # Load player data (which contains fixtures)
    if not os.path.exists(config.BRONZE_PLAYERS_RAW):
        logging.error(f"❌ Bootstrap-static not found: {config.BRONZE_PLAYERS_RAW}")
        logging.info("Run extract_players_raw() first")
        return []
    
    with open(config.BRONZE_PLAYERS_RAW, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    if not raw_data or 'fixtures' not in raw_data:
        logging.error("❌ No fixtures data found in bootstrap-static")
        return []
    
    fixtures = raw_data['fixtures']
    
    # Save raw JSON to Bronze layer
    fixtures_path = os.path.join(config.BRONZE_DIR, "fixtures_raw.json")
    save_raw_json(fixtures, fixtures_path)
    logging.info(f"✅ Bronze: Fixtures raw data saved ({len(fixtures)} fixtures)")
    
    return fixtures


def extract_gameweek_raw(gameweek: int) -> Dict[Any, Any]:
    """
    Extract raw gameweek live data from FPL API.
    
    Args:
        gameweek: Gameweek number
        
    Returns:
        Raw JSON response from API
    """
    url = f"{config.BASE_URL}/event/{gameweek}/live"
    logging.info(f"📈 Fetching raw gameweek {gameweek} data")
    
    data = fetch_data(url)
    
    if not data:
        logging.warning(f"⚠️ No data found for gameweek {gameweek}")
        return {}
    
    # Save raw JSON to Bronze layer
    file_path = config.get_bronze_gameweek_path(gameweek)
    save_raw_json(data, file_path)
    logging.info(f"✅ Bronze: Gameweek {gameweek} raw data saved")
    
    return data


def extract_manager_picks_raw(manager_id: int, gameweek: int) -> Dict[Any, Any]:
    """
    Extract raw manager picks for a specific gameweek.
    
    Args:
        manager_id: Manager ID
        gameweek: Gameweek number
        
    Returns:
        Raw JSON response from API
    """
    url = f"{config.BASE_URL}/entry/{manager_id}/event/{gameweek}"
    
    data = fetch_data(url)
    
    if not data:
        logging.warning(f"⚠️ No picks found for manager {manager_id} in GW{gameweek}")
        return {}
    
    # Save raw JSON to Bronze layer
    file_path = config.get_bronze_picks_path(gameweek, manager_id)
    save_raw_json(data, file_path)
    
    return data


def extract_all_manager_picks_raw(manager_ids: List[int], gameweek: int) -> List[Dict[Any, Any]]:
    """
    Extract raw manager picks for all managers in a gameweek.
    
    Args:
        manager_ids: List of manager IDs
        gameweek: Gameweek number
        
    Returns:
        List of raw JSON responses
    """
    logging.info(f"🔄 Extracting picks for {len(manager_ids)} managers in GW{gameweek}")
    
    picks_data = []
    for manager_id in manager_ids:
        data = extract_manager_picks_raw(manager_id, gameweek)
        if data:
            picks_data.append(data)
    
    logging.info(f"✅ Bronze: Extracted {len(picks_data)} manager picks for GW{gameweek}")
    return picks_data


def get_current_gameweek() -> int:
    """
    Get current active gameweek from FPL API.
    
    Returns:
        Current gameweek number
    """
    url = f"{config.BASE_URL}/game"
    data = fetch_data(url)
    
    if data and 'current_event' in data:
        return data['current_event']
    
    logging.warning("⚠️ Could not determine current gameweek, defaulting to 1")
    return 1


def extract_all_gameweeks():
    """
    Extract ALL gameweeks from GW1 to current (full historical load).
    Use this for initial data load.
    """
    logging.info(f"🔄 Extracting ALL gameweeks (full load)...")
    
    # Get current gameweek
    current_gw = get_current_gameweek()
    logging.info(f"📅 Current gameweek: {current_gw}")
    
    # Load league data to get manager IDs
    import json
    if not os.path.exists(config.BRONZE_LEAGUE_RAW):
        logging.warning("⚠️ League data not found, extracting first...")
        extract_league_raw()
    
    with open(config.BRONZE_LEAGUE_RAW, 'r') as f:
        league_data = json.load(f)
    manager_ids = [entry['entry_id'] for entry in league_data.get('league_entries', [])]
    
    logging.info(f"📈 Extracting gameweeks 1 to {current_gw}")
    
    for gw in range(1, current_gw + 1):
        logging.info(f"  Extracting GW{gw}...")
        extract_gameweek_raw(gw)
        extract_all_manager_picks_raw(manager_ids, gw)
    
    logging.info(f"✅ All {current_gw} gameweeks extracted!")


def extract_recent_gameweeks(num_gameweeks: int = 2):
    """
    Extract only the most recent gameweeks (incremental update).
    This is more efficient than re-extracting all historical data.
    
    Args:
        num_gameweeks: Number of recent gameweeks to update (default: 2)
    """
    logging.info(f"🔄 Extracting last {num_gameweeks} gameweeks (incremental update)...")
    
    # Get current gameweek
    current_gw = get_current_gameweek()
    logging.info(f"📅 Current gameweek: {current_gw}")
    
    # Load league data to get manager IDs
    import json
    if not os.path.exists(config.BRONZE_LEAGUE_RAW):
        logging.warning("⚠️ League data not found, extracting first...")
        extract_league_raw()
    
    with open(config.BRONZE_LEAGUE_RAW, 'r') as f:
        league_data = json.load(f)
    manager_ids = [entry['entry_id'] for entry in league_data.get('league_entries', [])]
    
    # Calculate which gameweeks to extract (current and previous)
    start_gw = max(1, current_gw - num_gameweeks + 1)
    
    logging.info(f"📈 Updating gameweeks {start_gw} to {current_gw}")
    
    for gw in range(start_gw, current_gw + 1):
        logging.info(f"  Updating GW{gw}...")
        extract_gameweek_raw(gw)
        extract_all_manager_picks_raw(manager_ids, gw)
    
    logging.info(f"✅ Last {num_gameweeks} gameweeks updated!")


def main():
    """Run Bronze layer extraction for all data sources."""
    logging.info("🥉 Starting Bronze Layer extraction...")
    
    # Extract league data (always update - it's small)
    extract_league_raw()
    
    # Extract player data (always update - it's the master list)
    extract_players_raw()
    
    # Extract fixtures data (always update - needed for analysis)
    extract_fixtures_raw()
    
    # Check mode: full load vs incremental
    if config.INCREMENTAL_MODE:
        # Incremental: Extract only recent gameweeks
        logging.info(f"⚡ Running in INCREMENTAL mode (last {config.INCREMENTAL_GAMEWEEKS} GWs)")
        extract_recent_gameweeks(num_gameweeks=config.INCREMENTAL_GAMEWEEKS)
    else:
        # Full load: Extract all gameweeks
        logging.info("🔄 Running in FULL LOAD mode (all gameweeks)")
        extract_all_gameweeks()
    
    logging.info("🎉 Bronze Layer extraction complete!")


if __name__ == "__main__":
    main()
