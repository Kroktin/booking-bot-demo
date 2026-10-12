"""HTTP API демо: веб-чат, админка и webhook Telegram."""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Header, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from _core.engine import Engine  # noqa: E402
from _core.ratelimit import allowed  # noqa: E402
from _core.storage import get_store  # noqa: E402

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
# CORS нужен только для локальной разработки: на проде фронт и API на одном домене через прокси.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

SID_RE = re.compile(r"^[a-zA-Z0-9-]{8,64}$")


def engine() -> Engine:
    return Engine(get_store())


def web_sid(sid: str) -> str:
    if not SID_RE.match(sid or ""):
        raise HTTPException(400, "bad session")
    return f"web:{sid}"


def client_ip(request: Request) -> str:
    return (request.headers.get("x-forwarded-for") or request.client.host or "?").split(",")[0].strip()


class ChatIn(BaseModel):
    sid: str
    event: dict


class StatusIn(BaseModel):
    status: str


@app.get("/api/py/health")
async def health():
    return {"ok": True}


@app.post("/api/py/chat")
async def chat(body: ChatIn, request: Request):
    sid = web_sid(body.sid)
    if not (await allowed(sid) and await allowed(f"ip:{client_ip(request)}")):
        raise HTTPException(429, "Слишком много сообщений, подождите минуту")
    event = {k: v for k, v in body.event.items() if k in ("type", "text", "data", "phone")}
    if event.get("type") not in ("start", "text", "action"):
        raise HTTPException(400, "bad event")
    if isinstance(event.get("text"), str):
        event["text"] = event["text"][:300]
    return {"replies": await engine().handle(sid, "web", event)}


@app.get("/api/py/inbox")
async def inbox(sid: str):
    return {"messages": await engine().pop_inbox(web_sid(sid))}


@app.get("/api/py/leads")
async def leads():
    e = engine()
    await e.ensure_seed()
    items = sorted(await e.leads(), key=lambda x: x["created_at"], reverse=True)
    public = [{k: v for k, v in x.items() if k not in ("sid", "seed")} for x in items]
    return {"leads": public, "stats": await e.stats()}


@app.post("/api/py/leads/{lead_id}")
async def set_status(lead_id: str, body: StatusIn, request: Request):
    if not await allowed(f"admin:{client_ip(request)}"):
        raise HTTPException(429, "Слишком часто")
    e = engine()
    lead = await e.set_status(lead_id, body.status)
    if not lead:
        raise HTTPException(404, "not found")
    text = e.status_message(lead)
    if text:
        if lead["sid"].startswith("web:"):
            await e.push_inbox(lead["sid"], text)
        elif lead["sid"].startswith("tg:") and os.getenv("TELEGRAM_BOT_TOKEN"):
            from aiogram import Bot

            bot = Bot(os.environ["TELEGRAM_BOT_TOKEN"])
            try:
                await bot.send_message(int(lead["sid"][3:]), text)
            except Exception:
                pass
            finally:
                await bot.session.close()
    return {"ok": True}


@app.post("/api/py/telegram")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not secret or x_telegram_bot_api_secret_token != secret:
        raise HTTPException(403, "forbidden")
    from aiogram import Bot
    from aiogram.types import Update

    from _core.tg import build_dispatcher

    bot = Bot(os.environ["TELEGRAM_BOT_TOKEN"])
    try:
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await build_dispatcher().feed_update(bot, update)
    except Exception as exc:  # отвечаем 200, иначе Telegram будет повторять апдейт
        print(f"telegram update failed: {exc!r}")
    finally:
        await bot.session.close()
    return {"ok": True}
