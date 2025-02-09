import functools
from core.cache import get_from_cache, set_to_cache

def cache(key: str, ex: int = 300):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Here we assume the first argument after self is telegram_id
            # Adjust the key formatting as needed.
            telegram_id = kwargs.get("telegram_id") or (args[1] if len(args) > 1 else None)
            formatted_key = key.format(telegram_id=telegram_id)
            cached = await get_from_cache(formatted_key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            await set_to_cache(formatted_key, result, expiration=ex)
            return result
        return wrapper
    return decorator