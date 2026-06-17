"""
Debug script to analyze Ministry budget CSV files.

Usage:
    python debug_csv.py path/to/file.zip

Shows:
- Filenames in ZIP
- Column names in each CSV
- Sample data from each file
- Identifies if columns match expected format
"""

import sys
import zipfile
import pandas as pd
import tempfile
import os
from pathlib import Path

def analyze_zip(zip_path):
    """Analyze and show contents of a budget ZIP file."""
    
    print("=" * 70)
    print(f"📦 Analyzing ZIP: {zip_path}")
    print("=" * 70)
    
    try:
        # Extract ZIP
        temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # List files
        csv_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.csv'):
                    csv_files.append(os.path.join(root, file))
        
        print(f"\n📄 CSV Files Found ({len(csv_files)}):")
        for i, f in enumerate(csv_files, 1):
            filename = Path(f).name
            file_size = os.path.getsize(f)
            print(f"   {i}. {filename} ({file_size:,} bytes)")
        
        # Analyze each file
        for csv_file in csv_files:
            filename = Path(csv_file).name
            print(f"\n" + "=" * 70)
            print(f"🔍 File: {filename}")
            print("=" * 70)
            
            try:
                # Try UTF-8-sig (with BOM)
                df = pd.read_csv(csv_file, encoding='utf-8-sig')
                print(f"✓ Encoding: UTF-8-sig")
            except:
                try:
                    # Fallback to UTF-8
                    df = pd.read_csv(csv_file, encoding='utf-8')
                    print(f"✓ Encoding: UTF-8")
                except:
                    try:
                        # Try latin-1
                        df = pd.read_csv(csv_file, encoding='latin-1')
                        print(f"✓ Encoding: Latin-1")
                    except Exception as e:
                        print(f"❌ Could not read file: {e}")
                        continue
            
            # Show structure
            print(f"\nStructure:")
            print(f"  Rows: {len(df)}")
            print(f"  Columns: {len(df.columns)}")
            
            # Show column names
            print(f"\n📋 Columns:")
            for i, col in enumerate(df.columns, 1):
                print(f"   {i}. {col}")
            
            # Show first 3 rows
            print(f"\n📊 First 3 Rows:")
            print(df.head(3).to_string())
            
            # Show data types
            print(f"\n📈 Data Types:")
            for col, dtype in df.dtypes.items():
                print(f"   {col}: {dtype}")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        
        print("\n" + "=" * 70)
        print("✅ Analysis complete!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Check if column names match expected format")
        print("2. If not, paste the column names here so we can update the parser")
        print("3. Re-upload the file and check backend console for results")
        
    except zipfile.BadZipFile:
        print(f"❌ ERROR: {zip_path} is not a valid ZIP file")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_csv.py path/to/file.zip")
        sys.exit(1)
    
    zip_path = sys.argv[1]
    if not os.path.exists(zip_path):
        print(f"❌ File not found: {zip_path}")
        sys.exit(1)
    
    analyze_zip(zip_path)
