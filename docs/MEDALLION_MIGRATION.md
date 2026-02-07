# Medallion Architecture Migration Guide

## Overview

The FPL-ETL project has been upgraded to use a **medallion architecture** with three distinct data layers:

- 🥉 **Bronze**: Raw data exactly as received from API (JSON)
- 🥈 **Silver**: Cleaned and validated data (CSV/Parquet)
- 🥇 **Gold**: Analytics-ready aggregated datasets (Parquet)

## What Changed

### Before (Flat Structure)
```
Data/
├── league_standings.csv
├── players_data.csv
├── gw_data.parquet
└── gameweeks_parquet/
```

### After (Medallion Structure)
```
Data/
├── bronze/                         # Raw API responses
│   ├── league_standings_raw.json
│   ├── players_raw.json
│   ├── gameweeks/
│   │   └── gw_1_raw.json
│   └── manager_picks/
│       └── gw_1_manager_123.json
│
├── silver/                         # Cleaned data
│   ├── league_standings.csv
│   ├── players_data.csv
│   └── gameweeks_parquet/
│       └── gw_data_gw1.parquet
│
└── gold/                           # Analytics datasets
    ├── gw_data_full.parquet
    ├── player_season_stats.parquet
    └── manager_performance.parquet
```

## New Files Added

### Core Modules
- `src/config.py` - Centralized configuration with medallion paths
- `src/etl/bronze.py` - Bronze layer extraction (raw data)
- `src/etl/silver.py` - Silver layer transformation (cleaned data)
- `src/etl/gold.py` - Gold layer aggregation (analytics)
- `src/main_medallion.py` - New pipeline orchestrator

### Updated Files
- `src/etl/upload_database.py` - Now uploads to bronze/, silver/, gold/ paths in Supabase

## How to Use

### Option 1: Run New Medallion Pipeline (Recommended)

```bash
# Set environment variables
export FPL_LEAGUE_ID='24636'
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_SERVICE_KEY='your-service-key'

# Run new medallion pipeline
python -m src.main_medallion
```

This will:
1. Extract raw data to Bronze layer (JSON files)
2. Transform to Silver layer (cleaned CSV/Parquet)
3. Aggregate to Gold layer (analytics Parquet)
4. Upload all layers to Supabase with proper folder structure

### Option 2: Run Individual Layers

```python
# Bronze layer only (extract raw data)
python -m src.etl.bronze

# Silver layer only (transform data)
python -m src.etl.silver

# Gold layer only (create analytics)
python -m src.etl.gold

# Upload only
python -m src.etl.upload_database
```

### Option 3: Keep Using Old Pipeline

The original `src/main.py` still exists and works, but uses the old flat structure.

```bash
python -m src.main  # Old pipeline (still functional)
```

## Supabase Changes

Your Supabase bucket structure will automatically become:

```
data/  (bucket)
├── bronze/
│   ├── league_standings_raw.json
│   ├── players_raw.json
│   ├── gameweeks/
│   │   └── gw_1_raw.json
│   └── manager_picks/
│       └── gw_1_manager_123.json
│
├── silver/
│   ├── league_standings.csv
│   ├── players_data.csv
│   └── gameweeks_parquet/
│       └── gw_data_gw1.parquet
│
└── gold/
    ├── gw_data_full.parquet
    ├── player_season_stats.parquet
    └── manager_performance.parquet
```

**No manual folder creation needed** - Supabase creates folders automatically when files are uploaded with path prefixes.

## New Gold Layer Datasets

### 1. Full Gameweek Dataset (`gold/gw_data_full.parquet`)
Complete dataset with all gameweeks, enriched with player and manager info.

**Columns**: ID, name, team, position, gameweek, gw_points, gw_minutes, gw_goals, gw_assists, manager_id, manager_team_name, season_points, etc.

### 2. Player Season Stats (`gold/player_season_stats.parquet`)
Aggregated player-level statistics for the season.

**Columns**: ID, name, team, position, total_points, avg_points, max_points, total_goals, total_assists, gameweeks_played, points_per_game, etc.

### 3. Manager Performance (`gold/manager_performance.parquet`)
Manager performance metrics over time.

**Columns**: manager_id, gameweek, manager_team_name, total_gw_points, cumulative_points, rolling_avg_3gw, gw_rank

## Benefits of Medallion Architecture

### 1. Data Lineage
Trace data from raw API → cleaned → aggregated

### 2. Reprocessability
Rerun Silver/Gold layers without re-calling APIs (saves API calls)

```bash
# Reprocess Silver layer from existing Bronze data
python -m src.etl.silver

# Reprocess Gold layer from existing Silver data
python -m src.etl.gold
```

### 3. Debugging
Inspect raw API responses when issues occur

```python
# Check raw API response
import json
with open('Data/bronze/players_raw.json') as f:
    raw_data = json.load(f)
```

### 4. Scalability
Easy to add new Gold layer aggregations without touching Bronze/Silver

### 5. Data Quality
Each layer acts as a quality checkpoint

## Migration Steps

### Step 1: Update Environment Variables (Already Done)
Your existing environment variables work as-is.

### Step 2: Run New Pipeline
```bash
python -m src.main_medallion
```

### Step 3: Verify Supabase
Check your Supabase Storage → `data` bucket → you should see `bronze/`, `silver/`, `gold/` folders.

### Step 4: Update Downstream Apps (If Any)
If you have dashboards or apps reading from Supabase:

**Before:**
```python
# Old path
url = supabase.storage.from_('data').get_public_url('gw_data.parquet')
```

**After:**
```python
# New path (Gold layer recommended for analytics)
url = supabase.storage.from_('data').get_public_url('gold/gw_data_full.parquet')
```

## Backward Compatibility

The old pipeline (`src/main.py`) still works. You can:
- Keep using it while testing the new one
- Run both pipelines in parallel
- Gradually migrate to the new pipeline

## Storage Impact

**Before**: ~15 MB
**After**: ~44 MB (Bronze + Silver + Gold)

Still well within Supabase free tier (1 GB included).

## Troubleshooting

### Issue: "Bronze file not found"
**Solution**: Run Bronze layer first
```bash
python -m src.etl.bronze
```

### Issue: "Missing SUPABASE_URL"
**Solution**: Set environment variables
```bash
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_SERVICE_KEY='your-key'
```

### Issue: "No gameweek data available"
**Solution**: Ensure Bronze layer has data for the gameweek
```bash
# Check if Bronze data exists
ls Data/bronze/gameweeks/
```

## GitHub Actions Update

To use the new pipeline in GitHub Actions:

```yaml
# .github/workflows/etl.yml
- name: Run ETL pipeline
  run: python -m src.main_medallion  # Changed from: python -m src.main
```

## Next Steps

1. ✅ Run the new pipeline: `python -m src.main_medallion`
2. ✅ Verify data in Supabase Storage (bronze/, silver/, gold/ folders)
3. ✅ Explore new Gold layer datasets
4. Optional: Update README.md with medallion architecture
5. Optional: Update GitHub Actions workflow

## Questions?

- Check `src/config.py` for all path configurations
- Check individual layer modules (`bronze.py`, `silver.py`, `gold.py`) for details
- Review the plan in `.copilot/session-state/.../plan.md`

---

**Status**: ✅ Medallion architecture implemented and ready to use!
