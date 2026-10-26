import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configuración de Vite para el frontend de PlaneAI UdeA.
// El backend (FastAPI) habilita CORS para http://localhost:5173.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    rollupOptions: {
      output: {
        // Separa las librerías para que el navegador las cachee entre despliegues.
        manualChunks: {
          react: ["react", "react-dom"],
          motion: ["framer-motion"],
          markdown: ["react-markdown", "remark-gfm"],
        },
      },
    },
  },
});
