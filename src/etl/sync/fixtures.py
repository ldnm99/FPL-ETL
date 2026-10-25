"""
Fixtures and Match Window Detection Module.
Synchronizes match fixtures from official Premier League API, validates records
with Pydantic v2 schemas, and determines whether active match action is ongoing.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from src.etl.sync.client import HTTP_SESSION, fetch_json
from src.etl.schemas import FixtureIngest

logger = logging.getLogger("fpl_sync.fixtures")


def sync_fixtures(supabase, current_gw: int = None, refresh_all: bool = False) -> int:
    """
    Extracts match fixtures JSON from official FPL API, validates with FixtureIngest,
    and upserts into dim_fixtures.
    Captures live status: started, finished, finished_provisional, minutes, scores.
    Returns the count of upserted fixtures.
    """
    if refresh_all or not current_gw:
        logger.info("📅 Fetching Full Season Premier League Fixtures (380 Matches)...")
        fixtures_url = "https://fantasy.premierleague.com/api/fixtures/"
    else:
        logger.info(f"📅 Fetching Live Fixtures for Gameweek {current_gw}...")
        fixtures_url = f"https://fantasy.premierleague.com/api/fixtures/?event={current_gw}"

    try:
        res = HTTP_SESSION.get(fixtures_url, timeout=15)
        res.raise_for_status()
        fixtures_data = res.json()
    except Exception as e:
        logger.warning(f"⚠️ Could not fetch fixtures from main API: {e}")
        fixtures_data = fetch_json(f"/fixtures?event={current_gw}" if current_gw else "/fixtures")

    if not fixtures_data or not isinstance(fixtures_data, list):
        logger.warning("⚠️ Could not fetch fixtures data.")
        return 0

    validated_fixtures = []
    for f in fixtures_data:
        try:
            fix_obj = FixtureIngest(
                id=f["id"],
                gameweek_id=f.get("event"),
                team_h=f.get("team_h"),
                team_a=f.get("team_a"),
                team_h_score=f.get("team_h_score"),
                team_a_score=f.get("team_a_score"),
                fdr_h=f.get("team_h_difficulty", 3),
                fdr_a=f.get("team_a_difficulty", 3),
                kickoff_time=f.get("kickoff_time"),
                started=f.get("started", False),
                finished=f.get("finished", False),
                finished_provisional=f.get("finished_provisional", False),
                minutes=f.get("minutes", 0),
            )
            validated_fixtures.append(fix_obj.model_dump())
        except Exception as e_fix:
            logger.warning(f"⚠️ Fixture validation error for match ID {f.get('id')}: {e_fix}")

    if validated_fixtures:
        supabase.table("dim_fixtures").upsert(validated_fixtures).execute()
        logger.info(f"✅ Upserted {len(validated_fixtures)} match fixtures into 'dim_fixtures'")

    return len(validated_fixtures)


def is_fixture_window_active(supabase, current_gw: int = None) -> bool:
    """
    Detect if any Premier League match is currently live or in post-match BPS settlement:
    - started == True and finished == False (Live match in progress)
    - OR finished_provisional == True and finished == False (Opta bonus settlement window)
    - OR kickoff is within [-150m, +25m] of current UTC time and match is not finished
    """
    try:
        query = supabase.table("dim_fixtures").select("id, started, finished, finished_provisional, kickoff_time")
        if current_gw:
            query = query.eq("gameweek_id", current_gw)
        res = query.execute()
        if not res.data:
            return False

        now = datetime.now(timezone.utc)
        for f in res.data:
            started = f.get("started", False)
            finished = f.get("finished", False)
            finished_prov = f.get("finished_provisional", False)

            # 1. Live in-play
            if started and not finished:
                return True

            # 2. Post-match provisional settlement (BPS, bonus points recalculation)
            if finished_prov and not finished:
                return True

            # 3. Imminent or recently kicked off match window
            kickoff_str = f.get("kickoff_time")
            if kickoff_str and not finished:
                try:
                    ko = datetime.fromisoformat(kickoff_str.replace("Z", "+00:00"))
                    if (now - timedelta(minutes=150)) <= ko <= (now + timedelta(minutes=25)):
                        return True
                except Exception:
                    pass

        return False
    except Exception as err:
        logger.warning(f"⚠️ Error checking active fixture window: {err}")
        return False
