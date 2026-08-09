/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          cyan: '#22d3ee',
          emerald: '#34d399',
          amber: '#fbbf24',
        },
      },
    },
  },
  plugins: [],
}
