"""
Real-time alert checking task.
"""
from __future__ import annotations
import asyncio
from celery.utils.log import get_task_logger
from celery_app import app
from config import settings
import redis.asyncio as aioredis

logger = get_task_logger(__name__)

async def process_active_alerts():
    """
    Fetch all active user alerts and evaluate them against the latest Redis prices.
    Used during market hours every few minutes.
    """
    redis = await aioredis.from_url(settings.redis_url)
    # Placeholder: Evaluate realtime signals against SQL user alerts
    # Since DB connection involves SQLAlchemy, we just log for dev server here
    logger.info("Checking user configured alerts against live price state...")
    await redis.close()

@app.task
def evaluate_user_alerts():
    """Background task evaluating user alerts."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(process_active_alerts())
