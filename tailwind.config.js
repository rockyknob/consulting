/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: "#1a202c",
        accent: "#3b82f6",
      },
    },
  },
  plugins: [],
}
