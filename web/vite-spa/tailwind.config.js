/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#E6F0FF',
          100: '#CCE0FF',
          500: '#0066FF',
          600: '#0052CC',
          700: '#003D99',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
      },
      maxWidth: {
        page: '1200px',
      },
    },
  },
  plugins: [],
};
