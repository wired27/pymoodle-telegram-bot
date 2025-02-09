import json
import redis.asyncio as redis
from config import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_from_cache(key: str):
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None

async def set_to_cache(key: str, value, expiration: int = 300):
    await redis_client.set(key, json.dumps(value), ex=expiration)