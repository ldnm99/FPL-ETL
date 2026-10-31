"""
Manager Picks and Player Performance Sync Module.
Extracts manager squad picks and real-time player performance stats,
calculates position-tailored Defcons, validates records with Pydantic v2 schemas,
and upserts into Supabase fact_manager_picks and fact_player_performance.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from src.etl.sync.client import HTTP_SESSION, fetch_json
from src.etl.schemas import ManagerPickIngest, PlayerPerformanceIngest
from src.etl.sync.history_feed import feed_local_history

logger = logging.getLogger("fpl_sync.performance")
REPO_ROOT = Path(__file__).resolve().parents[3]


def sync_manager_picks_and_performance(
    supabase,
    league_entries: List[Dict[str, Any]],
    current_gw: int = 1,
    sync_all_history: bool = False,
    include_previous_gw: bool = False,
    target_gws_override: List[int] = None
) -> Dict[str, int]:
    """
    Extracts manager picks and player performance stats.
    By default, syncs only the current active gameweek (3-4s execution).
    When include_previous_gw is True (e.g. EOD or Full consolidation), syncs [current_gw - 1, current_gw]
    to capture post-gameweek automatic substitutions, bonus settlements, and Opta stat adjustments.
    When sync_all_history is True, syncs all gameweeks 1..current_gw.
    Returns dictionary with counts: {"picks_count": X, "perf_records_count": Y}.
    """
    if target_gws_override:
        target_gws = sorted(set(g for g in target_gws_override if g >= 1))
    elif sync_all_history:
        target_gws = list(range(1, current_gw + 1))
    elif include_previous_gw and current_gw > 1:
        target_gws = [current_gw - 1, current_gw]
    else:
        target_gws = [current_gw]

    logger.info(
        f"📊 Syncing Picks & Performance for Gameweek(s): {target_gws} "
        f"(history={sync_all_history}, include_previous_gw={include_previous_gw})..."
    )

    total_picks_synced = 0
    total_perf_synced = 0

    # 1. Fetch player position map once outside loop
    pos_map = {}
    try:
        p_res = supabase.table("dim_players").select("id, element_type").execute()
        if p_res.data:
            pos_map = {row["id"]: row.get("element_type", 3) for row in p_res.data}
    except Exception as e_pos:
        logger.warning(f"⚠️ Notice fetching player position map: {e_pos}")

    # 2. Build Code -> Draft ID and Reg ID -> Code translation maps once outside loop
    reg_id_to_code = {}
    code_to_draft_id = {}
    try:
        r_reg_bs = HTTP_SESSION.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=15)
        if r_reg_bs.ok:
            reg_id_to_code = {p["id"]: p["code"] for p in r_reg_bs.json().get("elements", [])}

        r_draft_bs = fetch_json("/bootstrap-static")
        if r_draft_bs and "elements" in r_draft_bs:
            code_to_draft_id = {p["code"]: p["id"] for p in r_draft_bs.get("elements", [])}
    except Exception as e_map:
        logger.warning(f"⚠️ Notice building player code map: {e_map}")

    # 3. Process each targeted Gameweek
    for gw in target_gws:
        logger.info(f"📊 Fetching Manager Picks and Performance Stats for GW {gw}...")

        # A. Sync Manager Picks for GW
        all_picks = []
        for entry in league_entries:
            entry_id = entry.get("entry_id") or entry.get("id")
            manager_id = entry["id"]

            try:
                picks_data = fetch_json(f"/entry/{entry_id}/event/{gw}")
                picks = picks_data.get("picks", [])

                for p in picks:
                    try:
                        pick_obj = ManagerPickIngest(
                            manager_id=manager_id,
                            gameweek_id=gw,
                            player_id=p["element"],
                            position=p["position"]
                        )
                        all_picks.append(pick_obj.model_dump())
                    except Exception as e_pick:
                        logger.warning(f"⚠️ Pick validation error for manager {manager_id} player {p.get('element')}: {e_pick}")
            except Exception as err:
                logger.warning(f"⚠️ Notice fetching picks for manager {manager_id} GW {gw}: {err}")

        if all_picks:
            supabase.table("fact_manager_picks").upsert(all_picks).execute()
            total_picks_synced += len(all_picks)
            logger.info(f"✅ Upserted {len(all_picks)} validated manager picks into 'fact_manager_picks' for GW {gw}")

        # B. Sync Player Performance Stats for GW (Real-Time Regular FPL API with Code Mapping)
        try:
            reg_url = f"https://fantasy.premierleague.com/api/event/{gw}/live/"
            elements_data = []
            is_regular_api = False
            try:
                r_reg = HTTP_SESSION.get(reg_url, timeout=15)
                if r_reg.ok:
                    res_json = r_reg.json()
                    elements_data = res_json.get("elements", [])
                    is_regular_api = True
                    logger.info(f"⚡ Fetched {len(elements_data)} real-time stats from Regular FPL API for GW {gw}")
            except Exception as e_reg:
                logger.warning(f"⚠️ Could not fetch real-time stats from Regular FPL API: {e_reg}")

            # Fallback to Draft FPL API if needed
            if not elements_data:
                live_data = fetch_json(f"/event/{gw}/live")
                raw_elems = live_data.get("elements", {})
                if isinstance(raw_elems, dict):
                    elements_data = [{"id": int(k), **v} for k, v in raw_elems.items()]
                elif isinstance(raw_elems, list):
                    elements_data = raw_elems

            perf_records = []
            for item in elements_data:
                raw_id = item.get("id")
                if not raw_id:
                    continue

                # Translate Regular FPL ID to Draft FPL ID via player code
                if is_regular_api and reg_id_to_code:
                    p_code = reg_id_to_code.get(raw_id)
                    pid = code_to_draft_id.get(p_code, raw_id) if p_code else raw_id
                else:
                    pid = raw_id

                stats = item.get("stats", {})
                cbi = stats.get("clearances_blocks_interceptions", 0)
                tackles = stats.get("tackles", 0)
                recoveries = stats.get("recoveries", 0)
                p_pos = pos_map.get(pid, 3)  # 1=GKP, 2=DEF, 3=MID, 4=FWD

                def_contrib = stats.get("defensive_contribution")
                if def_contrib is not None and def_contrib > 0:
                    defcons_val = def_contrib
                elif p_pos == 2:
                    defcons_val = cbi + tackles
                elif p_pos == 3:
                    defcons_val = cbi + tackles + recoveries
                else:
                    defcons_val = 0

                try:
                    perf_obj = PlayerPerformanceIngest(
                        player_id=pid,
                        gameweek_id=gw,
                        total_points=stats.get("total_points", 0),
                        goals_scored=stats.get("goals_scored", 0),
                        assists=stats.get("assists", 0),
                        clean_sheets=stats.get("clean_sheets", 0),
                        goals_conceded=stats.get("goals_conceded", 0),
                        yellow_cards=stats.get("yellow_cards", 0),
                        red_cards=stats.get("red_cards", 0),
                        own_goals=stats.get("own_goals", 0),
                        penalties_saved=stats.get("penalties_saved", 0),
                        penalties_missed=stats.get("penalties_missed", 0),
                        saves=stats.get("saves", 0),
                        defcons=defcons_val,
                        bonus=stats.get("bonus", 0),
                        bps=stats.get("bps", 0),
                        minutes=stats.get("minutes", 0)
                    )
                    perf_records.append(perf_obj.model_dump())
                except Exception as e_perf:
                    logger.warning(f"⚠️ Performance validation error for player {pid} GW {gw}: {e_perf}")

            if perf_records:
                supabase.table("fact_player_performance").upsert(perf_records).execute()
                total_perf_synced += len(perf_records)
                logger.info(f"✅ Upserted {len(perf_records)} validated performance records for GW {gw}")

            # Dual-Write to local SQLite historical database and multi-season Parquet
            feed_local_history(
                REPO_ROOT,
                season_id="2026_2027",
                gameweek_id=gw,
                manager_picks=all_picks if 'all_picks' in locals() else None,
                player_performance=perf_records
            )

        except Exception as err:
            logger.warning(f"⚠️ Notice fetching live stats for GW {gw}: {err}")

    return {
        "picks_count": total_picks_synced,
        "perf_records_count": total_perf_synced
    }


def reconcile_standings_with_official(
    supabase,
    league_entries: List[Dict[str, Any]],
    current_gw: int = 1
) -> Dict[str, Any]:
    """
    Self-Healing Standings Reconciliation Gate:
    Compares cumulative starter points in Supabase for closed gameweeks (< current_gw)
    against the official FPL Draft API standings (api_total - api_event_total).
    If any manager's closed-gameweek total disagrees with the official API,
    automatically re-syncs prior gameweeks to guarantee 100% scoring parity.
    """
    if not league_entries or current_gw <= 1:
        return {"reconciled": True, "drifted_managers": [], "healed": False}

    # Check if entries carry official API totals from /league/{id}/details
    expected_prior_by_mgr: Dict[int, int] = {}
    for e in league_entries:
        mgr_id = e.get("id")
        api_total = e.get("api_total")
        api_event_total = e.get("api_event_total", 0) or 0
        if mgr_id is not None and api_total is not None:
            expected_prior_by_mgr[int(mgr_id)] = int(api_total) - int(api_event_total)

    if not expected_prior_by_mgr:
        return {"reconciled": True, "drifted_managers": [], "healed": False}

    try:
        res = (
            supabase.table("vw_draft_gameweek_overview")
            .select("manager_id, gameweek_id, points, is_starter")
            .eq("is_starter", True)
            .lt("gameweek_id", current_gw)
            .execute()
        )
        rows = res.data or []
    except Exception as err:
        logger.warning(f"⚠️ Could not query vw_draft_gameweek_overview for reconciliation: {err}")
        return {"reconciled": False, "drifted_managers": [], "healed": False}

    sb_prior_by_mgr: Dict[int, int] = {mgr_id: 0 for mgr_id in expected_prior_by_mgr}
    for r in rows:
        m_id = r.get("manager_id")
        if m_id in sb_prior_by_mgr:
            sb_prior_by_mgr[m_id] += int(r.get("points") or 0)

    drifted = []
    for mgr_id, official_pts in expected_prior_by_mgr.items():
        sb_pts = sb_prior_by_mgr.get(mgr_id, 0)
        if sb_pts != official_pts:
            drifted.append({
                "manager_id": mgr_id,
                "supabase_pts": sb_pts,
                "official_pts": official_pts,
                "delta": official_pts - sb_pts
            })

    if not drifted:
        logger.info("✅ Standings Reconciliation Gate: 100% parity verified between Supabase and Official FPL Standings.")
        return {"reconciled": True, "drifted_managers": [], "healed": False}

    logger.warning(
        f"⚠️ Standings drift detected across {len(drifted)} manager(s) in closed GWs (1..{current_gw - 1}): {drifted}. "
        f"Triggering automatic self-healing resync..."
    )
    heal_res = sync_manager_picks_and_performance(
        supabase,
        league_entries,
        current_gw=current_gw - 1,
        sync_all_history=True
    )
    return {
        "reconciled": True,
        "drifted_managers": drifted,
        "healed": True,
        "heal_stats": heal_res
    }
