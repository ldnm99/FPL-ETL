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
        raise RuntimeError(f"Failed to fetch league data for league ID {config.LEAGUE_ID}")

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
        raise RuntimeError("Failed to fetch player data from bootstrap-static")

    # Save raw JSON to Bronze layer
    save_raw_json(data, config.BRONZE_PLAYERS_RAW)
    logging.info(f"✅ Bronze: Player raw data saved")

    return data


def extract_fixtures_raw(force: bool = False) -> List[Dict[Any, Any]]:
    """
    Extract raw fixtures data from bootstrap-static endpoint.
    The Draft API includes fixtures in the bootstrap-static response.

    Fixtures are static for the season. This function skips the API call
    if the file already exists unless force=True.

    Args:
        force: If True, re-fetch even if the file already exists.

    Returns:
        List of fixture dicts
    """
    fixtures_path = os.path.join(config.BRONZE_DIR, "fixtures_raw.json")

    if not force and os.path.exists(fixtures_path):
        logging.info("⏭️ Fixtures already fetched — skipping (pass force=True to refresh)")
        return []

    logging.info("🏟️ Extracting fixtures from bootstrap-static...")
    
    if not os.path.exists(config.BRONZE_PLAYERS_RAW):
        raise RuntimeError(
            f"Bootstrap-static not found at {config.BRONZE_PLAYERS_RAW}. "
            "Run extract_players_raw() first."
        )
    
    with open(config.BRONZE_PLAYERS_RAW, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    if not raw_data or 'fixtures' not in raw_data:
        raise RuntimeError("No fixtures data found in bootstrap-static response.")
    
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


def _load_manager_ids() -> List[int]:
    """
    Load manager IDs from the Bronze league file.
    Fetches league data first if the file doesn't exist yet.

    Returns:
        List of manager entry IDs.
    """
    if not os.path.exists(config.BRONZE_LEAGUE_RAW):
        logging.warning("⚠️ League data not found, extracting first...")
        extract_league_raw()

    if not os.path.exists(config.BRONZE_LEAGUE_RAW):
        raise RuntimeError(
            f"League raw file still missing after extraction attempt: {config.BRONZE_LEAGUE_RAW}"
        )

    with open(config.BRONZE_LEAGUE_RAW, 'r') as f:
        league_data = json.load(f)
    return [entry['entry_id'] for entry in league_data.get('league_entries', [])]


def extract_all_gameweeks():
    """
    Extract ALL gameweeks from GW1 to current (full historical load).
    Use this for initial data load.
    """
    logging.info(f"🔄 Extracting ALL gameweeks (full load)...")

    current_gw = get_current_gameweek()
    logging.info(f"📅 Current gameweek: {current_gw}")

    manager_ids = _load_manager_ids()

    logging.info(f"📈 Extracting gameweeks 1 to {current_gw}")

    for gw in range(1, current_gw + 1):
        logging.info(f"  Extracting GW{gw}...")
        try:
            extract_gameweek_raw(gw)
            extract_all_manager_picks_raw(manager_ids, gw)
        except Exception as e:
            logging.error(f"❌ Failed to extract GW{gw}: {e} — skipping")

    logging.info(f"✅ All {current_gw} gameweeks extracted!")


def extract_recent_gameweeks(num_gameweeks: int = 2):
    """
    Extract only the most recent gameweeks (incremental update).
    This is more efficient than re-extracting all historical data.

    Args:
        num_gameweeks: Number of recent gameweeks to update (default: 2)
    """
    logging.info(f"🔄 Extracting last {num_gameweeks} gameweeks (incremental update)...")

    current_gw = get_current_gameweek()
    logging.info(f"📅 Current gameweek: {current_gw}")

    manager_ids = _load_manager_ids()

    start_gw = max(1, current_gw - num_gameweeks + 1)
    logging.info(f"📈 Updating gameweeks {start_gw} to {current_gw}")

    for gw in range(start_gw, current_gw + 1):
        logging.info(f"  Updating GW{gw}...")
        try:
            extract_gameweek_raw(gw)
            extract_all_manager_picks_raw(manager_ids, gw)
        except Exception as e:
            logging.error(f"❌ Failed to update GW{gw}: {e} — skipping")

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
