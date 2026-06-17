"""
Preview helper for monthly memo HTML block.

Usage:
  python -m backend.utils.preview_monthly_memo --municipality-id 4 --month 2026-03
"""

import argparse
from pathlib import Path

from backend.database import SessionLocal
from backend.services.monthly_memo_engine import (
    build_monthly_memo_data_bundle,
    generate_monthly_memo,
)


def main():
    parser = argparse.ArgumentParser(description="Preview monthly memo HTML block")
    parser.add_argument("--municipality-id", type=int, required=True)
    parser.add_argument("--month", type=str, required=True, help="YYYY-MM")
    parser.add_argument(
        "--out",
        type=str,
        default="tmp/monthly_memo_preview.html",
        help="Output file path",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        data = build_monthly_memo_data_bundle(db, args.municipality_id, args.month)
        result = generate_monthly_memo(args.month, data)
    finally:
        db.close()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Keep output self-contained while making browser preview convenient.
    preview_doc = f"""<!doctype html>
<html lang=\"he\" dir=\"rtl\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Monthly Memo Preview</title>
  </head>
  <body style=\"background:#f3f4f6;padding:24px;\">{result.html}</body>
</html>"""

    out_path.write_text(preview_doc, encoding="utf-8")
    print(f"Preview written to: {out_path}")


if __name__ == "__main__":
    main()
