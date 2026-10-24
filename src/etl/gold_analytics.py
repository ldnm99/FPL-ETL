"""
Gold Analytics Pipeline Orchestrator.
Project Blaziken (v5.0) — FPL Draft League (#38279)

Integrates:
1. Performance Clustering (Scikit-Learn KMeans k=4 & Residual Regression)
2. Gold Player Analytics Table Updates in Supabase
3. Waiver Opportunity Detection & Regression Alerts
"""

import os
import sys
import time
import logging
from typing import Dict, List, Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from src.etl.performance_clusters import run_performance_clustering, get_supabase_client


def run_gold_analytics_pipeline() -> Dict[str, Any]:
    """
    Executes the complete Gold Player Analytics pipeline:
    - Runs Scikit-Learn KMeans and residual regression
    - Computes cluster_label and performance_delta_z
    - Upserts into gold_player_analytics in Supabase (<2s SLA)
    """
    logging.info("🚀 Starting Gold Analytics Pipeline Execution...")
    start_time = time.time()

    client = get_supabase_client()
    records = run_performance_clustering(client)

    elapsed = time.time() - start_time

    # Compute key analytical KPIs
    underperformers = [r for r in records if r["cluster_label"] == "underperformer_buy"]
    overperformers = [r for r in records if r["cluster_label"] == "overperformer_sell"]
    elite = [r for r in records if r["cluster_label"] == "elite"]
    free_agent_underperformers = [r for r in underperformers if r.get("is_free_agent")]

    summary = {
        "status": "success",
        "total_players_analyzed": len(records),
        "elite_count": len(elite),
        "underperformers_buy_count": len(underperformers),
        "overperformers_sell_count": len(overperformers),
        "free_agent_buy_opportunities": len(free_agent_underperformers),
        "execution_time_seconds": round(elapsed, 2),
    }

    logging.info("📊 Gold Analytics Summary:")
    logging.info(f"   • Total Active Players (>= 270m): {summary['total_players_analyzed']}")
    logging.info(f"   • Elite Players: {summary['elite_count']}")
    logging.info(f"   • Underperformers (Buy Opportunities): {summary['underperformers_buy_count']}")
    logging.info(f"   • Overperformers (Sell / Regression Alerts): {summary['overperformers_sell_count']}")
    logging.info(f"   • Free Agent Buy Opportunities: {summary['free_agent_buy_opportunities']}")
    logging.info(f"   • Execution Time: {summary['execution_time_seconds']}s")

    return summary


def main():
    res = run_gold_analytics_pipeline()
    print(f"\n🎉 Pipeline Finished Successfully in {res['execution_time_seconds']}s!")


if __name__ == "__main__":
    main()
