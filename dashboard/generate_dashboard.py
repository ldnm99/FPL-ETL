"""
FPL "Dobradinha" League — End-of-Season Recap Dashboard Generator
Reads local Gold parquet files + Bronze JSON picks and produces a
self-contained HTML report with embedded Plotly charts.
"""

import json
import os
import glob
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "Data"
GOLD = DATA_DIR / "gold"
BRONZE = DATA_DIR / "bronze"
OUTPUT_HTML = Path(__file__).parent / "fpl_season_recap.html"

# ---------------------------------------------------------------------------
# FPL colour palette
# ---------------------------------------------------------------------------
COLORS = {
    "green":      "#00FF87",
    "purple":     "#37003C",
    "light_purple": "#963CFF",
    "white":      "#FFFFFF",
    "grey":       "#EBEBE4",
    "dark":       "#1a0a1e",
    "card_bg":    "#2d0a35",
    "text_light": "#E8D5F5",
}

MANAGER_PALETTE = [
    "#00FF87", "#963CFF", "#FFB800", "#FF4B4B",
    "#00B4D8", "#FF6EC7", "#A8FF3E",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data():
    print("📂 Loading data...")

    mgr_perf = pd.read_parquet(GOLD / "manager_performance.parquet")
    gw_full  = pd.read_parquet(GOLD / "gw_data_full.parquet")
    dim_mgr  = pd.read_parquet(GOLD / "dimensions" / "dim_managers.parquet")
    dim_pl   = pd.read_parquet(GOLD / "dimensions" / "dim_players.parquet")
    dim_clubs = pd.read_parquet(GOLD / "dimensions" / "dim_clubs.parquet")
    player_stats = pd.read_parquet(GOLD / "facts" / "fact_player_seasonal_stats.parquet")

    # normalise manager ids
    mgr_perf["manager_id"] = mgr_perf["manager_id"].astype(int)
    gw_full["manager_id"]  = pd.to_numeric(gw_full["manager_id"], errors="coerce").astype("Int64")
    dim_mgr["manager_id"]  = dim_mgr["manager_id"].astype(int)

    # League metadata from bronze
    with open(BRONZE / "league_standings_raw.json") as f:
        league_raw = json.load(f)

    league_name = league_raw["league"]["name"]
    league_entries = {e["entry_id"]: e for e in league_raw["league_entries"]}

    print(f"   League: {league_name} | GWs: {mgr_perf['gameweek'].max()} | Managers: {len(dim_mgr)}")
    return {
        "mgr_perf": mgr_perf,
        "gw_full":  gw_full,
        "dim_mgr":  dim_mgr,
        "dim_pl":   dim_pl,
        "dim_clubs": dim_clubs,
        "player_stats": player_stats,
        "league_name": league_name,
        "league_entries": league_entries,
    }


def parse_captain_data(dim_mgr: pd.DataFrame, gw_full: pd.DataFrame) -> pd.DataFrame:
    """FPL Draft has no captain mechanic — return empty DataFrame."""
    print("ℹ️  FPL Draft league — no captain mechanic (all multipliers=1)")
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def compute_stats(d: dict, capt_df: pd.DataFrame) -> dict:
    print("🔢 Computing stats...")
    mgr_perf = d["mgr_perf"]
    gw_full  = d["gw_full"]
    dim_mgr  = d["dim_mgr"]

    max_gw = mgr_perf["gameweek"].max()
    manager_order = dim_mgr["team_name"].tolist()
    mgr_color = {t: MANAGER_PALETTE[i % len(MANAGER_PALETTE)] for i, t in enumerate(manager_order)}

    # ── Final standings ──────────────────────────────────────────────────────
    final_gw = mgr_perf[mgr_perf["gameweek"] == max_gw].copy()
    final_gw = final_gw.merge(
        dim_mgr[["manager_id", "first_name", "last_name"]], on="manager_id", how="left"
    )
    final_gw["manager_name"] = final_gw["first_name"] + " " + final_gw["last_name"]
    final_gw = final_gw.sort_values("cumulative_points", ascending=False).reset_index(drop=True)
    final_gw["final_rank"] = final_gw.index + 1

    # Per-manager GW stats
    mgr_gw_stats = (
        mgr_perf.groupby("manager_team_name")["total_gw_points"]
        .agg(["max", "min", "mean", "std"])
        .rename(columns={"max": "best_gw", "min": "worst_gw", "mean": "avg_gw", "std": "std_gw"})
        .reset_index()
    )
    final_gw = final_gw.merge(mgr_gw_stats, on="manager_team_name", how="left")

    # ── Weekly 1st place tracker ─────────────────────────────────────────────
    gw_ranks = mgr_perf.copy()
    weeks_first = (
        gw_ranks[gw_ranks["gw_rank"] == 1]
        .groupby("manager_team_name")
        .size()
        .reset_index(name="weeks_first")
    )
    final_gw = final_gw.merge(weeks_first, on="manager_team_name", how="left")
    final_gw["weeks_first"] = final_gw["weeks_first"].fillna(0).astype(int)

    # ── Awards ───────────────────────────────────────────────────────────────
    champion = final_gw.iloc[0]
    wooden_spoon = final_gw.iloc[-1]

    best_gw_row = mgr_perf.loc[mgr_perf["total_gw_points"].idxmax()]
    worst_gw_row = mgr_perf.loc[mgr_perf["total_gw_points"].idxmin()]

    most_consistent = mgr_gw_stats.loc[mgr_gw_stats["std_gw"].idxmin()]
    most_volatile   = mgr_gw_stats.loc[mgr_gw_stats["std_gw"].idxmax()]

    # Best comeback: largest positive rank change across the season
    mgr_perf_sorted = mgr_perf.sort_values(["manager_team_name", "gameweek"])
    mgr_perf_sorted["rank_change"] = mgr_perf_sorted.groupby("manager_team_name")["gw_rank"].diff(-1)
    best_comeback_row = mgr_perf_sorted.loc[mgr_perf_sorted["rank_change"].idxmax()]

    # Most points in comeback (most points scored the GW after their worst GW)
    worst_gw_per_mgr = mgr_perf.loc[mgr_perf.groupby("manager_team_name")["total_gw_points"].idxmin()]
    best_recovery_rows = []
    for _, row in worst_gw_per_mgr.iterrows():
        next_gw = mgr_perf[
            (mgr_perf["manager_team_name"] == row["manager_team_name"]) &
            (mgr_perf["gameweek"] == row["gameweek"] + 1)
        ]
        if not next_gw.empty:
            best_recovery_rows.append({
                "team": row["manager_team_name"],
                "worst_gw": row["gameweek"],
                "worst_pts": row["total_gw_points"],
                "next_pts": next_gw.iloc[0]["total_gw_points"],
            })
    recovery_df = pd.DataFrame(best_recovery_rows)
    best_recovery = recovery_df.loc[recovery_df["next_pts"].idxmax()] if not recovery_df.empty else None

    # ── Captain stats ────────────────────────────────────────────────────────
    capt_stats = {}
    if not capt_df.empty:
        capt_total = (
            capt_df.groupby("team_name")["captain_points"].sum()
            .reset_index(name="total_captain_pts")
        )
        best_capt_week = capt_df.loc[capt_df["captain_points"].idxmax()]
        worst_capt_week = capt_df.loc[capt_df["captain_points"].idxmin()]
        popular_captain = (
            capt_df.groupby("captain_name").size()
            .reset_index(name="times_captained")
            .sort_values("times_captained", ascending=False)
        )
        capt_by_mgr = (
            capt_df.groupby(["team_name", "captain_name"])
            .agg(times=("captain_name", "count"), pts=("captain_points", "sum"))
            .reset_index()
            .sort_values(["team_name", "times"], ascending=[True, False])
        )
        capt_stats = {
            "capt_total": capt_total,
            "best_capt_week": best_capt_week,
            "worst_capt_week": worst_capt_week,
            "popular_captain": popular_captain,
            "capt_by_mgr": capt_by_mgr,
        }

    # ── Player ownership stats (starters only) ───────────────────────────────
    starters = gw_full[gw_full["position"] <= 11].copy()
    starters["manager_id"] = starters["manager_id"].astype("Int64")
    owned_players = (
        starters.groupby(["player_id", "name"])
        .agg(
            managers_count=("manager_id", "nunique"),
            total_pts_for_owners=("gw_points", "sum"),
        )
        .reset_index()
        .sort_values("managers_count", ascending=False)
    )
    most_owned = owned_players.head(15)

    # Top performers (total points scored while being played)
    top_performers = owned_players.sort_values("total_pts_for_owners", ascending=False).head(15)

    # Best single GW player performance in the league
    best_player_gw = starters.loc[starters["gw_points"].idxmax()]

    # Club breakdown
    club_pts = (
        starters.groupby("team")["gw_points"].sum()
        .reset_index()
        .sort_values("gw_points", ascending=False)
    )

    # ── Positional breakdown ─────────────────────────────────────────────────
    starters_pos = starters.copy()
    starters_pos["position_label"] = starters_pos["position_season"].map(
        {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}
    ).fillna(starters_pos["position_season"].astype(str))

    pos_by_mgr = (
        starters_pos.groupby(["manager_team_name", "position_label"])["gw_points"]
        .sum()
        .reset_index()
    )

    # Best player per position in the league
    best_by_pos = (
        starters_pos.groupby(["position_label", "player_id", "name"])["gw_points"]
        .sum()
        .reset_index()
        .sort_values("gw_points", ascending=False)
        .groupby("position_label")
        .first()
        .reset_index()
        .rename(columns={"gw_points": "total_pts"})
    )

    # ── H2H weekly win matrix ────────────────────────────────────────────────
    # For each GW, which manager had higher points?
    gw_pivot = mgr_perf.pivot(index="gameweek", columns="manager_team_name", values="total_gw_points")
    teams = gw_pivot.columns.tolist()
    h2h_wins = pd.DataFrame(0, index=teams, columns=teams)
    for t1 in teams:
        for t2 in teams:
            if t1 != t2:
                h2h_wins.loc[t1, t2] = (gw_pivot[t1] > gw_pivot[t2]).sum()

    print("   ✅ Stats computed")
    return {
        "final_gw": final_gw,
        "mgr_perf": mgr_perf,
        "champion": champion,
        "wooden_spoon": wooden_spoon,
        "best_gw_row": best_gw_row,
        "worst_gw_row": worst_gw_row,
        "most_consistent": most_consistent,
        "most_volatile": most_volatile,
        "best_comeback_row": best_comeback_row,
        "best_recovery": best_recovery,
        "capt_stats": capt_stats,
        "most_owned": most_owned,
        "top_performers": top_performers,
        "best_player_gw": best_player_gw,
        "club_pts": club_pts,
        "h2h_wins": h2h_wins,
        "mgr_color": mgr_color,
        "max_gw": max_gw,
        "league_name": d["league_name"],
        "gw_pivot": gw_pivot,
        "pos_by_mgr": pos_by_mgr,
        "best_by_pos": best_by_pos,
    }


# ---------------------------------------------------------------------------
# Plotly chart builders (return JSON strings)
# ---------------------------------------------------------------------------

def chart_cumulative_points(stats: dict) -> str:
    mgr_perf = stats["mgr_perf"]
    mgr_color = stats["mgr_color"]

    fig = go.Figure()
    for team, color in mgr_color.items():
        df = mgr_perf[mgr_perf["manager_team_name"] == team].sort_values("gameweek")
        fig.add_trace(go.Scatter(
            x=df["gameweek"], y=df["cumulative_points"],
            mode="lines+markers",
            name=team,
            line=dict(color=color, width=2.5),
            marker=dict(size=5),
            hovertemplate=f"<b>{team}</b><br>GW %{{x}}: %{{y}} pts<extra></extra>",
        ))

    fig.update_layout(
        title="Season Journey — Cumulative Points",
        xaxis_title="Gameweek",
        yaxis_title="Cumulative Points",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        legend=dict(bgcolor="#2d0a35", bordercolor="#963CFF", borderwidth=1),
        xaxis=dict(gridcolor="#3d1045", tickmode="linear", dtick=5),
        yaxis=dict(gridcolor="#3d1045"),
        hovermode="x unified",
        height=450,
        margin=dict(l=60, r=20, t=50, b=50),
    )
    return pio.to_json(fig)


def chart_gw_heatmap(stats: dict) -> str:
    gw_pivot = stats["gw_pivot"]
    teams = gw_pivot.columns.tolist()
    gws = gw_pivot.index.tolist()
    z = gw_pivot[teams].values

    # Short labels for y axis
    short = [t if len(t) <= 14 else t[:12] + "…" for t in teams]

    fig = go.Figure(go.Heatmap(
        z=z.T,
        x=[f"GW{g}" for g in gws],
        y=short,
        colorscale=[
            [0.0, "#8B0000"], [0.3, "#FF4B4B"],
            [0.5, "#FFB800"], [0.7, "#A8FF3E"],
            [1.0, "#00FF87"],
        ],
        hoverongaps=False,
        hovertemplate="<b>%{y}</b><br>%{x}: %{z} pts<extra></extra>",
        colorbar=dict(title="GW pts", tickfont=dict(color="#E8D5F5"), titlefont=dict(color="#E8D5F5")),
    ))
    fig.update_layout(
        title="GW Points Heatmap",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
        height=320,
        margin=dict(l=140, r=20, t=50, b=70),
    )
    return pio.to_json(fig)


def chart_captain_points(stats: dict) -> str:
    capt_stats = stats["capt_stats"]
    if not capt_stats:
        return "{}"
    capt_total = capt_stats["capt_total"].sort_values("total_captain_pts", ascending=True)
    mgr_color = stats["mgr_color"]
    colors = [mgr_color.get(t, "#963CFF") for t in capt_total["team_name"]]

    fig = go.Figure(go.Bar(
        x=capt_total["total_captain_pts"],
        y=capt_total["team_name"],
        orientation="h",
        marker_color=colors,
        hovertemplate="<b>%{y}</b><br>Total captain pts: %{x}<extra></extra>",
    ))
    fig.update_layout(
        title="Total Captain Points by Manager",
        xaxis_title="Points",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        xaxis=dict(gridcolor="#3d1045"),
        yaxis=dict(gridcolor="#3d1045"),
        height=320,
        margin=dict(l=160, r=20, t=50, b=50),
    )
    return pio.to_json(fig)


def chart_gw_distribution(stats: dict) -> str:
    mgr_perf = stats["mgr_perf"]
    mgr_color = stats["mgr_color"]

    fig = go.Figure()
    for team, color in mgr_color.items():
        pts = mgr_perf[mgr_perf["manager_team_name"] == team]["total_gw_points"]
        fig.add_trace(go.Box(
            y=pts, name=team,
            marker_color=color, line_color=color,
            boxmean=True,
            hovertemplate=f"<b>{team}</b><br>%{{y}} pts<extra></extra>",
        ))
    fig.update_layout(
        title="GW Points Distribution",
        yaxis_title="GW Points",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        yaxis=dict(gridcolor="#3d1045"),
        showlegend=False,
        height=380,
        margin=dict(l=60, r=20, t=50, b=100),
        xaxis=dict(tickangle=-25),
    )
    return pio.to_json(fig)


def chart_most_owned(stats: dict) -> str:
    most_owned = stats["most_owned"].sort_values("managers_count")
    fig = go.Figure(go.Bar(
        x=most_owned["managers_count"],
        y=most_owned["name"],
        orientation="h",
        marker_color="#963CFF",
        hovertemplate="<b>%{y}</b><br>Owned by %{x} managers<extra></extra>",
    ))
    fig.update_layout(
        title="Most Owned Players (Starting XI)",
        xaxis_title="Number of Managers",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        xaxis=dict(gridcolor="#3d1045", dtick=1),
        height=420,
        margin=dict(l=160, r=20, t=50, b=50),
    )
    return pio.to_json(fig)


def chart_top_performers(stats: dict) -> str:
    top = stats["top_performers"].sort_values("total_pts_for_owners")
    fig = go.Figure(go.Bar(
        x=top["total_pts_for_owners"],
        y=top["name"],
        orientation="h",
        marker_color="#00FF87",
        hovertemplate="<b>%{y}</b><br>%{x} total pts scored for owners<extra></extra>",
    ))
    fig.update_layout(
        title="Top Player Performers (Total Points for Owners)",
        xaxis_title="Points",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        xaxis=dict(gridcolor="#3d1045"),
        height=420,
        margin=dict(l=160, r=20, t=50, b=50),
    )
    return pio.to_json(fig)


def chart_club_breakdown(stats: dict) -> str:
    club_pts = stats["club_pts"].head(15).sort_values("gw_points")
    fig = go.Figure(go.Bar(
        x=club_pts["gw_points"],
        y=club_pts["team"],
        orientation="h",
        marker_color="#FFB800",
        hovertemplate="<b>%{y}</b><br>%{x} pts contributed<extra></extra>",
    ))
    fig.update_layout(
        title="Points by Club (Top 15 — Starting XI only)",
        xaxis_title="Total Points",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        xaxis=dict(gridcolor="#3d1045"),
        height=420,
        margin=dict(l=120, r=20, t=50, b=50),
    )
    return pio.to_json(fig)


def chart_h2h_matrix(stats: dict) -> str:
    h2h = stats["h2h_wins"]
    teams = h2h.index.tolist()
    z = h2h.values.astype(float)
    np.fill_diagonal(z, np.nan)

    short = [t if len(t) <= 14 else t[:12] + "…" for t in teams]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=short, y=short,
        colorscale=[[0, "#8B0000"], [0.5, "#FFB800"], [1, "#00FF87"]],
        hoverongaps=False,
        hovertemplate="<b>%{y}</b> beat <b>%{x}</b> %{z:.0f} GWs<extra></extra>",
        colorbar=dict(title="GW wins", tickfont=dict(color="#E8D5F5"), titlefont=dict(color="#E8D5F5")),
    ))
    for i in range(len(teams)):
        for j in range(len(teams)):
            if i != j:
                fig.add_annotation(
                    x=short[j], y=short[i],
                    text=str(int(z[i, j])),
                    showarrow=False,
                    font=dict(color="white", size=12),
                )
    fig.update_layout(
        title="Head-to-Head Weekly Win Matrix (row beat column N times)",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        height=420,
        margin=dict(l=160, r=20, t=60, b=120),
        xaxis=dict(tickangle=-35),
    )
    return pio.to_json(fig)


def chart_pos_by_mgr(stats: dict) -> str:
    pos_by_mgr = stats["pos_by_mgr"]
    mgr_color = stats["mgr_color"]
    pos_order = ["GK", "DEF", "MID", "FWD"]

    fig = go.Figure()
    for team, color in mgr_color.items():
        df = pos_by_mgr[pos_by_mgr["manager_team_name"] == team]
        # ensure all positions present
        df = df.set_index("position_label").reindex(pos_order).reset_index()
        fig.add_trace(go.Bar(
            name=team,
            x=df["position_label"],
            y=df["gw_points"],
            marker_color=color,
            hovertemplate=f"<b>{team}</b><br>%{{x}}: %{{y}} pts<extra></extra>",
        ))
    fig.update_layout(
        barmode="group",
        title="Points by Position per Manager",
        xaxis_title="Position",
        yaxis_title="Total Points",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        yaxis=dict(gridcolor="#3d1045"),
        legend=dict(bgcolor="#2d0a35", bordercolor="#963CFF", borderwidth=1),
        height=380,
        margin=dict(l=60, r=20, t=50, b=50),
    )
    return pio.to_json(fig)



    capt_stats = stats["capt_stats"]
    if not capt_stats:
        return "{}"
    pop = capt_stats["popular_captain"].head(12).sort_values("times_captained")
    fig = go.Figure(go.Bar(
        x=pop["times_captained"],
        y=pop["captain_name"],
        orientation="h",
        marker_color="#FF6EC7",
        hovertemplate="<b>%{y}</b><br>Captained %{x} times<extra></extra>",
    ))
    fig.update_layout(
        title="Most Popular Captains (Across All Managers)",
        xaxis_title="Times Captained",
        plot_bgcolor="#1a0a1e",
        paper_bgcolor="#1a0a1e",
        font=dict(color="#E8D5F5"),
        xaxis=dict(gridcolor="#3d1045", dtick=1),
        height=360,
        margin=dict(l=140, r=20, t=50, b=50),
    )
    return pio.to_json(fig)


# ---------------------------------------------------------------------------
# HTML generation helpers
# ---------------------------------------------------------------------------

def medal(rank: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")


def fmt(v) -> str:
    if pd.isna(v):
        return "—"
    if isinstance(v, float):
        return f"{v:.1f}"
    return str(v)


def standings_rows(final_gw: pd.DataFrame) -> str:
    rows = []
    for _, r in final_gw.iterrows():
        rank = int(r["final_rank"])
        highlight = " champion-row" if rank == 1 else (" spoon-row" if rank == len(final_gw) else "")
        rows.append(f"""
        <tr class="standings-row{highlight}">
          <td>{medal(rank)}</td>
          <td><strong>{r['manager_team_name']}</strong></td>
          <td>{r['manager_name']}</td>
          <td class="pts">{int(r['cumulative_points'])}</td>
          <td>{int(r['best_gw'])}</td>
          <td>{int(r['worst_gw'])}</td>
          <td>{r['avg_gw']:.1f}</td>
          <td>{int(r['weeks_first'])}</td>
        </tr>""")
    return "\n".join(rows)


def award_card(emoji: str, title: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="award-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="award-card">
      <div class="award-emoji">{emoji}</div>
      <div class="award-title">{title}</div>
      <div class="award-value">{value}</div>
      {sub_html}
    </div>"""


def captain_table_rows(capt_by_mgr: pd.DataFrame) -> str:
    rows = []
    for _, r in capt_by_mgr.iterrows():
        rows.append(f"""
        <tr>
          <td>{r['team_name']}</td>
          <td><strong>{r['captain_name']}</strong></td>
          <td>{int(r['times'])}</td>
          <td>{int(r['pts'])}</td>
        </tr>""")
    return "\n".join(rows)


def best_by_pos_cards(best_by_pos: pd.DataFrame) -> str:
    pos_emoji = {"GK": "🧤", "DEF": "🛡️", "MID": "⚙️", "FWD": "⚡"}
    pos_order = ["GK", "DEF", "MID", "FWD"]
    cards = []
    for pos in pos_order:
        row = best_by_pos[best_by_pos["position_label"] == pos]
        if row.empty:
            continue
        row = row.iloc[0]
        emoji = pos_emoji.get(pos, "")
        cards.append(f"""
        <div class="award-card">
          <div class="award-emoji">{emoji}</div>
          <div class="award-title">Best {pos} in League</div>
          <div class="award-value">{row['name']}</div>
          <div class="award-sub">{int(row['total_pts'])} pts scored for their manager</div>
        </div>""")
    return "\n".join(cards)


def chart_div(div_id: str, chart_json: str) -> str:
    if chart_json == "{}":
        return f'<div id="{div_id}" class="chart-placeholder">No data available</div>'
    return f"""
    <div id="{div_id}" class="chart-container"></div>
    <script>
      (function() {{
        var fig = {chart_json};
        Plotly.newPlot('{div_id}', fig.data, fig.layout, {{responsive: true, displayModeBar: false}});
      }})();
    </script>"""


# ---------------------------------------------------------------------------
# Full HTML assembly
# ---------------------------------------------------------------------------

def build_html(stats: dict, capt_df: pd.DataFrame) -> str:
    print("🎨 Building HTML...")

    league_name  = stats["league_name"]
    final_gw     = stats["final_gw"]
    champion     = stats["champion"]
    wooden_spoon = stats["wooden_spoon"]
    best_gw_row  = stats["best_gw_row"]
    worst_gw_row = stats["worst_gw_row"]
    most_consistent = stats["most_consistent"]
    most_volatile    = stats["most_volatile"]
    best_comeback_row = stats["best_comeback_row"]
    best_recovery    = stats["best_recovery"]
    best_player_gw = stats["best_player_gw"]
    max_gw       = stats["max_gw"]

    # Charts
    c_cumulative  = chart_cumulative_points(stats)
    c_heatmap     = chart_gw_heatmap(stats)
    c_box         = chart_gw_distribution(stats)
    c_most_owned  = chart_most_owned(stats)
    c_top_perf    = chart_top_performers(stats)
    c_clubs       = chart_club_breakdown(stats)
    c_h2h         = chart_h2h_matrix(stats)
    c_pos_mgr     = chart_pos_by_mgr(stats)

    # Award cards
    awards_html = ""
    awards_html += award_card("🏆", "Champion", str(champion["manager_team_name"]),
                              f"{int(champion['cumulative_points'])} pts total")
    awards_html += award_card("🪑", "Wooden Spoon", str(wooden_spoon["manager_team_name"]),
                              f"{int(wooden_spoon['cumulative_points'])} pts total")
    awards_html += award_card("💥", "Highest Single GW",
                              f"GW{int(best_gw_row['gameweek'])} — {best_gw_row['manager_team_name']}",
                              f"{int(best_gw_row['total_gw_points'])} pts")
    awards_html += award_card("😬", "Lowest Single GW",
                              f"GW{int(worst_gw_row['gameweek'])} — {worst_gw_row['manager_team_name']}",
                              f"{int(worst_gw_row['total_gw_points'])} pts")
    awards_html += award_card("🎯", "Most Consistent",
                              str(most_consistent["manager_team_name"]),
                              f"Std dev: {most_consistent['std_gw']:.1f} pts")
    awards_html += award_card("🎲", "Most Volatile",
                              str(most_volatile["manager_team_name"]),
                              f"Std dev: {most_volatile['std_gw']:.1f} pts")
    if best_recovery is not None:
        awards_html += award_card("⬆️", "Best Recovery",
                                  str(best_recovery["team"]),
                                  f"Bounced back to {int(best_recovery['next_pts'])} pts after {int(best_recovery['worst_pts'])} pts worst GW")
    awards_html += award_card("🔝", "Most Weeks in 1st",
                              str(final_gw.sort_values("weeks_first", ascending=False).iloc[0]["manager_team_name"]),
                              f"{int(final_gw.sort_values('weeks_first', ascending=False).iloc[0]['weeks_first'])} gameweeks")
    awards_html += award_card("⭐", "Best Player in a GW",
                              str(best_player_gw["name"]),
                              f"{int(best_player_gw['gw_points'])} pts in GW{int(best_player_gw['gameweek'])} for {best_player_gw['manager_team_name']}")

    # Best by position cards
    best_pos_cards_html = best_by_pos_cards(stats["best_by_pos"])

    # Captain table (empty for draft leagues)
    capt_table_html = ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{league_name} — Season Recap 2025/26</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: {COLORS['dark']};
      color: {COLORS['text_light']};
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      line-height: 1.5;
    }}

    /* ── Hero ── */
    .hero {{
      background: linear-gradient(135deg, {COLORS['purple']} 0%, #1a0050 50%, #000428 100%);
      padding: 60px 24px;
      text-align: center;
      border-bottom: 3px solid {COLORS['green']};
      position: relative;
      overflow: hidden;
    }}
    .hero::before {{
      content: '';
      position: absolute; inset: 0;
      background: radial-gradient(ellipse at 50% 0%, rgba(0,255,135,0.12) 0%, transparent 70%);
    }}
    .hero-tag {{
      display: inline-block;
      background: {COLORS['green']};
      color: {COLORS['purple']};
      font-weight: 700;
      font-size: 0.75rem;
      letter-spacing: 2px;
      text-transform: uppercase;
      padding: 4px 14px;
      border-radius: 20px;
      margin-bottom: 16px;
    }}
    .hero h1 {{
      font-size: clamp(2.2rem, 5vw, 3.5rem);
      font-weight: 900;
      color: {COLORS['white']};
      letter-spacing: -1px;
      position: relative;
    }}
    .hero h1 span {{ color: {COLORS['green']}; }}
    .hero-sub {{
      font-size: 1.1rem;
      color: {COLORS['text_light']};
      margin-top: 10px;
      opacity: 0.8;
    }}
    .champion-banner {{
      display: inline-flex;
      align-items: center;
      gap: 12px;
      background: rgba(0,255,135,0.12);
      border: 1.5px solid {COLORS['green']};
      border-radius: 12px;
      padding: 14px 28px;
      margin-top: 28px;
      font-size: 1.15rem;
      font-weight: 600;
    }}

    /* ── Layout ── */
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 20px;
    }}

    .section {{
      padding: 48px 0;
      border-bottom: 1px solid rgba(150,60,255,0.15);
    }}
    .section h2 {{
      font-size: 1.5rem;
      font-weight: 800;
      color: {COLORS['white']};
      margin-bottom: 28px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .section h2::after {{
      content: '';
      flex: 1;
      height: 1px;
      background: linear-gradient(90deg, rgba(150,60,255,0.5), transparent);
    }}

    /* ── Standings table ── */
    .table-wrapper {{ overflow-x: auto; }}
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}
    .data-table th {{
      background: {COLORS['card_bg']};
      color: {COLORS['green']};
      padding: 12px 14px;
      text-align: left;
      font-weight: 700;
      font-size: 0.8rem;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}
    .data-table td {{
      padding: 11px 14px;
      border-bottom: 1px solid rgba(150,60,255,0.1);
    }}
    .standings-row:hover {{ background: rgba(150,60,255,0.1); }}
    .champion-row td {{ background: rgba(0,255,135,0.07); }}
    .champion-row td:first-child {{ font-size: 1.3rem; }}
    .spoon-row td {{ background: rgba(255,75,75,0.07); }}
    .pts {{ font-weight: 700; color: {COLORS['green']}; font-size: 1.05rem; }}

    /* ── Awards grid ── */
    .awards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 8px;
    }}
    .award-card {{
      background: {COLORS['card_bg']};
      border: 1px solid rgba(150,60,255,0.3);
      border-radius: 12px;
      padding: 20px;
      transition: border-color 0.2s, transform 0.15s;
    }}
    .award-card:hover {{
      border-color: {COLORS['light_purple']};
      transform: translateY(-2px);
    }}
    .award-emoji {{ font-size: 1.8rem; margin-bottom: 8px; }}
    .award-title {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: {COLORS['green']}; margin-bottom: 6px; font-weight: 600; }}
    .award-value {{ font-size: 1rem; font-weight: 700; color: {COLORS['white']}; }}
    .award-sub {{ font-size: 0.8rem; color: {COLORS['text_light']}; margin-top: 4px; opacity: 0.8; }}

    /* ── Charts ── */
    .chart-container {{ width: 100%; min-height: 300px; }}
    .chart-placeholder {{
      background: {COLORS['card_bg']};
      border: 1px dashed rgba(150,60,255,0.3);
      border-radius: 8px;
      padding: 40px;
      text-align: center;
      color: {COLORS['text_light']};
      opacity: 0.6;
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(440px, 1fr));
      gap: 24px;
    }}
    @media (max-width: 700px) {{
      .grid-2 {{ grid-template-columns: 1fr; }}
    }}

    /* ── Footer ── */
    .footer {{
      text-align: center;
      padding: 32px 20px;
      font-size: 0.8rem;
      color: {COLORS['text_light']};
      opacity: 0.5;
    }}
  </style>
</head>
<body>

<!-- ══════════════════════════════ HERO ══════════════════════════════ -->
<div class="hero">
  <div class="hero-tag">End of Season Recap</div>
  <h1>⚽ <span>{league_name}</span></h1>
  <div class="hero-sub">Fantasy Premier League Draft · 2025/26 Season · {max_gw} Gameweeks</div>
  <div class="champion-banner">
    🏆 &nbsp; Champion: <strong style="color:{COLORS['green']}">&nbsp;{champion['manager_team_name']}</strong>
    &nbsp;·&nbsp; {int(champion['cumulative_points'])} points
  </div>
</div>

<div class="container">

<!-- ══════════════════════════ STANDINGS ═════════════════════════════ -->
<section class="section">
  <h2>📊 Final Standings</h2>
  <div class="table-wrapper">
    <table class="data-table">
      <thead>
        <tr>
          <th>Rank</th><th>Team</th><th>Manager</th>
          <th>Total Pts</th><th>Best GW</th><th>Worst GW</th>
          <th>Avg GW</th><th>Weeks 1st</th>
        </tr>
      </thead>
      <tbody>
        {standings_rows(final_gw)}
      </tbody>
    </table>
  </div>
</section>

<!-- ══════════════════════════ SEASON JOURNEY ════════════════════════ -->
<section class="section">
  <h2>📈 Season Journey</h2>
  {chart_div("chart-cumulative", c_cumulative)}
</section>

<!-- ══════════════════════════ HEATMAP ═══════════════════════════════ -->
<section class="section">
  <h2>🌡️ GW Heatmap &amp; Distribution</h2>
  {chart_div("chart-heatmap", c_heatmap)}
  <div style="margin-top:24px">
    {chart_div("chart-box", c_box)}
  </div>
</section>

<!-- ══════════════════════════ AWARDS ════════════════════════════════ -->
<section class="section">
  <h2>🏅 Season Awards</h2>
  <div class="awards-grid">
    {awards_html}
  </div>
</section>

<!-- ══════════════════ BEST PLAYERS BY POSITION ══════════════════════ -->
<section class="section">
  <h2>🎖️ Best Players by Position</h2>
  <div class="awards-grid">
    {best_pos_cards_html}
  </div>
</section>

<!-- ══════════════════════════ CAPTAINS ══════════════════════════════ -->
{capt_table_html}

<!-- ══════════════════════════ PLAYER STATS ══════════════════════════ -->
<section class="section">
  <h2>👕 Player Stats</h2>
  <div class="grid-2">
    {chart_div("chart-most-owned", c_most_owned)}
    {chart_div("chart-top-perf", c_top_perf)}
  </div>
  <div style="margin-top:24px">
    {chart_div("chart-pos-mgr", c_pos_mgr)}
  </div>
  <div style="margin-top:24px">
    {chart_div("chart-clubs", c_clubs)}
  </div>
</section>

<!-- ══════════════════════════ H2H MATRIX ════════════════════════════ -->
<section class="section">
  <h2>⚔️ Head-to-Head Weekly Matrix</h2>
  <p style="font-size:0.85rem;opacity:0.7;margin-bottom:16px">
    Each cell shows how many GWs the row manager outscored the column manager.
  </p>
  {chart_div("chart-h2h", c_h2h)}
</section>

</div><!-- /container -->

<div class="footer">
  Generated by FPL-ETL · {league_name} · Season 2025/26
</div>

</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("🚀 FPL Season Recap Dashboard Generator")
    print("=" * 50)

    d = load_data()
    capt_df = parse_captain_data(d["dim_mgr"], d["gw_full"])
    stats = compute_stats(d, capt_df)
    html = build_html(stats, capt_df)

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"\n✅ Dashboard saved to: {OUTPUT_HTML}")
    print(f"   Open in your browser: file:///{OUTPUT_HTML.as_posix()}")


if __name__ == "__main__":
    main()
