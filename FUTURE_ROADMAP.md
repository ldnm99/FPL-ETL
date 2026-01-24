# FPL-ETL: Future Improvement Roadmap

**Last Updated:** January 24, 2026  
**Current Status:** Production-Ready (7.1/10)  
**Overall Assessment:** Solid foundation with opportunities for scaling and robustness

---

## 📊 Current Health Score

| Category | Score | Status |
|----------|-------|--------|
| Architecture | 8/10 | ✅ Solid foundation |
| Code Quality | 7/10 | ⚠️ Syntax good, error handling incomplete |
| Performance | 7/10 | ⚠️ Good for current scale, serial bottleneck exists |
| Testing | 0/10 | ❌ **CRITICAL GAP** |
| Documentation | 9/10 | ✅ Excellent |
| Security | 8/10 | ✅ Good practices, validation needed |
| DevOps/CI-CD | 7/10 | ⚠️ Functional, missing error handling |
| **OVERALL** | **7.1/10** | ✅ Production-ready but needs refinement |

---

## 🚨 CRITICAL ISSUES TO FIX

### 1. **Import Inconsistency** (30 min fix)
**Status:** HIGH PRIORITY  
**Current Problem:**
```python
# src/main.py (WRONG - relative imports)
from etl import merge_players_data
from etl.league import get_league_standings

# src/etl/league.py (CORRECT - absolute imports)
from src.utils import fetch_data, save_csv
```

**Why:** Causes fragility when running as module vs script  
**Fix:**
```python
# Change all main.py imports to absolute
from src.etl import merge_players_data
from src.etl.league import get_league_standings
from src.etl.players import get_player_data
from src.etl import upload_database
```

---

### 2. **Missing Test Coverage** (8-12 hours to implement)
**Status:** CRITICAL - 0% coverage  
**Current Problem:** No unit tests, integration tests, or fixtures

**Implementation Plan:**
```
tests/
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── test_utils.py             # Test retry logic, CSV ops
│   ├── test_league.py            # Test league data extraction
│   ├── test_players.py           # Test player data parsing
│   └── test_merge.py             # Test gameweek merging
├── integration/
│   └── test_pipeline_e2e.py      # Full pipeline mock test
└── fixtures/
    ├── mock_api_responses.json
    └── sample_gameweek_data.py
```

**Setup:**
```bash
pip install pytest pytest-cov pytest-mock
echo "pytest" >> requirements.txt
pip-compile requirements.txt -o requirements.lock
```

**Example Tests:**
```python
# tests/unit/test_utils.py
import pytest
from unittest.mock import Mock, patch
from src.utils import fetch_data

def test_fetch_data_success():
    """Test successful API call"""
    with patch('requests.Session.get') as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        result = fetch_data("https://api.example.com")
        assert result == {"status": "ok"}

def test_fetch_data_retry_logic():
    """Test retry mechanism on transient failures"""
    with patch('requests.Session.get') as mock_get:
        # First 2 calls fail, 3rd succeeds
        mock_get.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            Mock(json=lambda: {"data": "success"})
        ]
        
        result = fetch_data("https://api.example.com", retries=3)
        assert result == {"data": "success"}
        assert mock_get.call_count == 3
```

**Run Tests:**
```bash
pytest -v --cov=src --cov-report=html
```

---

### 3. **Hardcoded Paths** (1 hour fix)
**Status:** HIGH PRIORITY  
**Current Problem:** Paths scattered throughout code

```python
# utils.py line 11
DB_FILE = "fpl_data.db"

# merge_players_data.py line 12-14
GW_FOLDER = "Data/gameweeks_parquet"
MERGED_OUTPUT = "Data/gw_data.parquet"

# Multiple hardcoded "Data/" references
```

**Fix - Create config file:**
```python
# src/config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    """Pipeline configuration"""
    # Paths
    DATA_DIR: str = os.getenv("FPL_DATA_DIR", "Data")
    GW_FOLDER: str = None
    MERGED_OUTPUT: str = None
    DB_FILE: str = None
    
    # API
    LEAGUE_ID: str = os.getenv("FPL_LEAGUE_ID", "24636")
    BASE_URL: str = "https://draft.premierleague.com/api"
    RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 2
    REQUEST_TIMEOUT: int = 10
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY")
    SUPABASE_BUCKET: str = "data"
    
    def __post_init__(self):
        """Initialize computed paths"""
        self.GW_FOLDER = os.path.join(self.DATA_DIR, "gameweeks_parquet")
        self.MERGED_OUTPUT = os.path.join(self.DATA_DIR, "gw_data.parquet")
        self.DB_FILE = os.path.join(self.DATA_DIR, "fpl_data.db")
```

**Usage:**
```python
# In modules
from src.config import Config
config = Config()
os.makedirs(config.GW_FOLDER, exist_ok=True)
```

---

### 4. **No Input Validation** (2 hours fix)
**Status:** HIGH PRIORITY  
**Current Problem:** DataFrames merged without schema validation

```python
# merge_players_data.py line 54-56 (CURRENT - NO VALIDATION)
gw_stats = get_player_gw_data(gw)
if gw_stats.empty:
    return pd.DataFrame()

gw_stats.merge(picks_df, on=["ID", "gameweek"], how="left")  # Could have NaN columns!
```

**Fix - Add validation:**
```python
# src/validators.py
from typing import List
import pandas as pd

class SchemaValidator:
    """Validate dataframe schemas"""
    
    @staticmethod
    def validate_gameweek_stats(df: pd.DataFrame) -> pd.DataFrame:
        """Validate GW player stats have required columns"""
        required = {'id', 'gameweek', 'total_points', 'minutes_played'}
        missing = required - set(df.columns)
        
        if missing:
            raise ValueError(f"GW stats missing columns: {missing}")
        
        # Check for NaN in critical columns
        if df[required].isna().any().any():
            logging.warning(f"Found NaN values in GW{df['gameweek'].iloc[0]} stats")
        
        return df
    
    @staticmethod
    def validate_merge_result(df: pd.DataFrame, 
                             expected_cols: List[str]) -> pd.DataFrame:
        """Validate merge didn't lose critical columns"""
        missing = set(expected_cols) - set(df.columns)
        if missing:
            raise ValueError(f"Merge lost columns: {missing}")
        return df

# Usage
gw_stats = get_player_gw_data(gw)
gw_stats = SchemaValidator.validate_gameweek_stats(gw_stats)
merged = gw_stats.merge(picks_df, ...)
merged = SchemaValidator.validate_merge_result(merged, ['ID', 'total_points', 'manager_id'])
```

---

## 🎯 HIGH PRIORITY IMPROVEMENTS

### Phase 1: Robustness (Week 1)
These ensure reliability and prevent silent failures.

| Issue | Fix | Effort | Impact |
|-------|-----|--------|--------|
| Import consistency | Convert main.py to absolute imports | 30 min | HIGH |
| Config extraction | Move hardcoded values to config.py | 1 hr | HIGH |
| Schema validation | Add validator.py with dataframe checks | 2 hrs | HIGH |
| Remove dead code | Delete unused utils.py functions | 30 min | MEDIUM |
| **Total** | | **4 hrs** | |

**Specific Changes:**

```python
# Step 1: Create config.py
# src/config.py - (see above)

# Step 2: Fix imports in main.py
from src.etl import merge_players_data  # Change from: from etl import...

# Step 3: Create validators.py
# src/validators.py - (see above)

# Step 4: Update merge_players_data.py
from src.validators import SchemaValidator

def build_gameweek_data(gw: int, managers: list[int], players_df: pd.DataFrame):
    gw_stats = get_player_gw_data(gw)
    gw_stats = SchemaValidator.validate_gameweek_stats(gw_stats)  # ADD
    # ... rest of code

# Step 5: Remove from utils.py
# Delete: fetch_players_data(), create_database(), etc.
```

---

### Phase 2: Performance (Week 2)
These reduce API calls and improve speed.

| Issue | Fix | Effort | Impact |
|-------|-----|--------|--------|
| Serial API calls | Implement ThreadPoolExecutor | 3 hrs | HIGH |
| Full dataframe remerge | Implement append-only merge | 3 hrs | MEDIUM |
| Retry logic | Add exponential backoff | 1 hr | MEDIUM |
| **Total** | | **7 hrs** | |

**Parallel API Calls:**

```python
# src/etl/merge_players_data.py
from concurrent.futures import ThreadPoolExecutor
import logging

def fetch_all_manager_picks(managers: list[int], gw: int) -> list[pd.DataFrame]:
    """Fetch manager picks in parallel (currently serial!)"""
    picks_list = []
    
    # BEFORE (SLOW - serial):
    # picks_list = [fetch_manager_picks(mid, gw) for mid in managers]
    
    # AFTER (FAST - parallel):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_manager_picks, mid, gw): mid 
            for mid in managers
        }
        
        for future in as_completed(futures):
            try:
                picks_df = future.result(timeout=30)
                if not picks_df.empty:
                    picks_list.append(picks_df)
            except Exception as e:
                manager_id = futures[future]
                logging.error(f"Failed to fetch picks for manager {manager_id}: {e}")
    
    return picks_list

# Improvement
# - Current: 100 managers × 3 retries = 300 serial requests (~2 min)
# - After: Same 300 requests but 5 concurrent = ~24 seconds (80% faster!)
```

**Append-Only Merge:**

```python
# src/etl/merge_players_data.py
def merge_all_gameweeks():
    """Combine gameweek files - append only, don't reprocess all"""
    
    # BEFORE (SLOW - reloads all GWs):
    files = sorted([f for f in os.listdir(GW_FOLDER) if f.endswith(".parquet")])
    dfs = [pd.read_parquet(os.path.join(GW_FOLDER, f)) for f in files]
    merged_df = pd.concat(dfs, ignore_index=True)
    
    # AFTER (FAST - append only):
    merged_path = os.path.join(config.DATA_DIR, "gw_data.parquet")
    
    if os.path.exists(merged_path):
        # Load existing data
        existing_df = pd.read_parquet(merged_path)
        existing_gws = set(existing_df['gameweek'].unique())
        
        # Load only new gameweeks
        files = sorted([f for f in os.listdir(GW_FOLDER) if f.endswith(".parquet")])
        new_gws = [
            f for f in files 
            if int(f.split("gw")[-1].split(".")[0]) not in existing_gws
        ]
        
        if new_gws:
            new_data = [pd.read_parquet(os.path.join(GW_FOLDER, f)) for f in new_gws]
            merged_df = pd.concat([existing_df, *new_data], ignore_index=True)
        else:
            logging.info("No new gameweeks to merge")
            return
    else:
        # First run - load all
        files = sorted([f for f in os.listdir(GW_FOLDER) if f.endswith(".parquet")])
        dfs = [pd.read_parquet(os.path.join(GW_FOLDER, f)) for f in files]
        merged_df = pd.concat(dfs, ignore_index=True)
    
    merged_df = rename_columns(merged_df)
    merged_df.to_parquet(merged_path, index=False, engine="pyarrow")
```

---

### Phase 3: Testing & CI/CD (Week 3)
These enable confident deployments.

| Issue | Fix | Effort | Impact |
|-------|-----|--------|--------|
| Unit tests | Create pytest suite | 6 hrs | CRITICAL |
| Integration tests | Test full pipeline flow | 2 hrs | HIGH |
| Error notifications | Add Slack/email alerts | 2 hrs | MEDIUM |
| CI/CD hardening | Add validation, conditionals | 2 hrs | HIGH |
| **Total** | | **12 hrs** | |

**Enhanced CI/CD Workflow:**

```yaml
name: FPL ETL Pipeline

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 */6 * * *'          # Every 6 hours
  workflow_dispatch:
  repository_dispatch:
    types: [run_pipeline]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Syntax check
        run: python -m py_compile src/**/*.py
      
      - name: Lint
        run: |
          pip install pylint
          pylint src --fail-under=9.0 || true
      
      - name: Type check (optional)
        run: |
          pip install mypy
          mypy src --ignore-missing-imports || true

  test:
    runs-on: ubuntu-latest
    needs: validate
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: pip install -r requirements.lock pytest pytest-cov pytest-mock
      
      - name: Run unit tests
        run: pytest tests/unit -v --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  etl:
    runs-on: ubuntu-latest
    needs: test
    if: success()
    env:
      SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
      SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
      FPL_LEAGUE_ID: ${{ secrets.FPL_LEAGUE_ID }}
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Backup current data
        run: python -m src.backup_current_data || true
      
      - name: Install dependencies
        run: pip install -r requirements.lock --no-deps
      
      - name: Run ETL pipeline
        run: python -m src.main
      
      - name: Validate output
        run: python -m src.validate_output
      
      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: fpl-data-${{ github.run_number }}
          path: Data/
          retention-days: 30
      
      - name: Slack notify on success
        if: success()
        uses: 8398a7/action-slack@v3
        with:
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
          status: Success ✅
          text: 'FPL ETL completed successfully'
      
      - name: Slack notify on failure
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
          status: Failure ❌
          text: 'FPL ETL failed. Check workflow logs.'
```

---

## 🔮 MEDIUM PRIORITY IMPROVEMENTS

### Performance Optimizations

| Issue | Benefit | Effort |
|-------|---------|--------|
| Chunked parquet loading | Handle multi-year data without OOM | 3 hrs |
| Connection pooling | Reuse HTTP connections | 1 hr |
| Dataframe caching | Avoid re-reading same files | 2 hrs |
| Batch API requests | Combine multiple manager queries | 4 hrs |

### Scalability

| Issue | Benefit | Effort |
|-------|---------|--------|
| Database mode (PostgreSQL) | Scale to 1000+ managers | 6 hrs |
| Distributed processing | Run on multiple workers | 8 hrs |
| Data archival system | Auto-archive old gameweeks | 3 hrs |
| Compression | Reduce storage by 80% | 2 hrs |

### Code Quality

| Issue | Benefit | Effort |
|-------|---------|--------|
| Type hints (mypy) | Catch type errors at lint time | 3 hrs |
| Pre-commit hooks | Automated linting/formatting | 1 hr |
| Dead code removal | Cleaner codebase | 1 hr |
| Extract column mapping | Config-driven instead of hardcoded | 2 hrs |

---

## 🟢 LOW PRIORITY IMPROVEMENTS

### Documentation
- Add architecture decision records (ADRs)
- Document API rate limits and quotas
- Create performance tuning guide
- Add troubleshooting FAQ

### Monitoring
- Add performance metrics (API response times, data size)
- Track data quality (nulls, anomalies)
- Monitor storage usage
- Log execution statistics

### User Experience
- Add CLI with options (league ID, dry-run, verbose)
- Interactive setup wizard
- Dashboard to view current data
- Export utilities (to CSV, JSON)

---

## 📅 RECOMMENDED ROLLOUT TIMELINE

### **Month 1: Robustness** ⚠️ MUST DO
```
Week 1: Fix imports, extract config, add validation
Week 2: Remove dead code, add basic error handling  
Week 3: Create unit test foundation (20% coverage)
Week 4: Fix ci/cd, add notifications
```

### **Month 2: Performance** 🔥 SHOULD DO
```
Week 1-2: Implement parallel API calls
Week 3: Append-only merge strategy
Week 4: Performance testing & benchmarking
```

### **Month 3: Scale & Polish** 📈 NICE TO HAVE
```
Week 1-2: Add test coverage to 60%+
Week 3: Database mode exploration
Week 4: Documentation & polish
```

---

## ✅ SUCCESS METRICS

After implementing improvements:

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Test Coverage | 0% | 60%+ | Month 2 |
| API Call Time | ~120s (20 GW serial) | ~30s (parallel) | Month 2 |
| Merge Time | ~10s (full reload) | ~2s (append) | Month 2 |
| Uptime | N/A | 99.9% | Month 3 |
| Error Recovery | 0% | 100% (auto-retry) | Month 1 |
| Documentation | Good | Excellent | Ongoing |

---

## 🚀 GETTING STARTED

### Next Steps (Do This Today)
1. ✅ Create `src/config.py` with all constants
2. ✅ Fix imports in `src/main.py`
3. ✅ Create `src/validators.py` with schema checks
4. ✅ Create `tests/` directory structure
5. ✅ Add first unit test: `tests/unit/test_utils.py`

### This Week
- [ ] Implement parallel API calls
- [ ] Add Slack notifications to CI/CD
- [ ] Reach 20% test coverage

### This Month
- [ ] 60% test coverage
- [ ] Append-only merge strategy
- [ ] Enhanced error handling
- [ ] Performance benchmarks

---

**Questions or suggestions?** Check `docs/PROJECT_STRUCTURE.md` and `README.md`

