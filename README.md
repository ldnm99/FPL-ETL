# ⚡ FPL-ETL: Fantasy Premier League Data Pipeline & Live Auto-Sync

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Status](https://img.shields.io/badge/Status-Production-brightgreen)
![Database](https://img.shields.io/badge/Database-Supabase_PostgreSQL-emerald)
![Live Sync](https://img.shields.io/badge/Live_Sync-Background_Daemon-purple)

A production-ready ETL pipeline and live auto-sync engine for Fantasy Premier League (FPL) Draft data using **Supabase PostgreSQL** and **Dimensional Star Schema Modeling**.

---

## 🎯 System Overview

```
FPL Draft API → Python ETL Engine → Supabase PostgreSQL → SQL Analytical Views → React Web App
```

* **Live Data Engine:** Extracts live player stats, bonus points (BPS), and match scores directly from official FPL Draft APIs (`draft.premierleague.com`).
* **Supabase PostgreSQL Integration:** Loads cleaned star-schema records into `dim_clubs`, `dim_players`, `dim_managers`, `dim_gameweeks`, `dim_fixtures`, `fact_manager_picks`, and `fact_player_performance`.
* **Automated Views:** Instant computation of standings, starter totals, and bench points via `vw_manager_standings` and `vw_draft_gameweek_overview`.

---

## 🚀 Key ETL Features

### ⚡ 1. Fast Live Sync Mode
* Sub-2-second execution mode skipping static metadata for rapid live match updates.
* Automatically detects active gameweeks (`is_current = True`) and synchronizes all completed & active gameweeks dynamically.

### 🔁 2. Real-Time Auto-Sync Daemon (`--loop`)
* Continuous background daemon mode polling FPL Draft API every **60 seconds** during live matchdays.
* Automatically captures live goals, assists, yellow cards, clean sheets, and bonus points as they occur in real life.

### 🧹 3. Mistake-League Purging
* Automated cleanup purging stale manager records from previous or mistyped league IDs before upserting active managers.

---

## 💻 Running the Live Pipeline

```bash
# 1. Run single fast live sync
python src/etl/sync_fpl_draft_to_supabase.py

# 2. Run full metadata sync (Clubs, Players, Gameweeks)
python src/etl/sync_fpl_draft_to_supabase.py --full

# 3. Start background live auto-sync daemon (60s loop)
python src/etl/sync_fpl_draft_to_supabase.py --loop 60
```

---

## 📊 Star Schema Data Model

```
dim_clubs (20) ────→ dim_players (622) ────→ fact_player_performance (622/GW)
                          │
dim_managers (7) ─────────┼───────────────→ fact_manager_picks (105/GW)
                          │
dim_gameweeks (38) ───────┴───────────────→ dim_fixtures (380)
```

---

## 🛠️ Configuration & Credentials

Set environment variables in `.env`:

```env
SUPABASE_URL=https://xgesjwvsdatcqrzudoyg.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-key
FPL_LEAGUE_ID=38279
```

---

**Built with ❤️ for FPL Draft League Analytics**