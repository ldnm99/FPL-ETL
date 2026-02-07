# Updated Dimensional Model - Player Stats & Fixtures

## Changes Summary

### 1. ✅ Complete Player Data (All Columns)

**Updated Tables**:
- `dim_players` - Now includes ALL available columns from FPL API
- `fact_player_seasonal_stats` - NEW table for seasonal accumulated stats

**Player Data Now Split Into**:
1. **dim_players**: Profile + ALL seasonal stats (70+ columns)
2. **fact_player_performance**: Gameweek-specific stats (per GW)
3. **fact_player_seasonal_stats**: Season totals snapshot

---

### 2. ✅ New dim_fixtures (with Difficulty Ratings)

**Created**: `dim_fixtures.parquet`

**Connections**:
- `home_club_id` → `dim_clubs.club_id` (FK)
- `away_club_id` → `dim_clubs.club_id` (FK)
- `gameweek_id` → `dim_gameweeks.gameweek_id` (FK)

**Columns**:
- `fixture_id` (PK)
- `gameweek_id` (FK)
- `home_club_id` (FK) ← Connection to clubs
- `away_club_id` (FK) ← Connection to clubs
- `home_difficulty` ← Difficulty rating for home team
- `away_difficulty` ← Difficulty rating for away team
- `kickoff_time`
- `home_score`
- `away_score`
- `is_finished`
- `is_started`

---

## Updated ER Diagram (Mermaid)

```mermaid
erDiagram
    dim_clubs ||--o{ dim_players : "has many players"
    dim_clubs ||--o{ dim_fixtures_home : "plays at home"
    dim_clubs ||--o{ dim_fixtures_away : "plays away"
    dim_clubs ||--o{ fact_player_performance : "plays for"
    
    dim_players ||--o{ fact_player_performance : "has gameweek stats"
    dim_players ||--|| fact_player_seasonal_stats : "has seasonal stats"
    dim_players ||--o{ fact_manager_picks : "is picked"
    
    dim_managers ||--o{ fact_manager_picks : "picks players"
    
    dim_gameweeks ||--o{ fact_player_performance : "contains performances"
    dim_gameweeks ||--o{ fact_manager_picks : "contains picks"
    dim_gameweeks ||--o{ dim_fixtures : "contains matches"
    
    dim_clubs {
        int club_id PK
        string club_name
        string short_name
        timestamp created_at
    }
    
    dim_players {
        int player_key PK "Surrogate"
        int player_id UK "Natural"
        string name
        int club_id FK "→ dim_clubs"
        string position
        int code
        
        SEASONAL_STATS "70+ columns"
        int total_points "Season total"
        int goals "Season total"
        int assists "Season total"
        int minutes "Season total"
        float xG "Expected goals"
        float xA "Expected assists"
        float PpG "Points per game"
        int now_cost "Current price"
        string status "Available/Injured"
        float form "Recent form"
        float selected_by_percent "% ownership"
        
        date valid_from
        date valid_to
        boolean is_current
    }
    
    dim_fixtures {
        int fixture_id PK
        int gameweek_id FK "→ dim_gameweeks"
        int home_club_id FK "→ dim_clubs"
        int away_club_id FK "→ dim_clubs"
        int home_difficulty "1-5 rating"
        int away_difficulty "1-5 rating"
        timestamp kickoff_time
        int home_score
        int away_score
        boolean is_finished
        boolean is_started
    }
    
    fact_player_seasonal_stats {
        bigint seasonal_stats_id PK
        int player_id FK "→ dim_players"
        int player_key FK "→ dim_players"
        int club_id FK "→ dim_clubs"
        
        ALL_SEASONAL_COLUMNS "70+"
        int total_points
        int goals
        int assists
        int clean_sheets
        int minutes
        float xG
        float xA
        float PpG
        int now_cost
        string status
        float form
    }
    
    fact_player_performance {
        bigint performance_id PK
        int player_id FK
        int club_id FK
        int gameweek_id FK
        
        GW_SPECIFIC_STATS
        int gw_points
        int gw_minutes
        int gw_goals
        int gw_assists
        int gw_clean_sheets
        int gw_bonus
    }
```

---

## Complete Table Definitions

### dim_players (Enhanced - All Columns)

**Purpose**: Player profiles with ALL available seasonal stats

| Column Category | Examples | Count |
|----------------|----------|-------|
| **Identifiers** | player_id, player_key, code | 3 |
| **Profile** | name, position, club_id | 5 |
| **Seasonal Totals** | total_points, goals, assists, minutes, clean_sheets | 15+ |
| **Expected Stats** | xG, xA, xGi, xGc | 4 |
| **Averages** | PpG, points_per_game, form | 3 |
| **Value** | now_cost, cost_change_start, cost_change_event | 3 |
| **Influence** | influence, creativity, threat, ict_index, bps | 5 |
| **Availability** | status, chance_of_playing_this_round, news | 4 |
| **Appearances** | starts, appearances, minutes | 3 |
| **Discipline** | yellow_cards, red_cards | 2 |
| **Other** | selected_by_percent, transfers_in, transfers_out | 10+ |
| **SCD Type 2** | valid_from, valid_to, is_current | 3 |

**Total**: 70+ columns (all from FPL API preserved)

---

### fact_player_seasonal_stats (NEW)

**Purpose**: Current season snapshot of player stats (accumulated totals)

**Grain**: One row per player

**Key Columns**:
```
seasonal_stats_id (PK)
player_id (FK)
player_key (FK)
club_id (FK)

# All seasonal accumulated stats
total_points, goals, assists, clean_sheets, minutes
xG, xA, xGi, xGc
PpG, form, selected_by_percent
now_cost, status
influence, creativity, threat, ict_index
starts, appearances
yellow_cards, red_cards
... (70+ total)
```

---

### dim_fixtures (NEW)

**Purpose**: Match fixtures with difficulty ratings

**Grain**: One row per match

**Relationships**:
- `home_club_id` → `dim_clubs.club_id` (N:1)
- `away_club_id` → `dim_clubs.club_id` (N:1)
- `gameweek_id` → `dim_gameweeks.gameweek_id` (N:1)

**Columns**:
```sql
fixture_id          INT         Primary Key
gameweek_id         INT         FK → dim_gameweeks
home_club_id        INT         FK → dim_clubs (home team)
away_club_id        INT         FK → dim_clubs (away team)
home_difficulty     INT         Difficulty rating 1-5 (for home team)
away_difficulty     INT         Difficulty rating 1-5 (for away team)
kickoff_time        TIMESTAMP   Match start time
home_score          INT         Home team goals (NULL if not played)
away_score          INT         Away team goals (NULL if not played)
is_finished         BOOLEAN     Has match finished?
is_started          BOOLEAN     Has match started?
```

**Difficulty Rating Scale**:
- 1 = Very Easy
- 2 = Easy
- 3 = Medium
- 4 = Hard
- 5 = Very Hard

---

## Data Access Patterns

### Pattern 1: Seasonal Stats (Overall Performance)
```python
# Use fact_player_seasonal_stats
seasonal_stats = pd.read_parquet('Data/gold/facts/fact_player_seasonal_stats.parquet')

# All columns available
print(seasonal_stats[['name', 'total_points', 'goals', 'assists', 'xG', 'PpG', 'now_cost']])
```

### Pattern 2: Gameweek Stats (Performance per GW)
```python
# Use fact_player_performance
gw_stats = pd.read_parquet('Data/gold/facts/fact_player_performance.parquet')

# Filter for specific gameweek
gw10 = gw_stats[gw_stats['gameweek_id'] == 10]
print(gw10[['player_id', 'gw_points', 'gw_goals', 'gw_assists']])
```

### Pattern 3: Fixtures with Difficulty
```python
# Load fixtures and clubs
fixtures = pd.read_parquet('Data/gold/dimensions/dim_fixtures.parquet')
clubs = pd.read_parquet('Data/gold/dimensions/dim_clubs.parquet')

# Join to get club names
fixtures_with_clubs = fixtures.merge(
    clubs.rename(columns={'club_id': 'home_club_id', 'club_name': 'home_team'}),
    on='home_club_id'
).merge(
    clubs.rename(columns={'club_id': 'away_club_id', 'club_name': 'away_team'}),
    on='away_club_id'
)

# Show upcoming fixtures with difficulty
upcoming = fixtures_with_clubs[fixtures_with_clubs['is_finished'] == False]
print(upcoming[['home_team', 'away_team', 'home_difficulty', 'away_difficulty', 'kickoff_time']])
```

### Pattern 4: Player with Upcoming Fixtures
```python
# Get player's club
players = pd.read_parquet('Data/gold/dimensions/dim_players.parquet')
salah = players[players['name'] == 'M. Salah'].iloc[0]

# Get Liverpool's upcoming fixtures
fixtures = pd.read_parquet('Data/gold/dimensions/dim_fixtures.parquet')
liverpool_fixtures = fixtures[
    (fixtures['home_club_id'] == salah['club_id']) | 
    (fixtures['away_club_id'] == salah['club_id'])
]
```

---

## Updated File Structure

```
Data/gold/
├── dimensions/
│   ├── dim_clubs.parquet
│   ├── dim_players.parquet          ← Enhanced with ALL columns (70+)
│   ├── dim_managers.parquet
│   ├── dim_gameweeks.parquet
│   └── dim_fixtures.parquet         ← NEW (with difficulty ratings)
│
└── facts/
    ├── fact_player_performance.parquet      ← Gameweek stats
    ├── fact_player_seasonal_stats.parquet   ← NEW (seasonal stats)
    ├── fact_manager_picks.parquet
    └── manager_gameweek_performance.parquet
```

---

## Benefits

✅ **Complete Player Data**: Access to all 70+ columns from FPL API  
✅ **Separated Concerns**: Seasonal vs Gameweek stats clearly separated  
✅ **Fixture Planning**: Difficulty ratings help with transfer decisions  
✅ **Club Connections**: Fixtures properly linked to home/away clubs  
✅ **Query Flexibility**: Choose seasonal or gameweek stats as needed  

---

## Sample Queries

### Query 1: Players with Best Form and Low Cost
```python
seasonal = pd.read_parquet('Data/gold/facts/fact_player_seasonal_stats.parquet')

# Filter by form and cost
value_players = seasonal[
    (seasonal['form'] > 5.0) & 
    (seasonal['now_cost'] < 80)  # Cost in 0.1m units
].sort_values('PpG', ascending=False)

print(value_players[['name', 'position', 'PpG', 'form', 'now_cost']].head(10))
```

### Query 2: Upcoming Easy Fixtures
```python
fixtures = pd.read_parquet('Data/gold/dimensions/dim_fixtures.parquet')
clubs = pd.read_parquet('Data/gold/dimensions/dim_clubs.parquet')

# Easy home fixtures (difficulty 1-2)
easy_home = fixtures[
    (fixtures['home_difficulty'] <= 2) & 
    (fixtures['is_finished'] == False)
].merge(clubs, left_on='home_club_id', right_on='club_id')

print(easy_home[['club_name', 'gameweek_id', 'home_difficulty']])
```

---

**Updated**: February 2026
