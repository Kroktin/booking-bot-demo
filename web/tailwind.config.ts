import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17181f',
        panel: '#1f2029',
        line: 'rgba(255,255,255,0.08)',
        lumi: { 50: '#fdf2f8', 200: '#f5c2dc', 400: '#e879b0', 500: '#d9468f', 600: '#b8326f' },
        tg: { bg: '#0e1621', head: '#17212b', in: '#182533', out: '#2b5278', btn: '#1f2f3f', accent: '#64b5ef' },
      },
      fontFamily: { sans: ['var(--font-sans)', 'system-ui', 'sans-serif'] },
      keyframes: {
        pop: { '0%': { opacity: '0', transform: 'translateY(6px) scale(.98)' }, '100%': { opacity: '1', transform: 'none' } },
        flash: { '0%': { backgroundColor: 'rgba(217,70,143,.25)' }, '100%': { backgroundColor: 'transparent' } },
      },
      animation: { pop: 'pop .25s ease-out', flash: 'flash 2.5s ease-out' },
    },
  },
  plugins: [],
}
export default config
