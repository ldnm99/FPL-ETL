"""
Bootstrap Static Dimension Sync Module.
Extracts clubs, players, and gameweeks from FPL Draft API, validates records
with Pydantic v2 schemas, and upserts into Supabase PostgreSQL.
"""
import logging
from typing import Optional, List, Dict, Any
from src.etl.sync.client import fetch_json
from src.etl.schemas import ClubIngest, PlayerIngest, GameweekIngest

logger = logging.getLogger("fpl_sync.bootstrap")


def sync_bootstrap_data(supabase) -> int:
    """
    Extracts bootstrap-static JSON, validates via Pydantic,
    and upserts dim_clubs, dim_players, and dim_gameweeks.
    Returns the detected active gameweek ID.
    """
    logger.info("⚽ Fetching FPL Draft Bootstrap Static Data...")
    data = fetch_json("/bootstrap-static")
    if not data:
        logger.error("❌ Could not fetch bootstrap static data.")
        return 1

    # 1. Sync dim_clubs
    teams = data.get("teams", [])
    if teams:
        validated_clubs = []
        for t in teams:
            try:
                badge = f"https://resources.premierleague.com/premierleague/badges/70/t{t.get('code')}.png" if t.get("code") else None
                club_obj = ClubIngest(
                    id=t["id"],
                    name=t["name"],
                    short_name=t["short_name"],
                    code=t.get("code"),
                    badge_url=badge
                )
                validated_clubs.append(club_obj.model_dump())
            except Exception as e_club:
                logger.warning(f"⚠️ Club validation error for {t.get('name')}: {e_club}")

        if validated_clubs:
            supabase.table("dim_clubs").upsert(validated_clubs).execute()
            logger.info(f"✅ Upserted {len(validated_clubs)} clubs into 'dim_clubs'")

    # 2. Sync dim_players
    elements = data.get("elements", [])
    element_types = {t["id"]: t["singular_name_short"] for t in data.get("element_types", [])}
    if elements:
        validated_players = []
        for p in elements:
            try:
                pos_short = element_types.get(p.get("element_type"), "MID")
                code_val = p.get("code")
                photo_str = f"{code_val}.jpg" if code_val else None
                photo_code_str = str(code_val) if code_val else None
                player_obj = PlayerIngest(
                    id=p["id"],
                    web_name=p["web_name"],
                    first_name=p.get("first_name", ""),
                    second_name=p.get("second_name", ""),
                    club_id=p.get("team"),
                    position_name=pos_short,
                    element_type=p.get("element_type", 3),
                    price=price_val,
                    photo=photo_str,
                    photo_code=photo_code_str,
                )
                validated_players.append(player_obj.model_dump())
            except Exception as e_pl:
                logger.warning(f"⚠️ Player validation error for {p.get('web_name')}: {e_pl}")

        if validated_players:
            supabase.table("dim_players").upsert(validated_players).execute()
            logger.info(f"✅ Upserted {len(validated_players)} players into 'dim_players'")

    # 3. Sync dim_gameweeks
    events = data.get("events", {}).get("data", []) or data.get("events", [])
    current_gw_id = 1
    if events and isinstance(events, list):
        unfinished = [e for e in events if not e.get("finished", False)]
        if unfinished:
            current_gw_id = unfinished[0]["id"]
        else:
            current_gw_id = events[-1]["id"]

        validated_gws = []
        for e in events:
            try:
                gw_obj = GameweekIngest(
                    id=e["id"],
                    name=e.get("name", f"Gameweek {e['id']}"),
                    deadline_time=e.get("deadline_time"),
                    is_current=(e["id"] == current_gw_id),
                    is_next=(e["id"] == current_gw_id + 1),
                    is_finished=e.get("finished", False)
                )
                validated_gws.append(gw_obj.model_dump())
            except Exception as e_gw:
                logger.warning(f"⚠️ Gameweek validation error for event {e.get('id')}: {e_gw}")

        if validated_gws:
            supabase.table("dim_gameweeks").upsert(validated_gws).execute()
            logger.info(f"✅ Upserted {len(validated_gws)} gameweeks into 'dim_gameweeks' (Active GW: {current_gw_id})")

    return current_gw_id
