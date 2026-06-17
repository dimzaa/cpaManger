/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
    "./src/pages/**/*.{js,jsx}",
    "./src/components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#F0F6FF',
          100: '#E0EEFF',
          200: '#C1DDFF',
          300: '#A2CCFF',
          400: '#83BBFF',
          500: '#1E3A5F', // main primary (deep navy)
          600: '#1A3252',
          700: '#142A47',
          800: '#0F213C',
          900: '#0A1831',
          light: '#2E5491', // lighter navy for hover
        },
        success: '#16A34A',
        warning: '#D97706',
        danger: '#DC2626',
        neutral: {
          50: '#F8FAFC',
          100: '#F1F5F9',
          200: '#E2E8F0',
          300: '#CBD5E1',
          400: '#94A3B8',
          500: '#64748B',
          600: '#475569',
          700: '#334155',
          800: '#1E293B',
          900: '#0F172A',
        },
      },
      fontFamily: {
        hebrew: ['Heebo', 'sans-serif'],
        body: ['Assistant', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '12px',
        sm: '8px',
        lg: '16px',
      },
      boxShadow: {
        sm: '0 1px 3px rgba(0,0,0,0.08)',
        DEFAULT: '0 1px 3px rgba(0,0,0,0.12)',
        md: '0 4px 6px rgba(0,0,0,0.12)',
        lg: '0 10px 15px rgba(0,0,0,0.15)',
      },
      spacing: {
        'sidebar': '240px',
        'topbar': '64px',
      },
    },
  },
  plugins: [],
}
