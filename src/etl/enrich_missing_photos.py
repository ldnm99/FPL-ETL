"""
Enrich Missing Player Photos ETL Pipeline
Fetches official FPL /api/bootstrap-static/ elements to enrich 'photo' and 'photo_code'
in Supabase table 'dim_players' and local snapshot 'dim_players.parquet'.
"""
import os
import sys
import json
import logging
import urllib.request
import pandas as pd
from typing import Dict, Any, List
from src.config import config
from src.etl.upload_database import get_supabase_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
DRAFT_BOOTSTRAP_URL = "https://draft.premierleague.com/api/bootstrap-static"


def fetch_json(url: str) -> Dict[str, Any]:
    """Fetch JSON with custom User-Agent and timeout."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def enrich_photos() -> Dict[str, int]:
    """
    Main routine:
    1. Fetch official FPL elements
    2. Query dim_players from Supabase
    3. Map photo and photo_code
    4. Upsert into Supabase dim_players
    5. Update local dim_players.parquet
    """
    logging.info("🚀 Starting enrich_missing_photos pipeline...")

    # 1. Fetch bootstrap static data
    fpl_elements = []
    draft_elements = []

    try:
        logging.info(f"🌐 Fetching official FPL bootstrap static: {FPL_BOOTSTRAP_URL}")
        fpl_data = fetch_json(FPL_BOOTSTRAP_URL)
        fpl_elements = fpl_data.get("elements", [])
        logging.info(f"✅ Retrieved {len(fpl_elements)} FPL elements.")
    except Exception as e:
        logging.warning(f"⚠️ Failed to fetch standard FPL bootstrap: {e}")

    try:
        logging.info(f"🌐 Fetching draft FPL bootstrap static: {DRAFT_BOOTSTRAP_URL}")
        draft_data = fetch_json(DRAFT_BOOTSTRAP_URL)
        draft_elements = draft_data.get("elements", [])
        logging.info(f"✅ Retrieved {len(draft_elements)} Draft elements.")
    except Exception as e:
        logging.warning(f"⚠️ Failed to fetch draft FPL bootstrap: {e}")

    # Build lookup dictionaries
    # draft id -> code
    draft_id_to_code: Dict[int, str] = {}
    for el in draft_elements:
        p_id = el.get("id")
        code = el.get("code")
        if p_id is not None and code is not None:
            draft_id_to_code[int(p_id)] = str(code)

    # name -> code from fpl
    name_to_code: Dict[str, str] = {}
    for el in fpl_elements:
        code = el.get("code")
        if code:
            code_str = str(code)
            web_name = (el.get("web_name") or "").lower().strip()
            first_name = (el.get("first_name") or "").lower().strip()
            second_name = (el.get("second_name") or "").lower().strip()
            full_name = f"{first_name} {second_name}".strip()

            if web_name:
                name_to_code[web_name] = code_str
            if full_name:
                name_to_code[full_name] = code_str

    # Fallback to local playerCodeMap.json if available
    local_map_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "FPL_web", "src", "data", "playerCodeMap.json"
    )
    local_map: Dict[str, str] = {}
    if os.path.exists(local_map_path):
        try:
            with open(local_map_path, "r", encoding="utf-8") as f:
                local_map = json.load(f)
            logging.info(f"📂 Loaded local playerCodeMap.json with {len(local_map)} mappings.")
        except Exception as e:
            logging.warning(f"Could not load local playerCodeMap: {e}")

    # 2. Query dim_players from Supabase
    supabase = get_supabase_client()
    res = supabase.table("dim_players").select("*").execute()
    db_players = res.data or []
    logging.info(f"📊 Retrieved {len(db_players)} players from Supabase dim_players.")

    updates: List[Dict[str, Any]] = []
    enriched_count = 0

    for p in db_players:
        pid = p["id"]
        current_photo = p.get("photo")
        current_photo_code = p.get("photo_code")

        resolved_code = None

        # Check draft mapping first
        if pid in draft_id_to_code:
            resolved_code = draft_id_to_code[pid]
        # Check local map
        elif str(pid) in local_map:
            resolved_code = local_map[str(pid)]
        else:
            # Check name match
            wname = (p.get("web_name") or "").lower().strip()
            fname = (p.get("first_name") or "").lower().strip()
            sname = (p.get("second_name") or "").lower().strip()
            fullname = f"{fname} {sname}".strip()

            if wname in name_to_code:
                resolved_code = name_to_code[wname]
            elif fullname in name_to_code:
                resolved_code = name_to_code[fullname]

        if resolved_code:
            clean_code = str(resolved_code).replace(".jpg", "").replace("p", "").strip()
            target_photo = f"{clean_code}.jpg"
            target_photo_code = clean_code

            # Check if update is needed
            if current_photo != target_photo or current_photo_code != target_photo_code:
                row_copy = dict(p)
                row_copy["photo"] = target_photo
                row_copy["photo_code"] = target_photo_code
                updates.append(row_copy)
                enriched_count += 1

    logging.info(f"🔄 Need to update {len(updates)} players in Supabase dim_players.")

    # 3. Bulk upsert into Supabase dim_players in batches of 100
    if updates:
        batch_size = 100
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            try:
                supabase.table("dim_players").upsert(batch, on_conflict="id").execute()
                logging.info(f"  ✅ Upserted batch {i // batch_size + 1} ({len(batch)} players)")
            except Exception as e:
                logging.error(f"❌ Failed to upsert batch {i // batch_size + 1}: {e}")

    # 4. Update local dim_players.parquet snapshots
    parquet_paths = [
        os.path.join(config.GOLD_DIR, "dimensions", "dim_players.parquet"),
        os.path.join(config.GOLD_DIR, "dim_players.parquet"),
    ]

    for ppath in parquet_paths:
        if os.path.exists(ppath):
            try:
                df = pd.read_parquet(ppath)
                code_dict = {u["id"]: u["photo_code"] for u in updates}
                photo_dict = {u["id"]: u["photo"] for u in updates}

                # Update or create columns
                if "photo_code" not in df.columns:
                    df["photo_code"] = None
                if "photo" not in df.columns:
                    df["photo"] = None

                # Apply updates
                for pid, pcode in code_dict.items():
                    df.loc[df["player_id"] == pid if "player_id" in df.columns else df["id"] == pid, "photo_code"] = pcode
                    df.loc[df["player_id"] == pid if "player_id" in df.columns else df["id"] == pid, "photo"] = photo_dict[pid]

                df.to_parquet(ppath, index=False, engine="pyarrow")
                logging.info(f"💾 Updated local parquet snapshot at {ppath} ({len(df)} rows)")
            except Exception as e:
                logging.warning(f"⚠️ Could not update {ppath}: {e}")

    # 5. Synchronize local playerCodeMap.json for frontend
    if os.path.exists(local_map_path):
        try:
            for u in updates:
                local_map[str(u["id"])] = u["photo_code"]
            with open(local_map_path, "w", encoding="utf-8") as f:
                json.dump(local_map, f)
            logging.info(f"🌐 Synchronized frontend {local_map_path} with {len(local_map)} players.")
        except Exception as e:
            logging.warning(f"⚠️ Could not sync frontend playerCodeMap: {e}")

    logging.info(f"🎉 Photo enrichment complete! Enriched {enriched_count} players.")
    return {"total_checked": len(db_players), "enriched": enriched_count}


if __name__ == "__main__":
    enrich_photos()
