/** @type {import('tailwindcss').Config} */

// Las escalas slate (superficies/texto) y cyan (acento) se resuelven con
// variables CSS que cada tema redefine (ver src/theme/themes.ts).
const themed = (name) =>
  Object.fromEntries(
    ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"].map((k) => [
      k,
      `rgb(var(--${name}-${k}) / <alpha-value>)`,
    ]),
  );

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        slate: themed("slate"),
        cyan: themed("cyan"),
        risk: { low: "#22c55e", mid: "#facc15", high: "#dc2626" },
      },
      fontFamily: {
        sans: ["var(--font-body)", "Inter", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
