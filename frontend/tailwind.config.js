/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'risk-low': '#10b981',
        'risk-medium': '#f59e0b',
        'risk-high': '#ef4444',
      },
    },
  },
  plugins: [],
}
