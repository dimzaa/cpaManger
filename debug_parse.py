"""
Debug: Check what columns are in the parsed DataFrames
"""
import sys
sys.path.insert(0, '/Users/zahal/OneDrive/cpa')

from backend.services.file_parser import FileParser

zip_file = 'uploads/20260402_163222_Horada.zip'

print(f"Parsing {zip_file}...")
try:
    result = FileParser.parse_zip(zip_file)
    invoice_df = result['invoice_df']
    breakdown_df = result['breakdown_df']
    
    print(f"\n📊 Invoice DataFrame:")
    print(f"   Shape: {invoice_df.shape}")
    print(f"   Columns: {list(invoice_df.columns)}")
    print(f"   Data types:")
    for col, dtype in invoice_df.dtypes.items():
        print(f"      {col}: {dtype}")
    print(f"\n   First row:")
    print(invoice_df.head(1).to_string())
    
    print(f"\n📊 Breakdown DataFrame:")
    print(f"   Shape: {breakdown_df.shape}")
    print(f"   Columns: {list(breakdown_df.columns)}")
    print(f"   Data types:")
    for col, dtype in breakdown_df.dtypes.items():
        print(f"      {col}: {dtype}")
    print(f"\n   First row:")
    print(breakdown_df.head(1).to_string())
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
