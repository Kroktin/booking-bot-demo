export type Button = { text: string; data: string }
export type Reply = { text: string; buttons: Button[][]; contact: boolean; remove_kb: boolean }
export type ChatEvent =
  | { type: 'start' }
  | { type: 'text'; text: string }
  | { type: 'action'; data: string }

export type LeadStatus = 'new' | 'confirmed' | 'done' | 'cancelled'
export type Lead = {
  id: string
  source: 'web' | 'telegram'
  created_at: string
  name: string
  phone: string
  service: string
  master: string
  date: string
  time: string
  status: LeadStatus
}
export type Stats = { total: number; new: number; confirmed: number; telegram: number; web: number; revenue: number }

// Локально API крутится на uvicorn, на проде доступен по тому же домену через прокси хостинга.
const BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/api/py'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers || {}) },
    cache: 'no-store',
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  chat: (sid: string, event: ChatEvent) =>
    call<{ replies: Reply[] }>('/chat', { method: 'POST', body: JSON.stringify({ sid, event }) }),
  inbox: (sid: string) => call<{ messages: string[] }>(`/inbox?sid=${encodeURIComponent(sid)}`),
  leads: () => call<{ leads: Lead[]; stats: Stats }>('/leads'),
  setStatus: (id: string, status: LeadStatus) =>
    call<{ ok: boolean }>(`/leads/${id}`, { method: 'POST', body: JSON.stringify({ status }) }),
}

export const SERVICES: Record<string, string> = {
  hw: 'Женская стрижка',
  hm: 'Мужская стрижка',
  cl: 'Окрашивание',
  mn: 'Маникюр с покрытием',
}
export const PRICES: Record<string, number> = { hw: 2500, hm: 1500, cl: 4500, mn: 1800 }
export const MASTERS: Record<string, string> = { anna: 'Анна', irina: 'Ирина', oleg: 'Олег', maria: 'Мария' }

export function sessionId(): string {
  const key = 'lumi-demo-sid'
  try {
    const saved = localStorage.getItem(key)
    if (saved) return saved
    const sid = crypto.randomUUID()
    localStorage.setItem(key, sid)
    return sid
  } catch {
    return crypto.randomUUID()
  }
}

export const BOT_USERNAME = process.env.NEXT_PUBLIC_BOT_USERNAME || 'lumi_demo_bot'
export const PORTFOLIO_URL = 'https://anatoly-dev.netlify.app'
