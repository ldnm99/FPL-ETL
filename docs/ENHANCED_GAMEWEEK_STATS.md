# Enhanced Gameweek Stats - Complete Column List

## Summary

**Added 18 new columns** to `fact_player_performance` table!

**Before**: 15 columns (basic stats only)  
**After**: 33 columns (comprehensive stats)

---

## Complete Column List

### Identity & Keys (5 columns)
1. `performance_id` - Surrogate key
2. `player_key` - Player dimension key
3. `player_id` - FPL player ID
4. `club_id` - Club dimension key
5. `gameweek_id` - Gameweek dimension key

### Basic Performance (7 columns)
6. `gw_points` - Total FPL points
7. `gw_minutes` - Minutes played
8. `gw_goals` - Goals scored
9. `gw_assists` - Assists
10. `gw_clean_sheets` - Clean sheets (defenders/GK)
11. `gw_goals_conceded` - Goals conceded (defenders/GK)
12. `gw_bonus` - Bonus points

### Advanced Performance (4 columns)
13. `gw_bps` - Bonus Points System score
14. `gw_saves` - Saves (goalkeepers)
15. `gw_penalties_saved` - Penalty saves
16. `gw_penalties_missed` - Penalty misses

### Disciplinary (3 columns)
17. `gw_yellow_cards` - Yellow cards
18. `gw_red_cards` - Red cards  
19. `gw_own_goals` - Own goals

### ICT Index Stats (4 columns)
20. `gw_influence` - Influence score
21. `gw_creativity` - Creativity score
22. `gw_threat` - Threat score
23. `gw_ict_index` - Overall ICT index

### Expected Stats (4 columns)
24. `gw_xG` - Expected goals
25. `gw_xA` - Expected assists
26. `gw_xGi` - Expected goal involvements
27. `gw_xGc` - Expected goals conceded

### Defensive Stats (4 columns)
28. `gw_clearances_blocks_interceptions` - Defensive actions
29. `gw_recoveries` - Ball recoveries
30. `gw_tackles` - Successful tackles
31. `gw_defensive_contribution` - Overall defensive contribution

### Other (2 columns)
32. `gw_starts` - Started the match (1) or bench (0)
33. `gw_in_dreamteam` - In dream team this GW

---

## Usage Examples

### Find Top xG Performers in a Gameweek

```python
import pandas as pd

df = pd.read_parquet('Data/gold/facts/fact_player_performance.parquet')

# Top xG in GW25
top_xg = df[df['gameweek_id'] == 25].nlargest(10, 'gw_xG')
print(top_xg[['player_id', 'gw_xG', 'gw_goals', 'gw_points']])
```

### Analyze Defensive Contribution

```python
# Best defenders by tackles + recoveries
df['defensive_actions'] = df['gw_tackles'] + df['gw_recoveries']
top_defenders = df.nlargest(20, 'defensive_actions')
print(top_defenders[[' player_id', 'gw_tackles', 'gw_recoveries', 'defensive_actions']])
```

### Compare xG vs Actual Goals

```python
# Players outperforming xG
df['goals_vs_xg'] = df['gw_goals'] - df['gw_xG']
overperformers = df[df['goals_vs_xg'] > 0].sort_values('goals_vs_xg', ascending=False)
print(overperformers[['player_id', 'gw_goals', 'gw_xG', 'goals_vs_xg']].head(10))
```

### ICT Index Analysis

```python
# Players with high threat but low goals
high_threat = df[(df['gw_threat'] > 50) & (df['gw_goals'] == 0)]
print(high_threat[['player_id', 'gw_threat', 'gw_xG', 'gw_goals']])
```

---

## Data Source

All stats come from the **FPL Gameweek API** endpoint:
- `https://draft.premierleague.com/api/event/{gameweek}/live`
- Located in the `elements[player_id]['stats']` object
- Extracted in Bronze layer, transformed in Silver, aggregated in Gold

---

## Files Updated

### Silver Layer (`src/etl/silver.py`)
- Updated `transform_gameweek_data()` to extract ALL stats from the API
- Changed from parsing `explain` array to reading `stats` object directly
- Now extracts 28 gameweek-level stats (up from 10)

### Gold Layer (`src/etl/gold_facts.py`)
- Updated `create_fact_player_performance()` column mapping
- Added all 18 new columns to fact table
- Renamed expected stats for clarity (expected_goals → gw_xG)

### Data Files
- **Silver**: `Data/silver/gameweeks_parquet/*.parquet` (now 32 columns)
- **Gold**: `Data/gold/facts/fact_player_performance.parquet` (now 33 columns)

---

## Verification

```bash
# Check Silver columns (should be 32)
python -c "import pandas as pd; df = pd.read_parquet('Data/silver/gameweeks_parquet/gw_data_gw1.parquet'); print('Silver columns:', len(df.columns))"

# Check Gold fact columns (should be 33)
python -c "import pandas as pd; df = pd.read_parquet('Data/gold/facts/fact_player_performance.parquet'); print('Fact columns:', len(df.columns))"
```

---

## Status

✅ **Complete** - All requested stats now available in Gold layer!

**Updated**: February 7, 2026  
**Version**: 2.0.1 (enhanced stats)
