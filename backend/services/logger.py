"""
Logging service for comprehensive audit trails and system monitoring.

Features:
- Request/response logging
- Error tracking
- Performance monitoring
- Audit trail for compliance
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
import io
import sys
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).parent.parent.parent / "logs"
logs_dir.mkdir(exist_ok=True)


def _utf8_stdout():
    """Return a write-stream that always encodes as UTF-8 with replacement.

    Needed on Windows where the console may default to cp1255 / cp1252 and
    emoji characters in log messages (🔍, ✅, etc.) would raise
    UnicodeEncodeError when the logging StreamHandler writes to stdout.
    """
    try:
        # Python 3.7+: reconfigure preserves identity, cheapest fix
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        return sys.stdout
    except Exception:
        pass
    try:
        # Fallback: wrap the underlying buffer in a fresh TextIOWrapper
        return io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace",
            line_buffering=True,
        )
    except Exception:
        return sys.stdout


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger  # Already configured
    
    logger.setLevel(logging.DEBUG)
    
    # File handler - all logs
    file_handler = logging.FileHandler(logs_dir / "app.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = StructuredFormatter()
    file_handler.setFormatter(file_formatter)
    
    # File handler - error logs only
    error_handler = logging.FileHandler(logs_dir / "error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Console handler - info and above. Force UTF-8 so emoji/Hebrew in log
    # messages don't crash the handler on Windows consoles (cp1255/cp1252).
    console_handler = logging.StreamHandler(_utf8_stdout())
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger


class APILogger:
    """Log API requests and responses."""
    
    @staticmethod
    def log_request(
        logger: logging.Logger,
        method: str,
        endpoint: str,
        user_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Log incoming API request."""
        logger.info(
            f"{method} {endpoint}",
            extra={
                "user_id": user_id,
                "endpoint": endpoint,
            }
        )
    
    @staticmethod
    def log_response(
        logger: logging.Logger,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[int] = None,
    ):
        """Log API response."""
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
        logger.log(
            level,
            f"{method} {endpoint} -> {status_code}",
            extra={
                "user_id": user_id,
                "endpoint": endpoint,
                "duration_ms": duration_ms,
            }
        )
    
    @staticmethod
    def log_error(
        logger: logging.Logger,
        method: str,
        endpoint: str,
        error: Exception,
        user_id: Optional[int] = None,
    ):
        """Log API error."""
        logger.error(
            f"{method} {endpoint} - {type(error).__name__}: {str(error)}",
            extra={"user_id": user_id, "endpoint": endpoint},
            exc_info=True
        )


class AuditLogger:
    """Log significant business events for compliance."""
    
    @staticmethod
    def log_file_upload(
        logger: logging.Logger,
        user_id: int,
        filename: str,
        municipalities_count: int,
        runs_count: int,
    ):
        """Log file upload event."""
        logger.info(
            f"FILE_UPLOAD: {filename} ({municipalities_count} mun, {runs_count} runs)",
            extra={"user_id": user_id, "action": "file_upload"}
        )
    
    @staticmethod
    def log_budget_view(
        logger: logging.Logger,
        user_id: int,
        municipality_id: int,
        month: str,
    ):
        """Log budget data access."""
        logger.info(
            f"BUDGET_VIEW: municipality={municipality_id}, month={month}",
            extra={"user_id": user_id, "action": "budget_view"}
        )
    
    @staticmethod
    def log_data_export(
        logger: logging.Logger,
        user_id: int,
        export_type: str,  # csv, pdf, json
        municipality_id: Optional[int] = None,
    ):
        """Log data export."""
        logger.info(
            f"DATA_EXPORT: type={export_type}, municipality={municipality_id}",
            extra={"user_id": user_id, "action": "data_export"}
        )
    
    @staticmethod
    def log_user_login(logger: logging.Logger, user_id: int, email: str):
        """Log user login."""
        logger.info(
            f"USER_LOGIN: {email}",
            extra={"user_id": user_id, "action": "login"}
        )
    
    @staticmethod
    def log_permission_denied(
        logger: logging.Logger,
        user_id: int,
        action: str,
        reason: str,
    ):
        """Log permission denial."""
        logger.warning(
            f"PERMISSION_DENIED: action={action}, reason={reason}",
            extra={"user_id": user_id, "action": action}
        )


# Module-level logger instances
api_logger = logging.getLogger("api")
audit_logger = logging.getLogger("audit")
db_logger = logging.getLogger("database")

# Configure them
for logger in [api_logger, audit_logger, db_logger]:
    get_logger(logger.name)
