"""
Daily Setup tasks running at 7:30 AM before market hours.
"""
from __future__ import annotations
import asyncio
from celery.utils.log import get_task_logger
from celery_app import app
from data.upstox_instruments import load_instruments_to_redis

logger = get_task_logger(__name__)

@app.task
def download_instrument_master():
    """Download the Upstox CSV and populate Redis with active NSE Equity instruments."""
    logger.info("Starting daily instrument master download")
    
    # Run the async loader in a synchronous Celery wrapper
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        count = loop.run_until_complete(load_instruments_to_redis())
        logger.info(f"Successfully loaded {count} instruments into Redis.")
    except Exception as e:
        logger.error(f"Failed to load instruments: {str(e)}")
        raise e
