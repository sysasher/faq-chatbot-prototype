import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configure Vite with the React plugin for JSX and fast development refresh.
export default defineConfig({
  plugins: [react()],
});
