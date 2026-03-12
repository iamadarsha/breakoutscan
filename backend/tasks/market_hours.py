"""
Market hours specific scheduled tasks.
"""
from __future__ import annotations
import asyncio
from celery.utils.log import get_task_logger
from celery_app import app
from config import settings
import redis.asyncio as aioredis
import json

logger = get_task_logger(__name__)

async def store_orb_redis():
    """Stores the high/low pricing of the first 15 mins (ORB) of the trading day."""
    redis = await aioredis.from_url(settings.redis_url)
    
    # Fetch all current 15min prices and lock them as the ORB high/low
    cursor = b"0"
    processed = 0
    while cursor:
        cursor, keys = await redis.scan(cursor, match="price:*", count=1000)
        if not keys:
            break
            
        prices = await redis.mget(keys)
        for key, p_data in zip(keys, prices):
            if not p_data: continue
            try:
                data = json.loads(p_data)
                symbol = data.get("symbol")
                if not symbol: continue
                
                # Assume ORB logic takes the high/low of the very first candle
                orb_data = {
                    "orb_high": data.get("high", data.get("ltp")),
                    "orb_low": data.get("low", data.get("ltp")),
                    "orb_timestamp": data.get("timestamp")
                }
                
                # Store until end of day (10 hours)
                await redis.setex(f"orb:{symbol}", 36000, json.dumps(orb_data))
                processed += 1
            except Exception as e:
                logger.debug(f"ORB skip {key}: {e}")
                
    await redis.close()
    return processed

@app.task
def record_orb():
    """Fired at 9:30 AM to record the Opening Range Breakout high/low limits."""
    logger.info("Recording Opening Range Breakout (ORB) High/Low for all active stocks.")
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    count = loop.run_until_complete(store_orb_redis())
    logger.info(f"Recorded ORB for {count} stocks.")
