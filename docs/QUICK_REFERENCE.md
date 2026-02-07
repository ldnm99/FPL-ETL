# Medallion Schema Quick Reference

## 🚀 Quick Start

```bash
# 1. Set environment variables
$env:FPL_LEAGUE_ID = '24636'
$env:SUPABASE_URL = 'https://your-project.supabase.co'
$env:SUPABASE_SERVICE_KEY = 'your-service-key'

# 2. Run medallion pipeline
python -m src.main_medallion
```

---

## 📁 Folder Structure

```
Data/
├── bronze/     # 🥉 Raw JSON from API
├── silver/     # 🥈 Cleaned CSV/Parquet
└── gold/       # 🥇 Analytics Parquet
```

**Supabase**: Same structure in `data` bucket

---

## 🎯 Use Cases

| Task | Use This Layer | File |
|------|---------------|------|
| Dashboard | Gold | `gold/gw_data_full.parquet` |
| Player rankings | Gold | `gold/player_season_stats.parquet` |
| Manager standings | Gold | `gold/manager_performance.parquet` |
| Debug API issue | Bronze | `bronze/players_raw.json` |
| Reprocess data | Silver | `silver/*.parquet` |

---

## 🔄 Run Individual Layers

```bash
python -m src.etl.bronze   # Extract raw data
python -m src.etl.silver   # Transform to cleaned
python -m src.etl.gold     # Create analytics
python -m src.etl.upload_database  # Upload all
```

---

## 📊 Gold Layer Datasets

### `gw_data_full.parquet`
Complete dataset with all gameweeks + enrichments

### `player_season_stats.parquet`
Aggregated: points, goals, assists, games played

### `manager_performance.parquet`
Weekly points, cumulative, rolling avg, rank

---

## ⚙️ Configuration

All paths in `src/config.py`:

```python
from src.config import config

config.BRONZE_DIR           # Data/bronze
config.SILVER_DIR           # Data/silver
config.GOLD_DIR             # Data/gold
config.get_supabase_path('bronze', 'file.json')
```

---

## 🆚 Old vs New

| Aspect | Old | New (Medallion) |
|--------|-----|-----------------|
| **Run** | `python -m src.main` | `python -m src.main_medallion` |
| **Structure** | Flat | 3 layers |
| **Reprocess** | Re-call API | Use Bronze cache |
| **Debug** | Limited | Raw API data |
| **Analytics** | Manual | Gold layer |

---

## 📚 Documentation

- `docs/MEDALLION_MIGRATION.md` - How to migrate
- `docs/MEDALLION_ARCHITECTURE.md` - Full architecture
- `.copilot/.../IMPLEMENTATION_SUMMARY.md` - This implementation
- `.copilot/.../supabase_setup.md` - Supabase details

---

## ✅ Checklist

- [ ] Environment variables set
- [ ] Run: `python -m src.main_medallion`
- [ ] Verify: Supabase has bronze/silver/gold folders
- [ ] Test: Load `gold/gw_data_full.parquet` in dashboard

---

**Need help?** Check `docs/MEDALLION_MIGRATION.md`
