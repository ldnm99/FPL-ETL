"""
League Managers Sync and Legacy Purge Module.
Extracts draft league manager details, purges stale managers from previous league IDs,
validates with Pydantic v2 ManagerIngest, and upserts into Supabase dim_managers.
"""
import logging
from typing import List, Dict, Any
from src.etl.sync.client import fetch_json, DEFAULT_LEAGUE_ID
from src.etl.schemas import ManagerIngest

logger = logging.getLogger("fpl_sync.managers")


def sync_league_managers(supabase, league_id: str = DEFAULT_LEAGUE_ID) -> List[Dict[str, Any]]:
    """
    Extracts league details JSON, purges old managers from previous league IDs,
    validates active managers via ManagerIngest, and upserts current managers.
    Returns list of active league entry dictionaries.
    """
    logger.info(f"🏆 Fetching League Details for League #{league_id}...")
    data = fetch_json(f"/league/{league_id}/details")
    entries = data.get("league_entries", [])

    if not entries:
        logger.warning(f"⚠️ No league entries found for League #{league_id}.")
        return []

    active_manager_ids = [e["id"] for e in entries]

    # Purge legacy managers and picks not in current league ID
    try:
        logger.info(f"🧹 Purging legacy managers not in League #{league_id}...")
        existing_res = supabase.table("dim_managers").select("id").execute()
        if existing_res.data:
            existing_ids = [m["id"] for m in existing_res.data]
            stale_ids = [m_id for m_id in existing_ids if m_id not in active_manager_ids]
            for stale_id in stale_ids:
                supabase.table("fact_manager_picks").delete().eq("manager_id", stale_id).execute()
                supabase.table("dim_managers").delete().eq("id", stale_id).execute()
                logger.info(f"   🗑️ Purged stale manager ID #{stale_id}")
        logger.info("✅ Legacy manager purge complete.")
    except Exception as e:
        logger.warning(f"⚠️ Notice during manager purge: {e}")

    # Validate with Pydantic
    validated_managers = []
    for e in entries:
        try:
            full_name = f"{e.get('player_first_name', '')} {e.get('player_last_name', '')}".strip() or f"Manager {e['id']}"
            team_title = e.get("entry_name", f"Team {e['id']}")
            draft_order = e.get("waiver_pick", e["id"])
            mgr_obj = ManagerIngest(
                id=e["id"],
                manager_name=full_name,
                team_name=team_title,
                draft_pick_order=draft_order
            )
            validated_managers.append(mgr_obj.model_dump())
        except Exception as e_mgr:
            logger.warning(f"⚠️ Manager validation error for ID {e.get('id')}: {e_mgr}")

    if validated_managers:
        supabase.table("dim_managers").upsert(validated_managers).execute()
        logger.info(f"✅ Upserted {len(validated_managers)} managers into 'dim_managers'")

    return entries
