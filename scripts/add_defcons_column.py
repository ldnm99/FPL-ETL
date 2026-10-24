import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=r"c:\Users\lourencomarvao\Desktop\Blaziken\FPL-ETL\.env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation"
}

# Update row with saves = defcons_val (storing defensive contribution count)
test_payload = {
    "player_id": 12,
    "gameweek_id": 1,
    "saves": 7
}

res = requests.post(f"{url}/rest/v1/fact_player_performance", headers=headers, json=test_payload)
print("Upsert status:", res.status_code, res.json())

