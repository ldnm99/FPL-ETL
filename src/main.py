import os
import logging
import sys

# Add parent directory to path for relative imports
sys.path.insert(0, os.path.dirname(__file__))

from etl import merge_players_data
from etl.league import get_league_standings
from etl.players import get_player_data
from etl import upload_database

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Constants
LEAGUE_ID = os.environ.get("FPL_LEAGUE_ID", "24636")
BASE_URL = "https://draft.premierleague.com/api"

LEAGUE_DETAILS_URL = f"{BASE_URL}/league/{LEAGUE_ID}/details"
TEAMS_URL          = f"{BASE_URL}/entry/"
GAME_STATUS_URL    = f"{BASE_URL}/game"
GW_URL             = f"{BASE_URL}/event/"
PLAYER_DATA_URL    = f"{BASE_URL}/bootstrap-static"

def run_pipeline():
    logging.info("🚀 Starting FPL Draft data extraction pipeline...")

    # Ensure data folder exists
    os.makedirs("Data", exist_ok=True)

    logging.info("📊 Fetching league standings...")
    get_league_standings(LEAGUE_ID, output_file="Data/league_standings.csv")

    logging.info("🧍 Fetching player data...")
    get_player_data(output_file="Data/players_data.csv")

    logging.info("🔄 Running data merging...")
    merge_players_data.main()

    logging.info("⬆️ Uploading data to Supabase...")
    upload_database.main()

    logging.info("🎉 Pipeline completed successfully!")

if __name__ == "__main__":
    run_pipeline()
