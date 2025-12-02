import os
import csv
import logging
import sqlite3
import pandas as pd
import requests
import time
from typing import List, Any, Optional

# Database file (used by fetch_players_data)
DB_FILE = "fpl_data.db"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Session for re-use
session = requests.Session()


# Database file
DB_FILE = "fpl_data.db"
# Define URLs
BASE_URL        = "https://draft.premierleague.com/api"

#Player data from the gameweek endpoint
GW_URL      = f"{BASE_URL}/event/"

session = requests.session()

# ------------------ API HELPERS ------------------ #
def fetch_data(url: str, retries: int = 3, delay: int = 2, timeout: int = 10) -> Optional[dict]:
    """
    Fetch JSON data from a given URL with retries and error handling.

    Args:
        url (str): The API endpoint to fetch.
        retries (int): Number of retry attempts if request fails.
        delay (int): Delay (seconds) between retries.
        timeout (int): Timeout (seconds) for each request.

    Returns:
        dict | None: JSON response if successful, else None.
    """
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.warning(f"Attempt {attempt}/{retries} failed for {url}: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                logging.error(f"❌ Failed to fetch data from {url} after {retries} attempts.")
                return None
    
# ------------------ FILE HELPERS ------------------ #
def save_csv(filename: str, headers: List[str], rows: List[List[Any]]):
    """
    Save tabular data to a CSV file.

    Args:
        filename (str): Path to save the CSV file.
        headers (list): Column headers.
        rows (list): Row data.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    try:
        with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerows(rows)
        logging.info(f"✅ Saved CSV: {filename}")
    except Exception as e:
        logging.error(f"Failed to save CSV {filename}: {e}")

def load_csv(filename: str) -> pd.DataFrame:
    """
    Load a CSV file into a Pandas DataFrame.

    Args:
        filename (str): Path to CSV file.

    Returns:
        pd.DataFrame: Loaded data.
    """
    if not os.path.exists(filename):
        logging.error(f"CSV file not found: {filename}")
        return pd.DataFrame()
    return pd.read_csv(filename)

# ------------------ LEAGUE HELPERS ------------------ #
def fetch_managers_ids(csv_path: str = "Data/league_standings.csv") -> List[int]:
    """
    Fetch the list of manager IDs from the league standings CSV.

    Args:
        csv_path (str): Path to league standings CSV.

    Returns:
        list[int]: Unique manager IDs.
    """
    df = load_csv(csv_path)
    if df.empty or "manager_id" not in df.columns:
        logging.error("No manager IDs found in league_standings.csv")
        return []
    return df["manager_id"].dropna().unique().tolist()
    
# ------------------ DATABASE HELPERS ------------------ #
def fetch_players_data() -> pd.DataFrame:
    """
    Fetch player data from the players_data table in SQLite DB.

    Returns:
        pd.DataFrame: Players data.
    """
    if not os.path.exists(DB_FILE):
        logging.error(f"Database file not found: {DB_FILE}")
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM players_data", conn)
        conn.close()
        return df
    except Exception as e:
        logging.error(f"Error reading from database: {e}")
        return pd.DataFrame()

# ------------------ GAMEWEEK HELPERS ------------------ #
def get_player_gw_data(gameweek: int, base_url: str = "https://draft.premierleague.com/api") -> pd.DataFrame:
    """
    Fetch all player stats for a given gameweek.

    Args:
        gameweek (int): Gameweek number.
        base_url (str): Base API URL.

    Returns:
        pd.DataFrame: Gameweek player stats.
    """
    gw_url = f"{base_url}/event/{gameweek}/live"
    data = fetch_data(gw_url)

    if not data or "elements" not in data:
        logging.warning(f"No gameweek data found for GW{gameweek}")
        return pd.DataFrame()

    records = []
    for player_id, value in data["elements"].items():
        stats = value.get("stats", {})
        stats["id"] = int(player_id)
        stats["gameweek"] = int(gameweek)
        records.append(stats)

    return pd.DataFrame(records)