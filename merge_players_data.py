import logging
import os
import pandas as pd
from utils import fetch_data, fetch_managers_ids, get_player_gw_data

# ------------------ CONFIG ------------------ #
BASE_URL        = "https://draft.premierleague.com/api"
TEAMS_URL       = f"{BASE_URL}/entry/"
GAME_STATUS_URL = f"{BASE_URL}/game"

PLAYERS_CSV     = "Data/players_data.csv"
GW_FOLDER       = "Data/gameweeks_parquet"
MERGED_OUTPUT   = "Data/gw_data.parquet"
STANDINGS_CSV   = "Data/league_standings.csv"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def load_players() -> pd.DataFrame:
    """Load player IDs and names from CSV."""
    df = pd.read_csv(PLAYERS_CSV)
    df = df.astype({"ID": int})
    return df

def fetch_current_gameweek() -> int:
    """Fetch the current gameweek number from API."""
    data = fetch_data(GAME_STATUS_URL)
    if not data or "current_event" not in data:
        logging.error("Failed to fetch current gameweek.")
        return 0
    return data["current_event"]

def fetch_manager_picks(manager_id: int, gw: int) -> pd.DataFrame:
    """Fetch a managers team picks for a given gameweek."""
    url = f"{TEAMS_URL}/{manager_id}/event/{gw}"
    data = fetch_data(url)
    if not data or "picks" not in data:
        return pd.DataFrame()

    picks = pd.DataFrame(data["picks"])
    picks.rename(columns={"element": "ID", "position": "team_position"}, inplace=True)
    picks["manager_id"] = manager_id
    picks["gameweek"] = gw
    return picks[["ID", "manager_id", "gameweek", "team_position"]]

def build_gameweek_data(gw: int, managers: list[int], players_df: pd.DataFrame) -> pd.DataFrame:
    """Build a single gameweek DataFrame."""
    logging.info(f"Processing Gameweek {gw}...")

    gw_stats = get_player_gw_data(gw)
    if gw_stats.empty:
        logging.warning(f"No player stats found for GW{gw}")
        return pd.DataFrame()

    gw_stats.rename(columns={"id": "ID"}, inplace=True)
    gw_stats["gameweek"] = gw
    gw_stats = gw_stats.merge(players_df, on="ID", how="left")

    # Collect all manager picks for the GW
    picks = [fetch_manager_picks(mid, gw) for mid in managers]
    picks = [p for p in picks if not p.empty]

    if picks:
        picks_df = pd.concat(picks, ignore_index=True)
        gw_stats = gw_stats.merge(picks_df, on=["ID", "gameweek"], how="left")
        gw_stats["team_id"] = gw_stats["manager_id"]

    return gw_stats

def save_gameweek(gw_df: pd.DataFrame, gw: int, standings_csv="Data/league_standings.csv"):
    """Save a single gameweek file."""
    os.makedirs(GW_FOLDER, exist_ok=True)
    output_path = f"{GW_FOLDER}/gw_data_gw{gw}.parquet"

    # ✅ Read the CSV first
    standings_df = pd.read_csv(standings_csv)

    # Merge team names
    gw_df = gw_df.merge(
        standings_df[['manager_id', 'team_name']],
        left_on='team_id',
        right_on='manager_id',
        how='left'
    )
    
    gw_df.to_parquet(output_path, index=False, engine="pyarrow")
    logging.info(f"✅ Saved Gameweek {gw} as Parquet: {output_path}")

def merge_all_gameweeks():
    """Combine all GW CSVs into one big file."""
    files = sorted([f for f in os.listdir(GW_FOLDER) if f.startswith("gw_data_gw") and f.endswith(".parquet")])
    if not files:
        logging.warning("No gameweek Parquet files found to merge.")
        return

    dfs = [pd.read_parquet(os.path.join(GW_FOLDER, f)) for f in files]
    merged_df = pd.concat(dfs, ignore_index=True)
    merged_df = rename_columns(merged_df)
    merged_df.to_parquet(MERGED_OUTPUT, index=False, engine="pyarrow")
    logging.info(f"📦 Merged all gameweeks into {MERGED_OUTPUT}")

def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    # --- Step 1: Rename columns ---
    rename_map = {
        "minutes_x": "gw_minutes",
        "goals_scored_x": "gw_goals",
        "assists_x": "gw_assists",
        "clean_sheets": "gw_clean_sheets",
        "goals_conceded": "gw_goals_conceded",
        "bps_x": "gw_bps",
        "bonus_x": "gw_bonus",
        "ict_index_x": "gw_ict_index",
        "total_points_x": "gw_points",
        "in_dreamteam": "gw_in_dreamteam",
        "expected_goals": "gw_expected_goals",
        "expected_assists_x": "gw_expected_assists",
        "expected_goal_involvements_x": "gw_expected_goal_involvements",
        "expected_goals_conceded": "gw_expected_goals_conceded",
        "own_goals_x": "gw_own_goals",
        "penalties_saved_x": "gw_penalties_saved",
        "penalties_missed_x": "gw_penalties_missed",
        "yellow_cards_x": "gw_yellow_cards",
        "red_cards_x": "gw_red_cards",
        "saves_x": "gw_saves",
        "influence_x": "gw_influence",
        "creativity_x": "gw_creativity",
        "threat_x": "gw_threat",
        "starts_x": "gw_starts",
        "clearances_blocks_interceptions_x": "gw_clearances_blocks_interceptions",
        "recoveries_x": "gw_recoveries",
        "tackles_x": "gw_tackles",
        "defensive_contribution_x": "gw_defensive_contribution",
    
        # --- Season stats ---
        "minutes_y": "season_minutes",
        "goals_scored_y": "season_goals",
        "assists_y": "season_assists",
        "bps_y": "season_bps",
        "bonus_y": "season_bonus",
        "ict_index_y": "season_ict_index",
        "total_points_y": "season_points",
        "xG": "season_expected_goals",
        "xGc": "season_expected_goals_conceded",
        "CS": "season_clean_sheets",
        "Gc": "season_goals_conceded",
        "own_goals_y": "season_own_goals",
        "penalties_saved_y": "season_penalties_saved",
        "penalties_missed_y": "season_penalties_missed",
        "yellow_cards_y": "season_yellow_cards",
        "red_cards_y": "season_red_cards",
        "saves_y": "season_saves",
        "influence_y": "season_influence",
        "creativity_y": "season_creativity",
        "threat_y": "season_threat",
        "starts_y": "season_starts",
        "expected_assists_y": "season_expected_assists",
        "expected_goal_involvements_y": "season_expected_goal_involvements",
        "clearances_blocks_interceptions_y": "season_clearances_blocks_interceptions",
        "recoveries_y": "season_recoveries",
        "tackles_y": "season_tackles",
        "defensive_contribution_y": "season_defensive_contribution",
    
        # --- Identifiers ---
        "ID": "player_id",
        "team_id": "manager_team_id",
        "team_name": "manager_team_name",
        "manager_id_x": "manager_id",
        "manager_id_y": "manager_id",
        "web_name": "short_name",
        "name": "full_name",
        "team": "real_team",
        "gameweek": "gw",
    }

    df = df.rename(columns=rename_map)
    # --- Step 2: Remove duplicated columns ---
    # Drop duplicated manager_id or repeated metrics if both versions exist
    df = df.loc[:, ~df.columns.duplicated()]

    return df

def main():
    logging.info("🏁 Starting incremental FPL gameweek data extraction...")

    current_gw = fetch_current_gameweek()
    if current_gw == 0:
        logging.error("Aborting: could not fetch current gameweek.")
        return

    managers = fetch_managers_ids()
    if not managers:
        logging.error("Aborting: no manager IDs found.")
        return

    players_df = load_players()

    # Identify already processed GWs
    os.makedirs(GW_FOLDER, exist_ok=True)
    existing_gws = {
        int(f.split("gw")[-1].split(".")[0])
        for f in os.listdir(GW_FOLDER)
        if f.startswith("gw_data_gw")
    }

    logging.info(f"Already have data for GWs: {sorted(existing_gws)}")

    # Update the current gameweek and the last already processed gameweek (if any)
    to_update = set()
    if existing_gws:
        last_processed_gw = max(existing_gws)
        if last_processed_gw != current_gw:
            to_update.add(last_processed_gw)
    to_update.add(current_gw)
    for gw in sorted(to_update):
        gw_df = build_gameweek_data(gw, managers, players_df)
        if not gw_df.empty:
            save_gameweek(gw_df, gw)
            logging.info(f"Saved Gameweek {gw}")
        else:
            logging.warning(f"No data for Gameweek {gw}")

    # Rebuild master dataset
    merge_all_gameweeks()

    logging.info("🏁 Incremental data extraction completed successfully.")