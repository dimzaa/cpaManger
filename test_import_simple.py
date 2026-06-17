#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

print("Step 1: Importing router directly...")
try:
    from backend.routes.suggestions import router
    print("✅ Router imported successfully")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
