# Project Structure Guide

## Overview

The FPL-ETL project is organized into a clean, maintainable structure with separation of concerns.

## Directory Tree

```
FPL-ETL/
├── src/                              # Source code directory
│   ├── __init__.py                  # Package initialization
│   ├── main.py                      # Pipeline entry point
│   ├── utils.py                     # Shared utilities & helpers
│   │
│   └── etl/                         # ETL modules package
│       ├── __init__.py              # Package initialization
│       ├── league.py                # League standings extraction
│       ├── players.py               # Player data extraction
│       ├── merge_players_data.py    # Gameweek data merging & processing
│       └── upload_database.py       # Supabase storage upload
│
├── data/                             # Generated output (auto-created, .gitignored)
│   ├── league_standings.csv         # Extracted league data
│   ├── players_data.csv             # Extracted player data
│   ├── gw_data.parquet              # Final merged dataset
│   └── gameweeks_parquet/           # Individual gameweek parquet files
│       ├── gw_data_gw1.parquet
│       ├── gw_data_gw2.parquet
│       └── ...
│
├── docs/                             # Documentation
│   ├── PROJECT_STRUCTURE.md         # This file
│   └── DEPENDENCY_MANAGEMENT.md     # Dependency management guide
│
├── .github/
│   └── workflows/
│       └── etl.yml                  # GitHub Actions CI/CD pipeline
│
├── .env                             # Environment variables (not committed, .gitignored)
├── .env.example                     # Environment template (committed)
├── .gitignore                       # Git ignore rules
├── README.md                        # Main project documentation
├── requirements.txt                 # Direct dependencies (loose versions)
├── requirements.lock                # Locked dependency tree (exact versions)
└── [other config files]
```

## Module Descriptions

### `src/main.py`
**Purpose:** Pipeline orchestrator and entry point  
**Key Functions:**
- `run_pipeline()` - Orchestrates the full ETL pipeline
- Imports and calls modules in sequence: league → players → merge → upload

**Usage:**
```bash
python -m src.main
cd src && python main.py
```

### `src/utils.py`
**Purpose:** Shared utilities and helper functions  
**Key Functions:**
- `fetch_data()` - Generic API fetching with retries
- `save_csv()` - CSV file writing utilities
- `load_csv()` - CSV file reading utilities
- `fetch_managers_ids()` - Extract manager IDs from standings
- `fetch_players_data()` - Fetch player data from local database
- `get_player_gw_data()` - Fetch gameweek-specific player stats

**Used By:** All ETL modules

### `src/etl/league.py`
**Purpose:** Extract league standings data  
**Key Functions:**
- `get_league_standings()` - Fetch and save league data to CSV

**Outputs:** `data/league_standings.csv`

### `src/etl/players.py`
**Purpose:** Extract and process player data  
**Key Functions:**
- `get_player_data()` - Fetch all players and save to CSV

**Outputs:** `data/players_data.csv`

### `src/etl/merge_players_data.py`
**Purpose:** Merge gameweek data with player stats and manager picks  
**Key Functions:**
- `main()` - Orchestrate gameweek data processing
- `fetch_current_gameweek()` - Get current GW number
- `load_players()` - Load player data from CSV
- `build_gameweek_data()` - Process single gameweek
- `save_gameweek()` - Save gameweek to parquet
- `merge_all_gameweeks()` - Combine all GW files
- `rename_columns()` - Standardize column names

**Logic:**
1. Detect gaps in historical gameweek data
2. Backfill missing gameweeks (if any)
3. Always update current-1 and current gameweeks (incremental)
4. Merge all gameweeks into master file

**Outputs:** `data/gameweeks_parquet/`, `data/gw_data.parquet`

### `src/etl/upload_database.py`
**Purpose:** Upload processed data to Supabase  
**Key Functions:**
- `main()` - Upload all data files
- `upload_csv()` - Upload CSV to Supabase
- `upload_parquet()` - Upload Parquet to Supabase

**Outputs:** Files uploaded to Supabase storage bucket `data`

## Data Flow

```
FPL API
    ↓
┌─────────────────────┐
│ league.py           │ → data/league_standings.csv
│ (get_league_data)   │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ players.py          │ → data/players_data.csv
│ (get_player_data)   │
└─────────────────────┘
    ↓
┌──────────────────────────┐
│ merge_players_data.py    │
│ (main)                   │
├──────────────────────────┤
│ • Fetch GW data          │ → data/gameweeks_parquet/
│ • Fetch manager picks    │    gw_data_gw1.parquet
│ • Merge with player data │    gw_data_gw2.parquet
│ • Combine all GWs        │    ...
└──────────────────────────┘
    ↓
    ├─→ data/gw_data.parquet (merged all gameweeks)
    │
┌─────────────────────┐
│ upload_database.py  │ → Supabase Storage
│ (main)              │
└─────────────────────┘
```

## Import Pattern

### From Root Directory
```python
# Run as module
python -m src.main

# In Python code
from src.etl.league import get_league_standings
from src.utils import fetch_data
```

### From src Directory
```bash
cd src
python main.py
```

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Runtime environment variables (not committed) |
| `.env.example` | Template for users (committed) |
| `requirements.txt` | Direct dependencies with ranges |
| `requirements.lock` | Locked dependencies (all transitive) |
| `.gitignore` | Git ignore patterns |

## Output Files

All data files are auto-generated and stored in `data/` directory:

| File | Format | Purpose |
|------|--------|---------|
| `league_standings.csv` | CSV | Manager info & team names |
| `players_data.csv` | CSV | Player demographics & season stats |
| `gameweeks_parquet/` | Directory | Individual gameweek files |
| `gw_data.parquet` | Parquet | Complete merged dataset |

All files are automatically uploaded to Supabase storage bucket `data`.

## Adding New Modules

To add a new ETL module:

1. **Create file** in `src/etl/new_module.py`
2. **Add imports** at top:
   ```python
   import logging
   from src.utils import fetch_data  # if needed
   ```
3. **Define functions** with docstrings
4. **Import in** `src/etl/__init__.py`:
   ```python
   from . import new_module
   ```
5. **Call from** `src/main.py`:
   ```python
   from src.etl import new_module
   new_module.main()
   ```

## Performance Considerations

### Incremental Processing
- **First run:** Fetches all GW1 through GWcurrent
- **Subsequent runs:** Only fetches GW(current-1) and GWcurrent
- **API calls reduced:** ~90% after first run

### Caching
- GitHub Actions uses pip cache for dependencies
- **First run:** 18s (downloads all packages)
- **Cached runs:** 2-3s (uses cache)

### Dependency Management
- `requirements.lock` pre-resolves all dependencies
- No time spent on dependency resolution in CI/CD
- Exact reproducibility across runs

## Testing & Validation

All modules include:
- ✅ Error handling with try-except
- ✅ Comprehensive logging
- ✅ File existence validation
- ✅ Type hints on functions
- ✅ Docstrings explaining purpose

Run syntax check:
```bash
python -m py_compile src/main.py src/utils.py src/etl/*.py
```

Run linting:
```bash
pylint src/**/*.py
```

