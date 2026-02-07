# Incremental Mode Configuration Guide

## Overview

The FPL ETL pipeline supports two modes:
1. **Full Load Mode**: Extract all historical gameweeks (initial setup)
2. **Incremental Mode**: Extract only recent gameweeks (ongoing updates)

---

## Current Configuration

**File**: `src/config.py`

```python
# Pipeline mode
INCREMENTAL_MODE: bool = False  # Current: FULL LOAD
INCREMENTAL_GAMEWEEKS: int = 2  # Number of recent GWs when incremental
```

---

## How It Works

### Full Load Mode (`INCREMENTAL_MODE = False`)

**What it does:**
- Extracts ALL gameweeks from GW1 to current gameweek
- Example: If current GW is 25, extracts GW1, GW2, ..., GW25
- Use for: Initial setup, backfilling historical data

**Bronze Layer Function:**
```python
extract_all_gameweeks()  # Called when INCREMENTAL_MODE = False
```

**API Calls:**
- 1 call for league data
- 1 call for player data
- N calls for gameweek data (where N = current GW)
- N × M calls for manager picks (where M = number of managers)
- **Total**: ~177 API calls for 25 GWs with 7 managers

**Time**: ~3-4 minutes

---

### Incremental Mode (`INCREMENTAL_MODE = True`)

**What it does:**
- Extracts only the last N gameweeks (default: 2)
- Example: If current GW is 25, extracts GW24 and GW25
- Use for: Weekly updates, scheduled runs

**Bronze Layer Function:**
```python
extract_recent_gameweeks(num_gameweeks=2)  # Called when INCREMENTAL_MODE = True
```

**API Calls:**
- 1 call for league data
- 1 call for player data
- 2 calls for gameweek data (last 2 GWs)
- 2 × M calls for manager picks
- **Total**: ~16 API calls for 2 GWs with 7 managers

**Time**: ~25-30 seconds (95% faster!)

---

## When to Use Each Mode

### Use Full Load Mode When:
- ✅ First time running the pipeline
- ✅ Backfilling missing historical data
- ✅ Major schema changes require reprocessing all data
- ✅ Data corruption detected in Bronze layer

### Use Incremental Mode When:
- ✅ Running scheduled updates (GitHub Actions)
- ✅ Refreshing current gameweek data
- ✅ Normal weekly operations
- ✅ Updating recent gameweeks only

---

## Switching to Incremental Mode

### Step 1: Verify Full Load Complete

Check that historical data exists:
```bash
# Windows
dir Data\bronze\gameweeks\
dir Data\silver\gameweeks_parquet\
dir Data\gold\dimensions\

# Linux/Mac
ls Data/bronze/gameweeks/
ls Data/silver/gameweeks_parquet/
ls Data/gold/dimensions/
```

You should see files for all gameweeks (GW1 through current).

### Step 2: Update Configuration

Edit `src/config.py`:

```python
# BEFORE (Full Load)
INCREMENTAL_MODE: bool = False

# AFTER (Incremental)
INCREMENTAL_MODE: bool = True
```

### Step 3: Test Incremental Run

```bash
python -m src.main_medallion
```

**Expected Output:**
```
🥉 BRONZE LAYER: Extracting raw data from FPL API
⚡ Running in INCREMENTAL mode (last 2 GWs)
📅 Current gameweek: 25
📈 Updating gameweeks 24 to 25
  Updating GW24...
  Updating GW25...
✅ Last 2 gameweeks updated!
```

### Step 4: Verify

Check that only recent GWs were updated:
- Bronze files should have new timestamps for GW24-25 only
- Silver should have new timestamps for GW24-25 only
- Gold should be completely regenerated (all files updated)

---

## Customizing Incremental Window

To change how many recent gameweeks are updated:

```python
# src/config.py

# Update only last gameweek
INCREMENTAL_GAMEWEEKS: int = 1

# Update last 3 gameweeks
INCREMENTAL_GAMEWEEKS: int = 3

# Update last week (recommended for weekly runs)
INCREMENTAL_GAMEWEEKS: int = 2  # Default
```

---

## GitHub Actions Integration

### Automatic Mode Switching

**Recommended Setup:**

1. **Manual Trigger** → Full Load
   - When you manually trigger the workflow, use full load
   - Good for backfilling or fixing issues

2. **Scheduled Runs** → Incremental
   - Automated Saturday runs use incremental mode
   - Faster and more efficient

### Configuration

No changes needed! Just set `INCREMENTAL_MODE = True` in `config.py` and commit:

```bash
git add src/config.py
git commit -m "Switch to incremental mode for scheduled runs"
git push origin main
```

Next scheduled run will use incremental mode automatically.

---

## Troubleshooting

### Issue: "Missing gameweek data"

**Cause**: Incremental mode running before full load complete
**Solution**: Switch to full load mode, run pipeline, then switch back

```python
# Temporarily use full load
INCREMENTAL_MODE = False
```

Run pipeline, then switch back:
```python
INCREMENTAL_MODE = True
```

### Issue: "Stale data in Gold layer"

**Cause**: Gold layer caches data from all GWs
**Solution**: This is normal! Gold layer always regenerates completely, even in incremental mode.

The Bronze layer updates only recent GWs (efficient), but Gold layer reads ALL Silver data and regenerates the star schema (ensures consistency).

### Issue: "Too slow even in incremental mode"

**Cause**: Too many gameweeks in incremental window
**Solution**: Reduce the window

```python
INCREMENTAL_GAMEWEEKS = 1  # Update only current GW
```

---

## Best Practices

### 1. Start with Full Load
Always run full load mode first to establish baseline data.

### 2. Use Incremental for Scheduled Runs
Set `INCREMENTAL_MODE = True` for automated GitHub Actions runs.

### 3. Monitor API Usage
- Full load: ~200 API calls
- Incremental (2 GWs): ~20 API calls
- Stay under API rate limits

### 4. Verify After Mode Switch
After switching modes, run pipeline locally once to verify before pushing to GitHub.

### 5. Log Timestamps
Check Bronze file timestamps to confirm incremental updates are working:

```bash
# Windows
dir /O:D Data\bronze\gameweeks\

# Linux/Mac
ls -lt Data/bronze/gameweeks/
```

Only recent GWs should have new timestamps.

---

## Performance Comparison

| Mode | GWs Extracted | API Calls | Time | Use Case |
|------|--------------|-----------|------|----------|
| **Full Load** | All (25) | ~200 | 3-4 min | Initial setup |
| **Incremental (2)** | Last 2 | ~20 | 25-30 sec | Weekly updates |
| **Incremental (1)** | Last 1 | ~12 | 15-20 sec | Daily updates |

---

## Summary

✅ **Full Load Mode**: Use once for initial setup  
✅ **Incremental Mode**: Use for all subsequent runs  
✅ **Current Status**: Full load complete (25 GWs) ✅  
✅ **Next Step**: Switch to incremental mode and test

**Ready to switch!** Update `INCREMENTAL_MODE = True` in `src/config.py`.
