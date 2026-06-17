"""
Reminders & Notifications API routes.

/api/reminders/...    — ministry deadlines + reminder scheduling
/api/notifications/... — in-app notifications for municipalities
"""
import json
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.ministry_deadline import MinistryDeadline
from backend.models.deadline_reminder import DeadlineReminder
from backend.models.in_app_notification import InAppNotification
from backend.models.reminder_settings import ReminderSettings
from backend.models.municipality import Municipality
from backend.models.user import User
from backend.utils.auth_guards import require_login, require_admin

router = APIRouter(tags=["reminders"])

# ─── HELPERS ──────────────────────────────────────────────────────────────────

MONTH_NAMES_HE = {
    1: "ינואר", 2: "פברואר", 3: "מרץ", 4: "אפריל",
    5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט",
    9: "ספטמבר", 10: "אוקטובר", 11: "נובמבר", 12: "דצמבר",
}


def _deadline_urgency(days_until: int) -> str:
    if days_until <= 1:
        return "critical"
    elif days_until <= 7:
        return "high"
    elif days_until <= 30:
        return "medium"
    else:
        return "low"


def _next_occurrence(deadline: MinistryDeadline, today: date) -> Optional[date]:
    """Calculate the next occurrence of a deadline from today."""
    months = deadline.get_deadline_months()
    if not months:
        return None

    candidates = []
    for yr in [today.year, today.year + 1]:
        for month in months:
            try:
                d = date(yr, month, deadline.deadline_day)
                if d >= today:
                    candidates.append(d)
            except ValueError:
                pass

    return min(candidates) if candidates else None


def _serialize_deadline(deadline: MinistryDeadline, today: date) -> dict:
    next_date = _next_occurrence(deadline, today)
    days_until = (next_date - today).days if next_date else None
    return {
        "id": deadline.id,
        "title": deadline.title,
        "description": deadline.description,
        "deadline_type": deadline.deadline_type,
        "deadline_month": deadline.deadline_month,
        "deadline_day": deadline.deadline_day,
        "next_deadline_date": next_date.isoformat() if next_date else None,
        "days_until": days_until,
        "urgency": _deadline_urgency(days_until) if days_until is not None else "low",
        "reminder_days_before": deadline.get_reminder_days(),
        "topic_codes": deadline.get_topic_codes(),
        "applies_to": deadline.applies_to,
        "action_required": deadline.action_required,
        "ministry_reference": deadline.ministry_reference,
        "is_active": deadline.is_active,
    }


def _time_ago(dt: datetime) -> str:
    if not dt:
        return ""
    now = datetime.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "עכשיו"
    if seconds < 3600:
        m = seconds // 60
        return f"לפני {m} דקות"
    if seconds < 86400:
        h = seconds // 3600
        return f"לפני {h} שעות" if h > 1 else "לפני שעה"
    d = seconds // 86400
    if d == 1:
        return "לפני יום"
    return f"לפני {d} ימים"


# ─── PYDANTIC SCHEMAS ─────────────────────────────────────────────────────────

class DeadlineCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline_type: str = "annual"
    deadline_month: Optional[str] = None
    deadline_day: int
    reminder_days_before: List[int] = [30, 14, 7, 1]
    topic_codes: List[str] = ["all"]
    applies_to: str = "all"
    ministry_reference: Optional[str] = None
    action_required: Optional[str] = None
    is_active: bool = True


class DeadlineUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline_type: Optional[str] = None
    deadline_month: Optional[str] = None
    deadline_day: Optional[int] = None
    reminder_days_before: Optional[List[int]] = None
    topic_codes: Optional[List[str]] = None
    applies_to: Optional[str] = None
    ministry_reference: Optional[str] = None
    action_required: Optional[str] = None
    is_active: Optional[bool] = None


class SettingsUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    contact_email: Optional[str] = None


# ─── DEADLINES ────────────────────────────────────────────────────────────────

@router.get("/api/reminders/deadlines")
def get_all_deadlines(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """All active ministry deadlines with next occurrence."""
    today = date.today()
    deadlines = (
        db.query(MinistryDeadline)
        .filter(MinistryDeadline.is_active == True)
        .all()
    )
    result = [_serialize_deadline(d, today) for d in deadlines]
    result.sort(key=lambda x: x["days_until"] if x["days_until"] is not None else 9999)
    return result


@router.get("/api/reminders/upcoming/{municipality_id}")
def get_upcoming_reminders(
    municipality_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Upcoming reminders for a specific municipality (next 90 days)."""
    # Access control: municipality users can only see their own
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="Access denied")

    today = date.today()
    cutoff = today + timedelta(days=90)

    reminders = (
        db.query(DeadlineReminder)
        .filter(
            DeadlineReminder.municipality_id == municipality_id,
            DeadlineReminder.reminder_date >= today,
            DeadlineReminder.reminder_date <= cutoff,
            DeadlineReminder.status.in_(["pending", "sent"]),
        )
        .order_by(DeadlineReminder.reminder_date)
        .all()
    )

    result = []
    for r in reminders:
        dl = r.deadline
        days_until_reminder = (r.reminder_date - today).days
        # next occurrence of the deadline itself
        next_dl = _next_occurrence(dl, today)
        days_until_deadline = (next_dl - today).days if next_dl else None

        result.append({
            "id": r.id,
            "reminder_date": r.reminder_date.isoformat(),
            "reminder_date_he": f"{r.reminder_date.day} {MONTH_NAMES_HE.get(r.reminder_date.month, '')} {r.reminder_date.year}",
            "days_until_reminder": days_until_reminder,
            "days_before": r.days_before,
            "deadline_id": dl.id,
            "deadline_title": dl.title,
            "deadline_date": next_dl.isoformat() if next_dl else None,
            "days_until_deadline": days_until_deadline,
            "urgency": _deadline_urgency(days_until_deadline) if days_until_deadline is not None else "low",
            "action_required": dl.action_required,
            "ministry_reference": dl.ministry_reference,
            "status": r.status,
        })

    return result


@router.get("/api/reminders/calendar/{municipality_id}")
def get_calendar_reminders(
    municipality_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Full year calendar of reminders, grouped by month."""
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="Access denied")

    today = date.today()
    year_end = date(today.year + 1, 12, 31)

    reminders = (
        db.query(DeadlineReminder)
        .filter(
            DeadlineReminder.municipality_id == municipality_id,
            DeadlineReminder.reminder_date >= today,
            DeadlineReminder.reminder_date <= year_end,
        )
        .order_by(DeadlineReminder.reminder_date)
        .all()
    )

    calendar = {}
    for r in reminders:
        month_key = r.reminder_date.strftime("%Y-%m")
        dl = r.deadline
        next_dl = _next_occurrence(dl, today)
        days_until_deadline = (next_dl - today).days if next_dl else None

        entry = {
            "id": r.id,
            "date": r.reminder_date.isoformat(),
            "day": r.reminder_date.day,
            "month": r.reminder_date.month,
            "month_name_he": MONTH_NAMES_HE.get(r.reminder_date.month, ""),
            "days_before": r.days_before,
            "deadline_id": dl.id,
            "deadline_title": dl.title,
            "deadline_date": next_dl.isoformat() if next_dl else None,
            "days_until_deadline": days_until_deadline,
            "urgency": _deadline_urgency(days_until_deadline) if days_until_deadline is not None else "low",
            "action_required": dl.action_required,
            "status": r.status,
            "is_deadline_day": next_dl == r.reminder_date if next_dl else False,
        }

        if month_key not in calendar:
            calendar[month_key] = []
        calendar[month_key].append(entry)

    return calendar


@router.post("/api/reminders/dismiss/{reminder_id}")
def dismiss_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Municipality dismisses a reminder."""
    reminder = db.query(DeadlineReminder).filter(DeadlineReminder.id == reminder_id).first()
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if current_user.role == "municipality" and current_user.municipality_id != reminder.municipality_id:
        raise HTTPException(status_code=403, detail="Access denied")

    reminder.status = "dismissed"
    reminder.dismissed_at = datetime.now()
    reminder.dismissed_by = current_user.id
    db.commit()
    return {"success": True}


@router.get("/api/reminders/admin/all")
def admin_get_all_reminders(
    status_filter: Optional[str] = None,
    municipality_id: Optional[int] = None,
    deadline_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: all reminders across all municipalities."""
    query = db.query(DeadlineReminder)
    if status_filter:
        query = query.filter(DeadlineReminder.status == status_filter)
    if municipality_id:
        query = query.filter(DeadlineReminder.municipality_id == municipality_id)
    if deadline_id:
        query = query.filter(DeadlineReminder.deadline_id == deadline_id)

    reminders = query.order_by(DeadlineReminder.reminder_date.desc()).limit(500).all()
    today = date.today()

    return [
        {
            "id": r.id,
            "municipality_name": r.municipality.name if r.municipality else "",
            "municipality_id": r.municipality_id,
            "deadline_title": r.deadline.title if r.deadline else "",
            "deadline_id": r.deadline_id,
            "reminder_date": r.reminder_date.isoformat(),
            "days_before": r.days_before,
            "status": r.status,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "dismissed_at": r.dismissed_at.isoformat() if r.dismissed_at else None,
        }
        for r in reminders
    ]


@router.post("/api/reminders/deadlines")
def create_deadline(
    data: DeadlineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: create a custom deadline."""
    deadline = MinistryDeadline(
        title=data.title,
        description=data.description,
        deadline_type=data.deadline_type,
        deadline_month=data.deadline_month,
        deadline_day=data.deadline_day,
        reminder_days_before=json.dumps(data.reminder_days_before),
        topic_codes=json.dumps(data.topic_codes),
        applies_to=data.applies_to,
        ministry_reference=data.ministry_reference,
        action_required=data.action_required,
        is_active=data.is_active,
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)

    # Regenerate reminders for the new deadline
    try:
        from backend.services.reminder_service import _service_instance
        if _service_instance:
            _service_instance.generate_upcoming_reminders()
    except Exception:
        pass

    return _serialize_deadline(deadline, date.today())


@router.put("/api/reminders/deadlines/{deadline_id}")
def update_deadline(
    deadline_id: int,
    data: DeadlineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: update a deadline."""
    deadline = db.query(MinistryDeadline).filter(MinistryDeadline.id == deadline_id).first()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    if data.title is not None:
        deadline.title = data.title
    if data.description is not None:
        deadline.description = data.description
    if data.deadline_type is not None:
        deadline.deadline_type = data.deadline_type
    if data.deadline_month is not None:
        deadline.deadline_month = data.deadline_month
    if data.deadline_day is not None:
        deadline.deadline_day = data.deadline_day
    if data.reminder_days_before is not None:
        deadline.reminder_days_before = json.dumps(data.reminder_days_before)
    if data.topic_codes is not None:
        deadline.topic_codes = json.dumps(data.topic_codes)
    if data.applies_to is not None:
        deadline.applies_to = data.applies_to
    if data.ministry_reference is not None:
        deadline.ministry_reference = data.ministry_reference
    if data.action_required is not None:
        deadline.action_required = data.action_required
    if data.is_active is not None:
        deadline.is_active = data.is_active

    db.commit()
    db.refresh(deadline)
    return _serialize_deadline(deadline, date.today())


@router.delete("/api/reminders/deadlines/{deadline_id}")
def deactivate_deadline(
    deadline_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: deactivate (soft-delete) a deadline."""
    deadline = db.query(MinistryDeadline).filter(MinistryDeadline.id == deadline_id).first()
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    deadline.is_active = False
    db.commit()
    return {"success": True}


# ─── REMINDER SETTINGS ────────────────────────────────────────────────────────

@router.get("/api/reminders/settings")
def get_settings(
    municipality_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Get reminder settings (global or per municipality)."""
    if municipality_id:
        settings = db.query(ReminderSettings).filter(
            ReminderSettings.municipality_id == municipality_id
        ).first()
    else:
        settings = db.query(ReminderSettings).filter(
            ReminderSettings.municipality_id == None
        ).first()

    if not settings:
        return {
            "municipality_id": municipality_id,
            "email_enabled": True,
            "in_app_enabled": True,
            "whatsapp_enabled": False,
            "contact_email": None,
        }

    return {
        "municipality_id": settings.municipality_id,
        "email_enabled": settings.email_enabled,
        "in_app_enabled": settings.in_app_enabled,
        "whatsapp_enabled": settings.whatsapp_enabled,
        "contact_email": settings.contact_email,
    }


@router.post("/api/reminders/settings")
def save_settings(
    data: SettingsUpdate,
    municipality_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: save global or per-municipality reminder settings."""
    settings = db.query(ReminderSettings).filter(
        ReminderSettings.municipality_id == municipality_id
    ).first()

    if not settings:
        settings = ReminderSettings(municipality_id=municipality_id)
        db.add(settings)

    if data.email_enabled is not None:
        settings.email_enabled = data.email_enabled
    if data.in_app_enabled is not None:
        settings.in_app_enabled = data.in_app_enabled
    if data.whatsapp_enabled is not None:
        settings.whatsapp_enabled = data.whatsapp_enabled
    if data.contact_email is not None:
        settings.contact_email = data.contact_email

    db.commit()
    return {"success": True}


@router.get("/api/reminders/settings/all-municipalities")
def get_all_municipality_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: all per-municipality settings."""
    municipalities = db.query(Municipality).all()
    settings_map = {
        s.municipality_id: s
        for s in db.query(ReminderSettings).filter(
            ReminderSettings.municipality_id != None
        ).all()
    }

    return [
        {
            "municipality_id": m.id,
            "municipality_name": m.name,
            "email_enabled": settings_map[m.id].email_enabled if m.id in settings_map else True,
            "in_app_enabled": settings_map[m.id].in_app_enabled if m.id in settings_map else True,
            "contact_email": settings_map[m.id].contact_email if m.id in settings_map else None,
        }
        for m in municipalities
    ]


# ─── IN-APP NOTIFICATIONS ─────────────────────────────────────────────────────

@router.get("/api/notifications/{municipality_id}")
def get_notifications(
    municipality_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Get in-app notifications for a municipality."""
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="Access denied")

    notifications = (
        db.query(InAppNotification)
        .filter(InAppNotification.municipality_id == municipality_id)
        .order_by(InAppNotification.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "action_url": n.action_url,
            "action_text": n.action_text,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "time_ago": _time_ago(n.created_at),
        }
        for n in notifications
    ]


@router.get("/api/notifications/unread-count/{municipality_id}")
def get_unread_count(
    municipality_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Count unread notifications."""
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="Access denied")

    count = (
        db.query(InAppNotification)
        .filter(
            InAppNotification.municipality_id == municipality_id,
            InAppNotification.is_read == False,
        )
        .count()
    )
    return {"count": count}


@router.patch("/api/notifications/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Mark a single notification as read."""
    notif = db.query(InAppNotification).filter(InAppNotification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if current_user.role == "municipality" and current_user.municipality_id != notif.municipality_id:
        raise HTTPException(status_code=403, detail="Access denied")

    notif.is_read = True
    notif.read_at = datetime.now()
    db.commit()
    return {"success": True}


@router.patch("/api/notifications/read-all/{municipality_id}")
def mark_all_read(
    municipality_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_login),
):
    """Mark all notifications as read for a municipality."""
    if current_user.role == "municipality" and current_user.municipality_id != municipality_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.query(InAppNotification).filter(
        InAppNotification.municipality_id == municipality_id,
        InAppNotification.is_read == False,
    ).update({"is_read": True, "read_at": datetime.now()})
    db.commit()
    return {"success": True}
