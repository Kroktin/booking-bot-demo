"""Данные демо-салона: услуги, мастера, расписание."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

MSK = timezone(timedelta(hours=3))

SALON = {
    "name": "Lumi",
    "address": "Москва, ул. Пятницкая, 12",
    "hours": "Ежедневно с 10:00 до 20:00",
    "phone": "+7 (495) 000-00-00",
}

SERVICES = {
    "hw": {"title": "Женская стрижка", "price": 2500, "minutes": 60, "masters": ["anna", "irina"]},
    "hm": {"title": "Мужская стрижка", "price": 1500, "minutes": 45, "masters": ["oleg"]},
    "cl": {"title": "Окрашивание", "price": 4500, "minutes": 120, "masters": ["anna", "irina"], "from": True},
    "mn": {"title": "Маникюр с покрытием", "price": 1800, "minutes": 90, "masters": ["maria"]},
}

MASTERS = {
    "anna": {"name": "Анна", "role": "топ-стилист"},
    "irina": {"name": "Ирина", "role": "колорист"},
    "oleg": {"name": "Олег", "role": "барбер"},
    "maria": {"name": "Мария", "role": "мастер маникюра"},
}

WORK_HOURS = list(range(10, 20))  # слоты 10:00 ... 19:00
DAYS_AHEAD = 6
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def now() -> datetime:
    return datetime.now(MSK)


def price_label(svc: dict) -> str:
    p = f"{svc['price']:,}".replace(",", " ") + " ₽"
    return f"от {p}" if svc.get("from") else p


def day_label(d: str) -> str:
    dt = datetime.strptime(d, "%Y-%m-%d")
    return f"{WEEKDAYS[dt.weekday()]} {dt.strftime('%d.%m')}"


def available_days() -> list[str]:
    start = now()
    if start.hour >= 19:
        start += timedelta(days=1)
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(DAYS_AHEAD)]


def _busy_by_default(master: str, day: str, hour: int) -> bool:
    """Часть слотов «занята» заранее, чтобы расписание выглядело живым."""
    h = hashlib.md5(f"{master}:{day}:{hour}".encode()).digest()[0]
    return h < 90  # примерно 35% слотов


def free_slots(service_id: str, master_id: str, day: str, taken: set[tuple[str, str, str]]) -> dict[str, str]:
    """Свободные слоты {"HH:MM": master_id}. master_id == "any" — любой подходящий мастер."""
    masters = SERVICES[service_id]["masters"] if master_id == "any" else [master_id]
    current = now()
    result: dict[str, str] = {}
    for hour in WORK_HOURS:
        t = f"{hour:02d}:00"
        if day == current.strftime("%Y-%m-%d") and hour <= current.hour:
            continue
        for m in masters:
            if not _busy_by_default(m, day, hour) and (m, day, t) not in taken:
                result[t] = m
                break
    return result
