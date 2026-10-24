/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
      colors: {
        risk: { low: "#22c55e", mid: "#facc15", high: "#dc2626" },
      },
    },
  },
  plugins: [],
};
