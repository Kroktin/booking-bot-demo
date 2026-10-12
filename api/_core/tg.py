"""Telegram-адаптер на aiogram 3: переводит апдейты в события движка и обратно."""
from __future__ import annotations

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, Message,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)

from .engine import Engine
from .ratelimit import allowed
from .storage import get_store

router = Router()


def markup(reply: dict):
    if reply["contact"]:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Отправить мой номер", request_contact=True)],
                [KeyboardButton(text="Использовать демо-номер")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )
    if reply["remove_kb"]:
        return ReplyKeyboardRemove()
    if reply["buttons"]:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=b["text"], callback_data=b["data"]) for b in row]
            for row in reply["buttons"]
        ])
    return None


async def send(bot: Bot, chat_id: int, replies: list[dict]) -> None:
    for r in replies:
        await bot.send_message(chat_id, r["text"], reply_markup=markup(r))


async def run(event: dict, chat_id: int, bot: Bot, first_name: str | None) -> None:
    sid = f"tg:{chat_id}"
    if not await allowed(sid):
        await bot.send_message(chat_id, "Слишком много сообщений, попробуйте через пару минут 🙏")
        return
    engine = Engine(get_store())
    await send(bot, chat_id, await engine.handle(sid, "telegram", event, profile_name=first_name))


@router.message(CommandStart())
async def on_start(m: Message, bot: Bot):
    await run({"type": "start"}, m.chat.id, bot, m.from_user.first_name if m.from_user else None)


@router.message(F.contact)
async def on_contact(m: Message, bot: Bot):
    await run({"type": "contact", "phone": m.contact.phone_number}, m.chat.id, bot, m.contact.first_name)


@router.message(F.text)
async def on_text(m: Message, bot: Bot):
    await run({"type": "text", "text": m.text}, m.chat.id, bot, m.from_user.first_name if m.from_user else None)


@router.callback_query()
async def on_button(cq: CallbackQuery, bot: Bot):
    await cq.answer()
    if cq.message:
        try:
            await cq.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await run({"type": "action", "data": cq.data or ""}, cq.message.chat.id, bot, cq.from_user.first_name)


_dp: Dispatcher | None = None


def build_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        _dp = Dispatcher()
        _dp.include_router(router)
    return _dp
