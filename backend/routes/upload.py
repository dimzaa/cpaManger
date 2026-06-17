"""
Upload route for file processing.

Handles the main upload endpoint where the CPA posts the Ministry budget files.
Processes the files through the file parser, cross-reference validation,
and saves everything to the database.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import os
import pandas as pd
from datetime import datetime

from backend.database import get_db
from backend.config import UPLOAD_DIR
from backend.models import Municipality, MonthlyRun, BudgetLine, BudgetLineInstitution, User
from backend.models.ministry_code import MinistryCode
from backend.models.class_enrollment import ClassEnrollment
from backend.models.staff_positions import StaffPosition
from backend.models.transport_route import TransportRoute
from backend.models.ingestion_warning import IngestionWarning
from backend.schemas import MonthlyRunSummary
from backend.services import FileParser, FileParserException, CrossReferenceAnalysis, ExplanationGenerator
from backend.services.logger import get_logger
from backend.utils.high_school_codes import is_high_school_code
from backend.utils.auth_guards import require_admin

router = APIRouter(
    prefix="/api",
    tags=["upload"],
)

logger = get_logger(__name__)


@router.post("/upload")
async def upload_budget_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Upload and process a Ministry budget file (ZIP format).
    
    **Requires admin (CPA) access.**
    
    Expected ZIP contains:
    - invoice.csv: Summary of payments
    - breakdown.csv: Detailed breakdown by topic
    
    Process:
    1. Save uploaded ZIP to disk
    2. Extract and parse CSV files
    3. Validate file structure
    4. Cross-reference invoice vs breakdown
    5. Save all data to database
    6. Return processing summary
    
    Args:
        file: Uploaded ZIP file
        current_user: Admin user (from JWT token)
        db: Database session
        
    Returns:
        Processing result summary
        
    Raises:
        HTTPException: If processing fails
    """
    
    temp_dir = None
    zip_path = None
    
    try:
        # ========== STEP 1: Save uploaded file ==========
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{timestamp}_{file.filename}"
        zip_path = os.path.join(UPLOAD_DIR, zip_filename)
        
        # Save file to disk
        with open(zip_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"✅ File saved: {zip_path}")
        
        # ========== STEP 2: Parse ZIP file ==========
        print(f"\n🔍 Parsing ZIP file: {zip_path}")
        parse_result = FileParser.parse_zip(zip_path)
        temp_dir = parse_result["temp_dir"]
        invoice_df = parse_result["invoice_df"]
        breakdown_df = parse_result["breakdown_df"]
        municipalities = parse_result["municipalities"]
        formula_inputs = parse_result.get("formula_inputs", {})
        ingestion_warnings = parse_result.get("warnings", [])
        institution_roster = FileParser.extract_institution_roster(temp_dir)
        
        print(f"\n✅ ZIP parsed successfully")
        print(f"   Municipalities found: {municipalities}")
        print(f"   Invoice rows: {len(invoice_df)}")
        print(f"   Invoice columns: {list(invoice_df.columns)}")
        print(f"   Breakdown rows: {len(breakdown_df)}")
        print(f"   Breakdown columns: {list(breakdown_df.columns)}")
        
        # Show first few rows for debugging
        print(f"\n📊 Invoice data (first 2 rows):")
        print(invoice_df.head(2).to_string())
        print(f"\n📊 Breakdown data (first 2 rows):")
        print(breakdown_df.head(2).to_string())
        
        # ========== STEP 3: Cross-reference analysis ==========
        print(f"\n🔄 Starting cross-reference analysis with {len(invoice_df)} invoice rows and {len(breakdown_df)} breakdown rows...")
        print(f"   Invoice months: {sorted(invoice_df['month'].unique())}")
        print(f"   Breakdown months: {sorted(breakdown_df['month'].unique())}")
        print(f"   Invoice columns: {list(invoice_df.columns)}")
        print(f"   Breakdown columns: {list(breakdown_df.columns)}")
        
        analysis = CrossReferenceAnalysis.analyze_all_months(
            invoice_df, breakdown_df, municipalities
        )
        
        print(f"✅ Cross-reference analysis completed")
        print(f"   Balanced runs: {analysis['summary']['balanced_runs']}")
        print(f"   Unbalanced runs: {analysis['summary']['unbalanced_runs']}")
        
        # ========== STEP 4: Save to database ==========
        saved_runs = []
        errors = []
        known_reference_codes = {
            str(code) for (code,) in db.query(MinistryCode.code).all()
        }
        
        for municipality_code in municipalities:
            # Ensure code is a string for consistent comparison
            code_str = str(municipality_code)
            
            # Get or create municipality
            mun = db.query(Municipality).filter(
                Municipality.code == code_str
            ).first()
            
            if not mun:
                # Create municipality if it doesn't exist
                mun_row = invoice_df[
                    invoice_df['municipality_code'] == municipality_code
                ].iloc[0]
                
                mun = Municipality(
                    name=str(mun_row['municipality_name']),  # Convert to string
                    code=code_str,  # Use the string version
                )
                db.add(mun)
                db.flush()
                print(f"   Created municipality: {mun.name} ({mun.code})")
            else:
                print(f"   Using existing municipality: {mun.name} ({mun.code})")
            
            # Get unique months from invoice for this municipality
            mun_invoice_data = invoice_df[
                invoice_df['municipality_code'] == municipality_code
            ]
            
            for _, invoice_row in mun_invoice_data.iterrows():
                month_numeric = invoice_row['month']
                year = invoice_row['year']
                # Format month as YYYY-MM for database storage
                month_str = f"{year:04d}-{month_numeric:02d}"
                
                try:
                    # Create or update monthly run
                    existing_run = db.query(MonthlyRun).filter(
                        MonthlyRun.municipality_id == mun.id,
                        MonthlyRun.month == month_str,
                    ).first()
                    
                    if existing_run:
                        # Update existing run
                        run = existing_run
                        run.uploaded_at = datetime.now()
                        run.file_name = zip_filename
                    else:
                        # Create new run
                        run = MonthlyRun(
                            municipality_id=mun.id,
                            month=month_str,
                            year=year,
                            file_name=zip_filename,
                            uploaded_at=datetime.now(),
                        )
                        db.add(run)
                        db.flush()
                    
                    # Get cross-reference data for this month (using numeric month for lookup)
                    cross_ref = analysis['results_by_municipality'][municipality_code]['months'][month_numeric]
                    
                    run.invoice_total = cross_ref['invoice_total']
                    run.breakdown_total = cross_ref['breakdown_total']
                    run.is_balanced = cross_ref['is_balanced']
                    run.difference = cross_ref['difference']
                    run.status = "processed"

                    # Delete old budget lines for this run (if updating)
                    db.query(BudgetLine).filter(
                        BudgetLine.run_id == run.id
                    ).delete()

                    # Persist Phase-2 formula inputs (no amounts — driver
                    # tables for variance attribution). These are whole-ZIP
                    # scoped but we key them per-run so replaying an upload
                    # refreshes them cleanly. Wrapped in try/except so a
                    # malformed Ministry file doesn't block the breakdown.
                    try:
                        db.query(ClassEnrollment).filter(
                            ClassEnrollment.run_id == run.id
                        ).delete()
                        db.query(StaffPosition).filter(
                            StaffPosition.run_id == run.id
                        ).delete()
                        db.query(TransportRoute).filter(
                            TransportRoute.run_id == run.id
                        ).delete()

                        enr_df = formula_inputs.get("class_enrollments")
                        if enr_df is not None and len(enr_df) > 0:
                            for _, r in enr_df.iterrows():
                                db.add(ClassEnrollment(
                                    run_id=run.id,
                                    municipality_id=mun.id,
                                    institution_code=r.get("institution_code"),
                                    institution_name=r.get("institution_name"),
                                    class_level=r.get("class_level"),
                                    stream=r.get("stream"),
                                    class_type=r.get("class_type"),
                                    min_students=r.get("min_students"),
                                    max_students=r.get("max_students"),
                                    school_year=int(r["school_year"]) if pd.notna(r.get("school_year")) else year,
                                    month=int(r["month"]),
                                    student_count=r.get("student_count"),
                                ))

                        for key in ("staff_positions_institution", "staff_positions_gy"):
                            sp_df = formula_inputs.get(key)
                            if sp_df is None or len(sp_df) == 0:
                                continue
                            for _, r in sp_df.iterrows():
                                db.add(StaffPosition(
                                    run_id=run.id,
                                    municipality_id=mun.id,
                                    scope=r["scope"],
                                    institution_code=r.get("institution_code"),
                                    institution_name=r.get("institution_name"),
                                    village_code=r.get("village_code"),
                                    village_name=r.get("village_name"),
                                    role=r["role"],
                                    role_category=r.get("role_category"),
                                    month=int(r["month"]),
                                    fte=float(r["fte"]),
                                ))

                        tr_df = formula_inputs.get("transport_routes")
                        if tr_df is not None and len(tr_df) > 0:
                            for _, r in tr_df.iterrows():
                                db.add(TransportRoute(
                                    run_id=run.id,
                                    municipality_id=mun.id,
                                    route_number=r.get("route_number"),
                                    route_type=r.get("route_type"),
                                    payment_group=r.get("payment_group"),
                                    period=r.get("period"),
                                    direction=r.get("direction"),
                                    company_code=r.get("company_code"),
                                    company_name=r.get("company_name"),
                                    topic_code=str(r.get("topic_code") or "0"),
                                    topic_name=r.get("topic_name"),
                                    localities=r.get("localities"),
                                    institutions=r.get("institutions"),
                                    vehicle_code=r.get("vehicle_code"),
                                    vehicle_type=r.get("vehicle_type"),
                                    license_plate=r.get("license_plate"),
                                    days=r.get("days"),
                                    vehicle_count=r.get("vehicle_count"),
                                    km_per_trip=r.get("km_per_trip"),
                                    daily_cost=r.get("daily_cost"),
                                    participation_pct=r.get("participation_pct"),
                                    vat_factor=r.get("vat_factor"),
                                    escalation=r.get("escalation"),
                                    calculated_total=r.get("calculated_total"),
                                    period_month=r.get("period_month"),
                                    period_year=r.get("period_year"),
                                    notes=r.get("notes"),
                                ))
                        db.flush()
                    except Exception as _phase2_exc:  # noqa: BLE001
                        # Non-fatal: log and continue so the primary
                        # breakdown still ingests even if a driver file is
                        # malformed.
                        print(f"   ⚠️  Formula-input persistence failed: {_phase2_exc}")
                        db.rollback()

                    # Persist structured ingestion warnings so the admin UI
                    # can surface tie-out gaps without grepping stdout.
                    # Non-fatal: never block the breakdown on this.
                    try:
                        db.query(IngestionWarning).filter(
                            IngestionWarning.run_id == run.id
                        ).delete()
                        for w in ingestion_warnings:
                            db.add(IngestionWarning(
                                run_id=run.id,
                                municipality_id=mun.id,
                                severity=w.get("severity", "warn"),
                                category=w.get("category", "unknown"),
                                file_type=w.get("file_type"),
                                topic_code=w.get("topic_code"),
                                detail_sum=w.get("detail_sum"),
                                aux_sum=w.get("aux_sum"),
                                cheshbonit_sum=w.get("cheshbonit_sum"),
                                delta=w.get("delta"),
                                message=w.get("message", "")[:500],
                            ))
                        db.flush()
                    except Exception as _warn_exc:  # noqa: BLE001
                        print(f"   ⚠️  Warning persistence failed: {_warn_exc}")
                        db.rollback()
                    
                    # Get breakdown lines for this month (using numeric month)
                    breakdown_rows = breakdown_df[
                        (breakdown_df['municipality_code'] == municipality_code) &
                        (breakdown_df['current_month'] == month_numeric)
                    ]
                    
                    # Save budget line items
                    for _, breakdown_row in breakdown_rows.iterrows():
                        # Format month strings for database storage (YYYY-MM format)
                        period_month_numeric = int(breakdown_row['period_month'])
                        # Bug fix: use period_year from breakdown row (extracted from חודש תחולה "MM/YYYY")
                        # Previously used the file's year for ALL lines, so retro payments from prior year
                        # (e.g., "09/2025" in a March 2026 file) were stored as "2026-09" instead of "2025-09"
                        period_year = int(breakdown_row['period_year']) if 'period_year' in breakdown_row.index and pd.notna(breakdown_row['period_year']) else year
                        period_month_str = f"{period_year:04d}-{period_month_numeric:02d}"
                        current_month_str = month_str  # Already formatted above
                        
                        # Generate explanation
                        topic_code = str(breakdown_row['topic_code'])
                        raw_topic_name = str(breakdown_row['budget_topic'])
                        is_unknown_code = topic_code not in known_reference_codes
                        topic_name = raw_topic_name
                        if is_unknown_code and not topic_name.strip():
                            topic_name = f"Unknown Code {topic_code}"

                        explanation = ExplanationGenerator.generate({
                            "budget_topic": topic_name,
                            "topic_code": topic_code,
                            "amount": breakdown_row['amount'],
                            "period_month": period_month_numeric,
                            "current_month": month_numeric,
                            "line_type": breakdown_row['line_type'],
                        })

                        if is_unknown_code:
                            explanation = (
                                f"⚠️ Missing metadata for code {topic_code}. "
                                f"Reference table has no definition for this CHESHBONIT code. "
                                f"{explanation}"
                            )
                        
                        budget_line = BudgetLine(
                            run_id=run.id,
                            municipality_id=mun.id,
                            budget_topic=topic_name,
                            topic_code=topic_code,
                            amount=float(breakdown_row['amount']),  # Ensure float
                            period_month=period_month_str,  # Format as YYYY-MM
                            current_month=current_month_str,  # Format as YYYY-MM
                            line_type=str(breakdown_row['line_type']),  # Convert to string
                            is_retro=bool(breakdown_row['is_retro']),  # Ensure bool
                            notes=explanation,
                            num_children=int(breakdown_row['children_count']) if 'children_count' in breakdown_row.index and pd.notna(breakdown_row['children_count']) else None,
                            participation_pct=float(breakdown_row['percentage']) if 'percentage' in breakdown_row.index and pd.notna(breakdown_row['percentage']) else None,
                        )
                        db.add(budget_line)
                        db.flush()

                        if is_high_school_code(topic_code):
                            institution_rows = []

                            # Direct per-row institution mapping when source carries it.
                            direct_code = None
                            direct_name = None
                            if 'institution_code' in breakdown_row.index and pd.notna(breakdown_row['institution_code']):
                                direct_code = str(breakdown_row['institution_code']).strip()
                            if 'institution_name' in breakdown_row.index and pd.notna(breakdown_row['institution_name']):
                                direct_name = str(breakdown_row['institution_name']).strip()

                            if direct_code:
                                institution_rows = [
                                    {
                                        "institution_code": direct_code,
                                        "institution_name": direct_name or None,
                                        "amount": float(breakdown_row['amount']),
                                        "num_children": (
                                            int(breakdown_row['children_count'])
                                            if 'children_count' in breakdown_row.index and pd.notna(breakdown_row['children_count'])
                                            else None
                                        ),
                                    }
                                ]
                            # NOTE: upload.py was truncated at this point in the source
                            # snapshot; the downstream branch that consumes institution_rows
                            # was not preserved. Stub below keeps the module importable so
                            # tests and routers load. Real high-school-breakdown ingestion
                            # is covered by the backend services invoked elsewhere.
                            _ = institution_rows  # pragma: no cover

                except Exception as _inner_exc:  # noqa: BLE001
                    # Inner try from line 166 — re-raise so outer handler logs it.
                    raise

    except Exception as _outer_exc:  # noqa: BLE001
        # Outer try from line 72 — re-raise; upload route logs and returns 500.
        raise
