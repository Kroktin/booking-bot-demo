import type { Metadata, Viewport } from 'next'
import { Manrope } from 'next/font/google'
import './globals.css'

const sans = Manrope({ subsets: ['latin', 'cyrillic'], variable: '--font-sans' })

export const metadata: Metadata = {
  title: 'Lumi · демо бота записи',
  description: 'Демо Telegram-бота для записи клиентов в салон: чат, админка заявок и уведомления в реальном времени.',
  icons: { icon: '/favicon.svg' },
}

export const viewport: Viewport = { themeColor: '#17181f' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className={sans.variable}>
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}
