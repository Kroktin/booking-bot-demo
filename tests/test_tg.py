import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from aiogram import Bot  # noqa: E402
from aiogram.types import Update  # noqa: E402

import _core.storage as storage  # noqa: E402
from _core import tg  # noqa: E402


def test_updates_flow(monkeypatch):
    storage._store = storage.MemoryStore()
    sent, calls = [], []

    async def fake_call(self, method, request_timeout=None):
        calls.append(type(method).__name__)
        if type(method).__name__ == "SendMessage":
            sent.append((method.text, method.reply_markup))
        return True

    monkeypatch.setattr(Bot, "__call__", fake_call)

    async def go():
        bot = Bot("123456:" + "A" * 35)
        dp = tg.build_dispatcher()
        user = {"id": 42, "is_bot": False, "first_name": "Толя"}
        chat = {"id": 42, "type": "private"}

        async def feed(payload):
            await dp.feed_update(bot, Update.model_validate(payload, context={"bot": bot}))

        await feed({"update_id": 1, "message": {"message_id": 1, "date": 0, "chat": chat, "from": user, "text": "/start", "entities": [{"type": "bot_command", "offset": 0, "length": 6}]}})
        assert "Здравствуйте" in sent[-1][0]
        await feed({"update_id": 2, "callback_query": {"id": "c1", "from": user, "chat_instance": "x", "data": "m:prices",
                                                       "message": {"message_id": 2, "date": 0, "chat": chat, "text": "menu"}}})
        assert "Наши цены" in sent[-1][0]
        assert "AnswerCallbackQuery" in calls and "EditMessageReplyMarkup" in calls
        await feed({"update_id": 3, "message": {"message_id": 3, "date": 0, "chat": chat, "from": user, "text": "где вы?"}})
        assert "Пятницкая" in sent[-1][0]
        await bot.session.close()

    asyncio.run(go())
