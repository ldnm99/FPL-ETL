"""Quick script to run ONLY the Gold layer (assumes Bronze and Silver are complete)"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.etl import gold
from src.config import config

print("🥇 Running ONLY Gold layer...")
print(f"   Using data from: {config.SILVER_DIR}")
print("")

try:
    # Run dimensional model creation
    print("Creating dimensional model...")
    gold.main()
    
    print("")
    print("✅ Gold layer complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
