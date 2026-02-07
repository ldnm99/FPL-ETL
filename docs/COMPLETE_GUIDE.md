# FPL-ETL Complete Guide

**Version**: 2.0.0  
**Last Updated**: February 7, 2026

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Data Model](#data-model)
4. [Usage Examples](#usage-examples)
5. [API Reference](#api-reference)
6. [Deployment](#deployment)

---

## Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd FPL-ETL

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Windows PowerShell
$env:FPL_LEAGUE_ID = '24636'
$env:SUPABASE_URL = 'https://your-project.supabase.co'
$env:SUPABASE_SERVICE_KEY = 'your-service-key'
```

### 3. Run Pipeline

```bash
python -m src.main_medallion
```

### 4. Query Data

```python
import pandas as pd

# Load player seasonal stats (70+ columns)
seasonal = pd.read_parquet('Data/gold/facts/fact_player_seasonal_stats.parquet')
print(seasonal[['name', 'total_points', 'form', 'now_cost']])
```

---

## Architecture

### Medallion Layers

```
🥉 Bronze (Raw)
├── Incremental: Last 2 gameweeks only
├── Format: JSON
└── Purpose: Raw API responses

🥈 Silver (Cleaned)
├── Validated data
├── Format: CSV/Parquet
└── Purpose: Clean, typed data

🥇 Gold (Analytics)
├── Star schema
├── Format: Parquet
└── Purpose: Dimensional model
```

### Pipeline Flow

```
FPL API → Bronze → Silver → Gold → Supabase
          (JSON)  (CSV)   (Star)   (Cloud)
```

---

## Data Model

### Dimensions (5 Tables)

#### dim_clubs
Premier League teams
```
club_id (PK)
club_name
short_name
```

#### dim_players
Players with ALL 70+ columns
```
player_id (PK)
name
club_id (FK → dim_clubs)
position
total_points
form
xG, xA
now_cost
... (70+ total)
```

#### dim_managers
FPL managers
```
manager_id (PK)
first_name
last_name
team_name
```

#### dim_gameweeks
Gameweek calendar
```
gameweek_id (PK)
gameweek_num
is_finished
is_current
```

#### dim_fixtures
Matches with difficulty ratings
```
fixture_id (PK)
gameweek_id (FK → dim_gameweeks)
home_club_id (FK → dim_clubs)
away_club_id (FK → dim_clubs)
home_difficulty (1-5)
away_difficulty (1-5)
kickoff_time
is_finished
```

### Facts (4 Tables)

#### fact_player_performance
Gameweek-specific stats
```
performance_id (PK)
player_id (FK → dim_players)
gameweek_id (FK → dim_gameweeks)
gw_points
gw_goals
gw_assists
gw_minutes
...
```

#### fact_player_seasonal_stats
Season totals (70+ columns)
```
seasonal_stats_id (PK)
player_id (FK → dim_players)
total_points
goals
assists
xG, xA
form
now_cost
... (70+ total)
```

#### fact_manager_picks
Manager selections
```
pick_id (PK)
manager_id (FK → dim_managers)
player_id (FK → dim_players)
gameweek_id (FK → dim_gameweeks)
position
```

#### manager_gameweek_performance
Denormalized (all joins pre-computed)
```
gameweek_num
manager_id
manager_team_name
player_id
player_name
club_name
gw_points
gw_goals
...
```

---

## Usage Examples

### Example 1: Player Seasonal Stats

```python
import pandas as pd

# Load seasonal stats
seasonal = pd.read_parquet('Data/gold/facts/fact_player_seasonal_stats.parquet')

# Best value players (high form, low cost)
value = seasonal[
    (seasonal['form'] > 5.0) &
    (seasonal['now_cost'] < 80)
].sort_values('PpG', ascending=False)

print(value[['name', 'position', 'total_points', 'form', 'now_cost']].head(10))
```

### Example 2: Manager's Team Performance

```python
# Load denormalized table
df = pd.read_parquet('Data/gold/facts/manager_gameweek_performance.parquet')

# Get specific manager's team for gameweek 10
team = df[(df['manager_id'] == 123) & (df['gameweek_num'] == 10)]

print(team[['player_name', 'club_name', 'player_position', 
            'gw_points', 'gw_goals', 'gw_assists']])
```

### Example 3: Fixtures with Difficulty

```python
# Load fixtures and clubs
fixtures = pd.read_parquet('Data/gold/dimensions/dim_fixtures.parquet')
clubs = pd.read_parquet('Data/gold/dimensions/dim_clubs.parquet')

# Join home team
fixtures_full = fixtures.merge(
    clubs.add_suffix('_home'),
    left_on='home_club_id',
    right_on='club_id_home'
).merge(
    clubs.add_suffix('_away'),
    left_on='away_club_id',
    right_on='club_id_away'
)

# Easy home fixtures
easy = fixtures_full[
    (fixtures_full['home_difficulty'] <= 2) &
    (fixtures_full['is_finished'] == False)
]

print(easy[['club_name_home', 'club_name_away', 'home_difficulty', 'kickoff_time']])
```

### Example 4: Player Performance Trend

```python
# Load gameweek stats
gw_stats = pd.read_parquet('Data/gold/facts/fact_player_performance.parquet')
players = pd.read_parquet('Data/gold/dimensions/dim_players.parquet')

# Get Salah's performance over time
salah_id = players[players['name'] == 'M. Salah']['player_id'].iloc[0]
salah_perf = gw_stats[gw_stats['player_id'] == salah_id].sort_values('gameweek_id')

print(salah_perf[['gameweek_id', 'gw_points', 'gw_goals', 'gw_assists']])
```

### Example 5: Club Players Analysis

```python
# Load dimensions
players = pd.read_parquet('Data/gold/dimensions/dim_players.parquet')
clubs = pd.read_parquet('Data/gold/dimensions/dim_clubs.parquet')

# Join and filter
players_clubs = players.merge(clubs, on='club_id')

# Liverpool players
liverpool = players_clubs[players_clubs['club_name'] == 'Liverpool']

print(liverpool[['name', 'position', 'total_points', 'form', 'now_cost']].sort_values('total_points', ascending=False))
```

---

## API Reference

### Bronze Layer

```python
from src.etl import bronze

# Extract last 2 gameweeks (incremental)
bronze.extract_recent_gameweeks(num_gameweeks=2)

# Extract specific components
bronze.extract_league_raw()
bronze.extract_players_raw()
bronze.extract_gameweek_raw(gameweek=10)
```

### Silver Layer

```python
from src.etl import silver

# Transform league data
silver.transform_league_standings()

# Transform player data (all 70+ columns preserved)
silver.transform_players_data()

# Transform gameweek data
silver.transform_gameweek_data(gameweek=10, manager_ids=[123, 456])
```

### Gold Layer

```python
from src.etl import gold_dimensions, gold_facts

# Create dimensions
gold_dimensions.create_dim_clubs()
gold_dimensions.create_dim_players()  # 70+ columns
gold_dimensions.create_dim_fixtures()  # With difficulty

# Create facts
gold_facts.create_fact_player_performance()  # Gameweek stats
gold_facts.create_fact_player_seasonal_stats()  # Season totals
```

---

## Deployment

### Local Development

```bash
# Run pipeline
python -m src.main_medallion

# Run individual layers
python -m src.etl.bronze
python -m src.etl.silver
python -m src.etl.gold
```

### GitHub Actions (Automated)

```yaml
name: FPL ETL Pipeline

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  etl:
    runs-on: ubuntu-latest
    env:
      SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
      SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
      FPL_LEAGUE_ID: ${{ secrets.FPL_LEAGUE_ID }}
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run pipeline
        run: python -m src.main_medallion
```

### Supabase Setup

1. Create Supabase account
2. Create new project
3. Create storage bucket named `data` (public)
4. Get credentials:
   - Project URL: Settings → API
   - Service Key: Settings → API → Service Role Key

No manual folder creation needed - folders are created automatically!

---

## Performance

### Bronze Layer - Incremental Updates

**Before**: Extract all 38 gameweeks  
**After**: Extract last 2 gameweeks only  
**Improvement**: 95% faster ⚡

### Data Size

```
Bronze:  ~20 MB  (raw JSON)
Silver:  ~15 MB  (cleaned CSV/Parquet)
Gold:    ~10 MB  (star schema)
Total:   ~45 MB  (well within free tier)
```

### Query Performance

- **Denormalized table**: Instant (no joins)
- **Star schema**: Fast (indexed dimensions)
- **Bronze reprocessing**: No API calls needed

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Check Python path, run from project root |
| Missing Bronze data | Run: `python -m src.etl.bronze` |
| Supabase upload fails | Verify credentials and bucket name |
| Empty dataframes | Check Bronze layer has data |
| API timeout | FPL API down, wait and retry |

---

## Best Practices

✅ **Use denormalized table** for dashboards (fast)  
✅ **Use star schema** for complex analysis (flexible)  
✅ **Reprocess from Bronze** when transform logic changes  
✅ **Query seasonal stats** for current form/value  
✅ **Query gameweek stats** for historical performance  
✅ **Check fixture difficulty** before transfers  

---

## FAQ

**Q: Why incremental Bronze updates?**  
A: Saves API calls and time. Historical data rarely changes.

**Q: Where are all 70+ player columns?**  
A: In `dim_players` and `fact_player_seasonal_stats`

**Q: What's the difference between seasonal and gameweek stats?**  
A: Seasonal = accumulated totals, Gameweek = per-GW performance

**Q: How do I update old gameweeks?**  
A: Modify `extract_recent_gameweeks(num_gameweeks=10)` to fetch more

**Q: Can I add more dimensions?**  
A: Yes! Create new table in `gold_dimensions.py` and add relationships

---

**For more details**: See `docs/fpl_etl_visualization.html` (open in browser)
