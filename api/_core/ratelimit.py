"""Простой лимит запросов: защищает публичную демку от спама."""
from .storage import get_store

LIMITS = (
    (60, 30),     # не больше 30 событий в минуту
    (3600, 300),  # и 300 в час
)


async def allowed(key: str) -> bool:
    store = get_store()
    for window, limit in LIMITS:
        if await store.incr(f"rl:{window}:{key}", ex=window) > limit:
            return False
    return True
