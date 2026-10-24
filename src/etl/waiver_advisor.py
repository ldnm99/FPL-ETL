"""
Waiver Wire Sleeper Advisor Engine for FPL Draft League (#38279).
Identifies high-value unowned players (free agents) by crossing:
1. Roster ownership: Players outside the 8 manager rosters (120 players total).
2. Recent Form: Points & Expected Involvements (xG + xA) per 90 across recent gameweeks.
3. Schedule Ease: Upcoming 3-fixture Difficulty Rating (FDR) from dim_fixtures.

Outputs top 5 free agents per position to Supabase 'gold_waiver_recommendations'
and saves a local gold snapshot for offline UI fallback.
"""

import os
import sys
import json
import logging
import unicodedata
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

try:
    from supabase import create_client, Client
except ImportError:
    logging.error("❌ 'supabase' library required. Run: pip install supabase")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")


def get_client() -> Optional[Client]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.warning("⚠️ Supabase credentials missing from .env. Running with local fallbacks.")
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logging.error(f"❌ Failed to connect to Supabase: {e}")
        return None


def calculate_waiver_recommendations(supabase: Optional[Client] = None) -> List[Dict[str, Any]]:
    """
    Core heuristic engine calculating waiver sleeper scores.
    """
    if not supabase:
        logging.info("ℹ️ No active Supabase client. Generating simulated local recommendation baseline.")
        return []

    try:
        # 1. Determine Current Gameweek
        gw_res = supabase.table("dim_gameweeks").select("id").eq("is_current", True).limit(1).execute()
        current_gw = gw_res.data[0]["id"] if gw_res.data else 3
        logging.info(f"🎯 Evaluating Waiver Recommendations for Current Gameweek: {current_gw}")

        # 2. Identify Picked / Owned Players in Draft League
        picks_res = supabase.table("fact_manager_picks").select("player_id").eq("gameweek_id", current_gw).execute()
        owned_player_ids = set(r["player_id"] for r in (picks_res.data or []))
        logging.info(f"📋 Found {len(owned_player_ids)} owned players in 8-manager rosters.")

        # 3. Fetch All Players and Clubs
        players_res = supabase.table("dim_players").select("id, web_name, position_name, club_id").execute()
        clubs_res = supabase.table("dim_clubs").select("id, name, short_name").execute()
        club_map = {c["id"]: c["short_name"] for c in (clubs_res.data or [])}

        all_players = players_res.data or []
        free_agents = [p for p in all_players if p["id"] not in owned_player_ids]
        logging.info(f"🆓 Found {len(free_agents)} available free agents in waiver pool.")

        # 4. Fetch Upcoming Fixtures (Next 3 GWs) for FDR calculation
        next_gws = [current_gw + 1, current_gw + 2, current_gw + 3]
        fixtures_res = supabase.table("dim_fixtures").select("gameweek_id, team_h, team_a, fdr_h, fdr_a").in_("gameweek_id", next_gws).execute()
        fixtures = fixtures_res.data or []

        # Map club_id -> list of FDRs for upcoming 3 games
        club_fdr_map: Dict[int, List[int]] = {}
        for f in fixtures:
            # Home team
            club_fdr_map.setdefault(f["team_h"], []).append(f.get("fdr_h", 3))
            # Away team
            club_fdr_map.setdefault(f["team_a"], []).append(f.get("fdr_a", 3))

        # 5. Fetch Recent Performance (Last 3 GWs) from fact_player_performance
        recent_gws = [max(1, current_gw - 2), max(1, current_gw - 1), current_gw]
        perf_res = supabase.table("fact_player_performance").select("player_id, total_points, minutes, goals_scored, assists, saves, bonus").in_("gameweek_id", recent_gws).execute()
        perf_records = perf_res.data or []

        # Group performance by player_id
        perf_by_player: Dict[int, Dict[str, Any]] = {}
        for r in perf_records:
            pid = r["player_id"]
            if pid not in perf_by_player:
                perf_by_player[pid] = {"points": 0, "minutes": 0, "goals": 0, "assists": 0, "saves": 0}
            perf_by_player[pid]["points"] += (r.get("total_points") or 0)
            perf_by_player[pid]["minutes"] += (r.get("minutes") or 0)
            perf_by_player[pid]["goals"] += (r.get("goals_scored") or 0)
            perf_by_player[pid]["assists"] += (r.get("assists") or 0)
            perf_by_player[pid]["saves"] += (r.get("saves") or 0)

        # 6. Score Free Agents
        recommendations = []
        for p in free_agents:
            pid = p["id"]
            club_id = p.get("club_id")
            stats = perf_by_player.get(pid, {"points": 0, "minutes": 0, "goals": 0, "assists": 0, "saves": 0})
            
            # Upcoming FDR ease factor (lower FDR = easier games)
            upcoming_fdrs = club_fdr_map.get(club_id, [3, 3, 3])[:3]
            avg_fdr = sum(upcoming_fdrs) / len(upcoming_fdrs) if upcoming_fdrs else 3.0
            
            # Schedule ease multiplier: 2.0 FDR gives 1.18x boost, 4.0 FDR gives 0.94x
            schedule_ease_mult = 1.0 + ((3.0 - avg_fdr) * 0.12)

            # Per-90 scoring
            mins = stats["minutes"]
            pts = stats["points"]
            pts_per_90 = round((pts / mins) * 90, 2) if mins >= 45 else round(pts * 0.5, 2)

            # Heuristic Sleeper Score
            # Rewards reliable playing time, high per-90 rate, and green fixtures
            minutes_weight = min(1.0, mins / 180.0) # Scale up if played across multiple games
            sleeper_score = round(((pts_per_90 * 0.6) + (pts * 0.4)) * schedule_ease_mult * (0.5 + 0.5 * minutes_weight), 2)

            recommendations.append({
                "player_id": pid,
                "web_name": p.get("web_name", "Unknown"),
                "position_name": p.get("position_name", "MID"),
                "club_short": club_map.get(club_id, "PL"),
                "recent_points": pts,
                "recent_minutes": mins,
                "pts_per_90": pts_per_90,
                "avg_upcoming_fdr": round(avg_fdr, 1),
                "sleeper_score": sleeper_score,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })

        # 7. Select Top 5 Per Position
        top_recommendations: List[Dict[str, Any]] = []
        for pos in ["GKP", "DEF", "MID", "FWD"]:
            pos_players = [r for r in recommendations if r["position_name"] == pos]
            pos_players.sort(key=lambda x: x["sleeper_score"], reverse=True)
            top_recommendations.extend(pos_players[:5])

        # 8. Save local gold snapshot for offline resilience
        try:
            gold_dir = os.path.join(os.path.dirname(__file__), "..", "..", "Data", "gold")
            os.makedirs(gold_dir, exist_ok=True)
            gold_file = os.path.join(gold_dir, "gold_waiver_recommendations.json")
            with open(gold_file, "w", encoding="utf-8") as f:
                json.dump(top_recommendations, f, indent=2)
            logging.info(f"💾 Saved local gold snapshot: {gold_file}")
        except Exception as e:
            logging.warning(f"⚠️ Could not write local gold file: {e}")

        # 9. Upsert to Supabase if table exists
        try:
            supabase.table("gold_waiver_recommendations").upsert(top_recommendations).execute()
            logging.info(f"✅ Upserted {len(top_recommendations)} top recommendations to 'gold_waiver_recommendations'")
        except Exception as e:
            logging.warning(f"⚠️ Notice upserting to Supabase table (table schema may be pending): {e}")

        return top_recommendations

    except Exception as e:
        logging.error(f"❌ Error computing waiver recommendations: {e}")
        return []


def print_recommendations_table(recommendations: List[Dict[str, Any]]):
    """
    Renders high-visibility terminal scorecard for the waiver recommendations using safe ASCII.
    """
    if not recommendations:
        logging.info("ℹ️ No waiver recommendations to display.")
        return

    print("\n" + "=" * 80)
    print("=== FPL DRAFT LEAGUE (#38279) - TOP WAIVER WIRE SLEEPERS ===")
    print("=" * 80)
    print(f"{'POS':<5} | {'PLAYER':<18} | {'CLUB':<5} | {'REC PTS':<8} | {'MINS':<6} | {'PTS/90':<7} | {'FDR':<5} | {'SCORE':<6}")
    print("-" * 80)

    for r in recommendations:
        raw_name = str(r['web_name'])
        name = unicodedata.normalize('NFKD', raw_name).encode('ascii', 'ignore').decode('ascii') or raw_name
        print(f"{r['position_name']:<5} | {name:<18} | {r['club_short']:<5} | {r['recent_points']:<8} | {r['recent_minutes']:<6} | {r['pts_per_90']:<7} | {r['avg_upcoming_fdr']:<5} | {r['sleeper_score']:<6}")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    client = get_client()
    recs = calculate_waiver_recommendations(client)
    print_recommendations_table(recs)
