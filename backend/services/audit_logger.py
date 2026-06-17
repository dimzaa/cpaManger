"""
Audit logging service for tracking changes to the Reasons Library.

Logs all create, update, and delete operations on reasons.
"""

import json
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.user import AuditLog


def log_reason_change(
    db: Session,
    user_id: int,
    action: str,  # "create_reason", "update_reason", "delete_reason"
    reason_code: str,
    reason_id: int,
    new_value: dict = None,
    old_value: dict = None,
):
    """
    Log a change to a reason in the audit trail.
    
    Args:
        db: Database session
        user_id: ID of the user making the change
        action: "create_reason", "update_reason", or "delete_reason"
        reason_code: Code of the reason being changed
        reason_id: ID of the reason being changed
        new_value: Dict of new values (for create/update)
        old_value: Dict of old values (for update/delete)
    """
    
    # Build request_data JSON string
    data = {
        "reason_code": reason_code,
        "action_time": datetime.utcnow().isoformat(),
    }
    
    if new_value:
        data["new_value"] = new_value
    if old_value:
        data["old_value"] = old_value
    
    # Create audit log entry
    audit = AuditLog(
        user_id=user_id,
        action=action,
        endpoint=f"POST /api/reasons" if action == "create_reason" else f"PATCH /api/reasons/{reason_id}" if action == "update_reason" else f"DELETE /api/reasons/{reason_id}",
        method="POST" if action == "create_reason" else "PATCH" if action == "update_reason" else "DELETE",
        resource_type="reason",
        resource_id=reason_id,
        request_data=json.dumps(data),
        status_code=200,  # Success status (only log successful changes)
    )
    
    db.add(audit)
    db.commit()


def log_reason_creation(db: Session, user_id: int, reason_code: str, reason_id: int, reason_data: dict):
    """Log creation of a new reason."""
    log_reason_change(
        db=db,
        user_id=user_id,
        action="create_reason",
        reason_code=reason_code,
        reason_id=reason_id,
        new_value=reason_data,
    )


def log_reason_update(db: Session, user_id: int, reason_code: str, reason_id: int, old_data: dict, new_data: dict):
    """Log update to a reason."""
    # Only log the fields that actually changed
    changes = {}
    for key in new_data:
        if old_data.get(key) != new_data.get(key):
            changes[key] = new_data[key]
    
    log_reason_change(
        db=db,
        user_id=user_id,
        action="update_reason",
        reason_code=reason_code,
        reason_id=reason_id,
        new_value=changes,
        old_value={k: old_data.get(k) for k in changes.keys()},
    )


def log_reason_deletion(db: Session, user_id: int, reason_code: str, reason_id: int, reason_data: dict):
    """Log deletion of a reason."""
    log_reason_change(
        db=db,
        user_id=user_id,
        action="delete_reason",
        reason_code=reason_code,
        reason_id=reason_id,
        old_value=reason_data,
    )
