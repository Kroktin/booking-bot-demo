# Lumi: бот записи для салона красоты

Демо-проект: Telegram-бот и веб-чат для записи клиентов к мастеру, плюс админка заявок.
Оба канала работают на одном Python-движке сценария, заявки из Telegram и с сайта попадают в одну админку.

**Demo:** https://lumi-bot-demo.netlify.app
**Telegram:** [@lumi_demo_bot](https://t.me/lumi_demo_bot)

## Что умеет
- Запись: услуга → мастер (или «любой свободный») → день → свободное время → имя → телефон → подтверждение
- Учет занятости: занятые слоты не предлагаются, повторная проверка при подтверждении
- «Мои записи» и отмена записи клиентом
- Цены, адрес и часы работы; понимает простые вопросы текстом («сколько стоит», «где вы»)
- Telegram: инлайн-кнопки, отправка номера кнопкой «Поделиться контактом»
- Админка: статистика, фильтры, смена статуса заявки
- Уведомление клиенту при подтверждении или отмене записи (в Telegram или в веб-чат)
- Защита публичного демо: лимиты запросов, заявки хранятся 24 часа, телефоны в админке маскируются

## Стек
- **Бэкенд:** Python 3.12, FastAPI, aiogram 3 (webhook), Upstash Redis
- **Фронтенд:** Next.js 14, TypeScript, Tailwind CSS (статический экспорт)
- **Хостинг:** API на Vercel (Python runtime), фронтенд на Netlify с проксированием `/api/py/*`

## Структура
```
api/
  index.py          HTTP API: чат, админка, webhook Telegram
  _core/engine.py   сценарий записи (не зависит от канала)
  _core/salon.py    услуги, мастера, расписание
  _core/tg.py       адаптер aiogram
  _core/storage.py  Redis или память процесса
web/                Next.js: веб-чат и админка
tests/              pytest: сценарий, API, Telegram-адаптер
```

## Локальный запуск
```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt uvicorn pytest httpx
.venv/Scripts/python -m pytest tests
.venv/Scripts/uvicorn api.index:app --port 8000 --app-dir .

cd web && npm install
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api/py npm run dev
```

## Webhook
```bash
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -d url=https://<api-domain>/api/py/telegram -d secret_token=$TELEGRAM_WEBHOOK_SECRET
```
