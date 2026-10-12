'use client'

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import { api, Button, ChatEvent, Reply, sessionId } from '@/lib/api'

type Msg = { id: number; from: 'bot' | 'me'; text: string; buttons: Button[][]; time: string; active: boolean; system?: boolean }

let counter = 0
const clock = () => new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })

export default function Chat({ onBooked }: { onBooked: () => void }) {
  const [sid, setSid] = useState('')
  const [messages, setMessages] = useState<Msg[]>([])
  const [typing, setTyping] = useState(false)
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const scroller = useRef<HTMLDivElement>(null)
  const started = useRef(false)

  const pushBot = useCallback((replies: Reply[]) => {
    setMessages(prev => [
      ...prev,
      ...replies
        .filter(r => r.text)
        .map(r => ({ id: ++counter, from: 'bot' as const, text: r.text, buttons: r.buttons, time: clock(), active: true })),
    ])
  }, [])

  const send = useCallback(async (event: ChatEvent, echo?: string) => {
    if (!sid) return
    setError('')
    setMessages(prev => [
      ...prev.map(m => ({ ...m, active: false })),
      ...(echo ? [{ id: ++counter, from: 'me' as const, text: echo, buttons: [], time: clock(), active: false }] : []),
    ])
    setTyping(true)
    try {
      const [{ replies }] = await Promise.all([api.chat(sid, event), new Promise(r => setTimeout(r, 450))])
      pushBot(replies)
      if (replies.some(r => r.text.includes('вы записаны') || r.text.includes('отменена'))) onBooked()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка сети')
    } finally {
      setTyping(false)
    }
  }, [sid, pushBot, onBooked])

  useEffect(() => { setSid(sessionId()) }, [])

  useEffect(() => {
    if (sid && !started.current) {
      started.current = true
      send({ type: 'start' })
    }
  }, [sid, send])

  // уведомления от «администратора» (подтверждение или отмена записи)
  useEffect(() => {
    if (!sid) return
    const t = setInterval(async () => {
      try {
        const { messages: inbox } = await api.inbox(sid)
        if (inbox.length) {
          setMessages(prev => [
            ...prev,
            ...inbox.map(text => ({ id: ++counter, from: 'bot' as const, text, buttons: [], time: clock(), active: false, system: true })),
          ])
        }
      } catch { /* сеть моргнула, попробуем в следующий раз */ }
    }, 3000)
    return () => clearInterval(t)
  }, [sid])

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' })
  }, [messages, typing])

  const submit = (e: FormEvent) => {
    e.preventDefault()
    const value = text.trim()
    if (!value || typing) return
    setText('')
    send({ type: 'text', text: value }, value)
  }

  const restart = () => send({ type: 'start' }, '/start')

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-[28px] border border-line bg-tg-bg shadow-2xl shadow-black/40">
      <div className="flex items-center gap-3 bg-tg-head px-4 py-3">
        <div className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-lumi-400 to-lumi-600 text-lg font-bold text-white">L</div>
        <div className="min-w-0 flex-1">
          <div className="truncate font-semibold text-white">Lumi · запись в салон</div>
          <div className="text-xs text-tg-accent">{typing ? 'печатает…' : 'бот онлайн'}</div>
        </div>
        <button onClick={restart} className="rounded-lg px-2 py-1 text-xs text-slate-400 transition hover:bg-white/5 hover:text-white" title="Начать заново">
          ↺ заново
        </button>
      </div>

      <div ref={scroller} className="chat-bg flex-1 space-y-2 overflow-y-auto px-3 py-4">
        {messages.map(m => (
          <div key={m.id} className={`flex animate-pop flex-col ${m.from === 'me' ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-[85%] whitespace-pre-line rounded-2xl px-3.5 py-2 text-[14.5px] leading-snug text-white ${
                m.from === 'me' ? 'rounded-br-md bg-tg-out' : m.system ? 'rounded-bl-md bg-emerald-900/70 ring-1 ring-emerald-500/40' : 'rounded-bl-md bg-tg-in'
              }`}
            >
              {m.text}
              <span className="ml-2 inline-block translate-y-1 text-[11px] text-white/40">{m.time}</span>
            </div>
            {m.active && m.buttons.length > 0 && (
              <div className="mt-1 w-full max-w-[85%] space-y-1">
                {m.buttons.map((row, i) => (
                  <div key={i} className="flex gap-1">
                    {row.map(b => (
                      <button
                        key={b.data}
                        onClick={() => send({ type: 'action', data: b.data }, b.text)}
                        disabled={typing}
                        className="flex-1 rounded-lg bg-tg-btn/90 px-2 py-2 text-[13.5px] font-medium text-white transition hover:bg-[#2a3f55] disabled:opacity-60"
                      >
                        {b.text}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {typing && (
          <div className="flex w-16 items-center gap-1 rounded-2xl rounded-bl-md bg-tg-in px-3 py-3">
            {[0, 1, 2].map(i => (
              <span key={i} className="h-2 w-2 animate-bounce rounded-full bg-white/50" style={{ animationDelay: `${i * 0.15}s` }} />
            ))}
          </div>
        )}
        {error && <div className="mx-auto w-fit rounded-full bg-red-500/15 px-3 py-1 text-xs text-red-300">{error}</div>}
      </div>

      <form onSubmit={submit} className="flex items-center gap-2 bg-tg-head px-3 py-2.5">
        <input
          value={text}
          onChange={e => setText(e.target.value)}
          maxLength={300}
          placeholder="Сообщение"
          className="min-w-0 flex-1 rounded-full bg-tg-bg px-4 py-2.5 text-[14.5px] text-white outline-none placeholder:text-slate-500 focus:ring-1 focus:ring-tg-accent/60"
        />
        <button type="submit" disabled={!text.trim() || typing} className="grid h-10 w-10 place-items-center rounded-full bg-tg-accent text-tg-bg transition disabled:opacity-40" aria-label="Отправить">
          <svg viewBox="0 0 24 24" className="h-5 w-5 fill-current"><path d="M3.4 20.4 21 12 3.4 3.6 3.4 10l12.6 2-12.6 2z" /></svg>
        </button>
      </form>
    </div>
  )
}
