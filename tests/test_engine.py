import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from _core.engine import Engine  # noqa: E402
from _core.storage import MemoryStore  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def buttons(reply):
    return [b["data"] for row in reply["buttons"] for b in row]


async def book(e, sid, source="web"):
    r = await e.handle(sid, source, {"type": "start"})
    assert "m:book" in buttons(r[0])
    r = await e.handle(sid, source, {"type": "action", "data": "m:book"})
    assert "svc:hw" in buttons(r[0])
    r = await e.handle(sid, source, {"type": "action", "data": "svc:hw"})
    assert "ms:any" in buttons(r[0])
    r = await e.handle(sid, source, {"type": "action", "data": "ms:any"})
    day = next(d for d in buttons(r[0]) if d.startswith("d:"))
    r = await e.handle(sid, source, {"type": "action", "data": day})
    slot = next(d for d in buttons(r[0]) if d.startswith("t:"))
    r = await e.handle(sid, source, {"type": "action", "data": slot})
    r = await e.handle(sid, source, {"type": "text", "text": "анна"})
    assert r[0]["contact"]
    r = await e.handle(sid, source, {"type": "text", "text": "8 (900) 123-45-67"})
    assert "Проверьте запись" in r[1]["text"] and "+7 900 123-45-67" in r[1]["text"]
    r = await e.handle(sid, source, {"type": "action", "data": "ok"})
    assert "вы записаны" in r[0]["text"]
    return day[2:], slot[2:]


def test_full_booking_and_cancel():
    async def go():
        e = Engine(MemoryStore())
        await book(e, "web:a")
        leads = await e.leads()
        assert len(leads) == 1 and leads[0]["name"] == "Анна" and leads[0]["phone"].endswith("67")
        my = await e.handle("web:a", "web", {"type": "action", "data": "m:my"})
        cancel = next(d for d in buttons(my[0]) if d.startswith("cancel:"))
        r = await e.handle("web:a", "web", {"type": "action", "data": cancel})
        assert "отменена" in r[0]["text"]
        assert (await e.leads())[0]["status"] == "cancelled"
    run(go())


def test_slot_taken_not_offered_again():
    async def go():
        e = Engine(MemoryStore())
        await e.handle("web:x", "web", {"type": "start"})
        await e.handle("web:x", "web", {"type": "action", "data": "m:book"})
        await e.handle("web:x", "web", {"type": "action", "data": "svc:hm"})
        r = await e.handle("web:x", "web", {"type": "action", "data": "ms:oleg"})
        day = next(d for d in buttons(r[0]) if d.startswith("d:"))
        r = await e.handle("web:x", "web", {"type": "action", "data": day})
        slot = next(d for d in buttons(r[0]) if d.startswith("t:"))
        await e.handle("web:x", "web", {"type": "action", "data": slot})
        await e.handle("web:x", "web", {"type": "text", "text": "Иван"})
        await e.handle("web:x", "web", {"type": "action", "data": "ph:demo"})
        await e.handle("web:x", "web", {"type": "action", "data": "ok"})
        # второй клиент не должен увидеть этот слот у того же мастера
        await e.handle("web:y", "web", {"type": "action", "data": "m:book"})
        await e.handle("web:y", "web", {"type": "action", "data": "svc:hm"})
        await e.handle("web:y", "web", {"type": "action", "data": "ms:oleg"})
        r = await e.handle("web:y", "web", {"type": "action", "data": day})
        assert slot not in buttons(r[0])
    run(go())


def test_validation_and_fallbacks():
    async def go():
        e = Engine(MemoryStore())
        r = await e.handle("web:z", "web", {"type": "text", "text": "сколько стоит маникюр?"})
        assert "Наши цены" in r[0]["text"]
        r = await e.handle("web:z", "web", {"type": "text", "text": "где вы находитесь"})
        assert "Пятницкая" in r[0]["text"]
        r = await e.handle("web:z", "web", {"type": "text", "text": "qwerty"})
        assert "демо-бот" in r[0]["text"]
        r = await e.handle("web:z", "web", {"type": "action", "data": "t:10:00"})
        assert "устарела" in r[0]["text"]
        await e.handle("web:z", "web", {"type": "action", "data": "m:book"})
        await e.handle("web:z", "web", {"type": "action", "data": "svc:mn"})
        r = await e.handle("web:z", "web", {"type": "action", "data": "ms:anna"})  # чужой мастер
        assert "К кому записать" in r[0]["text"]
    run(go())


def test_bad_name_and_phone():
    async def go():
        e = Engine(MemoryStore())
        s = {"step": "name", "service": "hw", "master": "anna", "date": "2030-01-01", "time": "10:00", "assigned": "anna"}
        await e.save_session("web:n", s)
        r = await e.handle("web:n", "web", {"type": "text", "text": "<script>"})
        assert "от 2 до 30 букв" in r[0]["text"]
        await e.handle("web:n", "web", {"type": "text", "text": "Ольга"})
        r = await e.handle("web:n", "web", {"type": "text", "text": "123"})
        assert "Не похоже на номер" in r[0]["text"]
    run(go())


def test_seed_and_stats():
    async def go():
        e = Engine(MemoryStore())
        await e.ensure_seed()
        await e.ensure_seed()
        assert len(await e.leads()) == 5
        st = await e.stats()
        assert st["total"] == 5 and st["telegram"] == 3
    run(go())
