"""
Ministry Integration API routes.

/api/ministry/codes           — code lookup (search, category filter)
/api/ministry/policy-changes  — policy change alerts
/api/ministry/circulars       — circular letters
"""
import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.ministry_code import MinistryCode
from backend.models.ministry_code_view import MinistryCodeView
from backend.models.policy_change import PolicyChange
from backend.models.circular_letter import CircularLetter
from backend.models.in_app_notification import InAppNotification
from backend.models.municipality import Municipality
from backend.models.budget_line import BudgetLine
from backend.models.user import User
from backend.utils.auth_guards import require_login, require_admin

router = APIRouter(tags=["ministry"])


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

class PolicyChangeCreate(BaseModel):
    title: str
    description: Optional[str] = None
    change_type: str = "formula"
    affected_codes: list = []
    affected_municipalities: str = "all"
    effective_date: Optional[date] = None
    announced_date: Optional[date] = None
    source: Optional[str] = None
    impact_description: Optional[str] = None
    action_required: Optional[str] = None
    action_deadline: Optional[date] = None
    severity: str = "medium"


class CircularCreate(BaseModel):
    circular_number: Optional[str] = None
    title: str
    subject: Optional[str] = None
    full_content: Optional[str] = None
    published_date: Optional[date] = None
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    category: str = "כללי"
    affected_codes: list = []
    affected_municipality_types: str = "all"
    importance: str = "routine"
    action_required: Optional[str] = None
    action_deadline: Optional[date] = None
    attachment_url: Optional[str] = None
    tags: list = []


class CodeUpdate(BaseModel):
    name_short: Optional[str] = None
    name_full: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    formula: Optional[str] = None
    participation_percent: Optional[float] = None
    booklet_page: Optional[int] = None
    purple_book_column: Optional[str] = None
    booklet_section: Optional[str] = None
    action_required: Optional[str] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _code_to_dict(code: MinistryCode, include_full: bool = False) -> dict:
    missing_fields = []
    if code.participation_percent is None:
        missing_fields.append("participation_percent")
    if not code.category:
        missing_fields.append("category")
    if not code.purple_book_column:
        missing_fields.append("purple_book_column")

    base = {
        "id": code.id,
        "code": code.code,
        "name_short": code.name_short,
        "name_full": code.name_full,
        "category": code.category,
        "description": code.description,
        "formula": code.formula,
        "participation_percent": code.participation_percent,
        "constant_divisor": code.constant_divisor,
        "payment_type": code.payment_type,
        "applies_to": code.applies_to,
        "booklet_page": code.booklet_page,
        "purple_book_column": code.purple_book_column,
        "booklet_section": code.booklet_section,
        "is_deduction": code.is_deduction,
        "related_codes": code.get_related_codes(),
        "keywords": code.keywords,
        "is_active": code.is_active,
        "metadata_status": "missing_metadata" if missing_fields else "complete",
        "missing_fields": missing_fields,
        "source": "reference",
    }
    if include_full:
        base["sub_topics"] = code.get_sub_topics()
        base["change_triggers"] = code.get_change_triggers()
    return base


def _policy_to_dict(pc: PolicyChange, municipality_id: Optional[int] = None) -> dict:
    d = {
        "id": pc.id,
        "title": pc.title,
        "description": pc.description,
        "change_type": pc.change_type,
        "affected_codes": pc.get_affected_codes(),
        "effective_date": pc.effective_date.isoformat() if pc.effective_date else None,
        "announced_date": pc.announced_date.isoformat() if pc.announced_date else None,
        "source": pc.source,
        "impact_description": pc.impact_description,
        "action_required": pc.action_required,
        "action_deadline": pc.action_deadline.isoformat() if pc.action_deadline else None,
        "severity": pc.severity,
        "created_at": pc.created_at.isoformat() if pc.created_at else None,
        "acknowledged_count": len(pc.get_acknowledged_by()),
    }
    if municipality_id is not None:
        d["is_acknowledged"] = pc.is_acknowledged_by_municipality(municipality_id)
    return d


def _circular_to_dict(cl: CircularLetter, user_id: Optional[int] = None, brief: bool = True) -> dict:
    d = {
        "id": cl.id,
        "circular_number": cl.circular_number,
        "title": cl.title,
        "subject": cl.subject,
        "published_date": cl.published_date.isoformat() if cl.published_date else None,
        "effective_date": cl.effective_date.isoformat() if cl.effective_date else None,
        "expiry_date": cl.expiry_date.isoformat() if cl.expiry_date else None,
        "category": cl.category,
        "affected_codes": cl.get_affected_codes(),
        "importance": cl.importance,
        "action_required": cl.action_required,
        "action_deadline": cl.action_deadline.isoformat() if cl.action_deadline else None,
        "tags": cl.get_tags(),
        "read_count": len(cl.get_read_by()),
        "created_at": cl.created_at.isoformat() if cl.created_at else None,
    }
    if user_id is not None:
        d["is_read"] = cl.is_read_by_user(user_id)
    if not brief:
        d["full_content"] = cl.full_content
        d["attachment_url"] = cl.attachment_url
    return d


def _notify_municipalities_policy_change(pc: PolicyChange, db: Session):
    """Create in-app notifications for municipalities when a new policy change is created."""
    municipalities = db.query(Municipality).filter(Municipality.is_active == True).all()
    severity_prefix = {"high": "🔴", "medium": "🟡", "low": "🔵", "info": "ℹ️"}.get(pc.severity, "🔔")

    for muni in municipalities:
        notif = InAppNotification(
            municipality_id=muni.id,
            type="budget_updated",
            title=f"{severity_prefix} שינוי מדיניות: {pc.title}",
            message=pc.impact_description or pc.description,
            action_url="/portal/ministry?tab=policy",
            action_text="ראה שינוי מדיניות",
        )
        db.add(notif)
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# CODES ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/ministry/codes")
def list_codes(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    is_deduction: Optional[bool] = Query(None),
    applies_to: Optional[str] = Query(None),
    include_unknown: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Search and filter ministry budget codes."""
    q = db.query(MinistryCode).filter(MinistryCode.is_active == True)

    if search:
        s = f"%{search}%"
        q = q.filter(
            MinistryCode.code.ilike(s)
            | MinistryCode.name_full.ilike(s)
            | MinistryCode.name_short.ilike(s)
            | MinistryCode.description.ilike(s)
            | MinistryCode.keywords.ilike(s)
        )
    if category:
        q = q.filter(MinistryCode.category == category)
    if is_deduction is not None:
        q = q.filter(MinistryCode.is_deduction == is_deduction)
    if applies_to:
        q = q.filter(MinistryCode.applies_to == applies_to)

    known_codes = q.all()
    known_payload = [_code_to_dict(c) for c in known_codes]

    if not include_unknown:
        return sorted(known_payload, key=lambda c: (0, int(c["code"])) if str(c["code"]).isdigit() else (1, str(c["code"])))

    known_codes_set = {c["code"] for c in known_payload}
    unknown_rows = (
        db.query(
            BudgetLine.topic_code.label("topic_code"),
            func.max(BudgetLine.budget_topic).label("sample_topic"),
            func.count(BudgetLine.id).label("occurrences"),
        )
        .group_by(BudgetLine.topic_code)
        .all()
    )

    unknown_payload = []
    for row in unknown_rows:
        topic_code = str(row.topic_code)
        if topic_code in known_codes_set:
            continue

        sample_topic = row.sample_topic or "Unknown Code"
        if search:
            s = search.lower()
            if s not in topic_code.lower() and s not in str(sample_topic).lower():
                continue

        unknown_payload.append({
            "id": None,
            "code": topic_code,
            "name_short": "Unknown Code",
            "name_full": f"Missing metadata for CHESHBONIT code {topic_code}",
            "category": "Missing Metadata",
            "description": f"Detected in CHESHBONIT upload as '{sample_topic}' but missing from reference table.",
            "formula": None,
            "participation_percent": None,
            "constant_divisor": None,
            "payment_type": "unknown",
            "applies_to": "all",
            "booklet_page": None,
            "purple_book_column": None,
            "booklet_section": None,
            "is_deduction": False,
            "related_codes": [],
            "keywords": None,
            "is_active": True,
            "metadata_status": "missing_metadata",
            "missing_fields": ["participation_percent", "category", "purple_book_column"],
            "source": "cheshbonit",
            "observed_topic": sample_topic,
            "occurrences": int(row.occurrences or 0),
        })

    combined = known_payload + unknown_payload
    return sorted(combined, key=lambda c: (0, int(c["code"])) if str(c["code"]).isdigit() else (1, str(c["code"])))


@router.get("/api/ministry/codes/{code_str}")
def get_code(
    code_str: str,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Full details for a single code, including related code details and recent alerts."""
    mc = db.query(MinistryCode).filter(MinistryCode.code == code_str, MinistryCode.is_active == True).first()
    if not mc:
        raise HTTPException(status_code=404, detail="Code not found")

    # Track view
    if user_id:
        view = MinistryCodeView(code_id=mc.id, user_id=user_id)
        db.add(view)
        db.commit()

    result = _code_to_dict(mc, include_full=True)

    # Add related code details
    related_details = []
    for rc in mc.get_related_codes():
        rel = db.query(MinistryCode).filter(MinistryCode.code == rc).first()
        if rel:
            related_details.append({"code": rel.code, "name": rel.name_short})
    result["related_codes_details"] = related_details

    # Recent policy changes mentioning this code
    recent_pcs = (
        db.query(PolicyChange)
        .filter(PolicyChange.affected_codes.ilike(f'%"{code_str}"%'))
        .order_by(PolicyChange.created_at.desc())
        .limit(3)
        .all()
    )
    result["recent_policy_changes"] = [_policy_to_dict(p) for p in recent_pcs]

    # Recent circulars mentioning this code
    recent_cls = (
        db.query(CircularLetter)
        .filter(CircularLetter.affected_codes.ilike(f'%"{code_str}"%'))
        .order_by(CircularLetter.created_at.desc())
        .limit(3)
        .all()
    )
    result["recent_circulars"] = [_circular_to_dict(cl) for cl in recent_cls]

    return result


@router.get("/api/ministry/categories")
def list_categories(db: Session = Depends(get_db)):
    """All categories with code count."""
    rows = (
        db.query(MinistryCode.category, func.count(MinistryCode.id).label("count"))
        .filter(MinistryCode.is_active == True)
        .group_by(MinistryCode.category)
        .order_by(func.count(MinistryCode.id).desc())
        .all()
    )
    return [{"category": r.category, "count": r.count} for r in rows]


@router.put("/api/ministry/codes/{code_id}")
def update_code(
    code_id: int,
    payload: CodeUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin — update a code's fields."""
    mc = db.query(MinistryCode).filter(MinistryCode.id == code_id).first()
    if not mc:
        raise HTTPException(status_code=404, detail="Code not found")

    for field, value in payload.dict(exclude_none=True).items():
        setattr(mc, field, value)
    mc.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(mc)
    return _code_to_dict(mc, include_full=True)


# ─────────────────────────────────────────────────────────────────────────────
# POLICY CHANGES ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/ministry/policy-changes")
def list_policy_changes(
    municipality_id: Optional[int] = Query(None),
    unacknowledged_only: bool = Query(False),
    severity: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """List policy changes, optionally filtered. Returns acknowledge flag per municipality."""
    q = db.query(PolicyChange).order_by(PolicyChange.created_at.desc())

    if severity:
        q = q.filter(PolicyChange.severity == severity)
    if from_date:
        q = q.filter(PolicyChange.created_at >= from_date)

    changes = q.all()

    # Filter unacknowledged if requested
    result = []
    for pc in changes:
        d = _policy_to_dict(pc, municipality_id=municipality_id)
        if unacknowledged_only and municipality_id and d.get("is_acknowledged"):
            continue
        result.append(d)

    return result


@router.post("/api/ministry/policy-changes")
def create_policy_change(
    payload: PolicyChangeCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin — create a new policy change alert and notify municipalities."""
    pc = PolicyChange(
        title=payload.title,
        description=payload.description,
        change_type=payload.change_type,
        affected_codes=json.dumps(payload.affected_codes, ensure_ascii=False),
        affected_municipalities=payload.affected_municipalities,
        effective_date=payload.effective_date,
        announced_date=payload.announced_date or date.today(),
        source=payload.source,
        impact_description=payload.impact_description,
        action_required=payload.action_required,
        action_deadline=payload.action_deadline,
        severity=payload.severity,
        is_acknowledged_by="[]",
        created_by=current_user.id,
    )
    db.add(pc)
    db.commit()
    db.refresh(pc)

    # Notify all municipalities
    try:
        _notify_municipalities_policy_change(pc, db)
    except Exception as e:
        print(f"⚠️  Could not create policy change notifications: {e}")

    return _policy_to_dict(pc)


@router.get("/api/ministry/policy-changes/unread-count/{municipality_id}")
def policy_unread_count(municipality_id: int, db: Session = Depends(get_db)):
    """Count unacknowledged policy changes for a municipality."""
    all_changes = db.query(PolicyChange).all()
    count = sum(1 for pc in all_changes if not pc.is_acknowledged_by_municipality(municipality_id))
    return {"count": count}


@router.patch("/api/ministry/policy-changes/{change_id}/acknowledge")
def acknowledge_policy_change(
    change_id: int,
    municipality_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Municipality acknowledges reading a policy change."""
    pc = db.query(PolicyChange).filter(PolicyChange.id == change_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Policy change not found")

    pc.add_acknowledgement(municipality_id)
    db.commit()
    return {"ok": True, "acknowledged_by_count": len(pc.get_acknowledged_by())}


@router.delete("/api/ministry/policy-changes/{change_id}")
def delete_policy_change(
    change_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin — delete a policy change."""
    pc = db.query(PolicyChange).filter(PolicyChange.id == change_id).first()
    if not pc:
        raise HTTPException(status_code=404, detail="Policy change not found")
    db.delete(pc)
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# CIRCULAR LETTERS ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/ministry/circulars")
def list_circulars(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    importance: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """List circulars with search + filters."""
    q = db.query(CircularLetter).order_by(CircularLetter.published_date.desc().nullslast(), CircularLetter.created_at.desc())

    if search:
        s = f"%{search}%"
        q = q.filter(
            CircularLetter.title.ilike(s)
            | CircularLetter.subject.ilike(s)
            | CircularLetter.circular_number.ilike(s)
            | CircularLetter.tags.ilike(s)
        )
    if category:
        q = q.filter(CircularLetter.category == category)
    if importance:
        q = q.filter(CircularLetter.importance == importance)
    if year:
        q = q.filter(func.strftime("%Y", CircularLetter.published_date) == str(year))

    circulars = q.all()
    return [_circular_to_dict(cl, user_id=user_id) for cl in circulars]


@router.get("/api/ministry/circulars/unread-count/{user_id_param}")
def circular_unread_count(user_id_param: int, db: Session = Depends(get_db)):
    """Count circulars not yet read by this user."""
    all_cls = db.query(CircularLetter).all()
    count = sum(1 for cl in all_cls if not cl.is_read_by_user(user_id_param))
    return {"count": count}


@router.get("/api/ministry/circulars/{circular_id}")
def get_circular(
    circular_id: int,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Full circular details. Optionally marks as read."""
    cl = db.query(CircularLetter).filter(CircularLetter.id == circular_id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Circular not found")

    if user_id:
        cl.mark_read(user_id)
        db.commit()

    return _circular_to_dict(cl, user_id=user_id, brief=False)


@router.post("/api/ministry/circulars")
def create_circular(
    payload: CircularCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin — publish a new circular letter."""
    cl = CircularLetter(
        circular_number=payload.circular_number,
        title=payload.title,
        subject=payload.subject,
        full_content=payload.full_content,
        published_date=payload.published_date or date.today(),
        effective_date=payload.effective_date,
        expiry_date=payload.expiry_date,
        category=payload.category,
        affected_codes=json.dumps(payload.affected_codes, ensure_ascii=False),
        affected_municipality_types=payload.affected_municipality_types,
        importance=payload.importance,
        action_required=payload.action_required,
        action_deadline=payload.action_deadline,
        attachment_url=payload.attachment_url,
        tags=json.dumps(payload.tags, ensure_ascii=False),
        read_by="[]",
        created_by=current_user.id,
    )
    db.add(cl)
    db.commit()
    db.refresh(cl)
    return _circular_to_dict(cl, brief=False)


@router.put("/api/ministry/circulars/{circular_id}")
def update_circular(
    circular_id: int,
    payload: CircularCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin — update an existing circular."""
    cl = db.query(CircularLetter).filter(CircularLetter.id == circular_id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Circular not found")

    for field, value in payload.dict(exclude_none=True).items():
        if field == "affected_codes":
            cl.affected_codes = json.dumps(value, ensure_ascii=False)
        elif field == "tags":
            cl.tags = json.dumps(value, ensure_ascii=False)
        else:
            setattr(cl, field, value)

    db.commit()
    db.refresh(cl)
    return _circular_to_dict(cl, brief=False)


@router.patch("/api/ministry/circulars/{circular_id}/read")
def mark_circular_read(
    circular_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Mark a circular as read by a user."""
    cl = db.query(CircularLetter).filter(CircularLetter.id == circular_id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Circular not found")
    cl.mark_read(user_id)
    db.commit()
    return {"ok": True}


@router.delete("/api/ministry/circulars/{circular_id}")
def delete_circular(
    circular_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin — delete a circular."""
    cl = db.query(CircularLetter).filter(CircularLetter.id == circular_id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Circular not found")
    db.delete(cl)
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# STATISTICS ENDPOINT (admin)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/api/ministry/stats")
def ministry_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin — usage stats: most-viewed codes, circular read rates."""
    # Top viewed codes
    view_rows = (
        db.query(MinistryCodeView.code_id, func.count(MinistryCodeView.id).label("views"))
        .group_by(MinistryCodeView.code_id)
        .order_by(func.count(MinistryCodeView.id).desc())
        .limit(10)
        .all()
    )
    code_ids = [r.code_id for r in view_rows]
    codes_map = {c.id: c for c in db.query(MinistryCode).filter(MinistryCode.id.in_(code_ids)).all()} if code_ids else {}

    top_codes = [
        {
            "code": codes_map[r.code_id].code if r.code_id in codes_map else "?",
            "name": codes_map[r.code_id].name_short if r.code_id in codes_map else "?",
            "views": r.views,
        }
        for r in view_rows
    ]

    # All municipalities for unread tracking
    all_munis = db.query(Municipality).all()
    total_munis = len(all_munis)

    # Circular read rates
    circulars = (
        db.query(CircularLetter)
        .order_by(CircularLetter.published_date.desc().nullslast())
        .limit(20)
        .all()
    )
    circular_stats = []
    for cl in circulars:
        readers = len(cl.get_read_by())
        circular_stats.append({
            "id": cl.id,
            "circular_number": cl.circular_number,
            "title": cl.title,
            "published_date": cl.published_date.isoformat() if cl.published_date else None,
            "importance": cl.importance,
            "read_count": readers,
            "unread_count": max(0, total_munis - readers),
        })

    return {
        "top_codes": top_codes,
        "circular_stats": circular_stats,
        "total_municipalities": total_munis,
    }
