import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from fastapi.testclient import TestClient  # noqa: E402

import _core.storage as storage  # noqa: E402
from index import app  # noqa: E402


def test_web_flow_and_admin():
    storage._store = storage.MemoryStore()
    c = TestClient(app)
    sid = "test-session-123"
    assert c.post("/api/py/chat", json={"sid": "bad sid!", "event": {"type": "start"}}).status_code == 400
    r = c.post("/api/py/chat", json={"sid": sid, "event": {"type": "start"}}).json()
    assert r["replies"][0]["buttons"]
    seq = ["m:book", "svc:mn", "ms:maria"]
    for d in seq:
        r = c.post("/api/py/chat", json={"sid": sid, "event": {"type": "action", "data": d}}).json()
    day = next(b["data"] for row in r["replies"][0]["buttons"] for b in row if b["data"].startswith("d:"))
    r = c.post("/api/py/chat", json={"sid": sid, "event": {"type": "action", "data": day}}).json()
    slot = next(b["data"] for row in r["replies"][0]["buttons"] for b in row if b["data"].startswith("t:"))
    c.post("/api/py/chat", json={"sid": sid, "event": {"type": "action", "data": slot}})
    c.post("/api/py/chat", json={"sid": sid, "event": {"type": "text", "text": "Мария"}})
    c.post("/api/py/chat", json={"sid": sid, "event": {"type": "action", "data": "ph:demo"}})
    r = c.post("/api/py/chat", json={"sid": sid, "event": {"type": "action", "data": "ok"}}).json()
    assert "вы записаны" in r["replies"][0]["text"]

    data = c.get("/api/py/leads").json()
    mine = [x for x in data["leads"] if x["source"] == "web" and x["name"] == "Мария"]
    assert mine and "sid" not in mine[0]
    assert data["stats"]["total"] == 6

    assert c.post(f"/api/py/leads/{mine[0]['id']}", json={"status": "confirmed"}).json()["ok"]
    inbox = c.get("/api/py/inbox", params={"sid": sid}).json()["messages"]
    assert inbox and "подтверждена" in inbox[0]
    assert c.get("/api/py/inbox", params={"sid": sid}).json()["messages"] == []
    assert c.post("/api/py/leads/zzz", json={"status": "confirmed"}).status_code == 404
    assert c.post(f"/api/py/leads/{mine[0]['id']}", json={"status": "hacked"}).status_code == 404


def test_webhook_requires_secret():
    c = TestClient(app)
    assert c.post("/api/py/telegram", json={}).status_code == 403


def test_rate_limit():
    storage._store = storage.MemoryStore()
    c = TestClient(app)
    codes = [c.post("/api/py/chat", json={"sid": "spam-session-1", "event": {"type": "text", "text": "hi"}}).status_code
             for _ in range(35)]
    assert 429 in codes
