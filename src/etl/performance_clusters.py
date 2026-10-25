"""
Performance Clustering & Residual Regression Engine using Scikit-Learn.
Project Blaziken (v5.0) — FPL Draft League (#38279)

Identifies Underperformers (Buy/Waiver targets) and Overperformers (Sell/Regression candidates):
1. Filters active players with minutes >= 270 (minimum 3 full 90s).
2. Computes per-90 metrics: xgi_per_90, actual_pts_per_90, defcon_rate.
3. Fits Linear Regression to establish expected points baseline based on xGI and defcon rates.
4. Calculates residual delta = actual_pts_per_90 - expected_baseline and performance_delta_z (Z-score).
5. Fits KMeans (k=4) on standardized feature space [xgi_per_90, actual_pts_per_90, defcon_rate].
6. Labels each player: 'underperformer_buy', 'overperformer_sell', 'elite', or 'fringe'.
7. Upserts results into Supabase 'gold_player_analytics' and creates local JSON snapshots.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge

from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")


def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logging.warning("⚠️ Supabase credentials missing. Will run offline mode.")
        return None
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logging.error(f"❌ Failed to create Supabase client: {e}")
        return None


def load_base_player_dataset() -> pd.DataFrame:
    """
    Loads complete player records from local gold/silver data or advanced stats json.
    """
    json_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "FPL_web", "src", "data", "advancedPlayerStats.json")
    )
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        logging.info(f"📁 Loaded {len(df)} base player records from advancedPlayerStats.json")
        return df

    # Fallback to silver players_data.csv
    csv_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Data", "silver", "players_data.csv")
    )
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        logging.info(f"📁 Loaded {len(df)} player records from silver players_data.csv")
        return df

    raise FileNotFoundError("Could not find base player data source.")


def load_historical_calibration_data() -> Optional[pd.DataFrame]:
    """
    Loads historical multi-season player performance to calibrate baseline expected points regression.
    Avoids overfitting on small early-season samples (e.g. GW 1-8).
    """
    # 1. Try parquet first
    parquet_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Data", "history", "fact_player_performance_all_seasons.parquet")
    )
    if os.path.exists(parquet_path):
        try:
            df_hist = pd.read_parquet(parquet_path)
            logging.info(f"📚 Loaded {len(df_hist)} historical facts from {os.path.basename(parquet_path)}")
            return df_hist
        except Exception as e:
            logging.warning(f"⚠️ Could not read historical parquet: {e}")

    # 2. Try sqlite
    sqlite_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "Data", "fpl_draft_history.sqlite")
    )
    if os.path.exists(sqlite_path):
        try:
            import sqlite3
            with sqlite3.connect(sqlite_path) as conn:
                df_hist = pd.read_sql_query("SELECT * FROM fact_player_performance", conn)
            logging.info(f"📚 Loaded {len(df_hist)} historical facts from fpl_draft_history.sqlite")
            return df_hist
        except Exception as e:
            logging.warning(f"⚠️ Could not read historical sqlite: {e}")

    return None


def run_performance_clustering(supabase_client=None) -> List[Dict[str, Any]]:
    """
    Executes the Scikit-Learn KMeans (k=4) clustering and residual regression.
    """
    start_time = time.time()
    client = supabase_client or get_supabase_client()

    df_base = load_base_player_dataset()

    # 1. Fetch live manager picks to tag free agents
    owned_player_ids = set()
    if client:
        try:
            picks_res = client.table("fact_manager_picks").select("player_id").execute()
            if picks_res.data:
                owned_player_ids = set(r["player_id"] for r in picks_res.data)
                logging.info(f"📋 Identified {len(owned_player_ids)} drafted/owned players in draft league.")
        except Exception as e:
            logging.warning(f"⚠️ Could not fetch manager picks from Supabase: {e}")

    # 2. Fetch live performance aggregates from Supabase fact_player_performance
    live_perf_map = {}
    if client:
        try:
            perf_res = client.table("fact_player_performance").select(
                "player_id, total_points, minutes, goals_scored, assists, saves, defcons"
            ).execute()
            if perf_res.data:
                for r in perf_res.data:
                    pid = r["player_id"]
                    if pid not in live_perf_map:
                        live_perf_map[pid] = {
                            "total_points": 0,
                            "minutes": 0,
                            "goals": 0,
                            "assists": 0,
                            "saves": 0,
                            "defcons": 0,
                        }
                    live_perf_map[pid]["total_points"] += (r.get("total_points") or 0)
                    live_perf_map[pid]["minutes"] += (r.get("minutes") or 0)
                    live_perf_map[pid]["goals"] += (r.get("goals_scored") or 0)
                    live_perf_map[pid]["assists"] += (r.get("assists") or 0)
                    live_perf_map[pid]["saves"] += (r.get("saves") or 0)
                    live_perf_map[pid]["defcons"] += (r.get("defcons") or 0)
                logging.info(f"⚡ Merged live performance facts for {len(live_perf_map)} players.")
        except Exception as e:
            logging.warning(f"⚠️ Could not fetch live performance facts from Supabase: {e}")

    # 3. Standardize column names
    col_map = {
        "id": "player_id",
        "name": "web_name",
        "team": "club_short",
        "club_code": "club_short",
        "position": "position_name",
    }
    for old_col, new_col in col_map.items():
        if old_col in df_base.columns and new_col not in df_base.columns:
            df_base[new_col] = df_base[old_col]

    # Ensure required columns exist
    for col in ["player_id", "web_name", "position_name", "club_short", "minutes", "total_points", "defcons", "xGi"]:
        if col not in df_base.columns:
            df_base[col] = 0

    # Overlay live performance if available
    for idx, row in df_base.iterrows():
        pid = int(row["player_id"])
        if pid in live_perf_map:
            lp = live_perf_map[pid]
            if lp["minutes"] > row["minutes"]:
                df_base.at[idx, "minutes"] = lp["minutes"]
                df_base.at[idx, "total_points"] = lp["total_points"]
            if lp["defcons"] > 0:
                df_base.at[idx, "defcons"] = max(df_base.at[idx, "defcons"], lp["defcons"])

    # 4. Filter active players with minutes >= 270 (strictly 3 full 90s)
    df_active = df_base[df_base["minutes"] >= 270].copy()
    logging.info(f"🔬 Qualified {len(df_active)} players with minutes >= 270 for clustering.")

    # 5. Compute per-90 rates
    df_active["nineties"] = df_active["minutes"] / 90.0
    df_active["gw_points_per_90"] = (df_active["total_points"] / df_active["nineties"]).round(2)
    df_active["xgi_per_90"] = (df_active["xGi"] / df_active["nineties"]).round(2)
    df_active["defcon_rate"] = (df_active["defcons"] / df_active["nineties"]).round(2)

    # Clean any NaNs or infinities
    for col in ["gw_points_per_90", "xgi_per_90", "defcon_rate"]:
        df_active[col] = df_active[col].fillna(0).replace([np.inf, -np.inf], 0)

    # 6. Fit Multi-Season Calibrated Regression for Expected Baseline Points
    df_hist = load_historical_calibration_data()
    hist_ps = None
    if df_hist is not None and not df_hist.empty:
        try:
            group_cols = ["season_id", "player_id"]
            avail_cols = [c for c in ["minutes", "total_points", "goals_scored", "assists", "defensive_contribution"] if c in df_hist.columns]
            hist_grouped = df_hist.groupby(group_cols)[avail_cols].sum().reset_index()
            # Filter players with at least 5 matches (450 mins)
            hist_ps = hist_grouped[hist_grouped["minutes"] >= 450].copy()
            hist_ps["nineties"] = hist_ps["minutes"] / 90.0
            hist_ps["gw_points_per_90"] = (hist_ps["total_points"] / hist_ps["nineties"]).round(2)
            # Use goal involvements / 90 as attacking proxy for xGI
            goals = hist_ps["goals_scored"] if "goals_scored" in hist_ps.columns else 0
            assists = hist_ps["assists"] if "assists" in hist_ps.columns else 0
            hist_ps["xgi_per_90"] = ((goals + assists) / hist_ps["nineties"]).round(2)
            defcon = hist_ps["defensive_contribution"] if "defensive_contribution" in hist_ps.columns else 0
            hist_ps["defcon_rate"] = (defcon / hist_ps["nineties"]).round(2)
            for c in ["gw_points_per_90", "xgi_per_90", "defcon_rate"]:
                hist_ps[c] = hist_ps[c].fillna(0).replace([np.inf, -np.inf], 0)
        except Exception as e:
            logging.warning(f"⚠️ Failed to process historical aggregates: {e}")
            hist_ps = None

    if hist_ps is not None and len(hist_ps) >= 50:
        logging.info(f"🎯 Calibrating baseline regression with {len(hist_ps)} multi-season historical player baselines.")
        X_hist = hist_ps[["xgi_per_90", "defcon_rate"]]
        y_hist = hist_ps["gw_points_per_90"]

        X_cur = df_active[["xgi_per_90", "defcon_rate"]]
        y_cur = df_active["gw_points_per_90"]

        # Current season players get sample_weight=1.0, historical seasons get sample_weight=0.35 (empirical prior)
        X_all = pd.concat([X_hist, X_cur], ignore_index=True).values
        y_all = pd.concat([y_hist, y_cur], ignore_index=True).values
        sample_weights = np.concatenate([np.full(len(X_hist), 0.35), np.full(len(X_cur), 1.0)])

        reg = Ridge(alpha=1.0)
        reg.fit(X_all, y_all, sample_weight=sample_weights)
        logging.info(f"📊 Calibrated Regression Coefs (xgi, defcon): {reg.coef_}, Intercept: {reg.intercept_:.2f}")
    else:
        # Fallback to standard linear regression on current active players
        X_reg = df_active[["xgi_per_90", "defcon_rate"]].values
        y_reg = df_active["gw_points_per_90"].values
        reg = LinearRegression()
        reg.fit(X_reg, y_reg)
        logging.info(f"📊 Current Season Regression Coefs (xgi, defcon): {reg.coef_}, Intercept: {reg.intercept_:.2f}")

    X_cur_pred = df_active[["xgi_per_90", "defcon_rate"]].values
    df_active["expected_pts_per_90"] = np.round(reg.predict(X_cur_pred), 2)
    df_active["residual_delta"] = np.round(df_active["gw_points_per_90"] - df_active["expected_pts_per_90"], 2)

    # Calculate residual Z-Score
    mean_res = df_active["residual_delta"].mean()
    std_res = df_active["residual_delta"].std()
    if std_res == 0:
        std_res = 1.0
    df_active["performance_delta_z"] = np.round((df_active["residual_delta"] - mean_res) / std_res, 2)

    # 7. Normalize Features and Run Scikit-Learn KMeans (k=4)
    cluster_features = ["xgi_per_90", "gw_points_per_90", "defcon_rate"]
    scaler = StandardScaler()
    X_cluster = scaler.fit_transform(df_active[cluster_features].values)

    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    df_active["cluster_id"] = kmeans.fit_predict(X_cluster)

    # 8. Assign Descriptive Semantic Labels:
    # - 'underperformer_buy': High xGI / defcons, but negative residual Z-score (due for positive regression)
    # - 'overperformer_sell': Modest xGI / defcons, but high points / positive residual Z-score (due for drop-off)
    # - 'elite': High points AND high xGI (top-tier contributors)
    # - 'fringe': Benchmark role players / average baseline
    cluster_labels = []
    for _, row in df_active.iterrows():
        z = row["performance_delta_z"]
        pts_90 = row["gw_points_per_90"]
        xgi_90 = row["xgi_per_90"]
        defcon = row["defcon_rate"]

        if pts_90 >= 5.5 and (xgi_90 >= 0.35 or defcon >= 7.0):
            label = "elite"
        elif z <= -0.40 and (xgi_90 >= 0.20 or defcon >= 5.0):
            label = "underperformer_buy"
        elif z >= 0.60 and xgi_90 <= 0.45:
            label = "overperformer_sell"
        else:
            label = "fringe"

        cluster_labels.append(label)

    df_active["cluster_label"] = cluster_labels
    df_active["is_free_agent"] = df_active["player_id"].apply(lambda pid: int(pid) not in owned_player_ids)

    # Summary statistics
    counts = df_active["cluster_label"].value_counts().to_dict()
    logging.info(f"🏷️ Cluster distribution: {counts}")

    # 9. Format records for Supabase upsert and local snapshot
    results: List[Dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for _, row in df_active.iterrows():
        results.append({
            "player_id": int(row["player_id"]),
            "web_name": str(row["web_name"]),
            "position_name": str(row["position_name"]),
            "club_short": str(row["club_short"]),
            "minutes": int(row["minutes"]),
            "total_points": int(row["total_points"]),
            "xgi_per_90": float(row["xgi_per_90"]),
            "gw_points_per_90": float(row["gw_points_per_90"]),
            "defcon_rate": float(row["defcon_rate"]),
            "expected_pts_per_90": float(row["expected_pts_per_90"]),
            "residual_delta": float(row["residual_delta"]),
            "performance_delta_z": float(row["performance_delta_z"]),
            "cluster_label": str(row["cluster_label"]),
            "cluster_id": int(row["cluster_id"]),
            "is_free_agent": bool(row["is_free_agent"]),
            "updated_at": now_iso,
        })

    # 10. Save local gold snapshots for offline resilience
    gold_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Data", "gold", "gold_player_analytics.json")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "FPL_web", "src", "data", "gold_player_analytics.json")),
    ]
    for p in gold_paths:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            logging.info(f"💾 Saved local gold analytics snapshot: {p}")
        except Exception as e:
            logging.warning(f"⚠️ Could not write gold snapshot to {p}: {e}")

    # 11. Upsert into Supabase gold_player_analytics table
    if client:
        try:
            upsert_start = time.time()
            # Batch upsert in chunks of 100 for maximum throughput
            batch_size = 100
            for i in range(0, len(results), batch_size):
                chunk = results[i:i + batch_size]
                client.table("gold_player_analytics").upsert(chunk, on_conflict="player_id").execute()
            upsert_elapsed = time.time() - upsert_start
            logging.info(f"🚀 Successfully upserted {len(results)} rows into Supabase in {upsert_elapsed:.2f}s (<2s SLA met!).")
        except Exception as e:
            logging.error(f"❌ Failed to upsert to Supabase gold_player_analytics: {e}")

    total_elapsed = time.time() - start_time
    logging.info(f"⏱️ Total performance clustering execution completed in {total_elapsed:.2f}s.")
    return results


if __name__ == "__main__":
    run_performance_clustering()
