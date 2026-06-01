import os
import csv
import logging
import random
import pandas as pd
import requests
import time
from typing import List, Any, Optional

# Session for re-use
session = requests.Session()

# ------------------ API HELPERS ------------------ #
def fetch_data(url: str, retries: int = 3, delay: int = 2, timeout: int = 10) -> Optional[dict]:
    """
    Fetch JSON data from a given URL with retries and error handling.

    Args:
        url (str): The API endpoint to fetch.
        retries (int): Number of retry attempts if request fails.
        delay (int): Delay (seconds) between retries.
        timeout (int): Timeout (seconds) for each request.

    Returns:
        dict | None: JSON response if successful, else None.
    """
    # Add cache-busting headers to ensure fresh data
    headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                logging.error(f"❌ Invalid JSON from {url} (attempt {attempt}): {response.text[:200]}")
                return None
        except requests.RequestException as e:
            logging.warning(f"Attempt {attempt}/{retries} failed for {url}: {e}")
            if attempt < retries:
                backoff = delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                time.sleep(backoff)
            else:
                logging.error(f"❌ Failed to fetch data from {url} after {retries} attempts.")
                return None
    
# ------------------ FILE HELPERS ------------------ #
def save_csv(filename: str, headers: List[str], rows: List[List[Any]]):
    """
    Save tabular data to a CSV file.

    Args:
        filename (str): Path to save the CSV file.
        headers (list): Column headers.
        rows (list): Row data.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    try:
        with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            writer.writerows(rows)
        logging.info(f"✅ Saved CSV: {filename}")
    except Exception as e:
        logging.error(f"Failed to save CSV {filename}: {e}")
        raise

def load_csv(filename: str) -> pd.DataFrame:
    """
    Load a CSV file into a Pandas DataFrame.

    Args:
        filename (str): Path to CSV file.

    Returns:
        pd.DataFrame: Loaded data.
    """
    if not os.path.exists(filename):
        logging.error(f"CSV file not found: {filename}")
        return pd.DataFrame()
    return pd.read_csv(filename)

# ------------------ LEAGUE HELPERS ------------------ #