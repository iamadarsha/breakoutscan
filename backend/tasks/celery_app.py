"""
Celery configuration for background tasks and scheduled cron jobs.
"""
from celery import Celery
from celery.schedules import crontab
from config import settings

app = Celery(
    "breakoutscan_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "tasks.daily_setup",
        "tasks.market_hours",
        "tasks.alert_checker"
    ],
)

app.conf.update(
    timezone="Asia/Kolkata",
    enable_utc=False,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
)

# Scheduled routing
app.conf.beat_schedule = {
    # 1. Update instrument master daily at 7:30 AM IST
    "download-instruments-daily": {
        "task": "tasks.daily_setup.download_instrument_master",
        "schedule": crontab(hour=7, minute=30, day_of_week="mon-fri"),
    },
    # 2. Check and alert on opening range breakouts at 9:31 AM IST
    "record-orb-high-low": {
        "task": "tasks.market_hours.record_orb",
        "schedule": crontab(hour=9, minute=31, day_of_week="mon-fri"),
    },
    # 3. Evaluate user alerts every minute during market hours
    "evaluate-alerts-realtime": {
        "task": "tasks.alert_checker.evaluate_user_alerts",
        "schedule": crontab(minute="*", hour="9-15", day_of_week="mon-fri"),
    },
}
