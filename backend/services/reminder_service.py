"""
Reminder Service — generates reminder records and sends them daily.

Runs at 7:00 AM Israel time every day.
Checks pending deadline_reminders for today and sends email + in-app notifications.
"""
import os
import json
import smtplib
import logging
from datetime import datetime, date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

_scheduler = None
_service_instance = None


class ReminderService:
    def __init__(self, db_session_factory):
        self.db_factory = db_session_factory

    # ─── SCHEDULER ────────────────────────────────────────────────────────────

    def start(self):
        global _scheduler
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            import pytz

            tz = pytz.timezone("Asia/Jerusalem")
            _scheduler = BackgroundScheduler(timezone=tz)
            _scheduler.add_job(
                self.process_daily_reminders,
                "cron",
                hour=7,
                minute=0,
                id="daily_reminders",
                replace_existing=True,
            )
            _scheduler.start()
            print("✅ Reminder scheduler started (daily 07:00 Israel time)")
        except ImportError as e:
            print(f"⚠️  Reminder scheduler not started (missing dependency: {e}). "
                  "Install apscheduler and pytz.")
        except Exception as e:
            print(f"⚠️  Reminder scheduler error: {e}")

    def stop(self):
        global _scheduler
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)
            print("🛑 Reminder scheduler stopped")

    # ─── DAILY PROCESSING ─────────────────────────────────────────────────────

    def process_daily_reminders(self):
        """Runs at 07:00 AM — sends pending reminders for today."""
        from backend.models.deadline_reminder import DeadlineReminder

        db = next(self.db_factory())
        today = date.today()
        print(f"🔔 Processing reminders for {today}")

        try:
            reminders = (
                db.query(DeadlineReminder)
                .filter(
                    DeadlineReminder.reminder_date == today,
                    DeadlineReminder.status == "pending",
                )
                .all()
            )

            sent = failed = 0
            for reminder in reminders:
                try:
                    self._send_reminder(reminder, db)
                    reminder.status = "sent"
                    reminder.sent_at = datetime.now()
                    sent += 1
                except Exception as exc:
                    reminder.status = "failed"
                    failed += 1
                    logger.error(f"Failed reminder {reminder.id}: {exc}")

            db.commit()
            print(f"✅ Reminders: {sent} sent, {failed} failed")
        finally:
            db.close()

    # ─── SEND SINGLE REMINDER ─────────────────────────────────────────────────

    def _send_reminder(self, reminder, db):
        deadline = reminder.deadline
        municipality = reminder.municipality
        days_before = reminder.days_before

        # Resolve contact email (municipality user)
        from backend.models.user import User
        muni_user = (
            db.query(User)
            .filter(User.municipality_id == municipality.id, User.is_active == True)
            .first()
        )

        # Check per-municipality settings
        from backend.models.reminder_settings import ReminderSettings
        settings = db.query(ReminderSettings).filter(
            ReminderSettings.municipality_id == municipality.id
        ).first()

        global_settings = db.query(ReminderSettings).filter(
            ReminderSettings.municipality_id == None
        ).first()

        email_enabled = True
        in_app_enabled = True
        contact_email = None

        if settings:
            email_enabled = settings.email_enabled
            in_app_enabled = settings.in_app_enabled
            contact_email = settings.contact_email
        elif global_settings:
            email_enabled = global_settings.email_enabled
            in_app_enabled = global_settings.in_app_enabled

        if not contact_email and muni_user:
            contact_email = muni_user.email
        elif not contact_email and municipality.login_email:
            contact_email = municipality.login_email

        if email_enabled and contact_email:
            try:
                self._send_email(contact_email, municipality, deadline, days_before)
            except Exception as exc:
                logger.warning(f"Email failed for reminder {reminder.id}: {exc}")

        if in_app_enabled:
            self._create_in_app_notification(municipality.id, deadline, days_before, db)

    # ─── EMAIL ────────────────────────────────────────────────────────────────

    def _send_email(self, email, municipality, deadline, days_before):
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        from_name = os.getenv("FROM_NAME", "SmartHub")

        if not smtp_user or not smtp_pass:
            logger.info(
                f"SMTP not configured — skipping email to {email} "
                f"(reminder: {deadline.title})"
            )
            return

        if days_before == 1:
            urgency = "🚨 מחר!"
            urgency_text = "מחר"
            border_color = "#EF4444"
        elif days_before <= 7:
            urgency = f"⚠️ עוד {days_before} ימים"
            urgency_text = f"עוד {days_before} ימים"
            border_color = "#F59E0B"
        elif days_before <= 14:
            urgency = f"📅 עוד {days_before} ימים"
            urgency_text = f"עוד {days_before} ימים"
            border_color = "#3B82F6"
        else:
            urgency = f"📋 עוד {days_before} ימים"
            urgency_text = f"עוד {days_before} ימים"
            border_color = "#6B7280"

        deadline_months = deadline.get_deadline_months()
        dl_month = deadline_months[0] if deadline_months else "?"
        deadline_date_str = f"{deadline.deadline_day}/{dl_month}"

        subject = f"תזכורת: {deadline.title} — {urgency_text} | {municipality.name}"

        html = f"""
        <div dir="rtl" style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <div style="background: #1E3A5F; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">SmartHub</h1>
            <p style="color: #93C5FD; margin: 5px 0; font-size: 14px;">מערכת ניהול תקציב חינוך</p>
          </div>
          <div style="padding: 30px; background: #F8FAFC;">
            <div style="background: white; border-radius: 12px; padding: 24px; border-right: 4px solid {border_color};">
              <h2 style="color: #1E3A5F; margin-top: 0;">🔔 תזכורת מועד הגשה</h2>
              <p style="font-size: 18px; color: #374151;">שלום {municipality.name},</p>
              <div style="background: #FEF3C7; border-radius: 8px; padding: 16px; margin: 16px 0;">
                <h3 style="color: #92400E; margin: 0;">{urgency} — {deadline.title}</h3>
                <p style="color: #78350F; margin: 8px 0 0 0;">מועד אחרון: {deadline_date_str}</p>
              </div>
              <p style="color: #6B7280;">{deadline.description or ''}</p>
              <div style="background: #EFF6FF; border-radius: 8px; padding: 16px; margin: 16px 0;">
                <h4 style="color: #1D4ED8; margin: 0 0 8px 0;">📋 מה צריך לעשות:</h4>
                <p style="color: #1E40AF; margin: 0;">{deadline.action_required or ''}</p>
              </div>
              <p style="color: #9CA3AF; font-size: 12px;">מקור: {deadline.ministry_reference or ''}</p>
              <div style="text-align: center; margin-top: 24px;">
                <a href="http://localhost:3000/portal/deadlines"
                   style="background: #1E3A5F; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">
                  כנס למערכת לפרטים נוספים ←
                </a>
              </div>
            </div>
            <p style="color: #9CA3AF; font-size: 12px; text-align: center; margin-top: 16px;">
              לביטול תזכורות פנה לרואה החשבון שלך<br>SmartHub | מערכת ניהול תקציב חינוך
            </p>
          </div>
        </div>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{smtp_user}>"
        msg["To"] = email
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Email sent to {email} for reminder: {deadline.title}")

    # ─── IN-APP NOTIFICATION ──────────────────────────────────────────────────

    def _create_in_app_notification(self, municipality_id, deadline, days_before, db):
        from backend.models.in_app_notification import InAppNotification

        deadline_months = deadline.get_deadline_months()
        dl_month = deadline_months[0] if deadline_months else "?"

        notif = InAppNotification(
            municipality_id=municipality_id,
            type="deadline_reminder",
            title=f"תזכורת: {deadline.title}",
            message=(
                f"המועד האחרון הוא ב-{deadline.deadline_day}/{dl_month}. "
                f"עוד {days_before} ימים."
            ),
            action_url="/portal/deadlines",
            action_text="צפה בפרטים",
            is_read=False,
            created_at=datetime.now(),
        )
        db.add(notif)

    # ─── GENERATE UPCOMING REMINDERS ──────────────────────────────────────────

    def generate_upcoming_reminders(self, year=None):
        """
        Pre-generate all reminder records for the year.
        Safe to call multiple times — idempotent.
        """
        from backend.models.ministry_deadline import MinistryDeadline
        from backend.models.deadline_reminder import DeadlineReminder
        from backend.models.municipality import Municipality

        db = next(self.db_factory())
        year = year or datetime.now().year
        today = date.today()

        try:
            deadlines = (
                db.query(MinistryDeadline)
                .filter(MinistryDeadline.is_active == True)
                .all()
            )
            municipalities = db.query(Municipality).all()

            created = 0
            for deadline in deadlines:
                reminder_days = deadline.get_reminder_days()

                if deadline.deadline_type == "quarterly":
                    months = deadline.get_deadline_months()
                    if not months:
                        months = [3, 6, 9, 12]
                    for month in months:
                        for yr in [year, year + 1]:
                            try:
                                dl_date = date(yr, month, deadline.deadline_day)
                            except ValueError:
                                continue
                            for days in reminder_days:
                                r_date = dl_date - timedelta(days=days)
                                if r_date >= today:
                                    for muni in municipalities:
                                        created += self._create_reminder_record(
                                            deadline, muni, r_date, days, db
                                        )

                elif deadline.deadline_type == "annual":
                    months = deadline.get_deadline_months()
                    month = months[0] if months else None
                    if not month:
                        continue
                    for yr in [year, year + 1]:
                        try:
                            dl_date = date(yr, month, deadline.deadline_day)
                        except ValueError:
                            continue
                        for days in reminder_days:
                            r_date = dl_date - timedelta(days=days)
                            if r_date >= today:
                                for muni in municipalities:
                                    created += self._create_reminder_record(
                                        deadline, muni, r_date, days, db
                                    )

            db.commit()
            print(f"✅ Generated {created} new reminder records for {year}")
        finally:
            db.close()

    def _create_reminder_record(self, deadline, municipality, reminder_date, days_before, db):
        from backend.models.deadline_reminder import DeadlineReminder

        existing = (
            db.query(DeadlineReminder)
            .filter(
                DeadlineReminder.deadline_id == deadline.id,
                DeadlineReminder.municipality_id == municipality.id,
                DeadlineReminder.reminder_date == reminder_date,
            )
            .first()
        )
        if not existing:
            r = DeadlineReminder(
                deadline_id=deadline.id,
                municipality_id=municipality.id,
                reminder_date=reminder_date,
                days_before=days_before,
                status="pending",
            )
            db.add(r)
            return 1
        return 0


# ─── Module-level helpers for main.py ─────────────────────────────────────────

def start_reminder_service(db_factory):
    global _service_instance
    _service_instance = ReminderService(db_factory)
    _service_instance.generate_upcoming_reminders()
    _service_instance.start()


def stop_reminder_service():
    global _service_instance
    if _service_instance:
        _service_instance.stop()
