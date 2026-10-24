/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import compression from "vite-plugin-compression";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [
    react(),
    compression({ algorithm: "gzip", ext: ".gz" }),
    compression({ algorithm: "brotliCompress", ext: ".br" }),
  ],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    port: 5173,
    // En desarrollo se usa el mismo esquema de proxy que Nginx en producción (sin CORS)
    proxy: { "/api": { target: process.env.VITE_PROXY_TARGET ?? "http://localhost:8000", changeOrigin: true } },
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          // React y las librerías que dependen de él en un mismo chunk: separarlos
          // provocaba que recharts se evaluara antes que React en producción.
          maplibre: ["maplibre-gl"],
          vendor: ["react", "react-dom", "recharts", "@tanstack/react-query", "@tanstack/react-table",
            "@tanstack/react-virtual"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
