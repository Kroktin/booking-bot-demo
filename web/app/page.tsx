'use client'

import { useCallback, useState } from 'react'
import Admin from '@/components/Admin'
import Chat from '@/components/Chat'
import { BOT_USERNAME, PORTFOLIO_URL } from '@/lib/api'

const STEPS = [
  ['Запишитесь в чате', 'Выберите услугу, мастера и время. Можно кнопками, можно текстом.'],
  ['Заявка появится в админке', 'Справа то, что видит администратор салона. Обновляется сама.'],
  ['Подтвердите запись', 'Нажмите «Подтвердить», и бот сразу пришлет клиенту уведомление.'],
]

export default function Page() {
  const [tab, setTab] = useState<'chat' | 'admin'>('chat')
  const [refreshKey, setRefreshKey] = useState(0)
  const onBooked = useCallback(() => setRefreshKey(k => k + 1), [])

  return (
    <main className="mx-auto flex min-h-screen max-w-[1240px] flex-col px-4 pb-8 pt-6 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-lumi-400 to-lumi-600 text-xl font-extrabold text-white">L</div>
          <div>
            <h1 className="text-lg font-bold leading-tight text-white sm:text-xl">Бот записи для салона красоты</h1>
            <p className="text-sm text-slate-400">Демо: веб-чат, Telegram-бот и админка работают на одном бэкенде</p>
          </div>
        </div>
        <a
          href={`https://t.me/${BOT_USERNAME}`}
          target="_blank"
          rel="noopener"
          className="inline-flex items-center gap-2 rounded-xl bg-[#2aabee] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#229ed9]"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current"><path d="M21.6 3.2 2.7 10.5c-1.3.5-1.3 1.2-.2 1.6l4.8 1.5 1.9 5.6c.2.6.4.9.9.9.4 0 .6-.2.9-.5l2.4-2.3 4.9 3.6c.9.5 1.6.2 1.8-.8l3.3-15.3c.3-1.3-.5-1.9-1.8-1.6Z" /></svg>
          Открыть в Telegram
        </a>
      </header>

      <ol className="mt-6 grid gap-3 sm:grid-cols-3">
        {STEPS.map(([title, text], i) => (
          <li key={title} className="rounded-2xl border border-line bg-white/[0.02] p-4">
            <div className="text-xs font-bold text-lumi-400">0{i + 1}</div>
            <div className="mt-1 font-semibold text-white">{title}</div>
            <div className="mt-1 text-sm text-slate-400">{text}</div>
          </li>
        ))}
      </ol>

      <div className="mt-5 flex gap-2 lg:hidden">
        {(['chat', 'admin'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-xl py-2.5 text-sm font-semibold transition ${tab === t ? 'bg-lumi-500 text-white' : 'bg-white/5 text-slate-300'}`}
          >
            {t === 'chat' ? 'Чат с ботом' : 'Админка'}
          </button>
        ))}
      </div>

      <section className="mt-4 grid flex-1 gap-5 lg:mt-6 lg:grid-cols-[420px_1fr]">
        <div className={`h-[640px] lg:block ${tab === 'chat' ? 'block' : 'hidden'}`}>
          <Chat onBooked={onBooked} />
        </div>
        <div className={`h-[640px] lg:block ${tab === 'admin' ? 'block' : 'hidden'}`}>
          <Admin refreshKey={refreshKey} />
        </div>
      </section>

      <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
        <span>Демо-сценарий записи. Заявки хранятся 24 часа, телефоны в админке скрыты.</span>
        <a href={PORTFOLIO_URL} target="_blank" rel="noopener" className="text-slate-400 transition hover:text-white">
          Портфолио разработчика →
        </a>
      </footer>
    </main>
  )
}
