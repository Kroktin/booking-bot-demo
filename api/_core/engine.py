"""
Сценарий бота записи. Не зависит от транспорта: одинаково работает для веб-чата и Telegram.

Событие на вход:
    {"type": "start"} | {"type": "text", "text": "..."} | {"type": "action", "data": "..."}
    | {"type": "contact", "phone": "...", "name": "..."}
Ответ: список сообщений {"text", "buttons": [[{"text", "data"}]], "contact": bool, "remove_kb": bool}
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta

from .salon import (
    MASTERS, SALON, SERVICES, available_days, day_label, free_slots, now, price_label,
)

TTL = 24 * 3600
DEMO_PHONE = "+79000000000"
STATUSES = {"new": "Новая", "confirmed": "Подтверждена", "done": "Завершена", "cancelled": "Отменена"}


def msg(text: str, buttons: list[list[tuple[str, str]]] | None = None, **flags) -> dict:
    return {
        "text": text,
        "buttons": [[{"text": t, "data": d} for t, d in row] for row in (buttons or [])],
        "contact": flags.get("contact", False),
        "remove_kb": flags.get("remove_kb", False),
    }


MENU = [
    [("📅 Записаться", "m:book")],
    [("💰 Цены", "m:prices"), ("📍 Адрес и часы", "m:info")],
    [("🗂 Мои записи", "m:my")],
]


def normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 11 and digits[0] in "78":
        return "+7" + digits[1:]
    if len(digits) == 10 and digits[0] == "9":
        return "+7" + digits
    return None


def mask_phone(phone: str) -> str:
    return f"+7 ••• •••-••-{phone[-2:]}"


def pretty_phone(phone: str) -> str:
    d = phone[2:]
    return f"+7 {d[:3]} {d[3:6]}-{d[6:8]}-{d[8:]}"


class Engine:
    def __init__(self, store):
        self.store = store

    # ---------- хранение ----------
    async def session(self, sid: str) -> dict:
        return await self.store.get_json(f"sess:{sid}") or {"step": "menu"}

    async def save_session(self, sid: str, s: dict) -> None:
        await self.store.set_json(f"sess:{sid}", s, ex=TTL)

    async def leads(self) -> list[dict]:
        items = await self.store.get_json("leads") or []
        border = (now() - timedelta(seconds=TTL)).isoformat()
        return [x for x in items if x["created_at"] >= border]

    async def save_leads(self, items: list[dict]) -> None:
        await self.store.set_json("leads", items[-300:], ex=TTL * 2)

    async def taken(self) -> set[tuple[str, str, str]]:
        return {(x["master"], x["date"], x["time"]) for x in await self.leads() if x["status"] != "cancelled"}

    async def push_inbox(self, sid: str, text: str) -> None:
        box = await self.store.get_json(f"inbox:{sid}") or []
        box.append(text)
        await self.store.set_json(f"inbox:{sid}", box[-20:], ex=TTL)

    async def pop_inbox(self, sid: str) -> list[str]:
        box = await self.store.get_json(f"inbox:{sid}") or []
        if box:
            await self.store.delete(f"inbox:{sid}")
        return box

    # ---------- вход ----------
    async def handle(self, sid: str, source: str, event: dict, profile_name: str | None = None) -> list[dict]:
        s = await self.session(sid)
        kind = event.get("type")

        if kind == "start":
            s = {"step": "menu"}
            out = [msg(
                f"Здравствуйте! Я бот салона красоты {SALON['name']} 👋\n"
                "Запишу вас к мастеру за минуту, подскажу цены и адрес.",
                MENU,
            )]
        elif kind == "action":
            out = await self.on_action(sid, source, s, event.get("data", ""), profile_name)
        elif kind == "contact":
            out = await self.on_phone(s, event.get("phone", ""))
        else:
            out = await self.on_text(sid, source, s, (event.get("text") or "").strip(), profile_name)

        await self.save_session(sid, s)
        return out

    # ---------- кнопки ----------
    async def on_action(self, sid, source, s, data, profile_name) -> list[dict]:
        if data in ("menu", "m:menu"):
            s.clear(); s["step"] = "menu"
            return [msg("Главное меню 👇", MENU)]
        if data == "m:book":
            s.clear(); s["step"] = "service"
            return [self.ask_service()]
        if data == "m:prices":
            return [self.prices()]
        if data == "m:info":
            return [self.info()]
        if data == "m:my":
            return [await self.my_bookings(sid)]

        if data.startswith("svc:") and data[4:] in SERVICES:
            s.update(step="master", service=data[4:])
            return [self.ask_master(s["service"])]
        if data.startswith("ms:") and "service" in s:
            master = data[3:]
            if master != "any" and master not in SERVICES[s["service"]]["masters"]:
                return [self.ask_master(s["service"])]
            s.update(step="date", master=master)
            return [await self.ask_date(s)]
        if data.startswith("d:") and "master" in s:
            s.update(step="slot", date=data[2:])
            return [await self.ask_slot(s)]
        if data.startswith("t:") and "date" in s:
            slots = free_slots(s["service"], s["master"], s["date"], await self.taken())
            t = data[2:]
            if t not in slots:
                return [msg("Это время только что заняли 😔 Выберите другое:"), await self.ask_slot(s)]
            s.update(step="name", time=t, assigned=slots[t])
            return [self.ask_name(profile_name)]
        if data.startswith("nm:") and s.get("step") == "name":
            return self.set_name(s, data[3:])
        if data == "ph:demo" and s.get("step") == "phone":
            return await self.on_phone(s, DEMO_PHONE)
        if data == "ok" and s.get("step") == "confirm":
            return await self.confirm(sid, source, s)
        if data == "back":
            return await self.back(s)
        if data.startswith("cancel:"):
            return await self.cancel(sid, data[7:])

        return [msg("Кнопка устарела, давайте начнем заново 👇", MENU)]

    # ---------- свободный текст ----------
    async def on_text(self, sid, source, s, text, profile_name) -> list[dict]:
        step = s.get("step")
        low = text.lower()
        if low in ("/start", "start", "меню", "/menu"):
            s.clear(); s["step"] = "menu"
            return [msg("Главное меню 👇", MENU)]
        if step == "name":
            return self.set_name(s, text)
        if step == "phone":
            if "демо" in low:
                return await self.on_phone(s, DEMO_PHONE)
            return await self.on_phone(s, text)

        if any(w in low for w in ("цен", "стоим", "сколько", "прайс")):
            return [self.prices()]
        if any(w in low for w in ("адрес", "где", "как добрат", "час", "работает", "время работы")):
            return [self.info()]
        if any(w in low for w in ("отмен", "мои запис", "перенес")):
            return [await self.my_bookings(sid)]
        if any(w in low for w in ("запис", "стриж", "маникюр", "окраш", "хочу")):
            s.clear(); s["step"] = "service"
            return [self.ask_service()]
        if any(w in low for w in ("привет", "здравств", "добрый", "hello", "hi")):
            return [msg("Здравствуйте! Чем помочь? 👇", MENU)]
        return [msg(
            "Я демо-бот записи и понимаю в основном кнопки 🙂\n"
            "Попробуйте записаться или спросите про цены и адрес.",
            MENU,
        )]

    # ---------- шаги ----------
    def ask_service(self) -> dict:
        rows = [[(f"{v['title']} · {price_label(v)}", f"svc:{k}")] for k, v in SERVICES.items()]
        return msg("Какую услугу выбираете?", rows + [[("← В меню", "menu")]])

    def ask_master(self, service_id: str) -> dict:
        rows = [[(f"{MASTERS[m]['name']}, {MASTERS[m]['role']}", f"ms:{m}")] for m in SERVICES[service_id]["masters"]]
        if len(rows) > 1:
            rows.append([("Любой свободный мастер", "ms:any")])
        return msg(f"{SERVICES[service_id]['title']}. К кому записать?", rows + [[("← Назад", "back")]])

    async def ask_date(self, s) -> dict:
        taken = await self.taken()
        days = [d for d in available_days() if free_slots(s["service"], s["master"], d, taken)]
        if not days:
            return msg("На ближайшую неделю мест нет 😔 Попробуйте другого мастера.", [[("← Назад", "back")]])
        buttons = [(day_label(d), f"d:{d}") for d in days]
        rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
        return msg("Выберите день:", rows + [[("← Назад", "back")]])

    async def ask_slot(self, s) -> dict:
        slots = list(free_slots(s["service"], s["master"], s["date"], await self.taken()))
        if not slots:
            return msg("На этот день все занято. Выберите другой:", [[("← Назад", "back")]])
        buttons = [(t, f"t:{t}") for t in slots]
        rows = [buttons[i:i + 4] for i in range(0, len(buttons), 4)]
        return msg(f"Свободное время на {day_label(s['date'])}:", rows + [[("← Назад", "back")]])

    def ask_name(self, profile_name: str | None) -> dict:
        rows = []
        if profile_name:
            short = profile_name.strip()[:20]
            rows.append([(f"Я {short}", f"nm:{short}")])
        return msg("Как к вам обращаться? Напишите имя.", rows + [[("← Назад", "back")]])

    def set_name(self, s, name: str) -> list[dict]:
        name = re.sub(r"\s+", " ", name).strip()
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\- ]{2,30}", name):
            return [msg("Имя должно быть от 2 до 30 букв. Как вас зовут?")]
        s.update(step="phone", name=name.title())
        return [msg(
            f"Приятно познакомиться, {s['name']}! Оставьте номер телефона для подтверждения записи.\n"
            "Можно отправить кнопкой или написать, например +7 900 123-45-67.",
            [[("Использовать демо-номер", "ph:demo")], [("← Назад", "back")]],
            contact=True,
        )]

    async def on_phone(self, s, raw: str) -> list[dict]:
        if s.get("step") != "phone":
            return [msg("Сначала выберите услугу и время 👇", MENU)]
        phone = normalize_phone(raw)
        if not phone:
            return [msg("Не похоже на номер 🤔 Напишите в формате +7 900 123-45-67 или нажмите «Использовать демо-номер».",
                        [[("Использовать демо-номер", "ph:demo")]], contact=True)]
        s.update(step="confirm", phone=phone)
        svc = SERVICES[s["service"]]
        return [
            msg("Номер получен ✓", remove_kb=True),
            msg(
                "Проверьте запись:\n\n"
                f"💇 {svc['title']} · {price_label(svc)}\n"
                f"👤 Мастер: {MASTERS[s['assigned']]['name']}\n"
                f"🗓 {day_label(s['date'])}, {s['time']}\n"
                f"🙋 {s['name']}, {pretty_phone(phone)}",
                [[("✅ Подтвердить", "ok")], [("← Изменить время", "back")]],
            ),
        ]

    async def confirm(self, sid, source, s) -> list[dict]:
        if (s["assigned"], s["date"], s["time"]) in await self.taken():
            s["step"] = "slot"
            return [msg("Ой, это время только что заняли 😔"), await self.ask_slot(s)]
        lead = {
            "id": secrets.token_hex(3),
            "sid": sid,
            "source": source,
            "created_at": now().isoformat(),
            "name": s["name"],
            "phone": mask_phone(s["phone"]),
            "service": s["service"],
            "master": s["assigned"],
            "date": s["date"],
            "time": s["time"],
            "status": "new",
        }
        items = await self.leads()
        items.append(lead)
        await self.save_leads(items)
        s.clear(); s["step"] = "menu"
        return [msg(
            f"Готово, вы записаны! 🎉\nНомер записи: #{lead['id']}\n\n"
            "Администратор подтвердит запись, и я пришлю уведомление.",
            MENU,
        )]

    async def back(self, s) -> list[dict]:
        order = ["service", "master", "date", "slot", "name", "phone", "confirm"]
        step = s.get("step", "menu")
        if step not in order or step == "service":
            s.clear(); s["step"] = "menu"
            return [msg("Главное меню 👇", MENU)]
        prev = {"master": "service", "date": "master", "slot": "date", "name": "slot",
                "phone": "name", "confirm": "slot"}[step]
        s["step"] = prev
        if prev == "service":
            return [self.ask_service()]
        if prev == "master":
            return [self.ask_master(s["service"])]
        if prev == "date":
            return [await self.ask_date(s)]
        if prev == "slot":
            return [await self.ask_slot(s)]
        return [self.ask_name(None)]

    def prices(self) -> dict:
        lines = [f"• {v['title']}: {price_label(v)} ({v['minutes']} мин)" for v in SERVICES.values()]
        return msg("Наши цены:\n\n" + "\n".join(lines), [[("📅 Записаться", "m:book")], [("← В меню", "menu")]])

    def info(self) -> dict:
        return msg(
            f"📍 {SALON['address']}\n🕙 {SALON['hours']}\n📞 {SALON['phone']}",
            [[("📅 Записаться", "m:book")], [("← В меню", "menu")]],
        )

    async def my_bookings(self, sid) -> dict:
        mine = [x for x in await self.leads() if x["sid"] == sid and x["status"] in ("new", "confirmed")]
        if not mine:
            return msg("У вас пока нет активных записей.", [[("📅 Записаться", "m:book")], [("← В меню", "menu")]])
        lines, rows = [], []
        for x in mine:
            lines.append(f"#{x['id']} · {SERVICES[x['service']]['title']}, {day_label(x['date'])} {x['time']}, "
                         f"{MASTERS[x['master']]['name']} ({STATUSES[x['status']].lower()})")
            rows.append([(f"Отменить #{x['id']}", f"cancel:{x['id']}")])
        return msg("Ваши записи:\n\n" + "\n".join(lines), rows + [[("← В меню", "menu")]])

    async def cancel(self, sid, lead_id) -> list[dict]:
        items = await self.leads()
        for x in items:
            if x["id"] == lead_id and x["sid"] == sid and x["status"] in ("new", "confirmed"):
                x["status"] = "cancelled"
                await self.save_leads(items)
                return [msg(f"Запись #{lead_id} отменена. Будем ждать вас в другой раз 🙌", MENU)]
        return [msg("Запись не найдена или уже отменена.", MENU)]

    # ---------- админка ----------
    async def set_status(self, lead_id: str, status: str) -> dict | None:
        if status not in STATUSES:
            return None
        items = await self.leads()
        for x in items:
            if x["id"] == lead_id:
                x["status"] = status
                await self.save_leads(items)
                return x
        return None

    def status_message(self, lead: dict) -> str | None:
        when = f"{day_label(lead['date'])} в {lead['time']}"
        if lead["status"] == "confirmed":
            return f"✅ Запись #{lead['id']} подтверждена! Ждем вас {when}. Мастер: {MASTERS[lead['master']]['name']}."
        if lead["status"] == "cancelled":
            return f"❌ К сожалению, запись #{lead['id']} на {when} отменена салоном. Выберите другое время в меню."
        return None

    async def ensure_seed(self) -> None:
        """Немного демо-заявок, чтобы админка не была пустой."""
        items = await self.store.get_json("leads") or []
        today = now().strftime("%Y-%m-%d")
        if any(x.get("seed") == today for x in items):
            return
        items = [x for x in items if not x.get("seed")]
        days = available_days()
        samples = [
            ("Екатерина", "hw", "anna", 0, "12:00", "telegram", "confirmed", 6),
            ("Дмитрий", "hm", "oleg", 0, "15:00", "web", "new", 3),
            ("Ольга", "mn", "maria", 1, "11:00", "telegram", "new", 2),
            ("Светлана", "cl", "irina", 1, "14:00", "telegram", "confirmed", 5),
            ("Игорь", "hm", "oleg", 2, "18:00", "web", "cancelled", 8),
        ]
        stamp = now()
        for i, (name, svc, master, d, t, src, status, hours_ago) in enumerate(samples):
            items.append({
                "id": f"d{today[-2:]}{i}", "sid": "seed", "seed": today, "source": src,
                "created_at": (stamp - timedelta(hours=hours_ago)).isoformat(),
                "name": name, "phone": f"+7 ••• •••-••-{17 + i * 11}", "service": svc, "master": master,
                "date": days[min(d, len(days) - 1)], "time": t, "status": status,
            })
        await self.save_leads(items)

    async def stats(self) -> dict:
        items = await self.leads()
        active = [x for x in items if x["status"] != "cancelled"]
        return {
            "total": len(items),
            "new": sum(x["status"] == "new" for x in items),
            "confirmed": sum(x["status"] == "confirmed" for x in items),
            "telegram": sum(x["source"] == "telegram" for x in items),
            "web": sum(x["source"] == "web" for x in items),
            "revenue": sum(SERVICES[x["service"]]["price"] for x in active),
        }
