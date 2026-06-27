import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  root: "frontend",
  publicDir: false,
  build: {
    outDir: "../dist",
    emptyOutDir: true
  }
});
