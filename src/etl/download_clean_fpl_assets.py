import os
import urllib.request
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB_PUBLIC_DIR = os.path.join(os.path.dirname(BASE_DIR), "FPL_web", "public")
BADGES_DIR = os.path.join(WEB_PUBLIC_DIR, "badges")
KITS_DIR = os.path.join(WEB_PUBLIC_DIR, "kits")

os.makedirs(BADGES_DIR, exist_ok=True)
os.makedirs(KITS_DIR, exist_ok=True)

print(f"Target Badges Dir: {BADGES_DIR}")
print(f"Target Kits Dir: {KITS_DIR}")

# Fetch official FPL team data
url = "https://draft.premierleague.com/api/bootstrap-static"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))

teams = data["teams"]
print(f"Found {len(teams)} teams in FPL API")

# Name mappings for consistency
NAME_MAP = {
    "Man City": "Manchester City",
    "Man Utd": "Manchester United",
    "Nott'm Forest": "Nottingham Forest",
    "Spurs": "Tottenham",
    "Wolves": "Wolverhampton",
}

for t in teams:
    code = t["code"]
    short_name = t["short_name"]
    name = NAME_MAP.get(t["name"], t["name"])

    print(f"Downloading assets for {name} ({short_name}), code={code}...")

    # 1. Download Badge (100x100 PNG)
    badge_url = f"https://resources.premierleague.com/premierleague/badges/100/t{code}.png"
    badge_path_name = os.path.join(BADGES_DIR, f"{name}.png")
    badge_path_short = os.path.join(BADGES_DIR, f"{short_name}.png")

    try:
        urllib.request.urlretrieve(badge_url, badge_path_name)
        urllib.request.urlretrieve(badge_url, badge_path_short)
        print(f"  [OK] Saved badge: {name}.png & {short_name}.png")
    except Exception as e:
        print(f"  [FAIL] Failed to download badge for {name}: {e}")

    # 2. Download Outfield Kit Shirt (Standardized 66x87 Transparent PNG)
    kit_url = f"https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_{code}-66.png"
    kit_path = os.path.join(KITS_DIR, f"{short_name}.png")

    try:
        urllib.request.urlretrieve(kit_url, kit_path)
        print(f"  [OK] Saved kit: {short_name}.png")
    except Exception as e:
        print(f"  [FAIL] Failed to download kit for {short_name}: {e}")

    # 3. Download Goalkeeper Kit Shirt
    gkp_kit_url = f"https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_{code}_1-66.png"
    gkp_kit_path = os.path.join(KITS_DIR, f"{short_name}_1.png")

    try:
        urllib.request.urlretrieve(gkp_kit_url, gkp_kit_path)
        print(f"  [OK] Saved GKP kit: {short_name}_1.png")
    except Exception as e:
        print(f"  [FAIL] Failed to download GKP kit for {short_name}: {e}")

print("All official FPL badges & kits downloaded cleanly!")
