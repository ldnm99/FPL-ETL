"""
Modern ELT Sync Script for FPL Draft -> Supabase PostgreSQL.

Extracts raw FPL Draft API data, performs light data type normalization,
and loads records directly into Supabase PostgreSQL Star Schema tables.

Supabase PostgreSQL SQL Views automatically compute starting XIs,
points, and league standings at database engine speed.
"""

import os
import sys
import time
import json
import logging
import requests
from typing import Dict, List, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

try:
    from supabase import create_client, Client
except ImportError:
    logging.error("❌ 'supabase' package is missing. Install with: pip install supabase")
    sys.exit(1)

# API & Config Constants
FPL_DRAFT_BASE_URL = "https://draft.premierleague.com/api"
DEFAULT_LEAGUE_ID = os.getenv("FPL_LEAGUE_ID", "24636")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")

def get_supabase_client() -> Client:
    """Initialize and return Supabase Client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.error("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment variables.")
        sys.exit(1)
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_json(endpoint: str) -> Dict[str, Any]:
    """Fetch JSON payload from FPL Draft API with timeout & error handling."""
    url = f"{FPL_DRAFT_BASE_URL}{endpoint}"
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logging.warning(f"⚠️ Failed to fetch {url}: {e}")
        return {}

# ------------------------------------------------------------
# ELT Extractor & Normalizer
# ------------------------------------------------------------

def sync_bootstrap_data(supabase: Client):
    """
    Extracts bootstrap-static JSON and upserts dim_clubs, dim_players, dim_gameweeks.
    """
    logging.info("⚽ Fetching FPL Draft Bootstrap Static Data...")
    data = fetch_json("/bootstrap-static")
    if not data:
        logging.error("❌ Could not fetch bootstrap static data.")
        return

    # 1. Sync dim_clubs
    teams = data.get("teams", [])
    if teams:
        club_records = [
            {
                "id": t["id"],
                "name": t["name"],
                "short_name": t["short_name"],
                "code": t.get("code"),
                "badge_url": f"https://resources.premierleague.com/premierleague/badges/70/t{t.get('code')}.png" if t.get("code") else None
            }
            for t in teams
        ]
        supabase.table("dim_clubs").upsert(club_records).execute()
        logging.info(f"✅ Upserted {len(club_records)} clubs into 'dim_clubs'")

    # 2. Sync dim_players
    elements = data.get("elements", [])
    element_types = {t["id"]: t["singular_name_short"] for t in data.get("element_types", [])}
    if elements:
        player_records = [
            {
                "id": p["id"],
                "web_name": p["web_name"],
                "first_name": p.get("first_name", ""),
                "second_name": p.get("second_name", ""),
                "club_id": p.get("team"),
                "position_name": element_types.get(p.get("element_type"), "MID"),
                "element_type": p.get("element_type"),
                "price": float(p.get("now_cost", 0)) / 10.0 if p.get("now_cost") else 0.0
            }
            for p in elements
        ]
        supabase.table("dim_players").upsert(player_records).execute()
        logging.info(f"✅ Upserted {len(player_records)} players into 'dim_players'")

    # 3. Sync dim_gameweeks
    events = data.get("events", {}).get("data", []) or data.get("events", [])
    current_gw_id = 1
    if events and isinstance(events, list):
        # Find active GW: first unfinished gameweek
        unfinished = [e for e in events if not e.get("finished", False)]
        if unfinished:
            current_gw_id = unfinished[0]["id"]
        else:
            current_gw_id = events[-1]["id"]

        gw_records = []
        for e in events:
            is_curr = (e["id"] == current_gw_id)
            is_nxt = (e["id"] == current_gw_id + 1)
            gw_records.append({
                "id": e["id"],
                "name": e.get("name", f"Gameweek {e['id']}"),
                "deadline_time": e.get("deadline_time"),
                "is_current": is_curr,
                "is_next": is_nxt,
                "is_finished": e.get("finished", False)
            })
        supabase.table("dim_gameweeks").upsert(gw_records).execute()
        logging.info(f"✅ Upserted {len(gw_records)} gameweeks into 'dim_gameweeks' (Active GW: {current_gw_id})")
        
    return current_gw_id

def sync_fixtures(supabase: Client):
    """
    Extracts match fixtures JSON from official FPL API and upserts dim_fixtures.
    """
    logging.info("📅 Fetching Premier League Fixtures...")
    
    fixtures_url = "https://fantasy.premierleague.com/api/fixtures/"
    try:
        res = requests.get(fixtures_url, timeout=15)
        res.raise_for_status()
        fixtures_data = res.json()
    except Exception as e:
        logging.warning(f"⚠️ Could not fetch fixtures from main API: {e}")
        fixtures_data = fetch_json("/fixtures")

    if not fixtures_data or not isinstance(fixtures_data, list):
        logging.warning("⚠️ Could not fetch fixtures data.")
        return

    fixture_records = []
    for f in fixtures_data:
        fixture_records.append({
            "id": f["id"],
            "gameweek_id": f.get("event"),
            "team_h": f.get("team_h"),
            "team_a": f.get("team_a"),
            "team_h_score": f.get("team_h_score"),
            "team_a_score": f.get("team_a_score"),
            "fdr_h": f.get("team_h_difficulty"),
            "fdr_a": f.get("team_a_difficulty"),
            "kickoff_time": f.get("kickoff_time"),
            "finished": f.get("finished", False)
        })

    if fixture_records:
        supabase.table("dim_fixtures").upsert(fixture_records).execute()
        logging.info(f"✅ Upserted {len(fixture_records)} match fixtures into 'dim_fixtures'")

def sync_league_managers(supabase: Client, league_id: str = DEFAULT_LEAGUE_ID):
    """
    Extracts league details JSON, purges old managers from previous league IDs, and upserts current managers.
    """
    logging.info(f"🏆 Fetching League Details for League #{league_id}...")
    data = fetch_json(f"/league/{league_id}/details")
    entries = data.get("league_entries", [])
    
    if entries:
        active_manager_ids = [e["id"] for e in entries]
        
        # Purge legacy managers and picks not in current league ID
        try:
            logging.info(f"🧹 Purging legacy managers not in League #{league_id}...")
            existing_res = supabase.table("dim_managers").select("id").execute()
            if existing_res.data:
                existing_ids = [m["id"] for m in existing_res.data]
                stale_ids = [m_id for m_id in existing_ids if m_id not in active_manager_ids]
                for stale_id in stale_ids:
                    supabase.table("fact_manager_picks").delete().eq("manager_id", stale_id).execute()
                    supabase.table("dim_managers").delete().eq("id", stale_id).execute()
                    logging.info(f"   🗑️ Purged stale manager ID #{stale_id}")
            logging.info("✅ Legacy manager purge complete.")
        except Exception as e:
            logging.warning(f"⚠️ Notice during purge: {e}")

        manager_records = [
            {
                "id": e["id"],
                "manager_name": f"{e.get('player_first_name', '')} {e.get('player_last_name', '')}".strip() or f"Manager {e['id']}",
                "team_name": e.get("entry_name", f"Team {e['id']}"),
                "draft_pick_order": e.get("waiver_pick", e["id"])
            }
            for e in entries
        ]
        supabase.table("dim_managers").upsert(manager_records).execute()
        logging.info(f"✅ Upserted {len(manager_records)} managers into 'dim_managers'")
        return entries
    return []

def sync_manager_picks_and_performance(supabase: Client, league_entries: List[Dict[str, Any]], current_gw: int = 2):
    """
    Extracts manager picks and player performance stats for all gameweeks up to current_gw.
    """
    for gw in range(1, current_gw + 1):
        logging.info(f"📊 Fetching Manager Picks and Performance Stats for GW {gw}...")
        
        # 1. Sync Manager Picks for GW
        all_picks = []
        for entry in league_entries:
            entry_id = entry.get("entry_id") or entry.get("id")
            manager_id = entry["id"]
            
            try:
                picks_data = fetch_json(f"/entry/{entry_id}/event/{gw}")
                picks = picks_data.get("picks", [])
                
                for p in picks:
                    all_picks.append({
                        "manager_id": manager_id,
                        "gameweek_id": gw,
                        "player_id": p["element"],
                        "position": p["position"]
                    })
            except Exception as err:
                logging.warning(f"⚠️ Notice fetching picks for manager {manager_id} GW {gw}: {err}")

        if all_picks:
            supabase.table("fact_manager_picks").upsert(all_picks).execute()
            logging.info(f"✅ Upserted {len(all_picks)} manager picks into 'fact_manager_picks' for GW {gw}")

        # 2. Sync Player Performance Stats for GW
        try:
            live_data = fetch_json(f"/event/{gw}/live")
            elements_stats = live_data.get("elements", {})

            # Fetch player position map from dim_players to distinguish DEF (2) vs MID (3)
            pos_map = {}
            try:
                p_res = supabase.table("dim_players").select("id, element_type").execute()
                if p_res.data:
                    pos_map = {row["id"]: row.get("element_type", 3) for row in p_res.data}
            except Exception:
                pass
            
            perf_records = []
            for elem_id, content in elements_stats.items():
                pid = int(elem_id)
                stats = content.get("stats", {})
                cbi = stats.get("clearances_blocks_interceptions", 0)
                tackles = stats.get("tackles", 0)
                recoveries = stats.get("recoveries", 0)
                p_pos = pos_map.get(pid, 3) # 1=GKP, 2=DEF, 3=MID, 4=FWD

                def_contrib = stats.get("defensive_contribution")
                if def_contrib is not None and def_contrib > 0:
                    defcons_val = def_contrib
                elif p_pos == 2:
                    defcons_val = cbi + tackles
                elif p_pos == 3:
                    defcons_val = cbi + tackles + recoveries
                else:
                    defcons_val = 0

                perf_records.append({
                    "player_id": pid,
                    "gameweek_id": gw,
                    "total_points": stats.get("total_points", 0),
                    "goals_scored": stats.get("goals_scored", 0),
                    "assists": stats.get("assists", 0),
                    "clean_sheets": stats.get("clean_sheets", 0),
                    "goals_conceded": stats.get("goals_conceded", 0),
                    "yellow_cards": stats.get("yellow_cards", 0),
                    "red_cards": stats.get("red_cards", 0),
                    "saves": defcons_val,
                    "bonus": stats.get("bonus", 0),
                    "bps": stats.get("bps", 0),
                    "minutes": stats.get("minutes", 0)
                })

            if perf_records:
                supabase.table("fact_player_performance").upsert(perf_records).execute()
                logging.info(f"✅ Upserted {len(perf_records)} player performance records for GW {gw}")
        except Exception as err:
            logging.warning(f"⚠️ Notice fetching live stats for GW {gw}: {err}")

# ------------------------------------------------------------
# Main Execution Entry Point
# ------------------------------------------------------------
def main(full_sync: bool = False, loop_interval: int = 0):
    logging.info("==================================================")
    logging.info(f"🚀 Modern ELT Sync (Mode: {'FULL METADATA' if full_sync else 'FAST LIVE SYNC'})")
    logging.info("==================================================")

    supabase = get_supabase_client()

    while True:
        try:
            # 1. Sync Static Metadata only when requested or if tables are empty
            if full_sync:
                logging.info("📌 Full Sync Mode: Updating static metadata (Clubs, Players, Gameweeks)...")
                current_gw_id = sync_bootstrap_data(supabase) or 1
            else:
                logging.info("⚡ Fast Live Mode: Skipping static club/player tables for sub-second execution...")
                try:
                    res = supabase.table("dim_gameweeks").select("id").eq("is_current", True).limit(1).execute()
                    current_gw_id = res.data[0]["id"] if res.data else 1
                except Exception:
                    current_gw_id = 1

            # 2. Sync Fixtures, Managers & Live Performance Stats
            sync_fixtures(supabase)
            entries = sync_league_managers(supabase)
            
            if entries:
                sync_manager_picks_and_performance(supabase, entries, current_gw=current_gw_id)

            logging.info("✨ ELT Sync Complete! SQL Views (vw_draft_gameweek_overview) updated automatically.")

        except Exception as e:
            logging.error(f"❌ Error during sync cycle: {e}")

        if loop_interval <= 0:
            break

        logging.info(f"⏱️ Sleeping for {loop_interval} seconds before next live auto-sync cycle...")
        time.sleep(loop_interval)

if __name__ == "__main__":
    is_full = "--full" in sys.argv
    interval = 0
    if "--loop" in sys.argv:
        try:
            idx = sys.argv.index("--loop")
            interval = int(sys.argv[idx + 1]) if idx + 1 < len(sys.argv) else 60
        except Exception:
            interval = 60

    main(full_sync=is_full, loop_interval=interval)
