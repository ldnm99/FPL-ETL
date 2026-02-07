# Entity-Relationship Diagram - FPL ETL Dimensional Model

## Mermaid ER Diagram

```mermaid
erDiagram
    dim_clubs ||--o{ dim_players : "has many"
    dim_players ||--o{ fact_player_performance : "has stats"
    dim_players ||--o{ fact_manager_picks : "is picked by"
    dim_managers ||--o{ fact_manager_picks : "picks"
    dim_gameweeks ||--o{ fact_player_performance : "contains"
    dim_gameweeks ||--o{ fact_manager_picks : "contains"
    dim_clubs ||--o{ fact_player_performance : "plays for"
    
    dim_clubs {
        int club_id PK
        string club_name
        string short_name
        timestamp created_at
    }
    
    dim_players {
        int player_key PK "Surrogate Key"
        int player_id UK "Natural Key"
        string name
        int club_id FK "→ dim_clubs"
        string position "GK, DEF, MID, FWD"
        int code
        date valid_from
        date valid_to "NULL if current"
        boolean is_current
    }
    
    dim_managers {
        int manager_id PK
        string first_name
        string last_name
        string team_name
        int waiver_pick
        timestamp created_at
    }
    
    dim_gameweeks {
        int gameweek_id PK
        int gameweek_num
        string gameweek_name
        timestamp deadline_time
        boolean is_finished
        boolean is_current
        float avg_score
        int highest_score
    }
    
    fact_player_performance {
        bigint performance_id PK
        int player_key FK "→ dim_players"
        int player_id FK "→ dim_players"
        int club_id FK "→ dim_clubs"
        int gameweek_id FK "→ dim_gameweeks"
        int gw_points
        int gw_minutes
        int gw_goals
        int gw_assists
        int gw_clean_sheets
        int gw_goals_conceded
        int gw_bonus
        int gw_saves
        int gw_yellow_cards
        int gw_red_cards
    }
    
    fact_manager_picks {
        bigint pick_id PK
        int manager_id FK "→ dim_managers"
        int player_id FK "→ dim_players"
        int gameweek_id FK "→ dim_gameweeks"
        int position "1-15"
    }
    
    manager_gameweek_performance {
        int gameweek_num
        int manager_id FK
        string first_name
        string last_name
        string manager_team_name
        int player_id FK
        string player_name
        string player_position
        string club_name
        string short_name
        int team_position
        int gw_points
        int gw_minutes
        int gw_goals
        int gw_assists
        int gw_clean_sheets
        int gw_bonus
        boolean is_finished
    }
```

## Relationship Descriptions

### 1:N Relationships

| Parent | Child | Relationship | Description |
|--------|-------|--------------|-------------|
| dim_clubs | dim_players | 1:N | One club has many players |
| dim_clubs | fact_player_performance | 1:N | One club has many performances |
| dim_players | fact_player_performance | 1:N | One player has many performances |
| dim_players | fact_manager_picks | 1:N | One player can be picked many times |
| dim_managers | fact_manager_picks | 1:N | One manager has many picks |
| dim_gameweeks | fact_player_performance | 1:N | One gameweek has many performances |
| dim_gameweeks | fact_manager_picks | 1:N | One gameweek has many picks |

### Foreign Key Constraints

```sql
-- fact_player_performance
ALTER TABLE fact_player_performance
  ADD CONSTRAINT fk_player FOREIGN KEY (player_id) REFERENCES dim_players(player_id),
  ADD CONSTRAINT fk_club FOREIGN KEY (club_id) REFERENCES dim_clubs(club_id),
  ADD CONSTRAINT fk_gameweek FOREIGN KEY (gameweek_id) REFERENCES dim_gameweeks(gameweek_id);

-- fact_manager_picks
ALTER TABLE fact_manager_picks
  ADD CONSTRAINT fk_manager FOREIGN KEY (manager_id) REFERENCES dim_managers(manager_id),
  ADD CONSTRAINT fk_player FOREIGN KEY (player_id) REFERENCES dim_players(player_id),
  ADD CONSTRAINT fk_gameweek FOREIGN KEY (gameweek_id) REFERENCES dim_gameweeks(gameweek_id);
```

## Cardinality Summary

```
dim_clubs (1) ──────────────────→ (N) dim_players
    │
    └───────────────────────────→ (N) fact_player_performance

dim_players (1) ─────────────────→ (N) fact_player_performance
    │
    └───────────────────────────→ (N) fact_manager_picks

dim_managers (1) ────────────────→ (N) fact_manager_picks

dim_gameweeks (1) ───────────────→ (N) fact_player_performance
    │
    └───────────────────────────→ (N) fact_manager_picks
```

## Data Flow

```
Bronze Layer (Raw JSON)
    ↓
Silver Layer (Cleaned CSV/Parquet)
    ↓
Gold Layer - Dimensions
    ├── dim_clubs ← From players_raw.json teams
    ├── dim_players ← From players_data.csv + clubs
    ├── dim_managers ← From league_standings.csv
    └── dim_gameweeks ← From players_raw.json events
    ↓
Gold Layer - Facts
    ├── fact_player_performance ← From gameweek parquets + dims
    ├── fact_manager_picks ← From gameweek parquets + dims
    └── manager_gameweek_performance ← Join all above
```
