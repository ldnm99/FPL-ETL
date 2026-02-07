# FPL-ETL Medallion Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FPL API                                 │
│              https://draft.premierleague.com/api                │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ API Calls
             │
┌────────────▼────────────────────────────────────────────────────┐
│                     🥉 BRONZE LAYER                             │
│                   (Raw Data - JSON)                             │
├─────────────────────────────────────────────────────────────────┤
│  bronze/                                                        │
│  ├── league_standings_raw.json      ← Direct API response      │
│  ├── players_raw.json                ← bootstrap-static        │
│  ├── gameweeks/                                                 │
│  │   ├── gw_1_raw.json              ← Event live data          │
│  │   └── gw_2_raw.json                                          │
│  └── manager_picks/                                             │
│      ├── gw_1_manager_123.json      ← Manager picks            │
│      └── gw_1_manager_456.json                                  │
│                                                                 │
│  📝 Purpose: Store exact API responses                          │
│  ✅ Benefits: Reprocessable, debuggable, audit trail            │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Transform (clean, validate, type-cast)
             │
┌────────────▼────────────────────────────────────────────────────┐
│                     🥈 SILVER LAYER                             │
│                (Cleaned Data - CSV/Parquet)                     │
├─────────────────────────────────────────────────────────────────┤
│  silver/                                                        │
│  ├── league_standings.csv           ← Cleaned manager data     │
│  ├── players_data.csv                ← Cleaned player data     │
│  ├── gameweeks_parquet/                                         │
│  │   ├── gw_data_gw1.parquet        ← Per-GW stats + picks     │
│  │   └── gw_data_gw2.parquet                                    │
│  └── metadata/                                                  │
│      └── data_quality.json          ← Validation logs          │
│                                                                 │
│  📝 Purpose: Cleaned, validated, consistent format              │
│  ✅ Benefits: Quality assured, analysis-ready                   │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Aggregate (join, calculate, enrich)
             │
┌────────────▼────────────────────────────────────────────────────┐
│                     🥇 GOLD LAYER                               │
│              (Analytics-Ready - Parquet)                        │
├─────────────────────────────────────────────────────────────────┤
│  gold/                                                          │
│  ├── gw_data_full.parquet           ← Full merged dataset      │
│  │   • All gameweeks combined                                   │
│  │   • Enriched with player/manager info                        │
│  │   • Ready for dashboards                                     │
│  │                                                              │
│  ├── player_season_stats.parquet    ← Aggregated player stats  │
│  │   • Total points, goals, assists                             │
│  │   • Average per game                                         │
│  │   • Season summary                                           │
│  │                                                              │
│  └── manager_performance.parquet    ← Manager analytics        │
│      • Points per gameweek                                      │
│      • Cumulative rankings                                      │
│      • Rolling averages                                         │
│                                                                 │
│  📝 Purpose: Business-ready aggregations                        │
│  ✅ Benefits: Optimized for queries, dashboards, ML             │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Upload (with layer prefixes)
             │
┌────────────▼────────────────────────────────────────────────────┐
│                    SUPABASE STORAGE                             │
│                    Bucket: "data"                               │
├─────────────────────────────────────────────────────────────────┤
│  bronze/                            ← Raw JSON files            │
│  silver/                            ← Cleaned CSV/Parquet       │
│  gold/                              ← Analytics Parquet         │
│  last_updated.json                  ← Timestamp tracker         │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Bronze Layer Extraction
```
API Call → Raw JSON → Save to bronze/
```
- **Input**: FPL API endpoints
- **Output**: JSON files (exact API responses)
- **Module**: `src/etl/bronze.py`
- **Functions**:
  - `extract_league_raw()` - League standings
  - `extract_players_raw()` - Player database
  - `extract_gameweek_raw(gw)` - Gameweek stats
  - `extract_manager_picks_raw(manager_id, gw)` - Manager picks

### 2. Silver Layer Transformation
```
bronze/*.json → Clean/Validate → Save to silver/
```
- **Input**: Bronze layer JSON files
- **Output**: CSV/Parquet files (cleaned, typed)
- **Module**: `src/etl/silver.py`
- **Functions**:
  - `transform_league_standings()` - Clean league data
  - `transform_players_data()` - Clean player data
  - `transform_gameweek_data(gw, managers)` - Merge stats + picks
  - `merge_all_gameweeks()` - Combine all GWs

### 3. Gold Layer Aggregation
```
silver/*.parquet → Aggregate/Enrich → Save to gold/
```
- **Input**: Silver layer Parquet files
- **Output**: Analytics-ready Parquet files
- **Module**: `src/etl/gold.py`
- **Functions**:
  - `create_full_gameweek_dataset()` - Complete merged dataset
  - `create_player_season_stats()` - Player aggregations
  - `create_manager_performance()` - Manager metrics

### 4. Upload to Supabase
```
Data/* → Upload with layer prefix → Supabase Storage
```
- **Input**: All layer files
- **Output**: Organized Supabase bucket
- **Module**: `src/etl/upload_database.py`
- **Functions**:
  - `upload_bronze_layer()` - Upload raw JSONs
  - `upload_silver_layer()` - Upload cleaned data
  - `upload_gold_layer()` - Upload analytics

## Pipeline Orchestration

### Main Pipeline (`src/main_medallion.py`)
```python
def run_pipeline():
    run_bronze_layer()    # Extract raw data
    run_silver_layer()    # Transform to cleaned
    run_gold_layer()      # Create analytics
    run_upload()          # Upload to Supabase
```

**Execution**:
```bash
python -m src.main_medallion
```

## Configuration (`src/config.py`)

Centralized configuration for all paths and settings:

```python
config = Config()

# Paths
config.BRONZE_DIR      # Data/bronze
config.SILVER_DIR      # Data/silver
config.GOLD_DIR        # Data/gold

# Bronze files
config.BRONZE_LEAGUE_RAW       # league_standings_raw.json
config.BRONZE_PLAYERS_RAW      # players_raw.json
config.get_bronze_gameweek_path(1)  # bronze/gameweeks/gw_1_raw.json

# Silver files
config.SILVER_LEAGUE_CSV       # league_standings.csv
config.SILVER_PLAYERS_CSV      # players_data.csv
config.get_silver_gameweek_path(1)  # silver/gameweeks_parquet/gw_data_gw1.parquet

# Gold files
config.GOLD_GW_DATA_FULL           # gw_data_full.parquet
config.GOLD_PLAYER_SEASON_STATS    # player_season_stats.parquet
config.GOLD_MANAGER_PERFORMANCE    # manager_performance.parquet
```

## Layer Characteristics

| Aspect | Bronze 🥉 | Silver 🥈 | Gold 🥇 |
|--------|----------|----------|---------|
| **Format** | JSON | CSV/Parquet | Parquet |
| **Source** | API | Bronze | Silver |
| **Quality** | Raw | Validated | Aggregated |
| **Schema** | Variable | Consistent | Optimized |
| **Size** | ~20 MB | ~15 MB | ~8 MB |
| **Use Case** | Debugging, Audit | ETL, Validation | Analytics, ML |
| **Retention** | 90 days (optional) | Forever | Forever |

## Reprocessing Capabilities

### Scenario 1: API Structure Changed
```bash
# Fix transformation logic in silver.py, then:
python -m src.etl.silver  # Reprocess from Bronze
python -m src.etl.gold    # Recreate Gold
python -m src.etl.upload_database  # Re-upload
```

### Scenario 2: New Gold Aggregation Needed
```bash
# Add function to gold.py, then:
python -m src.etl.gold    # Only reprocess Gold layer
python -m src.etl.upload_database  # Upload new Gold files
```

### Scenario 3: Data Quality Issue Detected
```bash
# Check Bronze layer (raw data):
cat Data/bronze/players_raw.json

# Fix Silver transformation:
python -m src.etl.silver

# Recreate Gold:
python -m src.etl.gold
```

## Benefits Summary

### 🎯 Data Lineage
Track data from source → cleaned → aggregated

### ♻️ Reprocessability
Rerun transformations without API calls (saves rate limits)

### 🔍 Debugging
Inspect raw responses when issues occur

### 📈 Scalability
Add new Gold datasets without touching Bronze/Silver

### ✅ Quality
Each layer is a quality checkpoint

### 💰 Cost Efficiency
Store raw data, reprocess cheaply (no API calls)

## Storage Breakdown

```
Total: ~44 MB

Bronze:  ~20 MB (40 gameweeks × ~500 KB each)
Silver:  ~15 MB (same as before)
Gold:    ~8 MB  (3 aggregated files)
```

**Cost**: Free tier (1 GB included) ✅

## Access Patterns

### For Analytics/Dashboards
→ Use **Gold layer** (optimized for queries)

### For ETL/Data Engineering
→ Use **Silver layer** (clean, consistent)

### For Debugging/Audit
→ Use **Bronze layer** (raw truth)

## Next Steps

1. Run pipeline: `python -m src.main_medallion`
2. Verify Supabase: Check `data` bucket for bronze/silver/gold folders
3. Explore Gold datasets: Load in Pandas/SQL for analysis
4. Update dashboards: Point to Gold layer files
5. Set up retention: Auto-delete old Bronze files (optional)

---

**Status**: ✅ Medallion architecture fully implemented and documented
