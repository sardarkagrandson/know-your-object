import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the FastAPI backend so the browser sees a single origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.ASTROSCOPE_API_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 3000, // aladin-lite ships its WebAssembly inline (~2 MB)
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
