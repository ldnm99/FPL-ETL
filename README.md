# FPL-ETL: Fantasy Premier League Draft Data Pipeline

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Code Quality](https://img.shields.io/badge/Pylint-10%2F10-success)

A robust ETL (Extract, Transform, Load) pipeline for collecting and processing Fantasy Premier League (FPL) draft league data. This project extracts real-time player statistics, league standings, and manager picks from the official FPL API and uploads them to Supabase for storage and analysis.

## 📁 Project Structure

```
FPL-ETL/
├── src/                           # Source code
│   ├── __init__.py               # Package initialization
│   ├── main.py                   # Pipeline entry point
│   ├── utils.py                  # Shared utilities & API helpers
│   └── etl/                      # ETL modules
│       ├── __init__.py
│       ├── league.py             # League standings extraction
│       ├── players.py            # Player data extraction
│       ├── merge_players_data.py # Gameweek data merging
│       └── upload_database.py    # Supabase storage upload
├── data/                          # Generated data (auto-created)
│   ├── league_standings.csv      # Manager & team info
│   ├── players_data.csv          # Player seasonal stats
│   ├── gw_data.parquet           # Merged gameweek data
│   └── gameweeks_parquet/        # Individual gameweek files
├── docs/                          # Documentation
│   └── DEPENDENCY_MANAGEMENT.md  # Dependency management guide
├── .github/workflows/             # GitHub Actions
│   └── etl.yml                   # Pipeline automation
├── .env                          # Environment variables (not committed)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Direct dependencies
├── requirements.lock             # Locked dependency tree
└── README.md                     # This file
```

## 🎯 Features

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Code Quality](https://img.shields.io/badge/Pylint-10%2F10-success)

A robust ETL (Extract, Transform, Load) pipeline for collecting and processing Fantasy Premier League (FPL) draft league data. This project extracts real-time player statistics, league standings, and manager picks from the official FPL API and uploads them to Supabase for storage and analysis.

## 🎯 Overview

The FPL-ETL pipeline automates the collection of FPL draft league data including:

- **League Standings**: Manager names, team information, and waiver pick order
- **Player Statistics**: Real-time performance metrics (goals, assists, clean sheets, bonus points, etc.)
- **Gameweek Data**: Player performance for each gameweek with manager team selections
- **Historical Data**: Season-wide accumulation of stats with gameweek-level detail

Perfect for fantasy football analysis, league management dashboards, and data-driven decision making.

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)
- **Supabase Account** (free tier available at [supabase.com](https://supabase.com))
- Internet connection for API access

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd FPL-ETL
   ```

2. **Install dependencies:**
   ```bash
   # For CI/CD (faster - uses locked versions)
   pip install -r requirements.lock
   
   # For local development (flexible - uses version ranges)
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   # Linux/Mac
   export FPL_LEAGUE_ID='24636'
   export SUPABASE_URL='https://your-project.supabase.co'
   export SUPABASE_SERVICE_KEY='your-service-key-here'
   
   # Windows PowerShell
   $env:FPL_LEAGUE_ID = '24636'
   $env:SUPABASE_URL = 'https://your-project.supabase.co'
   $env:SUPABASE_SERVICE_KEY = 'your-service-key-here'
   ```

4. **Run the pipeline:**
   ```bash
   # Using Python module path (recommended)
   python -m src.main
   
   # Or from the src directory
   cd src && python main.py
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

### Running the Full Pipeline

```bash
# From project root
python -m src.main

# Or from src directory
cd src && python main.py
```

This will:
1. ✅ Fetch league standings (managers & teams)
2. ✅ Fetch all player data from the FPL database
3. ✅ Extract gameweek data for all active gameweeks
4. ✅ Merge player stats with manager picks
5. ✅ Upload all data to Supabase
6. ✅ Update `last_updated.txt` timestamp

### Running Individual Components

**Extract League Data Only:**
```python
from src.etl.league import get_league_standings
get_league_standings('24636', output_file='Data/league_standings.csv')
```

**Extract Player Data Only:**
```python
from src.etl.players import get_player_data
get_player_data(output_file='Data/players_data.csv')
```

**Process Gameweek Data Only:**
```python
from src.etl import merge_players_data
merge_players_data.main()
```

**Upload to Supabase Only:**
```python
from src.etl import upload_database
upload_database.main()
```

---

## 📊 Output Files

### Data Files Generated

**1. `league_standings.csv`**
- Manager IDs, names, and team information
- Waiver pick order
- Columns: `manager_id, id, first_name, last_name, short_name, waiver_pick, team_name`

**2. `players_data.csv`**
- Seasonal player statistics
- Player identifiers and team assignments
- Columns: `ID, name, team, position, assists, bonus, total_points, xA, CS, Gc, Goals Scored, minutes, red_cards, starts, xG, xGi, xGc, code, PpG`

**3. `gw_data.parquet`**
- Merged gameweek-level data with player stats and manager picks
- One row per player per gameweek per manager
- Comprehensive column names like `gw_points, gw_goals, gw_assists, season_points, manager_team_name, etc.`

**4. `gameweeks_parquet/gw_data_gwN.parquet`**
- Individual gameweek files for detailed analysis
- Helpful for incremental processing and storage efficiency

### Data Stored in Supabase

All generated files are uploaded to your Supabase `data` storage bucket and can be:
- Downloaded via Supabase dashboard
- Accessed via Supabase API
- Used in downstream applications

---

## 🔄 Pipeline Logic

### Data Extraction Flow

```
API (draft.premierleague.com)
        ↓
    ┌───────────────────────────────┐
    │  League Data                  │
    │  - Manager info               │
    │  - Team standings             │
    └────────→ league_standings.csv │
        ↓
    ┌───────────────────────────────┐
    │  Player Data                  │
    │  - Seasonal stats             │
    │  - Demographics               │
    └────────→ players_data.csv     │
        ↓
    ┌───────────────────────────────┐
    │  Gameweek Data (Loop GW1→GWN) │
    │  - Player stats per GW        │
    │  - Manager picks per GW       │
    └────────→ gw_data_gwN.parquet  │
        ↓
    ┌───────────────────────────────┐
    │  Merge All Gameweeks          │
    │  - Combine GW data            │
    │  - Rename columns             │
    │  - Add season stats           │
    └────────→ gw_data.parquet      │
        ↓
    ┌───────────────────────────────┐
    │  Upload to Supabase           │
    │  - CSV files                  │
    │  - Parquet files              │
    │  - Update timestamp           │
    └────────→ Supabase Storage     │
```

### Key Features

- **Retry Logic**: API calls have automatic retry with exponential backoff
- **Error Handling**: Comprehensive logging and error recovery
- **Incremental Processing**: Gameweeks are processed and saved individually
- **Data Validation**: CSV and file existence checks before processing
- **Type Safety**: Consistent type handling throughout pipeline

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

### Common Issues

#### 1. **Missing Environment Variables**
```
❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables
```
**Solution:**
```bash
# Check if variables are set
echo $SUPABASE_URL

# Set them
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_SERVICE_KEY='your-key'
```

#### 2. **League ID Not Found**
```
❌ Error: No league data found for league ID 24636
```
**Solution:**
- Verify your league ID is correct
- Check that the league is a public or accessible league
- Try accessing it directly: `https://draft.premierleague.com/api/league/{ID}/details`

#### 3. **CSV File Not Found**
```
❌ Error: Players CSV file not found: Data/players_data.csv
```
**Solution:**
- Ensure `get_player_data()` ran first
- Check that `Data/` folder exists and is writable
- Run the full pipeline: `python main.py`

#### 4. **Supabase Upload Fails**
```
❌ Error uploading CSV: ...
```
**Solution:**
- Verify Supabase credentials are correct
- Check that the `data` bucket exists in Supabase Storage
- Ensure bucket permissions allow uploads
- Test credentials with Supabase dashboard

#### 5. **Network/API Timeout**
```
❌ Failed to fetch data from https://... after 3 attempts
```
**Solution:**
- Check internet connection
- Try again (API may be temporarily unavailable)
- Increase retry attempts in `utils.py` if needed

---

## 📝 Logging

The pipeline uses Python's logging module for detailed diagnostics.

**Log Format:**
```
LEVEL: Message
INFO: 🚀 Starting FPL Draft data extraction pipeline...
INFO: 📊 Fetching league standings...
✅ Saved CSV: Data/league_standings.csv
```

**Viewing Logs:**
- Console output shows real-time progress
- All messages are prefixed with emojis for quick visual scanning
- Errors are marked with ❌
- Successes are marked with ✅

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

## 🚀 Changelog

### Version 1.1.0 (Current)
- ✨ Fixed duplicate variable definitions
- ✨ Enhanced error messages with helpful guidance
- ✨ Consistent logging throughout (replaced print with logging)
- ✨ Added file existence validation before processing
- ✨ Environment variable support for League ID
- ✨ Improved Parquet file location detection

### Version 1.0.0
- Initial release with core ETL pipeline

---

**Last Updated:** January 23, 2026

For the latest updates and features, check the [GitHub repository](link-to-repo).

---