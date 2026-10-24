import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { searchForWorkspaceRoot } from 'vite';
import { defineConfig } from 'vitest/config';

const FACT_TEMPLATES = fileURLToPath(new URL('../facts/templates', import.meta.url));
const API_ORIGIN = process.env.HOSHIZORA_API_ORIGIN ?? 'http://localhost:8080';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': API_ORIGIN },
    fs: { allow: [searchForWorkspaceRoot(process.cwd()), FACT_TEMPLATES] },
  },
  preview: {
    port: 4173,
    strictPort: true,
    proxy: { '/api': API_ORIGIN },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}', 'scripts/**/*.test.ts'],
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
    unstubGlobals: true,
  },
});
