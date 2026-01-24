import logging
from src.utils import fetch_data, save_csv

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Define URLs
BASE_URL            = "https://draft.premierleague.com/api"

HEADERS = [
        "manager_id",
        "id",
        "first_name",
        "last_name",
        "short_name",
        "waiver_pick",
        "team_name"
    ]


def get_league_standings(LEAGUE_ID, output_file: str = "Data/league_standings.csv"):
    """
    Fetches the league standings data, processes it, and saves it to a CSV file.
    """

    logging.info(f"Fetching league standings for League ID {LEAGUE_ID}...")

    # Build URL
    league_details_url = f"{BASE_URL}/league/{LEAGUE_ID}/details"

    data = fetch_data(league_details_url)
    if not data or "league_entries" not in data:
        logging.error(f"No league data found for league ID {LEAGUE_ID}")
        return []
    
    # Extract standings
    standings = data["league_entries"]

    
    standings_data = [
        [
            entry.get("entry_id"),
            entry.get("id"),
            entry.get("player_first_name", "").strip(),
            entry.get("player_last_name", "").strip(),
            entry.get("short_name", "").strip(),
            entry.get("waiver_pick"),
            entry.get("entry_name", "").strip()
        ]
        for entry in standings
    ]

    # Save CSV
    try:
        save_csv(output_file, HEADERS, standings_data)
        logging.info(f"✅ League standings saved to {output_file}")
    except Exception as e:
        logging.error(f"Failed to save league standings CSV: {e}")
