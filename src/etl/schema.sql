-- ============================================================
-- Project Blaziken: FPL Draft Star Schema & Views (Supabase Postgres)
-- ============================================================

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- 1. DIMENSION TABLES
-- ------------------------------------------------------------

-- Premier League Clubs
CREATE TABLE IF NOT EXISTS dim_clubs (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(10) NOT NULL,
    code INT,
    badge_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- FPL Players
CREATE TABLE IF NOT EXISTS dim_players (
    id INT PRIMARY KEY,
    web_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100),
    second_name VARCHAR(100),
    club_id INT REFERENCES dim_clubs(id) ON DELETE SET NULL,
    position_name VARCHAR(10) NOT NULL, -- GKP, DEF, MID, FWD
    element_type INT, -- 1=GKP, 2=DEF, 3=MID, 4=FWD
    price DECIMAL(4,1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Draft League Managers
CREATE TABLE IF NOT EXISTS dim_managers (
    id INT PRIMARY KEY,
    manager_name VARCHAR(100) NOT NULL,
    team_name VARCHAR(100) NOT NULL,
    draft_pick_order INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Gameweeks
CREATE TABLE IF NOT EXISTS dim_gameweeks (
    id INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    deadline_time TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT FALSE,
    is_next BOOLEAN DEFAULT FALSE,
    is_finished BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fixtures
CREATE TABLE IF NOT EXISTS dim_fixtures (
    id INT PRIMARY KEY,
    gameweek_id INT REFERENCES dim_gameweeks(id) ON DELETE CASCADE,
    team_h INT REFERENCES dim_clubs(id) ON DELETE CASCADE,
    team_a INT REFERENCES dim_clubs(id) ON DELETE CASCADE,
    team_h_score INT,
    team_a_score INT,
    fdr_h INT,
    fdr_a INT,
    kickoff_time TIMESTAMPTZ,
    finished BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 2. FACT TABLES (FPL DRAFT RULES: NO CAPTAINS, NO CHIPS)
-- ------------------------------------------------------------

-- Manager Gameweek Picks (Starting XI = pos 1-11, Bench = pos 12-15)
CREATE TABLE IF NOT EXISTS fact_manager_picks (
    manager_id INT REFERENCES dim_managers(id) ON DELETE CASCADE,
    gameweek_id INT REFERENCES dim_gameweeks(id) ON DELETE CASCADE,
    player_id INT REFERENCES dim_players(id) ON DELETE CASCADE,
    position INT NOT NULL, -- 1 to 15
    PRIMARY KEY (manager_id, gameweek_id, player_id)
);

-- Player Performance per Gameweek
CREATE TABLE IF NOT EXISTS fact_player_performance (
    player_id INT REFERENCES dim_players(id) ON DELETE CASCADE,
    gameweek_id INT REFERENCES dim_gameweeks(id) ON DELETE CASCADE,
    total_points INT DEFAULT 0,
    goals_scored INT DEFAULT 0,
    assists INT DEFAULT 0,
    clean_sheets INT DEFAULT 0,
    goals_conceded INT DEFAULT 0,
    own_goals INT DEFAULT 0,
    penalties_saved INT DEFAULT 0,
    penalties_missed INT DEFAULT 0,
    yellow_cards INT DEFAULT 0,
    red_cards INT DEFAULT 0,
    saves INT DEFAULT 0,
    bonus INT DEFAULT 0,
    bps INT DEFAULT 0,
    minutes INT DEFAULT 0,
    PRIMARY KEY (player_id, gameweek_id)
);

-- Draft Waivers & Free Agent Transactions
CREATE TABLE IF NOT EXISTS fact_draft_transactions (
    id SERIAL PRIMARY KEY,
    manager_id INT REFERENCES dim_managers(id) ON DELETE CASCADE,
    gameweek_id INT REFERENCES dim_gameweeks(id) ON DELETE CASCADE,
    element_in INT REFERENCES dim_players(id) ON DELETE SET NULL,
    element_out INT REFERENCES dim_players(id) ON DELETE SET NULL,
    transaction_type VARCHAR(20) NOT NULL, -- 'waiver' | 'free_agent'
    transaction_time TIMESTAMPTZ DEFAULT NOW()
);

-- ------------------------------------------------------------
-- 3. INDEXES FOR SUB-10MS QUERY PERFORMANCE
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_players_club ON dim_players(club_id);
CREATE INDEX IF NOT EXISTS idx_picks_manager_gw ON fact_manager_picks(manager_id, gameweek_id);
CREATE INDEX IF NOT EXISTS idx_picks_player ON fact_manager_picks(player_id);
CREATE INDEX IF NOT EXISTS idx_perf_player_gw ON fact_player_performance(player_id, gameweek_id);
CREATE INDEX IF NOT EXISTS idx_fixtures_gw ON dim_fixtures(gameweek_id);

-- ------------------------------------------------------------
-- 4. DATABASE VIEWS FOR INSTANT 1-QUERY FRONTEND FETCHING
-- ------------------------------------------------------------

-- View: Complete Manager Starting XI & Bench for any Gameweek with Player + Club Details
CREATE OR REPLACE VIEW vw_draft_gameweek_overview AS
SELECT 
    mp.manager_id,
    m.manager_name,
    m.team_name,
    mp.gameweek_id,
    mp.position,
    CASE WHEN mp.position <= 11 THEN TRUE ELSE FALSE END AS is_starter,
    p.id AS player_id,
    p.web_name,
    p.position_name,
    c.name AS club_name,
    c.short_name AS club_code,
    c.badge_url,
    COALESCE(pp.total_points, 0) AS points,
    COALESCE(pp.goals_scored, 0) AS goals,
    COALESCE(pp.assists, 0) AS assists,
    COALESCE(pp.minutes, 0) AS minutes
FROM fact_manager_picks mp
JOIN dim_managers m ON mp.manager_id = m.id
JOIN dim_players p ON mp.player_id = p.id
LEFT JOIN dim_clubs c ON p.club_id = c.id
LEFT JOIN fact_player_performance pp ON mp.player_id = pp.player_id AND mp.gameweek_id = pp.gameweek_id;

-- View: Cumulative Manager Standings
CREATE OR REPLACE VIEW vw_manager_standings AS
SELECT 
    m.id AS manager_id,
    m.manager_name,
    m.team_name,
    COUNT(DISTINCT mp.gameweek_id) AS gameweeks_played,
    SUM(CASE WHEN mp.position <= 11 THEN COALESCE(pp.total_points, 0) ELSE 0 END) AS total_starter_points,
    SUM(CASE WHEN mp.position > 11 THEN COALESCE(pp.total_points, 0) ELSE 0 END) AS total_bench_points
FROM dim_managers m
LEFT JOIN fact_manager_picks mp ON m.id = mp.manager_id
LEFT JOIN fact_player_performance pp ON mp.player_id = pp.player_id AND mp.gameweek_id = pp.gameweek_id
GROUP BY m.id, m.manager_name, m.team_name
ORDER BY total_starter_points DESC;

-- Enable Row Level Security (RLS) with Public Read Access on ALL tables
ALTER TABLE dim_clubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_managers ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_gameweeks ENABLE ROW LEVEL SECURITY;
ALTER TABLE dim_fixtures ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_manager_picks ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_player_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_draft_transactions ENABLE ROW LEVEL SECURITY;

-- Safely recreate public read policies
DROP POLICY IF EXISTS "Allow public read access on dim_clubs" ON dim_clubs;
DROP POLICY IF EXISTS "Allow public read access on dim_players" ON dim_players;
DROP POLICY IF EXISTS "Allow public read access on dim_managers" ON dim_managers;
DROP POLICY IF EXISTS "Allow public read access on dim_gameweeks" ON dim_gameweeks;
DROP POLICY IF EXISTS "Allow public read access on dim_fixtures" ON dim_fixtures;
DROP POLICY IF EXISTS "Allow public read access on fact_manager_picks" ON fact_manager_picks;
DROP POLICY IF EXISTS "Allow public read access on fact_player_performance" ON fact_player_performance;
DROP POLICY IF EXISTS "Allow public read access on fact_draft_transactions" ON fact_draft_transactions;

CREATE POLICY "Allow public read access on dim_clubs" ON dim_clubs FOR SELECT USING (true);
CREATE POLICY "Allow public read access on dim_players" ON dim_players FOR SELECT USING (true);
CREATE POLICY "Allow public read access on dim_managers" ON dim_managers FOR SELECT USING (true);
CREATE POLICY "Allow public read access on dim_gameweeks" ON dim_gameweeks FOR SELECT USING (true);
CREATE POLICY "Allow public read access on dim_fixtures" ON dim_fixtures FOR SELECT USING (true);
CREATE POLICY "Allow public read access on fact_manager_picks" ON fact_manager_picks FOR SELECT USING (true);
CREATE POLICY "Allow public read access on fact_player_performance" ON fact_player_performance FOR SELECT USING (true);
CREATE POLICY "Allow public read access on fact_draft_transactions" ON fact_draft_transactions FOR SELECT USING (true);
