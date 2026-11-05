import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

const proxyTarget = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000';
const usePolling = process.env.CHOKIDAR_USEPOLLING === 'true';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'By the Book',
        short_name: 'By the Book',
        description: 'Inspection reports and security deposit records for Alberta rental properties.',
        theme_color: '#3e6b5a',
        background_color: '#f5f5f7',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
  server: {
    port: 3000,
    host: true,
    watch: usePolling ? { usePolling: true, interval: 1000 } : undefined,
    proxy: {
      '/api': { target: proxyTarget },
      '/media': { target: proxyTarget },
    },
  },
  preview: {
    port: 3000,
    host: true,
  },
});
