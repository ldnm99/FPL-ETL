# FPL-ETL: Fantasy Premier League Data Pipeline

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Status](https://img.shields.io/badge/Status-Production-brightgreen)
![Architecture](https://img.shields.io/badge/Architecture-Medallion-gold)
![Model](https://img.shields.io/badge/Model-Star_Schema-purple)

A production-ready ETL pipeline for Fantasy Premier League (FPL) draft league data using **medallion architecture** (Bronze, Silver, Gold layers) and **dimensional modeling** (star schema) for analytics.

## 🎯 Architecture Overview

```
FPL API → Bronze (Raw JSON) → Silver (Cleaned Parquet) → Gold (Star Schema) → Supabase
```

**Bronze Layer**: Raw data extraction (last 2 gameweeks)  
**Silver Layer**: Cleaned and validated parquet files  
**Gold Layer**: Star schema with 5 dimensions + 4 fact tables

---

## 🚀 Quick Start

### Installation

```bash
# 1. Clone repository
git clone https://github.com/ldnm99/FPL-ETL.git
cd FPL-ETL

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your SUPABASE_URL and SUPABASE_SERVICE_KEY
```

### Running the Pipeline

```bash
# Run complete ETL pipeline (Bronze → Silver → Gold → Upload)
python -m src.main_medallion
```

**What it does:**
- ✅ Extracts last 2 gameweeks from FPL API (Bronze)
- ✅ Transforms to cleaned parquet files (Silver)
- ✅ Creates star schema dimensions and facts (Gold)
- ✅ Uploads all layers to Supabase storage

---

## 📊 Data Model

### Star Schema (Gold Layer)

**Dimensions:**
- `dim_players` - Player master data
- `dim_clubs` - Team information
- `dim_managers` - League managers
- `dim_gameweeks` - Gameweek metadata
- `dim_fixtures` - Match fixtures

**Facts:**
- `fact_player_performance` - Player stats per gameweek (70+ columns)
- `fact_manager_picks` - Manager team selections
- `fact_player_seasonal_stats` - Season aggregations
- `manager_gameweek_performance` - Denormalized view for dashboards

### Enhanced Statistics

All 70+ FPL statistics including:
- Basic: Points, minutes, goals, assists, clean sheets
- Advanced: xG, xA, xGi, xGc, ICT index
- Defensive: Tackles, clearances, recoveries
- Goalkeeping: Saves, penalties saved

---

## 📁 Project Structure

```
FPL-ETL/
├── src/
│   ├── main_medallion.py           # Pipeline orchestrator
│   ├── config.py                   # Configuration
│   ├── utils.py                    # Shared utilities
│   └── etl/
│       ├── bronze.py               # Raw data extraction
│       ├── silver.py               # Data transformation
│       ├── gold.py                 # Gold layer coordinator
│       ├── gold_dimensions.py      # Dimension tables
│       ├── gold_facts.py           # Fact tables
│       ├── gold_seasonal_stats.py  # Aggregations
│       └── upload_database.py      # Supabase upload
├── Data/
│   ├── bronze/                     # Raw JSON files
│   ├── silver/                     # Cleaned parquet files
│   └── gold/                       # Star schema parquet files
│       ├── dimensions/
│       └── facts/
├── docs/                           # Documentation
├── .github/workflows/etl.yml       # GitHub Actions
├── requirements.txt
└── README.md
```

---

## 🔄 Automated Runs

The pipeline runs automatically via GitHub Actions:
- **Weekly**: Every Saturday at 2 AM UTC (after gameweek)
- **Manual**: Trigger from GitHub Actions UI
- **API**: Repository dispatch event

See [`.github/workflows/etl.yml`](.github/workflows/etl.yml) for configuration.

---

## 📚 Documentation

- [**MEDALLION_ARCHITECTURE.md**](docs/MEDALLION_ARCHITECTURE.md) - Detailed architecture explanation
- [**DIMENSIONAL_MODEL.md**](docs/DIMENSIONAL_MODEL.md) - Star schema design
- [**UPDATED_DIMENSIONAL_MODEL.md**](docs/UPDATED_DIMENSIONAL_MODEL.md) - Latest enhancements
- [**ENHANCED_GAMEWEEK_STATS.md**](docs/ENHANCED_GAMEWEEK_STATS.md) - All 70+ statistics
- [**GITHUB_ACTIONS_GUIDE.md**](docs/GITHUB_ACTIONS_GUIDE.md) - CI/CD setup
- [**QUICK_REFERENCE.md**](docs/QUICK_REFERENCE.md) - Command reference

---

## 🛠️ Configuration

Edit `src/config.py` to customize:

```python
LEAGUE_ID = "24636"  # Your FPL Draft league ID
BASE_URL = "https://draft.premierleague.com/api"
```

Environment variables (`.env`):
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
```

---

## 🔍 Key Features

✅ **Incremental Updates** - Only processes last 2 gameweeks (95% faster)  
✅ **Star Schema** - Optimized for analytics queries  
✅ **Complete Statistics** - All 70+ FPL data points  
✅ **Automated Runs** - GitHub Actions weekly schedule  
✅ **Cloud Storage** - Supabase object storage  
✅ **Type Safe** - Full type hints throughout  
✅ **Logging** - Comprehensive pipeline logging  

---

## 📈 Performance

- **Full load (25 GWs)**: ~2 minutes
- **Incremental (2 GWs)**: ~15 seconds
- **Data volume**: ~280KB total (compressed parquet)
- **Gameweek stats**: 70+ columns per player

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

MIT License - See LICENSE file for details

---

## 🔗 Related Projects

- **Frontend Dashboard**: [fpl_draft_frontend](https://github.com/ldnm99/fpl_draft_frontend)
- Uses this ETL pipeline's Gold layer for visualizations

---

**Built with ❤️ for FPL Draft League Analytics**

## 📁 Project Structure

```
FPL-ETL/
├── src/                              # Source code
│   ├── config.py                    # Centralized configuration
│   ├── utils.py                     # API helpers & utilities
│   ├── main_medallion.py            # Main pipeline orchestrator
│   └── etl/                         # ETL modules
│       ├── bronze.py                # Bronze: Raw data extraction (incremental)
│       ├── silver.py                # Silver: Data cleaning & validation
│       ├── gold.py                  # Gold: Aggregations
│       ├── gold_dimensions.py       # Gold: Dimension tables (star schema)
│       ├── gold_facts.py            # Gold: Fact tables (star schema)
│       ├── gold_seasonal_stats.py   # Gold: Player seasonal stats
│       └── upload_database.py       # Supabase upload (all layers)
│
├── Data/                             # Generated data (medallion structure)
│   ├── bronze/                      # Raw JSON from API
│   │   ├── league_standings_raw.json
│   │   ├── players_raw.json
│   │   ├── gameweeks/*.json         # Last 2 GWs updated
│   │   └── manager_picks/*.json
│   ├── silver/                      # Cleaned CSV/Parquet
│   │   ├── league_standings.csv
│   │   ├── players_data.csv         # ALL 70+ columns
│   │   └── gameweeks_parquet/*.parquet
│   └── gold/                        # Star schema (analytics-ready)
│       ├── dimensions/              # 5 dimension tables
│       │   ├── dim_clubs.parquet
│       │   ├── dim_players.parquet  # 70+ columns
│       │   ├── dim_managers.parquet
│       │   ├── dim_gameweeks.parquet
│       │   └── dim_fixtures.parquet # With difficulty ratings
│       └── facts/                   # 4 fact tables
│           ├── fact_player_performance.parquet      # Gameweek stats
│           ├── fact_player_seasonal_stats.parquet   # Season totals
│           ├── fact_manager_picks.parquet
│           └── manager_gameweek_performance.parquet # Denormalized
│
├── docs/                             # Documentation
│   ├── MEDALLION_ARCHITECTURE.md    # Architecture guide
│   ├── DIMENSIONAL_MODEL.md         # Star schema details
│   ├── UPDATED_DIMENSIONAL_MODEL.md # Latest model updates
│   ├── QUICK_REFERENCE.md           # Quick start guide
│   ├── fpl_etl_visualization.html   # Interactive visualization
│   └── er_diagram.md                # Entity-relationship diagram
│
├── .github/workflows/
│   └── etl.yml                      # Automated pipeline
├── requirements.txt                 # Dependencies
└── README.md                        # This file
```

## 🎯 Key Features

### Medallion Architecture (3 Layers)
- 🥉 **Bronze**: Raw API data (JSON) - Full load first, then incremental (last 2 GWs)
- 🥈 **Silver**: Cleaned & validated data (CSV/Parquet) - All 70+ player columns
- 🥇 **Gold**: Star schema dimensional model - 5 dimensions + 4 facts

### Incremental vs Full Load Modes
- **Full Load**: Extracts ALL gameweeks (GW1 to current) - ~3-4 minutes
- **Incremental**: Extracts last 2 gameweeks only - ~25-30 seconds (95% faster!)
- **Configuration**: Toggle via `INCREMENTAL_MODE` in `src/config.py`
- See [INCREMENTAL_MODE_GUIDE.md](docs/INCREMENTAL_MODE_GUIDE.md)

### Dimensional Model (Star Schema)
- **5 Dimensions**: clubs, players (70+ cols), managers, gameweeks, fixtures
- **4 Fact Tables**: player performance, seasonal stats, manager picks, denormalized view
- **Proper Relationships**: Foreign keys linking clubs → players → performance

### Complete Player Data
- ✅ **70+ columns** from FPL API (all preserved)
- ✅ **Seasonal stats**: total_points, goals, form, xG, now_cost
- ✅ **Gameweek stats**: per-GW performance
- ✅ **Fixture difficulty**: ratings for transfer planning

### Performance Optimizations
- ⚡ **Incremental mode**: 95% faster (30 sec vs 4 min)
- 📦 **Efficient storage**: Parquet files for analytics
- 🔄 **Reprocessable**: Transform without re-calling APIs
- 🤖 **Automated**: GitHub Actions scheduled runs

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.8+**
- **Supabase Account** ([free tier](https://supabase.com))
- **FPL Draft League ID**

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd FPL-ETL

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables (Windows PowerShell)
$env:FPL_LEAGUE_ID = '24636'
$env:SUPABASE_URL = 'https://your-project.supabase.co'
$env:SUPABASE_SERVICE_KEY = 'your-service-key'

# 4. Run medallion pipeline
python -m src.main_medallion
```

### What Gets Created

```
Data/
├── bronze/     # Raw JSON (last 2 gameweeks updated)
├── silver/     # Cleaned CSV/Parquet
└── gold/       # Star schema
    ├── dimensions/ (5 tables)
    └── facts/      (4 tables)

Supabase: data/
├── bronze/
├── silver/
└── gold/
    ├── dimensions/
    └── facts/
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `FPL_LEAGUE_ID` | No | Your FPL draft league ID | `24636` |
| `SUPABASE_URL` | Yes | Supabase project URL | None |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service account key | None |

### Finding Your League ID

1. Go to [https://draft.premierleague.com](https://draft.premierleague.com)
2. Login and navigate to your league
3. The URL will show: `https://draft.premierleague.com/leagues/YOUR_LEAGUE_ID`
4. Use the number after `/leagues/` as your `FPL_LEAGUE_ID`

### Setting Up Supabase

1. **Create a free account** at [supabase.com](https://supabase.com)
2. **Create a new project** (select any region)
3. **Get your credentials:**
   - Project URL: Settings → API
   - Service Key: Settings → API → Service Role Key (use this, not the anon key)
4. **Create a storage bucket:**
   - Go to Storage in the left sidebar
   - Click "New bucket" → Name it `data`
   - Set it to **Public** (or configure CORS as needed)

---

## 🚀 Usage

### Run Complete Pipeline

```bash
python -m src.main_medallion
```

**Pipeline Flow**:
1. 🥉 **Bronze**: Extract raw data (incremental - last 2 GWs)
2. 🥈 **Silver**: Clean and validate
3. 🥇 **Gold**: Create dimensional model (5 dims + 4 facts)
4. ⬆️ **Upload**: Send to Supabase (bronze/, silver/, gold/)

### Run Individual Layers

```bash
# Bronze only (extract raw data)
python -m src.etl.bronze

# Silver only (transform data)
python -m src.etl.silver

# Gold only (create star schema)
python -m src.etl.gold

# Upload only
python -m src.etl.upload_database
```

### Query Data (Python/Pandas)

**Seasonal Stats (All 70+ Columns)**:
```python
import pandas as pd

# Load player seasonal stats
seasonal = pd.read_parquet('Data/gold/facts/fact_player_seasonal_stats.parquet')

# Access all columns
print(seasonal[['name', 'total_points', 'form', 'now_cost', 'xG', 'PpG']])
```

**Manager's Team for Gameweek**:
```python
# Load denormalized table (all joins pre-computed)
df = pd.read_parquet('Data/gold/facts/manager_gameweek_performance.parquet')

# Filter for specific manager and gameweek
team = df[(df['manager_id'] == 123) & (df['gameweek_num'] == 10)]
print(team[['player_name', 'club_name', 'gw_points', 'gw_goals']])
```

**Fixtures with Difficulty Ratings**:
```python
fixtures = pd.read_parquet('Data/gold/dimensions/dim_fixtures.parquet')
clubs = pd.read_parquet('Data/gold/dimensions/dim_clubs.parquet')

# Join to get club names
fixtures_full = fixtures.merge(
    clubs.add_suffix('_home'),
    left_on='home_club_id',
    right_on='club_id_home'
).merge(
    clubs.add_suffix('_away'),
    left_on='away_club_id',
    right_on='club_id_away'
)

# Show upcoming easy fixtures
easy = fixtures_full[
    (fixtures_full['is_finished'] == False) &
    (fixtures_full['home_difficulty'] <= 2)
]
print(easy[['club_name_home', 'club_name_away', 'home_difficulty']])
```

---

## 📊 Data Model

### Dimensional Model (Star Schema)

**5 Dimension Tables**:

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `dim_clubs` | Premier League teams | club_id, club_name, short_name |
| `dim_players` | Players (70+ columns) | player_id, name, club_id, position, total_points, form, xG, now_cost |
| `dim_managers` | FPL managers | manager_id, first_name, last_name, team_name |
| `dim_gameweeks` | Gameweek calendar | gameweek_id, gameweek_num, is_finished, is_current |
| `dim_fixtures` | Matches with difficulty | fixture_id, home_club_id, away_club_id, home_difficulty, away_difficulty |

**4 Fact Tables**:

| Table | Grain | Description |
|-------|-------|-------------|
| `fact_player_performance` | Player × Gameweek | Gameweek-specific stats (gw_points, gw_goals, etc.) |
| `fact_player_seasonal_stats` | Player | Season totals (all 70+ columns) |
| `fact_manager_picks` | Manager × Player × Gameweek | Manager selections |
| `manager_gameweek_performance` | Manager × Player × Gameweek | Denormalized (all joins pre-computed) |

### Relationships

```
dim_clubs (1) ──→ (N) dim_players [club_id]
            │
            ├──→ (N) dim_fixtures [home_club_id]
            │
            └──→ (N) dim_fixtures [away_club_id]

dim_players (1) ──→ (N) fact_player_performance [player_id]
              │
              ├──→ (N) fact_manager_picks [player_id]
              │
              └──→ (1) fact_player_seasonal_stats [player_id]

dim_gameweeks (1) ──→ (N) fact_player_performance [gameweek_id]
                │
                ├──→ (N) fact_manager_picks [gameweek_id]
                │
                └──→ (N) dim_fixtures [gameweek_id]
```

### Complete Player Data (70+ Columns)

Now includes ALL columns from FPL API:
- **Seasonal totals**: total_points, goals, assists, minutes
- **Expected stats**: xG, xA, xGi, xGc
- **Form & value**: form, PpG, now_cost, selected_by_percent
- **Influence**: influence, creativity, threat, ict_index
- **Availability**: status, chance_of_playing, news
- **Plus 50+ more columns**!

---

## 🏗️ Architecture

### Medallion Flow

```
FPL API
   ↓
🥉 Bronze Layer (Raw JSON)
   │ - Incremental: Last 2 gameweeks only
   │ - league_standings_raw.json
   │ - players_raw.json (70+ columns preserved)
   │ - gameweeks/gw_*.json
   │ - manager_picks/*.json
   ↓
🥈 Silver Layer (Cleaned)
   │ - Validated & typed data
   │ - league_standings.csv
   │ - players_data.csv (ALL columns)
   │ - gameweeks_parquet/*.parquet
   ↓
🥇 Gold Layer (Star Schema)
   │ - Dimensions (5 tables)
   │   • dim_clubs, dim_players, dim_managers,
   │     dim_gameweeks, dim_fixtures
   │ - Facts (4 tables)
   │   • fact_player_performance (gameweek)
   │   • fact_player_seasonal_stats (season)
   │   • fact_manager_picks
   │   • manager_gameweek_performance (denormalized)
   ↓
☁️ Supabase Storage
   └─ bronze/, silver/, gold/ folders
```

### Key Design Decisions

✅ **Incremental Bronze Updates**: Only last 2 gameweeks re-fetched (95% faster)  
✅ **Complete Player Data**: All 70+ columns preserved from API  
✅ **Separated Stats**: Seasonal vs gameweek stats in different tables  
✅ **Star Schema**: Proper dimensional model for analytics  
✅ **Denormalized View**: Pre-joined table for fast queries  
✅ **Fixture Difficulty**: Ratings connected to clubs for transfer planning

---

## ⚙️ API Integration

### API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /api/league/{id}/details` | League standings & manager info |
| `GET /api/bootstrap-static` | All player data & metadata |
| `GET /api/event/{gw}/live` | Gameweek-specific player stats |
| `GET /api/entry/{manager_id}/event/{gw}` | Manager picks for gameweek |
| `GET /api/game` | Current gameweek status |

### Rate Limiting

The pipeline respects API rate limits with:
- 3 retry attempts per request
- 2-second delay between retries
- 10-second timeout per request
- Session reuse to minimize connections

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing environment variables | Set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` |
| "Bronze file not found" | Run Bronze layer first: `python -m src.etl.bronze` |
| Supabase upload fails | Verify bucket name is `data` and credentials are correct |
| API timeout | FPL API may be down, retry in a few minutes |
| "No gameweek data" | Check if Bronze layer has data: `ls Data/bronze/gameweeks/` |

**Debug Mode**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| `README.md` | This file - overview and quick start |
| `docs/MEDALLION_ARCHITECTURE.md` | Detailed medallion architecture guide |
| `docs/DIMENSIONAL_MODEL.md` | Star schema model documentation |
| `docs/UPDATED_DIMENSIONAL_MODEL.md` | Latest model enhancements |
| `docs/QUICK_REFERENCE.md` | Quick reference guide |
| `docs/fpl_etl_visualization.html` | Interactive visual documentation (open in browser) |
| `docs/er_diagram.md` | Entity-relationship diagram (Mermaid) |

**Start here**: Open `docs/fpl_etl_visualization.html` in your browser for an interactive guide!

---

## 🔐 Security

### Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data
3. **Use Service Key** (not anon key) for Supabase uploads
4. **Restrict API access** in Supabase to only what's needed
5. **Keep dependencies updated** with `pip install --upgrade -r requirements.txt`

### Environment Variable Management

**Using `.env` file (not committed):**
```bash
# Create .env
FPL_LEAGUE_ID=24636
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-secret-key

# Load in Python
from dotenv import load_dotenv
load_dotenv()
```

---

## 📦 Dependencies & Dependency Management

The project uses two requirements files for flexibility:

| File | Purpose | When to Use |
|------|---------|------------|
| `requirements.txt` | Direct dependencies with version ranges | Local development |
| `requirements.lock` | Locked dependency tree (all transitive deps) | CI/CD, production |

### Installing Dependencies

**For local development (flexible):**
```bash
pip install -r requirements.txt
```

**For CI/CD (faster, uses locked versions):**
```bash
pip install -r requirements.lock
```

### Managing Dependencies

To add a new package:
```bash
echo "new-package>=1.0" >> requirements.txt
pip-compile requirements.txt -o requirements.lock
pip install -r requirements.lock
```

**Details:** See [docs/DEPENDENCY_MANAGEMENT.md](docs/DEPENDENCY_MANAGEMENT.md)

### Direct Dependencies

| Package | Purpose |
|---------|---------|
| `pandas>=1.5.0` | Data manipulation & CSV/Parquet handling |
| `requests>=2.28.0` | HTTP API calls |
| `supabase>=1.0.0` | Supabase client & storage |
| `pyarrow>=12.0.0` | Parquet file format support |
| `python-dotenv>=1.0.0` | Environment variable loading |

---

## 🤝 Contributing

### Reporting Issues

Found a bug? Please include:
- What you were trying to do
- Exact error message (if any)
- Environment (OS, Python version)
- Steps to reproduce

### Code Quality

The project maintains:
- **Pylint Score**: 10/10 (perfect)
- **Type Hints**: Used throughout
- **Error Handling**: Try-except blocks with logging
- **Documentation**: Docstrings on all functions

---

## 📚 Further Documentation

- [FPL API Docs](https://draft.premierleague.com/api) - Official API reference
- [Supabase Docs](https://supabase.com/docs) - Supabase setup & usage
- [Pandas Docs](https://pandas.pydata.org/) - Data manipulation reference

---

## 📄 License

[Add your license here]

---

## 👨‍💻 Author

[Add your information here]

---

## 📈 Features by Version

### v2.0.0 (Current - February 2026)
- ✨ **Medallion architecture**: Bronze, Silver, Gold layers
- ✨ **Star schema**: 5 dimensions + 4 fact tables
- ✨ **Complete player data**: All 70+ columns from API
- ✨ **Fixture difficulty**: dim_fixtures with ratings
- ✨ **Incremental updates**: Bronze layer updates last 2 GWs only
- ✨ **Separated stats**: Seasonal vs gameweek fact tables
- ✨ **Denormalized view**: Pre-joined manager performance table

### v1.0.0 (January 2026)
- Initial release with basic ETL pipeline
- Flat data structure

---

## 📝 License

[Add your license]

---

## 👤 Author

[Add your info]

---

**Last Updated**: February 7, 2026