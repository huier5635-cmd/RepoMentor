import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const backendUrl = process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: backendUrl,
        changeOrigin: true
      }
    }
  }
});
