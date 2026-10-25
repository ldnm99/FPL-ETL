"""
Resilient HTTP and Supabase Client Module for FPL-ETL.
Provides connection pooling, exponential backoff retries, and Supabase client initialization.
"""
import os
import sys
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Setup Logging
logger = logging.getLogger("fpl_sync.client")

# Constants
FPL_DRAFT_BASE_URL = "https://draft.premierleague.com/api"
DEFAULT_LEAGUE_ID = os.getenv("FPL_LEAGUE_ID", "24636")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")


def create_resilient_session() -> requests.Session:
    """
    Creates a requests.Session with connection pooling and exponential backoff retry strategy.
    Retries on status codes 429 (rate-limit) and 5xx (server errors).
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


HTTP_SESSION = create_resilient_session()


def get_supabase_client():
    """Initialize and return Supabase Client instance."""
    try:
        from supabase import create_client, Client
    except ImportError:
        logger.error("❌ 'supabase' package is missing. Install with: pip install supabase")
        sys.exit(1)

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment variables.")
        sys.exit(1)

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_json(endpoint: str) -> Dict[str, Any]:
    """Fetch JSON payload from FPL Draft API with connection pooling & error handling."""
    url = f"{FPL_DRAFT_BASE_URL}{endpoint}"
    try:
        res = HTTP_SESSION.get(url, timeout=15)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.warning(f"⚠️ Failed to fetch {url}: {e}")
        return {}
