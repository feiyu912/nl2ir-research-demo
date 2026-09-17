import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig(({ command }) => ({
  // GitHub Pages 项目站点部署在 /nl2ir-research-demo/；开发服务器仍使用根路径。
  base: command === 'build' ? '/nl2ir-research-demo/' : '/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    target: 'es2020',
    outDir: 'dist',
    sourcemap: false,
  },
  server: {
    port: 5173,
    host: '127.0.0.1',
  },
}));
