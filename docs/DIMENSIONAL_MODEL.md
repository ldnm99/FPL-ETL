# Dimensional Model - Tables & Relationships

## Overview

The Gold layer now includes a **star schema dimensional model** with proper relationships and a denormalized table for easy querying.

---

## 📊 Dimensional Model (Star Schema)

### Entity-Relationship Diagram

```
                    dim_clubs
                    ┌─────────────┐
                    │ club_id (PK)│
                    │ club_name   │
                    │ short_name  │
                    └──────┬──────┘
                           │
                           │ 1:N (one club has many players)
                           │
                    ┌──────▼──────┐
                    │ dim_players │
                    ├─────────────┤
                    │ player_id(PK│
                    │ name        │
                    │ club_id (FK)│◄────┐
                    │ position    │     │
                    └──────┬──────┘     │
                           │            │
                           │ N:1        │ N:1
                           │            │
              ┌────────────┼────────────┼──────────┐
              │            │            │          │
    ┌─────────▼────┐  ┌────▼─────┐  ┌──▼──────────▼───┐
    │fact_manager  │  │   fact_  │  │  dim_gameweeks  │
    │   _picks     │  │  player_ │  ├─────────────────┤
    ├──────────────┤  │performance│  │ gameweek_id (PK)│
    │ pick_id (PK) │  ├───────────┤  │ gameweek_num    │
    │ manager_id(FK│  │ perf_id(PK│  │ is_finished     │
    │ player_id(FK)│  │ player_id │  │ is_current      │
    │ gameweek_id  │  │   (FK)    │  └─────────────────┘
    │ position     │  │ club_id(FK│
    └──────┬───────┘  │ gameweek_ │
           │          │   id (FK) │
           │          │ gw_points │
           │          │ gw_goals  │
           │          │ gw_assists│
           │          └───────────┘
           │
           │ N:1
           │
    ┌──────▼─────────┐
    │  dim_managers  │
    ├────────────────┤
    │ manager_id (PK)│
    │ first_name     │
    │ last_name      │
    │ team_name      │
    └────────────────┘
```

---

## 📋 Tables Detail

### Dimension Tables

#### 1. `dim_clubs` (Reference for Teams)
**Relationship**: **1:N with dim_players** (one club has many players)

| Column | Type | Description |
|--------|------|-------------|
| club_id (PK) | INT | Primary Key |
| club_name | VARCHAR | Full name (e.g., "Manchester City") |
| short_name | VARCHAR | 3-letter code (e.g., "MCI") |
| created_at | TIMESTAMP | When record was created |

**Sample Data**:
```
club_id | club_name          | short_name
1       | Arsenal            | ARS
2       | Aston Villa        | AVL
3       | Chelsea            | CHE
14      | Liverpool          | LIV
```

---

#### 2. `dim_players` (Player Info with Club)
**Relationship**: 
- **N:1 with dim_clubs** (many players belong to one club) via `club_id`
- **1:N with fact_player_performance** (one player has many performances)
- **1:N with fact_manager_picks** (one player has many picks)

| Column | Type | Description |
|--------|------|-------------|
| player_key (PK) | INT | Surrogate Key |
| player_id | INT | Natural Key (from API) |
| name | VARCHAR | Player name |
| **club_id (FK)** | INT | **Foreign Key → dim_clubs** |
| position | VARCHAR | GK, DEF, MID, FWD |
| code | INT | FPL player code |
| valid_from | DATE | When this version became active |
| valid_to | DATE | When expired (NULL = current) |
| is_current | BOOLEAN | True for current version |

**Sample Data**:
```
player_id | name        | club_id | position | is_current
263       | M. Salah    | 14      | MID      | True
308       | Haaland     | 1       | FWD      | True
```

**Relationship Example**:
```sql
-- Get all players for Liverpool (club_id = 14)
SELECT p.name, p.position, c.club_name
FROM dim_players p
JOIN dim_clubs c ON p.club_id = c.club_id
WHERE c.club_id = 14 AND p.is_current = TRUE;
```

---

#### 3. `dim_managers` (Manager Info)
**Relationship**: **1:N with fact_manager_picks** (one manager has many picks)

| Column | Type | Description |
|--------|------|-------------|
| manager_id (PK) | INT | Primary Key |
| first_name | VARCHAR | Manager first name |
| last_name | VARCHAR | Manager last name |
| team_name | VARCHAR | Fantasy team name |
| waiver_pick | INT | Waiver order |

---

#### 4. `dim_gameweeks` (Gameweek Calendar)
**Relationship**: 
- **1:N with fact_player_performance** (one gameweek has many performances)
- **1:N with fact_manager_picks** (one gameweek has many picks)

| Column | Type | Description |
|--------|------|-------------|
| gameweek_id (PK) | INT | Primary Key |
| gameweek_num | INT | Gameweek number (1-38) |
| is_finished | BOOLEAN | Has gameweek finished? |
| is_current | BOOLEAN | Is this current GW? |
| avg_score | FLOAT | Average score across league |

---

### Fact Tables

#### 1. `fact_player_performance` (Player Stats per GW)
**Grain**: One row per player per gameweek

**Relationships**:
- `player_id` → `dim_players.player_id` (N:1)
- `club_id` → `dim_clubs.club_id` (N:1)
- `gameweek_id` → `dim_gameweeks.gameweek_id` (N:1)

| Column | Type | Description |
|--------|------|-------------|
| performance_id (PK) | BIGINT | Surrogate Key |
| player_id (FK) | INT | → dim_players |
| **club_id (FK)** | INT | **→ dim_clubs** |
| gameweek_id (FK) | INT | → dim_gameweeks |
| gw_points | INT | Points this gameweek |
| gw_minutes | INT | Minutes played |
| gw_goals | INT | Goals scored |
| gw_assists | INT | Assists |
| gw_clean_sheets | INT | Clean sheets |
| gw_bonus | INT | Bonus points |

---

#### 2. `fact_manager_picks` (Manager Selections)
**Grain**: One row per manager per player per gameweek

**Relationships**:
- `manager_id` → `dim_managers.manager_id` (N:1)
- `player_id` → `dim_players.player_id` (N:1)
- `gameweek_id` → `dim_gameweeks.gameweek_id` (N:1)

| Column | Type | Description |
|--------|------|-------------|
| pick_id (PK) | BIGINT | Surrogate Key |
| manager_id (FK) | INT | → dim_managers |
| player_id (FK) | INT | → dim_players |
| gameweek_id (FK) | INT | → dim_gameweeks |
| position | INT | Position in team (1-15) |

---

## 🎯 Special Table: Manager Gameweek Performance

### `manager_gameweek_performance` (Denormalized)

**This is the table you requested!** It shows each manager's full team with performance for each gameweek.

**Grain**: One row per manager per player per gameweek (with all joins pre-computed)

| Column | Type | Description |
|--------|------|-------------|
| gameweek_num | INT | Gameweek number |
| manager_id | INT | Manager ID |
| first_name | VARCHAR | Manager first name |
| last_name | VARCHAR | Manager last name |
| manager_team_name | VARCHAR | Manager's team name |
| player_id | INT | Player ID |
| player_name | VARCHAR | Player name |
| player_position | VARCHAR | Player position |
| **club_name** | VARCHAR | **Premier League club** |
| **short_name** | VARCHAR | **Club short name** |
| team_position | INT | Position in manager's team |
| gw_points | INT | Points scored this GW |
| gw_minutes | INT | Minutes played |
| gw_goals | INT | Goals scored |
| gw_assists | INT | Assists |
| gw_clean_sheets | INT | Clean sheets |
| gw_bonus | INT | Bonus points |
| is_finished | BOOLEAN | Is gameweek finished? |

**Sample Data**:
```
gameweek_num | manager_id | manager_team_name | player_name | club_name   | gw_points
1            | 123        | FC Thunder        | M. Salah    | Liverpool   | 12
1            | 123        | FC Thunder        | Haaland     | Man City    | 18
1            | 123        | FC Thunder        | Son         | Spurs       | 8
2            | 123        | FC Thunder        | M. Salah    | Liverpool   | 6
2            | 123        | FC Thunder        | Haaland     | Man City    | 15
```

---

## 🔍 Sample Queries

### Query 1: Manager's Team for Gameweek 10 (Using Denormalized Table)
```python
import pandas as pd

# Load the denormalized table
df = pd.read_parquet('Data/gold/facts/manager_gameweek_performance.parquet')

# Filter for specific manager and gameweek
my_team = df[(df['manager_id'] == 123) & (df['gameweek_num'] == 10)]

# Show team performance
print(my_team[['player_name', 'club_name', 'player_position', 'gw_points']])
```

**Output**:
```
   player_name    club_name  player_position  gw_points
0  M. Salah       Liverpool        MID            12
1  Haaland        Man City         FWD            18
2  Son            Spurs            MID             8
...
```

---

### Query 2: All Players from Manchester City (Using Dimensional Model)
```python
import pandas as pd

# Load dimensions
dim_players = pd.read_parquet('Data/gold/dimensions/dim_players.parquet')
dim_clubs = pd.read_parquet('Data/gold/dimensions/dim_clubs.parquet')

# Join players with clubs
players_with_clubs = dim_players.merge(
    dim_clubs,
    on='club_id',
    how='left'
)

# Filter for Manchester City
mci_players = players_with_clubs[
    players_with_clubs['club_name'] == 'Manchester City'
]

print(mci_players[['name', 'position', 'club_name']])
```

---

### Query 3: Manager Performance Over Season
```python
# Load denormalized table
df = pd.read_parquet('Data/gold/facts/manager_gameweek_performance.parquet')

# Aggregate by manager and gameweek
manager_summary = df.groupby(['gameweek_num', 'manager_id', 'manager_team_name']).agg({
    'gw_points': 'sum'
}).reset_index()

# Calculate cumulative points
manager_summary['cumulative_points'] = manager_summary.groupby('manager_id')['gw_points'].cumsum()

print(manager_summary)
```

---

### Query 4: Top Scorers by Club
```python
# Load facts and dimensions
fact_perf = pd.read_parquet('Data/gold/facts/fact_player_performance.parquet')
dim_players = pd.read_parquet('Data/gold/dimensions/dim_players.parquet')
dim_clubs = pd.read_parquet('Data/gold/dimensions/dim_clubs.parquet')

# Join all together
player_stats = fact_perf.merge(dim_players, on='player_id')
player_stats = player_stats.merge(dim_clubs, on='club_id')

# Aggregate by player and club
top_scorers = player_stats.groupby(['club_name', 'name']).agg({
    'gw_points': 'sum',
    'gw_goals': 'sum'
}).reset_index()

# Sort by total points
top_scorers = top_scorers.sort_values('gw_points', ascending=False)

print(top_scorers.head(10))
```

---

## 📁 File Structure

```
Data/gold/
├── dimensions/
│   ├── dim_managers.parquet        # Manager info
│   ├── dim_clubs.parquet           # Premier League clubs
│   ├── dim_players.parquet         # Players (linked to clubs via club_id)
│   └── dim_gameweeks.parquet       # Gameweek calendar
│
└── facts/
    ├── fact_player_performance.parquet      # Player stats per GW
    ├── fact_manager_picks.parquet           # Manager selections
    └── manager_gameweek_performance.parquet # 🎯 DENORMALIZED TABLE
```

---

## 🔗 Key Relationships Summary

1. **dim_clubs → dim_players**: One club has many players (via `club_id`)
2. **dim_players → fact_player_performance**: One player has many performances
3. **dim_players → fact_manager_picks**: One player can be picked by many managers
4. **dim_managers → fact_manager_picks**: One manager has many picks
5. **dim_gameweeks → fact_***: One gameweek has many facts

---

## ⚡ Benefits

✅ **Normalized**: Dimensions prevent data duplication  
✅ **Connected**: All tables properly linked via foreign keys  
✅ **Queryable**: Easy to write SQL/Pandas queries  
✅ **Denormalized Option**: `manager_gameweek_performance` for fast queries  
✅ **Club Connection**: Players linked to clubs via `club_id`  

---

## 🚀 Usage

### For Analysis (Use Denormalized Table)
```python
df = pd.read_parquet('Data/gold/facts/manager_gameweek_performance.parquet')
# All joins already done, ready to query!
```

### For Data Warehouse (Use Star Schema)
Load dimensions and facts separately, join as needed for specific queries.

---

**The `manager_gameweek_performance` table is exactly what you asked for** - it shows each manager's player picks for each gameweek along the season, with club information included! 🎉
