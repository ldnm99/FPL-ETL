import pandas as pd
import io
import os
import logging
from supabase import create_client, Client
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# --------------------------
# Supabase Client Setup
# --------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("❌ Missing required environment variables")
    logging.error("   Please set SUPABASE_URL and SUPABASE_SERVICE_KEY")
    logging.error("   Example: export SUPABASE_URL='https://your-project.supabase.co'")
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --------------------------
# Upload Helpers
# --------------------------
def upload_csv(file_path, bucket="data"):
    try:
        df = pd.read_csv(file_path)
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)

        res = supabase.storage.from_(bucket).upload(
            path=os.path.basename(file_path),
            file=buffer.getvalue().encode("utf-8"),  # convert string -> bytes
            file_options={"content-type": "text/csv", "upsert": "true"}
        )

        logging.info(f"✅ Uploaded CSV: {file_path}")
        return res
    except Exception as e:
        logging.error(f"❌ Error uploading CSV {file_path}: {e}")


def upload_parquet(file_path, bucket="data"):
    try:
        df = pd.read_parquet(file_path)
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)

        res = supabase.storage.from_(bucket).upload(
            path=os.path.basename(file_path),
            file=buffer.read(),
            file_options={"content-type": "application/octet-stream", "upsert": "true"}
        )

        logging.info(f"✅ Uploaded Parquet: {file_path}")
        return res
    except Exception as e:
        logging.error(f"❌ Error uploading Parquet {file_path}: {e}")


# --------------------------
# Main function for external calls
# --------------------------
def main():
    data_dir = "Data"

    # Upload main files
    upload_csv(os.path.join(data_dir, "league_standings.csv"))
    upload_csv(os.path.join(data_dir, "players_data.csv"))
    upload_parquet(os.path.join(data_dir, "gw_data.parquet"))

    # Upload individual gameweek parquet files
    gw_folder = os.path.join(data_dir, "gameweeks_parquet")
    if os.path.exists(gw_folder):
        for f in os.listdir(gw_folder):
            if f.endswith(".parquet"):
                upload_parquet(os.path.join(gw_folder, f))

    # Write last updated timestamp
    with open("last_updated.txt", "w") as f:
        f.write(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

    logging.info("📁 last_updated.txt updated.")
    logging.info("🎉 All uploads complete.")


# --------------------------
# Allow standalone execution
# --------------------------
if __name__ == "__main__":
    main()
