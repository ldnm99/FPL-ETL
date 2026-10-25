"""
Pydantic v2 Schemas for FPL-ETL Data Contracts.
Enforces strict type validation and the Lesson 18 Active Starter Invariant on raw FPL Draft payloads.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator, ConfigDict


# ------------------------------------------------------------
# Dimension Ingestion Models
# ------------------------------------------------------------

class ClubIngest(BaseModel):
    """Validated model for dim_clubs record."""
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    short_name: str
    code: Optional[int] = None
    badge_url: Optional[str] = None


class PlayerIngest(BaseModel):
    """Validated model for dim_players record."""
    model_config = ConfigDict(extra="ignore")

    id: int
    web_name: str
    first_name: str = ""
    second_name: str = ""
    club_id: Optional[int] = Field(default=None, alias="team")
    position_name: str = "MID"
    element_type: int = 3
    price: float = 0.0


class GameweekIngest(BaseModel):
    """Validated model for dim_gameweeks record."""
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    deadline_time: Optional[str] = None
    is_current: bool = False
    is_next: bool = False
    is_finished: bool = False


class FixtureIngest(BaseModel):
    """Validated model for dim_fixtures record."""
    model_config = ConfigDict(extra="ignore")

    id: int
    gameweek_id: Optional[int] = Field(default=None, alias="event")
    team_h: Optional[int] = None
    team_a: Optional[int] = None
    team_h_score: Optional[int] = None
    team_a_score: Optional[int] = None
    fdr_h: Optional[int] = Field(default=3, alias="team_h_difficulty")
    fdr_a: Optional[int] = Field(default=3, alias="team_a_difficulty")
    kickoff_time: Optional[str] = None
    started: bool = False
    finished: bool = False
    finished_provisional: bool = False
    minutes: int = 0


class ManagerIngest(BaseModel):
    """Validated model for dim_managers record."""
    model_config = ConfigDict(extra="ignore")

    id: int
    manager_name: str
    team_name: str
    draft_pick_order: int


# ------------------------------------------------------------
# Fact Ingestion Models
# ------------------------------------------------------------

class ManagerPickIngest(BaseModel):
    """Validated model for fact_manager_picks record."""
    model_config = ConfigDict(extra="ignore")

    manager_id: int
    gameweek_id: int
    player_id: int
    position: int


class PlayerPerformanceIngest(BaseModel):
    """Validated model for fact_player_performance record."""
    model_config = ConfigDict(extra="ignore")

    player_id: int
    gameweek_id: int
    total_points: int = 0
    goals_scored: int = 0
    assists: int = 0
    clean_sheets: int = 0
    goals_conceded: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    own_goals: int = 0
    penalties_saved: int = 0
    penalties_missed: int = 0
    saves: int = 0
    defcons: int = 0
    bonus: int = 0
    bps: int = 0
    minutes: int = 0


# ------------------------------------------------------------
# Pipeline Telemetry & Run History Audit Model
# ------------------------------------------------------------

class PipelineRunAudit(BaseModel):
    """Telemetry schema for execution history audit logging in Supabase & SQLite."""
    model_config = ConfigDict(extra="ignore")

    run_timestamp: str
    mode: str
    gameweek_id: int
    status: str
    duration_ms: int
    fixtures_count: int = 0
    managers_count: int = 0
    picks_count: int = 0
    perf_records_count: int = 0
    error_message: Optional[str] = None


# ------------------------------------------------------------
# Legacy & Raw Helper Models (Maintained for Backward Compatibility)
# ------------------------------------------------------------

class PlayerPerformanceRaw(BaseModel):
    """
    Validated model for raw individual player performance in a gameweek.
    Conforms to official FPL Draft API elements payload structure.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    player_id: int
    minutes: int = 0
    points: int = Field(default=0, alias="total_points")
    bonus: int = 0
    bps: int = 0
    expected_goals: float = 0.0
    expected_assists: float = 0.0

    # Optional match event metrics with safe defaults
    goals_scored: int = 0
    assists: int = 0
    clean_sheets: int = 0
    goals_conceded: int = 0
    saves: int = 0
    penalties_saved: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    own_goals: int = 0
    penalties_missed: int = 0
    influence: float = 0.0
    creativity: float = 0.0
    threat: float = 0.0
    ict_index: float = 0.0
    expected_goal_involvements: float = 0.0
    expected_goals_conceded: float = 0.0
    clearances_blocks_interceptions: int = 0
    recoveries: int = 0
    tackles: int = 0
    defensive_contribution: int = 0
    starts: int = 0
    in_dreamteam: bool = False

    # Lesson 18 Active Starter Invariant indicator
    has_played: bool = False

    @model_validator(mode="after")
    def enforce_lesson_18(self) -> "PlayerPerformanceRaw":
        """
        Enforce Lesson 18: A player is considered to have played already if and only if
        they recorded >0 minutes or have non-zero points recorded for the fixture.
        """
        self.has_played = bool((self.minutes > 0) or (self.points != 0))
        return self


class ManagerPickRaw(BaseModel):
    """
    Validated model for a manager squad pick in a given gameweek.
    """
    model_config = ConfigDict(extra="ignore")

    element: int
    position: int
    is_captain: bool = False
    is_vice_captain: bool = False
    multiplier: int = 1


class GameweekLiveStats(BaseModel):
    """
    Root validator for gameweek live API response.
    """
    model_config = ConfigDict(extra="allow")

    elements: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class PlayerDimensionRaw(BaseModel):
    """
    Validated model for dim_players dimension ingestion contract.
    Ensures canonical photo code mapping for official Premier League headshots.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    player_id: int
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    code: Optional[int] = None
    photo: Optional[str] = None
    team_id: Optional[int] = None
    team: Optional[str] = None
    position: Optional[str] = None

    @model_validator(mode="after")
    def resolve_photo_code(self) -> "PlayerDimensionRaw":
        """Ensure photo has a valid format (e.g. 154561.jpg or p154561.png)."""
        if not self.photo and self.code:
            self.photo = f"{self.code}.jpg"
        return self
