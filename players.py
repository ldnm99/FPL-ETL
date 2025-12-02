import logging
import pandas as pd
from utils import fetch_data

# Define URLs
BASE_URL            = "https://draft.premierleague.com/api"
PLAYER_DATA_URL     = f"{BASE_URL}/bootstrap-static"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

HEADERS_DROP = ["first_name", "second_name",'influence_rank',
       'influence_rank_type', 'creativity_rank', 'creativity_rank_type',
       'threat_rank', 'threat_rank_type', 'ict_index_rank',
       'ict_index_rank_type', 'form_rank', 'form_rank_type',
       'points_per_game_rank', 'points_per_game_rank_type',
       'corners_and_indirect_freekicks_order',
       'corners_and_indirect_freekicks_text', 'direct_freekicks_order',
       'direct_freekicks_text', 'penalties_order', 'penalties_text', 'status',"points_per_game",'in_dreamteam',
       'ep_this','ep_next','dreamteam_count','draft_rank']

# Map team numbers to names
TEAMS_MAP = {
        1: "Arsenal", 2: "Aston Villa", 3: "Burnley", 4: "Bournemouth",
        5: "Brentford", 6: "Brighton", 7: "Chelsea", 8: "Crystal Palace",
        9: "Everton", 10: "Fulham", 11: "Leeds United", 12: "Liverpool",
        13: "Manchester City", 14: "Manchester United", 15: "Newcastle United",
        16: "Nottingham Forest", 17: "Sunderland", 18: "Tottenham",
        19: "West Ham", 20: "Wolverhampton"
    }

POSITION_ORDER = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}

#Gets all the players data and saves into a CSV file called players_data.csv in data folder
def get_player_data(output_file: str = "Data/players_data.csv"):
    """
    Fetches player data, processes it, and saves it to a CSV file.
    This function performs the following steps:
    1. Fetches player data from a specified URL.
    2. Extracts relevant fields from the player data.
    3. Saves the processed player data to a CSV file.
    4. Returns the player data as a pandas DataFrame.
    Returns:
        pd.DataFrame: A DataFrame containing player data with columns:
                      ['ID', 'First_Name', 'Last_Name', 'Team', 'Position', 'Assists', 'bonus', 'Total points',
                       'xA', 'CS', 'Gc', 'Goals Scored', 'minutes', 'red_cards', 'starts', 'xG',
                       'xGi','xGc','code','PpG']
    """

    data = fetch_data(PLAYER_DATA_URL)
    if not data or "elements" not in data:
        logging.error("No player data retrieved from API.")
        return []
    
    players = data["elements"]

    # Convert list of dicts to DataFrame (includes all fields)
    df = pd.DataFrame(players)
    
    # Merge first_name and second_name into name and drop the original columns
    df["name"] = df["first_name"] + " " + df["second_name"]
    df.drop(HEADERS_DROP, axis=1, inplace=True)
    df = df.rename(columns={"id": "ID",
                            "element_type":   "position",
                            "assists":        "assists", 
                            "total_points":   "total_points",
                            "clean_sheets":   "CS", 
                            "goals_conceded": "Gc",
                            "goals_scored":   "goals_scored",
                            "expected_goals": "xG", 
                            "expected_involvements":   "xGi", 
                            "expected_goals_conceded": "xGc",
                            "code": "code",
                            })

    df["team"]     = df["team"].map(TEAMS_MAP)
    df['position'] = df['position'].map(POSITION_ORDER)

    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    logging.info(f"✅ Full player dataset saved to {output_file}")
        
