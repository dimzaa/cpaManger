"""
Report Auto-Scheduler — runs on 1st of every month at 06:00 AM.
Generates monthly reports for all municipalities that have data for the previous month.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler = None


def _generate_reports_job():
    """APScheduler job: generate reports for the previous month."""
    try:
        from backend.database import get_db
        from backend.models.municipality import Municipality
        from backend.models.monthly_run import MonthlyRun
        from backend.routes.reports import GeneratedReport, _do_generate_monthly
        from backend.services.pdf_generator import register_fonts

        register_fonts()

        today = datetime.now()
        # Always run for previous month regardless of day (scheduler ensures timing)
        first_of_this_month = today.replace(day=1)
        prev = first_of_this_month - timedelta(days=1)
        month_str = prev.strftime('%Y-%m')

        logger.info(f"Auto-generation job started for month: {month_str}")

        db = next(get_db())
        try:
            municipalities = db.query(Municipality).all()
            generated = 0
            failed = 0

            for muni in municipalities:
                try:
                    # Check data exists
                    run = db.query(MonthlyRun).filter(
                        MonthlyRun.municipality_id == muni.id,
                        MonthlyRun.month == month_str,
                    ).first()
                    if not run:
                        continue

                    # Check not already generated
                    existing = db.query(GeneratedReport).filter(
                        GeneratedReport.municipality_id == muni.id,
                        GeneratedReport.month == month_str,
                        GeneratedReport.is_auto_generated == True,
                    ).first()
                    if existing:
                        continue

                    # Use a dummy job_id for background tracking
                    import uuid
                    job_id = f'auto_{muni.id}_{month_str}_{uuid.uuid4().hex[:8]}'

                    # Run synchronously inside this thread
                    _do_generate_monthly(job_id, muni.id, month_str, 'auto', get_db)
                    generated += 1

                except Exception as e:
                    logger.error(f"Auto-gen failed for {muni.name}: {e}")
                    failed += 1

        finally:
            db.close()

        logger.info(f"Auto-generation complete: {generated} generated, {failed} failed")

    except Exception as e:
        logger.error(f"Auto-generation job crashed: {e}")


def start_scheduler():
    """Start the APScheduler background scheduler."""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            _generate_reports_job,
            trigger='cron',
            day=1,
            hour=6,
            minute=0,
            id='monthly_report_generation',
            replace_existing=True,
        )
        _scheduler.start()
        logger.info("Report scheduler started — will run on 1st of each month at 06:00")
    except Exception as e:
        logger.error(f"Could not start report scheduler: {e}")


def stop_scheduler():
    """Stop the scheduler on app shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Report scheduler stopped")
        except Exception:
            pass
