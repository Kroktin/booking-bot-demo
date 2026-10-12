'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { api, Lead, LeadStatus, MASTERS, PRICES, SERVICES, Stats } from '@/lib/api'

const STATUS: Record<LeadStatus, { label: string; cls: string }> = {
  new: { label: 'Новая', cls: 'bg-lumi-500/15 text-lumi-200 ring-lumi-500/40' },
  confirmed: { label: 'Подтверждена', cls: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/40' },
  done: { label: 'Завершена', cls: 'bg-sky-500/15 text-sky-300 ring-sky-500/40' },
  cancelled: { label: 'Отменена', cls: 'bg-slate-500/15 text-slate-400 ring-slate-500/30' },
}
const FILTERS: { id: 'all' | LeadStatus; label: string }[] = [
  { id: 'all', label: 'Все' },
  { id: 'new', label: 'Новые' },
  { id: 'confirmed', label: 'Подтвержденные' },
  { id: 'cancelled', label: 'Отмененные' },
]
const WEEKDAYS = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']

function dayLabel(d: string) {
  const dt = new Date(d + 'T00:00:00')
  return `${WEEKDAYS[dt.getDay()]} ${dt.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })}`
}
function ago(iso: string) {
  const min = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000))
  if (min < 1) return 'только что'
  if (min < 60) return `${min} мин назад`
  return `${Math.round(min / 60)} ч назад`
}
const rub = (n: number) => n.toLocaleString('ru-RU') + ' ₽'

export default function Admin({ refreshKey }: { refreshKey: number }) {
  const [leads, setLeads] = useState<Lead[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [filter, setFilter] = useState<'all' | LeadStatus>('all')
  const [fresh, setFresh] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState('')
  const [offline, setOffline] = useState(false)
  const known = useRef<Set<string> | null>(null)

  const load = useCallback(async () => {
    try {
      const data = await api.leads()
      if (known.current) {
        const added = data.leads.filter(l => !known.current!.has(l.id)).map(l => l.id)
        if (added.length) setFresh(new Set(added))
      }
      known.current = new Set(data.leads.map(l => l.id))
      setLeads(data.leads)
      setStats(data.stats)
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }, [])

  useEffect(() => {
    load()
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [load])

  useEffect(() => { if (refreshKey) load() }, [refreshKey, load])

  const change = async (id: string, status: LeadStatus) => {
    setBusy(id)
    try {
      await api.setStatus(id, status)
      await load()
    } finally {
      setBusy('')
    }
  }

  const shown = leads.filter(l => filter === 'all' || l.status === filter)

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-[28px] border border-line bg-panel shadow-2xl shadow-black/40">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div>
          <div className="text-xs uppercase tracking-[0.2em] text-lumi-400">Админка салона</div>
          <div className="text-lg font-semibold text-white">Заявки на запись</div>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className={`h-2 w-2 rounded-full ${offline ? 'bg-red-500' : 'bg-emerald-400 shadow-[0_0_8px] shadow-emerald-400'}`} />
          {offline ? 'нет связи' : 'обновляется онлайн'}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 px-5 pt-4 sm:grid-cols-4">
        {[
          ['Заявок за сутки', stats?.total ?? '—'],
          ['Ждут ответа', stats?.new ?? '—'],
          ['Из Telegram / сайта', stats ? `${stats.telegram} / ${stats.web}` : '—'],
          ['Сумма записей', stats ? rub(stats.revenue) : '—'],
        ].map(([label, value]) => (
          <div key={label as string} className="rounded-2xl border border-line bg-white/[0.03] px-4 py-3">
            <div className="text-xl font-bold text-white">{value}</div>
            <div className="text-xs text-slate-400">{label}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-1.5 overflow-x-auto px-5 pt-4">
        {FILTERS.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-medium transition ${
              filter === f.id ? 'bg-lumi-500 text-white' : 'bg-white/5 text-slate-300 hover:bg-white/10'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-3 flex-1 space-y-2 overflow-y-auto px-5 pb-5">
        {shown.length === 0 && <div className="py-10 text-center text-sm text-slate-500">Заявок пока нет</div>}
        {shown.map(l => (
          <div
            key={l.id}
            className={`rounded-2xl border border-line bg-white/[0.02] p-4 ${fresh.has(l.id) ? 'animate-flash ring-1 ring-lumi-500/60' : ''}`}
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">{l.name}</span>
                  <span className="text-xs text-slate-500">#{l.id}</span>
                  <span title={l.source === 'telegram' ? 'Из Telegram' : 'С сайта'} className="text-xs text-slate-400">
                    {l.source === 'telegram' ? '✈ Telegram' : '🌐 сайт'}
                  </span>
                </div>
                <div className="mt-1 text-sm text-slate-300">
                  {SERVICES[l.service]} · {MASTERS[l.master]} · {dayLabel(l.date)}, {l.time}
                </div>
                <div className="mt-0.5 text-xs text-slate-500">
                  {l.phone} · {rub(PRICES[l.service])} · {ago(l.created_at)}
                </div>
              </div>
              <span className={`rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${STATUS[l.status].cls}`}>{STATUS[l.status].label}</span>
            </div>
            {(l.status === 'new' || l.status === 'confirmed') && (
              <div className="mt-3 flex flex-wrap gap-2">
                {l.status === 'new' && (
                  <button disabled={busy === l.id} onClick={() => change(l.id, 'confirmed')} className="rounded-lg bg-emerald-500/90 px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-emerald-400 disabled:opacity-50">
                    Подтвердить
                  </button>
                )}
                {l.status === 'confirmed' && (
                  <button disabled={busy === l.id} onClick={() => change(l.id, 'done')} className="rounded-lg bg-sky-500/90 px-3 py-1.5 text-xs font-semibold text-ink transition hover:bg-sky-400 disabled:opacity-50">
                    Клиент пришел
                  </button>
                )}
                <button disabled={busy === l.id} onClick={() => change(l.id, 'cancelled')} className="rounded-lg bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-300 transition hover:bg-white/10 disabled:opacity-50">
                  Отменить
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
