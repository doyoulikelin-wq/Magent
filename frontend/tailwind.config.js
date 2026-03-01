/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        heading: ['"Space Grotesk"', 'sans-serif'],
        body: ['"IBM Plex Sans"', 'sans-serif'],
      },
      colors: {
        primary: '#0f766e',
        accent: '#ea580c',
        panel: '#f8fafc',
      },
      boxShadow: {
        soft: '0 12px 30px -20px rgba(15,118,110,0.45)',
      },
      animation: {
        fadeUp: 'fadeUp 400ms ease-out',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
