/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        // Surface tokens mapped from CSS vars for Tailwind class usage
        bg:         '#080d1a',
        surface:    '#0f172a',
        'surface-2':'#172033',
        slate: {
          950: '#0a0f1e',
          900: '#0f172a',
          850: '#131d31',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
          500: '#64748b',
          400: '#94a3b8',
          300: '#cbd5e1',
          200: '#e2e8f0',
        },
        accent: {
          DEFAULT: '#22d3ee',
          dim:     '#0ea5e9',
        },
        accent2: '#818cf8',
      },
      borderRadius: {
        sm:  '4px',
        md:  '8px',
        lg:  '12px',
        xl:  '16px',
        '2xl':'20px',
      },
      boxShadow: {
        sm:   '0 1px 2px rgba(0,0,0,0.5)',
        md:   '0 4px 12px rgba(0,0,0,0.4)',
        lg:   '0 8px 24px rgba(0,0,0,0.5)',
        glow: '0 0 16px rgba(34,211,238,0.14)',
        'glow-violet': '0 0 16px rgba(129,140,248,0.22)',
      },
      animation: {
        'pulse-slow':  'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-live':  'pulse-live 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow':   'spin 2s linear infinite',
        'fade-slide':  'fadeSlideIn 180ms ease both',
        shimmer:       'shimmer 1.4s ease-in-out infinite',
      },
      keyframes: {
        'pulse-live': {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.4' },
        },
        fadeSlideIn: {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          from: { backgroundPosition: '200% 0' },
          to:   { backgroundPosition: '-200% 0' },
        },
      },
      backgroundImage: {
        'accent-gradient': 'linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)',
      },
      maxWidth: {
        content: '1360px',
      },
    },
  },
  plugins: [],
}
